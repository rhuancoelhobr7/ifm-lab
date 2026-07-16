#!/usr/bin/env python3
"""
export_bars_g8.py — exportador de barras via API Python do MetaTrader 5 (E1).

Equivalente ao ExportBarsG8.mq5, com três vantagens:

- 🔒 TRAVA DE SERVIDOR: recusa exportar se a conta conectada não for a do
  `config.yaml → mt5.conta_servidor` (MetaQuotes-Demo) — evita repetir o
  engano de 2026-07-15 (reexport de outro servidor, reprovado no PROGRESS).
- Escreve direto em `research/2026-07-reatividade-metricas/data/raw/`
  (quando rodado de dentro do repo), sem copiar pasta na mão — e NUNCA
  toca nos arquivos que não são dele (golden_*.csv, server_meta.csv).
- Períodos, pares e servidor esperado vêm do config.yaml da pesquisa
  (nada hard-coded; fallback embutido idêntico só se rodar fora do repo).

💡 Em linguagem simples: é o mesmo exportador de barras, só que em Python —
você roda um comando no computador onde o MetaTrader está instalado e os
CSVs caem prontos na pasta certa, com o script conferindo antes se você
está logado no servidor certo.

Requisitos: rodar NA MÁQUINA do MetaTrader 5 (o pacote `MetaTrader5` só
existe para Windows), com o terminal instalado e logado na conta correta:
    pip install MetaTrader5 pyyaml

Uso típico (da raiz do repo):
    python tools/export_bars/export_bars_g8.py                 # tudo que falta
    python tools/export_bars/export_bars_g8.py --tfs M30,H1 --overwrite
                        # ^ a pendência de 2026-07-15: refazer M30/H1 desde 2021
    python tools/export_bars/export_bars_g8.py --out C:/temp/IFM_export
                        # ^ fora do repo: exporta para uma pasta qualquer

Esquema dos CSVs (idêntico ao ExportBarsG8.mq5, consumido pelo e01_inventario):
    time_epoch,time_server,open,high,low,close,tick_volume,spread
"""

from __future__ import annotations

import argparse
import sys
import time as time_mod
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
RESEARCH = REPO_ROOT / "research" / "2026-07-reatividade-metricas"

G8 = ["USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD"]

# Fallback SOMENTE para rodar fora do repo — cópia fiel do config.yaml congelado.
FALLBACK = {
    "conta_servidor": "MetaQuotes-Demo",
    "fim": "2026-06-30",
    "periodos": {  # tf -> data de início (PLANO §3)
        "MN1": "2016-01-01", "W1": "2016-01-01",
        "D1": "2021-01-01", "H4": "2021-01-01", "H1": "2021-01-01", "M30": "2021-01-01",
        "M15": "2024-07-01", "M5": "2024-07-01",
    },
}
TF_ORDER = ["M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1"]
ARQUIVOS_PROTEGIDOS = ("golden_", "server_meta")   # nunca sobrescritos


def carrega_config() -> dict:
    """Lê config.yaml da pesquisa se existir; senão usa o fallback embutido."""
    cfg_path = RESEARCH / "config.yaml"
    if not cfg_path.exists():
        print(f"AVISO: {cfg_path} não encontrado — usando períodos embutidos "
              f"(cópia do config congelado).")
        return dict(FALLBACK)
    import yaml
    with open(cfg_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    periodos: dict[str, str] = {}
    for camada in raw["timeframes"].values():
        if not isinstance(camada, dict):
            continue
        for tf in camada["tfs"]:
            tf = "MN1" if tf == "MN" else tf
            periodos[tf] = str(camada["periodo"]["inicio"])
    fim = str(next(iter(raw["timeframes"].values()))["periodo"]["fim"])
    return {"conta_servidor": raw["mt5"]["conta_servidor"], "fim": fim, "periodos": periodos}


def detecta_pares_g8(mt5) -> list[str]:
    """Mesma lógica do indicador: base e cotada no G8, sem par repetido.

    Havendo mais de um símbolo para o mesmo par (sufixos de broker), prefere
    o de nome canônico (ex.: 'EURUSD' em vez de 'EURUSD.r').
    """
    candidatos: dict[frozenset, list] = {}
    for s in mt5.symbols_get():
        b, q = s.currency_base, s.currency_profit
        if b in G8 and q in G8 and b != q:
            candidatos.setdefault(frozenset((b, q)), []).append(s)
    pares = []
    for grupo in candidatos.values():
        canonicos = [s for s in grupo if len(s.name) == 6]
        s = (canonicos or grupo)[0]
        if mt5.symbol_select(s.name, True):
            pares.append(s.name)
    return sorted(pares)


def offset_server_gmt(mt5, simbolo: str) -> tuple[float, str]:
    """Estima o offset servidor↔GMT pelo tick mais recente vs. relógio UTC local.

    💡 O tempo do MT5 vem 'carimbado' no fuso do servidor; comparando o carimbo
    do último tick com o relógio UTC desta máquina, a diferença (arredondada)
    é o offset. Só é confiável com o MERCADO ABERTO (tick fresco) e relógio do
    PC certo — com mercado fechado o tick é velho e o número sai errado, então
    o script avisa em vez de afirmar.
    """
    tick = mt5.symbol_info_tick(simbolo)
    if tick is None:
        return float("nan"), "indisponível (sem tick)"
    bruto = (tick.time - datetime.now(timezone.utc).timestamp()) / 3600.0
    arred = round(bruto)
    if abs(bruto - arred) < 0.25 and 0 <= arred <= 4:
        return float(arred), f"{arred:+.1f}h (tick fresco — confiável)"
    return bruto, (f"{bruto:+.1f}h SUSPEITO — mercado fechado ou relógio do PC "
                   f"errado; confira o server_meta/manifest de um export anterior")


def copia_barras(mt5, simbolo: str, tf_const, ini: datetime, fim: datetime):
    """copy_rates_range em pedaços anuais, com retry (histórico baixa aos poucos)."""
    import numpy as np
    pedacos = []
    ano = ini.year
    while True:
        a = max(ini, datetime(ano, 1, 1, tzinfo=timezone.utc))
        b = min(fim, datetime(ano + 1, 1, 1, tzinfo=timezone.utc))
        if a >= fim:
            break
        rates = None
        for _ in range(5):
            rates = mt5.copy_rates_range(simbolo, tf_const, a, b)
            if rates is not None:
                break
            time_mod.sleep(1.0)   # aguarda a sincronização do histórico
        if rates is None:
            return None, f"copy_rates_range falhou: {mt5.last_error()}"
        if len(rates):
            pedacos.append(rates)
        ano += 1
    if not pedacos:
        return None, "vazio (broker sem histórico no período)"
    tudo = np.concatenate(pedacos)
    _, idx = np.unique(tudo["time"], return_index=True)   # dedup na emenda dos anos
    return tudo[np.sort(idx)], "ok"


def escreve_csv(path: Path, rates, digits: int) -> None:
    fmt = f"%.{digits}f"
    with open(path, "w", encoding="ascii", newline="\n") as f:
        f.write("time_epoch,time_server,open,high,low,close,tick_volume,spread\n")
        for r in rates:
            t = int(r["time"])
            f.write("%d,%s,%s,%s,%s,%s,%d,%d\n" % (
                t, datetime.fromtimestamp(t, timezone.utc).strftime("%Y.%m.%d %H:%M"),
                fmt % r["open"], fmt % r["high"], fmt % r["low"], fmt % r["close"],
                int(r["tick_volume"]), int(r["spread"])))


def main() -> int:
    ap = argparse.ArgumentParser(description="Exporta barras dos 28 pares G8 do MT5 para CSV.")
    ap.add_argument("--tfs", default=",".join(TF_ORDER),
                    help="TFs a exportar, separados por vírgula (default: todos)")
    ap.add_argument("--pairs", default="", help="filtro opcional de pares (ex.: EURUSD,GBPJPY)")
    ap.add_argument("--out", default=str(RESEARCH / "data" / "raw"),
                    help="pasta de saída (default: data/raw da pesquisa)")
    ap.add_argument("--overwrite", action="store_true",
                    help="reescreve CSVs existentes (default: pula, como o .mq5)")
    ap.add_argument("--allow-any-server", action="store_true",
                    help="DESLIGA a trava de servidor (use só se souber por quê)")
    ap.add_argument("--terminal", default="", help="caminho do terminal64.exe (opcional)")
    args = ap.parse_args()

    try:
        import MetaTrader5 as mt5
    except ImportError:
        print("ERRO: pacote MetaTrader5 não instalado (é Windows-only).\n"
              "Na máquina do MT5: pip install MetaTrader5 pyyaml")
        return 1

    cfg = carrega_config()
    tfs = [t.strip().replace("MN", "MN1").replace("MN11", "MN1") for t in args.tfs.split(",") if t.strip()]
    invalidos = [t for t in tfs if t not in TF_ORDER]
    if invalidos:
        print(f"ERRO: TF(s) desconhecido(s): {invalidos}. Válidos: {TF_ORDER}")
        return 1

    ok = mt5.initialize(path=args.terminal) if args.terminal else mt5.initialize()
    if not ok:
        print(f"ERRO: mt5.initialize() falhou: {mt5.last_error()} — o terminal está instalado/logado?")
        return 1
    try:
        conta = mt5.account_info()
        servidor = conta.server if conta else "?"
        print(f"Conectado: servidor={servidor} | conta={getattr(conta, 'login', '?')}")

        # 🔒 trava de servidor (a lição de 2026-07-15)
        esperado = cfg["conta_servidor"]
        if esperado.lower() not in servidor.lower():
            if not args.allow_any_server:
                print(f"\n🔒 TRAVA DE SERVIDOR: conectado a '{servidor}', mas o config.yaml da "
                      f"pesquisa exige '{esperado}'.\nDados de outro servidor têm outro fuso, outro "
                      f"histórico e outros símbolos — foi exatamente o erro reprovado no PROGRESS em "
                      f"2026-07-15.\nLogue na conta {esperado} e rode de novo "
                      f"(ou --allow-any-server, por sua conta e risco, para outra finalidade).")
                return 2
            print(f"⚠ trava de servidor DESLIGADA por --allow-any-server (servidor: {servidor})")

        pares = detecta_pares_g8(mt5)
        if args.pairs:
            filtro = {p.strip().upper() for p in args.pairs.split(",") if p.strip()}
            pares = [p for p in pares if any(p.upper().startswith(f) for f in filtro)]
        if len(pares) < 28 and not args.pairs:
            print(f"AVISO: só {len(pares)} pares G8 detectados (esperados 28) — "
                  f"habilite 'Mostrar Todos' no Observatório de Mercado.")
        if not pares:
            print("ERRO: nenhum par G8 encontrado.")
            return 1

        offset, offset_txt = offset_server_gmt(mt5, pares[0])
        print(f"Offset servidor↔GMT estimado: {offset_txt}")

        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        fim = datetime.fromisoformat(cfg["fim"] + "T23:59:00+00:00")

        manifest = [
            f"# export_bars_g8.py v1.0 | exportado_em_local={datetime.now():%Y.%m.%d %H:%M:%S}",
            f"# offset_server_gmt_h={offset:.1f} | fonte=tick_vs_relogio_utc ({offset_txt})",
            f"# broker={getattr(conta, 'company', '?')} | conta_servidor={servidor}",
            "symbol,tf,rows,first_bar,last_bar,status,file",
        ]
        n_ok = n_skip = n_fail = 0
        total = len(pares) * len(tfs)
        feito = 0
        for par in pares:
            digits = mt5.symbol_info(par).digits
            for tf in tfs:
                feito += 1
                arq = out / f"{par}_{tf}.csv"
                assert not arq.name.startswith(ARQUIVOS_PROTEGIDOS)
                if arq.exists() and not args.overwrite:
                    manifest.append(f"{par},{tf},-1,,,pulado_existia,{arq.name}")
                    n_skip += 1
                    continue
                ini = datetime.fromisoformat(cfg["periodos"][tf] + "T00:00:00+00:00")
                rates, status = copia_barras(mt5, par, getattr(mt5, f"TIMEFRAME_{tf}"), ini, fim)
                if rates is None:
                    manifest.append(f"{par},{tf},0,,,FALHA:{status},{arq.name}")
                    n_fail += 1
                    print(f"[{feito}/{total}] {par} {tf}: FALHA ({status})")
                    continue
                escreve_csv(arq, rates, digits)
                t0 = datetime.fromtimestamp(int(rates[0]["time"]), timezone.utc)
                t1 = datetime.fromtimestamp(int(rates[-1]["time"]), timezone.utc)
                manifest.append(f"{par},{tf},{len(rates)},{t0:%Y.%m.%d %H:%M},{t1:%Y.%m.%d %H:%M},ok,{arq.name}")
                n_ok += 1
                print(f"[{feito}/{total}] {par} {tf}: {len(rates)} barras ({t0:%Y-%m-%d} → {t1:%Y-%m-%d})")

        (out / "_manifest.csv").write_text("\n".join(manifest) + "\n", encoding="ascii")
        print(f"\nFIM — {n_ok} ok, {n_skip} pulados, {n_fail} falhas (de {total}).")
        if n_fail:
            print("Rode de novo (sem --overwrite) até zerar as falhas — o histórico baixa aos poucos.")
            return 1
        print(f"CSVs em {out}. Próximo passo: python scripts/e01_inventario.py na pesquisa.")
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    sys.exit(main())

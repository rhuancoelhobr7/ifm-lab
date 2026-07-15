#!/usr/bin/env python3
"""
e01_inventario.py — inventário de cobertura dos CSVs exportados do MT5 (E1).

💡 O que este script faz, em linguagem simples: depois que o usuário roda o
ExportBarsG8 no MetaTrader e copia os CSVs para data/raw/, este script confere
a "mercadoria recebida": (1) chegaram todos os 28 pares × 8 TFs? (2) cada
arquivo cobre o período que o config.yaml pede? (3) há buracos no meio do
histórico (barras faltando fora de fim de semana)? e (4) desenha a "assinatura"
de volume/volatilidade por hora do servidor — a figura que mostra ONDE, no
relógio do servidor, as sessões de Tóquio/Londres/NY realmente acordam
(calibração prevista no adendo 2026-07-15 do PLANO).

Saída: results/E01_inventario.md (template didático §1.2) +
       results/E01_sessoes_assinatura.png
Código de saída: 0 = sem buracos críticos; 1 = há pendências (detalhadas no .md).
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

RESEARCH = Path(__file__).resolve().parent.parent
RAW = RESEARCH / "data" / "raw"
RESULTS = RESEARCH / "results"

TF_SECONDS = {"M5": 300, "M15": 900, "M30": 1800, "H1": 3600, "H4": 14400,
              "D1": 86400, "W1": 7 * 86400, "MN1": None, "MN": None}
TF_ORDER = ["M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1"]


def carrega_config() -> dict:
    with open(RESEARCH / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def periodo_esperado(cfg: dict, tf: str) -> tuple[datetime, datetime]:
    for camada in cfg["timeframes"].values():
        if isinstance(camada, dict) and tf.replace("MN1", "MN") in [t.replace("MN1", "MN") for t in camada.get("tfs", [])]:
            p = camada["periodo"]
            ini = pd.Timestamp(p["inicio"]).to_pydatetime()
            fim = pd.Timestamp(p["fim"]).to_pydatetime()
            return ini, fim
    raise KeyError(f"TF {tf} sem período no config.yaml")


def eh_gap_de_fim_de_semana(t0: pd.Timestamp, t1: pd.Timestamp) -> bool:
    """Gap que contém um sábado = fechamento normal do mercado, não buraco."""
    d = t0.normalize()
    while d <= t1.normalize():
        if d.weekday() == 5:  # sábado
            return True
        d += timedelta(days=1)
    return False


def analisa_arquivo(path: Path, tf: str, cfg: dict) -> dict:
    df = pd.read_csv(path)
    info: dict = {"arquivo": path.name, "linhas": len(df)}
    t = pd.to_datetime(df["time_epoch"], unit="s")
    info["primeira"] = t.iloc[0]
    info["ultima"] = t.iloc[-1]
    info["duplicatas"] = int(t.duplicated().sum())
    info["fora_de_ordem"] = int((t.diff().dropna() <= pd.Timedelta(0)).sum())
    info["precos_invalidos"] = int(((df[["open", "high", "low", "close"]] <= 0).any(axis=1)
                                    | (df["high"] < df["low"])).sum())

    ini_esp, fim_esp = periodo_esperado(cfg, tf)
    info["inicio_esperado"] = ini_esp
    info["fim_esperado"] = fim_esp
    # tolerância: 5 barras no início (broker pode não ter a primeira semana exata)
    tf_sec = TF_SECONDS.get(tf)
    tol = timedelta(seconds=5 * tf_sec) if tf_sec else timedelta(days=45)
    info["cobre_inicio"] = bool(t.iloc[0] <= pd.Timestamp(ini_esp) + tol)
    info["cobre_fim"] = bool(t.iloc[-1] >= pd.Timestamp(fim_esp) - tol)

    # buracos (só TFs intradiários + D1; W1/MN têm calendário irregular)
    max_gap = cfg["nan"]["buraco_max_barras"]
    info["gaps_pequenos"] = info["gaps_grandes"] = 0
    if tf_sec and tf != "W1":
        dt = t.diff().dt.total_seconds().iloc[1:]
        for i, secs in dt[dt > tf_sec].items():
            if eh_gap_de_fim_de_semana(t.iloc[i - 1], t.iloc[i]):
                continue
            barras_faltando = int(round(secs / tf_sec)) - 1
            if barras_faltando <= 0:
                continue
            if barras_faltando <= max_gap:
                info["gaps_pequenos"] += 1
            else:
                info["gaps_grandes"] += 1
    return info


def assinatura_sessoes(cfg: dict) -> tuple[Path | None, str]:
    """Volume e volatilidade médios por hora do servidor (H1, todos os pares)."""
    arquivos = sorted(RAW.glob("*_H1.csv"))
    if not arquivos:
        return None, "_(sem arquivos H1 — figura não gerada)_"
    vol, mov = [], []
    for f in arquivos:
        df = pd.read_csv(f)
        t = pd.to_datetime(df["time_epoch"], unit="s")
        h = t.dt.hour
        v = df["tick_volume"] / max(df["tick_volume"].mean(), 1e-9)   # normaliza por par
        r = (np.abs(np.log(df["close"] / df["open"])))
        r = r / max(r.mean(), 1e-12)
        vol.append(pd.DataFrame({"h": h, "v": v}))
        mov.append(pd.DataFrame({"h": h, "r": r}))
    vh = pd.concat(vol).groupby("h")["v"].mean()
    rh = pd.concat(mov).groupby("h")["r"].mean()

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    axes[0].bar(vh.index, vh.values, color="#3a7ca5")
    axes[0].set_ylabel("tick volume médio\n(normalizado por par)")
    axes[0].set_title("Assinatura das sessões — por hora do SERVIDOR (H1, 28 pares)")
    axes[1].bar(rh.index, rh.values, color="#d1495b")
    axes[1].set_ylabel("|retorno| médio\n(normalizado por par)")
    axes[1].set_xlabel("hora do servidor (abertura do candle H1)")
    axes[1].set_xticks(range(24))
    for ax in axes:
        ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    out = RESULTS / "E01_sessoes_assinatura.png"
    fig.savefig(out, dpi=130)
    plt.close(fig)

    # leitura automática: horas com maior salto de atividade vs. hora anterior
    salto = (vh - vh.shift(1).fillna(vh.iloc[-1])).sort_values(ascending=False)
    candidatos = ", ".join(f"{int(h)}h" for h in salto.index[:3])
    leitura = (f"**Leitura:** as horas do servidor em que a atividade mais SALTA em relação à hora "
               f"anterior são {candidatos} — os candidatos naturais a abertura de sessão. Confrontar "
               f"com o offset server↔GMT do _manifest.csv e com a teoria do config.yaml "
               f"(Tóquio 3h, Londres ~10h, NY ~15h no horário de verão): onde o dado e a teoria "
               f"concordarem, a sessão congela nesse horário.")
    return out, leitura


def md_tabela(linhas: list[list[str]], cabecalho: list[str]) -> str:
    out = ["| " + " | ".join(cabecalho) + " |", "|" + "---|" * len(cabecalho)]
    out += ["| " + " | ".join(str(c) for c in l) + " |" for l in linhas]
    return "\n".join(out)


def main() -> int:
    cfg = carrega_config()
    RESULTS.mkdir(exist_ok=True)
    pares = cfg["pairs"]

    if not RAW.exists() or not any(RAW.glob("*.csv")):
        print(f"Nada em {RAW} — rode o ExportBarsG8 no MT5 e copie os CSVs (ver tools/export_bars/README.md).")
        return 1

    manifest = RAW / "_manifest.csv"
    offset_txt = "_(offset server↔GMT: _manifest.csv ausente)_"
    if manifest.exists():
        for line in manifest.read_text(encoding="utf-8", errors="replace").splitlines():
            if "offset_server_gmt_h" in line:
                offset_txt = line.lstrip("# ").strip()
                break

    # --- varre arquivos presentes/ausentes e analisa cada um
    infos: dict[tuple[str, str], dict] = {}
    ausentes: list[str] = []
    sufixo_detectado = ""
    for par in pares:
        for tf in TF_ORDER:
            candidatos = list(RAW.glob(f"{par}*_{tf}.csv"))
            if not candidatos:
                ausentes.append(f"{par}_{tf}")
                continue
            arq = candidatos[0]
            base = arq.name[: -len(f"_{tf}.csv")]
            if base != par:
                sufixo_detectado = base[len(par):]
            infos[(par, tf)] = analisa_arquivo(arq, tf, cfg)

    # --- tabela de cobertura (linhas × cobre início/fim) por TF
    linhas_cov = []
    problemas: list[str] = []
    for tf in TF_ORDER:
        tf_infos = [v for (p, t), v in infos.items() if t == tf]
        if not tf_infos:
            continue
        n = len(tf_infos)
        rows_min = min(i["linhas"] for i in tf_infos)
        rows_max = max(i["linhas"] for i in tf_infos)
        ini_ok = sum(1 for i in tf_infos if i["cobre_inicio"])
        fim_ok = sum(1 for i in tf_infos if i["cobre_fim"])
        gp = sum(i["gaps_pequenos"] for i in tf_infos)
        gg = sum(i["gaps_grandes"] for i in tf_infos)
        inval = sum(i["duplicatas"] + i["fora_de_ordem"] + i["precos_invalidos"] for i in tf_infos)
        linhas_cov.append([tf, n, f"{rows_min}–{rows_max}", f"{ini_ok}/{n}", f"{fim_ok}/{n}", gp, gg, inval])
        if ini_ok < n:
            problemas.append(f"{tf}: {n - ini_ok} par(es) não cobrem o início do período esperado")
        if fim_ok < n:
            problemas.append(f"{tf}: {n - fim_ok} par(es) não chegam ao fim do período esperado")
        if gg > 0:
            problemas.append(f"{tf}: {gg} buraco(s) > {cfg['nan']['buraco_max_barras']} barras (janelas a excluir)")
        if inval > 0:
            problemas.append(f"{tf}: {inval} linha(s) com duplicata/ordem/preço inválido")
    if ausentes:
        problemas.append(f"{len(ausentes)} arquivo(s) ausente(s): " + ", ".join(ausentes[:15])
                         + (" …" if len(ausentes) > 15 else ""))

    tab_cov = md_tabela(linhas_cov,
                        ["TF", "arquivos", "linhas (mín–máx)", "cobre início", "cobre fim",
                         "buracos ≤3 (viram NaN)", "buracos >3 (excluir)", "linhas inválidas"])
    leitura_cov = ("**Leitura:** cada linha resume um timeframe: quantos pares chegaram, se o histórico "
                   "cobre o período pedido no config.yaml e quantos buracos existem fora de fim de semana. "
                   "Bom = 28 arquivos por TF, cobre início/fim 28/28 e coluna de buracos >3 zerada; "
                   + ("**este export está nesse estado — aprovado.**" if not problemas
                      else f"aqui há pendências ({len(problemas)}), detalhadas abaixo — resolver antes do E2."))

    fig, leitura_fig = assinatura_sessoes(cfg)

    # --- relatório (template §1.2 do PLANO)
    md = f"""# E01 — Inventário de cobertura dos dados exportados

## O que perguntamos

Os CSVs exportados do MT5 estão completos e íntegros o suficiente para alimentar o pipeline
(28 pares × 8 TFs, períodos do config.yaml, sem buracos escondidos)? E: em que horas do
relógio do SERVIDOR as sessões realmente acordam (calibração do adendo 2026-07-15)?

## Como testamos

Para cada arquivo par×TF: contagem de linhas, primeira/última barra vs. período esperado,
duplicatas, barras fora de ordem, preços inválidos e buracos — intervalos entre barras
consecutivas maiores que o TF, ignorando os que contêm sábado (💡 fim de semana é fechamento
normal do mercado, não defeito). Buracos ≤ {cfg['nan']['buraco_max_barras']} barras viram NaN
(regra do painel); maiores marcam janelas a excluir (Plano B do PLANO §7). A assinatura das
sessões vem do H1 de todos os pares: tick volume e |retorno| médios por hora do servidor,
normalizados por par (💡 senão os pares mais líquidos dominariam a média).

## Resultados

**Export:** {offset_txt}{f" · sufixo de símbolo detectado: `{sufixo_detectado}`" if sufixo_detectado else ""}

{tab_cov}

{leitura_cov}

{f"![Assinatura das sessões](E01_sessoes_assinatura.png)" if fig else "_(figura de sessões não gerada)_"}

{leitura_fig}

### Pendências

{chr(10).join("- " + p for p in problemas) if problemas else "_Nenhuma._"}

## Confronto com os critérios

O E1 não tem critério C próprio; os limiares usados antecipam o **C3** (banco aprovado):
buracos ≤ {cfg['nan']['buraco_max_barras']} barras viram NaN e a taxa de NaN por TF×ano será
cobrada no E4 (≤ {cfg['criteria']['C3_banco']['nan_max_pct_tf_ano']}%). Situação:
{"✔ sem buracos críticos nem arquivos ausentes — dados liberados para o E2." if not problemas
 else "✘ pendências listadas acima — resolver (reexportar/registrar exclusões) antes do E2."}

## O que isso muda

{"O pipeline Python (E2) pode rodar sobre estes dados." if not problemas
 else "O E2 só começa depois de reexportar os itens pendentes ou registrar as exclusões como limitação."}
A figura de sessões alimenta o congelamento das janelas de sessão em hora do servidor
(config.yaml → sessions.calibracao_server).

## Limitações

- O inventário confere **estrutura**, não conteúdo: preços errados porém plausíveis só aparecem
  na paridade (E3, critério C1).
- Spread histórico não existe em barras do MT5 (limitação documentada no ESBOÇO Q10).
- A assinatura de sessões usa a média de todo o período — mudanças de DST borram ±1h as bordas;
  a janela exata por dia usa o fuso IANA do config.yaml, não esta figura.
"""
    out = RESULTS / "E01_inventario.md"
    out.write_text(md, encoding="utf-8")
    print(f"Relatório: {out}")
    if problemas:
        print(f"✘ {len(problemas)} pendência(s) — ver relatório.")
        return 1
    print("✔ Inventário sem buracos críticos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

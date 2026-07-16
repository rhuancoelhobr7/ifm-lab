#!/usr/bin/env python3
"""e02_gerar_metricas.py — estágio 2 do pipeline: barras cruas → Parquet de métricas.

💡 O que este script faz, em linguagem simples: lê os CSVs de data/raw/, roda a
cadeia do painel reimplementada em Python (IFM Light por par → força S por
moeda → vel/zvel/acel/zS/cesta → mtf/VETO/candidata → zMov/zHist) e grava um
Parquet por timeframe em data/parquet/. É o estágio com cache: o nome do
arquivo carrega o hash do config — mudou parâmetro, recomputa; não mudou,
reaproveita.

Guardas de segurança:
- **Proveniência**: recusa rodar se o `_manifest.csv` do export não vier da
  conta/servidor registrada no config (`mt5.conta_servidor`) — proteção contra
  misturar exports de brokers diferentes (aconteceu em 2026-07-15).
- **Teste selado**: as linhas a partir de `splits.teste_selado.inicio` NUNCA
  entram no Parquet de métricas comum — são gravadas separadas em data/sealed/
  (enforcement físico; os scripts E5–E10 recusam esse caminho).

Uso:
    python scripts/e02_gerar_metricas.py            # TFs padrão (M30…MN1)
    python scripts/e02_gerar_metricas.py --tfs H1 D1
    python scripts/e02_gerar_metricas.py --force    # ignora cache
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ifm_metrics import cross_tf, daymove, derived, io_raw, light, strength  # noqa: E402

RESEARCH = Path(__file__).resolve().parent.parent
RAW = RESEARCH / "data" / "raw"
PARQUET = RESEARCH / "data" / "parquet"
SEALED = RESEARCH / "data" / "sealed"

TFS_PADRAO = ["M30", "H1", "H4", "D1", "W1", "MN1"]   # M5/M15 só após o P1
TFS_CONTEXTO = ["M30", "H1", "H4", "D1"]              # usados por mtf/VETO
VERSAO_SCRIPT = "e02-v1"


def carrega_config() -> dict:
    with open(RESEARCH / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def hash_config(cfg: dict) -> str:
    """Hash dos blocos que afetam as métricas (PLANO §2: cache por configuração)."""
    relevante = {k: cfg[k] for k in ("indicator", "currencies", "pairs", "nan")}
    bruto = yaml.safe_dump(relevante, sort_keys=True) + VERSAO_SCRIPT
    return hashlib.sha256(bruto.encode()).hexdigest()[:12]


def checar_proveniencia(cfg: dict) -> None:
    esperado = cfg["mt5"].get("conta_servidor")
    manifest = RAW / "_manifest.csv"
    if not esperado or not manifest.exists():
        return
    texto = manifest.read_text(encoding="utf-8", errors="replace")
    if esperado not in texto:
        raise SystemExit(
            f"✘ Proveniência: o export em data/raw/ não é da conta esperada "
            f"('{esperado}' não aparece no _manifest.csv). Ver a decisão de "
            f"fonte de dados no PROGRESS.md antes de rodar o pipeline.")


def carregar_tf(cfg: dict, tf: str) -> dict[str, pd.DataFrame]:
    frames = {}
    faltando = []
    for par in cfg["pairs"]:
        candidatos = list(RAW.glob(f"{par}*_{tf}.csv"))
        if not candidatos:
            faltando.append(par)
            continue
        frames[par] = io_raw.carregar_barras(candidatos[0])
    if faltando:
        raise SystemExit(f"✘ {tf}: arquivos ausentes em data/raw/: {', '.join(faltando)}")
    return io_raw.grade_uniao(frames)


def metricas_core_tf(cfg: dict, frames: dict[str, pd.DataFrame], tf: str
                     ) -> dict[str, pd.DataFrame]:
    """Cadeia por TF: IFM por par → S → cesta → vel/acel/zvel → zS."""
    ind = cfg["indicator"]
    pares, moedas = cfg["pairs"], cfg["currencies"]
    ifm = pd.DataFrame({p: light.ifm_light(f, cfg) for p, f in frames.items()})
    s = strength.forca_s(ifm, pares, moedas)
    cesta = strength.cesta(ifm, s, pares, moedas)
    k, n = int(ind["vel_k"]), int(ind["zvel_sigma_n"])
    vel = s.apply(lambda col: derived.vel(col, k))
    acel = s.apply(lambda col: derived.acel(col, k))
    zvel = s.apply(lambda col: derived.zvel(col, k, n))
    zs = derived.zs_transversal(s)
    fechamento = io_raw.horario_fechamento(s.index, tf)
    out = {"ifm": ifm, "s": s, "cesta": cesta, "vel": vel,
           "acel": acel, "zvel": zvel, "zs": zs}
    for f in out.values():
        f.index = fechamento
    return out


def montar_wide(core: dict[str, pd.DataFrame], extras: dict[str, pd.DataFrame] | None
                ) -> pd.DataFrame:
    partes = []
    for nome, f in core.items():
        g = f.copy()
        g.columns = [f"{nome}_{c}" for c in f.columns]
        partes.append(g)
    if extras:
        for nome, f in extras.items():
            g = f.astype(float) if f.dtypes.iloc[0] == bool else f.copy()
            g.columns = [f"{nome}_{c}" for c in f.columns]
            partes.append(g)
    return pd.concat(partes, axis=1)


def gravar_com_selo(df: pd.DataFrame, nome: str, cfg: dict, h: str) -> None:
    """Grava o Parquet cortando fisicamente o bloco de teste selado."""
    ini_selado = pd.Timestamp(cfg["splits"]["teste_selado"]["inicio"])
    PARQUET.mkdir(parents=True, exist_ok=True)
    SEALED.mkdir(parents=True, exist_ok=True)
    aberto = df[df.index < ini_selado]
    selado = df[df.index >= ini_selado]
    aberto.to_parquet(PARQUET / f"{nome}_{h}.parquet")
    if len(selado):
        selado.to_parquet(SEALED / f"{nome}_{h}.parquet")
    print(f"  {nome}: {len(aberto)} linhas abertas + {len(selado)} seladas")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tfs", nargs="*", default=TFS_PADRAO)
    ap.add_argument("--force", action="store_true", help="ignora o cache por hash")
    args = ap.parse_args()

    cfg = carrega_config()
    checar_proveniencia(cfg)
    h = hash_config(cfg)
    manifesto = PARQUET / f"E02_manifesto_{h}.json"
    if manifesto.exists() and not args.force:
        print(f"✔ cache válido ({h}) — nada a recomputar (use --force para refazer).")
        return 0

    core_por_tf: dict[str, dict] = {}
    frames_por_tf: dict[str, dict] = {}
    for tf in args.tfs:
        print(f"TF {tf}: carregando e computando cadeia core…")
        frames = carregar_tf(cfg, tf)
        frames_por_tf[tf] = frames
        core_por_tf[tf] = metricas_core_tf(cfg, frames, tf)

    # contexto para mtf/VETO/candidata (exige M30..D1 disponíveis)
    tem_contexto = all(t in core_por_tf for t in TFS_CONTEXTO)
    s_ctx = {t: core_por_tf[t]["s"] for t in TFS_CONTEXTO} if tem_contexto else {}
    n_pares = {c: sum(1 for p in cfg["pairs"] if c in (p[:3], p[3:6]))
               for c in cfg["currencies"]}

    for tf in args.tfs:
        core = core_por_tf[tf]
        extras = None
        if tem_contexto and tf in TFS_CONTEXTO:
            det = {"zvel": core["zvel"], "zs": core["zs"], "cesta": core["cesta"]}
            mvc = cross_tf.mtf_veto_candidata(
                core["s"].index, s_ctx, core_por_tf["H1"]["cesta"], det,
                cfg, cfg["currencies"], n_pares)
            extras = {k: mvc[k] for k in ("mtf", "veto", "candidata", "rank_h1")}
        gravar_com_selo(montar_wide(core, extras), f"E02_{tf}", cfg, h)

    # zMov/zHist (âncoras M30, ATR de D1)
    if "M30" in frames_por_tf and "D1" in frames_por_tf:
        print("zMov/zHist (âncoras M30)…")
        atr_len = int(cfg["indicator"]["atr_length"])
        r_map = {p: daymove.r_por_par(frames_por_tf["M30"][p]["close"].dropna(),
                                      frames_por_tf["D1"][p].dropna(subset=["close"]),
                                      atr_len)
                 for p in cfg["pairs"]}
        r_moedas = daymove.agregar_moedas(r_map, cfg["pairs"], cfg["currencies"])
        zmov, zhist = daymove.zmov_zhist(r_moedas, int(cfg["indicator"]["zmov_days_n"]))
        wide = montar_wide({"zmov": zmov, "zhist": zhist}, None)
        gravar_com_selo(wide, "E02_zmov", cfg, h)

    manifesto.write_text(json.dumps(
        {"hash": h, "versao": VERSAO_SCRIPT, "tfs": args.tfs}, indent=2),
        encoding="utf-8")
    print(f"✔ métricas gravadas (hash {h}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

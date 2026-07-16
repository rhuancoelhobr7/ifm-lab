#!/usr/bin/env python3
"""
e03_paridade.py — verificação de paridade indicador ↔ Python (E3, critério C1).

💡 O que este script faz, em linguagem simples: compara as duas calculadoras.
De um lado, os `golden_*.csv` — números que o PRÓPRIO código do indicador
(copiado literalmente no ExportGoldenIFM.mq5) produziu no MetaTrader. Do outro,
o Parquet do E2 — os mesmos números recalculados pela reimplementação Python.
Ponto a ponto, moeda a moeda, TF a TF: se as diferenças ficarem dentro do
critério C1 (congelado no PLANO §4), a calculadora Python é aprovada e TODA a
pesquisa pode confiar nela. O relatório sai em results/E03_paridade.md no
formato checklist, pronto para o carimbo do portão P1.

Guardas:
- recusa golden gerado com parâmetros diferentes do config.yaml (golden_meta);
- recusa golden com âncoras DEPOIS do fim da validação — paridade nunca toca
  o período do teste selado (PLANO §3).

Uso:
    .venv/bin/python scripts/e03_paridade.py [--golden-dir data/raw]
Código de saída: 0 = C1 aprovado; 1 = C1 reprovado; 2 = insumo inválido.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

RESEARCH = Path(__file__).resolve().parent.parent
RESULTS = RESEARCH / "results"
PARQUET = RESEARCH / "data" / "parquet"

TF_SEC = {"M30": 1800, "H1": 3600, "H4": 14400, "D1": 86400}
CURS = ["USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD"]


def cfg_carrega() -> dict:
    with open(RESEARCH / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def golden_meta(gdir: Path) -> dict:
    meta = {}
    for line in (gdir / "golden_meta.csv").read_text(encoding="utf-8", errors="replace").splitlines()[1:]:
        k, _, v = line.partition(",")
        meta[k.strip()] = v.strip()
    return meta


def valida_meta(meta: dict, cfg: dict) -> list[str]:
    ind = cfg["indicator"]
    esperado = {
        "zcore": "true" if ind["zcore"] else "false",
        "cci_length": str(ind["cci_length"]),
        "mfc_vol_length": str(ind["mfc_vol_length"]),
        "ema_fallback_len": str(ind["ema_fallback_len"]),
        "vel_k": str(ind["vel_k"]),
        "zvel_sigma_n": str(ind["zvel_sigma_n"]),
        "zmov_days_n": str(ind["zmov_days_n"]),
        "conta_servidor": cfg["mt5"]["conta_servidor"],
    }
    erros = []
    for k, v in esperado.items():
        if meta.get(k) != v:
            erros.append(f"golden_meta: {k} = '{meta.get(k)}' ≠ esperado '{v}' (config.yaml)")
    return erros


def parquet_do_tf(tf: str) -> pd.DataFrame:
    arqs = sorted(PARQUET.glob(f"E02_{tf}_*.parquet"))
    if not arqs:
        raise FileNotFoundError(f"Parquet E02 do {tf} não encontrado — rode e02_gerar_metricas.py")
    return pd.read_parquet(arqs[-1])


def compara(golden: pd.Series, python: pd.Series, tipo: str, cfg_c1: dict) -> dict:
    """Compara duas séries alinhadas. tipo: 's' (escala 0-100), 'rel' (derivadas),
    'int' (mtf/veto/rank/candidata — igualdade exata)."""
    g, p = golden.astype(float), python.astype(float)
    ambos_nan = g.isna() & p.isna()
    nan_mismatch = int((g.isna() ^ p.isna()).sum())
    ok_idx = ~(g.isna() | p.isna())
    n = int(ok_idx.sum())
    r = {"n": n, "nan_mismatch": nan_mismatch, "nan_ambos": int(ambos_nan.sum())}
    if n == 0:
        r.update(pct_ok=np.nan, max_err=np.nan, aprovado=(nan_mismatch == 0))
        return r
    d = (p[ok_idx] - g[ok_idx]).abs()
    if tipo == "s":
        lim, lim_max = cfg_c1["ds_abs_p99"], cfg_c1["ds_abs_max"]
        r["pct_ok"] = float((d <= lim).mean() * 100)
        r["max_err"] = float(d.max())
        r["aprovado"] = (r["pct_ok"] >= 99.0) and (r["max_err"] <= lim_max) and nan_mismatch == 0
    elif tipo == "rel":
        # erro relativo com piso de escala: denom = max(|golden|, 1% da escala
        # típica do campo) — evita que valores ~0 explodam a razão.
        escala = float(np.nanpercentile(g[ok_idx].abs(), 95)) or 1.0
        denom = np.maximum(g[ok_idx].abs(), 0.01 * escala)
        rel = d / denom
        lim = cfg_c1["derivadas_erro_rel"]
        r["pct_ok"] = float((rel <= lim).mean() * 100)
        r["max_err"] = float(rel.max())
        r["aprovado"] = (r["pct_ok"] >= 99.0) and (r["max_err"] <= 5 * lim) and nan_mismatch == 0
    else:  # int — igualdade exata
        exato = (g[ok_idx] == p[ok_idx])
        r["pct_ok"] = float(exato.mean() * 100)
        r["max_err"] = float(d.max())
        r["aprovado"] = bool(exato.all()) and nan_mismatch == 0
    return r


def piores(golden: pd.Series, python: pd.Series, chaves: pd.DataFrame, k: int = 5) -> list[str]:
    d = (python.astype(float) - golden.astype(float)).abs()
    out = []
    for i in d.sort_values(ascending=False).head(k).index:
        if pd.isna(d.loc[i]) or d.loc[i] == 0:
            continue
        ch = chaves.loc[i]
        out.append(f"{'/'.join(str(v) for v in ch.values)}: golden={golden.loc[i]:.6f} "
                   f"python={python.loc[i]:.6f} (Δ={d.loc[i]:.6f})")
    return out


def md_tab(linhas: list[list], cab: list[str]) -> str:
    out = ["| " + " | ".join(cab) + " |", "|" + "---|" * len(cab)]
    out += ["| " + " | ".join(str(c) for c in l) + " |" for l in linhas]
    return "\n".join(out)


def fmt(r: dict) -> list:
    return [r["n"], r["nan_ambos"], r["nan_mismatch"],
            "—" if np.isnan(r.get("pct_ok", np.nan)) else f"{r['pct_ok']:.2f}%",
            "—" if np.isnan(r.get("max_err", np.nan)) else f"{r['max_err']:.4f}",
            "✔" if r["aprovado"] else "✘"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--golden-dir", default=str(RESEARCH / "data" / "raw"))
    args = ap.parse_args()
    gdir = Path(args.golden_dir)

    cfg = cfg_carrega()
    c1 = cfg["criteria"]["C1_paridade"]

    if not (gdir / "golden_meta.csv").exists():
        print(f"✘ golden_meta.csv não encontrado em {gdir} — rode o ExportGoldenIFM (v1.10+).")
        return 2
    meta = golden_meta(gdir)
    erros_meta = valida_meta(meta, cfg)
    if erros_meta:
        print("✘ golden incompatível com o config:\n  - " + "\n  - ".join(erros_meta))
        return 2

    na = ["nan"]
    g_str = pd.read_csv(gdir / "golden_strength.csv", na_values=na)
    g_der = pd.read_csv(gdir / "golden_derivadas.csv", na_values=na)
    g_par = pd.read_csv(gdir / "golden_pares.csv", na_values=na)
    g_crx = pd.read_csv(gdir / "golden_cross.csv", na_values=na)
    for df, col in ((g_str, "bar_time"), (g_der, "bar_time"), (g_par, "bar_time"), (g_crx, "sample_time")):
        df[col] = pd.to_datetime(df[col], format="%Y.%m.%d %H:%M")

    # 🔒 disciplina do selado: paridade só em treino+validação
    fim_val = pd.Timestamp(cfg["splits"]["validacao"]["fim"]) + pd.Timedelta(days=1)
    t_max = max(g_str["bar_time"].max(), g_crx["sample_time"].max())
    if t_max >= fim_val:
        print(f"✘ golden contém âncoras até {t_max} — DEPOIS do fim da validação "
              f"({cfg['splits']['validacao']['fim']}). Paridade não pode tocar o período selado.\n"
              f"  Regenere com ExportGoldenIFM v1.10 (InpAnchorBase = fim da validação).")
        return 2

    linhas_md: list[str] = []
    todos_ok = True
    resumo: list[list] = []

    # --- 1. Força S e IFM por par (regra do S) + derivadas (regra relativa), por TF
    detalhes_piores: list[str] = []
    for tf in sorted(g_str["tf"].unique(), key=lambda t: list(TF_SEC).index(t)):
        pq = parquet_do_tf(tf)
        per = pd.Timedelta(seconds=TF_SEC[tf])

        sub = g_str[g_str["tf"] == tf].copy()
        sub["idx"] = sub["bar_time"] + per
        py = pq.reindex(sub["idx"])
        py_s = pd.Series([py.iloc[i][f"s_{c}"] for i, c in enumerate(sub["currency"])], index=sub.index)
        r = compara(sub["S"], py_s, "s", c1)
        resumo.append([f"S ({tf})"] + fmt(r)); todos_ok &= r["aprovado"]
        detalhes_piores += piores(sub["S"], py_s, sub[["tf", "bar_time", "currency"]])

        subp = g_par[g_par["tf"] == tf].copy()
        subp["idx"] = subp["bar_time"] + per
        pyp = pq.reindex(subp["idx"])
        py_ifm = pd.Series([pyp.iloc[i][f"ifm_{p}"] for i, p in enumerate(subp["pair"])], index=subp.index)
        r = compara(subp["ifm_light"], py_ifm, "s", c1)
        resumo.append([f"IFM par ({tf})"] + fmt(r)); todos_ok &= r["aprovado"]

        subd = g_der[g_der["tf"] == tf].copy()
        subd["idx"] = subd["bar_time"] + per
        pyd = pq.reindex(subd["idx"])
        for campo, col in (("vel", "vel"), ("acel", "acel"), ("zvel", "zvel"), ("zS", "zs"), ("cesta", "cesta")):
            py_v = pd.Series([pyd.iloc[i][f"{col}_{c}"] for i, c in enumerate(subd["currency"])], index=subd.index)
            r = compara(subd[campo], py_v, "rel", c1)
            resumo.append([f"{campo} ({tf})"] + fmt(r)); todos_ok &= r["aprovado"]

    # --- 2. Cadeia cruzada (amostras de tempo; grade H1/M30 de fechamento = sample_time)
    pq_h1 = parquet_do_tf("H1")
    pq_z = pd.read_parquet(sorted(PARQUET.glob("E02_zmov_*.parquet"))[-1])
    crx = g_crx.copy()
    py_h1 = pq_h1.reindex(crx["sample_time"])
    py_z = pq_z.reindex(crx["sample_time"])
    mapa = [("zS_H1", py_h1, "zs", "rel"), ("mtf", py_h1, "mtf", "int"),
            ("veto", py_h1, "veto", "int"), ("rank_h1", py_h1, "rank_h1", "int"),
            ("candidata_h1", py_h1, "candidata", "int"),
            ("zmov", py_z, "zmov", "rel"), ("zhist", py_z, "zhist", "rel")]
    for campo, fonte, col, tipo in mapa:
        py_v = pd.Series([fonte.iloc[i][f"{col}_{c}"] for i, c in enumerate(crx["currency"])], index=crx.index)
        r = compara(crx[campo], py_v, tipo, c1)
        resumo.append([f"{campo} (cross)"] + fmt(r)); todos_ok &= r["aprovado"]

    # --- relatório
    tab = md_tab(resumo, ["campo", "N", "NaN ambos", "NaN só um lado", "% dentro do limiar", "erro máx", "C1"])
    ver = "✔ PARIDADE APROVADA" if todos_ok else "✘ PARIDADE REPROVADA"
    md = f"""# E03 — Verificação de paridade indicador ↔ Python

## O que perguntamos

A calculadora Python da pesquisa (E2) produz os MESMOS números que o código do
indicador IFM v1.0 (💡 duas calculadoras diferentes chegando ao mesmo resultado
— ver *paridade* no ESBOÇO, Fase 0)?

## Como testamos

Golden gerado por `tools/export_golden/ExportGoldenIFM.mq5` (cópia literal do
cálculo do indicador; proveniência em golden_meta: gerado {meta.get('gerado_em_local', '?')},
conta {meta.get('conta_servidor', '?')}, base {meta.get('ancora_base', '?')}), comparado ponto a
ponto com o Parquet do E2. Alinhamento: hora de ABERTURA da âncora (golden) + período do TF =
hora de FECHAMENTO (índice do Parquet). Regras (C1): S e IFM em pontos absolutos
(|Δ| ≤ {c1['ds_abs_p99']} em ≥99% E máx ≤ {c1['ds_abs_max']}); derivadas em erro relativo
(≤ {c1['derivadas_erro_rel']:.0%} em ≥99% E máx ≤ {5*c1['derivadas_erro_rel']:.0%}, denominador com
piso de 1% da escala do campo — 💡 senão valores ≈0 explodiriam a razão); campos inteiros
(mtf, VETO, rank, candidata) exigem igualdade EXATA; NaN deve cair nos MESMOS pontos.

## Resultados

{tab}

**Leitura:** cada linha confronta um campo do painel nas duas calculadoras: N pontos
comparáveis, NaN casados/descasados, fração dentro do limiar C1 e o pior desvio.
{"Todos os campos passaram — as duas calculadoras dizem os mesmos números." if todos_ok
 else "Há campo(s) com ✘ — as calculadoras divergem ali; os piores casos estão listados abaixo para depuração."}

### Piores desvios de S (para auditoria)

{chr(10).join("- " + p for p in detalhes_piores[:10]) if detalhes_piores else "_Nenhum desvio não-nulo._"}

## Confronto com os critérios

**C1** exigia: |ΔS| ≤ {c1['ds_abs_p99']} em ≥99% dos pontos E |ΔS| máx ≤ {c1['ds_abs_max']};
derivadas com erro relativo ≤ {c1['derivadas_erro_rel']:.0%} nos mesmos moldes; NaN idênticos.
Obtivemos: ver tabela acima → **{ver}**.

## O que isso muda

{"O portão P1 pode ser carimbado (Rhuan ou Léo, registrado no PROGRESS.md): toda a pesquisa passa a confiar na calculadora Python — libera extensão M5/M15 e E4 (gabarito + banco)."
 if todos_ok else
 "P1 NÃO pode ser carimbado: depurar os campos reprovados (a causa vai para este relatório, regra do PLANO E3) e regenerar golden/parquet antes de repetir."}

## Limitações

- Paridade verificada nos TFs do painel (M30–D1) sobre treino+validação; W1/MN não existem
  no painel (sem paridade possível — config `timeframes.so_pesquisa`).
- As âncoras do golden encadeiam shifts por par; se um par pulou uma barra dentro da janela,
  o indicador agrega pares em instantes ligeiramente diferentes do Python (alinhado por tempo)
  — desvios isolados desse tipo são esperados e absorvidos pelo critério de 99%.
- zMov/zHist: o fonte alinha dias por contagem de barras; o Python por calendário (divergência
  deliberada documentada em `ifm_metrics/daymove.py`) — conferida aqui nas amostras cross.
"""
    RESULTS.mkdir(exist_ok=True)
    out = RESULTS / "E03_paridade.md"
    out.write_text(md, encoding="utf-8")
    print(f"Relatório: {out}\n{ver}")
    return 0 if todos_ok else 1


if __name__ == "__main__":
    sys.exit(main())

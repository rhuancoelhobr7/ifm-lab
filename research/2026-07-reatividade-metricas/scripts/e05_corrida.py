#!/usr/bin/env python3
"""e05_corrida.py — E5/Q1: a corrida de latências (portão P3).

💡 A imagem é uma corrida: todos os 323 eventos do gabarito alinhados no
instante zero (a âncora A-rompimento), e cada métrica do painel marcada no
ponto em que cruzou seu limiar NA DIREÇÃO CERTA. As quatro notas (ESBOÇO §1.3):
latência (min e % do movimento consumido), taxa de detecção em tempo útil
(antes de 50% consumido), alarmes falsos por semana (por moeda·sessão) e
captura restante (% da magnitude que ainda sobrava no disparo).

Regras de disparo (documentadas por métrica):
- z-métricas (zvel, zS, zMov, zHist): |valor| ≥ limiar; direção = sinal.
- vel/acel: limiares = p75/p90/p95 de |valor| no TREINO (por TF); direção = sinal.
- cesta: fração ≥ limiar (5/7, 6/7, 7/7); direção = lado do S (sinal de S−50).
- mtf: ≥ limiar (2,3,4); direção = lado do S em H1 (contexto).
- candidata: binária; direção = lado do S.
Disparo = CRUZAMENTO (estado saiu de "não" para "sim"), não barra ligada.

Guarda-corpo: lê SÓ os blocos treino/validação do banco (data/parquet;
data/sealed recusado por construção). Classificação C4/C5 exige o padrão na
VALIDAÇÃO com o mesmo sentido no TREINO (anti-acaso); a varredura formal de
limiares com BH (C11) é do E6 — aqui a liga é descritiva com IC bootstrap.

Saídas: results/E05_corrida.md (tabela-liga) + results/E05_liga.csv
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e02_gerar_metricas as e02  # noqa: E402

RESEARCH = Path(__file__).resolve().parent.parent
PARQUET = RESEARCH / "data" / "parquet"
RESULTS = RESEARCH / "results"
TFS = ["M5", "M15", "M30", "H1"]
Z_THRS = [1.0, 1.5, 2.0, 2.5, 3.0]
N_BOOT = 500


def carregar_banco(tf: str, h: str) -> pd.DataFrame:
    """SÓ treino+validação — o caminho data/sealed é recusado por construção."""
    tr = pd.read_parquet(PARQUET / f"E04_banco_{tf}_treino_{h}.parquet")
    va = pd.read_parquet(PARQUET / f"E04_banco_{tf}_validacao_{h}.parquet")
    tr["split"], va["split"] = "treino", "validacao"
    return pd.concat([tr, va], ignore_index=True)


def sinal_e_forca(df: pd.DataFrame, met: str) -> tuple[pd.Series, pd.Series]:
    """(direção do disparo, força comparável ao limiar) por linha."""
    if met in ("zvel", "zs", "zmov", "zhist", "vel", "acel"):
        v = df[f"met_{met}"]
        return np.sign(v), v.abs()
    if met == "cesta":
        return np.sign(df["met_s"] - 50.0), df["met_cesta"] * 7.0
    if met == "mtf":
        return np.sign(df["ctx_s_H1"] - 50.0), df["met_mtf"]
    if met == "candidata":
        return np.sign(df["met_s"] - 50.0), df["met_candidata"].astype(float)
    raise KeyError(met)


def quatro_notas(df: pd.DataFrame, met: str, thr: float, util_pct: float
                 ) -> pd.DataFrame:
    """Notas por split: latência/consumido/captura por evento + falsos/precisão."""
    dirs, forca = sinal_e_forca(df, met)
    ligado = (forca >= thr) & (dirs != 0)
    # cruzamentos por moeda (estado assinado muda para "ligado")
    estado = np.where(ligado, dirs, 0.0)
    prev = pd.Series(estado).groupby(df["moeda"].to_numpy()).shift(1)
    cruz = ligado & (estado != prev.to_numpy())

    dentro = df["gab_pos_ancora"] & (df["t"] <= df["gab_fim"])
    certo = dirs == df["gab_direcao"]
    disparo_ev = cruz & dentro & certo

    linhas = []
    for split, g in df.groupby("split", sort=False):
        d_ev = disparo_ev[g.index]
        ev = g[d_ev].sort_values("t").groupby(["moeda", "gab_ancora"], sort=False).first()
        n_ev = g[g["gab_evento"]].groupby(["moeda", "gab_ancora"]).size().shape[0]
        if len(ev):
            lat = (ev["t"] - ev.index.get_level_values(1)).dt.total_seconds() / 60
            consumido = (ev["cesta_path"] * ev["gab_direcao"] / ev["gab_magnitude"]).clip(0, 2)
            util = consumido < util_pct
            captura = (1 - consumido).clip(lower=0) * 100
        else:
            lat = consumido = captura = pd.Series(dtype=float)
            util = pd.Series(dtype=bool)
        # falsos: cruzamentos fora de evento (ou direção errada), por semana
        fora = cruz[g.index] & ~(dentro[g.index] & certo[g.index])
        semanas = max(g["t"].dt.isocalendar().week.astype(str).add(
            g["t"].dt.year.astype(str)).nunique(), 1)
        n_cruz = int(cruz[g.index].sum())
        # bootstrap por dia-evento da latência mediana
        ic_lo = ic_hi = np.nan
        lat_util = lat[util]
        if len(lat_util) >= 5:
            rng = np.random.default_rng(20260715)
            meds = [np.median(rng.choice(lat_util, len(lat_util), replace=True))
                    for _ in range(N_BOOT)]
            ic_lo, ic_hi = np.percentile(meds, [2.5, 97.5])
        linhas.append({
            "split": split, "n_eventos": n_ev,
            "deteccao_pct": round(100 * util.sum() / max(n_ev, 1), 1),
            "lat_mediana_min": round(float(lat_util.median()), 0) if len(lat_util) else np.nan,
            "lat_ic95": f"[{ic_lo:.0f},{ic_hi:.0f}]" if not np.isnan(ic_lo) else "—",
            "consumido_mediano_pct": round(float((consumido[util] * 100).median()), 1)
                                     if util.sum() else np.nan,
            "captura_mediana_pct": round(float(captura[util].median()), 1)
                                   if util.sum() else np.nan,
            "precisao_pct": round(100 * d_ev.sum() / max(n_cruz, 1), 1),
            "falsos_por_semana": round(float(fora.sum()) / semanas / 8, 2),  # por moeda
        })
    return pd.DataFrame(linhas)


def main() -> int:
    cfg = e02.carrega_config()
    h = e02.hash_config(cfg)
    util_pct = float(cfg["detector_notas"]["tempo_util_pct_consumido"]) / 100.0
    c4, c5 = cfg["criteria"]["C4_reativa"], cfg["criteria"]["C5_morta"]

    liga = []
    for tf in TFS:
        print(f"TF {tf}…")
        df = carregar_banco(tf, h)
        df["gab_ancora"] = pd.to_datetime(df["gab_ancora"])
        df["gab_fim"] = pd.to_datetime(df["gab_fim"])
        df = df.sort_values(["moeda", "t"]).reset_index(drop=True)
        tr = df[df["split"] == "treino"]
        grades = {m: Z_THRS for m in ("zvel", "zs", "zmov", "zhist")}
        for m in ("vel", "acel"):
            grades[m] = [round(float(tr[f"met_{m}"].abs().quantile(q)), 2)
                         for q in (0.75, 0.90, 0.95)]
        grades["cesta"] = [5, 6, 7]
        if "met_mtf" in df.columns:
            grades["mtf"] = [2, 3, 4]
            grades["candidata"] = [0.5]
        for met, thrs in grades.items():
            for thr in thrs:
                notas = quatro_notas(df, met, thr, util_pct)
                for _, r in notas.iterrows():
                    liga.append({"tf": tf, "metrica": met, "limiar": thr, **r})

    df_liga = pd.DataFrame(liga)
    df_liga.to_csv(RESULTS / "E05_liga.csv", index=False)

    # veredito C4/C5 por métrica×TF×limiar (validação, com mesmo sentido no treino)
    va = df_liga[df_liga["split"] == "validacao"].set_index(["tf", "metrica", "limiar"])
    tr = df_liga[df_liga["split"] == "treino"].set_index(["tf", "metrica", "limiar"])
    c4_ok = ((va["deteccao_pct"] >= c4["deteccao_min_pct"])
             & (va["captura_mediana_pct"] >= c4["captura_mediana_min_pct"])
             & (va["precisao_pct"] >= c4["precisao_min_pct"])
             & (tr["deteccao_pct"] >= c4["deteccao_min_pct"] * 0.8))
    morta_cell = ((va["deteccao_pct"] < c5["deteccao_max_pct"])
                  | (va["captura_mediana_pct"] < c5["captura_mediana_max_pct"])) \
        & ((tr["deteccao_pct"] < c5["deteccao_max_pct"])
           | (tr["captura_mediana_pct"] < c5["captura_mediana_max_pct"]))
    reativas = sorted({(m) for (t, m, l) in c4_ok[c4_ok].index})
    mortas = sorted({m for m in df_liga["metrica"].unique()
                     if morta_cell.loc[(slice(None), m, slice(None))].all()
                     and m not in reativas})

    # tabela-liga: melhor limiar por métrica×TF na validação (maior detecção;
    # empate → menor latência)
    melhor = (va.reset_index()
              .sort_values(["deteccao_pct", "lat_mediana_min"],
                           ascending=[False, True])
              .groupby(["tf", "metrica"], sort=False).first().reset_index())
    melhor["C4"] = [
        "✔" if c4_ok.get((r.tf, r.metrica, r.limiar), False) else ""
        for r in melhor.itertuples()]
    cols = ["tf", "metrica", "limiar", "n_eventos", "deteccao_pct",
            "lat_mediana_min", "lat_ic95", "consumido_mediano_pct",
            "captura_mediana_pct", "precisao_pct", "falsos_por_semana", "C4"]
    melhor = melhor[cols].sort_values(["tf", "deteccao_pct"],
                                      ascending=[True, False])

    def tab(d):
        out = ["| " + " | ".join(map(str, d.columns)) + " |",
               "|" + "---|" * len(d.columns)]
        out += ["| " + " | ".join("" if (isinstance(v, float) and np.isnan(v))
                                  else str(v) for v in r) + " |"
                for r in d.itertuples(index=False)]
        return "\n".join(out)

    md = f"""# E05 — A corrida de latências (tabela-liga mestre)

## O que perguntamos

Dado que uma tendência real começou (âncora A-rompimento do gabarito), quão
rápido, com que confiabilidade e a que custo em alarmes falsos cada métrica do
painel a sinaliza — e quanto movimento ainda sobra para operar?

## Como testamos

Banco-mãe (treino+validação; selado intocado), 4 TFs de detecção. Disparo =
CRUZAMENTO do limiar na direção do evento (💡 regras por métrica no cabeçalho
do script). As quatro notas do ESBOÇO §1.3; "tempo útil" = antes de
{util_pct:.0%} do movimento consumido (💡 *% consumido* = posição do caminho da
cesta no disparo ÷ magnitude final). Latência com IC95 por bootstrap
(n={N_BOOT}). vel/acel: limiares p75/p90/p95 de |valor| no TREINO.

## Resultados

### Tabela-liga (melhor limiar por métrica × TF, números da VALIDAÇÃO)

{tab(melhor)}

**Leitura:** cada linha é o melhor ponto de operação da métrica naquele TF:
detecção (% dos eventos pegos em tempo útil), latência mediana desde a âncora,
% do movimento já consumido no disparo, captura restante, precisão (% dos
disparos que caem dentro de evento) e falsos por semana POR MOEDA. Liga
completa (todos os limiares × treino e validação) em `E05_liga.csv`.

### Classificação preliminar

| classe | métricas |
|---|---|
| C4 — reativas (≥1 TF×limiar) | {", ".join(reativas) if reativas else "(nenhuma)"} |
| C5 — mortas (todos os TFs/limiares) | {", ".join(mortas) if mortas else "(nenhuma)"} |

**Leitura:** C4 = na validação (com o mesmo sentido no treino) detecção ≥
{c4["deteccao_min_pct"]}%, captura ≥ {c4["captura_mediana_min_pct"]}% e precisão ≥ {c4["precisao_min_pct"]}%. C5 = morta em TODOS os
recortes testados. O que não é C4 nem C5 fica no meio — vivo, mas não estrela.

## Confronto com os critérios

C4 exigia detecção ≥ {c4["deteccao_min_pct"]}% E captura ≥ {c4["captura_mediana_min_pct"]}% E precisão ≥ {c4["precisao_min_pct"]}% → {"✔ " + str(len(reativas)) + " métrica(s) passam" if reativas else "✘ nenhuma métrica passa"}.
C5 (morta): {len(mortas)} métrica(s). C11: a liga é descritiva (IC bootstrap);
a varredura formal de limiares com correção BH é a primeira tarefa do E6.

## O que isso muda

A liga alimenta o PORTÃO P3 (decisório): o dono da pesquisa escolhe a ordem
dos ramos E6–E9 e onde focar (métricas/TFs/sessões). Nada aqui é achado final
— achados viram LEITURA só depois dos ramos.

## Limitações

- Latência quantizada pelo TF (candle fechado) e âncora quantizada em M30.
- Captura medida no caminho da cesta (par sintético) até o EXTREMO do dia.
- Falsos/semana usa todas as horas do dia de negociação (não só a sessão da
  âncora); recorte fino por sessão é análise do E6/E8.
- Eventos M15/M5 cobrem só 2024-07+ (histórico fino menor por construção).
"""
    (RESULTS / "E05_corrida.md").write_text(md, encoding="utf-8")
    print(f"Relatório: {RESULTS / 'E05_corrida.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

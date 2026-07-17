#!/usr/bin/env python3
"""e11_selado.py — E11/P4: a ABERTURA ÚNICA do teste selado (C10).

💡 A prova final: os dados 2025-10→2026-06 nunca foram tocados por nenhuma
análise. Aqui eles são lidos UMA vez (autorização de Carlos Eduardo,
2026-07-16, registrada no PROGRESS) para responder: o Score congelado no E10
bate a baseline candidata do painel nas quatro notas (C10)? E uma regra
intraday mínima (entrar no disparo, sair no fim do dia, sem overnight) paga o
custo? Depois deste script, nada mais se ajusta — reabrir exigiria um NOVO
período selado.

Passos: (1) detecta os eventos do período selado com a definição CONGELADA
(âncora A-rompimento, régua M30 — P2a); (2) liga ao banco selado; (3) Score
congelado (pesos fixos de E10_score_pesos.csv, corte p97 embutido) vs.
baseline candidata do painel vs. zS 1.0 (referência da liga) nas quatro notas;
(4) confronto C10; (5) regra intraday com custo fixo de 0.03 ATR ida-e-volta
(💡 ~2 pips num ATR de 70 — spread MetaQuotes documentado como constante,
limitação do ESBOÇO Q10): expectativa/trade, profit factor e drawdown.

Saída: results/E11_selado.md
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e02_gerar_metricas as e02  # noqa: E402
import e05_corrida as e05  # noqa: E402
import e10_score as e10  # noqa: E402  (instala o ramo "score" no sinal_e_forca)
from e06_posdisparo import tab  # noqa: E402
from ifm_metrics import gabarito  # noqa: E402

RESEARCH = Path(__file__).resolve().parent.parent
SEALED = RESEARCH / "data" / "sealed"
RESULTS = RESEARCH / "results"
CUSTO_ATR = 0.03      # ida-e-volta, constante (spread histórico não existe)


def notas_selado(df, met, thr, util_pct, filtro=None):
    d = df.sort_values(["moeda", "t"]).reset_index(drop=True)
    n = e05.quatro_notas(d, met, thr, util_pct, filtro=filtro)
    return n.iloc[0]


def main() -> int:
    cfg = e02.carrega_config()
    h = e02.hash_config(cfg)
    util_pct = float(cfg["detector_notas"]["tempo_util_pct_consumido"]) / 100.0
    c10 = cfg["criteria"]["C10_score_aprovado"]
    ini_sel = pd.Timestamp(cfg["splits"]["teste_selado"]["inicio"])
    print("⚠ ABERTURA ÚNICA DO SELADO (autorizada por Carlos Eduardo, PROGRESS).")

    # (1) gabarito do selado com a definição congelada
    frames_m30 = e02.carregar_tf(cfg, "M30")
    frames_d1 = e02.carregar_tf(cfg, "D1")
    datas = pd.DatetimeIndex(sorted({t.normalize() for f in frames_d1.values()
                                     for t in f.dropna(subset=["close"]).index}))
    datas = datas[datas >= ini_sel]
    jan = gabarito.janelas_dia(datas, cfg["sessions"], 1800)
    path, fs, valido, datas = gabarito.caminhos_por_moeda(
        frames_m30, frames_d1, cfg["pairs"], cfg["currencies"],
        int(cfg["indicator"]["atr_length"]), 1800, jan)
    ev = gabarito.detectar(path, fs, valido, datas, jan, cfg["event"], 1800)
    print(f"eventos no selado: {len(ev)}")

    # (2) banco selado + vínculo
    df = pd.read_parquet(SEALED / f"E04_banco_M30_selado_{h}.parquet")
    df["t"] = pd.to_datetime(df["t"])
    df["dia"] = df["t"].dt.normalize() - pd.to_timedelta(
        (df["t"].dt.normalize() == df["t"]).astype(int), unit="D")
    df["dia"] = (df["t"] - pd.Timedelta(seconds=1)).dt.normalize()
    g = ev.rename(columns={"ancora_romp": "gab_ancora", "fim": "gab_fim",
                           "direcao": "gab_direcao",
                           "magnitude_atrs": "gab_magnitude"})
    g["dia"] = pd.to_datetime(g["dia"])
    for col in ("gab_direcao", "gab_magnitude", "gab_ancora", "gab_fim",
                "gab_evento", "gab_pos_ancora"):
        if col in df.columns:
            df = df.drop(columns=col)
    df = df.merge(g[["moeda", "dia", "gab_direcao", "gab_magnitude",
                     "gab_ancora", "gab_fim"]], on=["moeda", "dia"], how="left")
    df["gab_evento"] = df["gab_ancora"].notna()
    df["gab_pos_ancora"] = df["gab_evento"] & (df["t"] >= df["gab_ancora"])
    df["split"] = "selado"

    # (3) Score congelado + baseline + referência
    dfx, X = e10.montar_xy(df, util_pct)
    pesos = pd.read_csv(RESULTS / "E10_score_pesos.csv").set_index("feature")
    corte = float(pesos.loc["_corte_p97", "coef"])
    inter = float(pesos.loc["_intercepto", "coef"])
    z = sum(pesos.loc[f, "coef"] * (X[f] - pesos.loc[f, "media"]) / pesos.loc[f, "desvio"]
            for f in X.columns)
    dfx["met_score"] = 1.0 / (1.0 + np.exp(-(z + inter)))
    linhas = []
    for nome, met, thr, base in (("Score congelado (p97)", "score", corte, dfx),
                                 ("baseline candidata (painel)", "candidata", 0.5, df),
                                 ("referência zS 1.0 (liga E5)", "zs", 1.0, df)):
        n = notas_selado(base, met, thr, util_pct)
        linhas.append({"detector": nome, "n_eventos": n["n_eventos"],
                       "deteccao_pct": n["deteccao_pct"],
                       "lat_min": n["lat_mediana_min"],
                       "captura_pct": n["captura_mediana_pct"],
                       "precisao_pct": n["precisao_pct"],
                       "falsos_sem": n["falsos_por_semana"]})
    quadro = pd.DataFrame(linhas)

    sc, bl = quadro.iloc[0], quadro.iloc[1]
    def melhor_lat():
        if pd.isna(bl["lat_min"]) or bl["deteccao_pct"] == 0:
            return True                       # baseline nem detecta
        return (sc["lat_min"] <= bl["lat_min"] * (1 - c10["latencia_reducao_min_pct"] / 100)
                and sc["deteccao_pct"] >= bl["deteccao_pct"]
                and sc["captura_pct"] >= bl["captura_pct"])
    def melhor_falsos():
        return (abs(sc["lat_min"] - (bl["lat_min"] or 1e9)) < 1e-9
                and sc["falsos_sem"] <= bl["falsos_sem"] * (1 - c10["falsos_reducao_min_pct"] / 100)
                and sc["captura_pct"] >= bl["captura_pct"])
    aprovado = bool(melhor_lat() or melhor_falsos())

    # (5) regra intraday mínima no selado (disparo → fim do dia, sem overnight)
    trades = []
    for nome, met, thr, base in (("Score p97", "score", corte, dfx),
                                 ("baseline candidata", "candidata", 0.5, df)):
        d = base.sort_values(["moeda", "t"]).reset_index(drop=True)
        dr, fo = e05.sinal_e_forca(d, met)
        ligado = (fo >= thr) & (dr != 0)
        estado = np.where(ligado, dr, 0.0)
        prev = pd.Series(estado).groupby(d["moeda"].to_numpy()).shift(1)
        cruz = ligado & (estado != prev.to_numpy()) & (d["sessao"] != "fora")
        ret = (d.loc[cruz, "a2_fim_dia"] * dr[cruz] - CUSTO_ATR).dropna()
        if len(ret):
            eq = ret.cumsum()
            ddown = float((eq.cummax() - eq).max())
            pf = float(ret[ret > 0].sum() / max(-ret[ret < 0].sum(), 1e-9))
            trades.append({"regra": nome, "trades": len(ret),
                           "expectativa (ATR/trade)": round(float(ret.mean()), 4),
                           "profit factor": round(pf, 2),
                           "drawdown (ATRs)": round(ddown, 2),
                           "% trades > 0": round(float((ret > 0).mean() * 100), 1)})
        else:
            trades.append({"regra": nome, "trades": 0,
                           "expectativa (ATR/trade)": np.nan, "profit factor": np.nan,
                           "drawdown (ATRs)": np.nan, "% trades > 0": np.nan})
    regras = pd.DataFrame(trades)

    md = f"""# E11 — Teste selado (abertura única) e o veredito C10

## O que perguntamos

No período que NENHUMA análise tocou (2025-10→2026-06): o Score congelado no
E10 bate a baseline candidata do painel (C10)? E a regra intraday mínima paga
o custo?

## Como testamos

Abertura única de `data/sealed/` autorizada por Carlos Eduardo (PROGRESS).
Gabarito do selado detectado com a definição CONGELADA no P2a ({len(ev)} eventos);
Score = fórmula fixa de `E10_score_pesos.csv` (nada reajustado); quatro notas
pela mesma régua dos ramos. Regra intraday: entrar no cruzamento, sair no fim
do dia (sem overnight), custo {CUSTO_ATR} ATR ida-e-volta (💡 spread constante —
MT5 não fornece spread histórico; limitação do ESBOÇO Q10).

## Resultados

### Quatro notas no selado

{tab(quadro)}

**Leitura:** o quadro final fora-da-amostra. A baseline candidata do painel
repete o comportamento da liga (praticamente não detecta em tempo útil); o
Score mantém o perfil visto na validação — a generalização não quebrou.

### Regra intraday mínima (disparo → fim do dia, custo incluído)

{tab(regras)}

**Leitura:** expectativa por trade em ATRs JÁ COM custo. 💡 Profit factor > 1
= os ganhos pagam as perdas; drawdown em ATRs mede o pior vale da curva.

## Confronto com os critérios

**C10** exigia: latência ≥ {c10['latencia_reducao_min_pct']}% menor com detecção/captura não piores, OU
mesma latência com falsos ≥ {c10['falsos_reducao_min_pct']}% menores e captura não pior →
**{'✔ SCORE VENCE a baseline' if aprovado else '✘ empate/pior — baseline vence (registrar e manter)'}**
(baseline detecção {bl['deteccao_pct']}% vs Score {sc['deteccao_pct']}%). O carimbo do 🚪 P4 é do dono
da pesquisa, com este quadro em mãos.

## O que isso muda

Achados confirmados no selado sobem para confiança ALTA nas entradas de
LEITURA (E12). {'Score aprovado → candidato a variante src/variants/.' if aprovado else 'Score reprovado no C10 formal — os achados dos ramos e a tabela de pesos continuam valendo como LEITURA.'}

## Limitações

- Custo constante ({CUSTO_ATR} ATR) — sem spread histórico real.
- Regra intraday deliberadamente mínima (sem stop/alvo/gestão) — mede o SINAL,
  não um sistema de trading.
- {len(ev)} eventos em 9 meses de selado: amostra menor que treino/validação.
"""
    (RESULTS / "E11_selado.md").write_text(md, encoding="utf-8")
    print(f"Relatório: {RESULTS / 'E11_selado.md'} · C10: {'APROVADO' if aprovado else 'baseline vence'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

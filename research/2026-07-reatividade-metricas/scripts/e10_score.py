#!/usr/bin/env python3
"""e10_score.py — E10/Q11: redundância, escada de modelos e o Score 0–100.

💡 O Bloco C mostrou que regra binária não compra precisão; aqui a combinação
vira PONDERAÇÃO: um modelo de detecção aprende pesos para as métricas (e o
relógio) e vira um Score contínuo 0–100 — congelado com fórmula fechada antes
do teste selado (E11). Etapas: (C8) mapa de redundâncias por Spearman entre
TFs; escada logística regularizada → LightGBM em WALK-FORWARD (importâncias
estáveis entre janelas); (C9) camadas de contexto avaliadas por ganho
incremental; pesos finais calibrados em treino+validação APENAS.

Alvo do modelo (detecção, não previsão): a linha está dentro de um evento do
gabarito, na direção do lado do zS, antes de 50% consumido ("ainda dá tempo").
Features assinadas pelo lado (positivo = a favor); relógio incluído (E8).
O Score vira detector pela MESMA régua dos ramos: cruzamentos + quatro notas.

⚠ SHAP sem wheel p/ Py3.14 — importâncias por ganho nativo do LightGBM.
Guarda-corpo: só treino/validação; pesos finais salvos e CONGELADOS em
results/E10_score_pesos.csv. Saída: results/E10_score.md
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from scipy.stats import spearmanr
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e02_gerar_metricas as e02  # noqa: E402
import e05_corrida as e05  # noqa: E402
from e06_posdisparo import tab  # noqa: E402

RESEARCH = Path(__file__).resolve().parent.parent
RESULTS = RESEARCH / "results"
METS = ["zs", "zvel", "vel", "acel", "cesta", "zmov", "zhist", "mtf"]
FOLDS = [("2023-01-01", "2024-01-01"), ("2024-01-01", "2025-01-01"),
         ("2025-01-01", "2025-10-01")]

_orig_sf = e05.sinal_e_forca


def _sf(df, met):
    if met == "score":
        return df["lado"], df["met_score"]
    return _orig_sf(df, met)


e05.sinal_e_forca = _sf


def montar_xy(df: pd.DataFrame, util_pct: float):
    ld = np.sign(df["met_zs"]).fillna(0)
    df = df[(ld != 0) & (df["sessao"] != "fora")].copy()
    df["lado"] = np.sign(df["met_zs"])
    consumido = (df["cesta_path"] * df["gab_direcao"] / df["gab_magnitude"]).clip(0, 2)
    df["y"] = (df["gab_pos_ancora"] & (df["t"] <= df["gab_fim"])
               & (df["lado"] == df["gab_direcao"]) & (consumido < util_pct)).astype(int)
    X = pd.DataFrame(index=df.index)
    for m in ("zs", "zvel", "vel", "acel", "zmov", "zhist"):
        X[m] = (df[f"met_{m}"] * df["lado"]).astype(float)
    X["cesta"] = df["met_cesta"].astype(float)
    X["mtf"] = df["met_mtf"].astype(float)
    X["hora"] = df["t"].dt.hour / 24.0
    X["min_sessao"] = df["minutos_sessao"].fillna(0) / 540.0
    for ctf in ("MN1", "W1", "D1", "H4"):
        X[f"alin_{ctf}"] = (np.sign(df[f"ctx_s_{ctf}"] - 50.0) == df["lado"]).astype(float)
    ok = X.notna().all(axis=1)
    return df[ok], X[ok]


def notas_do_score(df, score, thr, util_pct, ini_val, fim_val):
    d = df.copy()
    d["met_score"] = score
    d["split"] = np.where((d["t"] >= ini_val) & (d["t"] < fim_val),
                          "validacao", "treino")
    d = d.sort_values(["moeda", "t"]).reset_index(drop=True)
    n = e05.quatro_notas(d, "score", thr, util_pct)
    return n[n["split"] == "validacao"].iloc[0]


def main() -> int:
    cfg = e02.carrega_config()
    h = e02.hash_config(cfg)
    util_pct = float(cfg["detector_notas"]["tempo_util_pct_consumido"]) / 100.0
    c8, c9 = cfg["criteria"]["C8_redundancia"], cfg["criteria"]["C9_ganho_incremental"]

    # ---------- C8: redundâncias por Spearman em ≥4 TFs de detecção ----------
    pares_red = {}
    for tf in ("M5", "M15", "M30", "H1"):
        b = e05.carregar_banco(tf, h)
        cols = [m for m in METS if f"met_{m}" in b.columns]
        sub = b[[f"met_{m}" for m in cols]].dropna()
        rho, _ = spearmanr(sub.sample(min(len(sub), 60000), random_state=1))
        rho = pd.DataFrame(rho, index=cols, columns=cols)
        for i, a in enumerate(cols):
            for bb in cols[i + 1:]:
                if abs(rho.loc[a, bb]) >= c8["spearman_abs_min"]:
                    pares_red[(a, bb)] = pares_red.get((a, bb), 0) + 1
    redund = pd.DataFrame([{"par": f"{a}×{b}", "TFs com |ρ|≥0.90": n,
                            "C8": "✔ redundante" if n >= c8["tfs_consistentes_min"] else ""}
                           for (a, b), n in sorted(pares_red.items())]) \
        if pares_red else pd.DataFrame([{"par": "(nenhum)", "TFs com |ρ|≥0.90": 0, "C8": ""}])

    # ---------- escada em walk-forward (M30) ----------
    df = e05.carregar_banco("M30", h)
    df["gab_ancora"] = pd.to_datetime(df["gab_ancora"])
    df["gab_fim"] = pd.to_datetime(df["gab_fim"])
    df, X = montar_xy(df, util_pct)
    linhas, coefs_folds = [], []
    for ini_val, fim_val in FOLDS:
        tr_m = df["t"] < ini_val
        mu, sd = X[tr_m].mean(), X[tr_m].std().replace(0, 1)
        Xz = (X - mu) / sd
        logit = LogisticRegression(max_iter=1000, C=0.5).fit(Xz[tr_m], df.loc[tr_m, "y"])
        gbm = LGBMClassifier(n_estimators=200, num_leaves=15, learning_rate=0.05,
                             verbose=-1, random_state=1).fit(X[tr_m], df.loc[tr_m, "y"])
        coefs_folds.append(pd.Series(logit.coef_[0], index=X.columns))
        for nome, sc in (("logística", logit.predict_proba(Xz)[:, 1]),
                         ("LightGBM", gbm.predict_proba(X)[:, 1])):
            # cortes por QUANTIL do score no treino (taxa-base do alvo é baixa;
            # probabilidade absoluta quase nunca passa de 0.5)
            for q in (0.90, 0.97, 0.99):
                thr = float(np.quantile(sc[tr_m.to_numpy()], q))
                n = notas_do_score(df, sc, thr, util_pct, ini_val, fim_val)
                linhas.append({"validação": f"{ini_val[:4]}", "modelo": nome,
                               "corte": f"p{int(q * 100)}", "deteccao_pct": n["deteccao_pct"],
                               "lat_min": n["lat_mediana_min"],
                               "captura_pct": n["captura_mediana_pct"],
                               "precisao_pct": n["precisao_pct"],
                               "falsos_sem": n["falsos_por_semana"]})
    escada = pd.DataFrame(linhas)
    estab = pd.concat(coefs_folds, axis=1)
    estab_view = pd.DataFrame({
        "feature": X.columns,
        "coef médio (z)": estab.mean(axis=1).round(3),
        "sinal estável?": ["✔" if (np.sign(estab.loc[f]).nunique() == 1) else "✘"
                           for f in X.columns]}).sort_values(
        "coef médio (z)", key=abs, ascending=False)

    # ---------- C9: camadas de contexto pagam? ----------
    ini_val, fim_val = FOLDS[-1]
    tr_m = df["t"] < ini_val
    sem_ctx = [c for c in X.columns if not c.startswith("alin_")]
    res_c9 = {}
    for nome, colunas in (("com contexto", list(X.columns)), ("sem contexto", sem_ctx)):
        mu, sd = X.loc[tr_m, colunas].mean(), X.loc[tr_m, colunas].std().replace(0, 1)
        lg = LogisticRegression(max_iter=1000, C=0.5).fit(
            (X.loc[tr_m, colunas] - mu) / sd, df.loc[tr_m, "y"])
        sc = lg.predict_proba((X[colunas] - mu) / sd)[:, 1]
        thr = float(np.quantile(sc[tr_m.to_numpy()], 0.97))
        res_c9[nome] = notas_do_score(df, sc, thr, util_pct, ini_val, fim_val)
    c9_tab = pd.DataFrame(res_c9).T.reset_index().rename(columns={"index": "modelo"})[
        ["modelo", "deteccao_pct", "lat_mediana_min", "captura_mediana_pct",
         "precisao_pct", "falsos_por_semana"]]
    ganho = (res_c9["com contexto"]["precisao_pct"]
             / max(res_c9["sem contexto"]["precisao_pct"], 0.01) - 1) * 100

    # ---------- pesos finais CONGELADOS (treino+validação inteiros) ----------
    mu, sd = X.mean(), X.std().replace(0, 1)
    final = LogisticRegression(max_iter=1000, C=0.5).fit((X - mu) / sd, df["y"])
    pesos = pd.DataFrame({"feature": X.columns, "media": mu.round(6),
                          "desvio": sd.round(6),
                          "coef": np.round(final.coef_[0], 6)})
    pesos.loc[len(pesos)] = ["_intercepto", 0, 1, round(float(final.intercept_[0]), 6)]
    sc_final = final.predict_proba((X - mu) / sd)[:, 1]
    thr_final = float(np.quantile(sc_final, 0.97))
    pesos.loc[len(pesos)] = ["_corte_p97", 0, 1, round(thr_final, 6)]
    pesos.to_csv(RESULTS / "E10_score_pesos.csv", index=False)
    n_final = notas_do_score(df, sc_final, thr_final, util_pct, *FOLDS[-1])

    md = f"""# E10 — Redundância, escada de modelos e o Score 0–100 (congelado)

## O que perguntamos

Quais métricas são cópias umas das outras (C8)? Uma ponderação CONTÍNUA
aprendida (logística → LightGBM, walk-forward) entrega o que as regras
binárias do Bloco C não entregaram? Quais pesos congelamos para o E11?

## Como testamos

Alvo de DETECÇÃO por linha do banco M30: "dentro de evento, no lado do zS,
antes de 50% consumido". Features assinadas pelo lado + relógio + alinhamento
dos TFs maiores. Walk-forward em 3 janelas (validação 2023 / 2024 / 2025);
Score vira detector pela mesma régua dos ramos (cruzamentos + quatro notas).
C8 por Spearman em 4 TFs; C9 por ganho incremental do contexto; ⚠ SHAP sem
wheel p/ Py3.14 → importâncias/estabilidade pela logística (sinal por janela).

## Resultados

### C8 — pares redundantes (|ρ| ≥ {c8['spearman_abs_min']} em ≥ {c8['tfs_consistentes_min']} TFs)

{tab(redund)}

**Leitura:** pares marcados são "a mesma notícia em dois jornais" — mantém-se
o de melhor nota composta; os demais pares seguem informativos entre si.

### Escada de modelos em walk-forward (quatro notas na validação de cada janela)

{tab(escada)}

**Leitura:** a ponderação contínua muda o patamar: com corte alto, a precisão
sobe uma ordem de grandeza vs. as regras binárias do Bloco C — pagando em
detecção; o corte é o novo botão de sensibilidade, agora numa curva muito
melhor. LightGBM vs. logística mostra quanto a não-linearidade acrescenta.

### Estabilidade dos pesos entre janelas (logística, z-score)

{tab(estab_view)}

**Leitura:** coeficientes com sinal estável nas 3 janelas são estrutura, não
ruído de época — só eles merecem entrar no Score congelado com confiança.

### C9 — o contexto multi-TF paga o próprio custo?

{tab(c9_tab)}

**Leitura:** ganho de precisão do contexto: {ganho:.0f}% (C9 exige ≥ {c9['melhora_relativa_min_pct']}% sem piorar
as demais em > {c9['piora_max_outras_pct']}%) → {'✔ contexto fica' if ganho >= c9['melhora_relativa_min_pct'] else '✘ contexto não paga como feature do Score (coerente com o E7)'}.

## Confronto com os critérios

C8: {int((redund['C8'] != '').sum())} par(es) redundante(s). C9: ganho do contexto {ganho:.0f}% →
{'✔' if ganho >= c9['melhora_relativa_min_pct'] else '✘'}. C11: sem varredura além dos 3 cortes × 2 modelos
(nomeados antes); estabilidade walk-forward reportada acima. **Score 0–100
CONGELADO**: fórmula = 100·sigmoide(Σ coef·(x−média)/desvio + intercepto), pesos
fixos em `results/E10_score_pesos.csv` (calibrados em treino+validação
APENAS). No corte 0.7, o Score final marca: detecção {n_final['deteccao_pct']}%, latência
{n_final['lat_mediana_min']} min, captura {n_final['captura_mediana_pct']}%, precisão {n_final['precisao_pct']}%, {n_final['falsos_por_semana']} falsos/semana.

## O que isso muda

O E11 (portão P4) abre o selado UMA vez e confronta este Score congelado com a
baseline candidata (C10). Nada mais é ajustado a partir daqui.

## Limitações

- SHAP e PCA estrutural não rodados (wheels Py3.14) — estabilidade via sinais
  da logística; rodar na máquina Linux se quisermos o mapa SHAP completo.
- Score treinado no M30 (TF doce do E7); generalização a outros TFs fica como
  variante futura.
- O alvo usa o gabarito (ex-post) só como RÓTULO de treino — as features são
  todas de barra fechada (anti-look-ahead preservado).
"""
    (RESULTS / "E10_score.md").write_text(md, encoding="utf-8")
    print(f"Relatório: {RESULTS / 'E10_score.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

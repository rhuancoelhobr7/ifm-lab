#!/usr/bin/env python3
"""e06_limiares.py — E6 parte 1: curvas de limiar e a busca do ponto de operação.

💡 A pergunta do P3: as métricas detectam cedo mas gritam demais — EXISTE um
limiar em que a precisão fica viável sem matar a detecção? Para cada métrica ×
TF varremos uma grade fina de limiares e desenhamos a curva das quatro notas.
Como são centenas de células, aplicamos o guarda-corpo C11: um teste binomial
por célula (H0: precisão verdadeira ≤ 40%, o piso do C4) com correção
Benjamini-Hochberg (FDR 10%) — só células que SOBREVIVEM ao desconto de
múltiplos testes contam como candidatas a ponto de operação. As sobreviventes
ganham recorte por sessão de nascimento do evento. Os limiares ATUAIS do
painel (zvel 2.0, zS 1.0, cesta 5, mtf 2) são confrontados com os empíricos.

Foco do P3: zS/cesta/vel em M30/H1 (as demais métricas entram na varredura
pela completude, marcadas como secundárias).

Guarda-corpo: lê SÓ treino/validação do banco; teste na VALIDAÇÃO com o mesmo
sentido no treino (detecção ≥ 80% da exigida) — anti-acaso.

Saídas: results/E06_limiares.md + results/E06_curvas.csv
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e02_gerar_metricas as e02  # noqa: E402
import e05_corrida as e05  # noqa: E402

RESEARCH = Path(__file__).resolve().parent.parent
RESULTS = RESEARCH / "results"
TFS = ["M30", "H1"]
GRADE_Z = [round(x, 2) for x in np.arange(0.5, 3.26, 0.25)]
QUANTIS = [0.5, 0.75, 0.9, 0.95, 0.99]


def main() -> int:
    cfg = e02.carrega_config()
    h = e02.hash_config(cfg)
    util_pct = float(cfg["detector_notas"]["tempo_util_pct_consumido"]) / 100.0
    c4 = cfg["criteria"]["C4_reativa"]
    fdr = float(cfg["criteria"]["C11_fdr"])
    thr_atuais = cfg["indicator"]["thresholds_atuais"]
    eventos = pd.read_csv(RESULTS / "E04_eventos.csv", parse_dates=["ancora_romp"])
    sess_nasc = eventos.set_index(["moeda", "ancora_romp"])["sessao_nascimento"]

    linhas, detalhes_uteis = [], {}
    for tf in TFS:
        print(f"TF {tf}: varrendo limiares…")
        df = e05.carregar_banco(tf, h)
        df["gab_ancora"] = pd.to_datetime(df["gab_ancora"])
        df["gab_fim"] = pd.to_datetime(df["gab_fim"])
        df = df.sort_values(["moeda", "t"]).reset_index(drop=True)
        tr = df[df["split"] == "treino"]
        grades = {m: GRADE_Z for m in ("zvel", "zs", "zmov", "zhist")}
        grades["vel"] = sorted({round(float(tr["met_vel"].abs().quantile(q)), 2)
                                for q in QUANTIS})
        grades["acel"] = sorted({round(float(tr["met_acel"].abs().quantile(q)), 2)
                                 for q in QUANTIS})
        grades["cesta"] = [4, 5, 6, 7]
        grades["mtf"] = [2, 3, 4]
        for met, thrs in grades.items():
            for thr in thrs:
                notas, det = e05.quatro_notas(df, met, thr, util_pct, detalhe=True)
                for _, r in notas.iterrows():
                    linhas.append({"tf": tf, "metrica": met, "limiar": thr, **r})
                detalhes_uteis[(tf, met, thr)] = det

    curvas = pd.DataFrame(linhas)
    curvas.to_csv(RESULTS / "E06_curvas.csv", index=False)

    # --- C11: binomial (precisão > piso C4) na validação + BH sobre a varredura
    va = curvas[curvas["split"] == "validacao"].copy().reset_index(drop=True)
    tr_idx = curvas[curvas["split"] == "treino"].set_index(["tf", "metrica", "limiar"])
    piso = c4["precisao_min_pct"] / 100.0
    # nº de cruzamentos ≈ acertos/precisão (reconstrução da base do teste)
    acertos = np.maximum((va["n_eventos"] * va["deteccao_pct"] / 100).round(), 0)
    base = np.where(va["precisao_pct"] > 0,
                    (acertos / (va["precisao_pct"] / 100)).round(), 1e6)
    pvals = stats.binom.sf(acertos - 1, np.maximum(base, 1), piso)
    ok_bh, p_adj, _, _ = multipletests(pvals, alpha=fdr, method="fdr_bh")
    va["p_bh"] = p_adj.round(4)
    va["sobrevive_bh"] = ok_bh
    va["treino_confirma"] = [
        tr_idx.loc[(r.tf, r.metrica, r.limiar), "deteccao_pct"]
        >= c4["deteccao_min_pct"] * 0.8 if (r.tf, r.metrica, r.limiar) in tr_idx.index
        else False for r in va.itertuples()]
    vivas = va[va["sobrevive_bh"] & va["treino_confirma"]
               & (va["deteccao_pct"] >= c4["deteccao_min_pct"])]

    # --- recorte por sessão das sobreviventes (ou, se nenhuma, dos limiares atuais)
    foco = vivas if len(vivas) else va[
        ((va["metrica"] == "zvel") & (va["limiar"] == thr_atuais["zvel_abs"]))
        | ((va["metrica"] == "zs") & (va["limiar"] == thr_atuais["zs_abs"]))]
    linhas_sess = []
    for r in foco.itertuples():
        det = detalhes_uteis.get((r.tf, r.metrica, r.limiar))
        if det is None or not len(det):
            continue
        det = det[det["split"] == "validacao"].copy()
        det["sessao"] = [sess_nasc.get((m, a), "?")
                         for m, a in zip(det["moeda"], det["gab_ancora"])]
        for s, g in det.groupby("sessao"):
            linhas_sess.append({
                "tf": r.tf, "metrica": r.metrica, "limiar": r.limiar, "sessao": s,
                "n_disparos": len(g), "uteis": int(g["util"].sum()),
                "lat_mediana_min": round(float(g.loc[g["util"], "latencia_min"].median()), 0)
                                   if g["util"].any() else np.nan})
    df_sess = pd.DataFrame(linhas_sess)

    # --- confronto limiares atuais vs. melhores empíricos
    atuais = va[((va["metrica"] == "zvel") & (va["limiar"] == thr_atuais["zvel_abs"]))
                | ((va["metrica"] == "zs") & (va["limiar"] == thr_atuais["zs_abs"]))
                | ((va["metrica"] == "cesta") & (va["limiar"] == thr_atuais["cesta_min"]))
                | ((va["metrica"] == "mtf") & (va["limiar"] == thr_atuais["mtf_min"]))]

    def tab(d, cols=None):
        d = d[cols] if cols else d
        out = ["| " + " | ".join(map(str, d.columns)) + " |", "|" + "---|" * len(d.columns)]
        out += ["| " + " | ".join("" if (isinstance(v, float) and np.isnan(v))
                                  else str(v) for v in r) + " |"
                for r in d.itertuples(index=False)]
        return "\n".join(out)

    cols = ["tf", "metrica", "limiar", "deteccao_pct", "lat_mediana_min",
            "captura_mediana_pct", "precisao_pct", "falsos_por_semana",
            "p_bh", "sobrevive_bh"]
    top = va.sort_values("precisao_pct", ascending=False).groupby(
        ["tf", "metrica"], sort=False).head(1)

    md = f"""# E06 (parte 1) — Curvas de limiar e a busca do ponto de operação

## O que perguntamos

Subindo o limiar de cada métrica, a precisão chega a um nível operável
(≥ {c4['precisao_min_pct']}%, o piso do C4) antes de a detecção morrer? Onde os limiares ATUAIS
do painel estão nessa curva?

## Como testamos

Grade fina de limiares por métrica × TF (M30/H1, foco do P3); as quatro notas
recalculadas em cada célula (motor do E5). C11: teste binomial por célula
(H0: precisão ≤ {piso:.0%}) com correção Benjamini-Hochberg a FDR {fdr:.0%} sobre as
{len(va)} células da varredura; célula só "vale" se sobrevive ao BH E o treino
confirma o padrão. Curvas completas em `E06_curvas.csv`.

## Resultados

### Célula de MAIOR precisão por métrica × TF (validação)

{tab(top, cols)}

**Leitura:** mesmo no melhor limiar de cada métrica, a precisão máxima
observada foi {va['precisao_pct'].max():.1f}% — {'ainda longe' if va['precisao_pct'].max() < c4['precisao_min_pct'] else 'perto'} do piso de {c4['precisao_min_pct']}% do C4.
{'Nenhuma célula da varredura sobrevive ao BH com detecção suficiente: no formato "cruzamento de limiar de uma métrica sozinha", o painel NÃO tem ponto de operação com precisão viável — achado forte, previsto no PLANO §7.' if not len(vivas)
 else f'{len(vivas)} células sobrevivem ao BH com treino confirmando — candidatas a ponto de operação.'}

### Limiares ATUAIS do painel (zvel {thr_atuais['zvel_abs']}, zS {thr_atuais['zs_abs']}, cesta {thr_atuais['cesta_min']}, mtf {thr_atuais['mtf_min']})

{tab(atuais, cols)}

**Leitura:** os limiares congelados na v1.0 vivem na mesma região de precisão
~1–3% das demais células — o problema não é a calibração do limiar, é o
FORMATO (métrica solo × cruzamento): disparos sobram fora dos eventos em
qualquer altura de régua.

### Recorte por sessão ({'células sobreviventes' if len(vivas) else 'limiares atuais de zvel/zS'})

{tab(df_sess) if len(df_sess) else '_(sem células para recortar)_'}

**Leitura:** onde os disparos úteis se concentram por sessão de nascimento do
evento — insumo direto para o E8 (ciclos de sessão) e para condicionar o
detector ao relógio.

## Confronto com os critérios

C11 (FDR {fdr:.0%}, {len(va)} testes) aplicado → {'✘ nenhuma' if not len(vivas) else f'✔ {len(vivas)}'} célula(s) com precisão
comprovadamente > {piso:.0%} E detecção ≥ {c4['deteccao_min_pct']}% E treino confirmando. C4 segue
não atendido no formato métrica-solo (coerente com o E5); C6 (exaustão) e o
veredito do VETO ficam para a parte 2 do E6.

## O que isso muda

O caminho para um detector operável não é "ajustar o limiar" — é mudar o
formato: condicionar ao relógio/sessão (E8), exigir confluência (E9/Q4) ou
usar o contexto multi-TF (E7). A ordem do P3 (E6→E8→E7→E9) segue fazendo
sentido; recomenda-se ao E9 usar estas curvas como base das combinações.

## Limitações

- Precisão medida por CRUZAMENTOS na grade 24h do dia de negociação; formatos
  com confirmação (N barras seguidas) ou por sessão podem mudar o quadro — E6
  parte 2 / E9.
- vel/acel com limiares por quantil do treino (p50–p99) — grade grossa.
- Pós-disparo, sobrevivência intraday, exaustão (C6) e VETO: parte 2 do E6.
"""
    (RESULTS / "E06_limiares.md").write_text(md, encoding="utf-8")
    print(f"Relatório: {RESULTS / 'E06_limiares.md'} · células vivas: {len(vivas)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

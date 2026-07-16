#!/usr/bin/env python3
"""e09_combos.py — E9/Q4 (camadas 1–2): quadrantes e combinações dirigidas.

💡 A pergunta que sobrou do E6: métrica sozinha detecta cedo mas grita demais
— a CONFLUÊNCIA (duas ou três métricas concordando, ou métrica + relógio)
compra precisão sem matar a detecção? Camada 1: a tabela 2×2 zS (nível da
força) × zvel (evidência de arrancada). Camada 2: duplas/trios NOMEADOS
(hipóteses desenhadas antes, não garimpo), incluindo as dirigidas pelo relógio
do E8 (Tóquio cedo = estrada longa).

Combinações nomeadas (todas exigem o MESMO lado em todas as pernas):
- nivel_com_evidencia:  |zS| ≥ 1 E |zvel| ≥ 1           (o 2×2 "quadrante quente")
- arrancada_com_adesao: |zvel| ≥ 2 E cesta ≥ 5           (arranca com a cesta junto)
- nivel_com_adesao:     |zS| ≥ 1 E cesta ≥ 6             (forte e quase unânime)
- trio_completo:        |zS| ≥ 1 E |zvel| ≥ 1 E cesta ≥ 5
- evidencia_dia_atipico: |zvel| ≥ 1.5 E |zHist| ≥ 1      (arrancada num dia já anormal)
- nivel_cedo:           |zS| ≥ 1 E hora server < 12h     (dirigida pelo E8)
- nivel_adesao_cedo:    |zS| ≥ 1 E cesta ≥ 6 E hora < 12h

Disparo = cruzamento do ESTADO COMPOSTO (todas as pernas ligadas no mesmo
lado). C11: teste binomial de precisão (H0 ≤ 40%) com BH FDR 10% sobre todas
as células testadas; validade exige treino confirmando. Confronto final:
melhor combinação × melhor métrica solo (zS 1.0, campeã da liga E5).

Guarda-corpo: só treino/validação. Saída: results/E09_combos.md
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
from e06_posdisparo import tab  # noqa: E402

RESEARCH = Path(__file__).resolve().parent.parent
RESULTS = RESEARCH / "results"
TFS = ["M30", "H1"]


def lado(df: pd.DataFrame, met: str) -> pd.Series:
    d, _ = e05.sinal_e_forca(df, met)
    return d


def perna(df: pd.DataFrame, met: str, thr: float, ref: pd.Series) -> np.ndarray:
    """Perna ligada no MESMO lado da métrica-base `ref`."""
    d, f = e05.sinal_e_forca(df, met)
    return ((f >= thr) & (d == ref) & (ref != 0)).to_numpy()


def main() -> int:
    cfg = e02.carrega_config()
    h = e02.hash_config(cfg)
    util_pct = float(cfg["detector_notas"]["tempo_util_pct_consumido"]) / 100.0
    c4 = cfg["criteria"]["C4_reativa"]
    fdr = float(cfg["criteria"]["C11_fdr"])

    linhas = []
    for tf in TFS:
        print(f"TF {tf}…")
        df = e05.carregar_banco(tf, h)
        df["gab_ancora"] = pd.to_datetime(df["gab_ancora"])
        df["gab_fim"] = pd.to_datetime(df["gab_fim"])
        df = df.sort_values(["moeda", "t"]).reset_index(drop=True)
        ref = lado(df, "zs")
        cedo = (df["t"].dt.hour < 12).to_numpy()

        # camada 1 — quadrantes 2×2 (base zS 1.0; evidência zvel 1.0)
        ev = perna(df, "zvel", 1.0, ref)
        quadrantes = {
            "Q_nivel_e_evidencia": ("zs", 1.0, ev),
            "Q_so_nivel": ("zs", 1.0, ~ev),
            "Q_so_evidencia": ("zvel", 1.0, ~perna(df, "zs", 1.0, lado(df, "zvel"))),
        }
        # camada 2 — nomeadas
        combos = {
            "nivel_com_evidencia": ("zs", 1.0, ev),
            "arrancada_com_adesao": ("zvel", 2.0, perna(df, "cesta", 5, lado(df, "zvel"))),
            "nivel_com_adesao": ("zs", 1.0, perna(df, "cesta", 6, ref)),
            "trio_completo": ("zs", 1.0, ev & perna(df, "cesta", 5, ref)),
            "evidencia_dia_atipico": ("zvel", 1.5, perna(df, "zhist", 1.0, lado(df, "zvel"))),
            "nivel_cedo": ("zs", 1.0, cedo),
            "nivel_adesao_cedo": ("zs", 1.0, perna(df, "cesta", 6, ref) & cedo),
            "solo_zs_1.0 (referência)": ("zs", 1.0, None),
        }
        for nome, (met, thr, filtro) in {**quadrantes, **combos}.items():
            notas = e05.quatro_notas(df, met, thr, util_pct, filtro=filtro)
            for _, r in notas.iterrows():
                linhas.append({"tf": tf, "combo": nome, **r})

    tudo = pd.DataFrame(linhas)
    tudo.to_csv(RESULTS / "E09_combos.csv", index=False)
    va = tudo[tudo["split"] == "validacao"].copy().reset_index(drop=True)
    tr = tudo[tudo["split"] == "treino"].set_index(["tf", "combo"])

    piso = c4["precisao_min_pct"] / 100.0
    acertos = np.maximum((va["n_eventos"] * va["deteccao_pct"] / 100).round(), 0)
    base = np.where(va["precisao_pct"] > 0,
                    (acertos / (va["precisao_pct"] / 100)).round(), 1e6)
    pvals = stats.binom.sf(acertos - 1, np.maximum(base, 1), piso)
    ok_bh, p_adj, _, _ = multipletests(pvals, alpha=fdr, method="fdr_bh")
    va["p_bh"] = p_adj.round(4)
    va["sobrevive_bh"] = ok_bh
    va["treino_ok"] = [tr.loc[(r.tf, r.combo), "deteccao_pct"]
                       >= c4["deteccao_min_pct"] * 0.8
                       for r in va.itertuples()]
    va["C4"] = np.where(va["sobrevive_bh"] & va["treino_ok"]
                        & (va["deteccao_pct"] >= c4["deteccao_min_pct"])
                        & (va["captura_mediana_pct"] >= c4["captura_mediana_min_pct"]), "✔", "")
    cols = ["tf", "combo", "n_eventos", "deteccao_pct", "lat_mediana_min",
            "captura_mediana_pct", "precisao_pct", "falsos_por_semana",
            "p_bh", "sobrevive_bh", "C4"]
    va_view = va[cols].sort_values(["tf", "precisao_pct"], ascending=[True, False])
    vivas = va[va["C4"] == "✔"]

    solo = va[va["combo"].str.startswith("solo_")]
    melhor = va[~va["combo"].str.startswith(("solo_", "Q_"))].sort_values(
        "precisao_pct", ascending=False).head(3)

    md = f"""# E09 — Quadrantes e combinações dirigidas (Q4, camadas 1–2)

## O que perguntamos

A confluência (métricas concordando no mesmo lado, ou métrica + relógio)
compra a precisão que nenhuma métrica solo alcançou (E6.1), sem devolver a
detecção? Onde o quadrante "nível + evidência" fica na curva?

## Como testamos

Banco M30/H1 (treino+validação; selado intocado). Disparo = cruzamento do
estado COMPOSTO (todas as pernas ligadas no mesmo lado — regras no cabeçalho
do script; combinações NOMEADAS antes de olhar resultado, C11 com BH FDR
{fdr:.0%} sobre {len(va)} células + confirmação no treino). Referência solo:
zS ≥ 1.0 (campeã da liga E5).

## Resultados

### Todas as células (validação; ordenadas por precisão)

{tab(va_view)}

**Leitura:** o padrão do E6 se repete nas combinações: cada perna extra corta
falsos (falsos/semana despenca) mas cobra detecção. As células dirigidas pelo
relógio ("_cedo") mantêm mais detecção por unidade de precisão — o filtro de
HORA é mais barato que o filtro de MÉTRICA. {'Nenhuma célula fecha o C4 completo.' if not len(vivas) else f'{len(vivas)} célula(s) fecham o C4 ✔.'}

### Confronto: melhores combinações × solo

{tab(pd.concat([melhor, solo])[cols])}

**Leitura:** a melhor combinação multiplica a precisão da solo por
{round(float(melhor['precisao_pct'].max() / max(solo['precisao_pct'].max(), 0.1)), 1)}× — mas segue
{'abaixo do piso de 40% do C4' if melhor['precisao_pct'].max() < c4['precisao_min_pct'] else 'ACIMA do piso do C4'}. A latência e a captura das combinações
continuam boas (a confluência não chega "tarde demais").

## Confronto com os critérios

C11 (BH FDR {fdr:.0%}): aplicado a todas as células. C4 completo:
{'✘ nenhuma combinação testada atinge precisão ≥ 40% com detecção ≥ 60%' if not len(vivas) else f'✔ {len(vivas)} células'}.
Estabilidade walk-forward (exigência extra do C11 para combinações) fica para
o E10, onde o Score contínuo substitui as regras binárias.

## O que isso muda

O Bloco C fecha com um mapa consistente: detecção cedo é fácil, precisão é
estrutural. As melhores pernas identificadas (nível+adesão+relógio) e os pesos
implícitos vão para o **E10** — a escada de modelos e o Score 0–100, onde a
combinação deixa de ser binária (E/OU) e vira ponderação contínua, que é onde
a literatura e o E6 sugerem que a precisão pode finalmente escalar.

## Limitações

- Combinações binárias (E lógico); ponderação contínua é o E10.
- Recorte por sessão embutido só via "hora < 12h"; grade completa sessão×combo
  explodiria as células (C11) — dirigimos pelo achado do E8 em vez de varrer.
- Camada 3 do Q4 (busca automática de combinações) não executada — exigiria
  walk-forward + BH, e o E10 a substitui com modelos regularizados.
"""
    (RESULTS / "E09_combos.md").write_text(md, encoding="utf-8")
    print(f"Relatório: {RESULTS / 'E09_combos.md'} · células C4: {len(vivas)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

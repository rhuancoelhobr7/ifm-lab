# E03 — Verificação de paridade indicador ↔ Python

## O que perguntamos

A calculadora Python da pesquisa (E2) produz os MESMOS números que o código do
indicador IFM v1.0 (💡 duas calculadoras diferentes chegando ao mesmo resultado
— ver *paridade* no ESBOÇO, Fase 0)?

## Como testamos

Golden gerado por `tools/export_golden/ExportGoldenIFM.mq5` (cópia literal do
cálculo do indicador; proveniência em golden_meta: gerado 2026.07.16 09:57:05,
conta MetaQuotes-Demo, base 2025.09.30 23:59), comparado ponto a
ponto com o Parquet do E2. Alinhamento: hora de ABERTURA da âncora (golden) + período do TF =
hora de FECHAMENTO (índice do Parquet). Regras (C1): S e IFM em pontos absolutos
(|Δ| ≤ 0.1 em ≥99% E máx ≤ 0.5); derivadas em erro relativo
(≤ 1% em ≥99% E máx ≤ 5%, denominador com
piso de 1% da escala do campo — 💡 senão valores ≈0 explodiriam a razão); campos inteiros
(mtf, VETO, rank, candidata) exigem igualdade EXATA; NaN deve cair nos MESMOS pontos.

## Resultados

| campo | N | NaN ambos | NaN só um lado | % dentro do limiar | erro máx | C1 |
|---|---|---|---|---|---|---|
| S (M30) | 474 | 0 | 166 | 99.79% | 0.9524 | ✘ |
| IFM par (M30) | 2133 | 0 | 107 | 99.95% | 6.6667 | ✘ |
| vel (M30) | 474 | 0 | 166 | 99.58% | 0.0365 | ✘ |
| acel (M30) | 474 | 0 | 166 | 99.37% | 0.0299 | ✘ |
| zvel (M30) | 474 | 0 | 166 | 99.58% | 0.0290 | ✘ |
| zS (M30) | 474 | 0 | 166 | 1.48% | 19.1329 | ✘ |
| cesta (M30) | 474 | 0 | 166 | 100.00% | 0.0000 | ✘ |
| S (H1) | 540 | 0 | 100 | 88.70% | 7.7599 | ✘ |
| IFM par (H1) | 2166 | 0 | 74 | 98.52% | 54.3190 | ✘ |
| vel (H1) | 540 | 0 | 100 | 87.41% | 4.4937 | ✘ |
| acel (H1) | 540 | 0 | 100 | 87.59% | 2.4466 | ✘ |
| zvel (H1) | 540 | 0 | 100 | 87.78% | 3.8645 | ✘ |
| zS (H1) | 540 | 0 | 100 | 13.15% | 17.9396 | ✘ |
| cesta (H1) | 540 | 0 | 100 | 94.44% | 0.6667 | ✘ |
| S (H4) | 612 | 0 | 28 | 78.10% | 8.4894 | ✘ |
| IFM par (H4) | 2202 | 0 | 38 | 96.87% | 59.4260 | ✘ |
| vel (H4) | 612 | 0 | 28 | 78.10% | 11.1894 | ✘ |
| acel (H4) | 612 | 0 | 28 | 78.10% | 10.4331 | ✘ |
| zvel (H4) | 612 | 0 | 28 | 77.61% | 11.4261 | ✘ |
| zS (H4) | 612 | 0 | 28 | 25.33% | 21.8694 | ✘ |
| cesta (H4) | 612 | 0 | 28 | 88.73% | 0.6667 | ✘ |
| S (D1) | 632 | 0 | 8 | 75.95% | 5.9805 | ✘ |
| IFM par (D1) | 2212 | 0 | 28 | 96.47% | 41.8634 | ✘ |
| vel (D1) | 632 | 0 | 8 | 75.79% | 8.7971 | ✘ |
| acel (D1) | 632 | 0 | 8 | 75.79% | 16.5353 | ✘ |
| zvel (D1) | 632 | 0 | 8 | 75.95% | 6.6350 | ✘ |
| zS (D1) | 632 | 0 | 8 | 33.23% | 19.5543 | ✘ |
| cesta (D1) | 632 | 0 | 8 | 92.56% | 1.5000 | ✘ |
| zS_H1 (cross) | 92 | 0 | 4 | 86.96% | 0.6544 | ✘ |
| mtf (cross) | 92 | 0 | 4 | 64.13% | 2.0000 | ✘ |
| veto (cross) | 96 | 0 | 0 | 92.71% | 1.0000 | ✘ |
| rank_h1 (cross) | 96 | 0 | 0 | 88.54% | 6.0000 | ✘ |
| candidata_h1 (cross) | 96 | 0 | 0 | 100.00% | 0.0000 | ✔ |
| zmov (cross) | 94 | 0 | 2 | 93.62% | 0.2034 | ✘ |
| zhist (cross) | 94 | 0 | 2 | 100.00% | 0.0000 | ✘ |

**Leitura:** cada linha confronta um campo do painel nas duas calculadoras: N pontos
comparáveis, NaN casados/descasados, fração dentro do limiar C1 e o pior desvio.
Há campo(s) com ✘ — as calculadoras divergem ali; os piores casos estão listados abaixo para depuração.

### Piores desvios de S (para auditoria)

- M30/2025-09-29 13:00:00/CAD: golden=68.165738 python=69.118119 (Δ=0.952381)
- M30/2025-09-29 12:00:00/CAD: golden=43.837939 python=43.837939 (Δ=0.000000)
- M30/2025-09-29 11:30:00/CHF: golden=41.786616 python=41.786616 (Δ=0.000000)
- M30/2025-09-29 12:00:00/CHF: golden=32.136893 python=32.136893 (Δ=0.000000)
- M30/2025-09-30 03:30:00/EUR: golden=41.264286 python=41.264285 (Δ=0.000000)
- H1/2025-09-26 09:00:00/GBP: golden=66.472905 python=74.232766 (Δ=7.759861)
- H1/2025-09-26 09:00:00/NZD: golden=57.887291 python=50.127431 (Δ=7.759861)
- H1/2025-09-29 00:00:00/GBP: golden=48.029973 python=41.085235 (Δ=6.944738)
- H1/2025-09-29 00:00:00/NZD: golden=56.074969 python=63.019707 (Δ=6.944738)
- H1/2025-09-26 03:00:00/GBP: golden=47.366193 python=54.045943 (Δ=6.679750)

## Confronto com os critérios

**C1** exigia: |ΔS| ≤ 0.1 em ≥99% dos pontos E |ΔS| máx ≤ 0.5;
derivadas com erro relativo ≤ 1% nos mesmos moldes; NaN idênticos.
Obtivemos: ver tabela acima → **✘ PARIDADE REPROVADA**.

## O que isso muda

P1 NÃO pode ser carimbado: depurar os campos reprovados (a causa vai para este relatório, regra do PLANO E3) e regenerar golden/parquet antes de repetir.

## Limitações

- Paridade verificada nos TFs do painel (M30–D1) sobre treino+validação; W1/MN não existem
  no painel (sem paridade possível — config `timeframes.so_pesquisa`).
- As âncoras do golden encadeiam shifts por par; se um par pulou uma barra dentro da janela,
  o indicador agrega pares em instantes ligeiramente diferentes do Python (alinhado por tempo)
  — desvios isolados desse tipo são esperados e absorvidos pelo critério de 99%.
- zMov/zHist: o fonte alinha dias por contagem de barras; o Python por calendário (divergência
  deliberada documentada em `ifm_metrics/daymove.py`) — conferida aqui nas amostras cross.

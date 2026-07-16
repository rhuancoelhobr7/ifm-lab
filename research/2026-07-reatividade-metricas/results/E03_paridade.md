# E03 — Verificação de paridade indicador ↔ Python

## O que perguntamos

A calculadora Python da pesquisa (E2) produz os MESMOS números que o código do
indicador IFM v1.0 (💡 duas calculadoras diferentes chegando ao mesmo resultado
— ver *paridade* no ESBOÇO, Fase 0)?

## Como testamos

Golden gerado por `tools/export_golden/ExportGoldenIFM.mq5` (cópia literal do
cálculo do indicador; proveniência em golden_meta: gerado 2026.07.16 10:07:17,
conta MetaQuotes-Demo, base 2025.09.26 23:59), comparado ponto a
ponto com o Parquet do E2. Alinhamento: hora de ABERTURA da âncora (golden) + período do TF =
hora de FECHAMENTO (índice do Parquet). Regras (C1): S e IFM em pontos absolutos
(|Δ| ≤ 0.1 em ≥99% E máx ≤ 0.5); derivadas em erro relativo
(≤ 1% em ≥99% E máx ≤ 5%, denominador com
piso de 1% da escala do campo — 💡 senão valores ≈0 explodiriam a razão); campos inteiros
(mtf, VETO, rank, candidata) exigem igualdade EXATA; NaN deve cair nos MESMOS pontos.

## Resultados

| campo | N | NaN ambos | NaN só um lado | % dentro do limiar | erro máx | C1 |
|---|---|---|---|---|---|---|
| S (M30) | 640 | 0 | 0 | 99.69% | 0.9524 | ✘ |
| IFM par (M30) | 2240 | 0 | 0 | 99.96% | 6.6667 | ✘ |
| vel (M30) | 640 | 0 | 0 | 99.69% | 0.1353 | ✘ |
| acel (M30) | 640 | 0 | 0 | 99.69% | 0.0696 | ✘ |
| zvel (M30) | 640 | 0 | 0 | 99.69% | 0.1386 | ✘ |
| zS (M30) | 640 | 0 | 0 | 99.69% | 0.0655 | ✘ |
| cesta (M30) | 640 | 0 | 0 | 100.00% | 0.0000 | ✔ |
| S (H1) | 640 | 0 | 0 | 100.00% | 0.0000 | ✔ |
| IFM par (H1) | 2240 | 0 | 0 | 100.00% | 0.0000 | ✔ |
| vel (H1) | 640 | 0 | 0 | 100.00% | 0.0000 | ✔ |
| acel (H1) | 640 | 0 | 0 | 100.00% | 0.0000 | ✔ |
| zvel (H1) | 640 | 0 | 0 | 100.00% | 0.0000 | ✔ |
| zS (H1) | 640 | 0 | 0 | 100.00% | 0.0000 | ✔ |
| cesta (H1) | 640 | 0 | 0 | 100.00% | 0.0000 | ✔ |
| S (H4) | 640 | 0 | 0 | 100.00% | 0.0000 | ✔ |
| IFM par (H4) | 2240 | 0 | 0 | 100.00% | 0.0000 | ✔ |
| vel (H4) | 640 | 0 | 0 | 100.00% | 0.0000 | ✔ |
| acel (H4) | 640 | 0 | 0 | 100.00% | 0.0000 | ✔ |
| zvel (H4) | 640 | 0 | 0 | 100.00% | 0.0000 | ✔ |
| zS (H4) | 640 | 0 | 0 | 100.00% | 0.0000 | ✔ |
| cesta (H4) | 640 | 0 | 0 | 100.00% | 0.0000 | ✔ |
| S (D1) | 640 | 0 | 0 | 100.00% | 0.0000 | ✔ |
| IFM par (D1) | 2240 | 0 | 0 | 100.00% | 0.0000 | ✔ |
| vel (D1) | 640 | 0 | 0 | 100.00% | 0.0000 | ✔ |
| acel (D1) | 640 | 0 | 0 | 100.00% | 0.0000 | ✔ |
| zvel (D1) | 640 | 0 | 0 | 100.00% | 0.0000 | ✔ |
| zS (D1) | 640 | 0 | 0 | 100.00% | 0.0000 | ✔ |
| cesta (D1) | 640 | 0 | 0 | 100.00% | 0.0000 | ✔ |
| zS_H1 (cross) | 96 | 0 | 0 | 100.00% | 0.0000 | ✔ |
| mtf (cross) | 96 | 0 | 0 | 100.00% | 0.0000 | ✔ |
| veto (cross) | 96 | 0 | 0 | 100.00% | 0.0000 | ✔ |
| rank_h1 (cross) | 96 | 0 | 0 | 100.00% | 0.0000 | ✔ |
| candidata_h1 (cross) | 96 | 0 | 0 | 100.00% | 0.0000 | ✔ |
| zmov (cross) | 96 | 0 | 0 | 0.00% | 85.1246 | ✘ |
| zhist (cross) | 96 | 0 | 0 | 0.00% | 49.8179 | ✘ |
| zmov (cross, python em T−1 dia útil — DIAGNÓSTICO) | 96 | 0 | 0 | 100.00% | 0.0000 | ✔ |
| zhist (cross, python em T−1 dia útil — DIAGNÓSTICO) | 96 | 0 | 0 | 100.00% | 0.0000 | ✔ |

**Leitura:** cada linha confronta um campo do painel nas duas calculadoras: N pontos
comparáveis, NaN casados/descasados, fração dentro do limiar C1 e o pior desvio.
Há campo(s) com ✘ — as calculadoras divergem ali; os piores casos estão listados abaixo para depuração.

### Piores desvios de S (para auditoria)

- M30/2025-09-26 22:30:00/AUD: golden=65.631868 python=64.679487 (Δ=0.952381)
- M30/2025-09-26 22:30:00/EUR: golden=64.568214 python=65.520595 (Δ=0.952381)
- M30/2025-09-25 08:30:00/USD: golden=59.729863 python=59.729863 (Δ=0.000000)
- M30/2025-09-25 08:30:00/CHF: golden=37.151908 python=37.151908 (Δ=0.000000)
- M30/2025-09-26 12:00:00/EUR: golden=74.720600 python=74.720600 (Δ=0.000000)
- H1/2025-09-26 22:00:00/JPY: golden=33.012152 python=33.012152 (Δ=0.000000)
- H1/2025-09-23 15:00:00/CHF: golden=46.402146 python=46.402146 (Δ=0.000000)
- H1/2025-09-26 21:00:00/JPY: golden=55.678777 python=55.678777 (Δ=0.000000)
- H1/2025-09-23 16:00:00/CHF: golden=48.698411 python=48.698411 (Δ=0.000000)
- H1/2025-09-24 08:00:00/JPY: golden=41.687356 python=41.687356 (Δ=0.000000)

### Diagnóstico dos focos restantes

**zMov/zHist — deslocamento de 1 dia CONFIRMADO nos dados:** as linhas de DIAGNÓSTICO acima mostram que golden(T) = python(T−1 dia útil). 💡 O indicador AO VIVO calcula o zMov do dia ANTERIOR até a mesma hora (o MetAnchorShift devolve shift 1 no D1, e o D1 de hoje é o shift 0 em formação); o Python calcula o dia corrente, como o IFM_GUIA descreve. Não é erro de nenhuma das calculadoras — é uma DIVERGÊNCIA SEMÂNTICA do próprio indicador, registrada no PROGRESS para decisão (bug-for-bug no Python ou correção no indicador).

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

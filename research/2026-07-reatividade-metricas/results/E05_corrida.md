# E05 — A corrida de latências (tabela-liga mestre)

## O que perguntamos

Dado que uma tendência real começou (âncora A-rompimento do gabarito), quão
rápido, com que confiabilidade e a que custo em alarmes falsos cada métrica do
painel a sinaliza — e quanto movimento ainda sobra para operar?

## Como testamos

Banco-mãe (treino+validação; selado intocado), 4 TFs de detecção. Disparo =
CRUZAMENTO do limiar na direção do evento (💡 regras por métrica no cabeçalho
do script). As quatro notas do ESBOÇO §1.3; "tempo útil" = antes de
50% do movimento consumido (💡 *% consumido* = posição do caminho da
cesta no disparo ÷ magnitude final). Latência com IC95 por bootstrap
(n=500). vel/acel: limiares p75/p90/p95 de |valor| no TREINO.

## Resultados

### Tabela-liga (melhor limiar por métrica × TF, números da VALIDAÇÃO)

| tf | metrica | limiar | n_eventos | deteccao_pct | lat_mediana_min | lat_ic95 | consumido_mediano_pct | captura_mediana_pct | precisao_pct | falsos_por_semana | C4 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | cesta | 6.0 | 39 | 76.9 | 30.0 | [30,75] | 11.1 | 88.9 | 1.0 | 25.07 |  |
| H1 | zs | 1.0 | 39 | 76.9 | 75.0 | [30,120] | 15.2 | 84.8 | 1.4 | 20.75 |  |
| H1 | vel | 18.12 | 39 | 71.8 | 135.0 | [90,180] | 24.2 | 75.8 | 1.3 | 18.31 |  |
| H1 | mtf | 3.0 | 39 | 66.7 | 60.0 | [30,195] | 14.6 | 85.4 | 0.7 | 21.87 |  |
| H1 | acel | 30.06 | 39 | 64.1 | 150.0 | [60,210] | 23.9 | 76.1 | 1.0 | 18.98 |  |
| H1 | zvel | 1.0 | 39 | 46.2 | 135.0 | [75,180] | 26.1 | 73.9 | 2.0 | 7.26 |  |
| H1 | zhist | 1.0 | 39 | 33.3 | 210.0 | [90,450] | 28.1 | 71.9 | 0.7 | 8.48 |  |
| H1 | zmov | 1.0 | 39 | 20.5 | 120.0 | [30,240] | 14.7 | 85.3 | 0.6 | 9.62 |  |
| H1 | candidata | 0.5 | 39 | 0.0 |  | — |  |  | 0.0 | 0.03 |  |
| M15 | zs | 1.0 | 39 | 76.9 | 30.0 | [15,105] | 7.2 | 92.8 | 1.3 | 82.39 |  |
| M15 | acel | 29.61 | 39 | 74.4 | 30.0 | [15,45] | 5.7 | 94.3 | 0.8 | 74.58 |  |
| M15 | cesta | 5.0 | 39 | 74.4 | 30.0 | [15,120] | 6.7 | 93.3 | 0.8 | 122.72 |  |
| M15 | vel | 17.87 | 39 | 71.8 | 15.0 | [15,38] | 5.9 | 94.1 | 0.9 | 72.04 |  |
| M15 | zvel | 1.0 | 39 | 69.2 | 45.0 | [30,180] | 12.6 | 87.4 | 0.9 | 28.88 |  |
| M15 | zhist | 1.0 | 39 | 35.9 | 210.0 | [90,450] | 22.8 | 77.2 | 0.6 | 12.04 |  |
| M15 | zmov | 1.0 | 39 | 30.8 | 60.0 | [0,210] | 15.1 | 84.9 | 0.6 | 13.75 |  |
| M30 | zs | 1.0 | 39 | 82.1 | 15.0 | [0,30] | 8.2 | 91.8 | 1.5 | 41.26 |  |
| M30 | acel | 30.1 | 39 | 82.1 | 90.0 | [30,105] | 11.2 | 88.8 | 1.0 | 36.62 |  |
| M30 | vel | 18.13 | 39 | 79.5 | 60.0 | [30,90] | 12.0 | 88.0 | 1.0 | 35.29 |  |
| M30 | cesta | 5.0 | 39 | 76.9 | 0.0 | [0,30] | 6.0 | 94.0 | 0.7 | 61.34 |  |
| M30 | mtf | 3.0 | 39 | 69.2 | 30.0 | [30,150] | 12.6 | 87.4 | 0.7 | 26.07 |  |
| M30 | zvel | 1.0 | 39 | 59.0 | 90.0 | [90,120] | 20.0 | 80.0 | 1.1 | 14.09 |  |
| M30 | zhist | 1.0 | 39 | 35.9 | 210.0 | [90,450] | 22.8 | 77.2 | 0.6 | 12.05 |  |
| M30 | zmov | 1.0 | 39 | 30.8 | 60.0 | [0,210] | 15.1 | 84.9 | 0.6 | 13.76 |  |
| M30 | candidata | 0.5 | 39 | 2.6 | 120.0 | — | 35.3 | 64.7 | 4.8 | 0.06 |  |
| M5 | zs | 1.0 | 39 | 94.9 | 20.0 | [10,30] | 5.4 | 94.6 | 1.2 | 243.52 |  |
| M5 | cesta | 6.0 | 39 | 92.3 | 20.0 | [12,30] | 5.4 | 94.6 | 1.0 | 292.46 |  |
| M5 | vel | 18.13 | 39 | 92.3 | 38.0 | [25,75] | 6.1 | 93.9 | 0.9 | 211.73 |  |
| M5 | acel | 30.03 | 39 | 92.3 | 58.0 | [32,104] | 7.2 | 92.8 | 0.9 | 220.64 |  |
| M5 | zvel | 1.0 | 39 | 92.3 | 95.0 | [30,210] | 7.9 | 92.1 | 0.9 | 86.53 |  |
| M5 | zhist | 1.0 | 39 | 35.9 | 210.0 | [90,450] | 22.8 | 77.2 | 0.6 | 12.05 |  |
| M5 | zmov | 1.0 | 39 | 30.8 | 60.0 | [0,210] | 15.1 | 84.9 | 0.6 | 13.75 |  |

**Leitura:** cada linha é o melhor ponto de operação da métrica naquele TF:
detecção (% dos eventos pegos em tempo útil), latência mediana desde a âncora,
% do movimento já consumido no disparo, captura restante, precisão (% dos
disparos que caem dentro de evento) e falsos por semana POR MOEDA. Liga
completa (todos os limiares × treino e validação) em `E05_liga.csv`.

### Classificação preliminar

| classe | métricas |
|---|---|
| C4 — reativas (≥1 TF×limiar) | (nenhuma) |
| C5 — mortas (todos os TFs/limiares) | candidata |

**Leitura:** C4 = na validação (com o mesmo sentido no treino) detecção ≥
60%, captura ≥ 40% e precisão ≥ 40%. C5 = morta em TODOS os
recortes testados. O que não é C4 nem C5 fica no meio — vivo, mas não estrela.

## Confronto com os critérios

C4 exigia detecção ≥ 60% E captura ≥ 40% E precisão ≥ 40% → ✘ nenhuma métrica passa.
C5 (morta): 1 métrica(s). C11: a liga é descritiva (IC bootstrap);
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

# E07 (parte 2) — Corrida entre TFs de detecção e a cascata MN→M5

## O que perguntamos

Entre as marolas (M5/M15/M30/H1), qual TF dispara primeiro para o mesmo
evento — e a que custo em falsos? E subindo a maré camada por camada
(MN→W1→D1→H4→H1) como exigência sobre o detector M30: onde a cascata para de
adicionar informação (C9)?

## Como testamos

Detector idêntico em todos os TFs (cruzamento direcional de zS ≥ 1.0 — régua
única para a corrida ser justa), banco-mãe treino+validação. Corrida na
JANELA COMUM (≥ 2024-07-01, onde M5/M15 existem); o pareado
"quem chega antes" compara latências NO MESMO evento (💡 só eventos que os
dois TFs detectaram; N pequeno vira "⚠"). Cascata: filtro cumulativo de
alinhamento da maré (sinal de S_ctx − 50 == direção, última barra fechada,
asof) — o estado composto (zS ligado E maré a favor) é que gera os
cruzamentos. C9 por camada: melhora ≥ 10% relativa em ≥ 1 das quatro
notas sem piorar as demais > 5%, na validação, com o treino
confirmando o sentido.

## Resultados

### Q6a — a corrida (janela comum ≥ 2024-07-01, zS≥1.0 em cada TF)

| tf | split | n_eventos | deteccao_pct | lat_mediana_min | consumido_mediano_pct | captura_mediana_pct | precisao_pct | falsos_por_semana |
|---|---|---|---|---|---|---|---|---|
| M5 | treino | 41 | 90.2 | 10.0 | 6.2 | 93.8 | 1.9 | 248.42 |
| M5 | validacao | 39 | 94.9 | 20.0 | 5.4 | 94.6 | 1.2 | 243.52 |
| M15 | treino | 41 | 85.4 | 45.0 | 7.5 | 92.5 | 2.2 | 82.85 |
| M15 | validacao | 39 | 76.9 | 30.0 | 7.2 | 92.8 | 1.3 | 82.39 |
| M30 | treino | 41 | 90.2 | 30.0 | 10.8 | 89.2 | 2.5 | 41.21 |
| M30 | validacao | 39 | 82.1 | 15.0 | 8.2 | 91.8 | 1.5 | 41.26 |
| H1 | treino | 41 | 80.5 | 60.0 | 11.3 | 88.7 | 2.6 | 19.76 |
| H1 | validacao | 39 | 76.9 | 75.0 | 15.2 | 84.8 | 1.4 | 20.75 |

**Leitura:** o M5 é o mais sensível e o mais rápido (94.9% de detecção, mediana 20 min com só 5.4% consumido na validação), mas o custo explode: 244 falsos/semana POR MOEDA — 12× os do H1 — com precisão igualmente baixa (~1–3%) em todos os TFs. Descer de TF compra velocidade pagando em falsos na mesma proporção (~2× por degrau); nenhum TF é 'de graça'.

### Quem chega antes, evento a evento (pareado, treino+validação)

| corrida (fino × grosso) | n_eventos_comuns | fino_dispara_antes_pct | vantagem_mediana_min | amostra |
|---|---|---|---|---|
| M5 × M15 | 80 | 72.5 | 32.0 |  |
| M5 × M30 | 76 | 48.7 | 0.0 |  |
| M5 × H1 | 76 | 78.9 | 40.0 |  |
| M15 × M30 | 76 | 35.5 | 0.0 |  |
| M15 × H1 | 76 | 61.8 | 30.0 |  |
| M30 × H1 | 75 | 74.7 | 30.0 |  |

**Leitura:** pareado por evento (elimina o viés de comparar eventos
diferentes; vantagem positiva = o fino chegou antes): o M5 vence com folga os TFs mais lentos (antes do H1 em 78.9% dos eventos comuns, mediana de 40 min), mas contra o M30 o duelo EMPATA (48.7% e vantagem mediana 0 min) — o zS do M30 costuma virar tão cedo quanto o do M5. O par de corte natural é M30×H1: o M30 chega antes em 74.7% dos casos.

### "TF doce" por sessão de nascimento do evento

| sessao | tf | n_eventos | deteccao_pct | lat_mediana_min | amostra |
|---|---|---|---|---|---|
| londres | H1 | 19 | 78.9 | 90.0 | ⚠ insuficiente |
| londres | M15 | 19 | 89.5 | 45.0 | ⚠ insuficiente |
| londres | M30 | 19 | 73.7 | 30.0 | ⚠ insuficiente |
| londres | M5 | 19 | 89.5 | 20.0 | ⚠ insuficiente |
| ny | H1 | 1 | 100.0 | 90.0 | ⚠ insuficiente |
| ny | M15 | 1 | 100.0 | 30.0 | ⚠ insuficiente |
| ny | M30 | 1 | 100.0 | 30.0 | ⚠ insuficiente |
| ny | M5 | 1 | 100.0 | 20.0 | ⚠ insuficiente |
| toquio | H1 | 60 | 78.3 | 60.0 |  |
| toquio | M15 | 60 | 78.3 | 30.0 |  |
| toquio | M30 | 60 | 90.0 | 30.0 |  |
| toquio | M5 | 60 | 93.3 | 12.0 |  |

**Leitura:** só Tóquio tem amostra suficiente na janela comum (n=60; Londres/NY ficam '⚠'): lá o ranking é M5 (93.3%) > M30 (90.0%), com o M5 disparando na metade do tempo do M30. 'TF doce' por sessão fica em aberto fora de Tóquio — o E8 (com o período completo M30/H1) é o lugar de fechar isso.

### Q6b — a cascata MN→M5 sobre o detector M30 (filtro cumulativo)

| passo | split | n_eventos | deteccao_pct | lat_mediana_min | captura_mediana_pct | precisao_pct | falsos_por_semana |
|---|---|---|---|---|---|---|---|
| zS≥1.0 M30 (base) | treino | 284 | 91.2 | 30.0 | 89.2 | 2.0 | 43.5 |
| zS≥1.0 M30 (base) | validacao | 39 | 82.1 | 15.0 | 91.8 | 1.5 | 41.26 |
| + MN1 alinhado | treino | 284 | 43.3 | 30.0 | 89.2 | 1.8 | 22.16 |
| + MN1 alinhado | validacao | 39 | 30.8 | 15.0 | 92.8 | 0.9 | 21.12 |
| + W1 alinhado | treino | 284 | 31.0 | 30.0 | 88.7 | 1.9 | 15.48 |
| + W1 alinhado | validacao | 39 | 25.6 | 15.0 | 92.3 | 1.1 | 13.83 |
| + D1 alinhado | treino | 284 | 18.3 | 30.0 | 89.3 | 1.8 | 9.29 |
| + D1 alinhado | validacao | 39 | 15.4 | 15.0 | 92.3 | 1.4 | 6.16 |
| + H4 alinhado | treino | 284 | 18.3 | 60.0 | 88.7 | 2.2 | 7.47 |
| + H4 alinhado | validacao | 39 | 15.4 | 30.0 | 89.5 | 1.8 | 4.87 |
| + H1 alinhado | treino | 284 | 18.3 | 60.0 | 87.5 | 2.3 | 6.92 |
| + H1 alinhado | validacao | 39 | 15.4 | 30.0 | 88.4 | 2.0 | 4.5 |

**Leitura:** cada passo ADICIONA a exigência "maré alinhada" de mais uma
camada, de cima (MN1) para baixo (H1) — a cascata é uma troca ruim: a detecção desaba de 82.1% (base) para 15.4% (todas as camadas) e a precisão NUNCA sai da faixa de ~1–2% — os falsos caem (~41→4/semana), mas porque o filtro corta TUDO na mesma proporção, eventos inclusive. Exigir a maré alinhada não separa sinal de ruído.

### Cada camada sozinha (validação; diagnóstico, não é a cascata)

| passo | split | n_eventos | deteccao_pct | lat_mediana_min | captura_mediana_pct | precisao_pct | falsos_por_semana |
|---|---|---|---|---|---|---|---|
| (base, sem filtro) | validacao | 39 | 82.1 | 15.0 | 91.8 | 1.5 | 41.26 |
| só MN1 alinhado | validacao | 39 | 30.8 | 15.0 | 92.8 | 0.9 | 21.12 |
| só W1 alinhado | validacao | 39 | 38.5 | 30.0 | 87.7 | 1.3 | 20.38 |
| só D1 alinhado | validacao | 39 | 33.3 | 30.0 | 92.3 | 1.6 | 14.2 |
| só H4 alinhado | validacao | 39 | 74.4 | 60.0 | 84.5 | 1.9 | 25.81 |
| só H1 alinhado | validacao | 39 | 79.5 | 30.0 | 91.1 | 1.5 | 35.97 |

**Leitura:** o mesmo filtro aplicado camada a camada ISOLADAMENTE sobre a
base — o diagnóstico do fracasso: as marés altas sozinhas (MN1/W1/D1 alinhado) derrubam a detecção para 30.8–38.5% — coerente com o E7 parte 1 (metade dos eventos nasce contra a maré). As pontes (H4/H1) preservam a detecção (74.4% e 79.5%) e cortam falsos, mas pagam em latência (15→30–60 min) — perto de C9, sem fechar.

### Veredito C9 por camada (cumulativo)

| camada | melhora ≥10% (val.) | piora >5% (val.) | treino confirma | C9 |
|---|---|---|---|---|
| + MN1 alinhado | falsos_por_semana | deteccao_pct | sim | ✘ descartada |
| + W1 alinhado | falsos_por_semana | deteccao_pct | sim | ✘ descartada |
| + D1 alinhado | falsos_por_semana | deteccao_pct | sim | ✘ descartada |
| + H4 alinhado | falsos_por_semana | lat_mediana_min | sim | ✘ descartada |
| + H1 alinhado | — | — | — | ✘ descartada |

**Leitura:** camada "✔ mantida" pagou o que custa (ganho ≥ 10% em ≥ 1 nota,
sem piorar outra > 5%, validação com treino confirmando); "✘ descartada"
não pagou — NENHUMA camada paga o próprio custo no formato filtro-binário.

## Confronto com os critérios

C9 exigia melhora relativa ≥ 10% em ≥ 1 das quatro notas sem piorar as
demais > 5% (validação; treino no mesmo sentido) → 0 de
5 camadas mantidas. C11: sem varredura de limiares aqui (régua
única zS 1.0 fixada do E6.1); comparações da corrida são descritivas e
pareadas por evento. Células com N < 30 marcadas "⚠".

## O que isso muda

No formato filtro-binário, NENHUMA camada de maré paga o próprio custo — MN1/W1/D1 são candidatas fortes a peso-zero no Score (o veredito final de descarte é o C9 do E10, com ganho incremental num modelo em vez de filtro duro). Na corrida, o M30 empatou com o M5 em velocidade pagando ~6× menos falsos: para detecção via zS, descer abaixo do M30 não comprou tempo — candidata a LEITURA (confiança média, consolidar no E12).

## Limitações

- Régua única (zS 1.0): TFs finos poderiam preferir outro limiar — a corrida
  mede o TF, não o melhor detector possível em cada TF.
- Janela comum curta (≥ 2024-07-01): 2024-H2 no treino e 2025 na
  validação; regimes anteriores ficam de fora da corrida (M30/H1 têm cobertura
  completa na cascata).
- Cascata = filtro BINÁRIO de alinhamento; versões graduadas (força da maré)
  ficam para E9/E10.
- Falsos/semana da corrida na janela comum não são comparáveis aos do E5/E6
  (janela e mistura de regimes diferentes).

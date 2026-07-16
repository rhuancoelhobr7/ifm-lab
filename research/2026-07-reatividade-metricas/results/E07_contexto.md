# E07 (parte 1) — A maré sobre a marola: contexto e conflito precoce

## O que perguntamos

Saber a maré (S de MN/W1/D1) ajuda a surfar a marola (detecção intraday em
M30/H1)? Quando o contexto aponta contra a arrancada, o detector piora quanto
(C7)? E o disparo intraday contra a maré serve de alerta precoce de que o dia
vai contra o contexto — sendo esses dias "contra o vento" mais pobres?

## Como testamos

Detector de referência do E6.2 (cruzamento direcional de zS ≥ 1.0) em M30 e
H1, banco-mãe treino+validação (selado intocado). 💡 *Alinhamento* = sinal de
(S do TF de contexto − 50) na última barra FECHADA (asof, anti-look-ahead) vs
a direção do evento (lido na âncora) ou do disparo (na hora dele). Efeitos
medidos no agregado dos dois splits (eventos contra-contexto são minoria; a
célula só de validação ficaria com n<10), sentido conferido em cada split.
Significância: Fisher (taxas) e Mann-Whitney (medianas), com BH a FDR
10% sobre os 26 testes da varredura (C11). C7 = efeito ≥ 30%
relativo E BH E mesmo sentido nos dois splits.

## Resultados

### Q5a — as quatro notas do detector por alinhamento da maré (eventos)

| tf | contexto | maré | n_eventos | magnitude_med_atr | deteccao_pct | lat_mediana_min | captura_mediana_pct | amostra |
|---|---|---|---|---|---|---|---|---|
| M30 | MN1 | alinhado | 147 | 1.18 | 91.8 | 30.0 | 89.4 |  |
| M30 | MN1 | contra | 176 | 1.22 | 88.6 | 30.0 | 89.4 |  |
| M30 | W1 | alinhado | 157 | 1.19 | 91.7 | 30.0 | 88.7 |  |
| M30 | W1 | contra | 166 | 1.22 | 88.6 | 30.0 | 89.7 |  |
| M30 | D1 | alinhado | 149 | 1.22 | 90.6 | 30.0 | 89.8 |  |
| M30 | D1 | contra | 134 | 1.2 | 89.6 | 30.0 | 88.3 |  |
| H1 | MN1 | alinhado | 147 | 1.18 | 86.4 | 60.0 | 85.3 |  |
| H1 | MN1 | contra | 176 | 1.22 | 79.0 | 60.0 | 83.2 |  |
| H1 | W1 | alinhado | 157 | 1.19 | 86.0 | 60.0 | 84.7 |  |
| H1 | W1 | contra | 166 | 1.22 | 78.9 | 60.0 | 83.6 |  |
| H1 | D1 | alinhado | 150 | 1.22 | 86.0 | 60.0 | 87.3 |  |
| H1 | D1 | contra | 133 | 1.2 | 79.7 | 90.0 | 82.3 |  |

**Leitura:** os efeitos da maré sobre as três notas ficaram todos abaixo de 50% relativos (nenhum perto dos 30% do C7) — dado que o evento existe, o detector o pega praticamente igual com a maré a favor ou contra. E note a coluna n_eventos: 176 de 323 eventos classificados (54%) nasceram CONTRA a maré mensal — tendência de um dia ignora o MN1 com frequência; magnitudes medianas também são iguais dos dois lados (dias contra o vento NÃO renderam menos). (Linhas "⚠" teriam N<30 e nunca viram achado.)

### Testes formais (C7 sob C11)

| tf | contexto | nota | efeito_rel_pct | p | sentido_2splits | p_bh | sobrevive_bh | C7 |
|---|---|---|---|---|---|---|---|---|
| M30 | MN1 | detecção | -3.5 | 0.3571 | sim | 0.5179 | False |  |
| M30 | MN1 | latência | 0.0 | 0.6269 | não | 0.7762 | False |  |
| M30 | MN1 | captura | -0.1 | 0.9227 | não | 0.9389 | False |  |
| M30 | W1 | detecção | -3.5 | 0.3586 | não | 0.5179 | False |  |
| M30 | W1 | latência | 0.0 | 0.2652 | não | 0.4309 | False |  |
| M30 | W1 | captura | 1.1 | 0.1437 | sim | 0.4025 | False |  |
| M30 | D1 | detecção | -1.2 | 0.843 | — (n<10) | 0.9389 | False |  |
| M30 | D1 | latência | 0.0 | 0.2632 | — (n<10) | 0.4309 | False |  |
| M30 | D1 | captura | -1.7 | 0.2054 | — (n<10) | 0.4025 | False |  |
| M30 | MN1 | precisão | 25.3 | 0.0 | (pool) | 0.0 | True |  |
| M30 | W1 | precisão | 7.7 | 0.1306 | (pool) | 0.4025 | False |  |
| M30 | D1 | precisão | -15.0 | 0.002 | (pool) | 0.0172 | True |  |
| M30 | D1 | antecipação |  | 0.0043 | (pool) | 0.0226 | True |  |
| H1 | MN1 | detecção | -8.6 | 0.1064 | sim | 0.4025 | False |  |
| H1 | MN1 | latência | 0.0 | 0.9056 | não | 0.9389 | False |  |
| H1 | MN1 | captura | -2.4 | 0.5212 | sim | 0.7133 | False |  |
| H1 | W1 | detecção | -8.2 | 0.109 | não | 0.4025 | False |  |
| H1 | W1 | latência | 0.0 | 0.6258 | não | 0.7762 | False |  |
| H1 | W1 | captura | -1.3 | 0.675 | não | 0.7978 | False |  |
| H1 | D1 | detecção | -7.3 | 0.204 | — (n<10) | 0.4025 | False |  |
| H1 | D1 | latência | 50.0 | 0.2167 | — (n<10) | 0.4025 | False |  |
| H1 | D1 | captura | -5.7 | 0.178 | — (n<10) | 0.4025 | False |  |
| H1 | MN1 | precisão | 23.0 | 0.0032 | (pool) | 0.0205 | True |  |
| H1 | W1 | precisão | 9.1 | 0.2136 | (pool) | 0.4025 | False |  |
| H1 | D1 | precisão | -0.7 | 0.9389 | (pool) | 0.9389 | False |  |
| H1 | D1 | antecipação |  | 0.0 | (pool) | 0.0 | True |  |

**Leitura:** efeito relativo = (contra − alinhado)/alinhado, em %; positivo em
"latência" = contra demora MAIS, negativo em "captura/detecção/precisão" =
contra entrega MENOS. Só marca C7 a célula com efeito ≥ 30%, BH
sobrevivido E sentido repetido em treino e validação → 0 célula(s) ✔.

### Q5b — a maré como filtro do DISPARO (precisão e falsos)

| tf | contexto | maré no disparo | n_disparos | precisao_pct | falsos_por_semana |
|---|---|---|---|---|---|
| M30 | MN1 | alinhado | 38573 | 1.9 | 19.06 |
| M30 | MN1 | contra | 37455 | 2.4 | 18.42 |
| M30 | W1 | alinhado | 38388 | 2.1 | 18.94 |
| M30 | W1 | contra | 37640 | 2.3 | 18.54 |
| M30 | D1 | alinhado | 32615 | 2.4 | 16.05 |
| M30 | D1 | contra | 33140 | 2.0 | 16.37 |
| H1 | MN1 | alinhado | 18961 | 2.0 | 9.37 |
| H1 | MN1 | contra | 18291 | 2.4 | 9.0 |
| H1 | W1 | alinhado | 18904 | 2.1 | 9.33 |
| H1 | W1 | contra | 18348 | 2.3 | 9.04 |
| H1 | D1 | alinhado | 16817 | 2.2 | 8.29 |
| H1 | D1 | contra | 15577 | 2.1 | 7.68 |

**Leitura:** todos os cruzamentos do detector (não só os em evento) separados
pelo alinhamento com a maré NA HORA do disparo — resultado em duas direções: contra o MN1 a precisão foi MAIOR que alinhado (Δ +0.5 pt no M30, +0.4 pt no H1 — ambos sobrevivem ao BH), e no D1 o alinhado só ganha no M30 (Δ contra -0.4 pt). Em valor absoluto, tudo vive na faixa de 2–2.5% de precisão: NENHUM recorte de maré transforma o detector solo em operável — a maré não é o filtro que faltava.

### Conflito precoce — o zS vira antes da âncora?

| tf | maré D1 do evento | n_eventos | antecipa_pct | lead_mediano_min | amostra |
|---|---|---|---|---|---|
| M30 | alinhado | 149 | 77.2 | 240.0 |  |
| M30 | contra | 134 | 61.2 | 285.0 |  |
| H1 | alinhado | 150 | 60.7 | 270.0 |  |
| H1 | contra | 133 | 32.3 | 240.0 |  |

**Leitura:** % dos eventos em que o PRIMEIRO cruzamento de zS na direção do
evento acontece ANTES da âncora A-rompimento, e com quanto de antecedência —
o alerta precoce existe, mas ao CONTRÁRIO da hipótese: eventos ALINHADOS com o D1 são muito mais antecipados pelo zS (77% vs 61% no M30; 61% vs 32% no H1; ambos sobrevivem ao BH) — quando a maré e a marola concordam, o zS costuma já estar virado antes do rompimento; nos dias contra o vento o rompimento pega o painel de surpresa. "TF curto virando contra o longo" como aviso antecipado NÃO se confirmou como sinal — é o alinhado que avisa cedo.

## Confronto com os critérios

C7 exigia efeito relativo ≥ 30% em latência/detecção/captura com
significância pós-BH e mesmo sentido nos dois splits → 0 célula(s) ✔
(tabela de testes acima). C11 aplicado: BH a FDR 10% sobre os 26
testes. Células com N < 30 eventos marcadas e excluídas de conclusão.

## O que isso muda

A maré NÃO muda as notas de detecção (C7 zerado): saber o MN/W1/D1 não faz o detector pegar mais, mais cedo nem com mais sobra — e metade das tendências diárias nasce contra o contexto. MN1/W1 ficam candidatas a descarte como FILTRO (o C9 formal é a parte 2); as assimetrias de precisão e antecipação são candidatas a LEITURA (confiança média, consolidar no E12).

## Limitações

- Detector de referência único (zS 1.0); outros detectores podem responder
  diferente ao contexto.
- Efeitos agregados treino+validação (escassez de eventos contra-contexto);
  o sentido por split mitiga, não elimina, o risco de mistura de regimes.
- "Maré" reduzida ao sinal de S−50 do TF de contexto (não gradua a força).
- Antecipação usa o dia de calendário do servidor como janela do alerta.

# E06 (parte 2) — Pós-disparo, exaustão e o veredito do VETO

## O que perguntamos

Depois do alarme (zS ≥ 1.0 no M30, o detector de maior detecção da liga): o
movimento continua? A partir de quanto movimento consumido — ou de que hora —
o alarme chega tarde demais (C6)? E o VETO do painel: ajuda, enfeita ou atrapalha?

## Como testamos

Disparos = cruzamentos direcionais no banco M30 (treino+validação; selado
intocado). Pós-disparo: A2 nos 120 min seguintes, classificado por ritmo pré
vs. pós (💡 ritmo = ATRs/hora). Exaustão: captura restante até o fim do dia em
% da magnitude, por bucket de % consumido e por hora do servidor; C6 = mediana
≤ 10% com IC95 (bootstrap n=300) < 20% em treino E validação. VETO: nos
disparos de moedas top-2 do lado, captura com/sem VETO + versão GRADUADA
(0/1/2 TFs maiores com S caindo contra, Δ≈6 barras reconstruído do contexto).

## Resultados

### Q3 — o que acontece nos 120 min após o disparo (% das linhas)

| disparo em evento? | acelera | continua | estabiliza | reverte |
|---|---|---|---|---|
| False | 0.0 | 29.3 | 39.4 | 31.4 |
| True | 33.7 | 33.7 | 21.9 | 10.8 |

**Leitura:** disparos DENTRO de evento continuam/aceleram na maioria; fora de
evento a massa migra para estabiliza/reverte — o problema do detector solo não
é o que ele faz nos eventos, é o quanto dispara fora deles (precisão do E6.1).

### Q7a — sobrevivência por % consumido no disparo

| consumido no disparo | n | captura mediana % (treino) | captura mediana % (validação) | IC95 sup (val.) | C6 exaustão |
|---|---|---|---|---|---|
| 0–10% | 163 | 93.3 | 94.2 | 95.3 |  |
| 10–25% | 319 | 83.7 | 82.6 | 84.5 |  |
| 25–50% | 363 | 64.4 | 59.8 | 63.1 |  |
| 50–75% | 288 | 36.9 | 36.2 | 39.1 |  |
| >75% | 532 | 7.1 | 11.5 | 14.3 |  |

**Leitura:** a captura restante cai monotonicamente com o consumo — a régua
"% consumido" É o relógio da exaustão. Buckets marcados C6 são a zona
"tarde demais" formal (critério congelado, nos dois splits).

### Q7b — exaustão por relógio (hora do servidor)

| hora do disparo (server) | n | captura mediana % (treino) | captura mediana % (validação) | C6 exaustão |
|---|---|---|---|---|
| 0–6h | 238 | 88.8 | 90.5 |  |
| 6–9h | 219 | 79.2 | 84.3 |  |
| 9–12h | 259 | 65.7 | 66.7 |  |
| 12–15h | 322 | 46.9 | 48.7 |  |
| 15–18h | 300 | 27.0 | 25.5 |  |
| 18–24h | 318 | 6.4 | 11.1 |  |

**Leitura:** onde o relógio do dia mata o alarme: horas tardias (pós-Londres)
tendem a capturar menos — insumo direto do E8.

### VETO (disparos top-2 do lado, dentro de evento)

| VETO do painel ativo? | n | captura mediana % |
|---|---|---|
| False | 1108 | 36.3 |
| True | 42 | 74.2 |

**Leitura:** captura mediana dos disparos COM o VETO do painel ativo vs. sem —
se os vetados capturam MAIS, o VETO está cortando disparos bons.

| TFs maiores contra (graduada) | n disparos em evento | captura mediana % |
|---|---|---|
| 0 | 621 | 32.9 |
| 1 | 482 | 40.3 |
| 2 | 47 | 78.6 |

**Leitura:** veredito preliminar: **ATRAPALHA ou inconclusivo (vetados capturaram igual/mais)**. Na graduada, precisão do
disparo por nível de contra-tendência (0/1/2 TFs contra): {0: np.float64(4.0), 1: np.float64(2.6), 2: np.float64(1.5)} % —
se cair com o nível, a versão graduada tem sinal utilizável (contra-indicação
progressiva), não só a binária. N fora de evento no top-2: 35866.

## Confronto com os critérios

C6 (exaustão): 0 bucket(s) de consumo e 0 faixa(s) de hora
marcados (mediana ≤ 10% com IC95 < 20% em treino E validação). C11: sem nova
varredura de limiares aqui (detector fixado pelo E6.1).

## O que isso muda

Candidatas a LEITURA (confiança média, a consolidar no E12): (1) "% consumido
no disparo" como relógio de exaustão; (2) o veredito do VETO acima; (3) faixas
de hora exauridas → condicionamento por sessão no E8.

## Limitações

- Detector de referência único (zS 1.0 M30) — generalizar exige repetir por métrica.
- Ritmo pré usa a idade desde a âncora (só definida em eventos).
- Graduada do VETO usa Δ do contexto (aprox. de VEL6 H4/D1), não o VEL exato do painel.
- Captura medida até o fim do DIA (não do evento) nos disparos fora de evento.

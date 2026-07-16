# E08 — Persistência e ciclos de sessão (Q8 + Q9)

## O que perguntamos

Quanta vida resta na tendência depois do alarme certo — e quanto custa o
atraso? Quanto tempo a força S persiste (half-life)? O dia-evento tem fases
reconhecíveis, e como o relógio das sessões governa nascimento e morte das
tendências?

## Como testamos

Banco M30/H1 (treino+validação; selado intocado), detector de referência
zS ≥ 1.0 no M30 (P3), 1º disparo válido por evento. Half-life por AR(1) em
S−50 (💡 φ = quanto de hoje sobra amanhã; half-life = ln½/lnφ). Fases por
regras no caminho da cesta (definições no cabeçalho do script), validadas por
k-means (k=4; ⚠ hmmlearn sem wheel p/ Python 3.14/Windows — HMM fica como
verificação opcional noutra máquina). Recortes N < 30 marcados.

## Resultados

### Q8a — vida restante após o 1º disparo válido e custo do atraso

| sessão do disparo | split | n | vida mediana (min) | vida mediana (ATRs) | custo +30min (p.p.) | custo +60min (p.p.) | obs |
|---|---|---|---|---|---|---|---|
| londres | treino | 42 | 450.0 | 0.85 | 7.1 | 12.5 |  |
| londres | validacao | 5 | 360.0 | 0.93 | 0.4 | 5.6 | amostra insuficiente |
| ny | treino | 4 | 150.0 | 0.54 | 20.1 | 21.8 | amostra insuficiente |
| ny | validacao | 1 | 90.0 | 0.1 | 7.7 | 4.1 | amostra insuficiente |
| toquio | treino | 235 | 900.0 | 1.04 | 2.4 | 4.7 |  |
| toquio | validacao | 29 | 960.0 | 1.05 | 2.3 | 5.6 | amostra insuficiente |

**Leitura:** quanto ainda há para capturar (tempo e ATRs) por sessão do
disparo — e o pedágio de entrar 30/60 min atrasado, em pontos percentuais da
magnitude já consumidos. Disparo cedo (Tóquio) deixa mais estrada; o atraso
custa mais onde o ritmo é rápido.

### Q8b — half-life da força S (horas)

| moeda | half-life M30 (h) | half-life H1 (h) |
|---|---|---|
| AUD | 1.6 | 0.8 |
| CAD | 1.6 | 0.7 |
| CHF | 1.5 | 0.7 |
| EUR | 1.4 | 0.7 |
| GBP | 1.5 | 0.7 |
| JPY | 1.6 | 0.8 |
| NZD | 1.6 | 0.8 |
| USD | 1.7 | 0.8 |

**Leitura:** meia-vida do desvio de S por moeda: quanto maior, mais a força é
"lenta" — janela maior para reagir, porém sinais mais raros. Diferenças entre
moedas orientam expectativa de duração por moeda no playbook.

### Q9a — persistência das fases por sessão (% de ficar na mesma fase)

| sessão | n barras | fica em expansão % | fica em clímax % | fica em exaustão % | fica em reversão % |
|---|---|---|---|---|---|
| londres | 4477 | 76.0 | 57.0 | 25.0 | 66.0 |
| ny | 2839 | 78.0 | 52.0 | 40.0 | 82.0 |
| toquio | 3825 | 81.0 | 56.0 | 22.0 | 68.0 |

**Leitura:** diagonal da matriz de transição (prob. de continuar na fase na
barra seguinte) por sessão. Pureza do k-means vs. fases-regra: **67.8%**
(💡 4 aglomerados achados sem supervisão coincidem com as fases desenhadas à
mão — as fases não são invenção da regra).

### Q9b — relógio: onde as tendências nascem × onde morrem

| nasce em ↓ / morre em → | madrugada/Tóquio (0–10h) | Londres (10–15h) | NY/fim (15–24h) |
|---|---|---|---|
| londres | 25 | 0 | 67 |
| ny | 5 | 0 | 1 |
| toquio | 36 | 11 | 178 |

**Leitura:** linha = sessão da âncora; coluna = faixa do extremo do dia.
**84.0%** das tendências nascidas em Tóquio só fazem o extremo depois
das 10h (Londres em diante) — a tendência de Tóquio costuma sobreviver à
troca de turno.

| weekday | eventos | magnitude_mediana |
|---|---|---|
| Monday | 37 | 1.11 |
| Tuesday | 56 | 1.21 |
| Wednesday | 68 | 1.24 |
| Thursday | 83 | 1.2 |
| Friday | 79 | 1.21 |

**Leitura:** sazonalidade por dia da semana (nº de eventos e magnitude
mediana em ATRs) — insumo de expectativa, não de sinal.

## Confronto com os critérios

Etapa descritiva: sem varredura nova de limiares (**C11** não exige BH aqui;
detector fixado pelo P3/E6). O gradiente de relógio corrobora o quase-**C6**
do E6.2 (exaustão pós-15h). N < 30 sinalizado nas tabelas, nunca omitido.

## O que isso muda

Candidatas a LEITURA (confiança média): (1) vida restante por sessão do
disparo + custo do atraso (regra prática de "vale entrar atrasado?"); (2)
half-life de S por moeda; (3) fases com validação não-supervisionada
(67.8% de pureza) e persistência por sessão; (4) sobrevivência
Tóquio→Londres. O E9 (combinações) fecha o Bloco C.

## Limitações

- Detector de referência único (zS 1.0 M30); vida/custo dependem dele.
- HMM não rodado neste ambiente (sem wheel) — k-means como validação; rodar
  hmmlearn na máquina Linux se quisermos a matriz de transição probabilística.
- Half-life por AR(1) simples (pares consecutivos; buracos viram pares a menos).
- "Quão cedo cada fase é reconhecível" (Q9) não coberto — fica para adendo/E9.

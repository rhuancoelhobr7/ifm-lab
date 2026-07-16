# E04a — Gabarito de eventos (as tendências que realmente aconteceram)

## O que perguntamos

Quais (moeda, dia) tiveram uma tendência diária de verdade — e ONDE ela começou?
Este catálogo é a régua contra a qual toda métrica do painel será cronometrada.

## Como testamos

Dia de negociação = abertura de Tóquio → fechamento de NY (janelas congeladas,
fuso IANA → hora do servidor DST europeu). Caminho da cesta em **M30** (régua
única 2021→fim da validação; decisão/adendo P2a de 2026-07-16), por par:
±log(preço/abertura de Tóquio) ÷ banda ATR14 diária; cesta = média dos 7 pares.
Evento = |cesta no fim| ≥ 1.0 ATR E ≥ 6/7 pares na direção E
eficiência de Kaufman ≥ 0.3 (💡 ver *razão de eficiência* no ESBOÇO §1.1).
Âncoras candidatas: **A-20/10** (💡 "ponto sem retorno": atinge 20% da magnitude
final e nunca mais recua abaixo de 10%) e **A-rompimento** (💡 último cruzamento
do nível de abertura — depois dele o caminho não volta ao zero). O teste selado
(2025-10+) NÃO foi tocado.

## Resultados

| estatística | valor |
|---|---|
| dias de negociação válidos | 1198 |
| eventos | 323 |
| eventos/dia | 0.27 |
| % dias com ≥1 evento | 20% |
| magnitude mediana (ATRs) | 1.20 |
| duração mediana A-20/10→fim (min) | 690 |
| eficiência mediana | 0.44 |
| % eventos 7/7 pares | 90% |

**Leitura:** o tamanho e a cara do gabarito: quantos eventos existem, o quão
grandes e diretos são. Eventos/dia perto de 1–2 é o esperado pela Premissa P1
(pouca coisa por dia realmente tende); mediana de magnitude ≥ 1 ATR por
construção.

| moeda | eventos |
|---|---|
| AUD | 42 |
| CAD | 24 |
| CHF | 39 |
| EUR | 23 |
| GBP | 31 |
| JPY | 74 |
| NZD | 29 |
| USD | 61 |

**Leitura:** distribuição por moeda — se alguma moeda concentrar eventos demais
(ou de menos), é sinal de banda ATR mal calibrada para ela, não de "moeda que
tende mais"; conferir na auditoria.

| sessão da âncora A-20/10 | eventos que nascem nela |
|---|---|
| londres | 92 |
| ny | 6 |
| toquio | 225 |

**Leitura:** em que sessão a tendência do dia costuma NASCER (pela âncora
A-20/10). Insumo direto da Premissa P2 (a sessão é a unidade de operação).

| âncora | % dos eventos com âncora definida | hora mediana (servidor) |
|---|---|---|
| A-20/10 | 100% | 10.0 |
| A-rompimento | 100% | 4.0 |

**Leitura:** cobertura e horário típico de cada âncora candidata. Âncora sem
definição em muitos eventos = regra frágil; horários muito tardios = âncora
que "chega depois da festa".

| estatística | A-20/10 M30 × M15 |
|---|---|
| N dias-evento comparáveis | 45 |
| mediana |Δâncora| (min) | 15 |
| p90 |Δâncora| (min) | 33 |
| % com |Δ| ≤ 30 min (1 candle M30) | 89% |

**Leitura:** custo da régua M30: nos dias 2024-07+ em que as duas resoluções
detectam o mesmo evento, a âncora A-20/10 muda pouco (|Δ| ≤ 1 candle M30 na
grande maioria) → a régua única M30 não distorce a medição de latência.

## Amostras para a auditoria C2 (👤)

20 dias-evento sorteados (seed 20260715) em `results/E04a_amostras/`:
caminho da cesta com as DUAS âncoras marcadas, linhas de 10%/20% da magnitude e
faixas das sessões. Pergunta única da auditoria: **"é aqui que um trader diria
que a tendência começou?"** — responda por âncora, em ≥ 80% dos casos.

**Leitura:** a auditoria visual é o critério C2: quem valida a régua é o olho
de trader do dono da pesquisa, não a estatística.

## Confronto com os critérios

**C2** exige: 20 dias sorteados, aprovação ≥ 80% numa das âncoras, com no
máximo 3 rodadas (novo sorteio a cada rodada). Situação: **⏳ aguardando a
auditoria 👤** — este relatório prepara o portão P2a, não o fecha.

## O que isso muda

Com o C2 aprovado, a âncora escolhida congela no config.yaml e o banco-mãe
(E4b) é construído sobre ela. Reprovou → ajustar definição/âncora e re-sortear
(nunca reaproveitar os mesmos 20 dias).

## Limitações

- O gabarito olha o dia inteiro DE PROPÓSITO (é régua, não sinal) — nunca vira feature.
- Régua M30 uniforme: âncoras têm quantização de ±30 min (sensibilidade M15 acima).
- Dias com <80% das barras na janela (feed/feriado) ficam fora — reportados como inválidos.
- Eventos do período selado não foram computados; serão gerados no E11 com a
  definição congelada.

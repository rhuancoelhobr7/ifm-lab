# Guia Completo — IFM (Índice de Força da Moeda) v1.0

> **Arquivo:** `IFM.mq5` · **Tipo:** Indicador MetaTrader 5 (subjanela) · **Nome interno:** *IFM*

Este documento mapeia **toda** a arquitetura do indicador: o que ele calcula, como calcula, o que aparece na tela e o que cada número significa. Conceitos complexos vêm sempre acompanhados de uma **💡 interpretação fácil**.

---

## Índice

1. [Visão geral — o que o indicador é](#1-visão-geral)
2. [Arquitetura em blocos](#2-arquitetura-em-blocos)
3. [Inputs (parâmetros configuráveis)](#3-inputs)
4. [Constantes internas (`#define`)](#4-constantes-internas)
5. [Outputs — buffers de dados](#5-outputs--buffers)
6. [O núcleo IFM: os "5 juízes"](#6-o-núcleo-ifm-os-5-juízes)
7. [O Motor ML (par ativo)](#7-o-motor-ml-par-ativo)
8. [IFM Light — a versão para qualquer par](#8-ifm-light)
9. [Força da moeda (agregação G8)](#9-força-da-moeda-agregação-g8)
10. [Vista MÉTRICAS — coluna por coluna](#10-vista-métricas)
11. [Matriz 8x8](#11-matriz-8x8)
12. [Barra superior, botões e Replay](#12-barra-superior-botões-e-replay)
13. [Fluxo de eventos e ciclo de vida](#13-fluxo-de-eventos-e-ciclo-de-vida)
14. [Caches e desempenho](#14-caches-e-desempenho)
15. [Mapa de funções (referência rápida)](#15-mapa-de-funções)
16. [Glossário](#16-glossário)

---

## 1. Visão geral

O IFM responde a duas perguntas ao mesmo tempo:

1. **"Quais moedas do G8 estão fortes e quais estão fracas agora?"** — respondida pelo **painel visual** (vista Métricas + Matriz 8x8), que varre *todos* os pares detectados entre USD, EUR, GBP, JPY, CHF, CAD, AUD e NZD em 6 timeframes (M5 a D1).
2. **"O par do gráfico atual está com viés de alta ou de baixa, e com quanta qualidade?"** — respondida pelo **Motor ML**, que roda barra a barra no símbolo do gráfico e preenche 4 buffers numéricos (IFM, ML_RSI, Rank, Conf).

> 💡 **Interpretação fácil:** pense no indicador como duas ferramentas coladas. Uma é um "placar de campeonato" das 8 moedas (quem está ganhando de quem, em vários prazos). A outra é um "assistente de memória" que olha o par que você está operando e pergunta: *"das vezes no passado em que o mercado se parecia com agora, o que aconteceu depois?"*.

O indicador **não desenha linhas** na subjanela (todos os plots são `DRAW_NONE`): a subjanela é usada como uma *tela* onde o painel é desenhado com objetos gráficos (retângulos e labels). Os buffers existem para que os valores fiquem visíveis na Janela de Dados (Data Window) e acessíveis a outros programas via `iCustom`.

---

## 2. Arquitetura em blocos

```
┌────────────────────────────────────────────────────────────────────┐
│                            IFM.mq5                                 │
│                                                                    │
│  ┌──────────────────────────┐   ┌───────────────────────────────┐  │
│  │  MOTOR ML (par ativo)    │   │  PAINEL MULTI-MOEDA (G8)      │  │
│  │  roda em OnCalculate     │   │  roda em OnTimer/Compute      │  │
│  │                          │   │                               │  │
│  │  RSI + 8 features        │   │  IFM Light por par/TF         │  │
│  │  Banco de memória (kNN)  │   │  → força S por moeda (0-100)  │  │
│  │  Pesos Fisher (auto)     │   │  → série histórica (ring 64)  │  │
│  │  Supertrend adaptativo   │   │  → métricas: vel, zvel, zS,   │  │
│  │  Rank & Confidence       │   │    acel, zMov, zHist, cesta,  │  │
│  │  5 juízes → IFM 0-100    │   │    MTF, VETO, candidata       │  │
│  │                          │   │  → Matriz 8x8 (heatmap)       │  │
│  │  Saída: 4 buffers        │   │  Saída: objetos gráficos      │  │
│  └──────────────────────────┘   └───────────────────────────────┘  │
│                                                                    │
│  UI compartilhada: topbar, botões, replay, abas de timeframe        │
└────────────────────────────────────────────────────────────────────┘
```

As duas metades compartilham a mesma fórmula-mãe (o "IFM de 5 juízes"), mas em versões diferentes:

| | Motor ML (par ativo) | IFM Light (todos os pares) |
|---|---|---|
| Juízes usados | 5 (Pivot, MP, MFC, ML-RSI, CCI) | 4 (sem o juiz ML-RSI) |
| Fonte de dados | Buffers de indicadores nativos do gráfico | `CopyRates` (60 barras por par/TF) |
| Escala bruta | ±21 → normalizado 0-100 | ±15 → normalizado 0-100 |
| Custo | Alto (roda 1x por par) | Leve (roda para ~28 pares × 6 TFs) |

---

## 3. Inputs

### Grupo "ML Brain (Par Ativo)" — controla o motor de memória

| Input | Padrão | O que faz |
|---|---|---|
| `InpRSILength` | 14 | Período do RSI base. Dele derivam um RSI rápido (metade, mín. 2) e um lento (dobro). |
| `InpMemoryDepth` | 400 | Tamanho do banco de memória: quantas "fotos do mercado" passadas o motor guarda (barras). |
| `InpKNeighbors` | 8 | O **k** do kNN: quantos momentos passados mais parecidos com o atual são consultados. |
| `InpATRFactor` | 0.5 | Sensibilidade do aprendizado: um movimento futuro só conta como "alta/baixa relevante" se passar de `0.5 × ATR`. |
| `InpAutoOptimize` | true | Liga a auto-otimização dos pesos das 8 features via critério de Fisher. |
| `InpAdaptSpeed` | 1.0 | Velocidade com que os pesos auto-otimizados convergem para o alvo (1.0 = imediato). |
| `InpGateRank` | 60 | Rank mínimo para o juiz ML valer pontuação forte (±2 em vez de ±1). |
| `InpGateConf` | 50 | Confidence mínima para o juiz ML valer pontuação forte. |

> 💡 **Interpretação fácil:** o "ML Brain" é um caderno com 400 páginas. Cada página tem uma foto do mercado (8 números) e a anotação "o que aconteceu 4 barras depois". Quando chega uma barra nova, o motor folheia o caderno, acha as 8 páginas mais parecidas com o momento atual e vota: *"na maioria das vezes parecidas com essa, o preço subiu (ou caiu)"*.

### Grupo "IFM Modules" — períodos dos juízes clássicos

| Input | Padrão | O que faz |
|---|---|---|
| `InpCCILength` | 20 | Período do CCI (juiz 5) e da janela do z-score no modo IFM-Z. |
| `InpMFCVolLength` | 20 | Janela da média de volume usada pelo juiz MFC. |
| `InpEMAFallbackLen` | 21 | Período da EMA que simula o "Market Profile" (juiz 2). |

### Grupo "Painel" — aparência e atualização

| Input | Padrão | O que faz |
|---|---|---|
| `InpFont` | 9 | Tamanho da fonte da topbar. |
| `InpShowMatrix` | true | Mostra/oculta a Matriz 8x8 ao lado da tabela de métricas. |
| `InpRefreshSec` | 60 | Intervalo do auto-refresh do painel (mínimo efetivo: 10 s). |

### Grupo "Metricas (V2)" — parâmetros das colunas da tabela

| Input | Padrão | O que faz |
|---|---|---|
| `InpMetVelK` | 6 | O **k** da velocidade/aceleração: VEL = quanto a força S mudou nas últimas *k* barras. |
| `InpMetPersN` | 12 | N de persistência/eficiência (reservado; não usado no render atual). |
| `InpMetThrVel` | 17.6 | Limiar de destaque de \|VEL\| (calibrado no percentil 75 da fase de pesquisa "F3"). |
| `InpMetThrPers` | 0.58 | Limiar de PERS (reservado, idem acima). |
| `InpMetThrCesta` | 5 | Mínimo de pares confirmando (de 7) para a moeda ser candidata. |
| `InpMetThrMTF` | 2 | Mínimo de timeframes alinhados (de 4: M30/H1/H4/D1) para candidata. |

### Grupo "Z-Score (variante exploratória)" — o "Z" do IFM-Z

| Input | Padrão | O que faz |
|---|---|---|
| `InpZCore` | true | **Liga o núcleo IFM-Z**: o juiz CCI vira um z-score contínuo (ver §8), removendo a quantização da força. |
| `InpZVelN` | 32 | Janela usada para estimar o desvio-padrão dos passos de S (para o `zvel`). |
| `InpZThrVel` | 2.0 | Limiar de destaque de \|zvel\| (dourado + critério de candidata). |
| `InpZThrS` | 1.0 | Limiar de destaque de \|zS\| (z transversal da força). |
| `InpZMovN` | 20 | Quantos dias entram no z histórico do movimento diário (zHist). |

---

## 4. Constantes internas

Valores fixos no código (não configuráveis pelo usuário):

| Constante | Valor | Significado |
|---|---|---|
| `LIGHT_WINDOW` | 60 | Barras usadas em cada cálculo do IFM Light. |
| `IFM_STRONG` / `IFM_WEAK` | 65 / 35 | Referências de força/fraqueza (limiares conceituais do IFM). |
| `TOPBAR_H` | 30 px | Altura da faixa de botões no topo. |
| `STEP_LEN` | 3 | Passo (em barras) para medir inclinação do RSI. |
| `WIN_LEN` | 100 | Janela de normalização das features (min-max e percentil). |
| `HORIZON_BARS` | 4 | Horizonte do aprendizado: o "resultado" de uma foto é o movimento 4 barras à frente. |
| `SPACING_BARS` | 4 | O kNN só examina 1 a cada 4 linhas do banco (evita vizinhos redundantes/colados). |
| `TREND_LEN` | 50 | Período da EMA lenta usada na medida de força de tendência. |
| `CHOP_CUT` | 0.5 | Abaixo disso a distância EMA5–EMA50 (em ATRs) marca mercado "picotado" (chop). |
| `VOL_BAND_LO/HI` | 20 / 85 | Faixa saudável do percentil de ATR (volatilidade nem morta nem explosiva). |
| `AUTO_FLOOR` | 0.5 | Peso mínimo de qualquer feature na auto-otimização. |
| `AUTO_MIN_ROWS` | 60 | Linhas mínimas no banco antes de otimizar pesos. |
| `SMOOTH_LEN` | 10 | Período da EMA que suaviza a convicção do kNN. |
| `BANK_COLS` | 9 | Colunas por linha do banco: 8 features + 1 resultado. |
| `ST_ATR_LEN` / `ST_MULT_BASE` | 10 / 1.5 | ATR e multiplicador base do Supertrend adaptativo. |
| `MET_TFN` | 6 | Timeframes do painel: M5, M15, M30, H1, H4, D1. |
| `MET_RING` | 64 | Tamanho do histórico de força S por moeda/TF (64 pontos; índice 63 = agora). |
| `MET_MAXP` | 32 | Máximo de pares processados no rebuild das métricas. |
| `TF_M30_IDX…TF_D1_IDX` | 2…5 | Índices fixos de M30/H1/H4/D1 usados por MTF, VETO e rank. |

---

## 5. Outputs — buffers

O indicador declara 4 buffers, todos `DRAW_NONE` (invisíveis como linha, mas presentes na Janela de Dados e legíveis via `iCustom`):

| # | Buffer | Nome | Escala | O que é |
|---|---|---|---|---|
| 0 | `IFMBuf` | **IFM_ML** | 0–100 | IFM completo do par ativo (5 juízes). >50 = pressão compradora; <50 = vendedora. Referências: ≥65 forte, ≤35 fraco. |
| 1 | `MLRSIBuf` | **ML_RSI** | 0–100 | RSI base "inclinado" pelo motor ML (tilt de até ±18 pontos, proporcional à convicção × rank), suavizado por EMA(3). |
| 2 | `RankBuf` | **Rank** | 0–100 | Nota de qualidade do *setup* atual (contexto: tendência, volatilidade, estrutura…). |
| 3 | `ConfBuf` | **Conf** | 0–100 | Confiança no *sinal* do kNN (concordância e proximidade dos vizinhos). |

> 💡 **Interpretação fácil:** IFM diz **para onde** o mercado pende; Rank diz **se o ambiente é bom** para agir nessa direção; Conf diz **quanto o "caderno de memória" tem certeza**. Um IFM alto com Rank e Conf baixos é um palpite fraco; os três altos juntos é o cenário raro e valioso.

Além dos buffers, todos os elementos visuais (tabela, matriz, botões) são **objetos gráficos** desenhados na subjanela — descritos nas seções 10–12.

---

## 6. O núcleo IFM: os "5 juízes"

O IFM do par ativo é um **placar ponderado de 5 módulos independentes** ("juízes"). Cada juiz vota entre −2 e +2 (o CCI-Z vota contínuo), o placar é ponderado e reescalado para 0–100:

```
bruto = Pivot×2 + MarketProfile×2 + MFC×1 + ML-RSI×3 + CCI×3     (faixa: −21 … +21)
IFM   = (bruto + 21) / 42 × 100                                   (faixa: 0 … 100)
```

> 💡 **Interpretação fácil:** cinco analistas olham o mesmo gráfico por ângulos diferentes e dão notas de −2 (muito vendedor) a +2 (muito comprador). Os dois analistas mais confiáveis (ML e CCI) têm voto que vale 3×; o de volume (MFC) vale 1×. A média final vira uma nota de 0 a 100 onde 50 é neutro.

### Juiz 1 — Pivot Points (`CalcPivotScore`, peso 2)

Usa o pivô clássico da barra anterior: `PP = (H+L+C)/3`, `R1 = 2·PP − L`, `S1 = 2·PP − H`.

| Condição do fechamento atual | Voto |
|---|---|
| Acima de PP **e** acima de R1 | +2 |
| Acima de PP | +1 |
| Abaixo de PP **e** abaixo de S1 | −2 |
| Abaixo de PP | −1 |
| Exatamente em PP | 0 |

> 💡 Onde o preço está em relação ao "ponto de equilíbrio de ontem"? Acima do teto de referência = compradores dominando.

### Juiz 2 — Market Profile via EMA fallback (`CalcMPScore`, peso 2)

Não há Market Profile real; o código o **aproxima** com uma EMA(21):
`POC ≈ EMA21`, `VAH = POC × 1.01`, `VAL = POC × 0.99` (banda de ±1%).

| Condição | Voto |
|---|---|
| Fecha acima da VAH **e** EMA subindo | +2 |
| Fecha acima da VAH | +1 |
| Fecha abaixo da VAL **e** EMA caindo | −2 |
| Fecha abaixo da VAL | −1 |
| Dentro da banda | 0 |

> 💡 O preço "escapou para cima ou para baixo" da zona de valor onde ele costuma negociar? Escapar com a média a favor vale nota cheia.

### Juiz 3 — MFC / Market Facilitation (`CalcMFCScore`, peso 1)

MFC de Bill Williams: `MFC = (High − Low) / Volume` — quanto de "andamento de preço" cada unidade de volume comprou. Compara MFC atual vs. anterior e volume atual vs. média de `InpMFCVolLength` barras:

| MFC subiu? | Volume acima da média? | Voto | Leitura clássica |
|---|---|---|---|
| Sim | Sim | +1 | "Green" — mercado facilitado, movimento saudável |
| Não | Sim | −1 | "Squat" — muito volume, pouco avanço: briga/absorção |
| Sim | Não | 0 | "Fake" — anda sem volume, desconfiar |
| Não | Não | 0 | "Fade" — mercado desinteressado |

(A variável `mfcColor` codifica essas 4 categorias: 0=green, 1=squat, 2=fake, 3=fade.)

> 💡 Cada ponto de movimento "custou" muito ou pouco volume? Se o preço anda fácil com volume presente, o movimento é sincero.

### Juiz 4 — ML-RSI (`CalcMLRSIScore`, peso 3)

É a ponte entre o motor ML (§7) e o placar:

| Condição | Voto |
|---|---|
| Viés kNN de alta **e** Rank ≥ `InpGateRank` **e** Conf ≥ `InpGateConf` | +2 |
| Viés kNN de alta (sem os portões) | +1 |
| Viés de baixa com portões cumpridos | −2 |
| Viés de baixa sem portões | −1 |
| Sem viés | 0 |

> 💡 O voto forte (±2) só sai quando o "caderno de memória" aponta uma direção **e** o contexto (Rank) **e** a certeza (Conf) passam nos filtros mínimos.

### Juiz 5 — CCI (`CalcCCIScore`, peso 3)

CCI(20) sobre o preço típico:

| Condição | Voto |
|---|---|
| CCI > +100 | +2 |
| 0 < CCI ≤ +100 | +1 |
| CCI < −100 | −2 |
| −100 ≤ CCI < 0 | −1 |
| CCI = 0 | 0 |

> 💡 O preço está esticado acima ou abaixo do seu "normal" recente? Acima de +100 é impulso comprador claro.

---

## 7. O Motor ML (par ativo)

Roda em `OnCalculate`, barra a barra, apenas no símbolo do gráfico. É um pipeline de 7 estágios:

### 7.1 As 8 features (a "foto do mercado")

Cada barra vira um vetor de 8 números, todos normalizados para ~0–1 (janela `WIN_LEN = 100` barras):

| # | Feature | Fórmula | O que captura |
|---|---|---|---|
| 0 | `fVal` | RSI/100 | Nível do RSI |
| 1 | `fSlp` | min-max de (RSI − RSI 3 barras atrás) | Velocidade do RSI |
| 2 | `fAcc` | min-max da variação da velocidade | Aceleração do RSI |
| 3 | `fMid` | \|RSI − 50\| / 50 | Distância do neutro (esticamento) |
| 4 | `fPct` | percentil do RSI na janela | RSI está alto/baixo *para os padrões recentes*? |
| 5 | `fChn` | min-max do desvio-padrão do RSI(14) | Nervosismo/agitação do oscilador |
| 6 | `fSpr` | min-max de (RSI rápido − RSI lento) | Divergência entre prazos curtos e longos |
| 7 | `fReg` | min-max de (EMA20 do RSI − 50) | Regime: mercado morando acima ou abaixo do neutro |

Funções auxiliares: `Scale01` (min-max na janela), `PercentRank` (percentil), `CalcStdev` (desvio-padrão populacional).

> 💡 **Interpretação fácil:** em vez de guardar o gráfico inteiro, o motor tira uma "digital" de 8 números que descreve o humor do RSI: nível, velocidade, aceleração, esticamento, contexto, nervosismo, divergência e regime.

### 7.2 O banco de memória (feature bank)

Estrutura circular (`g_bank`) com `InpMemoryDepth` linhas × 9 colunas (8 features + resultado). Operações: `BankInit`, `BankPush`, `BankGetRow` (índice lógico 0 = linha mais recente).

**Rotulagem (`ClassifyOutcome`):** a foto tirada na barra `i − 4` só é arquivada quando a barra `i` fecha, com a etiqueta do movimento realizado nesses 4 candles, medido em bandas de ATR (`band = InpATRFactor × ATR14`):

| Movimento em 4 barras | Etiqueta |
|---|---|
| > +2 bandas | +3 |
| > +1 banda | +2 |
| > 0 | +1 |
| < −2 bandas | −3 |
| < −1 banda | −2 |
| < 0 | −1 |

> 💡 O motor nunca arquiva uma foto sem saber "o final da história". Ele espera 4 barras, mede o que aconteceu (em unidades de volatilidade, para funcionar igual em mercado calmo ou agitado) e só então cola a foto no caderno com a etiqueta do resultado. Isso evita trapaça de olhar o futuro (*look-ahead bias*).

### 7.3 Pesos de Fisher (`ComputeFisherWeights`)

Se `InpAutoOptimize` está ligado e o banco tem ≥60 linhas rotuladas, cada feature ganha um **score de Fisher**:

```
Fisher(j) = (média_altistas(j) − média_baixistas(j))² / (var_altistas(j) + var_baixistas(j))
```

O score é normalizado pelo maior, escalado ×10 com piso 0.5, e o peso atual desliza em direção ao alvo na velocidade `InpAdaptSpeed`.

> 💡 **Interpretação fácil:** o motor pergunta, feature por feature: *"você fica visivelmente diferente quando o mercado vai subir vs. quando vai cair?"*. Quem separa bem os dois grupos ganha peso maior na hora de comparar fotos; quem não separa nada fica com o peso mínimo (nunca zero, para não descartar informação de vez).

### 7.4 Busca kNN + votação (`RunKNN`, `GapTo`)

- **Distância:** `gap = Σ peso(j) × log(1 + |Δfeature(j)|)` — a compressão logarítmica (`Compress`) evita que uma feature discrepante domine tudo.
- **Varredura:** examina o banco até `InpMemoryDepth`, pulando de 4 em 4 (`SPACING_BARS`) para não pegar vizinhos praticamente idênticos e consecutivos.
- **Vizinhos:** mantém os `InpKNeighbors` de menor gap.
- **Voto ponderado:** cada vizinho vota sua etiqueta (−3…+3) com peso `1/(1+gap)` — vizinhos mais parecidos falam mais alto.

Saídas (struct `SEngine`):

| Campo | Significado |
|---|---|
| `analogScore` | Voto médio ponderado (−3…+3 teórico). |
| `biasDir` | Direção: +1 se score > 0.15, −1 se < −0.15, 0 na zona morta. |
| `agreeFrac` | Fração do peso total que votou na direção vencedora (0–1). |
| `gapTight` | Quão "coladas" as analogias estão (1 = passado quase idêntico ao presente). |
| `k` | Quantos vizinhos foram efetivamente encontrados. |

> 💡 É a máquina de "isso me lembra aquela vez": acha os 8 momentos mais parecidos, deixa os mais parecidos falarem mais alto, e resume em: direção (`biasDir`), unanimidade (`agreeFrac`) e semelhança (`gapTight`).

### 7.5 Supertrend adaptativo

Um Supertrend (ATR 10, multiplicador base 1.5) cujo multiplicador **abre e fecha conforme a convicção do ML**:

```
mlDrive   = 0.5×|convicção suavizada| + 0.3×gapTight + 0.2×agreeFrac   (0–1)
se chop: mlDrive ×= 0.35
multiplicador = 1.5 × (1 + (1 − mlDrive))     →  de 1.5 (ML confiante) a 3.0 (ML perdido)
```

Chop é declarado quando `|EMA5 − EMA50| / ATR14 < 0.5`.

> 💡 É um trilho de tendência com folga elástica: quando o ML está confiante, o trilho cola no preço (vira rápido); quando o ML está confuso ou o mercado está picotado, o trilho se afasta (evita ser chacoalhado por ruído).

### 7.6 Contexto, stance e proteções

Por barra, o motor levanta flags de contexto:

- `trendAligned` — o viés do kNN concorda com a direção do Supertrend;
- `volHealthy` — percentil do ATR14 entre 20 e 85 (volatilidade nem morta, nem em pânico);
- `chopRaw` — mercado lateral picotado;
- `slopeFit` — inclinação do RSI concorda com o viés;
- `stretched` — RSI > 70 comprando ou < 30 vendendo (perseguindo esticado);
- `oscReg` / `oscSmoothUp` — regime (EMA20 do RSI) e micro-momentum (EMA5 subindo);
- **Stance** (`g_stanceState`): a "postura" assumida (+1/−1) quando viés + tendência + volatilidade + não-chop se alinham; `g_stanceAge` conta há quantas barras ela dura; `earlyFlip` marca viradas de postura com menos de 4 barras (sinal instável).

### 7.7 Rank e Confidence

**Rank (`RankScore`, 0–100)** — nota do *setup*, soma de parcelas:

| Parcela | Máx. | Critério |
|---|---|---|
| Concordância dos vizinhos | 25 | `25 × agreeFrac` |
| Proximidade das analogias | 15 | `15 × gapTight` |
| Estrutura | 15 | +10 se inclinação do RSI concorda; +5 se não está esticado |
| Tendência | 10 | Supertrend a favor |
| Volatilidade | 10 | 10 saudável / 5 morta / 3 excessiva |
| Regime | 10 | Regime do RSI casa com o viés (10), neutro (4), contra (6) |
| Suavidade | 5 | Micro-momentum a favor |
| Persistência | 5 | +1 por barra de stance (até 5) |
| **Penalidades** | −20 | chop (−8), esticado (−6), virada precoce (−6), vizinhos faltando (até −5) |

**Confidence (`ConfScore`, 0–100)** — certeza no *sinal*:

```
Conf = 40×agreeFrac + 25×gapTight + 15×min(1, idade/5) + 10×slopeFit
       − 15×(virada precoce) − até 10×(vizinhos faltando)
```

> 💡 **Rank** = "a pista está boa para correr?" (ambiente). **Conf** = "o navegador tem certeza do caminho?" (sinal). São notas independentes de propósito diferente — por isso os dois portões (`InpGateRank`, `InpGateConf`) precisam passar juntos para o juiz ML dar voto forte.

### 7.8 ML RSI (buffer 1)

```
intensity = EMA3(Rank) / 100
tilt      = convicção_suavizada × intensity × 18      (−18 … +18 pontos)
ML_RSI    = EMA3( clamp(RSI + tilt, 0, 100) )
```

> 💡 É o RSI comum "empurrado" na direção que o ML acredita, com força proporcional à qualidade do momento. Se o ML vê alta com rank 80, o RSI aparece ~14 pontos mais alto do que o cru.

---

## 8. IFM Light

Versão econômica do IFM usada pelo painel para **qualquer par/TF/deslocamento**, sem criar handles de indicador. Funções: `CalcIFMLight` (copia 60 barras via `CopyRates`) e `CalcIFMLightAt` (calcula num índice arbitrário de um array já copiado — essencial para o rebuild em lote, §14).

Diferenças para o IFM completo:

- **4 juízes** (não há motor ML por par): Pivot×2 + MP×2 + MFC×1 + CCI×3 → bruto ±15 → `IFM = (bruto+15)/30×100`;
- EMA e CCI calculados **manualmente** a partir das barras copiadas (`EmaFromRates`, `CciFromRates`);
- Janela limitada a `LIGHT_WINDOW = 60` barras (paridade declarada com o `src/metrics.py` da pesquisa V2);
- Se faltam dados, devolve 50 (neutro) — e o chamador trata janela incompleta como NaN.

### O núcleo Z (`InpZCore = true`) — o que muda no "IFM-Z"

No modo clássico, o juiz CCI vota em degraus (−2, −1, +1, +2). No modo Z, ele é substituído por um **z-score contínuo do preço típico** (`TpZScore`):

```
z = (TP_atual − média(TP, 20)) / desvio_padrão(TP, 20)      clampado em ±2
```

> 💡 **Interpretação fácil:** em vez de um juiz que só sabe dizer "ruim/regular/bom/ótimo", entra um juiz que dá nota com casas decimais. Como esse juiz pesa 3 num placar de ±15, sua continuidade "descongela" a força S: sem ele, S só assumia valores em saltos de ~0.476 ponto (quantização); com ele, S varia suavemente — o que torna estatísticas como velocidade e z-score muito mais bem-comportadas.

---

## 9. Força da moeda (agregação G8)

### Detecção de pares (em `OnInit`)

O indicador varre **todos os símbolos do broker** e seleciona os que têm base e cotação dentro do G8 (USD, EUR, GBP, JPY, CHF, CAD, AUD, NZD), deduplicando por combinação (fica o primeiro símbolo encontrado de cada dupla — cobre sufixos de broker como `EURUSD.m`). Com todos disponíveis: **28 pares**, 7 por moeda (`g_cnt`).

### Fórmula da força S (`ComputeCurrencyStrength` / `MetRebuild`)

Para cada par: `dir = (IFM_par − 50) / 50` → um número de −1 (base fraca) a +1 (base forte). A direção é **creditada à moeda base e debitada da moeda cotada**:

```
S(moeda) = 50 + média(dir sobre os pares da moeda) × 50        (0–100)
```

> 💡 **Interpretação fácil:** cada par é uma "partida" entre duas moedas. O IFM do par diz quem está ganhando aquela partida e por quanto. A força S de uma moeda é a média dos seus 7 placares: EUR com S = 70 significa que, na média dos 7 jogos do EUR, ele está claramente ganhando.

**Regra de integridade (vista Métricas):** se *qualquer* par de uma moeda estiver sem dados, o S daquela moeda naquele ponto vira `EMPTY_VALUE` (NaN) — o painel **nunca imputa neutro**, e o NaN se propaga para todas as métricas derivadas (vel, zvel etc.). É preferível mostrar "—" a mostrar um número contaminado.

---

## 10. Vista MÉTRICAS

A tabela principal (esquerda do painel). Mantém, por moeda × TF, um **ring de 64 valores de S** (`g_metS`, índice 63 = barra fechada mais recente). Abas M5/M15/M30/H1/H4/D1 trocam o TF exibido. Linhas ordenadas por S decrescente (NaN por último), com zebra e fundo verde/vermelho quando a moeda é **candidata** (ver abaixo).

### As colunas, uma a uma

| Coluna | Cálculo | Como ler |
|---|---|---|
| **#** | Posição na ordenação da aba atual | 1 = mais forte no TF exibido. |
| **moeda** | — | Código com cor fixa (USD lima, EUR azul, GBP vermelho, JPY magenta, CHF prata, CAD laranja, AUD dourado, NZD ciano). |
| **força** | S no t0 + seta ▲/▼ + mini-barra | 0–100; >50 forte (verde), <50 fraca (vermelho). Barra proporcional a \|S−50\|. |
| **zS** | `(S − média_das_8) / desvio_das_8` no TF atual | Z **transversal**: quão fora da manada essa moeda está *agora*. ±1 já é destaque (`InpZThrS`). |
| **vel** | `S(t0) − S(t0−k)`, k=`InpMetVelK`(6) | Velocidade: quanto a força mudou nas últimas 6 barras do TF. |
| **zvel** | `vel / (σ(ΔS) × √k)`, σ sobre `InpZVelN`(32) passos | Velocidade **normalizada como passeio aleatório**: ≥2.0 (dourado) significa "esse deslocamento teria ~5% de chance de ser só ruído". |
| **acel** | `[S(t0)−S(t0−k)] − [S(t0−k)−S(t0−2k)]` + ↑/↓ | O movimento está ganhando (↑) ou perdendo (↓) gás. |
| **zMov** | Z transversal do movimento do dia em ATRs (`g_metZMov`) | Quem mais andou **hoje** (desde 00:00) em relação às outras moedas. ★ dourada = líder absoluto do dia. |
| **zHist** | Z do movimento de hoje vs. os mesmos horários dos últimos `InpZMovN`(20) dias (`g_metZMovH`) | O dia de hoje é normal ou excepcional **para essa própria moeda**? ≥2 vira dourado. |
| **cesta** | Pares confirmando o lado de S / total (ex.: `6/7`) | Unanimidade da cesta: 7/7 = todos os 7 pares concordam com a direção da moeda. |
| **mtf** | ▲▲▲△ — TFs (M30/H1/H4/D1) alinhados com o lado do H1 | Setas cheias = TFs concordando; ocas = não. ✕ vermelho = VETO ativo. |

> 💡 **zvel, o conceito-chave:** a força S sempre balança um pouco. O `zvel` pergunta: *"esse balanço das últimas 6 barras é grande comparado ao balanço típico?"*. Ele divide o deslocamento pelo "ruído esperado" (o desvio-padrão dos passos × √k, que é como ruído puro se acumula). zvel = 2 significa um movimento 2 desvios acima do esperado por acaso — provável movimento *de verdade*.

> 💡 **zMov vs. zHist:** zMov compara a moeda **com as irmãs** ("quem correu mais hoje?"); zHist compara a moeda **com ela mesma** ("hoje está sendo um dia atípico para ela?"). O zHist é medido *até a mesma hora do dia* em cada dia passado — comparar as 10h de hoje com dias completos seria injusto. Ambos medem o movimento em ATRs diários (log-retorno ÷ ATR14/preço), tornando moedas de volatilidades diferentes comparáveis.

### Cálculo detalhado do zMov/zHist (`MetRebuild`, bloco final)

1. Âncora: última barra M30 fechada; `tod` = segundos decorridos do dia até o *fechamento* dessa barra.
2. Para cada par e cada dia `i` (0 = hoje, 1…N passados): retorno logarítmico entre 00:00 e `00:00 + tod`, dividido pelo ATR14 diário relativo → `r`.
3. `r` é creditado/debitado nas duas moedas do par (mesma lógica do S). Falta de dado em qualquer par macula o dia (`badDay`).
4. **zHist**: z do valor de hoje contra a média/σ dos dias passados válidos (exige ≥10 dias).
5. **zMov**: z do valor de hoje contra a média/σ **das 8 moedas hoje** (exige ≥4 moedas válidas).

### Candidata (destaque de linha verde/vermelho)

Uma moeda é marcada candidata (a operação a favor do seu lado) quando **todas** as condições valem:

```
|zvel| ≥ InpZThrVel (2.0)      → movimento estatisticamente relevante
|zS|   ≥ InpZThrS (1.0)        → já descolada do grupo
cesta  ≥ InpMetThrCesta (5 de 7) → maioria clara dos pares confirmando
mtf    ≥ InpMetThrMTF (2 de 4)   → multi-timeframe minimamente alinhado
VETO   desligado                 → sem contra-indicação estrutural
lado definido (S ≠ 50)
```

### VETO (o ✕ vermelho)

Proteção contra "comprar o topo do movimento": se a moeda está no **top-2 do ranking pelo seu lado** (2 mais fortes se está forte; 2 mais fracas se está fraca — ranking H1 via `MetRankH1`, desempate por cesta e alfabeto) **e** a velocidade VEL(6) está **contrária ao lado tanto em H4 quanto em D1**, o VETO liga e anula a candidatura.

> 💡 A moeda ainda parece campeã no placar, mas os dois prazos maiores mostram que ela já está *desacelerando na contramão*. O VETO diz: "forte, sim — mas provavelmente no fim da festa".

### Rodapé

Linha de status com os parâmetros vigentes: k, N do sigma, limiares de destaque, N do zHist e qual núcleo está ativo ("IFM-Z" ou "IFM classico").

---

## 11. Matriz 8x8

Painel à direita (ocultável). Grade moeda-linha × moeda-coluna:

- **Célula (A,B)** = IFM Light do par A/B no TF selecionado, do ponto de vista de A: `100 − valor` preenche automaticamente a célula espelhada (B,A).
- **Heatmap contínuo** (`GradeColor`): fundo interpola do cinza-neutro para verde (>50) ou vermelho (<50), com intensidade proporcional a \|valor − 50\|. Texto vira branco quando \|v−50\| ≥ 15.
- **Diagonal** = "-" (moeda contra si mesma); **"?"** = par sem dados no broker.
- **Seletor de TF próprio** (independente do da tabela de métricas), pills douradas.
- **Rodapé**: moeda mais forte e mais fraca pela agregação `ComputeCurrencyStrength` no TF da matriz.

> 💡 **Interpretação fácil:** é a "tabela do campeonato" em modo confronto direto. A linha do EUR mostra o placar do EUR contra cada rival: verde forte = EUR atropelando aquele par; a matriz inteira esverdeada na linha = moeda dominante em todos os fronts. O uso clássico: casar a moeda mais forte contra a mais fraca do rodapé.

---

## 12. Barra superior, botões e Replay

Topbar de 30 px (`DrawButtons`), sempre redesenhada por último (fica no topo):

| Elemento | Função |
|---|---|
| **IFM** | Título. |
| **MATRIZ** | Liga/desliga a matriz (a tabela de métricas se expande para a largura toda quando oculta). |
| **ATUALIZAR** | Força um `Compute()` imediato (rebuild completo dos dados). |
| **REPLAY / LIVE** | Entra/sai do modo replay. |
| **◄◄ ◄ ► ►►** | (Só em replay) navega −10/−1/+1/+10 barras do TF do gráfico. |
| **Status** | Ao vivo: hora da última atualização + contagem regressiva. Em replay: timestamp âncora + shift (dourado, "auto pausado"). |

### Sistema de Replay

Permite "voltar no tempo" e ver o painel como ele estaria em qualquer barra fechada passada:

- `g_replayShift` = barras para trás no TF do gráfico; `SyncReplayTime` converte para um **timestamp absoluto** (`g_replayTime`).
- Esse timestamp é a âncora universal: `MetAnchorShift` / `ShiftForTF` o convertem para o shift equivalente em **cada par e cada TF** (via contagem de barras `Bars(...)`) — assim M5 e D1 apontam para o mesmo instante do passado.
- Em replay o auto-refresh e a atualização por barra nova **pausam** (âncora fixa).

> 💡 É um "modo VCR" honesto: como o IFM Light só usa barras já fechadas até a âncora, o que você vê no replay é exatamente o que o painel teria mostrado ao vivo naquele momento — ótimo para estudar se os sinais de candidata realmente antecederam movimentos.

---

## 13. Fluxo de eventos e ciclo de vida

### `OnInit`
1. Valida inputs do ML (RSI ≥ 2, memória ≥ 50, k ≥ 1).
2. Registra os 4 buffers e o nome curto ("IFM (auto Ns)").
3. Cria 11 handles de indicadores nativos do par ativo (3 RSIs, 2 ATRs, CCI, 2 EMAs sobre o RSI, 3 EMAs de preço).
4. Inicializa o banco ML e os pesos (todos = 1.0).
5. **Detecta os pares G8** no Market Watch (com `SymbolSelect` para garantir dados).
6. Estado inicial: métricas e matriz em H1, replay desligado.
7. Arma timer de 1 segundo.

### `OnTimer` (a cada 1 s)
- **Fase de carga:** enquanto não `g_ready`, tenta `Compute()` a cada 2 s; desiste (mostra o que houver) após ~30 s. "Pronto" = pelo menos 4 das 8 moedas com S válido em H1.
- **Em replay:** não faz nada (dados congelados).
- **Ao vivo:** incrementa a contagem; ao atingir `InpRefreshSec` refaz tudo; nos demais segundos só atualiza o texto do status (barato).

### `OnCalculate` (a cada tick)
1. Detecta **barra nova** no gráfico → dispara `Compute()` do painel (além do timer).
2. Roda o **Motor ML incremental** (§7): espera handles prontos, copia buffers, calcula da última barra processada em diante (`prev_calculated`), preenche os 4 buffers e cacheia o estado da última barra fechada (`g_activeIFM/Rank/Conf/Bias`).

### `OnChartEvent`
- `CHARTEVENT_CHART_CHANGE` → re-render responsivo se a janela mudou de tamanho.
- Cliques (rect **ou** label do botão — o sufixo `_t` é removido): toggle da matriz, refresh manual, replay e navegação, abas de TF das duas vistas.

### `OnDeinit`
Mata o timer, limpa o `Comment`, apaga todos os objetos (prefixos `IFMZM_`, `IFMZM_mx_`, `IFMZM_mt_`) e libera os 11 handles.

---

## 14. Caches e desempenho

O código separa rigorosamente **dado pesado** de **desenho leve**:

| Cache | Conteúdo | Invalidação |
|---|---|---|
| `g_metS[8][6][64]` | Ring de força S por moeda/TF | `g_metDirty = true` (via `MarkDirty`) → `MetRebuild` no próximo render |
| `g_metCesta`, `g_metZMov`, `g_metZMovH` | Cesta e z de movimento | Junto com o ring |
| `g_mtxVal/g_mtxOk/g_mtxStr` | Matriz 8x8 + força do rodapé | `g_mtxCacheTF = -1`, ou troca de TF da matriz |

Otimizações relevantes:

- **`MetRebuild` em lote:** por par/TF faz **uma única** chamada `CopyRates` de `60 + 64 − 1 = 123` barras e computa o IFM Light nos 64 offsets sobre o mesmo array (em vez de 64 cópias).
- **Trocar de aba não recalcula nada** na vista métricas (o ring de todos os TFs já está em memória); na matriz, recalcula só o TF novo.
- `UpdateStatusLabel` roda sozinho a cada segundo — o rebuild completo só no refresh.
- `g_computing` é um guarda de reentrância (o timer não empilha rebuilds).
- Motor ML é **incremental** (`prev_calculated`): só a barra nova é processada após o histórico inicial.

Custo aproximado de um rebuild completo: 28 pares × 6 TFs × 64 janelas ≈ **10.7 mil** execuções do IFM Light — daí o padrão de 60 s no auto-refresh.

---

## 15. Mapa de funções

| Bloco | Função | Papel |
|---|---|---|
| Helpers | `Clamp`, `CurIdx`, `Rtf`, `TfStr` | Utilidades gerais |
| Replay | `ShiftForTF`, `SyncReplayTime`, `MetAnchorShift` | Conversão tempo ↔ shift por TF/símbolo |
| ML helpers | `Scale01`, `Compress`, `PercentRank`, `CalcStdev`, `GetVolume`, `ClassifyOutcome`, `WeightSum` | Normalização, distância, rotulagem |
| Banco | `BankInit`, `BankPush`, `BankGetRow` | Memória circular 400×9 |
| ML engine | `ComputeFisherWeights`, `GapTo`, `RunKNN` | Pesos adaptativos + busca de analogias |
| Notas | `RankScore`, `ConfScore` | Qualidade do setup / certeza do sinal |
| Juízes (par ativo) | `CalcPivotScore`, `CalcMPScore`, `CalcMFCScore`, `CalcCCIScore`, `CalcMLRSIScore` | Votos −2…+2 |
| IFM Light | `EmaFromRates`, `CciFromRates`, `TpZScore`, `VolFromRates`, `CalcIFMLightAt`, `CalcIFMLight` | IFM de 4 juízes via CopyRates |
| Agregação | `ComputeCurrencyStrength` | S por moeda (rodapé da matriz) |
| UI primitivas | `Lbl`, `Rect`, `FlatBtn`, `DelBtn`, `LerpColor`, `GradeColor` | Desenho de objetos |
| Métricas | `MetSign`, `MetIsNan`, `MetSliceOk`, `MetVel`, `MetAcel`, `MetZVel`, `MetRebuild`, `MetRankH1`, `MetNum`, `RenderMetrics` | Dados + render da tabela |
| Matriz | `RenderMatrix` | Render do heatmap 8x8 |
| Orquestração | `DrawButtons`, `UpdateStatusLabel`, `MarkDirty`, `RenderAll`, `Compute` | Topbar, invalidação, pipeline |
| Eventos | `OnInit`, `OnDeinit`, `OnTimer`, `OnChartEvent`, `OnCalculate` | Ciclo de vida MT5 |

---

## 16. Glossário

| Termo | Definição curta |
|---|---|
| **ATR** | Average True Range — tamanho médio das barras; a "régua de volatilidade" usada em todo o indicador. |
| **CCI** | Commodity Channel Index — mede o quão esticado o preço típico está vs. sua média recente. |
| **Chop** | Mercado lateral picotado, sem tendência (EMA5 e EMA50 coladas em relação ao ATR). |
| **EMA** | Média móvel exponencial — média que dá mais peso às barras recentes. |
| **Feature** | Um dos 8 números que descrevem o "estado" do mercado numa barra. |
| **Fisher score** | Medida de quanto uma variável separa dois grupos (aqui: barras que antecederam alta vs. baixa). |
| **G8** | As 8 moedas principais: USD, EUR, GBP, JPY, CHF, CAD, AUD, NZD. |
| **kNN** | k-Nearest Neighbors — método que decide olhando os k exemplos passados mais parecidos com o presente. |
| **Look-ahead bias** | Erro de usar informação do futuro num cálculo do passado; evitado pela inserção atrasada no banco. |
| **MFC** | Market Facilitation Index (Bill Williams) — range da barra dividido pelo volume. |
| **POC / VAH / VAL** | Ponto de controle e limites da área de valor do Market Profile (aqui aproximados por EMA21 ± 1%). |
| **Ring buffer** | Vetor circular: quando enche, o dado novo sobrescreve o mais antigo. |
| **S (força)** | Nota 0–100 de uma moeda, média das suas 7 "partidas" (pares) — 50 = neutra. |
| **Stance** | A "postura" direcional assumida pelo motor ML quando sinal e contexto se alinham. |
| **Supertrend** | Trilho de tendência baseado em ATR que segue o preço e vira quando é cruzado. |
| **t0** | O ponto "agora" das séries do painel: a última barra **fechada** (ou a âncora do replay). |
| **Z-score** | Quantos desvios-padrão um valor está acima/abaixo da média de referência — a régua universal de "isso é normal ou excepcional?". |
| **EMPTY_VALUE / NaN** | Marcador de dado ausente; no painel, ausência nunca é substituída por neutro — ela se propaga e vira "—". |

---

*Guia gerado a partir da leitura integral de `IFM.mq5` (2033 linhas), versão 1.0.*

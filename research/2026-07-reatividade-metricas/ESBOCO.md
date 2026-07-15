# Esboço — Pesquisa Quantitativa do IFM

> **Status:** esboço em refinamento (pré-plano)
> **Escopo:** Fase 1 — painel G8 (força S e métricas derivadas). O motor ML kNN do par ativo (IFM/Rank/Conf) fica **fora** desta pesquisa e vira pesquisa própria depois.
> **Perfil de trading alvo:** **puramente intraday** (ver Premissa P2). Nada aqui busca resultados para swing ou position trade.
> **Destino previsto no repo:** `research/2026-07-reatividade-metricas/`, seguindo `research/_template/`.

---

## Regra de ouro da pesquisa: clareza obrigatória

Esta pesquisa segue o mesmo padrão didático do `IFM_GUIA.md`, e isso é uma **regra**, não um enfeite:

1. **Todo conceito técnico vem com uma 💡 interpretação fácil** — no esboço, no plano, nos READMEs e nos resultados. Se não dá para explicar em linguagem simples, é sinal de que nem nós entendemos direito.
2. **Todo resultado (tabela, gráfico) vem com uma "leitura em uma frase"** logo abaixo: o que esse número/figura está dizendo e o que seria bom vs. ruim ali. Ninguém deve precisar decifrar um gráfico sozinho.
3. **Toda decisão tem critério declarado ANTES de olhar o dado** ("consideramos achado se X ≥ Y"), para que julgar seja mecânico: bateu ou não bateu.
4. **Números sempre em unidades interpretáveis** — retornos em ATRs ("o preço andou 1.5 'passos típicos'"), tempos em candles E em minutos/horas de relógio, probabilidades em % simples.

> 💡 **Por quê:** o dono da pesquisa precisa conseguir **observar e julgar** cada etapa sem ser estatístico. Se um resultado só é compreensível para quem escreveu o script, ele não serve para tomar decisão — e decisão é o produto final deste repo.

---

## Premissas e convenções fixadas (o norte da pesquisa)

**P1 — A convenção do dia.** Todo dia há moedas que passam por tendências que se refletem em TODOS ou quase todos os seus 7 pares. Essas tendências podem durar uma sessão, duas, o dia inteiro — às vezes mais de um dia. Esta é a matéria-prima que o painel existe para capturar, e esta pesquisa a trata como **premissa fixada**: o primeiro trabalho empírico é justamente catalogar esses eventos (o "gabarito", seção 1).

**P2 — Perfil puramente intraday.** A janela máxima de captação é o day trade. As unidades de operação são **sessões**: Tóquio, Londres, NY, a interseção Londres+NY, e combinações (Tóquio+Londres etc.). Consequências diretas: (a) horizontes de avaliação são medidos dentro do dia — "até o fim da sessão" e "até o fim do dia" são os horizontes naturais; (b) timeframes altos (D1, W1, MN) entram como **contexto/viés**, nunca como janela de operação; (c) tendências que atravessam dias só nos interessam na fatia de hoje.

**P3 — Reatividade, não previsão.** Não estamos atrás de prever o movimento antes de ele existir. Estamos atrás de responder: **dado que uma tendência real começou a aflorar, quão rápido — e com que confiabilidade — cada métrica, TF e combinação a sinaliza?** E: quanto do movimento ainda resta para operar quando o sinal acende?

> 💡 **Sismógrafo, não bola de cristal.** Um sismógrafo não adivinha o terremoto de amanhã — ele detecta o tremor que **já começou**, segundos antes da onda destrutiva chegar, e esses segundos valem tudo. A pergunta desta pesquisa é a do sismógrafo: quando o "tremor" (a tendência do dia) começa, quantos minutos o painel leva para tocar o alarme? Quais colunas do painel tocam primeiro? E quantas vezes o alarme toca à toa? Prever seria adivinhar o terremoto; **reagir bem é ciência de detecção** — e é isso que buscamos.

> 💡 **Por que essa distinção muda tudo na pesquisa:** numa pesquisa de previsão, a nota de uma métrica é "o retorno futuro depois dela" (correlação com o futuro). Numa pesquisa de **detecção**, a nota tem quatro partes: pegou o evento? quão cedo? com quantos alarmes falsos? e sobrou movimento para operar? Uma métrica pode ser péssima vidente e excelente vigia — e vigia é o que um day trader precisa.

---

## 0. Objetivo geral

Tratar o IFM como laboratório quantitativo e responder, com evidência estatística e validação fora da amostra:

1. Quais métricas do painel **detectam mais rápido** os eventos reais de tendência intraday — e em quais timeframes.
2. Quais combinações de métricas e/ou timeframes detectam mais rápido e com menos alarmes falsos do que qualquer métrica sozinha.
3. Quais métricas são redundantes entre si (e quais podem ser removidas sem perda de reatividade).
4. Onde estão as regiões de exaustão — o ponto a partir do qual o alarme está tocando **tarde demais** (o movimento do dia já foi consumido).
5. Se a regra **candidata** atual (o "alarme oficial" do indicador) é um bom detector — e, se não, quais pesos e limiares deveriam substituí-la num Score contínuo otimizado para reatividade.
6. Como conflitos entre métricas e entre timeframes (descorrelação) afetam a detecção — conflito que atrasa, conflito irrelevante e conflito que é, ele mesmo, um sinal precoce.
7. Se existe uma lógica cíclica identificável na força das moedas — por sessão e por TF (expansão → clímax → exaustão → reversão/lateralidade) — e quão cedo cada fase é reconhecível.
8. Quais fatores estão faltando para detectar mais rápido (só se justificados por ganho incremental medido).

**Correções de premissa vs. esboço v1:** o indicador **não possui um "Score Final" numérico** — possui a regra binária *candidata* (|zvel| ≥ 2.0 E |zS| ≥ 1.0 E cesta ≥ 5/7 E mtf ≥ 2/4 E sem VETO E lado definido). Essa regra é o **baseline** (o detector a bater). E o "T-Statistic" do esboço v1 **já existe no indicador: é o zvel** — tratado aqui como a variável de *evidência estatística*, separada das variáveis de *nível* (S, zS).

> 💡 **Nível vs. evidência, versão detecção:** o **nível** (S, zS) diz *onde* a moeda está no placar; a **evidência** (zvel) diz se ela está *realmente arrancando agora* ou se o placar só balançou. Para um detector de tendências nascendo, a hipótese natural é que a evidência dispara **antes** do nível — é exatamente o tipo de coisa que a corrida de latências (Q1) vai medir.

> 💡 **Baseline:** é o "alarme a bater". Antes de inventar um detector novo, medimos a latência, a taxa de detecção e os alarmes falsos da regra candidata atual. Qualquer proposta só vale se ganhar dela — senão estamos trocando seis por meia dúzia com mais complexidade.

---

## Fase 0 — Infraestrutura e integridade (pré-requisito de tudo)

O indicador guarda apenas **64 pontos de S por moeda/TF** (`MET_RING`) — insuficiente para pesquisa. Portanto:

- **F0.1 — Exportador de barras** (`tools/`): script MQL5 que exporta OHLCV das barras dos 28 pares G8 para CSV, período configurável, nos TFs **M5, M15, M30, H1, H4, D1, W1, MN** (os dois últimos não existem no painel — entram na pesquisa como camada de contexto; ver Q6).
- **F0.2 — Reimplementação em Python** de toda a cadeia: IFM Light (4 juízes, núcleo Z, janela de 60 barras) → força S → vel, zvel, acel, zS, zMov, zHist, cesta, mtf, VETO, candidata. Mesmos parâmetros default do indicador (k=6, N_sigma=32, zMovN=20 etc.), estendida a W1/MN.
- **F0.3 — Verificação de paridade** indicador ↔ Python sobre uma janela de sobreposição (usando o replay do indicador como fonte da verdade), nos TFs que o painel cobre. Critério: erro máximo tolerável definido antes (ex.: |ΔS| < 0.1). **Sem paridade aprovada, nenhuma conclusão é válida** (regra do CLAUDE.md).
- **F0.4 — Regra de NaN idêntica à do painel:** dado faltante nunca é imputado como neutro; NaN se propaga. Linhas contaminadas saem da amostra (e a taxa de descarte é reportada).
- **F0.5 — Período e amostra definidos antes**, com divisão **treino / validação / teste out-of-sample fixada antes de olhar qualquer resultado** — o bloco de teste só é aberto uma vez, no final.

> 💡 **Por que reimplementar em Python?** O indicador é como um painel de carro: mostra o valor de agora, mas só guarda as últimas 64 leituras. Para pesquisar, precisamos de *anos* de leituras. Então reconstruímos a mesma calculadora em Python, alimentada pelas barras cruas exportadas do MT5 — e antes de confiar nela, conferimos que ela dá **exatamente** os mesmos números do indicador num período de teste. Isso é a "paridade": duas calculadoras diferentes chegando ao mesmo resultado.

> 💡 **Treino / validação / teste:** dividimos o histórico em três pedaços de tempo, como três provas. No **treino** aprendemos os padrões; na **validação** conferimos se eles se sustentam; o **teste** é um pedaço lacrado que só abrimos UMA vez, no fim, para o veredito final. Se olhássemos o teste várias vezes, acabaríamos "decorando a prova" sem perceber — e o resultado pareceria ótimo no papel e falharia ao vivo.

---

## 1. O gabarito de eventos e a gramática de avaliação (o coração)

Se o norte é reatividade, a primeira construção é o **gabarito**: o catálogo dos eventos reais que o painel deveria ter detectado. Ele é construído **ex-post** (com o dia inteiro já conhecido) — pode "olhar o futuro" à vontade, porque não é um sinal: é a **resposta certa da prova**.

### 1.1 O evento de tendência diária (operacionalizando a Premissa P1)

Definição candidata (parâmetros exatos congelados no plano e validados visualmente antes de qualquer análise):

- **Unidade:** (moeda, dia de negociação). O "dia" vai da abertura de Tóquio ao fechamento de NY.
- **Condição de magnitude:** |retorno da cesta da moeda no dia| ≥ limiar em ATRs (proposta inicial: ≥ 1.0 ATR médio dos pares).
- **Condição de unanimidade:** ≥ 6 dos 7 pares fecharam o dia na mesma direção para a moeda (a assinatura da P1).
- **Condição de qualidade do caminho:** razão de eficiência do dia ≥ limiar (o movimento foi razoavelmente direto, não um vai-e-volta que por acaso fechou longe).
- **Atributos registrados por evento:** direção, magnitude (ATRs), duração, sessões cobertas, e — crucial — a **âncora de início**.

> 💡 **Razão de eficiência (Kaufman):** distância em linha reta entre o começo e o fim do dia ÷ soma de todos os zigue-zagues do caminho. Perto de 1 = andou reto (tendência de verdade); perto de 0 = serrote que por sorte fechou deslocado. Serve para o gabarito não catalogar como "tendência" um dia caótico.

### 1.2 A âncora de início (a decisão mais delicada do gabarito)

A latência é medida a partir de "quando a tendência começou" — e isso precisa de uma definição honesta. Duas candidatas a testar (e auditar no gráfico):

- **A-20/10:** o início é o candle M15 em que o movimento acumulado do dia atinge 20% da magnitude final **e nunca mais recua abaixo de 10%** (o "ponto sem retorno").
- **A-rompimento:** o último cruzamento do preço da cesta pelo nível de abertura do dia antes do trecho final do movimento.

A escolha entre elas é feita por **auditoria visual**: sorteamos dias-evento, plotamos a cesta com a âncora marcada, e o usuário responde "é aqui que um trader diria que começou?". Só depois do gabarito aprovado a olho é que qualquer métrica é avaliada.

> 💡 **Por que tanto cuidado com a âncora:** se marcarmos o início cedo demais, toda métrica parecerá lenta; tarde demais, toda métrica parecerá vidente. A âncora errada não distorce uma métrica — distorce a régua inteira. Por isso ela é definida por regra transparente, conferida contra o olho humano, e congelada antes da corrida começar.

### 1.3 As quatro notas de um detector

Para cada métrica/combinação (com um limiar de disparo), contra o gabarito:

1. **Latência de detecção:** minutos (e candles do TF) entre a âncora de início e o primeiro disparo na direção certa. Reportada como mediana e distribuição — e também como **% do movimento já consumido** no momento do disparo.
2. **Taxa de detecção (recall):** % dos eventos reais que a métrica sinalizou em tempo útil (antes de X% do movimento consumido).
3. **Taxa de alarme falso:** disparos fora de eventos (ou na direção errada), normalizados por sessão — "toca à toa quantas vezes por semana?".
4. **Captura restante:** quanto do movimento (em ATRs e em % da magnitude) ainda restava do disparo até o fim do evento. **É a nota que conecta detecção a dinheiro:** detectar rápido só vale se sobrar estrada.

> 💡 **O trade-off fundamental (a curva do detector):** todo alarme tem um botão de sensibilidade. Sensível demais = dispara cedo, mas toca à toa toda hora; conservador demais = quase nunca erra, mas avisa quando a casa já queimou. Não existe "o limiar certo" em abstrato — existe uma **curva** latência × alarmes falsos, e a pesquisa desenha essa curva para cada métrica. Aí a escolha do ponto de operação vira uma decisão sua, informada e visual, não um número mágico.

### 1.4 Alvos e horizontes (versão intraday)

Os retornos continuam medidos nos três alvos do v2 — **A1** (ΔS da força), **A2** (cesta da moeda, em ATRs), **A3** (par mais forte × mais fraco, em ATRs) — mas os horizontes agora são os do day trade:

- **Horizontes de relógio:** +30 min, +1 h, +2 h, +4 h (traduzidos em candles por TF nas tabelas);
- **Horizontes naturais da P2:** até o **fim da sessão corrente** e até o **fim do dia**.

Não há horizontes de 50–100 candles em TFs altos: D1/W1/MN não são janelas de operação — são contexto (Q6).

### 1.5 Guarda-corpo estatístico (vale para todas as questões)

- Eventos são relativamente raros (algumas moedas por dia, no máximo) → intervalos de confiança por **block bootstrap por dia** (o dia é o bloco natural: eventos do mesmo dia são parentes).
- Amostras entre moedas no mesmo instante são correlacionadas (soma-zero do G8: se EUR sobe, alguém desce) → agrupar por timestamp/dia.
- Tudo que envolve varredura (limiares, combinações, TFs) → correção de múltiplos testes (Benjamini-Hochberg no mínimo) + confirmação no bloco out-of-sample.
- Critérios de "achado" definidos **antes**, no plano.
- **Anti-look-ahead em duas frentes:** (a) métricas usam só barras fechadas — inclusive o contexto W1/MN, que usa a **última semana/mês FECHADO** (a semana corrente não existe para o sinal); (b) o gabarito, que legitimamente olha o dia inteiro, **nunca vira feature** — ele é só régua.

> 💡 **Soma-zero do G8:** força é relativa — se o EUR sobe no placar, alguém necessariamente desce. Então "EUR forte" e "USD fraco" no mesmo instante não são duas evidências independentes; são em parte a mesma notícia contada por dois jornais.

> 💡 **Múltiplos testes (o problema dos 1000 palpites):** se você testar 1000 detectores aleatórios, uns 50 vão parecer ótimos por pura sorte. A correção de múltiplos testes pergunta: "esse resultado é bom *mesmo descontando* quantas tentativas fizemos?". Sem isso, garimpo de dados vira fábrica de ilusões.

---

> **Convenção de rótulos:** as questões de pesquisa usam **Q1…Q11** (Q de *questão*). Evitamos deliberadamente o prefixo "H" (de hipótese) porque colidiria com os nomes dos timeframes H1 e H4.

## 2. Q1 — A corrida de latências: reatividade individual

Para cada métrica (S, zS, vel, zvel, acel, zMov, zHist, cesta, mtf — e VETO como flag), em cada TF de operação/sinal (M5…H4), contra o gabarito:

- As **quatro notas** (latência, detecção, falso alarme, captura restante), com a curva sensibilidade × falso alarme por métrica.
- **Ranking de agilidade:** quais colunas do painel "tocam primeiro" — mediana de % do movimento consumido no disparo.
- Complemento preditivo leve: IC de Spearman da métrica contra A2/A3 nos horizontes intraday — serve de checagem ("depois do disparo ainda há relação com o que vem"), não de nota principal.

> 💡 **A imagem-resumo desta questão é uma corrida:** todos os eventos do gabarito alinhados no instante zero (a âncora), e cada métrica marcada no ponto em que cruzou seu limiar. O pódio mostra quem chega primeiro **em média** — e a tabela ao lado mostra o preço de cada velocista em alarmes falsos. É a resposta direta a "quais métricas descobriram a tendência mais rapidamente?".

> 💡 **IC de Spearman (papel coadjuvante aqui):** nota de "quanto a métrica ordena bem o retorno seguinte". Mantemos como sanidade: um detector rápido cujo disparo não guarda relação nenhuma com o que vem depois provavelmente está disparando em ruído.

**Produto:** tabela-liga (league table) métrica × TF × sessão com as quatro notas + heatmap com legenda de leitura.

## 3. Q2 — Limiares ótimos: onde pôr o botão de sensibilidade

Varrer o limiar de disparo de cada métrica (para zvel: 1.0, 1.5, 2.0, 2.5, 3.0; análogos para as demais) e desenhar a curva latência × falso alarme × captura de cada uma, por TF e por sessão.

- Comparar os limiares atuais do indicador (zvel 2.0, zS 1.0, cesta 5, mtf 2) contra o ponto da curva que o dado sugere **para o perfil intraday**.
- Verificar se o limiar ótimo muda por sessão (o que dispara bem em Londres pode tocar à toa em Tóquio).

> 💡 **O que estamos julgando:** os limiares atuais foram escolhidos por teoria. Esta seção pergunta ao dado: "se você pudesse posicionar o botão do alarme para um day trader, onde o poria?" — e responde com uma curva onde cada ponto é legível: "limiar 1.5 = pega 78% dos eventos com 25% consumido, ao custo de 3 alarmes falsos/semana".

## 4. Q3 — O que acontece depois do disparo: continuação vs. reversão

Estudo de eventos ancorado nos **disparos** (não mais em "extremos" abstratos): dado um disparo válido, a trajetória seguinte acelera / continua / estabiliza / reverte — dentro do dia?

- Probabilidade de cada cenário por métrica × TF × sessão × profundidade do disparo.
- Sobrevivência intraday: dos disparos, quantos ainda estavam "vivos" (tendência intacta) 30 min / 1 h / 2 h depois — e quantos morrem na virada de sessão?

> 💡 **Estudo de eventos:** é o "replay estatístico". Pegamos *todas* as vezes em que o alarme X tocou, alinhamos no instante do toque e desenhamos o caminho médio do que veio depois — como sobrepor centenas de fotos do mesmo lance. Resultado: "depois desse alarme, em média o movimento rende mais Y ATRs em Z minutos, e morre na entrada de NY em W% dos casos".

## 5. Q4 — Combinações: alguém junto detecta mais rápido que todos sozinhos?

A pergunta explícita do usuário — "qual correlação de métricas e/ou timeframes achou mais rápido a tendência?" — com disciplina contra o garimpo:

1. **Duplas e trios dirigidos por hipótese** (ex.: zvel M15 + cesta parcial ≥ 4/7 = "arrancada com adesão"; zvel H1 confirmado por vel M5 = "o grande acorda e o pequeno já corre").
2. **Quadrantes nível × evidência** — zS (nível) × zvel (evidência): hipótese central de detecção: *nível baixo + evidência alta = tendência aflorando (o melhor momento)*; *nível alto + evidência baixa = alarme atrasado*.
3. **Busca ampla model-based** (Q11) em vez de força bruta: interações saem de modelos com validação, não de enumerar tudo.

Cada combinação recebe as mesmas quatro notas — a régua é uma só, então "combinação X detecta 12 min antes que a melhor métrica sozinha, com metade dos falsos" é uma frase possível e verificável.

> 💡 **Por que não testar "todas as combinações"?** Pelo problema dos 1000 palpites: enumerar tudo *garante* achar combinações geniais por sorte. Testamos primeiro as que têm uma história plausível (cada uma com nome e motivo); a busca ampla fica para modelos julgados pelo acerto em dados que nunca viram.

## 6. Q5 — Descorrelação e conflito: atrasa, não importa, ou avisa?

Nem tudo precisa concordar — e saber **quanto** um conflito pesa muda a leitura do painel:

- **Conflito entre TFs:** quando o contexto (D1/W1/MN) aponta contra a arrancada intraday, a detecção piora? Quanto (latência, captura)? E o inverso: TF curto virando contra o longo é um **alerta precoce** de que a tendência do dia vai contra o contexto — e essas tendências "contra o vento" rendem menos?
- **Conflito entre métricas:** zMov vs. zHist discordando; vel vs. acel (andando mas desacelerando); cesta cheia vs. zvel fraco.
- **Produto:** tabela "conflito X → efeito Y sobre detecção/captura", que vira entrada em `docs/LEITURA.md` mesmo que nenhum código mude — saber que um conflito é irrelevante já muda a leitura.

> 💡 **Conflito não é defeito, é informação (talvez).** Quando M15 grita "compra" e o D1 diz "vende", isso pode ser (a) ruído, (b) motivo para reduzir mão, ou (c) o primeiro aviso de uma virada. As três respostas mudam como se opera. Esta seção mede qual é verdade, conflito por conflito — com números tipo "tendências intraday contra o W1 capturam 40% menos".

## 7. Q6 — A hierarquia de timeframes: de MN a M5

Cobertura completa da hierarquia, conforme pedido: **MN, W1, D1** (camada de contexto/viés — calculadas na pesquisa, ainda que o painel não as exiba), **H4, H1** (ponte), **M30, M15, M5** (detecção/operação). Qualquer TF pode ser **descartado** conforme os padrões forem aparecendo — descarte também é achado.

- **Papel de cada camada:** os TFs de contexto melhoram a detecção intraday (menos falsos? mais captura quando alinhados?) ou são peso morto para o day trade?
- **Corrida entre TFs de detecção:** para o mesmo evento, o M5 dispara antes do M15? Sempre? A que custo em falsos? Existe um "TF doce" para cada sessão?
- **Concordância em cascata:** medir o valor incremental de cada camada de cima para baixo (MN→W1→D1→H4→H1→M30→M15→M5) — onde a cascata para de adicionar informação?
- **Ponderação hierárquica** (com Q11): peso de cada métrica dentro de cada TF, depois peso de cada TF no detector composto.

> 💡 **A metáfora da maré, da onda e da marola:** MN/W1/D1 são a maré (o pano de fundo que muda devagar), H4/H1 são as ondas, M30–M5 são as marolas onde o day trade acontece. A pergunta desta seção: saber a maré ajuda a surfar a marola? E quanto? Se a resposta for "quase nada", descartamos camadas de cima sem dó — o painel fica mais leve e a leitura mais limpa. Se for "ajuda muito", o contexto vira filtro oficial.

## 8. Q7 — Exaustão: quando o alarme toca tarde demais

Versão intraday da exaustão: o ponto a partir do qual **entrar não compensa porque o dia já deu o que tinha**.

- Limites empíricos: a partir de que % do movimento consumido / que valor de zS, zvel, acel a captura restante mediana cai abaixo do aproveitável (derivado de Q2/Q3).
- Exaustão por relógio: existe hora da sessão a partir da qual sinais novos são estatisticamente tarde (ex.: última hora de Londres)?
- **Validação empírica do VETO** (hipótese de exaustão já codificada e nunca testada): moedas top-2 do ranking H1 com VEL contrária em H4 E D1 realmente têm captura pior? Quanto? A formulação atual (binária, top-2, H4∧D1) é a melhor, ou uma versão contínua/graduada domina?

> 💡 **O VETO é uma aposta não conferida.** Ele diz "campeã desacelerando nos prazos maiores = fim de festa". Três vereditos possíveis: ajuda (mantém), não muda nada (enfeite, remove), corta bons sinais (pior que nada, remove urgente). Também testamos o VETO "dimmer" (gradual) contra o atual "interruptor".

## 9. Q8 — Persistência: quanta estrada sobra depois do sinal

- Distribuição da vida restante dos eventos após o disparo (mediana, quantis) — em minutos e em ATRs, por sessão.
- **Half-life da força intraday:** modelo de reversão à média (AR(1)/OU) em S por moeda × TF de detecção — o "prazo de validade" natural de um desvio de força em cada TF, que fundamenta horizontes de saída com dado, não chute.
- Captura vs. idade do sinal: entrar no disparo vs. 15 min depois vs. 1 h depois — quanto custa o atraso do trader (não do indicador)?

> 💡 **Half-life (meia-vida):** o conceito da física nuclear aplicado à força: se o EUR está 20 pontos acima do neutro, em quanto tempo metade desse exagero se dissipa? Se a meia-vida no M30 for 40 minutos, um sinal de M30 tem ~40 min de "validade natural" — número que vai direto para a regra de saída.

## 10. Q9 — Ciclos e sessões: a rotina diária das moedas

A lógica cíclica pedida, com a sessão como unidade central:

- **Fases operacionais** a partir de (S, vel, acel, zvel): **expansão** (vel e acel a favor), **clímax** (vel alta, acel virando), **exaustão** (nível extremo, vel caindo), **reversão/lateralidade**. Primeiro por regras transparentes; depois validar com HMM de 3–4 estados e conferir se os estados descobertos coincidem com as fases desenhadas.
- **Quão cedo cada fase é reconhecível?** — a versão "detecção" da ciclicidade: com quantos candles de fase já dá para nomeá-la com 70%+ de acerto?
- **O relógio das sessões:** onde nascem as expansões (abertura de Londres? interseção Londres+NY?) e onde morrem? Tendências de Tóquio sobrevivem a Londres? Matriz de transição fase→fase **por sessão** e por TF; sazonalidade por hora e dia da semana (DST tratado).
- **Autocorrelação de S por TF:** em quais TFs a força intraday é mais "tendencial" e em quais é mais "elástica" (volta ao meio)?

> 💡 **A metáfora das estações, em miniatura:** a hipótese é que a força de uma moeda vive estações **dentro do dia** — primavera (expansão) na abertura de uma sessão, verão (clímax) na interseção, outono (exaustão) no fim dela. Se for verdade, o painel deixa de ser foto ("EUR forte agora") e vira previsão do tempo da sessão ("EUR forte, entrando no outono de Londres — não compre o rali velho").

> 💡 **HMM (Modelo Oculto de Markov) — o teste do desenho sem gabarito:** primeiro NÓS desenhamos as 4 fases com regras claras. Depois um algoritmo agrupa comportamentos parecidos **sem conhecer nossas regras**, e perguntamos: os grupos dele batem com as nossas fases? Se sim, as fases são reais, não invenção. Se ele achar grupos diferentes, o desenho dele pode ser melhor — também é achado.

## 11. Q10 — Banco de dados de pesquisa

Duas tabelas:

**Tabela de estados** — uma linha por (timestamp, moeda, TF):
- **Chaves/contexto:** data-hora (UTC do servidor + flag DST), moeda, TF, sessão, minutos desde a abertura da sessão, versão do indicador + hash dos parâmetros (reprodutibilidade).
- **Métricas no t0 (barra fechada):** S, zS, vel, zvel, acel, zMov, zHist, cesta (x/7), mtf (x/4), VETO, candidata, rank H1, lado.
- **Contexto multi-TF:** S e vel das camadas superiores usando a **última barra fechada** de D1/W1/MN (anti-look-ahead).
- **Contexto de mercado:** ATR14 do TF, ADR, volume agregado quando disponível. **Spread:** ⚠️ o MT5 não fornece spread histórico em barras — registrar spread típico por par como constante de custo e documentar a limitação.
- **Alvos:** A1/A2/A3 nos horizontes intraday da seção 1.4.

**Tabela de eventos (o gabarito)** — uma linha por evento: moeda, dia, direção, magnitude (ATRs), âncora de início, fim, duração, sessões cobertas, eficiência do caminho, nº de pares alinhados. Ligada à tabela de estados por (moeda, dia).

Formato Parquet (não CSV) pelo volume; gitignorado em `data/`; README documenta como regenerar.

> 💡 **Duas tabelas, dois papéis:** a tabela de estados é o "filme" (o que o painel via a cada momento, só com informação legal); a tabela de eventos é o "gabarito da prova" (o que de fato aconteceu, escrito depois com o dia inteiro na mão). Toda a pesquisa é cruzar filme com gabarito — e a regra sagrada é que o gabarito nunca vaza para dentro do filme.

## 12. Q11 — Redundância, importância e o novo Score (detector composto)

**Redundância primeiro:** correlação (Spearman) entre métricas por TF + clustering hierárquico + VIF. Hipóteses óbvias a confirmar: vel×zvel, zS×S, zMov×zHist em dias normais. Redundante = candidata a remoção.

> 💡 **Redundância = dois termômetros na mesma parede.** Se vel e zvel sobem e descem sempre juntos, ter os dois não acrescenta informação. O clustering desenha a "árvore de parentesco" das métricas; de cada galho basta a melhor representante.

**Importância depois — agora como problema de detecção:** com as duas tabelas, treinar modelos que respondam "há um evento aflorando AGORA (e para que lado)?": regressão logística regularizada → Gradient Boosting com SHAP → PCA como leitura estrutural. Sempre **walk-forward** (nunca embaralhar candles), importâncias estáveis entre janelas como critério, e avaliação final **nas quatro notas** (latência/detecção/falsos/captura), não em acurácia abstrata.

> 💡 **A escada de modelos:** começamos pelo transparente (regressão: pesos legíveis) e só subimos para os espertos (florestas) se provarem que enxergam algo a mais. Complexidade sem ganho comprovado a gente recusa.

> 💡 **SHAP:** o "extrato bancário" de cada decisão do modelo: "gritei 'evento!' porque zvel M15 depositou +0.3, cesta +0.2, e o contexto D1 sacou −0.1". Somando milhares de extratos, sai o ranking honesto de quem paga as contas do detector.

> 💡 **Walk-forward:** treinar no passado, testar no futuro imediato, andar a janela, repetir — como o mercado funciona. Embaralhar candles deixaria o modelo "treinar na terça sabendo da quarta".

**Ponderação hierárquica métrica × TF:** o produto final é uma **tabela de pesos legível** ("zvel manda no M15; cesta só importa de H1 para cima; MN não paga o que custa") + um **Score contínuo 0–100 de detecção** proposto, comparado ao baseline candidata nas quatro notas, com veredito no bloco de teste selado.

**Novos fatores (só com fundamento):** Efficiency Ratio de Kaufman (já usado no gabarito — testar como *feature* também), entropia, skew/curtose dos passos de S, percentis de momentum/volatilidade, distância da abertura da sessão em ATRs. Critério de admissão: **ganho incremental nas quatro notas** com as métricas existentes já no modelo — não basta ser bom sozinho.

> 💡 **Ganho incremental = o teste do contratado novo.** Não basta o candidato ser bom; ele precisa fazer algo que a equipe atual não faz. Fator novo que só repete o que o zvel já dizia é redundância entrando pela porta dos fundos.

## 13. Tradução em regras (última etapa, não primeira)

Só depois de Q1–Q11: regras objetivas de **entrada intraday** (disparo do detector vencedor + filtros de contexto/sessão), **saída** (fim de sessão, fim de dia, meia-vida, ou exaustão detectada) e **filtros**, avaliadas com custo (spread documentado), profit factor, drawdown e expectativa por trade, em walk-forward no alvo A3 — **sem posições atravessando a noite**, por definição do perfil.

> 💡 **Por que regras só no fim?** Uma regra de trading é uma torre de decisões empilhadas. Construindo andar por andar (Q1 → Q11), a regra final vem com a "planta baixa" de por que cada peça está ali — e cada peça já foi julgada sozinha antes.

## 14. Entregáveis (mapeados aos destinos do repo)

| Entregável | Destino |
|---|---|
| Ranking de reatividade das métricas (4 notas, por TF × sessão) | README da pesquisa + `docs/LEITURA.md` |
| Curvas de limiar (sensibilidade × falsos × captura) e limiares recomendados | README + possível ajuste em `src/IFM.mq5` |
| Ranking de redundâncias + recomendação de remoção/adição | README + possível mudança em `src/IFM.mq5` |
| Limites de exaustão intraday (por métrica e por relógio) + veredito do VETO | `docs/LEITURA.md` (ou ajuste no código) |
| Tabela de impacto dos conflitos TF×TF e métrica×métrica sobre a detecção | `docs/LEITURA.md` |
| Papel de cada camada de TF (MN→M5) + TFs descartados | `docs/LEITURA.md` |
| Mapa de fases/ciclos por sessão + relógio das sessões | `docs/LEITURA.md` |
| Tabela de pesos métrica × TF + Score de detecção proposto | variante em `src/variants/` (não mexer na principal antes de validar ao vivo) |
| Regras intraday de entrada/saída/filtros com backtest walk-forward | README da pesquisa |
| Hipóteses refutadas (registradas — refutar é resultado) | README da pesquisa |

> 💡 **Refutar é resultado.** Descobrir que "o contexto MN não ajuda em nada o day trade" vale tanto quanto um sinal novo: economiza atenção e fecha portas falsas. Toda hipótese morta ganha registro com a mesma dignidade das vivas.

---

## Ordem de dependência (esqueleto do futuro plano)

```
F0 (exportador → paridade → banco §11, incluindo o GABARITO validado a olho)
 └→ Q1 (corrida de latências — o mapa base)
     ├→ Q2 (limiares) ─→ Q3 (pós-disparo) ─→ Q7 (exaustão/VETO)
     ├→ Q5 (conflitos)  ├→ Q8 (persistência/half-life)
     ├→ Q6 (hierarquia MN→M5)  └→ Q9 (ciclos/sessões)
     └→ Q4 (combinações dirigidas)
          └→ Q11/§12 (redundância → importância → pesos → Score detector)
               └→ §13 (regras intraday) → §14 (entregáveis)
```

> 💡 **Leitura do esqueleto:** nada começa antes da Fase 0 (dados confiáveis E gabarito aprovado a olho); a corrida Q1 diz onde vale a pena cavar; as investigações do meio rodam em paralelo; a síntese (pesos, Score, regras) só acontece quando as peças individuais já foram julgadas. Cada seta é um ponto de parada natural para você observar e decidir.

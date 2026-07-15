# PLANO — Pesquisa Quantitativa do IFM: Reatividade das Métricas (perfil intraday)

> **Status:** aprovado para execução | **Executor:** Claude Code (análises) + usuário (MT5, portões)
> **Documento-mãe:** `ESBOCO_PESQUISA_QUANT_IFM.md`
> **Pasta da pesquisa:** `research/2026-07-reatividade-metricas/`
> **Convenções de rótulos:** questões = **Q1…Q11**; etapas de execução = **E0…E12**; portões de decisão = **P1…P4**; premissas = **P1–P3 do esboço** (contexto distingue de portões).
> **Norte (Premissa P3):** medir **reatividade** — dado que uma tendência real começou, quão rápido e com que confiabilidade cada métrica/TF/combinação a sinaliza, e quanto movimento resta para operar. Não é pesquisa de previsão.

---

## 1. Regra de ouro: clareza obrigatória (norma central deste plano)

Esta não é uma preferência de estilo — é **requisito de aceitação** de toda etapa, no mesmo nível dos critérios estatísticos. Um resultado tecnicamente correto mas incompreensível para o dono da pesquisa é considerado **incompleto** e a tarefa não fecha.

### 1.1 As quatro regras

1. **Todo conceito técnico novo vem com 💡 interpretação fácil** — explicação em linguagem do dia a dia, com analogia quando ajudar, no ponto exato onde o conceito aparece pela primeira vez. Vale para: relatórios de resultados, READMEs, PROGRESS, comentários de cabeçalho dos scripts e entradas de LEITURA.md. Se o conceito já foi explicado no esboço, basta referenciar ("💡 ver *captura restante* no esboço §1.3") — mas a referência precisa existir.
2. **Todo resultado nasce com sua "Leitura:"** — toda tabela e toda figura, sem exceção, é seguida imediatamente por uma linha `**Leitura:** ...` dizendo em uma ou duas frases: o que este resultado está dizendo, e se isso é bom, ruim ou neutro para a hipótese. O script que gera o número gera também o texto — nunca "explica depois".
3. **Todo critério de decisão já está congelado** (seção 4) — os relatórios se referem a eles por código (C1…C11) e mostram o confronto explícito: `critério exigia X, obtivemos Y → ✔/✘`.
4. **Unidades sempre interpretáveis** — latências em minutos E candles, retornos em ATRs, "% do movimento consumido" em vez de estatísticas abstratas, probabilidades em % simples. Jargão de unidade só acompanhado da tradução.

### 1.2 Template obrigatório dos relatórios de resultado (`results/EXX_*.md`)

```markdown
# EXX — [título]
## O que perguntamos
(a questão em 1–3 frases, linguagem simples)
## Como testamos
(método resumido; cada conceito técnico com 💡 ou referência ao esboço)
## Resultados
(tabela/figura → **Leitura:** ... , para CADA uma)
## Confronto com os critérios
(C_n exigia … / obtivemos … / ✔ ou ✘)
## O que isso muda
(consequência prática para o painel/pesquisa, em linguagem simples)
## Limitações
(o que este resultado NÃO diz)
```

### 1.3 Fiscalização automática

O `scripts/check_tarefas.py` valida também a conformidade didática, e **bloqueia o commit** se:

- algum `results/EXX_*.md` referenciado como evidência não seguir o template 1.2 (seções obrigatórias presentes);
- alguma tabela ou imagem num relatório não for seguida de linha `**Leitura:**`;
- a seção "Confronto com os critérios" não citar nenhum código C_n quando a etapa tem critério associado.

> 💡 **Por que fiscalizar clareza por script?** Porque clareza é a primeira coisa sacrificada na pressa — e é justamente o que garante que VOCÊ consiga observar e julgar cada etapa sem ser estatístico. No mesmo validador que já bloqueia commits, a explicação didática deixa de depender de disciplina e vira parte física do processo: relatório sem leitura não entra no repo.

> 💡 **Por que congelar critérios antes (regra 3):** se decidirmos "o que é bom" depois de ver os números, inconscientemente movemos a trave para onde a bola caiu. Congelar antes transforma cada portão numa checagem mecânica — e protege a pesquisa do nosso próprio entusiasmo.

---

## 2. Princípios de execução (como o Claude Code trabalha)

- **Uma etapa = uma sessão.** Cada sessão começa lendo `PROGRESS.md` e termina com: commit, `results/` atualizado, `PROGRESS.md` atualizado (onde estamos → o que foi decidido → próxima etapa). Nenhuma informação vive só na conversa.
- **Pipeline em estágios com cache:** `barras cruas (CSV do MT5) → métricas (Parquet) → banco-mãe + gabarito (Parquet) → análises (leem só o banco)`. Cada estágio grava seu output com o **hash da configuração**; se o hash não mudou, não recomputa.
- **`config.yaml` único** na raiz da pesquisa: períodos, parâmetros do indicador (k=6, N_sigma=32, zMovN=20, janela 60…), definição do evento/âncora, janelas de sessão (com DST), horizontes, splits, seeds. Nenhum parâmetro hard-coded em script.
- **Validar barato primeiro:** todo o pipeline (E2–E4) é validado com M30–D1 (+W1/MN, que são leves) antes de processar M5/M15.
- **Cada análise emite `results/EXX_*.md`** com figuras + leituras em uma frase, pronto para você julgar sem abrir código.
- **`TAREFAS.md` — a lista de tarefas viva:** todas as etapas e sub-tarefas existem como checkboxes num único arquivo, pré-populado no E0 (modelo na seção 9). A atualização é parte da **definição de concluído**: nenhuma tarefa é considerada feita sem seu checkbox marcado no mesmo commit que a conclui. Regras:
  - Estados: `[ ]` pendente · `[~]` em andamento · `[x]` concluída · `[!]` bloqueada (motivo ao lado) · `[-]` cancelada (motivo ao lado).
  - Cada `[x]` carrega a **evidência** entre parênteses: o arquivo de resultado ou hash de commit que prova a conclusão. Checkbox sem evidência não vale.
  - Portões (P1–P4) só podem ser marcados por decisão SUA registrada no `PROGRESS.md` — o Claude Code prepara, você carimba.
  - O script `scripts/check_tarefas.py` (criado no E0) valida a consistência automaticamente: toda tarefa `[x]` deve ter sua evidência existente no repo, nenhuma etapa pode ter tarefas `[x]` se um portão anterior estiver pendente, **e todo relatório usado como evidência deve cumprir o template didático da seção 1.2** (seções obrigatórias + `**Leitura:**` após cada tabela/figura). Roda no fim de toda sessão, antes do commit.

> 💡 **Por que checkbox com evidência e validador, e não só uma listinha?** Uma lista comum "marca-se sozinha" na empolgação — e três sessões depois ninguém sabe se E4 foi concluída ou só começada. Amarrando cada ✔ a um arquivo/commit verificável e rodando o validador antes de cada commit, a lista vira um **painel confiável do estado real da pesquisa**: você abre um único arquivo e sabe exatamente onde tudo está, com prova.

> 💡 **PROGRESS.md é a "memória externa" do Claude Code.** Sessões diferentes não compartilham lembrança — o arquivo é o caderno que qualquer sessão futura lê para saber exatamente onde retomar, o que já foi decidido nos portões e o que está proibido refazer.

---

## 3. Dados: TFs, períodos e divisão (congelados — ajustáveis SOMENTE em E0, nunca depois)

| Camada | TFs | Período total | Papel |
|---|---|---|---|
| Contexto/viés | **MN, W1** | 2016-01-01 → 2026-06-30 | Só a **última barra fechada** entra como feature (anti-look-ahead). Leves de calcular. Descartáveis se Q6 mostrar que não pagam o que custam. |
| Contexto/ponte | **D1, H4** | 2021-01-01 → 2026-06-30 | Contexto próximo + validação de paridade (o painel os cobre). |
| Detecção/operação | **H1, M30** | 2021-01-01 → 2026-06-30 | TFs de sinal com histórico longo (5,5 anos, regimes distintos). |
| Detecção/operação | **M15, M5** | 2024-07-01 → 2026-06-30 | TFs de sinal finos; 2 anos pelo volume de dados. |

**Sessões (janelas exatas + DST no `config.yaml`, congeladas em E0):** Tóquio, Londres, NY, interseção Londres+NY, e as combinações relevantes (Tóquio+Londres etc.). Toda análise reporta resultados **por sessão** além do agregado — a sessão é unidade de operação (Premissa P2).

**Divisão cronológica (comum a todos os TFs):**

| Bloco | Período | Uso |
|---|---|---|
| **Treino** | início → 2024-12-31 | Explorar, ajustar, aprender padrões. |
| **Validação** | 2025-01-01 → 2025-09-30 | Conferir se os padrões se sustentam; base dos achados provisórios. |
| **Teste selado** | 2025-10-01 → 2026-06-30 | **Aberto UMA vez, em E11.** Nenhum script toca nesses dados antes. |

Enforcement técnico: o construtor do banco (E4) grava os três blocos em **arquivos Parquet separados**, e o de teste fica em `data/sealed/` — os scripts de análise das etapas E5–E10 **recusam** esse caminho por construção.

**Níveis de confiança dos achados** (vão junto de cada entrada em `LEITURA.md`):
- **média** = confirmado em treino+validação;
- **alta** = também confirmado no teste selado (só possível a partir de E11).

---

## 4. Critérios de decisão congelados

As "quatro notas" de um detector (esboço §1.3): **latência** (mediana, também em % do movimento consumido no disparo), **taxa de detecção** (% dos eventos sinalizados em tempo útil = antes de 50% consumido), **taxa de alarme falso** (disparos fora de evento, por moeda·sessão) e **captura restante** (mediana, em % da magnitude do evento).

| # | Decisão | Critério (definido ANTES de olhar dados) |
|---|---|---|
| C1 | **Paridade aprovada (P1)** | Sobre a janela de sobreposição (TFs do painel): \|ΔS\| ≤ 0.1 em ≥ 99% dos pontos E \|ΔS\| máx ≤ 0.5; derivadas com erro relativo ≤ 1% nos mesmos moldes. NaN do Python = NaN do indicador (mesmos pontos). |
| C2 | **Gabarito aprovado (parte 1 do P2)** | 20 dias-evento sorteados, plotados (cesta + âncora marcada) e auditados por VOCÊ: em ≥ 80% dos casos "é aqui que um trader diria que a tendência começou". Reprovou → ajustar definição/âncora e re-auditar com NOVO sorteio. A definição só congela após aprovação — e congela ANTES de qualquer métrica ser avaliada. |
| C3 | **Banco aprovado (parte 2 do P2)** | Taxa de NaN ≤ 15% por (TF × ano); 20 linhas de estado sorteadas auditadas contra o replay sem discrepância; alvos A1–A3 recomputados por caminho independente batem; contexto W1/MN comprovadamente usando última barra FECHADA. |
| C4 | **Métrica "reativa" (achado Q1)** | Na validação (e mesmo sentido no treino): taxa de detecção ≥ 60% E captura restante mediana ≥ 40% da magnitude E precisão ≥ 40% (fração dos disparos que caem dentro de evento real), em pelo menos um TF × limiar. |
| C5 | **Métrica "morta"** | Em TODOS os TFs, sessões e limiares testados: taxa de detecção < 30% OU captura restante mediana < 15%, em treino e validação. |
| C6 | **Exaustão / "tarde demais" (Q2/Q3/Q7)** | Região (de métrica ou de relógio) onde a captura restante mediana ≤ 10% da magnitude, com IC95% (bootstrap por dia) abaixo de 20%, em treino E validação. |
| C7 | **Conflito relevante (Q5/Q6)** | Presença do conflito altera latência mediana, taxa de detecção ou captura em ≥ 30% (relativo), com significância após correção Benjamini-Hochberg. |
| C8 | **Redundância (Q11)** | \|ρ de Spearman\| ≥ 0.90 entre duas métricas, consistente em ≥ 4 dos TFs de detecção → par redundante; mantém-se a de melhor nota composta. |
| C9 | **Fator novo / camada de TF admitida (Q6/Q11)** | Ganho incremental: melhora ≥ 10% (relativo) em pelo menos uma das quatro notas SEM piorar as demais em > 5%, com as métricas/camadas existentes já incluídas, em walk-forward na validação. Vale também para decidir se MN/W1 ficam ou são descartadas. |
| C10 | **Score detector aprovado (P4/E11)** | No teste selado, vs. baseline candidata: latência mediana ≥ 20% menor com detecção e captura não piores, OU mesma latência com alarmes falsos ≥ 20% menores e captura não pior. Empate ou pior = baseline vence (registrar e manter). |
| C11 | **Correção de varredura** | Toda análise com > 20 testes simultâneos aplica Benjamini-Hochberg (FDR 10%). Busca de combinações (Q4 camada 3) exige adicionalmente estabilidade entre janelas walk-forward. |

> 💡 **Como ler esta tabela nos portões:** cada portão vira uma checklist. Ex.: no P2 você recebe "C2: 17/20 dias-evento aprovados a olho (85%) ✔ / C3: NaN máx 11% ✔ / 20 linhas sem discrepância ✔ → APROVADO". Você confere os ✔ e assina. Se algo falhar, a etapa volta, e o motivo fica registrado.

> 💡 **Por que o gabarito tem critério próprio (C2) e vem antes de tudo:** a âncora de início é a régua com que TODAS as latências serão medidas (esboço §1.2). Régua torta = pesquisa inteira torta. Por isso ela é validada pelo seu olho de trader e congelada antes que qualquer métrica entre na corrida — depois disso, mexer na régua para "melhorar" um resultado é proibido por construção.

---

## 5. Etapas de execução

### BLOCO A — Fundação (sequencial; você entra em E1, E3 e E4)

---

**E0 — Setup da pesquisa** · *Executor: Claude Code*
- **Tarefas:** criar `research/2026-07-reatividade-metricas/` do template; copiar esboço para dentro; criar `PLANO.md` (este), `PROGRESS.md`, `TAREFAS.md` (seção 9), `config.yaml` (TFs/períodos/splits da seção 3, janelas de sessão com DST, definição candidata do evento e das duas âncoras, parâmetros default do indicador), `requirements.txt`, `scripts/check_tarefas.py`; atualizar índice em `research/README.md`; propor ao usuário a adição das convenções de execução ao `CLAUDE.md`.
- **Saída/Done:** esqueleto commitado; você confirma (ou ajusta) períodos, sessões e critérios C1–C11 — **última chance de mexer neles**.

---

**E1 — Exportador de barras** · *Executor: Claude Code (script) + VOCÊ (MT5)*
- **Tarefas Claude:** script MQL5 em `tools/export_bars/` que exporta OHLCV + tick volume dos 28 pares G8 nos **8 TFs (M5…MN)** para CSV (um arquivo por par×TF, esquema documentado), período lido de input; instruções de uso passo a passo para leigo.
- **Tarefas suas:** compilar, rodar no MT5, conferir os CSVs, colocar em `data/raw/`.
- **Saída/Done:** CSVs presentes; script de inventário confirma cobertura (pares × TFs × período) e reporta buracos (results/E01_inventario.md).

---

**E2 — Pipeline de métricas em Python** · *Executor: Claude Code*
- **Tarefas:** implementar em `scripts/` a cadeia completa: IFM Light → força S → vel, zvel, acel, zS, zMov, zHist, cesta, mtf, VETO, candidata, rank H1 — parâmetros do `config.yaml`, estendida a W1/MN. **Testes unitários com fixtures sintéticas calculadas à mão ANTES de tocar dado real.** Regra de NaN idêntica ao painel (propaga, nunca imputa).
- **Saída/Done:** `pytest` verde; Parquet de métricas gerado para M30–D1 + W1/MN (M5/M15 só depois do P1).

---

**E3 — Verificação de paridade** · **PORTÃO P1** · *Executor: VOCÊ (export do replay) + Claude Code (comparação)*
- **Tarefas suas:** usando o replay do indicador (ou export auxiliar fornecido em E1), extrair os valores do painel para uma janela de ~60 barras × algumas moedas × 2–3 TFs.
- **Tarefas Claude:** comparar ponto a ponto com o Python; relatório `results/E03_paridade.md` no formato checklist do critério **C1**, com os maiores desvios listados e explicados.
- **Portão P1:** você aprova só se C1 fechar. Reprovou → depurar (a causa vai para o relatório) e repetir. **Nada do que vem depois vale sem este carimbo.**

---

**E4 — Gabarito de eventos + banco-mãe** · **PORTÃO P2 (duplo)** · *Executor: Claude Code + VOCÊ (duas auditorias)*
- **Tarefas (ordem interna):**
  1. **Gabarito primeiro:** detectar os eventos de tendência diária (definição do esboço §1.1) com as **duas âncoras candidatas** (§1.2); gerar `results/E04a_gabarito.md` com estatísticas descritivas (eventos/dia, distribuição de magnitudes/durações, sessões onde nascem — leitura em cada figura) + os **20 dias-evento sorteados plotados** para sua auditoria (critério **C2**), comparando as âncoras lado a lado.
  2. 👤 **Auditoria C2:** você escolhe a âncora e aprova (ou manda ajustar e re-sortear). **Definição congelada no `config.yaml`.**
  3. **Banco de estados:** gerar a tabela de estados (métricas t0 + contexto multi-TF com última barra fechada + sessão/minutos-da-sessão + alvos intraday §1.4) e ligá-la ao gabarito; splits físicos treino/validação/`data/sealed/`; relatório de sanidade `results/E04b_auditoria.md` (critério **C3**).
  4. 👤 **Auditoria C3:** 20 linhas conferidas, liberação.
- Depois do P2 aprovado em M30–D1: processar M5/M15 (E1→E4 repetidos mecanicamente, só com relatório de sanidade).

> 💡 **Por que auditar a olho (duas vezes)?** Estatística agregada esconde erro sistemático — uma âncora sistematicamente atrasada ou uma sessão errada por DST em TODAS as linhas parecem "normais" nas distribuições. Vinte casos conferidos pelo seu olho de trader pegam esse tipo de erro melhor que mil testes automáticos. E a auditoria do gabarito é a mais importante da pesquisa inteira: é você calibrando a régua.

---

### BLOCO B — O mapa (sequencial)

**E5 — Q1: a corrida de latências** · **PORTÃO P3 (o mais importante)** · *Executor: Claude Code*
- **Tarefas:** para cada métrica × TF de detecção × sessão: as quatro notas contra o gabarito (bootstrap por dia; C11 onde houver varredura); ranking de agilidade ("% do movimento consumido no disparo"); curvas preliminares de sensibilidade; IC intraday como sanidade coadjuvante; classificação preliminar pelas regras **C4** (reativa) e **C5** (morta); tudo com leituras.
- **Saída:** `results/E05_corrida.md` — a tabela-liga mestre.
- **Portão P3 (decisório, não só aprovação):** com a liga em mãos, VOCÊ decide: ordem de ataque dos ramos do Bloco C; quais métricas/TFs/sessões recebem foco; quais ramos podem ser cortados de saída. Decisões registradas no `PROGRESS.md`.

---

### BLOCO C — Ramos de investigação (independentes; ordem definida no P3; uma sessão cada)

Cada ramo produz `results/EXX_*.md` + mini-conclusão no README + entradas candidatas para `LEITURA.md` (confiança "média"). Ramo fraco pode ser abandonado sem afetar os demais (abandono registrado).

**E6 — Limiares, pós-disparo e exaustão (Q2 → Q3 → Q7)**
- Curvas limiar × (latência, falsos, captura) por métrica × TF × sessão; limiares empíricos vs. atuais (zvel 2.0, zS 1.0, cesta 5, mtf 2); estudo de eventos pós-disparo (acelera/continua/estabiliza/reverte + sobrevivência intraday); exaustão por métrica E por relógio (C6); **veredito do VETO** + versão graduada.

**E7 — Conflitos e hierarquia de TFs (Q5 + Q6)**
- Efeito do contexto (MN/W1/D1) sobre a detecção intraday: alinhado ajuda quanto? contra atrapalha quanto? (C7, C11); conflito precoce como sinal (TF curto virando contra o longo); corrida entre TFs de detecção (M5 vs M15 vs M30 vs H1, custo em falsos); concordância em cascata MN→M5 — onde a cascata para de adicionar? camadas descartadas via C9.

**E8 — Persistência e ciclos de sessão (Q8 + Q9)**
- Vida restante pós-disparo (minutos e ATRs, por sessão); half-life de S por moeda × TF de detecção; custo do atraso do trader (entrar +15 min, +1 h); fases operacionais (expansão/clímax/exaustão/reversão) por regras → validação HMM → matriz de transição **por sessão**; quão cedo cada fase é reconhecível; relógio das sessões (onde tendências nascem e morrem; Tóquio sobrevive a Londres?); sazonalidade hora/dia (DST tratado).

**E9 — Quadrantes e combinações dirigidas (Q4 camadas 1–2)**
- Tabela 2×2 zS (nível) × zvel (evidência) por TF × sessão, com as quatro notas; duplas/trios nomeados do esboço ("arrancada com adesão", "o grande acorda e o pequeno já corre" etc.), sob C11; confronto direto: melhor combinação vs. melhor métrica solo (latência e falsos).

---

### BLOCO D — Síntese (sequencial; depende dos ramos que sobreviveram)

**E10 — Redundância, importância e Score detector (Q11)**
- Correlações + clustering + VIF (C8 → lista de remoções); escada de modelos de **detecção** (logística regularizada → GBM com SHAP → PCA estrutural) em walk-forward, importâncias estáveis entre janelas, avaliação nas quatro notas; fatores novos e camadas de TF só via C9; **tabela de pesos métrica × TF** legível; **Score contínuo 0–100 de detecção CONGELADO** (fórmula fechada, pesos fixos) calibrado em treino+validação apenas.
- Saída: `results/E10_score.md`.

**E11 — Teste selado e regras intraday** · **PORTÃO P4 (final)** · *Executor: Claude Code + VOCÊ presente na decisão*
- **Abertura única de `data/sealed/`.** Avaliar: Score detector vs. regra candidata baseline (critério **C10**, nas quatro notas); regras de entrada/saída intraday derivadas dos ramos vencedores (saídas por fim de sessão/dia, meia-vida ou exaustão — **sem posições overnight**), com custo (spread documentado), profit factor, drawdown e expectativa por trade em walk-forward no alvo A3.
- **Portão P4:** veredito registrado. Score aprovado → variante; reprovado → baseline mantida e o porquê documentado (também é resultado). Achados confirmados no selado sobem para confiança "alta".

> 💡 **Disciplina do teste selado:** este é o único momento em que os dados 2025-10→2026-06 são lidos. Se der vontade de "só ajustar uma coisinha e rodar de novo", a resposta é não — reabrir o selado transformaria a prova final em mais um treino. Ajustes pós-P4 exigem **novo** período selado (dados futuros que ainda não existem).

**E12 — Consolidação** · *Executor: Claude Code*
- README da pesquisa completo (pergunta → método → resultados → conclusão); entradas definitivas em `docs/LEITURA.md` (com confiança e link); índice em `research/README.md`; se Score aprovado: variante `src/variants/` com cabeçalho explicativo; hipóteses refutadas registradas com a mesma dignidade das confirmadas; commit final.

---

## 6. Mapa de dependências e portões

```
E0 → E1(👤MT5) → E2 → E3[P1 👤] → E4[P2 👤 gabarito+banco] → E5[P3 👤 decide ordem]
                                                                ├→ E6 (limiares/pós-disparo/exaustão)
                                                                ├→ E7 (conflitos/hierarquia MN→M5)   → E10 → E11[P4 👤] → E12
                                                                ├→ E8 (persistência/ciclos de sessão)
                                                                └→ E9 (quadrantes/combos)
```
👤 = etapa/portão que precisa de você. Entre portões, o Claude Code trabalha sozinho.

---

## 7. Riscos e planos B (decididos antes, para não improvisar no calor)

| Risco | Plano B |
|---|---|
| **Gabarito reprova na auditoria C2 repetidamente** | Iterar definição/âncora COM novo sorteio a cada rodada (nunca reaproveitar os mesmos 20 dias); se após 3 rodadas não fechar 80%, reduzir a ambição: gabarito só de eventos "óbvios" (magnitude ≥ 1.5 ATR, 7/7 pares) — menos eventos, régua mais confiável. |
| Paridade falha por diferença numérica irredutível (ex.: arredondamento MQL5) | Documentar a divergência; se estável e ≤ 2× o critério C1, você pode aprovar com ressalva registrada; acima disso, a implementação Python é a suspeita até prova contrária. |
| Buracos de dados do broker | Buraco ≤ 3 barras: linha vira NaN (regra padrão). Maiores: janela excluída e reportada no inventário. |
| Poucos eventos em algum recorte (moeda × sessão) para estatística decente | Reportar N por célula em toda tabela; células com N < 30 eventos aparecem esmaecidas com aviso "amostra insuficiente" — nunca omitidas em silêncio, nunca interpretadas como achado. |
| M5/M15 pesados demais para o ambiente | Reduzir para 1 ano ou amostrar 14 pares (2 por moeda), registrando a limitação nas conclusões desses TFs. |
| Nenhuma métrica passa C4 em lugar nenhum | Resultado válido e publicável: "o painel não detecta em tempo útil nos recortes testados" → entrada de LEITURA + repensar definição de evento/limiar de tempo útil em pesquisa futura. Não afrouxar C4 retroativamente. |
| Score reprova no P4 | Baseline mantida; a tabela de pesos e os achados dos ramos continuam valendo como LEITURA (confiança média/alta conforme o caso). |
| Sessão do Claude Code interrompida no meio de uma etapa | `PROGRESS.md` + cache por hash garantem retomada sem retrabalho; etapa só é marcada concluída com commit + results. |

---

## 8. Estrutura final da pasta

```
research/2026-07-reatividade-metricas/
├── README.md          # pergunta → método → resultados → conclusão (preenchido ao longo, fechado em E12)
├── PLANO.md           # este documento (imutável após E0, exceto adendos datados)
├── PROGRESS.md        # memória externa: estado, decisões de portão, próxima etapa
├── TAREFAS.md         # lista de tarefas viva (checkboxes com evidência — modelo na seção 9)
├── config.yaml        # TFs, períodos, sessões, definição do evento/âncora, parâmetros, splits
├── requirements.txt
├── scripts/           # E1 (MQL5), E2 (pipeline), E4 (gabarito+banco), E5–E11 (análises), check_tarefas.py
├── data/              # gitignorado: raw/ (CSVs MT5), parquet intermediário, sealed/
└── results/           # commitado: E03_paridade.md, E04a_gabarito.md, E04b_auditoria.md, E05_corrida.md, ...
```

**Regra de imutabilidade:** após E0, este PLANO.md não muda — desvios necessários são **registrados como adendos datados** no fim do documento (o que mudou, por quê, e o que isso invalida), nunca editados por cima. Exceção única e prevista: a definição do evento/âncora congela no **P2** (não no E0), porque depende da auditoria visual C2 — o congelamento dela é registrado como adendo do P2.

---

## 9. Modelo do `TAREFAS.md` (criado como está abaixo no E0)

```markdown
# TAREFAS — Pesquisa Reatividade das Métricas do IFM (intraday)

Legenda: [ ] pendente · [~] em andamento · [x] concluída (evidência) · [!] bloqueada (motivo) · [-] cancelada (motivo)
Regras: checkbox só marca com evidência · portões P1–P4 só marcam com decisão do usuário no PROGRESS.md
Validação: `python scripts/check_tarefas.py` antes de todo commit (evidências + portões + template didático §1.2)
Última atualização: YYYY-MM-DD · sessão EXX

## BLOCO A — Fundação
### E0 — Setup
- [ ] Pasta da pesquisa criada do template
- [ ] PLANO.md, PROGRESS.md, TAREFAS.md, config.yaml, requirements.txt no lugar
- [ ] config.yaml com: TFs/períodos, janelas de sessão (DST), definição candidata do evento + 2 âncoras, splits
- [ ] scripts/check_tarefas.py criado e rodando (evidências + portões + template didático §1.2)
- [ ] Índice research/README.md atualizado
- [ ] 👤 Períodos, sessões e critérios C1–C11 confirmados pelo usuário (congelamento)
### E1 — Exportador (👤 MT5)
- [ ] Script MQL5 tools/export_bars/ escrito e documentado (8 TFs: M5…MN)
- [ ] 👤 Export rodado no MT5, CSVs em data/raw/
- [ ] Inventário de cobertura sem buracos críticos (results/E01_inventario.md)
### E2 — Pipeline Python
- [ ] Cadeia IFM Light → S → derivadas implementada (config.yaml, sem hard-code, incl. W1/MN)
- [ ] Testes unitários com fixtures sintéticas verdes (pytest)
- [ ] Parquet de métricas M30–D1 + W1/MN gerado
### E3 — Paridade · PORTÃO P1
- [ ] 👤 Export do replay do indicador entregue
- [ ] Relatório results/E03_paridade.md no formato checklist C1
- [ ] 🚪 P1: 👤 paridade APROVADA
### E4 — Gabarito + banco-mãe · PORTÃO P2 (duplo)
- [ ] Eventos detectados com as 2 âncoras candidatas (results/E04a_gabarito.md)
- [ ] 20 dias-evento sorteados e plotados para auditoria
- [ ] 🚪 P2a: 👤 gabarito APROVADO (C2) — âncora escolhida e congelada no config.yaml
- [ ] Banco de estados gerado (métricas t0 + contexto MN→M5 última barra fechada + sessões + alvos intraday)
- [ ] Splits físicos: treino / validação / data/sealed/
- [ ] Relatório de sanidade results/E04b_auditoria.md
- [ ] 🚪 P2b: 👤 banco APROVADO (C3, 20 linhas auditadas)
- [ ] Extensão M5/M15 processada (pós-P2, com relatório de sanidade)

## BLOCO B — O mapa
### E5 — Q1: corrida de latências · PORTÃO P3
- [ ] Quatro notas por métrica × TF de detecção × sessão (bootstrap por dia)
- [ ] Ranking de agilidade + tabela-liga com leituras (results/E05_corrida.md)
- [ ] Classificação preliminar C4 (reativa) / C5 (morta)
- [ ] 🚪 P3: 👤 ordem dos ramos do Bloco C decidida (registrada no PROGRESS.md)

## BLOCO C — Ramos (ordem definida no P3)
### E6 — Limiares, pós-disparo, exaustão e VETO (Q2→Q3→Q7)
- [ ] Curvas limiar × (latência, falsos, captura) por métrica × TF × sessão
- [ ] Limiares empíricos vs. atuais confrontados
- [ ] Estudo de eventos pós-disparo + sobrevivência intraday
- [ ] Exaustão por métrica e por relógio (C6)
- [ ] Veredito do VETO (ajuda / enfeite / atrapalha) + versão graduada testada
- [ ] results/E06_*.md + entradas candidatas a LEITURA.md
### E7 — Conflitos e hierarquia de TFs (Q5+Q6)
- [ ] Efeito do contexto MN/W1/D1 sobre detecção intraday (C7)
- [ ] Conflito precoce como sinal testado
- [ ] Corrida entre TFs de detecção + concordância em cascata MN→M5
- [ ] Camadas descartadas/mantidas via C9
- [ ] results/E07_*.md + entradas candidatas a LEITURA.md
### E8 — Persistência e ciclos de sessão (Q8+Q9)
- [ ] Vida restante pós-disparo + custo do atraso do trader
- [ ] Half-life de S por moeda × TF de detecção
- [ ] Fases por regras + validação HMM + matriz de transição por sessão
- [ ] Relógio das sessões (nascimento/morte de tendências) + sazonalidade
- [ ] results/E08_*.md + entradas candidatas a LEITURA.md
### E9 — Quadrantes e combinações dirigidas (Q4 camadas 1–2)
- [ ] Tabela 2×2 zS × zvel por TF × sessão (quatro notas)
- [ ] Duplas/trios nomeados testados (sob C11)
- [ ] Melhor combinação vs. melhor métrica solo confrontadas
- [ ] results/E09_*.md + entradas candidatas a LEITURA.md

## BLOCO D — Síntese
### E10 — Redundância, importância e Score detector (Q11)
- [ ] Correlações + clustering + VIF → lista de redundâncias (C8)
- [ ] Escada de modelos de detecção em walk-forward + SHAP + PCA
- [ ] Fatores novos / camadas de TF avaliados por ganho incremental (C9)
- [ ] Tabela de pesos métrica × TF + Score 0–100 CONGELADO (results/E10_score.md)
### E11 — Teste selado e regras intraday · PORTÃO P4
- [ ] Abertura ÚNICA de data/sealed/ registrada no PROGRESS.md
- [ ] Score vs. baseline candidata nas quatro notas (C10)
- [ ] Regras intraday de entrada/saída com custo, PF, drawdown (walk-forward, A3, sem overnight)
- [ ] 🚪 P4: 👤 veredito final registrado
### E12 — Consolidação
- [ ] README da pesquisa fechado (pergunta → método → resultados → conclusão)
- [ ] Entradas definitivas em docs/LEITURA.md (com confiança e link)
- [ ] Índice research/README.md atualizado
- [ ] Variante src/variants/ criada (se Score aprovado) OU baseline mantida documentada
- [ ] Hipóteses refutadas registradas
```

**Mecânica de preenchimento automático:** o fluxo de toda sessão do Claude Code é fixo — (1) abrir lendo `PROGRESS.md` + `TAREFAS.md`; (2) marcar `[~]` no que vai atacar; (3) trabalhar; (4) marcar `[x] (evidência)` no que concluiu; (5) rodar `check_tarefas.py` (evidências + portões + **conformidade didática §1.2**); (6) commit único com trabalho + lista + PROGRESS. O validador falhando **bloqueia o commit** — não existe caminho para concluir trabalho sem a lista refletir, nem para entregar resultado sem explicação que o dono da pesquisa entenda.

---

## Adendos

**2026-07-15 (fechamento do E0) — sessões: definição congela, mapeamento para hora do servidor é calibrado no E1.** As janelas de sessão congelam como previsto, mas definidas no **fuso local de cada praça** (IANA: Tóquio 09–18 `Asia/Tokyo`, Londres 08–17 `Europe/London`, NY 08–17 `America/New_York`), e não em hora fixa do servidor. Motivo: o usuário observou aberturas em hora do servidor (Tóquio ~3h ✔; Londres ~12h; NY ~18h) que divergem da teoria (server MetaQuotes = UTC+2/+3 → Londres ~10h, NY ~15h no verão) e são internamente inconsistentes com os candles citados (9º ≈ 8–9h) — e ele próprio marcou a observação como incerta. Em vez de congelar um chute, o mapeamento sessão↔servidor vira **medição do E1**: o exportador grava o offset server↔GMT no `_manifest.csv` e o `e01_inventario.py` gera a assinatura de volume/volatilidade por hora do servidor. O que isso invalida: nada — nenhuma análise depende disso antes do E4; a única consequência é que a confirmação final das janelas de sessão acontece junto com o inventário do E1 (registrada no PROGRESS), não no fechamento do E0. Períodos, splits e critérios C1–C11 foram confirmados pelo usuário em 2026-07-15 sem alteração.

# Changelog — IFM

Todas as versões do indicador `src/IFM.mq5`. Cada versão corresponde a um git tag.

Formato de cada entrada: **o que mudou** e **por quê**. A origem da mudança pode ser **pesquisa** (linkar a pasta em `research/`) ou **direta** (decisão/ideia/correção sem pesquisa prévia — registrar a motivação em texto). Ambas são válidas; nenhuma entrada fica sem motivação.

## v1.2 — 2026-07-16

Aplicação das conclusões da pesquisa [`research/2026-07-reatividade-metricas/`](research/2026-07-reatividade-metricas/) (E0–E12 concluídas; portões P1–P4 carimbados; achados em `docs/LEITURA.md`). Decisão de Rhuan: implementar todas as mudanças sugeridas pela consolidação. **Via pesquisa** — cada item cita a evidência:

- **Sinal em dois níveis no lugar da candidata única.** A candidata original detectava 0% das tendências reais em tempo útil no teste selado (E5/E11, confiança ALTA — "quando acende, a festa acabou"). Agora: **ALERTA** (tinta suave) = `|zS| ≥ 1.0` com lado definido — o sismógrafo da pesquisa (94% de detecção no selado, ~30 min de latência, ~87% de captura restante; precisão baixa → semântica "olhe para cá", não gatilho); **CONFIRMAÇÃO** (destaque forte) = a candidata enxuta (`|zvel| ≥ 2 E |zS| ≥ 1 E cesta ≥ 5/7`), sem VETO e sem mtf.
- **VETO rebaixado a informativo.** Vetados capturavam 74.2% vs 36.3% dos não-vetados (E6.2) — a trava cortava os pullbacks bons. O ✕ continua visível como contexto; não anula mais nada.
- **mtf fora da regra de sinal.** O alinhamento multi-TF não paga o próprio custo em nenhum formato (C7 e C9 zerados em E7; ganho 0% como feature em E10) — vira coluna só de exibição.
- **ALERTA esmaece após `InpLateHour` (15h server).** O relógio é o condicionante mais barato da qualidade do sinal (E6.2/E8/E9: captura ~90% na madrugada → ~11% pós-18h; filtro de hora preserva detecção como nenhum filtro de métrica).
- **Nova coluna `dia%` (consumo do dia).** |movimento de hoje| ÷ média dos dias cheios (régua do zMov): o relógio de exaustão do E6 (captura 94%→11% conforme o consumo) agora é visível por moeda.
- **Nova coluna `SCORE` 0–100 (detector E10, congelado).** Fórmula sigmoide com os pesos de `results/E10_score_pesos.csv` copiados como constantes (base M30 + relógio + alinhamentos W1/MN1 calculados sob demanda); corte p97 = 3.4 (● dourado). Aprovado no selado como detector (C10/P4) e **explicitamente não-sistema** (PF 0.78 com custo) — régua de atenção. Não recalibrar sem novo período selado.
- **Aba padrão da vista MÉTRICAS: M30.** O "TF doce" (E7: M5 empata em velocidade pagando ~6× mais falsos; H1 chega depois).
- **Juiz Market Profile removido do IFM Light.** Era código morto desde a origem (guard de 65 barras com janela de 60 → voto sempre 0; arqueologia E2). A escala ±15 da agregação foi **mantida** — S permanece bit-idêntico à v1.1 e à paridade P1.
- Inputs novos: `InpShowScore` (liga SCORE/dia%) e `InpLateHour` (hora de esmaecimento do alerta).

## v1.1 — 2026-07-16

Descobertas da etapa E3 (paridade) da pesquisa [`research/2026-07-reatividade-metricas/`](research/2026-07-reatividade-metricas/) — ver `PROGRESS.md` (descobertas técnicas 4 e 5) e `results/E03_paridade.md`. Mudança direta (decisão de Rhuan, 2026-07-16):

- **Correção de código — look-ahead no modo replay.** `MetAnchorShift`/`ShiftForTF` em replay ancoravam na barra que **contém** `g_replayTime`; nos TFs acima do gráfico isso lia a barra em formação com os valores FINAIS dela (o "modo VCR honesto" prometido no guia não era honesto nos TFs altos). O modo ao vivo nunca foi afetado. Correção: recuo para a última barra **fechada** até `g_replayTime` (mesma lógica `AnchorAt` da ferramenta `tools/export_golden/ExportGoldenIFM.mq5`, onde foi validada na E3). Efeito colateral correto: o zMov/zHist em replay passa a usar o mesmo dia de referência do modo ao vivo (antes o replay media um dia à frente do vivo).
- **Correção de documentação — zMov/zHist no `IFM_GUIA.md` §10.** A paridade E3 provou (diferença 0.0 em 96/96 amostras) que o dia 0 do zMov/zHist é a **última barra D1 fechada** (intradiário: ontem), medida até a mesma hora decorrida de agora — enquanto o guia descrevia "hoje desde 00:00". **Decisão registrada: o cálculo do indicador é a referência e o guia é que o descreve, não o oposto** — o comportamento do código foi declarado oficial (sem mudança de código) e o §10 foi corrigido para descrevê-lo. Um comentário no bloco zMov do `MetRebuild` fixa a semântica no fonte.

## v1.0 — 2026-07-14

Versão inicial importada para o repositório:

- Motor ML no par ativo: 8 features de RSI, banco de memória kNN (400 linhas), pesos auto-otimizados por critério de Fisher, Supertrend adaptativo, buffers IFM / ML_RSI / Rank / Conf.
- Núcleo de 5 juízes (Pivot, Market Profile via EMA, MFC, ML-RSI, CCI) com variante contínua IFM-Z (juiz CCI substituído por z-score do preço típico).
- Painel multi-moeda G8: IFM Light (4 juízes) em até 28 pares × 6 timeframes, força S por moeda, métricas (vel, zvel, zS, acel, zMov, zHist, cesta, MTF, VETO, candidata), matriz 8x8 com heatmap.
- Sistema de replay com âncora de timestamp universal.

Arquitetura completa documentada em `docs/IFM_GUIA.md`.

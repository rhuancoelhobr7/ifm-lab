# Changelog — IFM

Todas as versões do indicador `src/IFM.mq5`. Cada versão corresponde a um git tag.

Formato de cada entrada: **o que mudou** e **por quê**. A origem da mudança pode ser **pesquisa** (linkar a pasta em `research/`) ou **direta** (decisão/ideia/correção sem pesquisa prévia — registrar a motivação em texto). Ambas são válidas; nenhuma entrada fica sem motivação.

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

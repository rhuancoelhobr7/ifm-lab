# Changelog — IFM

Todas as versões do indicador `src/IFM.mq5`. Cada versão corresponde a um git tag.

Formato de cada entrada: **o que mudou**, **por quê** (com link para a pesquisa em `research/` quando aplicável).

## v1.0 — 2026-07-14

Versão inicial importada para o repositório. `IFM-Z Metrics`:

- Motor ML no par ativo: 8 features de RSI, banco de memória kNN (400 linhas), pesos auto-otimizados por critério de Fisher, Supertrend adaptativo, buffers IFM / ML_RSI / Rank / Conf.
- Núcleo de 5 juízes (Pivot, Market Profile via EMA, MFC, ML-RSI, CCI) com variante contínua IFM-Z (juiz CCI substituído por z-score do preço típico).
- Painel multi-moeda G8: IFM Light (4 juízes) em até 28 pares × 6 timeframes, força S por moeda, métricas (vel, zvel, zS, acel, zMov, zHist, cesta, MTF, VETO, candidata), matriz 8x8 com heatmap.
- Sistema de replay com âncora de timestamp universal.

Arquitetura completa documentada em `docs/IFM_GUIA.md`.

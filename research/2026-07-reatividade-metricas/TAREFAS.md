# TAREFAS — Pesquisa Reatividade das Métricas do IFM (intraday)

Legenda: [ ] pendente · [~] em andamento · [x] concluída (evidência) · [!] bloqueada (motivo) · [-] cancelada (motivo)
Regras: checkbox só marca com evidência · portões P1–P4 só marcam com decisão do usuário no PROGRESS.md
Validação: `python scripts/check_tarefas.py` antes de todo commit (evidências + portões + template didático §1.2)
Última atualização: 2026-07-16 · sessão E4b (banco-mãe — claude de Carlos Eduardo)

## BLOCO A — Fundação
### E0 — Setup
- [x] Pasta da pesquisa criada do template (README.md)
- [x] PLANO.md, PROGRESS.md, TAREFAS.md, config.yaml, requirements.txt no lugar (PLANO.md, PROGRESS.md, config.yaml, requirements.txt)
- [x] config.yaml com: TFs/períodos, janelas de sessão (DST), definição candidata do evento + 2 âncoras, splits (config.yaml)
- [x] scripts/check_tarefas.py criado e rodando (evidências + portões + template didático §1.2) (scripts/check_tarefas.py)
- [x] Índice research/README.md atualizado (research/README.md)
- [x] 👤 Períodos, sessões e critérios C1–C11 confirmados pelo usuário (congelamento) (PROGRESS.md, PLANO.md)
### E1 — Exportador (👤 MT5)
- [x] Script MQL5 tools/export_bars/ escrito e documentado (8 TFs: M5…MN) (tools/export_bars/ExportBarsG8.mq5, tools/export_bars/README.md)
- [x] Script de inventário pronto para rodar sobre os CSVs (scripts/e01_inventario.py)
- [x] 👤 Export rodado no MT5, CSVs em data/raw/ (data/raw/_manifest.csv)
- [x] Inventário de cobertura sem buracos críticos (results/E01_inventario.md)
### E2 — Pipeline Python
- [x] Cadeia IFM Light → S → derivadas implementada (config.yaml, sem hard-code, incl. W1/MN) (scripts/ifm_metrics, scripts/e02_gerar_metricas.py)
- [x] Testes unitários com fixtures sintéticas verdes (pytest) (tests)
- [x] Parquet de métricas M30–D1 + W1/MN gerado (scripts/e02_gerar_metricas.py, PROGRESS.md)
### E3 — Paridade · PORTÃO P1
- [x] Ferramenta de export do replay criada (cópia literal do cálculo v1.0) (tools/export_golden/ExportGoldenIFM.mq5, tools/export_golden/README.md)
- [x] 👤 Export do replay do indicador entregue (golden v2.00, base 2025-09-26) (data/raw/golden_meta.csv)
- [x] Script de comparação pronto com guardas testadas (meta + selado) (scripts/e03_paridade.py)
- [x] Relatório results/E03_paridade.md no formato checklist C1 (results/E03_paridade.md)
- [x] 🚪 P1: 👤 paridade APROVADA (PROGRESS.md, results/E03_paridade.md)
### E4 — Gabarito + banco-mãe · PORTÃO P2 (duplo)
- [x] Eventos detectados com as 2 âncoras candidatas (results/E04a_gabarito.md, results/E04_eventos.csv, scripts/e04a_gabarito.py)
- [x] 20 dias-evento sorteados e plotados para auditoria (results/E04a_amostras)
- [x] 🚪 P2a: 👤 gabarito APROVADO (C2) — âncora A-rompimento escolhida e congelada (PROGRESS.md, config.yaml)
- [x] Banco de estados gerado (métricas t0 + contexto MN1→M30 última barra fechada + sessões + alvos intraday A1–A3; M30 e H1) (scripts/e04b_banco.py, results/E04b_auditoria.md)
- [x] Splits físicos: treino / validação / data/sealed/ (scripts/e04b_banco.py, results/E04b_auditoria.md)
- [x] Relatório de sanidade results/E04b_auditoria.md (results/E04b_auditoria.md, results/E04b_20linhas.csv)
- [x] 🚪 P2b: 👤 banco APROVADO (C3, 20 linhas auditadas por Carlos Eduardo) (PROGRESS.md, results/E04b_auditoria.md)
- [x] Extensão M5/M15 processada (pós-P2, com relatório de sanidade) (results/E04b_auditoria.md, scripts/e04b_banco.py)

## BLOCO B — O mapa
### E5 — Q1: corrida de latências · PORTÃO P3
- [x] Quatro notas por métrica × TF de detecção × sessão (bootstrap por dia) (scripts/e05_corrida.py, results/E05_liga.csv)
- [x] Ranking de agilidade + tabela-liga com leituras (results/E05_corrida.md) (results/E05_corrida.md)
- [x] Classificação preliminar C4 (reativa) / C5 (morta) (results/E05_corrida.md)
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

# PROGRESS — memória externa da pesquisa

> Toda sessão do Claude Code **começa lendo este arquivo** (+ TAREFAS.md) e
> **termina atualizando-o**: onde estamos → o que foi decidido → próxima etapa.
> Nenhuma informação vive só na conversa.

## Onde estamos

**Etapa atual:** E1 e o fecho do E2 travados numa **decisão de dados 👤** (ver pendências). A parte de código do E2 está PRONTA e testada (34 testes verdes, só dados sintéticos); falta apenas gerar o parquet real quando a fonte de dados for decidida.

**⚠️ 2026-07-15 (noite) — o reexport recebido NÃO serve para o plano congelado.** O commit `1465b92` substituiu o `data/raw/` por um export de **outro servidor** (`Upcomers-Server`, antes `MetaQuotes-Demo`) com três problemas fatais: (1) **histórico só desde 2026-01-12** em TODOS os TFs (~6 meses; o config exige 2016/2021/2024 — treino, validação e teste selado ficam impossíveis); (2) **faltam EURUSD, GBPUSD e USDJPY** (o manifest nem os tentou — provável sufixo/ausência no Market Watch do broker novo; sem os majors não há cesta de 7 pares por moeda e o painel G8 quebra); (3) **offset GMT+2 em pleno julho** (MetaQuotes era +3 no verão) — outro regime de fuso, que invalidaria a calibração de sessões congelada. Além disso a substituição **apagou os `golden_*.csv`** (insumo da paridade E3) **e o `server_meta.csv`**. Nada está perdido: o export MetaQuotes-Demo completo (229 arquivos) é recuperável do commit `b7f19a8`.

- **E0 FECHADA em 2026-07-15:** usuário confirmou períodos, splits e critérios C1–C11 sem alteração ("De resto, tudo certo"). Sessões: ver decisão abaixo.
- E1: export recebido (229 arquivos); `e01_inventario.py` rodado → `results/E01_inventario.md` + figura + `results/E01_janelas_excluidas.csv` (janelas de exclusão que o E2/E4 consomem). Cobertura OK em 6 dos 8 TFs; sessões calibradas e congeladas (decisão abaixo). Pendência: M30/H1 vieram de um **export anterior em esquema legado** (coluna `time` em vez de `time_epoch` — o ExportBarsG8 os pulou por já existirem na pasta) e começam em **2022-01-03**, faltando o ano de 2021 que o config congelado exige.

## Decisões registradas

**2026-07-15 — Fechamento do E0 (congelamento).** Períodos/TFs (PLANO §3), splits (treino → 2024-12; validação 2025-01→09; teste selado 2025-10→2026-06) e critérios C1–C11 confirmados pelo usuário como estão.

**2026-07-15 — Sessões: definição congelada em fuso local; hora do servidor será MEDIDA no E1** (adendo no PLANO.md). O usuário observou, sem certeza: Tóquio abre ~3h do server (bate com a teoria UTC+3 no verão), Londres ~12h e NY ~18h (não batem com a teoria ~10h/~15h, nem com os candles H1 que ele citou — 9º ≈ 8–9h, 18º ≈ 17–18h). Em vez de congelar um chute: o exportador grava o offset server↔GMT no `_manifest.csv` e o inventário desenha a assinatura de volume/volatilidade por hora do servidor. A confirmação final das janelas sessão↔servidor acontece com o inventário do E1, junto com o usuário, e será registrada aqui.

**2026-07-15 — Sessões em hora do servidor: CONGELADAS (decidido por Léo; calibração prevista no adendo do PLANO concluída).** Evidência: `results/E01_sessoes_assinatura.png` + verificação verão×inverno (sessão E1). Medição: o servidor MetaQuotes-Demo segue o **DST europeu** (GMT+3 verão / GMT+2 inverno; `offset_server_gmt_h=3.0` no `_manifest.csv`). Aberturas em hora do servidor: **Tóquio 03h (verão) / 02h (inverno); Londres 10h; NY 15h — Londres e NY estáveis o ano todo** (os fusos deles também têm DST; Tóquio não tem e desliza). O salto de volume às 9h é a pré-abertura europeia (Frankfurt), não Londres. A teoria do config confirmou; a observação incerta do usuário (Londres ~12h, NY ~18h) foi **refutada pelos dados**. Registrado em `config.yaml → sessions.calibracao_server` (status `congelado_E1`) e `mt5.server_timezone`.

**2026-07-15 — Autoridade igual (Léo ↔ Rhuan) registrada no CLAUDE.md:** portões P1–P4 e auditorias podem ser carimbados por qualquer um dos dois; o PROGRESS registra QUEM decidiu e a decisão vale para ambos.

**2026-07-15 — Descobertas técnicas da E2 (arqueologia do fonte, para conferir com o Rhuan):**
1. **O juiz Market Profile é código morto no IFM Light** (`IFM.mq5` ~linha 634): o guard exige `copied ≥ 3×21+2 = 65` barras, mas a janela é capada em `LIGHT_WINDOW=60` → o voto MP é sempre 0 e a fórmula efetiva do Light é `Pivot×2 + MFC×1 + CCI-Z×3` (escala bruta continua ±15). O `docs/IFM_GUIA.md` §8 descreve o MP como ativo — **guia dessincronizado do código é bug pela regra 2 do CLAUDE.md**; decidir com o Rhuan: corrigir o guia ou o guard (mudança no indicador = CHANGELOG). O pipeline Python reproduz o comportamento REAL (MP mudo), com o guard implementado e testado para o caso de a janela mudar.
2. **O VETO usa VEL com k=6 fixo** (`MetVel(sr6H4, 6)`, linha ~1146), não `InpMetVelK` — coincidem no default, divergiriam se o input mudasse. Reproduzido fielmente.
3. Divergência deliberada e documentada no zMov/zHist: o fonte alinha "dia i" por contagem de barras D1 de cada par; o pipeline alinha por data de calendário (mais conservador; NaN onde um par pula um dia). Conferir no E3 se algum desvio de paridade cai nesses dias (docstring de `scripts/ifm_metrics/daymove.py`).

## Decisões de portão (P1–P4)

_Nenhuma ainda. Portões só são marcados com decisão do usuário registrada aqui._

**2026-07-15 — `data/raw/` desta pesquisa é VERSIONADO no git** (decisão do usuário, exceção à regra 4 do CLAUDE.md registrada lá e no .gitignore): o repo será compartilhado com um colaborador que rodará fases da pesquisa e precisa dos mesmos CSVs. Derivados regeneráveis (parquet, cache, sealed) continuam gitignorados. Export do usuário recebido em 2026-07-15: 229 arquivos, 549 MB.

## Pendências que dependem do usuário (👤)

- **DECISÃO: qual fonte de dados é a verdade?** Recomendação do Claude: **(a) restaurar o export MetaQuotes-Demo** do commit `b7f19a8` (um comando: `git checkout b7f19a8 -- research/2026-07-reatividade-metricas/data/raw` + commit) e refazer na conta **MetaQuotes-Demo** apenas o reexport de M30/H1 desde 2021-01-01 (apagar os `*_M30.csv`/`*_H1.csv` da pasta `MQL5/Files/IFM_export/` antes, senão o exportador os pula). Alternativa (b): adotar o servidor Upcomers exigiria reescrever os períodos congelados do PLANO (adendo) para ~6 meses de dados, sem os 3 majors — na prática mataria a pesquisa como desenhada. Enquanto não decidido, nenhum script roda sobre o `data/raw/` atual.
- **Confirmar com o Rhuan o formato/origem dos `golden_*.csv`** (export do replay do indicador, insumo da paridade E3) — eles foram apagados na substituição do data/raw; recuperáveis do mesmo commit `b7f19a8`.

## Log de sessões

| Data | Sessão | O que foi feito | Commit |
|---|---|---|---|
| 2026-07-15 | E0 | Esqueleto completo da pesquisa; parâmetros extraídos do fonte; validador criado, testado com violações sintéticas e verde. | fba98fa |
| 2026-07-15 | E0-fecho + E1 (Claude) | E0 carimbada pelo usuário; adendo das sessões no PLANO; exportador MQL5 + README leigo; script de inventário com calibração de sessões; convenções de pesquisa adicionadas ao CLAUDE.md. | 7a13dc2 |
| 2026-07-15 | E1 (inventário — Léo) | Inventário rodado (suporte ao esquema legado M30/H1 + classificação de buracos global×específico + CSV de janelas de exclusão); sessões calibradas verão×inverno e CONGELADAS em hora do servidor; autoridade igual Léo↔Rhuan no CLAUDE.md. Pendência 👤: reexportar M30/H1 desde 2021. | ea6841b |
| 2026-07-15 | E1-verificação do reexport (Léo) | Reexport recebido (`1465b92`) analisado e REPROVADO: outro servidor (Upcomers), 6 meses de histórico, sem os 3 majors, golden/server_meta apagados. Decisão de fonte de dados aberta como pendência 👤; recomendação: restaurar `b7f19a8`. | ddf9b27 |
| 2026-07-15 | E2 (pipeline + testes — Léo) | Cadeia completa do painel em Python (`scripts/ifm_metrics/`: IFM Light, S, cesta, vel/acel/zvel, zS, mtf/VETO/candidata/rank H1, zMov/zHist) + orquestrador `e02_gerar_metricas.py` (cache por hash, trava de proveniência, corte físico do selado já no estágio de métricas). 34 testes verdes: fixtures à mão + vetorizado × porta de referência (tradução literal do MQL5, `reference.py`) + ponta a ponta em raw sintético. Parquet real aguarda a decisão de dados. | (este commit) |

## Próxima etapa

O que o inventário encontrou (2026-07-15):

- **Cobertura:** 28 arquivos em todos os 8 TFs, sem linha inválida, sem duplicata. M5/M15/D1/W1/MN cobrem os períodos pedidos. H4 cobre (1ª barra 2021-01-04 = primeiro pregão do ano; 01/01/2021 caiu numa sexta de feriado). **M30/H1 NÃO cobrem** — export legado desde 2022-01-03 (pendência 👤 acima).
- **Buracos >3 barras:** quase todos são **fechamentos globais** (Natal, Ano-Novo, quedas de feed — os 28 pares apagam juntos) ou feriados em que os pares param em minutos diferentes; viram janelas de exclusão em `results/E01_janelas_excluidas.csv` (regra do PLANO §7), não defeito. Caso a vigiar: **GBPNZD** tem os maiores buracos individuais (ex.: 2 dias inteiros em 2025-09-29→10-01).
- Os `golden_*.csv` seguem aguardando confirmação de formato/origem com o Rhuan (insumo do E3).

Ordem real: (1) 👤 decidir a fonte de dados — restaurar `b7f19a8` e reexportar M30/H1 de 2021 na conta MetaQuotes-Demo; (2) rodar `e01_inventario.py` de novo e fechar E1; (3) rodar `python scripts/e02_gerar_metricas.py` (a parte de código do E2 já está pronta e testada — 34 testes verdes; o parquet sai em minutos quando os dados chegarem) e fechar E2; (4) E3 — paridade contra o replay (`golden_*.csv`, também recuperáveis de `b7f19a8`; confirmar formato com o Rhuan).

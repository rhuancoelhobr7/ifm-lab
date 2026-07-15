# PROGRESS — memória externa da pesquisa

> Toda sessão do Claude Code **começa lendo este arquivo** (+ TAREFAS.md) e
> **termina atualizando-o**: onde estamos → o que foi decidido → próxima etapa.
> Nenhuma informação vive só na conversa.

## Onde estamos

**Etapa atual:** E1 (Exportador) — parte do Claude pronta; **bola com o usuário** (rodar o export no MT5).

- **E0 FECHADA em 2026-07-15:** usuário confirmou períodos, splits e critérios C1–C11 sem alteração ("De resto, tudo certo"). Sessões: ver decisão abaixo.
- E1 (parte Claude): `tools/export_bars/ExportBarsG8.mq5` + README passo a passo escritos; `scripts/e01_inventario.py` pronto para rodar quando os CSVs chegarem (gera `results/E01_inventario.md` + figura de assinatura das sessões).

## Decisões registradas

**2026-07-15 — Fechamento do E0 (congelamento).** Períodos/TFs (PLANO §3), splits (treino → 2024-12; validação 2025-01→09; teste selado 2025-10→2026-06) e critérios C1–C11 confirmados pelo usuário como estão.

**2026-07-15 — Sessões: definição congelada em fuso local; hora do servidor será MEDIDA no E1** (adendo no PLANO.md). O usuário observou, sem certeza: Tóquio abre ~3h do server (bate com a teoria UTC+3 no verão), Londres ~12h e NY ~18h (não batem com a teoria ~10h/~15h, nem com os candles H1 que ele citou — 9º ≈ 8–9h, 18º ≈ 17–18h). Em vez de congelar um chute: o exportador grava o offset server↔GMT no `_manifest.csv` e o inventário desenha a assinatura de volume/volatilidade por hora do servidor. A confirmação final das janelas sessão↔servidor acontece com o inventário do E1, junto com o usuário, e será registrada aqui.

## Decisões de portão (P1–P4)

_Nenhuma ainda. Portões só são marcados com decisão do usuário registrada aqui._

**2026-07-15 — `data/raw/` desta pesquisa é VERSIONADO no git** (decisão do usuário, exceção à regra 4 do CLAUDE.md registrada lá e no .gitignore): o repo será compartilhado com um colaborador que rodará fases da pesquisa e precisa dos mesmos CSVs. Derivados regeneráveis (parquet, cache, sealed) continuam gitignorados. Export do usuário recebido em 2026-07-15: 229 arquivos, 549 MB.

## Pendências que dependem do usuário (👤)

_Nenhuma no momento._

## Log de sessões

| Data | Sessão | O que foi feito | Commit |
|---|---|---|---|
| 2026-07-15 | E0 | Esqueleto completo da pesquisa; parâmetros extraídos do fonte; validador criado, testado com violações sintéticas e verde. | fba98fa |
| 2026-07-15 | E0-fecho + E1 (Claude) | E0 carimbada pelo usuário; adendo das sessões no PLANO; exportador MQL5 + README leigo; script de inventário com calibração de sessões; convenções de pesquisa adicionadas ao CLAUDE.md. | (este commit) |

## Próxima etapa

CSVs já em `data/raw/` (recebidos 2026-07-15). O export veio com BÔNUS não solicitado: `golden_strength.csv` (S por moeda × TF × shift, 401 linhas), `golden_metrics.csv` e `golden_ifm_pairs.csv` — aparentemente o **export do replay do indicador**, insumo do E3/paridade (verificar formato e origem com o usuário antes de usar como verdade). `server_meta.csv` confirma servidor MetaQuotes-Demo = **GMT+3** (offset 10800 s) → teoria das sessões corrobora: Tóquio ~3h, Londres ~10h, NY ~15h server no verão; confirmação final na figura do inventário.

Próxima sessão: **rodar `scripts/e01_inventario.py`** (adiado a pedido do usuário — economia de tokens) → fechar E1 + congelar sessões em hora do servidor → **E2 — Pipeline de métricas em Python**.

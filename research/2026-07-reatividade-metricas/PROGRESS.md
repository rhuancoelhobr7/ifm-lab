# PROGRESS — memória externa da pesquisa

> Toda sessão do Claude Code **começa lendo este arquivo** (+ TAREFAS.md) e
> **termina atualizando-o**: onde estamos → o que foi decidido → próxima etapa.
> Nenhuma informação vive só na conversa.

## Onde estamos

**Etapa atual:** E0 (Setup) — esqueleto pronto, **aguardando o carimbo do usuário**.

O que já existe:
- Pasta `research/2026-07-reatividade-metricas/` criada do template, com ESBOCO.md e PLANO.md copiados para dentro.
- `config.yaml` com TFs/períodos (PLANO §3), splits treino/validação/teste-selado, janelas de sessão em fuso IANA (DST automático), definição candidata do evento + 2 âncoras, parâmetros default extraídos de `src/IFM.mq5` v1.0 (janela 60, ring 64, k=6, zvelN=32, zMovN=20, limiares da candidata) e parâmetros numéricos dos critérios C1–C11.
- `scripts/check_tarefas.py` rodando (evidências + portões + template didático §1.2).
- `TAREFAS.md` pré-populado (modelo do PLANO §9); índice `research/README.md` atualizado.

## Decisões de portão (P1–P4)

_Nenhuma ainda. Portões só são marcados com decisão do usuário registrada aqui._

## Pendências que dependem do usuário (👤)

1. **Fechamento do E0 (última chance de mexer):** confirmar ou ajustar
   períodos/TFs (PLANO §3), janelas de sessão (`sessions` no config.yaml —
   horários candidatos: Tóquio 09–18 JST, Londres 08–17 local, NY 08–17 local)
   e critérios C1–C11. Depois disso, congelado.
2. Itens preenchidos no E1 (não bloqueiam o congelamento): fuso do servidor
   MT5 e sufixo de símbolos do broker (`mt5.*` no config.yaml).

## Log de sessões

| Data | Sessão | O que foi feito | Commit |
|---|---|---|---|
| 2026-07-15 | E0 | Esqueleto completo da pesquisa criado; parâmetros do indicador extraídos do fonte; validador criado e verde. | (este commit) |

## Próxima etapa

**Fechamento do E0** (👤 confirma períodos/sessões/critérios) → **E1 — Exportador de barras**: Claude escreve o script MQL5 em `tools/export_bars/` (28 pares × 8 TFs → CSV) + instruções passo a passo; usuário compila, roda no MT5 e deposita os CSVs em `data/raw/`.

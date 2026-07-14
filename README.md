# IFM Lab

Laboratório de pesquisa e desenvolvimento do **IFM (Índice de Força da Moeda)** — indicador MetaTrader 5 que combina um painel de força das moedas do G8 (28 pares × 6 timeframes) com um motor ML (kNN sobre features de RSI) para o par ativo.

Este repositório reúne o source do indicador, sua documentação de arquitetura e as pesquisas (engenharia e análise de dados) que fundamentam cada modificação.

## Estrutura

```
ifm-lab/
├── src/
│   ├── IFM.mq5          # versão principal do indicador (sempre a mais recente)
│   └── variants/        # variantes experimentais que não são a versão principal
├── docs/
│   └── IFM_GUIA.md      # guia completo da arquitetura (mantido em sincronia com src/IFM.mq5)
├── research/
│   ├── README.md        # índice das pesquisas e convenção de organização
│   └── _template/       # esqueleto para iniciar uma nova pesquisa
├── tools/               # utilitários auxiliares (exportadores de dados MQL5, scripts de apoio)
├── CHANGELOG.md         # histórico de versões do indicador
└── CLAUDE.md            # estado atual, regras e fluxo de trabalho (para o Claude Code)
```

## Versionamento

- `src/IFM.mq5` é **sempre** a versão mais recente — o nome do arquivo nunca carrega rótulo de versão.
- Cada versão liberada recebe um **git tag** (`v1.0`, `v1.1`, ...) e uma entrada no [CHANGELOG.md](CHANGELOG.md).
- Para recuperar uma versão antiga: `git show v1.0:src/IFM.mq5 > IFM_v1.0.mq5`.
- Variantes (linhas de desenvolvimento que não substituem a principal) vivem em `src/variants/` com sufixo próprio (ex.: `IFM-X.mq5`).

## Fluxo de trabalho

Modificações no indicador podem nascer de **pesquisa** ou de **decisão direta** (ideia, correção, ajuste empírico) — pesquisa prévia não é obrigatória.

**Caminho com pesquisa:**

1. **Pergunta** → nasce uma pesquisa em `research/` (ver convenção em [research/README.md](research/README.md)).
2. **Pesquisa** → scripts, dados e resultados ficam na pasta da pesquisa; a conclusão vai no `README.md` dela.
3. **Decisão** → se a conclusão justifica mudança no indicador, a modificação é feita em `src/IFM.mq5` (ou vira variante).
4. **Registro** → CHANGELOG atualizado (com link da pesquisa), `docs/IFM_GUIA.md` sincronizado, commit + tag.

**Caminho direto (sem pesquisa):**

1. **Decisão** → a modificação (ou variante) é implementada diretamente.
2. **Registro** → mesmo rigor: CHANGELOG com a motivação em texto, guia sincronizado, commit + tag.

Em ambos os caminhos, o que é inegociável é o **registro**: toda mudança permanente tem versão, motivação e documentação atualizada.

## Estado atual

- **Versão:** 1.0 (`IFM-Z Metrics`)
- Nenhuma pesquisa iniciada ainda neste repositório.

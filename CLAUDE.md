# CLAUDE.md — ifm-lab

Repositório de pesquisa e desenvolvimento do indicador **IFM** (MetaTrader 5, MQL5). Todo o trabalho técnico é feito pelo Claude Code; o usuário gerencia as pesquisas e decide as modificações.

## Estado atual

- **Versão principal:** v1.0 (`src/IFM.mq5`, nome interno "IFM-Z Metrics", ~2033 linhas).
- **Documentação:** `docs/IFM_GUIA.md` cobre 100% da arquitetura da v1.0.
- **Pesquisas:** nenhuma iniciada ainda.
- **Variantes:** nenhuma ainda.

## Regras invioláveis

1. **`src/IFM.mq5` é sempre a versão mais recente.** O nome do arquivo nunca ganha rótulo de versão. Versões são marcadas com git tag (`v1.0`, `v1.1`, ...) + entrada no `CHANGELOG.md`. Nunca criar duplicatas físicas do arquivo para versionar.
2. **Toda modificação no indicador atualiza `docs/IFM_GUIA.md` no mesmo commit.** Guia dessincronizado é considerado bug.
3. **Modificações permanentes precisam de justificativa registrada** — idealmente apontando para a pesquisa em `research/` que a motivou (no CHANGELOG e na mensagem de commit).
4. **Dados brutos de mercado não entram no git** (barras, ticks, exports grandes). Ficam em `data/` dentro da pasta da pesquisa (gitignorados). Só entram scripts, resultados agregados/pequenos e conclusões.
5. **Variantes** que não substituem a versão principal vão para `src/variants/` com sufixo identificador (ex.: `IFM-X.mq5`). Cada variante deve ter um comentário de cabeçalho explicando no que difere da principal.

## Convenções

- **Pesquisas:** cada uma é uma subpasta autocontida `research/YYYY-MM-slug/` seguindo o template em `research/_template/`. O `README.md` da pesquisa segue o formato *pergunta → método → resultados → conclusão*. O índice em `research/README.md` deve ser atualizado ao criar/concluir uma pesquisa.
- **Versionamento semântico simples:** minor (`v1.1`) para mudanças de comportamento/features; patch (`v1.0.1`) para correções sem mudança de lógica; major (`v2.0`) para reestruturações do núcleo (juízes, motor ML, fórmula da força S).
- **Commits:** mensagem em português, imperativo, primeira linha ≤ 72 chars. Mudanças no indicador referenciam a versão (ex.: `v1.1: ...`).
- **Idioma:** documentação, comentários de pesquisa e commits em **português**. Código MQL5 segue o estilo já existente no `IFM.mq5` (identificadores em inglês, comentários curtos).
- **Python (pesquisas):** cada pesquisa declara suas dependências no próprio `README.md` (ou `requirements.txt` local se for extenso). Nada de venv commitado.

## Fluxo de alteração do indicador

1. Ler a pesquisa/motivação que originou a mudança.
2. Implementar em `src/IFM.mq5` (ou na variante, se for exploratório).
3. Atualizar `docs/IFM_GUIA.md` nas seções afetadas.
4. Atualizar `CHANGELOG.md` (versão, data, o que mudou, por quê, link da pesquisa).
5. Atualizar a seção "Estado atual" deste arquivo.
6. Commit único com tudo + `git tag vX.Y`.
7. Push com tags: `git push --follow-tags`.

## Contexto técnico essencial

- O indicador tem duas metades: **Motor ML** (par ativo, 5 juízes, buffers IFM/ML_RSI/Rank/Conf) e **Painel G8** (IFM Light de 4 juízes, força S por moeda, métricas zvel/zS/zMov/zHist, matriz 8x8). Detalhes completos em `docs/IFM_GUIA.md`.
- MQL5 não compila neste ambiente Linux — a compilação/teste no MetaEditor é feita pelo usuário. Ao modificar o `.mq5`, revisar sintaxe com cuidado extra e avisar o usuário para compilar e reportar warnings/erros.
- Paridade indicador ↔ pesquisa: quando uma pesquisa reimplementa um cálculo do indicador em Python, a paridade numérica deve ser verificada com dados exportados (via `tools/`) antes de tirar conclusões.

# CLAUDE.md — ifm-lab

Repositório de pesquisa e desenvolvimento do indicador **IFM** (MetaTrader 5, MQL5). Todo o trabalho técnico é feito pelo Claude Code; o usuário gerencia as pesquisas e decide as modificações.

## Estado atual

- **Versão principal:** v1.0 (`src/IFM.mq5`, ~2033 linhas).
- **Documentação:** `docs/IFM_GUIA.md` cobre 100% da arquitetura da v1.0; `docs/LEITURA.md` (playbook de interpretação) ainda sem entradas.
- **Pesquisas:** `research/2026-07-reatividade-metricas/` em andamento (E0 — setup; reatividade das métricas do painel G8, perfil intraday). Governança da pesquisa: PLANO.md + TAREFAS.md + PROGRESS.md na pasta da pesquisa; validador `scripts/check_tarefas.py` roda antes de todo commit da pesquisa.
- **Variantes:** nenhuma ainda.

## Regras invioláveis

1. **`src/IFM.mq5` é sempre a versão mais recente.** O nome do arquivo nunca ganha rótulo de versão. Versões são marcadas com git tag (`v1.0`, `v1.1`, ...) + entrada no `CHANGELOG.md`. Nunca criar duplicatas físicas do arquivo para versionar.
2. **Toda modificação no indicador atualiza `docs/IFM_GUIA.md` no mesmo commit.** Guia dessincronizado é considerado bug.
3. **Modificações permanentes precisam de justificativa registrada no CHANGELOG e na mensagem de commit.** Há dois caminhos válidos: **via pesquisa** (a entrada aponta para a pesquisa em `research/` que a motivou) e **direta** (ideia, correção, ajuste empírico ou decisão do usuário — sem pesquisa prévia; a entrada registra a motivação em texto). Pesquisa não é pré-requisito para modificar o indicador; justificativa registrada é.
4. **Dados brutos de mercado não entram no git** (barras, ticks, exports grandes). Ficam em `data/` dentro da pasta da pesquisa (gitignorados). Só entram scripts, resultados agregados/pequenos e conclusões. *Exceção registrada (2026-07-15): o `data/raw/` da pesquisa `2026-07-reatividade-metricas` é versionado por decisão do usuário — repo compartilhado com colaborador que precisa dos mesmos CSVs. Derivados (parquet/cache/sealed) continuam fora.*
5. **Variantes** que não substituem a versão principal vão para `src/variants/` com sufixo identificador (ex.: `IFM-X.mq5`). Cada variante deve ter um comentário de cabeçalho explicando no que difere da principal.

## Convenções

- **Pesquisas:** cada uma é uma subpasta autocontida `research/YYYY-MM-slug/` seguindo o template em `research/_template/`. O `README.md` da pesquisa segue o formato *pergunta → método → resultados → conclusão*. O índice em `research/README.md` deve ser atualizado ao criar/concluir uma pesquisa.
- **Destinos de uma conclusão de pesquisa:** (a) mudança no indicador (`src/IFM.mq5` + CHANGELOG); (b) variante (`src/variants/`); (c) **mudança de leitura** — o resultado altera como interpretamos/usamos o indicador sem tocar no código: vira entrada em `docs/LEITURA.md` (com link para a pesquisa e nível de confiança); (d) descarte — hipótese refutada/inconclusiva, registrada na própria pesquisa. Pesquisa relevante sem mudança de código é um desfecho normal, não uma pesquisa "incompleta".
- **Versionamento semântico simples:** minor (`v1.1`) para mudanças de comportamento/features; patch (`v1.0.1`) para correções sem mudança de lógica; major (`v2.0`) para reestruturações do núcleo (juízes, motor ML, fórmula da força S).
- **Commits:** mensagem em português, imperativo, primeira linha ≤ 72 chars. Mudanças no indicador referenciam a versão (ex.: `v1.1: ...`).
- **Idioma:** documentação, comentários de pesquisa e commits em **português**. Código MQL5 segue o estilo já existente no `IFM.mq5` (identificadores em inglês, comentários curtos).
- **Nome do indicador:** o indicador se chama apenas **IFM** (arquivo `IFM.mq5`), na documentação e no código (shortname, título da topbar, logs) — não usar apelidos ou nomes decorativos. "IFM-Z" permanece apenas como nome do *modo* do núcleo (`InpZCore`), em oposição a "IFM clássico".
- **Python (pesquisas):** cada pesquisa declara suas dependências no próprio `README.md` (ou `requirements.txt` local se for extenso). Nada de venv commitado.

## Fluxo de alteração do indicador

A mudança pode nascer de dois jeitos — ambos seguem os mesmos passos abaixo:

- **Via pesquisa:** a conclusão de uma pesquisa em `research/` justifica a mudança.
- **Direta:** o usuário decide a mudança sem pesquisa prévia — modificação, variante ou entrada de leitura em `docs/LEITURA.md`. Nesse caso a motivação é registrada em texto no CHANGELOG (e no cabeçalho da variante, se for variante); se for só entrada de leitura, a motivação vai na própria entrada, com confiança tipicamente "hipótese a confirmar".

1. Entender a motivação da mudança (pesquisa ou decisão direta).
2. Implementar em `src/IFM.mq5` (ou na variante, se for exploratório).
3. Atualizar `docs/IFM_GUIA.md` nas seções afetadas.
4. Atualizar `CHANGELOG.md` (versão, data, o que mudou, por quê — com link da pesquisa quando houver, ou a motivação direta quando não).
5. Atualizar a seção "Estado atual" deste arquivo.
6. Commit único com tudo + `git tag vX.Y`.
7. Push com tags: `git push --follow-tags`.

## Execução de pesquisas (convenções)

- **Autoridade do projeto (registrado 2026-07-15):** Léo e Rhuan têm autoridade **igual** sobre o projeto e as pesquisas. Portões P1–P4 e auditorias podem ser carimbados por **qualquer um dos dois**; a decisão registrada no `PROGRESS.md` indica **quem** decidiu e vale para ambos.
- Toda sessão de trabalho numa pesquisa **abre lendo** `PROGRESS.md` + `TAREFAS.md` da pesquisa e **fecha com commit único** (trabalho + TAREFAS + PROGRESS) após `python scripts/check_tarefas.py` verde — o validador falhando bloqueia o commit.
- Checkbox de tarefa só marca `[x]` com **evidência verificável** (arquivo no repo ou hash de commit). Portões (decisões do usuário) só marcam com a decisão registrada no `PROGRESS.md`.
- Relatórios em `results/` seguem o **template didático** do PLANO da pesquisa: seções obrigatórias, linha `**Leitura:**` após cada tabela/figura, confronto explícito com os critérios congelados.
- O bloco de **teste selado** (`data/sealed/`) só é lido na etapa final prevista no PLANO; scripts de análise recusam esse caminho.
- O PLANO da pesquisa é **imutável** após o setup — desvios viram adendos datados, nunca edição por cima.

## Contexto técnico essencial

- O indicador tem duas metades: **Motor ML** (par ativo, 5 juízes, buffers IFM/ML_RSI/Rank/Conf) e **Painel G8** (IFM Light de 4 juízes, força S por moeda, métricas zvel/zS/zMov/zHist, matriz 8x8). Detalhes completos em `docs/IFM_GUIA.md`.
- MQL5 não compila neste ambiente Linux — a compilação/teste no MetaEditor é feita pelo usuário. Ao modificar o `.mq5`, revisar sintaxe com cuidado extra e avisar o usuário para compilar e reportar warnings/erros.
- Paridade indicador ↔ pesquisa: quando uma pesquisa reimplementa um cálculo do indicador em Python, a paridade numérica deve ser verificada com dados exportados (via `tools/`) antes de tirar conclusões.

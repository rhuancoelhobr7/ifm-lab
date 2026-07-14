# Pesquisas

Cada pesquisa é uma subpasta autocontida no formato `YYYY-MM-slug/` (ex.: `2026-08-calibracao-zvel/`), criada a partir do esqueleto em [`_template/`](_template/).

## Convenção

Estrutura interna de uma pesquisa:

```
YYYY-MM-slug/
├── README.md      # pergunta → método → resultados → conclusão (obrigatório)
├── scripts/       # código da pesquisa (Python, MQL5 de export, etc.)
├── data/          # dados brutos usados (GITIGNORADO — não sobe para o repo)
└── results/       # saídas pequenas: tabelas agregadas, gráficos, CSVs de resumo
```

Regras:

- O `README.md` da pesquisa é o produto principal: alguém que leia só ele deve entender o que foi perguntado, como foi testado e o que se concluiu — sem rodar nada.
- Dados brutos (barras, ticks, exports grandes) ficam em `data/` e **não são commitados**. O README documenta como regenerá-los (qual script de `tools/` ou da pesquisa, símbolo, período).
- Resultados que sustentam a conclusão (tabelas finais, figuras) são pequenos e **são commitados** em `results/`.
- Pesquisa que motivou mudança no indicador é referenciada no `CHANGELOG.md` da raiz.
- Ao criar ou concluir uma pesquisa, atualizar o índice abaixo.

## Índice

| Pesquisa | Pergunta | Status | Conclusão |
|---|---|---|---|
| _(nenhuma ainda)_ | | | |

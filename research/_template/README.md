# [Título da pesquisa]

> **Status:** em andamento | concluída | abandonada
> **Período:** YYYY-MM-DD → YYYY-MM-DD
> **Relacionada a:** [versão do indicador / outra pesquisa, se houver]

## Pergunta

O que queremos descobrir, em uma ou duas frases. Se possível, formulada de modo falseável ("X melhora Y?" e não "explorar X").

## Método

- Dados usados (símbolos, timeframes, período) e como regenerá-los.
- Scripts e o que cada um faz.
- Métricas de avaliação e critérios de decisão definidos **antes** de olhar os resultados.

## Resultados

Tabelas/figuras principais (arquivos em `results/`), com leitura objetiva de cada uma.

## Conclusão

- Resposta à pergunta.
- Decisão tomada e link para o que foi feito. Destinos possíveis:
  - **Mudança no indicador** → `src/IFM.mq5` + CHANGELOG;
  - **Variante** → `src/variants/`;
  - **Mudança de leitura** → nova entrada em `docs/LEITURA.md` (o resultado muda como interpretamos/usamos o indicador, não o código);
  - **Descarte** → hipótese refutada ou inconclusiva (registrar mesmo assim — saber o que *não* funciona é resultado).
- Limitações e o que ficou em aberto.

# Reatividade das métricas do painel G8 (perfil intraday)

> **Status:** em andamento (E1 — export de dados; aguardando MT5 do usuário)
> **Período:** 2026-07-15 → (em curso)
> **Relacionada a:** IFM v1.0 (`src/IFM.mq5`) — painel G8 (força S e derivadas). O motor ML kNN do par ativo fica **fora** (vira pesquisa própria depois).
> **Documentos-mãe:** [ESBOCO.md](ESBOCO.md) (o quê e por quê) · [PLANO.md](PLANO.md) (como, critérios congelados C1–C11, etapas E0–E12) · [config.yaml](config.yaml) (parâmetros congelados) · [TAREFAS.md](TAREFAS.md) (estado real, com evidências) · [PROGRESS.md](PROGRESS.md) (memória externa)

## Pergunta

Dado que uma tendência intraday real de uma moeda **já começou** (Premissa P1), quão rápido — e com que confiabilidade — cada métrica do painel (S, zS, vel, zvel, acel, zMov, zHist, cesta, mtf, VETO), cada timeframe (MN→M5) e cada combinação a sinaliza, e **quanto do movimento ainda resta para operar** quando o sinal acende?

💡 É uma pesquisa de **detecção, não de previsão** (sismógrafo, não bola de cristal — ESBOÇO, Premissa P3): a nota de cada métrica tem quatro partes — latência, taxa de detecção, alarmes falsos e captura restante.

## Método

Resumo (detalhes e critérios congelados no [PLANO.md](PLANO.md)):

1. **Fundação (E0–E4):** exportar barras dos 28 pares G8 em 8 TFs (M5…MN) do MT5; reimplementar a cadeia IFM Light → S → derivadas em Python; **paridade** indicador ↔ Python aprovada (C1) antes de qualquer conclusão; construir o **gabarito** de eventos de tendência diária (auditado a olho, C2) e o banco-mãe estados+eventos em Parquet, com teste selado fisicamente separado em `data/sealed/`.
2. **Mapa (E5):** a corrida de latências — as quatro notas por métrica × TF × sessão contra o gabarito.
3. **Ramos (E6–E9):** limiares/pós-disparo/exaustão/VETO; conflitos e hierarquia de TFs; persistência e ciclos de sessão; quadrantes e combinações dirigidas.
4. **Síntese (E10–E12):** redundância → importância → Score detector 0–100, veredito no teste selado (aberto UMA vez), tradução em regras intraday e entradas em `docs/LEITURA.md`.

- **Dados:** CSVs exportados do MT5 ficam em `data/` (gitignorado); como regenerar: script de `tools/export_bars/` (criado no E1), período e TFs do `config.yaml`.
- **Critérios de decisão:** congelados ANTES de olhar dados — tabela C1–C11 no PLANO §4.
- **Regra de ouro:** todo resultado sai com "**Leitura:**" em linguagem simples; validado por `scripts/check_tarefas.py`.

## Resultados

_(preenchido ao longo das etapas — cada `results/EXX_*.md` traz tabelas/figuras com leitura)_

## Conclusão

_(aberta — fechada no E12; hipóteses refutadas serão registradas com a mesma dignidade das confirmadas)_

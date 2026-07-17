# Reatividade das métricas do painel G8 (perfil intraday)

> **Status:** ✅ CONCLUÍDA (2026-07-16) — 🚪 P4 carimbado por Carlos Eduardo: **o Score é detector, não sistema; baseline mantida no painel**
> **Período:** 2026-07-15 → 2026-07-16
> **Relacionada a:** IFM v1.0→v1.1 (`src/IFM.mq5`) — painel G8 (força S e derivadas). O motor ML kNN do par ativo ficou **fora** (vira pesquisa própria depois).
> **Documentos-mãe:** [ESBOCO.md](ESBOCO.md) (o quê e por quê) · [PLANO.md](PLANO.md) (como, critérios congelados C1–C11, etapas E0–E12) · [config.yaml](config.yaml) (parâmetros congelados) · [TAREFAS.md](TAREFAS.md) (estado real, com evidências) · [PROGRESS.md](PROGRESS.md) (memória externa)
> **Produto de leitura:** 10 entradas definitivas em [docs/LEITURA.md](../../docs/LEITURA.md)

## Pergunta

Dado que uma tendência intraday real de uma moeda **já começou** (Premissa P1), quão rápido — e com que confiabilidade — cada métrica do painel (S, zS, vel, zvel, acel, zMov, zHist, cesta, mtf, VETO), cada timeframe (MN→M5) e cada combinação a sinaliza, e **quanto do movimento ainda resta para operar** quando o sinal acende?

💡 É uma pesquisa de **detecção, não de previsão** (sismógrafo, não bola de cristal — ESBOÇO, Premissa P3): a nota de cada métrica tem quatro partes — latência, taxa de detecção, alarmes falsos e captura restante.

## Método

Resumo (detalhes e critérios congelados no [PLANO.md](PLANO.md)):

1. **Fundação (E0–E4):** barras dos 28 pares G8 em 8 TFs (M5…MN) exportadas do MT5 (conta MetaQuotes-Demo, sessões calibradas empiricamente em hora do servidor); cadeia IFM Light → S → derivadas reimplementada em Python com **paridade bit-a-bit** contra o replay do indicador (C1/P1: 100% dos pontos, erro máx 0.0000); **gabarito** de 323 eventos de tendência diária (magnitude ≥ 1 ATR, ≥ 6/7 pares, ER ≥ 0.30), âncora **A-rompimento** auditada a olho e congelada (C2/P2a); banco-mãe (t × moeda) com métricas t0, contexto multi-TF por última barra fechada, sessões e alvos A1–A3 (C3/P2b), splits físicos com teste selado em `data/sealed/`.
2. **Mapa (E5):** corrida de latências — as quatro notas por métrica × TF × limiar contra o gabarito.
3. **Ramos (E6–E9):** varredura de limiares com BH (C11) + pós-disparo/exaustão/VETO; conflitos e hierarquia de TFs (maré×marola, cascata MN→M5); persistência e ciclos de sessão (vida restante, half-life, fases, relógio); quadrantes e combinações nomeadas.
4. **Síntese (E10–E11):** redundância (C8) → escada logística→LightGBM em walk-forward → **Score 0–100 congelado** → teste selado aberto UMA vez (C10/P4).

- **Dados:** TODO o `data/` é versionado (decisão de Rhuan, 2026-07-16 — raw, parquet, banco, sealed); reprodutibilidade verificada por hash entre máquinas (`763beb9d23a1`).
- **Critérios de decisão:** congelados ANTES de olhar dados — tabela C1–C11 no PLANO §4.
- **Regra de ouro:** todo resultado sai com "**Leitura:**" em linguagem simples; validado por `scripts/check_tarefas.py`.

## Resultados

Cada relatório em `results/` traz tabelas com leitura; síntese por etapa:

| Etapa | Relatório | Achado central |
|---|---|---|
| E1 | [E01_inventario.md](results/E01_inventario.md) | Cobertura 28/28 nos 8 TFs; sessões congeladas em hora do servidor (Tóquio 03h verão/02h inverno, Londres 10h, NY 15h — DST europeu do broker) |
| E3 | [E03_paridade.md](results/E03_paridade.md) | Paridade Python↔indicador 100% (P1); descobertas 4 e 5 sobre o indicador (zMov mede o último D1 fechado — oficializado na v1.1; look-ahead do replay — corrigido na v1.1) |
| E4 | [E04a_gabarito.md](results/E04a_gabarito.md) · [E04b_auditoria.md](results/E04b_auditoria.md) | 323 eventos (284 treino/39 validação), âncora A-rompimento 20/20 na auditoria; banco aprovado (NaN pior 6.2%) |
| E5 | [E05_corrida.md](results/E05_corrida.md) | Métricas de nível detectam MUITO e CEDO (zS M30: 82%, 15 min, 8% consumido) mas precisão ~1%; **a regra "candidata" do painel é morta (C5)** — detecção 0–2.6% |
| E6 | [E06_limiares.md](results/E06_limiares.md) · [E06_posdisparo.md](results/E06_posdisparo.md) | Métrica-solo NÃO tem ponto de operação (268 células, nenhuma sobrevive BH com detecção útil — o trade-off é estrutural); exaustão monotônica por % consumido e por relógio; **VETO atrapalha** (vetados capturam 74% vs 36%) |
| E7 | [E07_contexto.md](results/E07_contexto.md) · [E07_cascata.md](results/E07_cascata.md) | **A maré não manda na marola** (C7 zerado; 54% dos eventos nascem contra o MN1 e rendem igual); cascata MN→M5 reprovada (C9 zerado); **M30 empata com M5 em velocidade** pagando 6× menos falsos; conflito precoce refutado |
| E8 | [E08_sessoes.md](results/E08_sessoes.md) | Disparo em Tóquio deixa ~900 min/1.0 ATR de estrada e atraso barato (+30min ≈ 2.4 p.p.); NY é caro (~20 p.p.); half-life de S homogêneo (~1.5h M30/~0.75h H1); fases com validação k-means 67.8%; 84% das tendências de Tóquio sobrevivem à troca de turno |
| E9 | [E09_combos.md](results/E09_combos.md) | Confluência binária corta falsos mas cobra detecção; **filtro de HORA é mais barato que filtro de métrica**; nenhuma combinação fecha C4 — o caminho é ponderação contínua |
| E10 | [E10_score.md](results/E10_score.md) | Score 0–100 congelado (logística walk-forward; pesos em [E10_score_pesos.csv](results/E10_score_pesos.csv)); LightGBM chega a 4.7–5.7% de precisão (≈3× as regras binárias); contexto multi-TF não paga como feature (C9 ✘, coerente com E7); zvel×vel redundantes (C8) |
| E11 | [E11_selado.md](results/E11_selado.md) | **Selado (50 eventos): Score generaliza** (26.5% detecção, 30 min, 86.7% captura, 3.5% precisão) e **vence a baseline pelo C10** (baseline: 0% — morta também fora-da-amostra); regra intraday mínima com custo: PF 0.78 → não é sistema |

## Conclusão

**O painel G8 é um sismógrafo honesto com o gatilho errado.** As quatro conclusões que a pesquisa sustenta:

1. **Detectar cedo é fácil; disparar com precisão é estruturalmente difícil.** O zS cruza cedo (94% dos eventos no selado, 30 min de latência, ~89% de captura restante) — mas nenhum formato testado (limiar solo, confluência E/OU, filtro de contexto, filtro de sessão) tira a precisão da faixa de 1–4%: os disparos fora de evento dominam em qualquer régua. A ponderação contínua (Score) triplica a precisão, e ainda fica longe do piso de 40% do C4. Leitura prática: **os sinais do painel são alertas de atenção, não gatilhos de entrada**.
2. **A regra "candidata" atual do painel está morta — e o VETO atrapalha.** A candidata detecta 0–2.6% dos eventos em tempo útil (0% no selado, confiança ALTA): quando acende, a festa já acabou. O VETO corta os disparos BONS (pullbacks de moedas fortes). A reforma da regra candidata fica marcada como mudança futura do indicador (via CHANGELOG, fora do escopo desta pesquisa).
3. **O relógio vale mais que o contexto.** A hora do dia (sessão, % consumido) é o condicionante mais barato da qualidade do sinal — enquanto o contexto multi-TF (MN/W1/D1) não paga o próprio custo nem como filtro (E7) nem como feature (E10). Tóquio é onde as tendências nascem com estrada pela frente; depois das 15h o alarme chega tarde.
4. **O Score 0–100 congelado é um detector aprovado (C10), não um sistema de trading (P4).** Ele generalizou no selado e venceu a baseline, mas a regra mínima de execução com custo dá PF 0.78 — **sem variante `src/variants/`; a baseline segue no painel**. O Score fica como régua de pesquisa e candidato a camada de "atenção" numa reforma futura.

### Hipóteses refutadas (com a mesma dignidade das confirmadas)

- **"Contexto alinhado melhora a detecção intraday"** — refutada (E7/E10: C7 e C9 zerados; 54% dos eventos nascem contra a maré e rendem igual).
- **"TF curto virando contra o longo é alerta precoce"** — refutada e invertida (E7: é o evento ALINHADO que o zS antecipa — 77% vs 61% no M30).
- **"TF mais fino dispara antes"** — refutada para M5 vs M30 (E7: empate pareado por evento, 6× mais falsos).
- **"O VETO protege de entradas ruins"** — refutada (E6.2: vetados capturaram MAIS — 74.2% vs 36.3%).
- **"Existe limiar que torna a métrica-solo operável"** — refutada (E6.1: 268 células, nenhuma sobrevive BH com detecção suficiente).
- **"A regra candidata do painel é um detector útil"** — refutada com confiança ALTA (C5 na liga; 0% no selado).

### Confiança dos achados

- **ALTA (confirmados no selado):** candidata morta; zS detecta cedo com captura alta; Score generaliza e vence C10; regra mínima não paga custo (detector ≠ sistema).
- **MÉDIA (treino+validação):** exaustão por relógio/% consumido, veredito do VETO, contexto não paga, conflito precoce invertido, M30 ⊇ M5, half-life, fases/sessões. ⚠ Nota de honestidade (E12): o texto do P4 listou "exaustão por relógio" e "VETO atrapalha" como ALTA, mas o `e11_selado.py` não re-mediu esses recortes no selado — pela definição congelada do PLANO §3 (alta = confirmado NO selado), essas entradas ficam MÉDIA; elevar exigiria novo período selado.

### Destinos (convenção do repo)

- **Mudança de leitura:** 10 entradas definitivas em [docs/LEITURA.md](../../docs/LEITURA.md).
- **Variante:** NÃO criada (P4) — baseline mantida; motivo documentado acima e no PROGRESS.
- **Mudança no indicador (futura, fora do escopo):** reforma da regra candidata + VETO marcada; look-ahead do replay já corrigido na v1.1 como subproduto da paridade (E3).
- **Pesquisa futura sugerida:** motor ML kNN do par ativo; HMM/SHAP como verificações opcionais (wheels indisponíveis no Windows/Py3.14 do Carlos Eduardo; a máquina Linux do Rhuan pode rodá-los).

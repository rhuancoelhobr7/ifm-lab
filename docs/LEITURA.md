# Leitura do IFM — conhecimento validado

Playbook de **como interpretar e usar o indicador**, construído a partir de conclusões de pesquisa (ou observações registradas) que **não exigem mudança no código**.

Enquanto o `IFM_GUIA.md` documenta *o que o indicador calcula*, este arquivo documenta *o que fazer com o que ele mostra*: regras de leitura, combinações de métricas que funcionam (ou não), contextos em que um sinal vale mais ou menos, armadilhas de interpretação.

Formato de cada entrada:

- **O que sabemos** — a regra/insight de leitura, em linguagem direta.
- **De onde veio** — link para a pesquisa em `research/` (ou motivação direta, se for observação sem pesquisa).
- **Confiança** — alta / média / hipótese a confirmar.

Entradas podem ser revisadas ou revogadas por pesquisas posteriores — nesse caso, a entrada antiga é atualizada (não apagada), com nota do que a substituiu.

---

_As 10 entradas abaixo vêm da pesquisa [2026-07-reatividade-metricas](../research/2026-07-reatividade-metricas/) (consolidação E12, 2026-07-16). Régua comum: eventos = tendências diárias reais do gabarito auditado (magnitude ≥ 1 ATR, ≥ 6/7 pares); "detecção" = sinal antes de 50% do movimento consumido; detector de referência = cruzamento direcional de zS ≥ 1.0._

## 1. Os sinais do painel são alertas de atenção, NÃO gatilhos de entrada

- **O que sabemos:** nenhum formato de disparo testado — limiar solo (268 células), confluência E/OU, filtro de contexto multi-TF, filtro de sessão — tira a precisão da faixa de 1–4% (o C4 pedia 40%). O trade-off detecção×precisão do painel é estrutural, não de calibração: em qualquer altura de régua, os cruzamentos fora de evento dominam. Trate todo acendimento como "olhe para cá", nunca como "entre agora".
- **De onde veio:** [E06_limiares](../research/2026-07-reatividade-metricas/results/E06_limiares.md), [E09_combos](../research/2026-07-reatividade-metricas/results/E09_combos.md), [E10_score](../research/2026-07-reatividade-metricas/results/E10_score.md).
- **Confiança:** média (treino+validação; o Score, único formato levado ao selado, manteve o padrão — 3.5%).

## 2. zS é o sismógrafo do painel: cedo, com estrada pela frente

- **O que sabemos:** quando a tendência diária é real, o zS no M30 cruza 1.0 em mediana 15–30 min após o rompimento, com só ~8% do movimento consumido e ~87–92% de captura restante — detecção de 82% (validação) a 94% (selado). É a melhor métrica-antena do painel; cesta/vel/zvel vêm na mesma família, mais tarde.
- **De onde veio:** [E05_corrida](../research/2026-07-reatividade-metricas/results/E05_corrida.md), [E11_selado](../research/2026-07-reatividade-metricas/results/E11_selado.md).
- **Confiança:** **alta** (confirmado no teste selado).

## 3. A regra "candidata" atual é conservadora demais — quando acende, a festa acabou

- **O que sabemos:** a candidata (|zvel|≥2 E |zS|≥1 E cesta≥5/7 E mtf≥2/4 E sem VETO) detecta 0–2.6% dos eventos em tempo útil na liga e **0% no selado**. Não usar como sinal de entrada em tendência intraday; a reforma da regra fica marcada como mudança futura do indicador.
- **De onde veio:** [E05_corrida](../research/2026-07-reatividade-metricas/results/E05_corrida.md), [E11_selado](../research/2026-07-reatividade-metricas/results/E11_selado.md).
- **Confiança:** **alta** (confirmado no teste selado).

## 4. O VETO atrapalha — não use como bloqueio

- **O que sabemos:** nos disparos de moedas top-2 do lado, os VETADOS capturaram mediana 74.2% vs 36.3% dos não-vetados: o VETO corta justamente os pullbacks bons de moedas fortes. A versão graduada (nº de TFs maiores contra) confirma o sentido. Ler o VETO no máximo como informação de contexto, nunca como proibição.
- **De onde veio:** [E06_posdisparo](../research/2026-07-reatividade-metricas/results/E06_posdisparo.md).
- **Confiança:** média (treino+validação; não re-medido no selado — elevar exigiria novo período selado).

## 5. O relógio manda mais que qualquer métrica

- **O que sabemos:** a qualidade do alarme decai monotonicamente com a hora do servidor (captura mediana ~90% nos disparos de 0–6h → ~11% depois das 18h) e com o % já consumido (94%→11%). O filtro de HORA foi o condicionante mais barato de todos os testados (mantém detecção cortando falsos pela metade). Depois das 15h (abertura de NY), alarme novo = provável exaustão.
- **De onde veio:** [E06_posdisparo](../research/2026-07-reatividade-metricas/results/E06_posdisparo.md), [E08_sessoes](../research/2026-07-reatividade-metricas/results/E08_sessoes.md), [E09_combos](../research/2026-07-reatividade-metricas/results/E09_combos.md).
- **Confiança:** média (gradiente forte e consistente nos dois splits; nenhum bucket fechou o C6 formal por margem mínima).

## 6. Disparo em Tóquio deixa estrada; atraso é barato de manhã e caro à tarde

- **O que sabemos:** o 1º disparo válido em Tóquio deixa mediana de ~900 min e ~1.0 ATR de movimento pela frente, e entrar 30 min atrasado custa só ~2.4 p.p. da magnitude; em NY o mesmo atraso custa ~20 p.p. E 84% das tendências nascidas em Tóquio só fazem o extremo do dia DEPOIS das 10h (Londres em diante) — a tendência da madrugada costuma sobreviver à troca de turno.
- **De onde veio:** [E08_sessoes](../research/2026-07-reatividade-metricas/results/E08_sessoes.md).
- **Confiança:** média (Tóquio robusto; Londres/NY com amostra fina — N<30 na validação).

## 7. O contexto multi-TF (maré) não paga o que custa na detecção intraday

- **O que sabemos:** o alinhamento de MN/W1/D1 NÃO muda as notas do detector (efeitos ≤9%, C7 zerado); ~54% das tendências diárias nascem CONTRA a maré mensal e rendem a mesma magnitude; como filtro em cascata, nenhuma camada passa o C9 (a detecção desaba sem a precisão sair do lugar); como feature do Score, ganho zero. Ignorar a maré ao julgar um alerta intraday não perde nada mensurável.
- **De onde veio:** [E07_contexto](../research/2026-07-reatividade-metricas/results/E07_contexto.md), [E07_cascata](../research/2026-07-reatividade-metricas/results/E07_cascata.md), [E10_score](../research/2026-07-reatividade-metricas/results/E10_score.md).
- **Confiança:** média (três verificações independentes convergem).

## 8. "Conflito precoce" ao contrário: é o dia ALINHADO que o zS antecipa

- **O que sabemos:** a hipótese "TF curto virando contra o longo avisa cedo" foi refutada e invertida — nos eventos alinhados ao D1 o zS já está virado antes do rompimento em 77% (M30), contra 61% nos eventos contra o D1 (no H1: 61% vs 32%, ambos sobrevivem ao BH). Dia contra a maré = rompimento que pega o painel de surpresa; espere latência, não antecipação.
- **De onde veio:** [E07_contexto](../research/2026-07-reatividade-metricas/results/E07_contexto.md).
- **Confiança:** média.

## 9. M30 é o TF doce de detecção — descer a M5 não compra tempo

- **O que sabemos:** pareado evento a evento, o zS do M5 dispara antes do M30 em só 48.7% dos casos (vantagem mediana: 0 min), pagando ~6× mais falsos (244 vs 41/semana por moeda). O M30 vence o H1 em 74.7% dos eventos com 30 min de vantagem. Para vigiar tendência diária: M30; M5/M15 só para timing de execução depois do alerta.
- **De onde veio:** [E07_cascata](../research/2026-07-reatividade-metricas/results/E07_cascata.md).
- **Confiança:** média (janela comum 2024-07+).

## 10. A força S tem meia-vida curta e homogênea — e o Score congelado é detector, não sistema

- **O que sabemos:** o desvio de S decai com half-life ~1.5h no M30 e ~0.75h no H1, praticamente igual nas 8 moedas — não existe moeda estruturalmente "lenta"; um S esticado há mais de ~2 half-lifes é história, não sinal. O Score 0–100 (pesos congelados em [E10_score_pesos.csv](../research/2026-07-reatividade-metricas/results/E10_score_pesos.csv)) generalizou no selado como DETECTOR (venceu a baseline pelo C10), mas a regra mínima de execução com custo deu PF 0.78 — é régua de atenção/pesquisa, não sistema de trading.
- **De onde veio:** [E08_sessoes](../research/2026-07-reatividade-metricas/results/E08_sessoes.md), [E10_score](../research/2026-07-reatividade-metricas/results/E10_score.md), [E11_selado](../research/2026-07-reatividade-metricas/results/E11_selado.md) + decisão P4 no [PROGRESS](../research/2026-07-reatividade-metricas/PROGRESS.md).
- **Confiança:** half-life média; Score-é-detector-não-sistema **alta** (veredito do selado, P4).

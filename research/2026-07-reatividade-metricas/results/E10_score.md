# E10 — Redundância, escada de modelos e o Score 0–100 (congelado)

## O que perguntamos

Quais métricas são cópias umas das outras (C8)? Uma ponderação CONTÍNUA
aprendida (logística → LightGBM, walk-forward) entrega o que as regras
binárias do Bloco C não entregaram? Quais pesos congelamos para o E11?

## Como testamos

Alvo de DETECÇÃO por linha do banco M30: "dentro de evento, no lado do zS,
antes de 50% consumido". Features assinadas pelo lado + relógio + alinhamento
dos TFs maiores. Walk-forward em 3 janelas (validação 2023 / 2024 / 2025);
Score vira detector pela mesma régua dos ramos (cruzamentos + quatro notas).
C8 por Spearman em 4 TFs; C9 por ganho incremental do contexto; ⚠ SHAP sem
wheel p/ Py3.14 → importâncias/estabilidade pela logística (sinal por janela).

## Resultados

### C8 — pares redundantes (|ρ| ≥ 0.9 em ≥ 4 TFs)

| par | TFs com |ρ|≥0.90 | C8 |
|---|---|---|
| zmov×zhist | 2 |  |
| zvel×vel | 4 | ✔ redundante |

**Leitura:** pares marcados são "a mesma notícia em dois jornais" — mantém-se
o de melhor nota composta; os demais pares seguem informativos entre si.

### Escada de modelos em walk-forward (quatro notas na validação de cada janela)

| validação | modelo | corte | deteccao_pct | lat_min | captura_pct | precisao_pct | falsos_sem |
|---|---|---|---|---|---|---|---|
| 2023 | logística | p90 | 48.6 | 150.0 | 79.7 | 2.5 | 10.24 |
| 2023 | logística | p97 | 21.6 | 30.0 | 85.8 | 2.6 | 3.87 |
| 2023 | logística | p99 | 9.5 | 30.0 | 93.6 | 3.1 | 1.58 |
| 2023 | LightGBM | p90 | 58.1 | 150.0 | 81.6 | 3.1 | 10.64 |
| 2023 | LightGBM | p97 | 33.8 | 180.0 | 74.0 | 4.7 | 3.77 |
| 2023 | LightGBM | p99 | 10.8 | 180.0 | 75.3 | 5.7 | 1.16 |
| 2024 | logística | p90 | 61.3 | 30.0 | 89.6 | 3.4 | 10.58 |
| 2024 | logística | p97 | 30.7 | 90.0 | 84.3 | 3.7 | 4.05 |
| 2024 | logística | p99 | 5.3 | 0.0 | 91.6 | 2.8 | 1.6 |
| 2024 | LightGBM | p90 | 64.0 | 60.0 | 87.2 | 3.7 | 10.6 |
| 2024 | LightGBM | p97 | 38.7 | 210.0 | 73.9 | 4.5 | 3.85 |
| 2024 | LightGBM | p99 | 13.3 | 255.0 | 64.1 | 4.5 | 1.44 |
| 2025 | logística | p90 | 55.9 | 90.0 | 85.8 | 1.8 | 10.23 |
| 2025 | logística | p97 | 29.4 | 30.0 | 86.9 | 2.7 | 3.84 |
| 2025 | logística | p99 | 17.6 | 15.0 | 85.6 | 3.5 | 1.46 |
| 2025 | LightGBM | p90 | 64.7 | 45.0 | 86.1 | 2.1 | 9.99 |
| 2025 | LightGBM | p97 | 38.2 | 60.0 | 81.8 | 2.8 | 4.01 |
| 2025 | LightGBM | p99 | 20.6 | 90.0 | 69.4 | 3.7 | 1.63 |

**Leitura:** a ponderação contínua muda o patamar: com corte alto, a precisão
sobe uma ordem de grandeza vs. as regras binárias do Bloco C — pagando em
detecção; o corte é o novo botão de sensibilidade, agora numa curva muito
melhor. LightGBM vs. logística mostra quanto a não-linearidade acrescenta.

### Estabilidade dos pesos entre janelas (logística, z-score)

| feature | coef médio (z) | sinal estável? |
|---|---|---|
| hora | -0.596 | ✔ |
| alin_H4 | 0.322 | ✔ |
| zs | 0.314 | ✔ |
| cesta | 0.253 | ✔ |
| alin_D1 | -0.235 | ✔ |
| mtf | 0.135 | ✔ |
| zvel | -0.094 | ✔ |
| zmov | 0.094 | ✔ |
| alin_MN1 | -0.092 | ✔ |
| zhist | 0.083 | ✔ |
| vel | -0.071 | ✔ |
| min_sessao | -0.056 | ✔ |
| alin_W1 | 0.056 | ✔ |
| acel | 0.0 | ✘ |

**Leitura:** coeficientes com sinal estável nas 3 janelas são estrutura, não
ruído de época — só eles merecem entrar no Score congelado com confiança.

### C9 — o contexto multi-TF paga o próprio custo?

| modelo | deteccao_pct | lat_mediana_min | captura_mediana_pct | precisao_pct | falsos_por_semana |
|---|---|---|---|---|---|
| com contexto | 29.4 | 30.0 | 86.9 | 2.7 | 3.84 |
| sem contexto | 32.4 | 0.0 | 91.4 | 2.7 | 3.56 |

**Leitura:** ganho de precisão do contexto: 0% (C9 exige ≥ 10% sem piorar
as demais em > 5%) → ✘ contexto não paga como feature do Score (coerente com o E7).

## Confronto com os critérios

C8: 1 par(es) redundante(s). C9: ganho do contexto 0% →
✘. C11: sem varredura além dos 3 cortes × 2 modelos
(nomeados antes); estabilidade walk-forward reportada acima. **Score 0–100
CONGELADO**: fórmula = 100·sigmoide(Σ coef·(x−média)/desvio + intercepto), pesos
fixos em `results/E10_score_pesos.csv` (calibrados em treino+validação
APENAS). No corte 0.7, o Score final marca: detecção 32.4%, latência
30.0 min, captura 86.5%, precisão 2.9%, 3.73 falsos/semana.

## O que isso muda

O E11 (portão P4) abre o selado UMA vez e confronta este Score congelado com a
baseline candidata (C10). Nada mais é ajustado a partir daqui.

## Limitações

- SHAP e PCA estrutural não rodados (wheels Py3.14) — estabilidade via sinais
  da logística; rodar na máquina Linux se quisermos o mapa SHAP completo.
- Score treinado no M30 (TF doce do E7); generalização a outros TFs fica como
  variante futura.
- O alvo usa o gabarito (ex-post) só como RÓTULO de treino — as features são
  todas de barra fechada (anti-look-ahead preservado).

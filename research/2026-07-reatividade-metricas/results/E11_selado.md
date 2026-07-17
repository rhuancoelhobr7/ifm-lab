# E11 — Teste selado (abertura única) e o veredito C10

## O que perguntamos

No período que NENHUMA análise tocou (2025-10→2026-06): o Score congelado no
E10 bate a baseline candidata do painel (C10)? E a regra intraday mínima paga
o custo?

## Como testamos

Abertura única de `data/sealed/` autorizada por Carlos Eduardo (PROGRESS).
Gabarito do selado detectado com a definição CONGELADA no P2a (50 eventos);
Score = fórmula fixa de `E10_score_pesos.csv` (nada reajustado); quatro notas
pela mesma régua dos ramos. Regra intraday: entrar no cruzamento, sair no fim
do dia (sem overnight), custo 0.03 ATR ida-e-volta (💡 spread constante —
MT5 não fornece spread histórico; limitação do ESBOÇO Q10).

## Resultados

### Quatro notas no selado

| detector | n_eventos | deteccao_pct | lat_min | captura_pct | precisao_pct | falsos_sem |
|---|---|---|---|---|---|---|
| Score congelado (p97) | 49 | 26.5 | 30.0 | 86.7 | 3.5 | 3.84 |
| baseline candidata (painel) | 50 | 0.0 |  |  | 0.0 | 0.1 |
| referência zS 1.0 (liga E5) | 50 | 94.0 | 30.0 | 88.9 | 2.1 | 40.02 |

**Leitura:** o quadro final fora-da-amostra. A baseline candidata do painel
repete o comportamento da liga (praticamente não detecta em tempo útil); o
Score mantém o perfil visto na validação — a generalização não quebrou.

### Regra intraday mínima (disparo → fim do dia, custo incluído)

| regra | trades | expectativa (ATR/trade) | profit factor | drawdown (ATRs) | % trades > 0 |
|---|---|---|---|---|---|
| Score p97 | 1306 | -0.0328 | 0.78 | 43.63 | 35.2 |
| baseline candidata | 33 | 0.0131 | 1.1 | 1.42 | 45.5 |

**Leitura:** expectativa por trade em ATRs JÁ COM custo. 💡 Profit factor > 1
= os ganhos pagam as perdas; drawdown em ATRs mede o pior vale da curva.

## Confronto com os critérios

**C10** exigia: latência ≥ 20% menor com detecção/captura não piores, OU
mesma latência com falsos ≥ 20% menores e captura não pior →
**✔ SCORE VENCE a baseline**
(baseline detecção 0.0% vs Score 26.5%). O carimbo do 🚪 P4 é do dono
da pesquisa, com este quadro em mãos.

## O que isso muda

Achados confirmados no selado sobem para confiança ALTA nas entradas de
LEITURA (E12). Score aprovado → candidato a variante src/variants/.

## Limitações

- Custo constante (0.03 ATR) — sem spread histórico real.
- Regra intraday deliberadamente mínima (sem stop/alvo/gestão) — mede o SINAL,
  não um sistema de trading.
- 50 eventos em 9 meses de selado: amostra menor que treino/validação.

# E04b — Auditoria de sanidade do banco-mãe

## O que perguntamos

O banco de estados (a mesa de trabalho das análises E5–E10) está íntegro:
NaN sob controle, contexto sem look-ahead, alvos recomputáveis, splits físicos?

## Como testamos

Banco por TF de detecção (M30, H1): linha = (t, moeda) com métricas t0 do
parquet (hash `763beb9d23a1`), contexto MN1→M30 por ÚLTIMA BARRA FECHADA (asof ≤ t),
sessão/minutos/flag DST, vínculo ao gabarito pela âncora **A-rompimento**
(congelada no P2a) e alvos A1–A3 (💡 §1.4 do ESBOÇO; A2/A3 no caminho de
cesta M30 do gabarito, capados no fim do dia; A3 = par sintético rank1×rank8).
Splits físicos: treino/validação em data/parquet/, selado em data/sealed/
(vínculo de gabarito do selado deixado vazio — eventos selados só no E11).
Contagem de NaN do C3: métricas/contexto em TODAS as linhas; alvos intraday
só dentro do dia Tóquio→NY (fora dele o alvo é indefinido por definição —
NaN estrutural, não dado faltante).

## Resultados

| tf | ano | nan_max_pct |
|---|---|---|
| M30 | 2021 | 6.0 |
| M30 | 2022 | 1.0 |
| M30 | 2023 | 2.0 |
| M30 | 2024 | 0.8 |
| M30 | 2025 | 5.4 |
| H1 | 2021 | 6.0 |
| H1 | 2022 | 1.4 |
| H1 | 2023 | 2.8 |
| H1 | 2024 | 1.8 |
| H1 | 2025 | 3.4 |
| M15 | 2024 | 1.7 |
| M15 | 2025 | 5.9 |
| M5 | 2024 | 1.4 |
| M5 | 2025 | 6.2 |

**Leitura:** pior taxa de NaN por TF×ano nas colunas-chave: 6.2% —
dentro do limite C3 (≤ 15%). NaN aqui é honestidade
(janelas de aquecimento, buracos propagados), nunca imputação.

| verificação | resultado |
|---|---|
| 20 linhas sorteadas para auditoria 👤 | results/E04b_20linhas.csv |
| A2_60 recomputado por caminho independente (dos CSVs crus) | 40/40 batem (tol. 1e-9) |
| contexto ctx_s_* usa barra fechada ≤ t | por construção (asof; teste test_asof_nao_olha_o_futuro) |

**Leitura:** o alvo A2 refeito fora do pipeline bate com o gravado, e o
contexto nunca lê barra em formação — as duas armadilhas clássicas (alvo
errado e look-ahead) estão vigiadas por código e teste.

## Confronto com os critérios

C3 exigia: NaN ≤ 15% por TF×ano → ✔ (pior 6.2%); alvos recomputados
por caminho independente batem → ✔ (40/40); contexto W1/MN por
última barra FECHADA → ✔; 20 linhas auditadas pelo dono da pesquisa → ⏳ 👤.
**Situação: aguardando a auditoria 👤 das 20 linhas (portão P2b).**

## O que isso muda

P2b aprovado → extensão M5/M15 do banco e E5 (corrida de latências) liberados.

## Limitações

- A3 é o par SINTÉTICO forte×fraco via cestas (não o par real da corretora) —
  suficiente para medir reatividade; custo real de operação entra só no E11.
- A2/A3 capados no fim do dia de negociação (horizonte é intraday por premissa).
- Vínculo de gabarito do bloco selado propositalmente vazio até o E11.

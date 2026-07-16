# E06 (parte 1) — Curvas de limiar e a busca do ponto de operação

## O que perguntamos

Subindo o limiar de cada métrica, a precisão chega a um nível operável
(≥ 40%, o piso do C4) antes de a detecção morrer? Onde os limiares ATUAIS
do painel estão nessa curva?

## Como testamos

Grade fina de limiares por métrica × TF (M30/H1, foco do P3); as quatro notas
recalculadas em cada célula (motor do E5). C11: teste binomial por célula
(H0: precisão ≤ 40%) com correção Benjamini-Hochberg a FDR 10% sobre as
130 células da varredura; célula só "vale" se sobrevive ao BH E o treino
confirma o padrão. Curvas completas em `E06_curvas.csv`.

## Resultados

### Célula de MAIOR precisão por métrica × TF (validação)

| tf | metrica | limiar | deteccao_pct | lat_mediana_min | captura_mediana_pct | precisao_pct | falsos_por_semana | p_bh | sobrevive_bh |
|---|---|---|---|---|---|---|---|---|---|
| M30 | zvel | 2.25 | 2.6 | 120.0 | 64.7 | 50.0 | 0.0 | 1.0 | False |
| H1 | zs | 2.5 | 0.0 |  |  | 20.0 | 0.01 | 1.0 | False |
| H1 | zmov | 2.5 | 5.1 | 180.0 | 63.4 | 9.7 | 0.09 | 1.0 | False |
| M30 | zmov | 2.5 | 5.1 | 165.0 | 60.3 | 7.8 | 0.15 | 1.0 | False |
| M30 | zs | 2.25 | 15.4 | 180.0 | 60.6 | 5.7 | 0.82 | 1.0 | False |
| H1 | zvel | 1.75 | 5.1 | 255.0 | 65.4 | 4.7 | 0.19 | 1.0 | False |
| H1 | vel | 40.13 | 12.8 | 150.0 | 71.6 | 3.1 | 0.88 | 1.0 | False |
| M30 | cesta | 7.0 | 74.4 | 30.0 | 90.6 | 2.0 | 28.69 | 1.0 | False |
| H1 | cesta | 7.0 | 71.8 | 135.0 | 79.1 | 1.9 | 14.55 | 1.0 | False |
| M30 | vel | 40.64 | 7.7 | 90.0 | 75.9 | 1.7 | 1.68 | 1.0 | False |
| H1 | acel | 66.06 | 10.3 | 150.0 | 65.2 | 1.3 | 0.93 | 1.0 | False |
| H1 | zhist | 1.75 | 12.8 | 210.0 | 67.0 | 1.2 | 3.73 | 1.0 | False |
| M30 | zhist | 1.75 | 12.8 | 210.0 | 67.0 | 1.2 | 5.22 | 1.0 | False |
| M30 | acel | 51.14 | 25.6 | 135.0 | 66.5 | 1.1 | 8.62 | 1.0 | False |
| H1 | mtf | 4.0 | 23.1 | 30.0 | 89.1 | 0.7 | 8.92 | 1.0 | False |
| M30 | mtf | 3.0 | 69.2 | 30.0 | 87.4 | 0.7 | 26.07 | 1.0 | False |

**Leitura:** mesmo no melhor limiar de cada métrica, a precisão máxima
observada foi 50.0% — perto do piso de 40% do C4.
Nenhuma célula da varredura sobrevive ao BH com detecção suficiente: no formato "cruzamento de limiar de uma métrica sozinha", o painel NÃO tem ponto de operação com precisão viável — achado forte, previsto no PLANO §7.

### Limiares ATUAIS do painel (zvel 2.0, zS 1.0, cesta 5, mtf 2)

| tf | metrica | limiar | deteccao_pct | lat_mediana_min | captura_mediana_pct | precisao_pct | falsos_por_semana | p_bh | sobrevive_bh |
|---|---|---|---|---|---|---|---|---|---|
| M30 | zvel | 2.0 | 2.6 | 120.0 | 64.7 | 3.6 | 0.08 | 1.0 | False |
| M30 | zs | 1.0 | 82.1 | 15.0 | 91.8 | 1.5 | 41.26 | 1.0 | False |
| M30 | cesta | 5.0 | 76.9 | 0.0 | 94.0 | 0.7 | 61.34 | 1.0 | False |
| M30 | mtf | 2.0 | 66.7 | 30.0 | 91.6 | 0.5 | 33.85 | 1.0 | False |
| H1 | zvel | 2.0 | 0.0 |  |  | 0.0 | 0.04 | 1.0 | False |
| H1 | zs | 1.0 | 76.9 | 75.0 | 84.8 | 1.4 | 20.75 | 1.0 | False |
| H1 | cesta | 5.0 | 74.4 | 30.0 | 91.4 | 0.7 | 31.33 | 1.0 | False |
| H1 | mtf | 2.0 | 64.1 | 30.0 | 91.4 | 0.5 | 31.33 | 1.0 | False |

**Leitura:** os limiares congelados na v1.0 vivem na mesma região de precisão
~1–3% das demais células — o problema não é a calibração do limiar, é o
FORMATO (métrica solo × cruzamento): disparos sobram fora dos eventos em
qualquer altura de régua.

### Recorte por sessão (limiares atuais de zvel/zS)

| tf | metrica | limiar | sessao | n_disparos | uteis | lat_mediana_min |
|---|---|---|---|---|---|---|
| M30 | zvel | 2.0 | toquio | 1 | 1 | 120.0 |
| M30 | zs | 1.0 | londres | 11 | 9 | 30.0 |
| M30 | zs | 1.0 | ny | 1 | 1 | 30.0 |
| M30 | zs | 1.0 | toquio | 23 | 22 | 0.0 |
| H1 | zs | 1.0 | londres | 11 | 10 | 135.0 |
| H1 | zs | 1.0 | ny | 1 | 1 | 90.0 |
| H1 | zs | 1.0 | toquio | 23 | 19 | 30.0 |

**Leitura:** onde os disparos úteis se concentram por sessão de nascimento do
evento — insumo direto para o E8 (ciclos de sessão) e para condicionar o
detector ao relógio.

## Confronto com os critérios

C11 (FDR 10%, 130 testes) aplicado → ✘ nenhuma célula(s) com precisão
comprovadamente > 40% E detecção ≥ 60% E treino confirmando. C4 segue
não atendido no formato métrica-solo (coerente com o E5); C6 (exaustão) e o
veredito do VETO ficam para a parte 2 do E6.

## O que isso muda

O caminho para um detector operável não é "ajustar o limiar" — é mudar o
formato: condicionar ao relógio/sessão (E8), exigir confluência (E9/Q4) ou
usar o contexto multi-TF (E7). A ordem do P3 (E6→E8→E7→E9) segue fazendo
sentido; recomenda-se ao E9 usar estas curvas como base das combinações.

## Limitações

- Precisão medida por CRUZAMENTOS na grade 24h do dia de negociação; formatos
  com confirmação (N barras seguidas) ou por sessão podem mudar o quadro — E6
  parte 2 / E9.
- vel/acel com limiares por quantil do treino (p50–p99) — grade grossa.
- Pós-disparo, sobrevivência intraday, exaustão (C6) e VETO: parte 2 do E6.

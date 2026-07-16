# E09 — Quadrantes e combinações dirigidas (Q4, camadas 1–2)

## O que perguntamos

A confluência (métricas concordando no mesmo lado, ou métrica + relógio)
compra a precisão que nenhuma métrica solo alcançou (E6.1), sem devolver a
detecção? Onde o quadrante "nível + evidência" fica na curva?

## Como testamos

Banco M30/H1 (treino+validação; selado intocado). Disparo = cruzamento do
estado COMPOSTO (todas as pernas ligadas no mesmo lado — regras no cabeçalho
do script; combinações NOMEADAS antes de olhar resultado, C11 com BH FDR
10% sobre 22 células + confirmação no treino). Referência solo:
zS ≥ 1.0 (campeã da liga E5).

## Resultados

### Todas as células (validação; ordenadas por precisão)

| tf | combo | n_eventos | deteccao_pct | lat_mediana_min | captura_mediana_pct | precisao_pct | falsos_por_semana | p_bh | sobrevive_bh | C4 |
|---|---|---|---|---|---|---|---|---|---|---|
| H1 | Q_nivel_e_evidencia | 39 | 46.2 | 135.0 | 73.9 | 3.2 | 4.67 | 1.0 | False |  |
| H1 | nivel_com_evidencia | 39 | 46.2 | 135.0 | 73.9 | 3.2 | 4.67 | 1.0 | False |  |
| H1 | trio_completo | 39 | 46.2 | 135.0 | 73.9 | 3.2 | 4.67 | 1.0 | False |  |
| H1 | Q_so_nivel | 39 | 71.8 | 90.0 | 80.8 | 1.7 | 19.98 | 1.0 | False |  |
| H1 | nivel_com_adesao | 39 | 76.9 | 75.0 | 84.8 | 1.4 | 19.68 | 1.0 | False |  |
| H1 | solo_zs_1.0 (referência) | 39 | 76.9 | 75.0 | 84.8 | 1.4 | 20.75 | 1.0 | False |  |
| H1 | nivel_adesao_cedo | 39 | 51.3 | 75.0 | 88.2 | 1.3 | 11.05 | 1.0 | False |  |
| H1 | nivel_cedo | 39 | 51.3 | 45.0 | 88.2 | 1.2 | 11.81 | 1.0 | False |  |
| H1 | Q_so_evidencia | 39 | 5.1 | 75.0 | 87.6 | 0.2 | 3.09 | 1.0 | False |  |
| H1 | arrancada_com_adesao | 39 | 0.0 |  |  | 0.0 | 0.04 | 1.0 | False |  |
| H1 | evidencia_dia_atipico | 39 | 0.0 |  |  | 0.0 | 0.15 | 1.0 | False |  |
| M30 | arrancada_com_adesao | 39 | 2.6 | 120.0 | 64.7 | 3.6 | 0.08 | 1.0 | False |  |
| M30 | Q_so_nivel | 39 | 82.1 | 30.0 | 91.4 | 1.7 | 39.14 | 1.0 | False |  |
| M30 | Q_nivel_e_evidencia | 39 | 53.8 | 90.0 | 79.3 | 1.6 | 9.45 | 1.0 | False |  |
| M30 | nivel_com_evidencia | 39 | 53.8 | 90.0 | 79.3 | 1.6 | 9.45 | 1.0 | False |  |
| M30 | trio_completo | 39 | 53.8 | 90.0 | 79.3 | 1.6 | 9.43 | 1.0 | False |  |
| M30 | nivel_com_adesao | 39 | 79.5 | 30.0 | 91.4 | 1.5 | 38.9 | 1.0 | False |  |
| M30 | solo_zs_1.0 (referência) | 39 | 82.1 | 15.0 | 91.8 | 1.5 | 41.26 | 1.0 | False |  |
| M30 | evidencia_dia_atipico | 39 | 0.0 |  |  | 1.1 | 0.28 | 1.0 | False |  |
| M30 | nivel_cedo | 39 | 69.2 | 0.0 | 93.3 | 1.1 | 21.86 | 1.0 | False |  |
| M30 | nivel_adesao_cedo | 39 | 66.7 | 15.0 | 92.4 | 1.1 | 20.22 | 1.0 | False |  |
| M30 | Q_so_evidencia | 39 | 7.7 | 90.0 | 82.9 | 0.2 | 5.78 | 1.0 | False |  |

**Leitura:** o padrão do E6 se repete nas combinações: cada perna extra corta
falsos (falsos/semana despenca) mas cobra detecção. As células dirigidas pelo
relógio ("_cedo") mantêm mais detecção por unidade de precisão — o filtro de
HORA é mais barato que o filtro de MÉTRICA. Nenhuma célula fecha o C4 completo.

### Confronto: melhores combinações × solo

| tf | combo | n_eventos | deteccao_pct | lat_mediana_min | captura_mediana_pct | precisao_pct | falsos_por_semana | p_bh | sobrevive_bh | C4 |
|---|---|---|---|---|---|---|---|---|---|---|
| M30 | arrancada_com_adesao | 39 | 2.6 | 120.0 | 64.7 | 3.6 | 0.08 | 1.0 | False |  |
| H1 | nivel_com_evidencia | 39 | 46.2 | 135.0 | 73.9 | 3.2 | 4.67 | 1.0 | False |  |
| H1 | trio_completo | 39 | 46.2 | 135.0 | 73.9 | 3.2 | 4.67 | 1.0 | False |  |
| M30 | solo_zs_1.0 (referência) | 39 | 82.1 | 15.0 | 91.8 | 1.5 | 41.26 | 1.0 | False |  |
| H1 | solo_zs_1.0 (referência) | 39 | 76.9 | 75.0 | 84.8 | 1.4 | 20.75 | 1.0 | False |  |

**Leitura:** a melhor combinação multiplica a precisão da solo por
2.4× — mas segue
abaixo do piso de 40% do C4. A latência e a captura das combinações
continuam boas (a confluência não chega "tarde demais").

## Confronto com os critérios

C11 (BH FDR 10%): aplicado a todas as células. C4 completo:
✘ nenhuma combinação testada atinge precisão ≥ 40% com detecção ≥ 60%.
Estabilidade walk-forward (exigência extra do C11 para combinações) fica para
o E10, onde o Score contínuo substitui as regras binárias.

## O que isso muda

O Bloco C fecha com um mapa consistente: detecção cedo é fácil, precisão é
estrutural. As melhores pernas identificadas (nível+adesão+relógio) e os pesos
implícitos vão para o **E10** — a escada de modelos e o Score 0–100, onde a
combinação deixa de ser binária (E/OU) e vira ponderação contínua, que é onde
a literatura e o E6 sugerem que a precisão pode finalmente escalar.

## Limitações

- Combinações binárias (E lógico); ponderação contínua é o E10.
- Recorte por sessão embutido só via "hora < 12h"; grade completa sessão×combo
  explodiria as células (C11) — dirigimos pelo achado do E8 em vez de varrer.
- Camada 3 do Q4 (busca automática de combinações) não executada — exigiria
  walk-forward + BH, e o E10 a substitui com modelos regularizados.

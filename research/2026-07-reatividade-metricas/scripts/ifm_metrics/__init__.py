"""ifm_metrics — reimplementação Python do painel G8 do IFM v1.0 (etapa E2).

💡 O que este pacote é, em linguagem simples: a "cópia de laboratório" da metade
painel do indicador. Cada módulo reimplementa um pedaço da cadeia que o IFM.mq5
calcula na tela — IFM Light por par, força S por moeda, e as métricas derivadas
(vel, zvel, acel, zS, zMov, zHist, cesta, mtf, VETO, candidata, rank H1) — de
forma vetorizada (rápida para 28 pares × anos de barras) e SEM olhar o futuro.
A fidelidade ao fonte é verificada de dois jeitos: fixtures sintéticas com
valores calculados à mão (tests/) e uma porta de referência em loop, tradução
literal do MQL5 (reference.py), contra a qual a versão vetorizada é comparada.
A paridade contra o indicador REAL é a etapa E3 (critério C1).

Todos os parâmetros vêm do config.yaml da pesquisa — nada é hard-coded.
"""

from . import light, strength, derived, cross_tf, daymove, reference  # noqa: F401

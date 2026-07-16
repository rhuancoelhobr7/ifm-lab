"""Testes do gabarito (E4) — âncoras e eficiência com caminhos montados à mão."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ifm_metrics import gabarito


def _linha(vals):
    return np.array([vals], dtype=float)


def test_ancora_20_10_ponto_sem_retorno():
    # fracs: 0.05, 0.25, 0.08, 0.30, 0.50, 1.00 (mag=10 → path = frac×10)
    path = _linha([0.5, 2.5, 0.8, 3.0, 5.0, 10.0])
    anc = gabarito.ancora_20_10(path, np.array([10.0]), 0.20, 0.10)
    # slot 1 atinge 20% mas recua a 8% depois → invalida; slot 3 nunca recua
    assert anc[0] == 3


def test_ancora_20_10_sem_ancora():
    path = _linha([0.5, 1.5, 0.5, 1.8])          # nunca atinge 20% de mag=10
    anc = gabarito.ancora_20_10(path, np.array([10.0]), 0.20, 0.10)
    assert anc[0] == -1


def test_ancora_rompimento_ultimo_cruzamento():
    # fracs: -0.02, 0.05, -0.01, 0.20, 0.60, 1.00 → último ≤0 no slot 2
    path = _linha([-0.2, 0.5, -0.1, 2.0, 6.0, 10.0])
    anc = gabarito.ancora_rompimento(path, np.array([10.0]))
    assert anc[0] == 3                            # primeiro slot após o toque


def test_ancora_rompimento_nunca_volta():
    path = _linha([0.5, 2.0, 4.0, 10.0])          # sempre do lado certo
    anc = gabarito.ancora_rompimento(path, np.array([10.0]))
    assert anc[0] == 0                            # primeiro slot válido do dia


def test_ancora_rompimento_evento_de_baixa():
    # mag negativa: frac = path/mag fica positiva quando o caminho desce junto
    path = _linha([0.3, -0.5, 0.1, -2.0, -6.0, -10.0])
    anc = gabarito.ancora_rompimento(path, np.array([-10.0]))
    assert anc[0] == 3                            # último lado errado: slot 2


def test_eficiencia_kaufman_a_mao():
    # caminho 0→1→0.5→2 (com o zero implícito da abertura):
    # líquido |2| ; passos |1|+|0.5|+|1.5| = 3 → ER = 2/3
    path = _linha([1.0, 0.5, 2.0])
    er = gabarito.eficiencia_kaufman(path)
    assert er[0] == pytest.approx(2.0 / 3.0)


def test_eficiencia_reta_perfeita():
    path = _linha([1.0, 2.0, 3.0, 4.0])
    assert gabarito.eficiencia_kaufman(path)[0] == pytest.approx(1.0)


def test_janelas_dia_verao_e_inverno():
    ses = {"toquio": {"tz": "Asia/Tokyo", "abre": "09:00", "fecha": "18:00"},
           "londres": {"tz": "Europe/London", "abre": "08:00", "fecha": "17:00"},
           "ny": {"tz": "America/New_York", "abre": "08:00", "fecha": "17:00"}}
    datas = pd.DatetimeIndex(["2025-07-15", "2025-01-15"])   # verão / inverno
    j = gabarito.janelas_dia(datas, ses, 1800)
    # verão: Tóquio 09h JST = 03h servidor (UTC+3) → slot 6; NY fecha 17h EDT
    # = 24h servidor → slot 48. inverno: Tóquio 02h → slot 4.
    assert j.loc[pd.Timestamp("2025-07-15"), "dia_ini"] == 6
    assert j.loc[pd.Timestamp("2025-07-15"), "dia_fim"] == 48
    assert j.loc[pd.Timestamp("2025-01-15"), "dia_ini"] == 4
    assert j.loc[pd.Timestamp("2025-01-15"), "dia_fim"] == 48
    # Londres 10h servidor nas duas estações (DST europeu acompanha)
    assert j.loc[pd.Timestamp("2025-07-15"), "londres_ini"] == 20
    assert j.loc[pd.Timestamp("2025-01-15"), "londres_ini"] == 20

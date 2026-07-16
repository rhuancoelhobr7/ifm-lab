"""Testes de força S, cesta e derivadas — universo mínimo calculado à mão."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ifm_metrics import derived, reference, strength

MOEDAS = ["AAA", "BBB", "CCC"]
PARES = ["AAABBB", "AAACCC", "BBBCCC"]
IDX = pd.date_range("2024-01-01", periods=1, freq="1h")


def frame_ifm(vals: dict[str, float]) -> pd.DataFrame:
    return pd.DataFrame({p: [v] for p, v in vals.items()}, index=IDX)


def test_forca_s_a_mao():
    # AAABBB=75 → dir +0.5 · AAACCC=60 → +0.2 · BBBCCC=50 → 0
    s = strength.forca_s(frame_ifm({"AAABBB": 75.0, "AAACCC": 60.0, "BBBCCC": 50.0}),
                         PARES, MOEDAS)
    assert s["AAA"].iloc[0] == pytest.approx(50 + (0.5 + 0.2) / 2 * 50)   # 67.5
    assert s["BBB"].iloc[0] == pytest.approx(50 + (-0.5 + 0.0) / 2 * 50)  # 37.5
    assert s["CCC"].iloc[0] == pytest.approx(50 + (-0.2 - 0.0) / 2 * 50)  # 45.0


def test_forca_s_nan_em_um_par_macula_as_duas_moedas():
    s = strength.forca_s(frame_ifm({"AAABBB": np.nan, "AAACCC": 60.0, "BBBCCC": 50.0}),
                         PARES, MOEDAS)
    assert np.isnan(s["AAA"].iloc[0]) and np.isnan(s["BBB"].iloc[0])
    assert s["CCC"].iloc[0] == pytest.approx(45.0)


def test_cesta_a_mao():
    ifm = frame_ifm({"AAABBB": 75.0, "AAACCC": 60.0, "BBBCCC": 50.0})
    s = strength.forca_s(ifm, PARES, MOEDAS)
    c = strength.cesta(ifm, s, PARES, MOEDAS)
    assert c["AAA"].iloc[0] == pytest.approx(1.0)     # 2/2 confirmam
    assert c["BBB"].iloc[0] == pytest.approx(0.5)     # AAABBB sim, BBBCCC neutro
    assert c["CCC"].iloc[0] == pytest.approx(0.5)     # AAACCC sim, BBBCCC neutro


def test_cesta_lado_indefinido_e_nan():
    # S da moeda em exatamente 50 → cesta NaN (lado indefinido)
    ifm = frame_ifm({"AAABBB": 60.0, "AAACCC": 40.0, "BBBCCC": 50.0})
    s = strength.forca_s(ifm, PARES, MOEDAS)
    assert s["AAA"].iloc[0] == pytest.approx(50.0)
    c = strength.cesta(ifm, s, PARES, MOEDAS)
    assert np.isnan(c["AAA"].iloc[0])


# ---------- derivadas: à mão + vetorizado × referência ----------

def serie(vals) -> pd.Series:
    return pd.Series(vals, index=pd.date_range("2024-01-01", periods=len(vals), freq="1h"),
                     dtype=float)


def test_vel_acel_a_mao():
    s = serie([50, 51, 49, 40, 44, 46])
    assert derived.vel(s, 2).iloc[-1] == pytest.approx(6.0)         # 46-40
    # acel k=2: (46-40) - (40-51) = 6 + 11 = 17
    assert derived.acel(s, 2).iloc[-1] == pytest.approx(17.0)


def test_zvel_a_mao():
    # diffs dos últimos 4 passos: [1, -2, 3, 2] → média 1, σ_pop=√3.5
    s = serie([50, 50, 51, 49, 52, 54])
    v = derived.vel(s, 2).iloc[-1]                                   # 54-49=5
    z = derived.zvel(s, 2, 4).iloc[-1]
    assert v == pytest.approx(5.0)
    assert z == pytest.approx(5.0 / (np.sqrt(3.5) * np.sqrt(2.0)))   # 5/√7


def test_derivadas_regra_de_fatia_nan():
    s = serie([50, np.nan, 51, 52, 53])
    assert np.isnan(derived.vel(s, 3).iloc[-1])       # NaN dentro da fatia
    assert derived.vel(s, 2).iloc[-1] == pytest.approx(2.0)   # fatia limpa


@pytest.mark.parametrize("seed", [2, 9])
def test_derivadas_vetorizadas_igual_referencia(seed):
    rng = np.random.default_rng(seed)
    vals = 50 + np.cumsum(rng.normal(0, 1.5, 400))
    vals[rng.integers(0, 400, 12)] = np.nan           # NaNs espalhados
    s = serie(vals)
    k, n, ring = 6, 32, 64
    v_vec, a_vec, z_vec = derived.vel(s, k), derived.acel(s, k), derived.zvel(s, k, n)
    for fim in range(ring - 1, 400, 7):
        janela = s.iloc[fim - ring + 1: fim + 1].tolist()
        for vec, ref_fn in ((v_vec, reference.met_vel),
                            (a_vec, reference.met_acel)):
            ref = ref_fn(janela, k)
            got = vec.iloc[fim]
            assert (np.isnan(ref) and np.isnan(got)) or got == pytest.approx(ref, abs=1e-10)
        ref = reference.met_zvel(janela, k, n)
        got = z_vec.iloc[fim]
        assert (np.isnan(ref) and np.isnan(got)) or got == pytest.approx(ref, abs=1e-10)


def test_zs_transversal_a_mao():
    f = pd.DataFrame([[60.0, 40.0, 50.0, 50.0]], columns=list("ABCD"), index=IDX)
    z = derived.zs_transversal(f)
    assert z["A"].iloc[0] == pytest.approx(10.0 / np.sqrt(50.0))     # √2
    assert z["B"].iloc[0] == pytest.approx(-np.sqrt(2.0))
    # menos de 4 moedas válidas → tudo NaN
    f2 = pd.DataFrame([[60.0, 40.0, 50.0, np.nan]], columns=list("ABCD"), index=IDX)
    assert derived.zs_transversal(f2).iloc[0].isna().all()


def test_rank_h1_a_mao():
    cur = ["USD", "EUR", "GBP", "JPY"]
    s = pd.DataFrame([[70.0, 70.0, 60.0, np.nan]], columns=cur, index=IDX)
    c = pd.DataFrame([[0.5, 0.7, np.nan, np.nan]], columns=cur, index=IDX)
    r = derived.rank_h1(s, c, cur)
    assert r.iloc[0].tolist() == [2, 1, 3, 4]         # EUR ganha no desempate
    # empate total → alfabético: EUR antes de USD
    c2 = pd.DataFrame([[0.5, 0.5, np.nan, np.nan]], columns=cur, index=IDX)
    r2 = derived.rank_h1(s, c2, cur)
    assert r2.iloc[0].tolist() == [2, 1, 3, 4]

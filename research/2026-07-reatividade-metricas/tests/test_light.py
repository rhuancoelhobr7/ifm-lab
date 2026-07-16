"""Testes do IFM Light — fixtures à mão + vetorizado × porta de referência."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from conftest import barras_aleatorias
from ifm_metrics import light, reference


# ---------- fixtures calculadas à mão ----------

def test_pivot_score_todos_os_votos():
    # barra anterior: H=12, L=10, C=11 → PP=11, R1=12, S1=10
    h = pd.Series([12.0, 13.0, 12.0, 11.0, 10.0, 11.5])
    l = pd.Series([10.0, 12.0, 11.0, 10.0, 9.0, 10.5])
    fechamentos = {12.5: 2.0, 11.5: 1.0, 10.5: -1.0, 9.5: -2.0, 11.0: 0.0}
    for c_val, esperado in fechamentos.items():
        c = pd.Series([11.0, c_val])
        hh = pd.Series([12.0, c_val + 0.5])
        ll = pd.Series([10.0, c_val - 0.5])
        sc = light.pivot_score(hh, ll, c)
        assert sc.iloc[1] == esperado, f"close {c_val}: {sc.iloc[1]} != {esperado}"
    assert np.isnan(light.pivot_score(h, l, pd.Series([np.nan] * 6)).iloc[1])


def test_tp_zscore_a_mao():
    # TP cronológico [30, 20, 10] (constrói h=l=c): média 20, σ_pop=√(200/3)
    h = l = c = pd.Series([30.0, 20.0, 10.0])
    z = light.tp_zscore(h, l, c, 3)
    esperado = (10.0 - 20.0) / np.sqrt(200.0 / 3.0)   # = -1.224744871…
    assert z.iloc[2] == pytest.approx(esperado, abs=1e-12)
    assert z.iloc[:2].isna().all()                    # janela incompleta


def test_tp_zscore_sigma_zero_vira_zero():
    h = l = c = pd.Series([5.0] * 10)
    assert (light.tp_zscore(h, l, c, 3).iloc[2:] == 0.0).all()


def test_ifm_light_precos_constantes_da_neutro(cfg):
    # preços e volume constantes: pivot 0, MP mudo, MFC 0 (vol == média,
    # não maior), juiz Z 0 (σ=0) → bruto 0 → IFM = 50
    n = 80
    df = pd.DataFrame({"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0,
                       "tick_volume": 100.0},
                      index=pd.date_range("2024-01-01", periods=n, freq="1h"))
    ifm = light.ifm_light(df, cfg)
    assert ifm.iloc[:59].isna().all()                 # sem 60 barras completas
    assert (ifm.iloc[59:] == 50.0).all()


def test_mfc_score_a_mao():
    # vol[3]=200 > média(100,100,200)=133.3; mfc sobe ((h-l)/vol: 0.5→? )
    h = pd.Series([2.0, 2.0, 2.0, 4.0])
    l = pd.Series([1.0, 1.0, 1.0, 1.0])
    vol = pd.Series([100.0, 100.0, 100.0, 200.0])
    # mfc: 0.01, 0.01, 0.01, 0.015 → subiu; volume acima da média → +1
    sc = light.mfc_score(h, l, vol, 3)
    assert sc.iloc[3] == 1.0
    # volume alto mas MFC caiu → -1 (squat)
    h2 = pd.Series([2.0, 2.0, 2.0, 2.0])
    sc2 = light.mfc_score(h2, l, vol, 3)              # mfc: 0.01,0.01,0.01,0.005
    assert sc2.iloc[3] == -1.0


def test_mp_score_mudo_com_janela_60():
    c = pd.Series(np.linspace(1.0, 2.0, 100))
    sc = light.mp_score(c, 21, 60)                    # 60 < 65 → juiz mudo
    assert (sc == 0.0).all()


# ---------- vetorizado × porta de referência (tradução literal do MQL5) ----------

def _as_series(df: pd.DataFrame, fim: int, n: int):
    """Fatia [fim-n+1 … fim] em ordem as-series (0 = mais novo), como o MQL5."""
    bloco = df.iloc[fim - n + 1: fim + 1][::-1]
    zeros = [0.0] * n
    return (bloco["high"].tolist(), bloco["low"].tolist(),
            bloco["close"].tolist(), bloco["tick_volume"].tolist(), zeros)


@pytest.mark.parametrize("seed", [1, 7, 42])
def test_ifm_light_vetorizado_igual_referencia(cfg, seed):
    df = barras_aleatorias(300, seed)
    ifm_vec = light.ifm_light(df, cfg)
    win = cfg["indicator"]["light_window"]
    for fim in range(win - 1, 300, 13):
        h, l, c, tick, real = _as_series(df, fim, win)
        ref = reference.calc_ifm_light_at(h, l, c, tick, real, 0, win, cfg)
        # 1e-8: folga p/ associação de ponto flutuante (rolling × two-pass);
        # ainda 10^7 vezes mais apertado que o critério C1 (|ΔS| ≤ 0.1)
        assert ifm_vec.iloc[fim] == pytest.approx(ref, abs=1e-8), f"barra {fim}"


def test_ifm_light_nucleo_classico_igual_referencia(cfg):
    cfg["indicator"]["zcore"] = False
    df = barras_aleatorias(200, 3)
    ifm_vec = light.ifm_light(df, cfg)
    win = cfg["indicator"]["light_window"]
    for fim in range(win - 1, 200, 17):
        h, l, c, tick, real = _as_series(df, fim, win)
        ref = reference.calc_ifm_light_at(h, l, c, tick, real, 0, win, cfg)
        assert ifm_vec.iloc[fim] == pytest.approx(ref, abs=1e-10)


def test_juiz_mp_ativo_igual_referencia(cfg):
    """Janela ampliada para 70 (> 65) liga o juiz MP — cobre o código
    hoje morto, contra a mesma tradução literal do fonte."""
    cfg["indicator"]["light_window"] = 70
    df = barras_aleatorias(250, 11)
    ifm_vec = light.ifm_light(df, cfg)
    for fim in range(69, 250, 19):
        h, l, c, tick, real = _as_series(df, fim, 70)
        ref = reference.calc_ifm_light_at(h, l, c, tick, real, 0, 70, cfg)
        assert ifm_vec.iloc[fim] == pytest.approx(ref, abs=1e-10)


def test_nan_no_meio_da_janela_propaga(cfg):
    df = barras_aleatorias(200, 5)
    df.iloc[100] = np.nan
    ifm = light.ifm_light(df, cfg)
    assert ifm.iloc[100:160].isna().all()             # 60 barras contaminadas
    assert ifm.iloc[160:].notna().all()

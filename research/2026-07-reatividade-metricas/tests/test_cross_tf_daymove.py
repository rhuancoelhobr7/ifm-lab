"""Testes de mtf/VETO/candidata e de zMov/zHist — cenários montados à mão."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ifm_metrics import cross_tf, daymove

CUR = ["AAA", "BBB", "CCC", "DDD"]


def _frame(idx, valores_por_moeda):
    return pd.DataFrame(valores_por_moeda, index=idx)


def _contexto_constante(fechos, s_por_moeda):
    """S constante ao longo de 8 barras (VEL(6) = 0 → nunca veta)."""
    return _frame(fechos, {c: [v] * len(fechos) for c, v in s_por_moeda.items()})


def base_cenario():
    """Grade H1 de 8 fechamentos; alvo = último fechamento."""
    fechos = pd.date_range("2024-01-01 01:00", periods=8, freq="1h")
    alvo = pd.DatetimeIndex([fechos[-1]])
    s = {"AAA": 70.0, "BBB": 60.0, "CCC": 45.0, "DDD": 30.0}
    s_tf = {tf: _contexto_constante(fechos, s) for tf in ("M30", "H1", "H4", "D1")}
    cesta_h1 = _frame(fechos, {c: [1.0] * 8 for c in CUR})
    det = {
        "zvel": _frame(alvo, {"AAA": [2.5], "BBB": [1.0], "CCC": [-2.5], "DDD": [-3.0]}),
        "zs": _frame(alvo, {"AAA": [1.5], "BBB": [0.5], "CCC": [-0.5], "DDD": [-1.5]}),
        "cesta": _frame(alvo, {c: [1.0] for c in CUR}),
    }
    cfg = {"indicator": {"thresholds_atuais":
                         {"zvel_abs": 2.0, "zs_abs": 1.0, "cesta_min": 5, "mtf_min": 2}}}
    n_pares = {c: 7 for c in CUR}
    return alvo, s_tf, cesta_h1, det, cfg, n_pares


def test_mtf_e_candidata_a_mao():
    alvo, s_tf, cesta_h1, det, cfg, n_pares = base_cenario()
    r = cross_tf.mtf_veto_candidata(alvo, s_tf, cesta_h1, det, cfg, CUR, n_pares)
    assert (r["mtf"].iloc[0] == 4.0).all()            # 4 TFs alinhados p/ todos
    assert r["rank_h1"].iloc[0].tolist() == [1, 2, 3, 4]
    assert not r["veto"].iloc[0].any()                # VEL(6)=0 nunca veta
    # candidatas: AAA (2.5/1.5 ✓) e DDD (3.0/1.5 no lado fraco ✓);
    # BBB falha zvel; CCC falha zS
    assert r["candidata"].iloc[0].tolist() == [True, False, False, True]


def test_veto_a_mao():
    alvo, s_tf, cesta_h1, det, cfg, n_pares = base_cenario()
    # AAA é rank 1 (top-2 do lado forte); VEL(6) < 0 em H4 E D1 → VETO
    queda = np.linspace(76, 69, 8)                    # S caindo 1/barra
    for tf in ("H4", "D1"):
        s_tf[tf] = s_tf[tf].copy()
        s_tf[tf]["AAA"] = queda
    r = cross_tf.mtf_veto_candidata(alvo, s_tf, cesta_h1, det, cfg, CUR, n_pares)
    assert bool(r["veto"].iloc[0]["AAA"])
    assert not bool(r["candidata"].iloc[0]["AAA"])    # VETO anula a candidatura
    # BBB (rank 2, top-2) sem queda → sem veto; DDD fraco sem alta → sem veto
    assert not bool(r["veto"].iloc[0]["BBB"])
    assert not bool(r["veto"].iloc[0]["DDD"])


def test_veto_espelhado_moeda_fraca():
    alvo, s_tf, cesta_h1, det, cfg, n_pares = base_cenario()
    # DDD é rank 4 = top-1 do lado fraco; VEL(6) > 0 em H4 e D1 → VETO
    alta = np.linspace(24, 31, 8)
    for tf in ("H4", "D1"):
        s_tf[tf] = s_tf[tf].copy()
        s_tf[tf]["DDD"] = alta
    r = cross_tf.mtf_veto_candidata(alvo, s_tf, cesta_h1, det, cfg, CUR, n_pares)
    assert bool(r["veto"].iloc[0]["DDD"])
    assert not bool(r["candidata"].iloc[0]["DDD"])


def test_asof_nao_olha_o_futuro():
    fechos = pd.date_range("2024-01-01 01:00", periods=3, freq="1h")
    f = pd.DataFrame({"AAA": [1.0, 2.0, 3.0]}, index=fechos)
    alvo = pd.DatetimeIndex(["2024-01-01 00:30", "2024-01-01 01:30",
                             "2024-01-01 03:00"])
    out = cross_tf.asof_ultima_fechada(f, alvo)
    assert np.isnan(out["AAA"].iloc[0])               # nada fechado ainda
    assert out["AAA"].iloc[1] == 1.0                  # só a barra de 01:00
    assert out["AAA"].iloc[2] == 3.0                  # fechamento exato conta


# ---------- zMov / zHist ----------

def test_banda_atr_d1_a_mao():
    idx = pd.date_range("2024-01-01", periods=4, freq="1D")
    d1 = pd.DataFrame({"open": [1, 1, 1, 1], "high": [1.2, 1.4, 1.3, 1.5],
                       "low": [0.8, 1.0, 0.9, 1.1],
                       "close": [1.0, 1.2, 1.1, 1.3]}, index=idx, dtype=float)
    banda = daymove.banda_atr_d1(d1, atr_len=2)
    # dia 3: TRs dos dias 1 e 2 = max(0.4,|1.4-1|,|1-1|)=0.4 e
    # max(0.4,|1.3-1.2|,|0.9-1.2|)=0.4 → soma 0.8; refC = close dia 2 = 1.1
    assert banda.iloc[3] == pytest.approx((0.8 / 2) / 1.1)
    assert banda.iloc[:3].isna().all()


def test_r_por_par_a_mao():
    # 2 dias de M30 (2 barras/dia para simplificar a mão), banda conhecida
    aberturas = pd.DatetimeIndex(["2024-01-01 00:00", "2024-01-01 00:30",
                                  "2024-01-02 00:00", "2024-01-02 00:30"])
    m30 = pd.Series([1.00, 1.02, 1.03, 1.05], index=aberturas)
    idx_d1 = pd.date_range("2023-12-29", periods=5, freq="1D")
    d1 = pd.DataFrame({"open": 1.0, "high": [1.1] * 5, "low": [0.9] * 5,
                       "close": [1.0] * 5}, index=idx_d1, dtype=float)
    r = daymove.r_por_par(m30, d1, atr_len=2)
    # banda constante = (0.2+0.2)/2 / 1.0 = 0.2 (TR=0.2 todos os dias)
    # dia 2, slot 0: c0 = último fechamento ≤ 2024-01-02 00:00 = 1.02;
    # c1 = 1.03 → r = ln(1.03/1.02)/0.2
    dia2 = pd.Timestamp("2024-01-02")
    assert r.loc[dia2, 0] == pytest.approx(np.log(1.03 / 1.02) / 0.2)
    assert r.loc[dia2, 1] == pytest.approx(np.log(1.05 / 1.02) / 0.2)
    # slots sem barra: ffill mantém o último fechamento (r "congela")
    assert r.loc[dia2, 5] == pytest.approx(r.loc[dia2, 1])
    # dia 1 não tem fechamento anterior (c0 NaN) → NaN
    assert np.isnan(r.loc[pd.Timestamp("2024-01-01"), 0])


def _r_moedas_sintetico():
    """25 dias × 48 slots por moeda, com padrão conhecido no slot 10."""
    dias = pd.date_range("2024-01-01", periods=25, freq="1D")
    base = np.zeros((25, 48))
    base[:, 10] = [1.0 if i % 2 == 0 else 2.0 for i in range(25)]  # alterna 1,2
    out = {}
    for j, cur in enumerate(CUR):
        m = base.copy() + j                        # níveis distintos por moeda
        out[cur] = pd.DataFrame(m, index=dias, columns=range(48))
    return dias, out


def test_zhist_a_mao():
    dias, r_moedas = _r_moedas_sintetico()
    _, zhist = daymove.zmov_zhist(r_moedas, n_hist=20)
    # BUG-FOR-BUG (decisão P1 2026-07-16): a âncora do dia 24 exibe o z do
    # DIA 23 (ímpar → valor 2+j); 20 anteriores no slot 10: dez 1s e dez 2s
    # → média 1.5, σ_pop 0.5 → z = (2 - 1.5)/0.5 = +1  (igual p/ toda moeda)
    ancora = dias[24] + pd.Timedelta(seconds=11 * 1800)
    for cur in CUR:
        assert zhist.loc[ancora, cur] == pytest.approx(+1.0)


def test_zmov_a_mao():
    dias, r_moedas = _r_moedas_sintetico()
    zmov, _ = daymove.zmov_zhist(r_moedas, n_hist=20)
    # BUG-FOR-BUG: âncora do dia 24 → z do dia 23 (ímpar), slot 10: valores
    # por moeda [2,3,4,5] → média 3.5, σ_pop=√1.25
    ancora = dias[24] + pd.Timedelta(seconds=11 * 1800)
    assert zmov.loc[ancora, "AAA"] == pytest.approx((2 - 3.5) / np.sqrt(1.25))
    assert zmov.loc[ancora, "DDD"] == pytest.approx((5 - 3.5) / np.sqrt(1.25))
    # slot 0: todas as moedas com r = j → σ>0, mas se todas iguais → NaN
    r_iguais = {c: pd.DataFrame(np.ones((25, 48)), index=dias, columns=range(48))
                for c in CUR}
    zmov2, _ = daymove.zmov_zhist(r_iguais, n_hist=20)
    assert zmov2.isna().all().all()                   # σ transversal = 0


def test_agregar_moedas_badday():
    dias = pd.date_range("2024-01-01", periods=2, freq="1D")
    r_a = pd.DataFrame(np.ones((2, 48)), index=dias, columns=range(48))
    r_b = r_a.copy()
    r_b.iloc[1, :] = np.nan                           # par 2 falha no dia 2
    r_map = {"AAABBB": r_a, "AAACCC": r_b, "BBBCCC": r_a}
    r_m = daymove.agregar_moedas(r_map, list(r_map), ["AAA", "BBB", "CCC"])
    assert r_m["AAA"].iloc[0, 0] == pytest.approx(2.0)   # 1 + 1 (duas bases)
    assert np.isnan(r_m["AAA"].iloc[1, 0])               # badDay propaga
    assert r_m["BBB"].iloc[0, 0] == pytest.approx(0.0)   # -1 (quote) +1 (base)
    assert np.isnan(r_m["CCC"].iloc[1, 0])

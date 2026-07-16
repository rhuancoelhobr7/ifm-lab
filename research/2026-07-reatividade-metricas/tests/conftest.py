"""conftest.py — fixtures compartilhadas dos testes do pipeline E2.

💡 Estes testes rodam SÓ sobre dados sintéticos (fabricados no próprio teste,
com resultados calculados à mão) — nenhum dado real de mercado é tocado aqui,
como manda o PLANO §5/E2. A paridade com o indicador real é a etapa E3.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))


@pytest.fixture()
def cfg():
    """Config mínimo com os parâmetros congelados do indicador (v1.0)."""
    return {
        "indicator": {
            "zcore": True,
            "light_window": 60,
            "met_ring": 64,
            "vel_k": 6,
            "pers_n": 12,
            "zvel_sigma_n": 32,
            "zmov_days_n": 20,
            "cci_length": 20,
            "atr_length": 14,
            "ema_fallback_len": 21,
            "mfc_vol_length": 20,
            "thresholds_atuais": {
                "zvel_abs": 2.0, "zs_abs": 1.0, "vel_abs": 17.6,
                "pers": 0.58, "cesta_min": 5, "mtf_min": 2,
            },
        },
    }


def barras_aleatorias(n: int, seed: int) -> pd.DataFrame:
    """Passeio aleatório OHLCV plausível, indexado por horários H1."""
    rng = np.random.default_rng(seed)
    close = 1.10 + np.cumsum(rng.normal(0, 0.0008, n))
    spread_hl = np.abs(rng.normal(0.0006, 0.0002, n))
    high = np.maximum(close, np.roll(close, 1)) + spread_hl
    low = np.minimum(close, np.roll(close, 1)) - spread_hl
    open_ = np.roll(close, 1)
    open_[0] = close[0]
    vol = rng.integers(50, 5000, n).astype(float)
    idx = pd.date_range("2024-01-02", periods=n, freq="1h")
    return pd.DataFrame({"open": open_, "high": high, "low": low,
                         "close": close, "tick_volume": vol}, index=idx)

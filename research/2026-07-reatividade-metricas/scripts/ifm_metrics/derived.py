"""derived.py — métricas derivadas da série S: vel, acel, zvel, zS e rank H1.

Fidelidade a MetVel/MetAcel/MetZVel/RenderMetrics/MetRankH1 do IFM.mq5:
- **Regra de fatia**: as derivadas exigem a fatia INTEIRA válida (MetSliceOk),
  não só os extremos — vel(k) precisa das k+1 barras, acel de 2k+1, zvel de
  n+1. Um NaN no meio invalida o valor daquele ponto.
- **zvel**: vel / (σ(ΔS) × √k), σ POPULACIONAL (com média subtraída) dos
  últimos n passos de S. Denominador < 1e-9 → NaN.
  💡 É a pergunta "esse deslocamento de 6 barras é grande comparado ao balanço
  típico?" — normaliza como passeio aleatório (ruído acumula com √k).
- **zS**: z transversal — (S da moeda − média das 8) / σ populacional das 8 no
  mesmo instante; exige ≥ 4 moedas válidas e σ ≥ 1e-9.
- **rank H1**: 1 = mais forte por S; desempate: cesta desc, depois alfabético.
  NaN vale -1e9 (S) / -1 (cesta) na ordenação, como no fonte.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _fatia_ok(s: pd.Series, m: int) -> pd.Series:
    """True onde as últimas m observações de S são todas válidas."""
    return s.rolling(m).count() == m


def vel(s: pd.Series, k: int) -> pd.Series:
    return (s - s.shift(k)).where(_fatia_ok(s, k + 1))


def acel(s: pd.Series, k: int) -> pd.Series:
    a = (s - s.shift(k)) - (s.shift(k) - s.shift(2 * k))
    return a.where(_fatia_ok(s, 2 * k + 1))


def zvel(s: pd.Series, k: int, n: int) -> pd.Series:
    v = vel(s, k)
    d = s.diff()
    sd = d.rolling(n).std(ddof=0)          # populacional, média subtraída
    den = sd * np.sqrt(float(k))
    z = v / den
    return z.where(_fatia_ok(s, n + 1) & v.notna() & (den >= 1e-9))


def zs_transversal(s_frame: pd.DataFrame) -> pd.DataFrame:
    """zS por instante: colunas = moedas. ≥4 válidas e σ≥1e-9, senão NaN."""
    m = s_frame.count(axis=1)
    media = s_frame.mean(axis=1)
    sd = s_frame.std(axis=1, ddof=0)
    z = s_frame.sub(media, axis=0).div(sd, axis=0)
    ok = (m >= 4) & (sd >= 1e-9)
    return z.where(ok, np.nan)


def rank_h1(s_h1: pd.DataFrame, cesta_h1: pd.DataFrame,
            currencies: list[str]) -> pd.DataFrame:
    """Rank 1–8 por instante (colunas = moedas), critério exato de MetRankH1.

    Ordena por: S desc (NaN=-1e9), cesta desc (NaN=-1), moeda alfabética asc.
    """
    cols = list(currencies)
    s2 = s_h1[cols].fillna(-1e9).to_numpy(dtype=float)
    c2 = cesta_h1[cols].fillna(-1.0).to_numpy(dtype=float)
    t_n, n_cur = s2.shape
    alfa = np.array([sorted(cols).index(c) for c in cols], dtype=float)

    # lexsort com a linha (instante) como chave primária → ordena dentro de
    # cada instante por S desc, cesta desc, alfabeto asc, tudo de uma vez
    linha = np.repeat(np.arange(t_n), n_cur)
    ordem = np.lexsort((np.tile(alfa, t_n), -c2.ravel(), -s2.ravel(), linha))
    pos_no_instante = np.empty(t_n * n_cur, dtype=int)
    pos_no_instante[ordem] = np.tile(np.arange(1, n_cur + 1), t_n)
    return pd.DataFrame(pos_no_instante.reshape(t_n, n_cur),
                        index=s_h1.index, columns=cols)

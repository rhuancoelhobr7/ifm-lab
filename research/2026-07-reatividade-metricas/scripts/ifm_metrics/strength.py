"""strength.py — força S por moeda e cesta, fiéis a MetRebuild do IFM.mq5.

💡 Força S: cada par é uma "partida" entre duas moedas; o IFM do par diz quem
está ganhando (0–100, 50 = empate). dir = (IFM−50)/50 é creditado à moeda base
e debitado da cotada; S(moeda) = 50 + média dos 7 confrontos × 50.
Regra de integridade do painel: se QUALQUER par da moeda está sem dado no
instante t, o S da moeda em t é NaN — nunca imputamos neutro.

💡 Cesta: dos 7 pares da moeda, quantos confirmam o lado do S dela agora?
Par com IFM exatamente 50 (lado indefinido) não confirma, mas não invalida.
S exatamente 50 (lado da moeda indefinido) → cesta NaN, como no fonte.
Valor armazenado como fração conf/n_pares (0–1), idem `g_metCesta`.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def mapa_pares(pairs: list[str], currencies: list[str]) -> list[tuple[str, str, str]]:
    """[(par, base, cotada)] — nomes canônicos de 6 letras (ex.: EURUSD)."""
    out = []
    for p in pairs:
        base, quote = p[:3], p[3:6]
        if base not in currencies or quote not in currencies:
            raise ValueError(f"par fora do G8: {p}")
        out.append((p, base, quote))
    return out


def forca_s(ifm: pd.DataFrame, pairs: list[str], currencies: list[str]) -> pd.DataFrame:
    """S por moeda (colunas = moedas), a partir do IFM por par (colunas = pares).

    NaN em qualquer par da moeda no instante t → S(moeda, t) = NaN.
    """
    mapa = mapa_pares(pairs, currencies)
    dir_ = (ifm - 50.0) / 50.0
    out = {}
    for cur in currencies:
        cols_base = [p for p, b, q in mapa if b == cur]
        cols_quote = [p for p, b, q in mapa if q == cur]
        n = len(cols_base) + len(cols_quote)
        if n == 0:
            out[cur] = pd.Series(np.nan, index=ifm.index)
            continue
        soma = dir_[cols_base].sum(axis=1, min_count=len(cols_base)) if cols_base else 0.0
        soma = soma - (dir_[cols_quote].sum(axis=1, min_count=len(cols_quote)) if cols_quote else 0.0)
        out[cur] = 50.0 + (soma / n) * 50.0
    return pd.DataFrame(out, index=ifm.index)


def cesta(ifm: pd.DataFrame, s: pd.DataFrame,
          pairs: list[str], currencies: list[str]) -> pd.DataFrame:
    """Fração da cesta confirmando o lado do S da moeda (0–1); NaN se algum par
    da moeda está NaN ou se o lado é indefinido (S = 50 ou NaN)."""
    mapa = mapa_pares(pairs, currencies)
    pside = np.sign(ifm - 50.0)          # NaN propaga
    out = {}
    for cur in currencies:
        meus = [(p, b == cur) for p, b, q in mapa if b == cur or q == cur]
        n = len(meus)
        if n == 0:
            out[cur] = pd.Series(np.nan, index=ifm.index)
            continue
        lado = np.sign(s[cur] - 50.0)
        conf = pd.Series(0.0, index=ifm.index)
        algum_nan = pd.Series(False, index=ifm.index)
        for p, sou_base in meus:
            ps = pside[p]
            algum_nan |= ps.isna()
            alvo = lado if sou_base else -lado
            conf += (ps == alvo).astype(float)   # ps==0 não confirma, não macula
        val = conf / n
        val[algum_nan | lado.isna() | (lado == 0)] = np.nan
        out[cur] = val
    return pd.DataFrame(out, index=ifm.index)

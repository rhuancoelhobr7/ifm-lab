"""light.py — IFM Light vetorizado (4 juízes), fiel a CalcIFMLightAt do IFM.mq5.

💡 O que é o IFM Light: a nota 0–100 de pressão compradora/vendedora de UM par,
calculada só com as últimas 60 barras (LIGHT_WINDOW). Quatro "juízes" votam:
Pivot (±2), Market Profile via EMA (±2), MFC de Bill Williams (±1) e o juiz
CCI (±3) — que no núcleo Z (InpZCore=true, o congelado nesta pesquisa) vira um
z-score contínuo do preço típico, clampado em ±2. O placar bruto (±15) é
reescalado para 0–100.

Fidelidade ao fonte (IFM.mq5 v1.0, linhas 555–696) — notas de arqueologia:
- **O juiz MP é código morto com os parâmetros atuais**: o guard exige
  copied ≥ 3×EMA_len+2 = 65 barras, mas a janela é capada em LIGHT_WINDOW=60.
  Logo scoreMP = 0 SEMPRE. Reproduzimos o guard (e a fórmula, para o caso de a
  janela mudar um dia), não o "conserto".
- O indicador devolve 50 (neutro) quando copied < max(CCI,EMA)+5 = 26 barras;
  mas o ring do painel (MetRebuild) só aceita janelas COMPLETAS de 60 barras —
  qualquer coisa menor vira EMPTY_VALUE. O pipeline segue o ring: janela
  incompleta (ou com barra faltante no meio) = NaN, nunca 50.
- Volume: real_volume se > 0, senão tick_volume se > 0, senão 1.0
  (VolFromRates). Barra NaN propaga NaN.

Regra de NaN (config nan.politica=propagar): a série de entrada vive numa grade
temporal (união das barras dos pares); barra ausente = linha NaN; qualquer NaN
dentro da janela de 60 barras torna o IFM daquele ponto NaN.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def volume_efetivo(df: pd.DataFrame) -> pd.Series:
    """VolFromRates: real_volume>0 ? real : (tick_volume>0 ? tick : 1.0)."""
    tick = df["tick_volume"].astype(float)
    real = df["real_volume"].astype(float) if "real_volume" in df.columns else pd.Series(0.0, index=df.index)
    v = np.where(real > 0, real, np.where(tick > 0, tick, 1.0))
    out = pd.Series(v, index=df.index)
    out[tick.isna()] = np.nan
    return out


def pivot_score(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """Juiz 1 — pivô clássico da barra anterior (voto -2…+2)."""
    pp = (high.shift(1) + low.shift(1) + close.shift(1)) / 3.0
    r1 = 2.0 * pp - low.shift(1)
    s1 = 2.0 * pp - high.shift(1)
    sc = pd.Series(0.0, index=close.index)
    sc = sc.mask((close > pp), 1.0).mask((close > pp) & (close > r1), 2.0)
    sc = sc.mask((close < pp), -1.0).mask((close < pp) & (close < s1), -2.0)
    return sc.mask(pp.isna() | close.isna())


def ema_janelada(close: pd.Series, period: int, n_taps: int) -> pd.Series:
    """EmaFromRates numa janela deslizante: EMA SEMEADA `n_taps-1` barras atrás
    (fonte: min(3×período, barras disponíveis)) e atualizada até a barra atual.

    💡 Não é a EMA usual (que carrega memória infinita): cada ponto t usa só
    `n_taps` barras, com o seed na mais antiga delas. Isso a torna um filtro
    FIR de `n_taps` pesos fixos — vetorizável por convolução.
    """
    k = 2.0 / (period + 1.0)
    n = int(n_taps)
    c = close.to_numpy(dtype=float)
    if len(c) < n:
        return pd.Series(np.nan, index=close.index)
    # recursão vetorizada POR LINHA: mesma ordem de operações do loop MQL5
    # (bitwise-idêntico; uma convolução mudaria a ordem de arredondamento e
    # flipparia comparações estritas como ema0 > ema1 em quase-empates)
    jan = np.lib.stride_tricks.sliding_window_view(c, n)   # (T-n+1, n)
    ema = jan[:, 0].copy()                                 # seed = barra mais antiga
    for i in range(1, n):
        ema = jan[:, i] * k + ema * (1.0 - k)
    vals = np.full(len(c), np.nan)
    vals[n - 1:] = ema
    out = pd.Series(vals, index=close.index)
    return out.mask(close.rolling(n).count() < n)


def mp_score(close: pd.Series, ema_len: int, window: int) -> pd.Series:
    """Juiz 2 — Market Profile aproximado por EMA (voto -2…+2).

    Reproduz o guard do fonte: só computa se window ≥ 3×ema_len+2; senão o voto
    é 0 constante (o caso dos parâmetros congelados: 60 < 65 → juiz mudo).
    O seed do EmaFromRates fica min(3×período, janela−1) barras atrás — para
    ema1 (avaliado em t−1) o alcance é min(3×período, janela−2)."""
    if window < 3 * ema_len + 2:
        return pd.Series(0.0, index=close.index)
    ema0 = ema_janelada(close, ema_len, min(3 * ema_len, window - 1) + 1)
    ema1 = ema_janelada(close, ema_len, min(3 * ema_len, window - 2) + 1).shift(1)
    vah, val = ema0 * 1.01, ema0 * 0.99
    sc = pd.Series(0.0, index=close.index)
    sc = sc.mask(close > vah, 1.0).mask((close > vah) & (ema0 > ema1), 2.0)
    sc = sc.mask(close < val, -1.0).mask((close < val) & (ema0 < ema1), -2.0)
    return sc.mask(ema0.isna() | ema1.isna() | close.isna())


def mfc_score(high: pd.Series, low: pd.Series, vol: pd.Series, vol_len: int) -> pd.Series:
    """Juiz 3 — Market Facilitation (voto -1/0/+1).

    MFC = (high-low)/volume; compara com a barra anterior e o volume com a
    média das últimas `vol_len` barras (INCLUINDO a atual, como no fonte)."""
    mfc0 = (high - low) / vol
    mfc1 = mfc0.shift(1)
    avg = vol.rolling(vol_len, min_periods=vol_len).mean()
    up, vup = mfc0 > mfc1, vol > avg
    sc = pd.Series(0.0, index=high.index)
    sc = sc.mask(up & vup, 1.0).mask(~up & vup, -1.0)
    return sc.mask(mfc0.isna() | mfc1.isna() | avg.isna())


def tp_zscore(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    """TpZScore — z-score populacional do preço típico na janela `period`.

    💡 O "juiz contínuo" do núcleo Z: quantos desvios o preço típico atual está
    acima/abaixo da sua média das últimas 20 barras. σ=0 → 0 (como no fonte).
    O clamp ±2 é aplicado pelo agregador (voto do juiz), não aqui."""
    tp = (high + low + close) / 3.0
    m = tp.rolling(period).mean()
    sd = tp.rolling(period).std(ddof=0)
    z = ((tp - m) / sd).where(sd != 0, 0.0)
    return z.mask(m.isna())


def cci_lambert(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    """CciFromRates — CCI de Lambert manual (usado só no núcleo clássico).

    Nota: usa rolling.apply (lento); o núcleo congelado da pesquisa é o Z."""
    tp = (high + low + close) / 3.0
    sma = tp.rolling(period).mean()
    md = tp.rolling(period).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    cci = ((tp - sma) / (0.015 * md)).where(md != 0, 0.0)
    return cci.mask(sma.isna())


def cci_score_classico(cci: pd.Series) -> pd.Series:
    """Voto em degraus do juiz CCI clássico (-2…+2)."""
    sc = pd.Series(0.0, index=cci.index)
    sc = sc.mask(cci > 0, 1.0).mask(cci > 100, 2.0)
    sc = sc.mask(cci < 0, -1.0).mask(cci < -100, -2.0)
    return sc.mask(cci.isna())


def ifm_light(df: pd.DataFrame, cfg: dict) -> pd.Series:
    """IFM Light 0–100 por barra, NaN onde a janela de 60 barras é incompleta.

    `df`: colunas high, low, close, tick_volume (+real_volume opcional), numa
    grade temporal fixa do TF (linhas NaN para barras ausentes).
    `cfg`: bloco `indicator` do config.yaml da pesquisa.
    """
    ind = cfg["indicator"]
    window = int(ind["light_window"])
    h, l, c = df["high"], df["low"], df["close"]
    vol = volume_efetivo(df)

    p = pivot_score(h, l, c)
    mp = mp_score(c, int(ind.get("ema_fallback_len", 21)), window)
    mfc = mfc_score(h, l, vol, int(ind.get("mfc_vol_length", 20)))
    if ind["zcore"]:
        juiz_cci = tp_zscore(h, l, c, int(ind["cci_length"])).clip(-2.0, 2.0)
    else:
        juiz_cci = cci_score_classico(cci_lambert(h, l, c, int(ind["cci_length"])))

    bruto = 2.0 * p + 2.0 * mp + 1.0 * mfc + 3.0 * juiz_cci
    ifm = ((bruto + 15.0) / 30.0 * 100.0).clip(0.0, 100.0)

    # regra do ring (MetRebuild): só vale com 60 barras VÁLIDAS consecutivas
    valida = h.notna() & l.notna() & c.notna() & vol.notna()
    janela_ok = valida.astype(float).rolling(window).sum() == window
    return ifm.where(janela_ok)

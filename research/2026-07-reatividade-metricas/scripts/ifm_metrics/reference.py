"""reference.py — porta de referência em LOOP, tradução literal do MQL5.

💡 Para que serve: é o "gêmeo lento" do pipeline. Cada função aqui traduz o
fonte do IFM.mq5 linha a linha (mesmos índices as-series, mesmos guards,
mesmos retornos neutros), sem nenhuma esperteza de vetorização. Os testes
comparam a versão vetorizada (light.py/derived.py) contra esta em dados
sintéticos aleatórios: se as duas concordam, um erro de tradução teria que
existir DUAS vezes, de formas diferentes, para passar. A paridade contra o
indicador de verdade continua sendo o E3 (critério C1).

Convenção: arrays "as-series" como no MQL5 — índice 0 = barra MAIS NOVA.
"""

from __future__ import annotations

import math

EMPTY = float("nan")


def _ema_from_rates(closes: list[float], period: int, at_idx: int, total: int) -> float:
    """EmaFromRates (IFM.mq5:555)."""
    seed_start = min(at_idx + period * 3, total - 1)
    ema = closes[seed_start]
    k = 2.0 / (period + 1.0)
    for i in range(seed_start - 1, at_idx - 1, -1):
        ema = closes[i] * k + ema * (1.0 - k)
    return ema


def _tp(h, l, c, i):
    return (h[i] + l[i] + c[i]) / 3.0


def tp_zscore(h: list, l: list, c: list, period: int, at_idx: int) -> float:
    """TpZScore (IFM.mq5:586)."""
    soma = sum(_tp(h, l, c, i) for i in range(at_idx, at_idx + period))
    sma = soma / period
    ss = sum((_tp(h, l, c, i) - sma) ** 2 for i in range(at_idx, at_idx + period))
    sd = math.sqrt(ss / period)
    if sd == 0:
        return 0.0
    return (_tp(h, l, c, at_idx) - sma) / sd


def cci_lambert(h: list, l: list, c: list, period: int, at_idx: int) -> float:
    """CciFromRates (IFM.mq5:566)."""
    tps = [_tp(h, l, c, i) for i in range(at_idx, at_idx + period)]
    sma = sum(tps) / period
    mean_dev = sum(abs(t - sma) for t in tps) / period
    if mean_dev == 0:
        return 0.0
    return (tps[0] - sma) / (0.015 * mean_dev)


def _vol(tick: list, real: list, i: int) -> float:
    """VolFromRates (IFM.mq5:604)."""
    if real[i] > 0:
        return float(real[i])
    if tick[i] > 0:
        return float(tick[i])
    return 1.0


def calc_ifm_light_at(h: list, l: list, c: list, tick: list, real: list,
                      at_idx: int, copied_total: int, cfg: dict) -> float:
    """CalcIFMLightAt (IFM.mq5:613) — retorna 50.0 nos guards, como o fonte.

    Arrays as-series (0 = mais novo). `cfg` = bloco indicator do config.yaml.
    """
    ind = cfg["indicator"]
    window = int(ind["light_window"])
    cci_len = int(ind["cci_length"])
    ema_len = int(ind.get("ema_fallback_len", 21))
    vol_len = int(ind.get("mfc_vol_length", 20))
    copied = min(copied_total - at_idx, window)
    if copied < max(cci_len, ema_len) + 5:
        return 50.0

    score_pivot = 0
    if copied >= 2:
        pp = _tp(h, l, c, at_idx + 1)
        r1 = 2.0 * pp - l[at_idx + 1]
        s1 = 2.0 * pp - h[at_idx + 1]
        cl = c[at_idx]
        if cl > pp and cl > r1:
            score_pivot = 2
        elif cl > pp:
            score_pivot = 1
        elif cl < pp and cl < s1:
            score_pivot = -2
        elif cl < pp:
            score_pivot = -1

    score_mp = 0
    if copied >= ema_len * 3 + 2:
        ema0 = _ema_from_rates(c, ema_len, at_idx, at_idx + copied)
        ema1 = _ema_from_rates(c, ema_len, at_idx + 1, at_idx + copied)
        vah, val = ema0 * 1.01, ema0 * 0.99
        cl = c[at_idx]
        if cl > vah and ema0 > ema1:
            score_mp = 2
        elif cl > vah:
            score_mp = 1
        elif cl < val and ema0 < ema1:
            score_mp = -2
        elif cl < val:
            score_mp = -1

    score_mfc = 0
    if copied >= vol_len + 2:
        vol0, vol1 = _vol(tick, real, at_idx), _vol(tick, real, at_idx + 1)
        mfc0 = (h[at_idx] - l[at_idx]) / vol0 if vol0 > 0 else 0
        mfc1 = (h[at_idx + 1] - l[at_idx + 1]) / vol1 if vol1 > 0 else 0
        avg = 0.0
        cnt = 0
        for j in range(min(vol_len, copied)):
            avg += _vol(tick, real, at_idx + j)
            cnt += 1
        avg = avg / cnt if cnt > 0 else 1.0
        var_preco, var_volume = mfc0 > mfc1, vol0 > avg
        if var_preco and var_volume:
            score_mfc = 1
        elif not var_preco and var_volume:
            score_mfc = -1

    score_cci = 0.0
    if copied >= cci_len + 2:
        if ind["zcore"]:
            score_cci = max(-2.0, min(2.0, tp_zscore(h, l, c, cci_len, at_idx)))
        else:
            cci = cci_lambert(h, l, c, cci_len, at_idx)
            if cci > 100:
                score_cci = 2
            elif cci > 0:
                score_cci = 1
            elif cci < -100:
                score_cci = -2
            elif cci < 0:
                score_cci = -1

    bruto = score_pivot * 2.0 + score_mp * 2.0 + score_mfc * 1.0 + score_cci * 3.0
    return max(0.0, min(100.0, (bruto + 15.0) / 30.0 * 100.0))


# --- derivadas sobre a série S (cronológica: s[-1] = t0), ring de `ring` ---

def _is_nan(v: float) -> bool:
    return v != v


def _slice_ok(s: list, from_idx: int) -> bool:
    return all(not _is_nan(s[i]) for i in range(from_idx, len(s)))


def met_vel(s: list, k: int) -> float:
    """MetVel (IFM.mq5:833) — s cronológico, tamanho = MET_RING."""
    ring = len(s)
    if k + 1 > ring or not _slice_ok(s, ring - 1 - k):
        return EMPTY
    return s[ring - 1] - s[ring - 1 - k]


def met_acel(s: list, k: int) -> float:
    """MetAcel (IFM.mq5:839)."""
    ring = len(s)
    if 2 * k + 1 > ring or not _slice_ok(s, ring - 1 - 2 * k):
        return EMPTY
    return (s[ring - 1] - s[ring - 1 - k]) - (s[ring - 1 - k] - s[ring - 1 - 2 * k])


def met_zvel(s: list, k: int, n: int) -> float:
    """MetZVel (IFM.mq5:846)."""
    ring = len(s)
    v = met_vel(s, k)
    if _is_nan(v):
        return EMPTY
    if n + 1 > ring or not _slice_ok(s, ring - 1 - n):
        return EMPTY
    soma = ss = 0.0
    m = 0
    for i in range(ring - n, ring):
        d = s[i] - s[i - 1]
        soma += d
        ss += d * d
        m += 1
    media = soma / m
    sd = math.sqrt(max(ss / m - media * media, 0.0))
    den = sd * math.sqrt(float(k))
    if den < 1e-9:
        return EMPTY
    return v / den

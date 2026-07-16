"""daymove.py — zMov e zHist: o movimento do dia, medido "até a mesma hora".

💡 A ideia (MetRebuild, bloco final do IFM.mq5): a cada âncora (fechamento de
barra M30), mede-se quanto cada par andou DESDE 00:00 do dia até aquela hora,
em unidades de ATR diário — e o mesmo trecho de relógio é medido nos N dias
anteriores, para comparação justa (as 10h de hoje contra as 10h de cada dia
passado, nunca contra dias completos). O movimento é creditado/debitado nas
duas moedas do par, como no S. Daí saem dois z-scores por moeda:
- **zHist**: o dia de hoje é normal ou excepcional PARA ELA MESMA? (z contra
  os últimos N dias na mesma hora; exige ≥10 dias válidos);
- **zMov**: quem mais andou hoje ENTRE AS 8? (z transversal; exige ≥4 moedas).

Fórmulas exatas do fonte:
- r = log(c1/c0) / ((ATR14_soma/14) / refC), onde c0 = último fechamento M30
  ≤ 00:00 do dia, c1 = último fechamento M30 ≤ 00:00+tod, ATR14_soma = soma
  dos 14 True Ranges D1 ANTERIORES ao dia, refC = fechamento D1 da véspera.
- Dia inválido para a moeda se QUALQUER par dela falhar (badDay) — NaN.
- zHist: média/σ populacional dos dias passados válidos entre os N anteriores
  (N = clamp(zmov_days_n, 5, 38)); σ < 1e-9 → NaN.
- zMov: média/σ populacional das moedas válidas hoje; exige σ > 1e-9.

Divergência DOCUMENTADA vs. o indicador: o fonte alinha "dia i" por CONTAGEM
de barras D1 de cada par; aqui alinhamos por DATA DE CALENDÁRIO (união dos
dias). Só difere quando um par pula um dia D1 que os outros têm — nesses dias
o painel mistura datas diferentes entre pares e nós marcamos NaN (mais
conservador). Conferir no E3 se algum desvio de paridade cai nesses dias.

BUG-FOR-BUG (decisão P1, 2026-07-16, PROGRESS): o painel AO VIVO exibe, no
dia D, o movimento do dia D−1 até a mesma hora (off-by-one do MetAnchorShift
no D1 — descoberta 4 do PROGRESS). Reproduzimos esse comportamento: o z
calculado para o dia D é carimbado nas âncoras do dia SEGUINTE (`empilhar`).
Se o indicador for corrigido (v1.0.1), reverter o deslocamento aqui.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

SLOTS_DIA = 48          # barras M30 por dia (tod = (slot+1) × 1800 s)
SEG_SLOT = 1800


def banda_atr_d1(d1: pd.DataFrame, atr_len: int = 14) -> pd.Series:
    """Banda de normalização por dia: (soma dos `atr_len` TRs anteriores /
    atr_len) / fechamento da véspera. Indexada pela data do dia (open D1)."""
    pc = d1["close"].shift(1)
    tr = np.maximum(d1["high"] - d1["low"],
                    np.maximum((d1["high"] - pc).abs(), (d1["low"] - pc).abs()))
    soma = tr.rolling(atr_len, min_periods=atr_len).sum().shift(1)
    ref_c = d1["close"].shift(1)
    banda = (soma / atr_len) / ref_c
    banda = banda.where((ref_c > 0) & (soma > 0))
    banda.index = pd.DatetimeIndex(d1.index).normalize()
    return banda


def r_por_par(m30_close: pd.Series, d1: pd.DataFrame, atr_len: int = 14) -> pd.DataFrame:
    """Matriz r[data, slot 0..47] do par: movimento do dia até cada meia hora,
    em ATRs diários. NaN onde faltou fechamento de referência ou banda.

    m30_close: fechamentos M30 indexados pelo horário de ABERTURA da barra.
    d1: OHLC diário indexado pela abertura (00:00 do dia).
    """
    ot = pd.DatetimeIndex(m30_close.index)
    dia = ot.normalize()
    slot = ((ot - dia).total_seconds() // SEG_SLOT).astype(int)
    mat = (pd.DataFrame({"dia": dia, "slot": slot, "c": m30_close.to_numpy()})
           .pivot_table(index="dia", columns="slot", values="c", aggfunc="last")
           .reindex(columns=range(SLOTS_DIA)))

    banda = banda_atr_d1(d1, atr_len)
    todas = mat.index.union(banda.index)
    mat = mat.reindex(todas)

    # ffill achatado: C[dia, slot] = último fechamento ≤ dia + (slot+1)*1800
    flat = pd.Series(mat.to_numpy().ravel()).ffill().to_numpy()
    c1 = flat.reshape(len(todas), SLOTS_DIA)
    c0 = np.concatenate(([np.nan], flat))[:-1].reshape(len(todas), SLOTS_DIA)[:, 0]

    banda_v = banda.reindex(todas).to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        r = np.log(c1 / c0[:, None]) / banda_v[:, None]
    invalido = ~((c1 > 0) & (c0[:, None] > 0) & (banda_v[:, None] > 0))
    r[invalido] = np.nan
    return pd.DataFrame(r, index=todas, columns=range(SLOTS_DIA))


def agregar_moedas(r_map: dict[str, pd.DataFrame],
                   pairs: list[str], currencies: list[str]) -> dict[str, pd.DataFrame]:
    """R por moeda: soma dos r dos pares onde é base, menos onde é cotada.
    NaN se qualquer par da moeda estiver NaN naquele (dia, slot) — badDay."""
    todas = None
    for f in r_map.values():
        todas = f.index if todas is None else todas.union(f.index)
    alinhado = {p: f.reindex(todas) for p, f in r_map.items()}
    out = {}
    for cur in currencies:
        base = [p for p in pairs if p[:3] == cur]
        quote = [p for p in pairs if p[3:6] == cur]
        acc = None
        valido = None
        for p in base + quote:
            f = alinhado[p]
            sinal = 1.0 if p in base else -1.0
            acc = sinal * f if acc is None else acc + sinal * f
            valido = f.notna() if valido is None else (valido & f.notna())
        out[cur] = acc.where(valido) if acc is not None else pd.DataFrame(
            np.nan, index=todas, columns=range(SLOTS_DIA))
    return out


def zmov_zhist(r_moedas: dict[str, pd.DataFrame], n_hist: int
               ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(zMov, zHist) por moeda, indexados pelo timestamp da âncora (fechamento
    da barra M30 = dia + (slot+1)×1800 s)."""
    n_h = int(min(max(n_hist, 5), 38))              # clamp do fonte
    currencies = list(r_moedas.keys())
    idx_dias = next(iter(r_moedas.values())).index

    zhist = {}
    for cur, r in r_moedas.items():
        passado = r.shift(1)                         # dias anteriores, mesma hora
        m = passado.rolling(n_h, min_periods=10).count()
        media = passado.rolling(n_h, min_periods=10).mean()
        sd = passado.rolling(n_h, min_periods=10).std(ddof=0)
        z = (r - media) / sd
        zhist[cur] = z.where(r.notna() & (m >= 10) & (sd >= 1e-9))

    # zMov: transversal por (dia, slot) sobre as moedas válidas (média/σ
    # populacionais só das válidas — soma manual, sem warnings de fatia vazia)
    pilha = np.stack([r_moedas[c].to_numpy() for c in currencies])   # (8, dias, slots)
    m8 = np.sum(~np.isnan(pilha), axis=0)
    den = np.where(m8 > 0, m8, np.nan)
    mean8 = np.nansum(np.nan_to_num(pilha, nan=0.0), axis=0) / den
    e2 = np.nansum(np.nan_to_num(pilha ** 2, nan=0.0), axis=0) / den
    sd8 = np.sqrt(np.maximum(e2 - mean8 ** 2, 0.0))
    zmov = {}
    for i, cur in enumerate(currencies):
        with np.errstate(invalid="ignore", divide="ignore"):
            z = (pilha[i] - mean8) / sd8
        ok = (~np.isnan(pilha[i])) & (m8 >= 4) & (sd8 > 1e-9)
        zmov[cur] = pd.DataFrame(np.where(ok, z, np.nan),
                                 index=idx_dias, columns=range(SLOTS_DIA))

    def empilhar(mapa: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """(dia × slot) → série longa indexada pelo fechamento da âncora do
        DIA SEGUINTE (bug-for-bug com o painel AO VIVO, decisão P1 de
        2026-07-16 no PROGRESS: `MetAnchorShift` devolve shift 1, e no D1
        intradiário o shift 1 é ONTEM — então o painel exibe, no dia D, o
        movimento do dia D−1 até a mesma hora; paridade E3 confirmou
        golden(T) = python(T−1 dia útil) com diferença 0.0)."""
        out = {}
        for cur, f in mapa.items():
            dias = pd.DatetimeIndex(f.index)
            if len(dias) < 2:
                out[cur] = pd.Series(dtype=float)
                continue
            ts = (np.repeat(dias[1:].to_numpy(), SLOTS_DIA)
                  + np.tile(((np.arange(SLOTS_DIA) + 1) * SEG_SLOT)
                            .astype("timedelta64[s]"), len(dias) - 1))
            out[cur] = pd.Series(f.to_numpy()[:-1].ravel(), index=pd.DatetimeIndex(ts))
        return pd.DataFrame(out).sort_index()

    return empilhar(zmov), empilhar(zhist)

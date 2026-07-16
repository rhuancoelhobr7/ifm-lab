"""cross_tf.py — métricas multi-timeframe: mtf, VETO e candidata.

💡 Estas três métricas cruzam timeframes: o painel olha, no MESMO instante, a
última barra FECHADA de cada TF (anti-look-ahead — nunca uma barra em curso).
Na pesquisa reproduzimos isso com alinhamento "as-of": para cada instante da
grade do TF de detecção, buscamos o último fechamento ≤ aquele instante em
cada TF de contexto.

Definições (RenderMetrics, IFM.mq5):
- **refSide**: lado do S em H1 (sinal de S_H1 − 50; NaN/50 → indefinido).
- **mtf**: de M30/H1/H4/D1, quantos têm S válido do MESMO lado do refSide.
  refSide indefinido → mtf indefinido (NaN; o fonte usa sentinela -1).
- **VETO**: moeda no top-2 do ranking H1 PELO SEU LADO (2 mais fortes se
  forte; 2 mais fracas se fraca) E VEL(6) contrária ao lado em H4 E em D1.
  ⚠ o k do VETO é 6 FIXO no fonte (linha 1146), independente de InpMetVelK.
- **candidata**: |zvel| ≥ thr E |zS| ≥ thr E cesta×n ≥ mínimo E mtf ≥ mínimo
  E sem VETO E lado definido. zvel/zS/cesta são do TF de detecção; refSide,
  mtf e VETO vêm de H1/M30–D1.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import derived

VETO_VEL_K = 6   # fixo no fonte (MetVel(sr6H4, 6)), NÃO segue indicator.vel_k


def asof_ultima_fechada(frame: pd.DataFrame, alvo: pd.DatetimeIndex) -> pd.DataFrame:
    """Reamostra um frame indexado por HORÁRIO DE FECHAMENTO de barra para a
    grade `alvo`: em cada instante do alvo, o valor da última barra já fechada
    (fechamento ≤ instante). Nunca olha barra futura ou em curso."""
    idx = frame.index
    pos = idx.searchsorted(alvo, side="right") - 1
    out = frame.iloc[np.clip(pos, 0, len(idx) - 1)].to_numpy()
    out = pd.DataFrame(out, index=alvo, columns=frame.columns)
    out[pos < 0] = np.nan          # alvo anterior à primeira barra fechada
    return out


def mtf_veto_candidata(alvo: pd.DatetimeIndex,
                       s_por_tf: dict[str, pd.DataFrame],
                       cesta_h1: pd.DataFrame,
                       det: dict[str, pd.DataFrame],
                       cfg: dict,
                       currencies: list[str],
                       n_pares: dict[str, int]) -> dict[str, pd.DataFrame]:
    """Calcula refSide, mtf, veto e candidata na grade `alvo`.

    s_por_tf: S por moeda de M30/H1/H4/D1, cada um indexado por FECHAMENTO.
    cesta_h1: cesta de H1 (fração 0–1), indexada por fechamento.
    det: métricas do TF de detecção JÁ na grade alvo: {"zvel","zs","cesta"}.
    """
    thr = cfg["indicator"]["thresholds_atuais"]
    ctx = {tf: asof_ultima_fechada(f, alvo) for tf, f in s_por_tf.items()}
    cesta_h1_a = asof_ultima_fechada(cesta_h1, alvo)

    s_h1 = ctx["H1"]
    ref_side = pd.DataFrame(np.sign(s_h1 - 50.0), index=alvo, columns=currencies)
    ref_side = ref_side.fillna(0.0)                    # NaN → lado indefinido

    # mtf: contagem de TFs alinhados ao refSide (NaN onde refSide indefinido)
    mtf = pd.DataFrame(0.0, index=alvo, columns=currencies)
    for tf in ("M30", "H1", "H4", "D1"):
        lado_tf = np.sign(ctx[tf] - 50.0)
        mtf += ((lado_tf == ref_side) & (ref_side != 0)).astype(float)
    mtf = mtf.where(ref_side != 0)

    # VETO: rank H1 + VEL(6) de H4 e D1 contrárias ao lado
    rank = derived.rank_h1(s_h1, cesta_h1_a, currencies)
    vel_h4 = asof_ultima_fechada(
        s_por_tf["H4"].apply(lambda col: derived.vel(col, VETO_VEL_K)), alvo)
    vel_d1 = asof_ultima_fechada(
        s_por_tf["D1"].apply(lambda col: derived.vel(col, VETO_VEL_K)), alvo)
    # espelho do lado fraco: 9−rank no fonte (8 moedas); generalizado n+1−rank
    r_sided = rank.where(ref_side > 0, (len(currencies) + 1) - rank)
    contra = pd.DataFrame(False, index=alvo, columns=currencies)
    contra |= (ref_side > 0) & (vel_h4 < 0) & (vel_d1 < 0)
    contra |= (ref_side < 0) & (vel_h4 > 0) & (vel_d1 > 0)
    veto = ((ref_side != 0) & vel_h4.notna() & vel_d1.notna()
            & (r_sided <= 2) & contra)

    # candidata (limiares congelados; NaN em qualquer perna → não candidata)
    npar = pd.Series(n_pares).reindex(currencies)
    cand = (det["zvel"].abs() >= float(thr["zvel_abs"])) \
        & (det["zs"].abs() >= float(thr["zs_abs"])) \
        & (det["cesta"].mul(npar, axis=1) >= float(thr["cesta_min"]) - 1e-9) \
        & (mtf >= float(thr["mtf_min"])) & ~veto & (ref_side != 0)
    cand = cand.fillna(False)

    return {"ref_side": ref_side, "mtf": mtf, "veto": veto,
            "candidata": cand, "rank_h1": rank}

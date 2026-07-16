"""io_raw.py — leitura dos CSVs do export MT5 (os dois esquemas) e grade comum.

💡 Grade comum: os pares não têm exatamente as mesmas barras (um pode pular
uma meia hora sem tick). Para agregar força por moeda, alinhamos todos os
pares numa grade única por TF (a UNIÃO dos horários de abertura); par sem
barra num horário vira linha NaN — e o NaN se propaga (política do painel).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

TF_SECONDS = {"M5": 300, "M15": 900, "M30": 1800, "H1": 3600, "H4": 14400,
              "D1": 86400, "W1": 7 * 86400}
COLS = ["open", "high", "low", "close", "tick_volume"]


def carregar_barras(path: Path) -> pd.DataFrame:
    """CSV do export → DataFrame indexado pela ABERTURA (hora do servidor).

    Esquema atual (ExportBarsG8): time_epoch,time_server,open,...,spread.
    Esquema legado: time,open,...,real_volume,spread (data como texto).
    """
    df = pd.read_csv(path)
    if "time_epoch" in df.columns:
        idx = pd.to_datetime(df["time_epoch"], unit="s")
    elif "time" in df.columns:
        idx = pd.to_datetime(df["time"], format="%Y.%m.%d %H:%M:%S")
    else:
        raise ValueError(f"{path.name}: sem coluna de tempo (time_epoch/time)")
    cols = [c for c in COLS + ["real_volume", "spread"] if c in df.columns]
    out = df[cols].copy()
    out.index = pd.DatetimeIndex(idx, name="time")
    if out.index.has_duplicates or not out.index.is_monotonic_increasing:
        raise ValueError(f"{path.name}: barras duplicadas ou fora de ordem")
    return out


def grade_uniao(frames: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Reindexa todos os pares na união dos horários (linhas NaN onde falta)."""
    idx = None
    for f in frames.values():
        idx = f.index if idx is None else idx.union(f.index)
    return {p: f.reindex(idx) for p, f in frames.items()}


def horario_fechamento(idx: pd.DatetimeIndex, tf: str) -> pd.DatetimeIndex:
    """Fechamento nominal da barra (abertura + duração do TF).

    MN1 não tem duração fixa: fechamento = primeiro dia do mês seguinte."""
    if tf in ("MN", "MN1"):
        return idx + pd.offsets.MonthBegin(1)
    return idx + pd.to_timedelta(TF_SECONDS[tf], unit="s")

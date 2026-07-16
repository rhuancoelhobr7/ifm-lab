"""Teste ponta a ponta do orquestrador E2 sobre um data/raw SINTÉTICO.

💡 Monta um export falso completo (28 pares × M30/H1/H4/D1) num diretório
temporário, roda o e02_gerar_metricas de verdade e confere: estrutura dos
Parquets, corte físico do bloco selado, cache por hash e a trava de
proveniência. Nenhum dado real é tocado.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
PARES_G8 = [
    "EURUSD", "EURGBP", "EURJPY", "EURCHF", "EURCAD", "EURAUD", "EURNZD",
    "GBPUSD", "GBPJPY", "GBPCHF", "GBPCAD", "GBPAUD", "GBPNZD",
    "AUDUSD", "AUDJPY", "AUDCHF", "AUDCAD", "AUDNZD",
    "NZDUSD", "NZDJPY", "NZDCHF", "NZDCAD",
    "USDJPY", "USDCHF", "USDCAD", "CADJPY", "CADCHF", "CHFJPY",
]
MOEDAS = ["USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD"]
TF_FREQ = {"M30": "30min", "H1": "1h", "H4": "4h", "D1": "1D"}
N_BARRAS = {"M30": 480, "H1": 240, "H4": 80, "D1": 60}


def _escrever_raw(raw: Path, seed: int) -> None:
    rng = np.random.default_rng(seed)
    raw.mkdir(parents=True)
    (raw / "_manifest.csv").write_text(
        "# ExportBarsG8 v1.00 sintético\n# broker=X | conta_servidor=Sintetico-Test\n",
        encoding="utf-8")
    for par in PARES_G8:
        nivel = rng.uniform(0.6, 1.8)
        for tf, freq in TF_FREQ.items():
            n = N_BARRAS[tf]
            idx = pd.date_range("2025-08-01", periods=n, freq=freq)
            close = nivel + np.cumsum(rng.normal(0, nivel * 5e-4, n))
            hl = np.abs(rng.normal(nivel * 4e-4, nivel * 1e-4, n))
            df = pd.DataFrame({
                "time_epoch": ((idx - pd.Timestamp("1970-01-01"))
                               // pd.Timedelta(seconds=1)),
                "time_server": idx.strftime("%Y.%m.%d %H:%M"),
                "open": np.roll(close, 1),
                "high": np.maximum(close, np.roll(close, 1)) + hl,
                "low": np.minimum(close, np.roll(close, 1)) - hl,
                "close": close,
                "tick_volume": rng.integers(10, 900, n),
                "spread": 10,
            })
            df.to_csv(raw / f"{par}_{tf}.csv", index=False)


@pytest.fixture()
def pesquisa_fake(tmp_path, monkeypatch):
    """Pesquisa temporária: config real (recortado) + raw sintético."""
    cfg_real = yaml.safe_load(
        (SCRIPTS.parent / "config.yaml").read_text(encoding="utf-8"))
    cfg = {k: cfg_real[k] for k in ("indicator", "currencies", "pairs", "nan",
                                    "splits", "mt5")}
    cfg["mt5"]["conta_servidor"] = "Sintetico-Test"
    # bloco selado começa no meio do período sintético → testa o corte físico
    cfg["splits"]["teste_selado"]["inicio"] = "2025-08-06"
    (tmp_path / "config.yaml").write_text(yaml.safe_dump(cfg), encoding="utf-8")
    _escrever_raw(tmp_path / "data" / "raw", seed=17)

    sys.path.insert(0, str(SCRIPTS))
    import e02_gerar_metricas as e02
    importlib.reload(e02)
    monkeypatch.setattr(e02, "RESEARCH", tmp_path)
    monkeypatch.setattr(e02, "RAW", tmp_path / "data" / "raw")
    monkeypatch.setattr(e02, "PARQUET", tmp_path / "data" / "parquet")
    monkeypatch.setattr(e02, "SEALED", tmp_path / "data" / "sealed")
    return e02, tmp_path


def test_e02_ponta_a_ponta(pesquisa_fake, monkeypatch):
    e02, root = pesquisa_fake
    monkeypatch.setattr(sys, "argv", ["e02", "--tfs", "M30", "H1", "H4", "D1"])
    assert e02.main() == 0

    pq = sorted((root / "data" / "parquet").glob("E02_H1_*.parquet"))
    assert len(pq) == 1
    df = pd.read_parquet(pq[0])
    # estrutura: ifm por par + métricas por moeda (incl. multi-TF)
    for col in ("ifm_EURUSD", "s_USD", "zvel_EUR", "zs_JPY", "cesta_GBP",
                "mtf_USD", "veto_CHF", "candidata_AUD", "rank_h1_NZD"):
        assert col in df.columns, f"coluna ausente: {col}"
    # corte físico do selado: nada ≥ 2025-08-06 no parquet aberto
    assert (df.index < pd.Timestamp("2025-08-06")).all()
    selado = sorted((root / "data" / "sealed").glob("E02_H1_*.parquet"))
    assert len(selado) == 1
    df_s = pd.read_parquet(selado[0])
    assert (df_s.index >= pd.Timestamp("2025-08-06")).all()
    assert len(df) + len(df_s) > 0

    # sanidade numérica: com 28 pares completos, S tem valores válidos e a
    # média transversal dos S válidos fica em ~50 (soma de dir é zero-sum)
    s_cols = [f"s_{c}" for c in MOEDAS]
    linhas_ok = df[s_cols].dropna()
    assert len(linhas_ok) > 50
    assert linhas_ok.mean(axis=1).round(6).eq(50.0).all()

    # zMov/zHist gravados (âncoras M30)
    zm = sorted((root / "data" / "parquet").glob("E02_zmov_*.parquet"))
    assert len(zm) == 1
    dfz = pd.read_parquet(zm[0])
    assert "zmov_USD" in dfz.columns and "zhist_EUR" in dfz.columns

    # cache: segunda rodada não recomputa
    assert e02.main() == 0


def test_trava_de_proveniencia(pesquisa_fake, monkeypatch):
    e02, root = pesquisa_fake
    manifest = root / "data" / "raw" / "_manifest.csv"
    manifest.write_text("# conta_servidor=Outra-Conta\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["e02", "--tfs", "H1"])
    with pytest.raises(SystemExit, match="Proveniência"):
        e02.main()

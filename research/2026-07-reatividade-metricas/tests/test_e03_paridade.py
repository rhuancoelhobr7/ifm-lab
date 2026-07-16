"""Teste do comparador de paridade E3 — golden sintético fabricado do próprio
pipeline.

💡 A lógica: se o "indicador" gravasse exatamente o que o pipeline Python
calcula, a paridade teria que APROVAR (valida o alinhamento âncora↔tempo do
comparador, a parte arriscada). E se um único valor for adulterado além do
critério C1, tem que REPROVAR (valida que o teste morde). Nenhum dado real.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from test_e02_pipeline import PARES_G8, _escrever_raw

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
TFS = ["M30", "H1", "H4", "D1"]
DUR = {"M30": pd.Timedelta(minutes=30), "H1": pd.Timedelta(hours=1),
       "H4": pd.Timedelta(hours=4), "D1": pd.Timedelta(days=1)}
FMT_T = "%Y.%m.%d %H:%M"


def _num(v: float) -> str:
    return "nan" if pd.isna(v) else f"{v:.10g}"


@pytest.fixture()
def pesquisa_com_golden(tmp_path, monkeypatch):
    """Pesquisa temporária com raw sintético + golden fabricado do pipeline."""
    cfg_real = yaml.safe_load((SCRIPTS.parent / "config.yaml").read_text(encoding="utf-8"))
    cfg = {k: cfg_real[k] for k in ("indicator", "currencies", "pairs", "nan",
                                    "splits", "mt5", "criteria")}
    cfg["mt5"]["conta_servidor"] = "Sintetico-Test"
    cfg["splits"]["teste_selado"]["inicio"] = "2030-01-01"   # nada selado aqui
    (tmp_path / "config.yaml").write_text(yaml.safe_dump(cfg), encoding="utf-8")
    _escrever_raw(tmp_path / "data" / "raw", seed=23)

    sys.path.insert(0, str(SCRIPTS))
    import e02_gerar_metricas as e02
    import e03_paridade as e03
    importlib.reload(e02)
    importlib.reload(e03)
    for mod in (e02,):
        monkeypatch.setattr(mod, "RESEARCH", tmp_path)
        monkeypatch.setattr(mod, "RAW", tmp_path / "data" / "raw")
        monkeypatch.setattr(mod, "PARQUET", tmp_path / "data" / "parquet")
        monkeypatch.setattr(mod, "SEALED", tmp_path / "data" / "sealed")
    monkeypatch.setattr(e03, "RESEARCH", tmp_path)
    monkeypatch.setattr(e03, "RAW", tmp_path / "data" / "raw")
    monkeypatch.setattr(e03, "RESULTS", tmp_path / "results")

    # fabrica o golden a partir do PRÓPRIO pipeline (indicador "perfeito")
    cfg2 = e02.carrega_config()
    core = {}
    for tf in TFS:
        core[tf] = e02.metricas_core_tf(cfg2, e02.carregar_tf(cfg2, tf), tf)

    raw = tmp_path / "data" / "raw"
    ind = cfg2["indicator"]
    meta = ["chave,valor", "ferramenta,golden sintético (teste)",
            "conta_servidor,Sintetico-Test"]
    for k in ("zcore", "cci_length", "mfc_vol_length", "ema_fallback_len",
              "vel_k", "zvel_sigma_n", "zmov_days_n"):
        meta.append(f"{k},{str(ind[k]).lower()}")
    meta.append("ancoras,6")
    (raw / "golden_meta.csv").write_text("\n".join(meta), encoding="utf-8")

    ls, ld, lp = (["tf,anchor_shift,bar_time,currency,S"],
                  ["tf,anchor_shift,bar_time,currency,vel,acel,zvel,zS,cesta"],
                  ["tf,anchor_shift,bar_time,pair,ifm_light"])
    for tf in TFS:
        s = core[tf]["s"]
        for shift in range(1, 7):                       # âncoras 1..6
            t_close = s.index[-shift]
            bt = (t_close - DUR[tf]).strftime(FMT_T)    # bar_time = ABERTURA
            for cur in cfg2["currencies"]:
                ls.append(f"{tf},{shift},{bt},{cur},{_num(s.loc[t_close, cur])}")
                ld.append(f"{tf},{shift},{bt},{cur},"
                          + ",".join(_num(core[tf][m].loc[t_close, cur])
                                     for m in ("vel", "acel", "zvel", "zs", "cesta")))
            for par in PARES_G8:
                lp.append(f"{tf},{shift},{bt},{par},"
                          f"{_num(core[tf]['ifm'].loc[t_close, par])}")
    (raw / "golden_strength.csv").write_text("\n".join(ls), encoding="utf-8")
    (raw / "golden_derivadas.csv").write_text("\n".join(ld), encoding="utf-8")
    (raw / "golden_pares.csv").write_text("\n".join(lp), encoding="utf-8")

    # cross: 3 amostras de tempo, valores do próprio cross_tf/daymove
    from ifm_metrics import cross_tf, daymove
    tempos = pd.DatetimeIndex([core["H1"]["s"].index[-1],
                               core["H1"]["s"].index[-13],
                               core["H1"]["s"].index[-29]])
    s_ctx = {tf: core[tf]["s"] for tf in TFS}
    det = {k: cross_tf.asof_ultima_fechada(core["H1"][m], tempos)
           for k, m in (("zvel", "zvel"), ("zs", "zs"), ("cesta", "cesta"))}
    n_pares = {c: 7 for c in cfg2["currencies"]}
    mvc = cross_tf.mtf_veto_candidata(tempos, s_ctx, core["H1"]["cesta"], det,
                                      cfg2, cfg2["currencies"], n_pares)
    frames_m30 = e02.carregar_tf(cfg2, "M30")
    frames_d1 = e02.carregar_tf(cfg2, "D1")
    r_map = {p: daymove.r_por_par(frames_m30[p]["close"].dropna(),
                                  frames_d1[p].dropna(subset=["close"]), 14)
             for p in cfg2["pairs"]}
    zmov, zhist = daymove.zmov_zhist(
        daymove.agregar_moedas(r_map, cfg2["pairs"], cfg2["currencies"]),
        int(ind["zmov_days_n"]))
    zmov_a = cross_tf.asof_ultima_fechada(zmov, tempos)
    zhist_a = cross_tf.asof_ultima_fechada(zhist, tempos)
    s_asof = {tf: cross_tf.asof_ultima_fechada(core[tf]["s"], tempos) for tf in TFS}
    zs_asof = cross_tf.asof_ultima_fechada(core["H1"]["zs"], tempos)

    lx = ["sample_time,currency,S_M30,S_H1,S_H4,S_D1,zS_H1,mtf,veto,rank_h1,zmov,zhist,candidata_h1"]
    for tA in tempos:
        for cur in cfg2["currencies"]:
            mtf = mvc["mtf"].loc[tA, cur]
            lx.append(",".join([
                tA.strftime(FMT_T), cur,
                _num(s_asof["M30"].loc[tA, cur]), _num(s_asof["H1"].loc[tA, cur]),
                _num(s_asof["H4"].loc[tA, cur]), _num(s_asof["D1"].loc[tA, cur]),
                _num(zs_asof.loc[tA, cur]),
                str(-1 if pd.isna(mtf) else int(mtf)),
                str(int(mvc["veto"].loc[tA, cur])),
                str(int(mvc["rank_h1"].loc[tA, cur])),
                _num(zmov_a.loc[tA, cur]), _num(zhist_a.loc[tA, cur]),
                str(int(mvc["candidata"].loc[tA, cur])),
            ]))
    (raw / "golden_cross.csv").write_text("\n".join(lx), encoding="utf-8")
    return e03, tmp_path


def test_paridade_aprova_golden_identico(pesquisa_com_golden):
    e03, root = pesquisa_com_golden
    assert e03.main() == 0
    rel = (root / "results" / "E03_paridade.md").read_text(encoding="utf-8")
    assert "✔ APROVADO" in rel
    for secao in ("## O que perguntamos", "## Como testamos", "## Resultados",
                  "## Confronto com os critérios", "## O que isso muda", "## Limitações"):
        assert secao in rel                    # template didático §1.2


def test_paridade_reprova_valor_adulterado(pesquisa_com_golden):
    e03, root = pesquisa_com_golden
    gs = root / "data" / "raw" / "golden_strength.csv"
    linhas = gs.read_text(encoding="utf-8").splitlines()
    # adultera o S da primeira linha de dados além do C1 (|ΔS| máx 0.5)
    partes = linhas[1].split(",")
    if partes[-1] == "nan":                    # acha uma linha com valor
        for i, l in enumerate(linhas[1:], 1):
            if not l.endswith("nan"):
                partes, idx = l.split(","), i
                break
    else:
        idx = 1
    partes[-1] = str(float(partes[-1]) + 3.0)
    linhas[idx] = ",".join(partes)
    gs.write_text("\n".join(linhas), encoding="utf-8")
    assert e03.main() == 1
    rel = (root / "results" / "E03_paridade.md").read_text(encoding="utf-8")
    assert "✘ REPROVADO" in rel

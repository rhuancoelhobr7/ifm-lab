#!/usr/bin/env python3
"""e03_paridade.py — E3: paridade Python × replay do indicador (critério C1).

💡 O que este script faz, em linguagem simples: pega os "valores-verdade"
gravados pelo ExportGoldenIFM (a cópia literal do indicador rodando no MT5),
recalcula os MESMOS pontos com o pipeline Python da pesquisa e mede a
diferença ponto a ponto. O relatório sai no formato checklist do critério C1
(congelado no E0): força S precisa bater com |ΔS| ≤ 0.1 em ≥99% dos pontos e
máximo ≤ 0.5; derivadas com erro relativo ≤ 1%; e os NaN precisam cair nos
MESMOS lugares (dado ausente de um lado é dado ausente do outro). Só com o C1
fechado (portão P1 carimbado) as conclusões das etapas seguintes valem.

Entrada:  data/raw/golden_{meta,strength,derivadas,pares,cross}.csv
          (gerados por tools/export_golden/ExportGoldenIFM.mq5 no MT5)
Saída:    results/E03_paridade.md
Código de saída: 0 = C1 fechado; 1 = golden ausente/incompatível ou C1 falhou.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ifm_metrics import cross_tf, daymove, io_raw  # noqa: E402
import e02_gerar_metricas as e02  # noqa: E402

RESEARCH = Path(__file__).resolve().parent.parent
RAW = RESEARCH / "data" / "raw"
RESULTS = RESEARCH / "results"

TFS = ["M30", "H1", "H4", "D1"]
DUR = {"M30": pd.Timedelta(minutes=30), "H1": pd.Timedelta(hours=1),
       "H4": pd.Timedelta(hours=4), "D1": pd.Timedelta(days=1)}
FMT_T = "%Y.%m.%d %H:%M"

# chaves do golden_meta que precisam bater com o config (paridade dos defaults)
META_VS_CONFIG = {"zcore": "zcore", "cci_length": "cci_length",
                  "mfc_vol_length": "mfc_vol_length",
                  "ema_fallback_len": "ema_fallback_len", "vel_k": "vel_k",
                  "zvel_sigma_n": "zvel_sigma_n", "zmov_days_n": "zmov_days_n"}


def carrega_golden() -> dict[str, pd.DataFrame] | None:
    nomes = ["meta", "strength", "derivadas", "pares", "cross"]
    faltam = [n for n in nomes if not (RAW / f"golden_{n}.csv").exists()]
    if faltam:
        print("✘ golden ausente em data/raw/: " + ", ".join(f"golden_{n}.csv" for n in faltam))
        print("  Rodar tools/export_golden/ExportGoldenIFM.mq5 no MT5 (conta "
              "MetaQuotes-Demo) e copiar os 5 CSVs — ver o README de lá.")
        return None
    out = {}
    for n in nomes:
        out[n] = pd.read_csv(RAW / f"golden_{n}.csv", na_values=["nan"])
    return out


def valida_meta(meta: pd.DataFrame, cfg: dict) -> list[str]:
    kv = dict(zip(meta["chave"], meta["valor"].astype(str)))
    erros = []
    esperado = cfg["mt5"].get("conta_servidor", "")
    if esperado and esperado not in kv.get("conta_servidor", ""):
        erros.append(f"conta_servidor do golden = '{kv.get('conta_servidor')}' "
                     f"≠ '{esperado}' do config")
    for k_meta, k_cfg in META_VS_CONFIG.items():
        if k_meta not in kv:
            erros.append(f"golden_meta sem a chave '{k_meta}'")
            continue
        v_cfg = str(cfg["indicator"][k_cfg]).lower()
        if kv[k_meta].strip().lower() != v_cfg:
            erros.append(f"parâmetro '{k_meta}': golden={kv[k_meta]} ≠ config={v_cfg}")
    return erros


def confronta(gold: pd.Series, py: pd.Series, modo: str) -> dict:
    """Estatísticas de confronto de duas séries alinhadas.

    modo: 'abs' (ΔS absoluto — escala 0–100), 'rel' (erro relativo — C1 1%),
          'exato' (colunas discretas: mtf, veto, rank, candidata, cesta).
    """
    g, p = gold.to_numpy(dtype=float), py.to_numpy(dtype=float)
    nan_g, nan_p = np.isnan(g), np.isnan(p)
    nan_iguais = int((nan_g == nan_p).sum())
    ambos = ~nan_g & ~nan_p
    r = {"n": len(g), "n_nan_gold": int(nan_g.sum()), "n_nan_py": int(nan_p.sum()),
         "nan_batem": nan_iguais == len(g), "n_comparaveis": int(ambos.sum()),
         "p99": np.nan, "maximo": np.nan, "pct_dentro": np.nan, "exatos_pct": np.nan}
    if not ambos.any():
        return r
    d = np.abs(g[ambos] - p[ambos])
    if modo == "rel":
        den = np.maximum(np.abs(g[ambos]), 1e-9)
        d = d / den
    r["p99"] = float(np.percentile(d, 99))
    r["maximo"] = float(d.max())
    if modo == "exato":
        r["exatos_pct"] = float((d <= 1e-9).mean() * 100)
    return r


def maiores_desvios(df: pd.DataFrame, col_g: str, col_p: str, chaves: list[str],
                    n: int = 8) -> pd.DataFrame:
    d = (df[col_g] - df[col_p]).abs()
    top = df.assign(_desvio=d).nlargest(n, "_desvio")
    return top[chaves + [col_g, col_p, "_desvio"]].rename(columns={"_desvio": "|Δ|"})


def main() -> int:
    cfg = e02.carrega_config()
    golden = carrega_golden()
    if golden is None:
        return 1
    erros_meta = valida_meta(golden["meta"], cfg)
    if erros_meta:
        print("✘ golden incompatível com o config (paridade seria contra a versão errada):")
        for e in erros_meta:
            print(f"  - {e}")
        return 1

    e02.checar_proveniencia(cfg)
    print("Computando a cadeia Python (M30/H1/H4/D1)…")
    frames, core = {}, {}
    for tf in TFS:
        frames[tf] = e02.carregar_tf(cfg, tf)
        core[tf] = e02.metricas_core_tf(cfg, frames[tf], tf)   # índice = FECHAMENTO

    def lookup(tf: str, metrica: str, bar_time: pd.Series, coluna: pd.Series) -> np.ndarray:
        """Valor Python da métrica no fechamento = bar_time (abertura) + duração."""
        f = core[tf][metrica]
        alvo = pd.to_datetime(bar_time, format=FMT_T) + DUR[tf]
        pos = f.index.get_indexer(alvo)
        cols = f.columns.get_indexer(coluna)
        vals = np.full(len(alvo), np.nan)
        ok = (pos >= 0) & (cols >= 0)
        vals[ok] = f.to_numpy()[pos[ok], cols[ok]]
        return vals

    blocos: list[tuple[str, str, dict, pd.DataFrame | None]] = []

    def col_py(df: pd.DataFrame, metrica: str, col_id: str) -> pd.Series:
        """Valores Python alinhados linha a linha (atribuição por índice do grupo)."""
        out = pd.Series(np.nan, index=df.index)
        for tf, g in df.groupby("tf", sort=False):
            out.loc[g.index] = lookup(tf, metrica, g["bar_time"], g[col_id])
        return out

    # --- A) IFM Light por par -------------------------------------------------
    gp = golden["pares"].copy()
    gp["py"] = col_py(gp, "ifm", "pair")
    blocos.append(("IFM Light por par (golden_pares)", "abs",
                   confronta(gp["ifm_light"], gp["py"], "abs"),
                   maiores_desvios(gp, "ifm_light", "py", ["tf", "bar_time", "pair"])))

    # --- B) Força S -----------------------------------------------------------
    gs = golden["strength"].copy()
    gs["py"] = col_py(gs, "s", "currency")
    blocos.append(("Força S por moeda (golden_strength)", "abs",
                   confronta(gs["S"], gs["py"], "abs"),
                   maiores_desvios(gs, "S", "py", ["tf", "bar_time", "currency"])))

    # --- C) Derivadas ---------------------------------------------------------
    gd = golden["derivadas"].copy()
    for met, modo in (("vel", "rel"), ("acel", "rel"), ("zvel", "rel"),
                      ("zS", "rel"), ("cesta", "exato")):
        met_py = {"zS": "zs"}.get(met, met)
        gd[f"py_{met}"] = col_py(gd, met_py, "currency")
        blocos.append((f"Derivada {met} (golden_derivadas)", modo,
                       confronta(gd[met], gd[f"py_{met}"], modo),
                       maiores_desvios(gd, met, f"py_{met}", ["tf", "bar_time", "currency"])))

    # --- D) Cadeia cruzada (âncora por tempo) ---------------------------------
    gx = golden["cross"].copy()
    tempos = pd.DatetimeIndex(pd.to_datetime(gx["sample_time"].unique(), format=FMT_T))
    moedas = cfg["currencies"]
    s_ctx = {tf: core[tf]["s"] for tf in TFS}
    det = {k: cross_tf.asof_ultima_fechada(core["H1"][m], tempos)
           for k, m in (("zvel", "zvel"), ("zs", "zs"), ("cesta", "cesta"))}
    n_pares = {c: sum(1 for p in cfg["pairs"] if c in (p[:3], p[3:6])) for c in moedas}
    mvc = cross_tf.mtf_veto_candidata(tempos, s_ctx, core["H1"]["cesta"], det,
                                      cfg, moedas, n_pares)
    print("zMov/zHist (âncoras M30)…")
    if "D1" not in frames:
        frames["D1"] = e02.carregar_tf(cfg, "D1")
    atr_len = int(cfg["indicator"]["atr_length"])
    r_map = {p: daymove.r_por_par(frames["M30"][p]["close"].dropna(),
                                  frames["D1"][p].dropna(subset=["close"]), atr_len)
             for p in cfg["pairs"]}
    r_moedas = daymove.agregar_moedas(r_map, cfg["pairs"], cfg["currencies"])
    zmov, zhist = daymove.zmov_zhist(r_moedas, int(cfg["indicator"]["zmov_days_n"]))

    tA = pd.to_datetime(gx["sample_time"], format=FMT_T)
    idx = pd.MultiIndex.from_arrays([tA, gx["currency"]])
    def achata(frame: pd.DataFrame, asof: bool = False) -> pd.Series:
        f = cross_tf.asof_ultima_fechada(frame, tempos) if asof else frame
        return pd.Series(f.stack().reindex(idx).to_numpy(), index=gx.index)

    comparacoes_cross = [
        ("S_M30", achata(cross_tf.asof_ultima_fechada(core["M30"]["s"], tempos)), "abs"),
        ("S_H1", achata(cross_tf.asof_ultima_fechada(core["H1"]["s"], tempos)), "abs"),
        ("S_H4", achata(cross_tf.asof_ultima_fechada(core["H4"]["s"], tempos)), "abs"),
        ("S_D1", achata(cross_tf.asof_ultima_fechada(core["D1"]["s"], tempos)), "abs"),
        ("zS_H1", achata(cross_tf.asof_ultima_fechada(core["H1"]["zs"], tempos)), "rel"),
        ("mtf", achata(mvc["mtf"]), "exato"),
        ("veto", achata(mvc["veto"].astype(float)), "exato"),
        ("rank_h1", achata(mvc["rank_h1"].astype(float)), "exato"),
        ("zmov", achata(zmov, asof=True), "rel"),
        ("zhist", achata(zhist, asof=True), "rel"),
        ("candidata_h1", achata(mvc["candidata"].astype(float)), "exato"),
    ]
    for col, py_vals, modo in comparacoes_cross:
        g = gx[col].astype(float)
        if col == "mtf":
            g = g.replace(-1, np.nan)          # -1 do painel = indefinido = NaN
        gx[f"py_{col}"] = py_vals.to_numpy()
        blocos.append((f"Cross {col} (golden_cross)", modo,
                       confronta(g, gx[f"py_{col}"], modo),
                       maiores_desvios(gx.assign(**{col: g}), col, f"py_{col}",
                                       ["sample_time", "currency"])))

    # --- veredito C1 ----------------------------------------------------------
    c1 = cfg["criteria"]["C1_paridade"]
    checks: list[tuple[str, bool, str]] = []
    for nome, modo, st, _ in blocos:
        if st["n_comparaveis"] == 0:
            # nada a comparar: só passa se o NaN cair nos MESMOS pontos dos
            # dois lados (C1 nan_identicos) — ex.: zHist sem 10 dias de história
            checks.append((nome, st["nan_batem"],
                           "0 pontos comparáveis; NaN "
                           + ("idênticos nos dois lados" if st["nan_batem"] else "DIFEREM")))
            continue
        if modo == "abs":
            ok = (st["p99"] <= c1["ds_abs_p99"] and st["maximo"] <= c1["ds_abs_max"]
                  and st["nan_batem"])
            detalhe = (f"p99={st['p99']:.4g} (≤{c1['ds_abs_p99']}), "
                       f"máx={st['maximo']:.4g} (≤{c1['ds_abs_max']}), "
                       f"NaN {'idênticos' if st['nan_batem'] else 'DIFEREM'}")
        elif modo == "rel":
            ok = st["p99"] <= c1["derivadas_erro_rel"] and st["nan_batem"]
            detalhe = (f"erro rel p99={st['p99']:.4g} (≤{c1['derivadas_erro_rel']}), "
                       f"máx={st['maximo']:.4g}, "
                       f"NaN {'idênticos' if st['nan_batem'] else 'DIFEREM'}")
        else:
            ok = st["exatos_pct"] == 100.0 and st["nan_batem"]
            detalhe = (f"exatos={st['exatos_pct']:.2f}% (exige 100%), "
                       f"NaN {'idênticos' if st['nan_batem'] else 'DIFEREM'}")
        checks.append((nome, ok, detalhe))
    aprovado = all(ok for _, ok, _ in checks)

    # --- relatório (template §1.2) ---------------------------------------------
    def md_conf():
        linhas = ["| bloco | resultado | detalhe |", "|---|---|---|"]
        for nome, ok, detalhe in checks:
            linhas.append(f"| {nome} | {'✔' if ok else '✘'} | {detalhe} |")
        return "\n".join(linhas)

    def md_desvios():
        partes = []
        for nome, _, st, top in blocos:
            if top is None or not len(top):
                continue
            t = top.copy()
            for c in t.columns:
                if t[c].dtype == float:
                    t[c] = t[c].map(lambda v: f"{v:.6g}")
            tabela = "| " + " | ".join(t.columns) + " |\n|" + "---|" * len(t.columns)
            for _, row in t.iterrows():
                tabela += "\n| " + " | ".join(str(v) for v in row) + " |"
            partes.append(f"### {nome}\n\n{tabela}\n\n**Leitura:** os {len(t)} maiores "
                          f"desvios deste bloco ({st['n_comparaveis']} pontos comparados; "
                          f"NaN golden={st['n_nan_gold']}, Python={st['n_nan_py']}). "
                          f"Desvio grande e isolado sugere borda (buraco de barra, "
                          f"início de série); desvio sistemático sugere erro de fórmula.")
        return "\n\n".join(partes)

    md = f"""# E03 — Verificação de paridade (Python × replay do indicador)

## O que perguntamos

A reimplementação Python do painel (E2) calcula os MESMOS números que o
indicador IFM v1.0 no MT5? (💡 paridade: duas calculadoras, mesma conta —
sem isso, qualquer achado da pesquisa poderia ser artefato de tradução.)

## Como testamos

O `ExportGoldenIFM.mq5` (cópia literal do fonte v1.0) gravou, na conta
MetaQuotes-Demo: IFM Light por par, S, vel/acel/zvel/zS/cesta em
{golden['meta'].set_index('chave')['valor'].get('ancoras', '80')} âncoras × 4 TFs, e a cadeia cruzada
(mtf/VETO/rank/candidata/zMov/zHist) em amostras de tempo com âncora
"última barra fechada". O Python recalculou os mesmos pontos a partir de
data/raw/ e comparou ponto a ponto. Critério **C1** congelado: |ΔS| ≤ {c1['ds_abs_p99']}
em ≥99% dos pontos E |ΔS| máx ≤ {c1['ds_abs_max']}; derivadas com erro relativo ≤
{c1['derivadas_erro_rel']:.0%}; colunas discretas exatas; **NaN nos mesmos pontos**.

## Resultados

{md_conf()}

**Leitura:** cada linha confronta um bloco de valores do indicador com o Python.
{'Todos os blocos dentro do C1 — as duas calculadoras fazem a mesma conta.' if aprovado
 else 'Há blocos fora do C1 — investigar os maiores desvios abaixo antes de qualquer conclusão.'}

## Maiores desvios por bloco

{md_desvios()}

## Confronto com os critérios

**C1** exigia: ΔS p99 ≤ {c1['ds_abs_p99']}, ΔS máx ≤ {c1['ds_abs_max']}, derivadas ≤ {c1['derivadas_erro_rel']:.0%},
NaN idênticos → **{'✔ APROVADO' if aprovado else '✘ REPROVADO'}** (detalhe por bloco acima).
{'O portão P1 está pronto para o carimbo (registrar no PROGRESS.md quem aprovou).' if aprovado
 else 'Reprovou → depurar a causa (vai para este relatório) e repetir. Nada do que vem depois vale sem o P1.'}

## O que isso muda

{'O pipeline Python está validado como réplica do indicador: E4 (gabarito + banco-mãe) pode começar.' if aprovado
 else 'O E4 NÃO começa até a paridade fechar (PLANO §5/E3).'}

## Limitações

- A paridade cobre os TFs do painel (M30–D1) e as âncoras amostradas — W1/MN não
  existem no painel (sem paridade possível; config `timeframes.so_pesquisa`).
- O golden vem de uma cópia literal do fonte, não do indicador desenhando na tela
  (limitação documentada no README da ferramenta; mitigada por ser cópia 1:1).
- Divergências conhecidas e documentadas: alinhamento de dias do zMov/zHist
  (PROGRESS 2026-07-15, descoberta 3) pode gerar desvio pontual em dias em que
  algum par pula uma barra D1.
"""
    RESULTS.mkdir(exist_ok=True)
    out = RESULTS / "E03_paridade.md"
    out.write_text(md, encoding="utf-8")
    print(f"Relatório: {out}")
    print("✔ C1 fechado — P1 pronto para carimbo." if aprovado
          else "✘ C1 reprovado — ver relatório.")
    return 0 if aprovado else 1


if __name__ == "__main__":
    sys.exit(main())

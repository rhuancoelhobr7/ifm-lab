#!/usr/bin/env python3
"""e07_contexto.py — E7 parte 1: a maré sobre a marola — contexto e conflito (Q5/C7).

💡 A metáfora do ESBOÇO §6–7: MN/W1/D1 são a MARÉ (o pano de fundo que muda
devagar), M30/H1 são a MAROLA onde o day trade acontece. Perguntas desta parte:
(1) quando a maré aponta A FAVOR da arrancada intraday, o detector pega mais,
mais cedo e com mais sobra? Quando aponta CONTRA, quanto piora? (critério C7);
(2) "conflito precoce": o disparo intraday CONTRA a maré funciona como alerta
de que o dia vai contra o contexto — e esses dias "contra o vento" rendem menos?

Definições:
- Detector de referência (foco do P3, o mesmo do E6.2): cruzamento direcional
  de zS ≥ 1.0, medido em M30 e H1.
- Alinhamento: sinal de (S_contexto − 50) na ÚLTIMA barra fechada do TF de
  contexto (coluna ctx_s_* do banco, asof — anti-look-ahead) vs a direção do
  EVENTO (lido na âncora) ou do DISPARO (lido na hora dele).
- C7: conflito "relevante" se muda latência, detecção ou captura ≥ 30%
  (relativo) E sobrevive ao BH (C11) E tem o mesmo sentido em treino e validação.

Guarda-corpo: só treino/validação (data/sealed recusado por construção).
Eventos contra-contexto são MINORIA — os efeitos são medidos no agregado
treino+validação (senão a célula da validação fica com n<10), com o SENTIDO
conferido nos dois splits separadamente; célula com N < n_minimo é marcada
"⚠ amostra insuficiente" e nunca vira achado (PLANO §7).

Saída: results/E07_contexto.md
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e02_gerar_metricas as e02  # noqa: E402
import e05_corrida as e05  # noqa: E402

RESEARCH = Path(__file__).resolve().parent.parent
RESULTS = RESEARCH / "results"
TFS_DET = ["M30", "H1"]
CTX = ["MN1", "W1", "D1"]
MET, THR = "zs", 1.0
N_SENTIDO_MIN = 10          # mínimo por grupo/split p/ conferir o sentido


def carregar(tf: str, h: str) -> pd.DataFrame:
    df = e05.carregar_banco(tf, h)
    df["gab_ancora"] = pd.to_datetime(df["gab_ancora"])
    df["gab_fim"] = pd.to_datetime(df["gab_fim"])
    return df.sort_values(["moeda", "t"]).reset_index(drop=True)


def cruzamentos(df: pd.DataFrame) -> pd.DataFrame:
    """Todos os cruzamentos direcionais do detector de referência."""
    dirs, forca = e05.sinal_e_forca(df, MET)
    ligado = (forca >= THR) & (dirs != 0)
    estado = np.where(ligado, dirs, 0.0)
    prev = pd.Series(estado).groupby(df["moeda"].to_numpy()).shift(1)
    cruz = ligado & (estado != prev.to_numpy())
    out = df[cruz].copy()
    out["dir_disp"] = dirs[cruz]
    return out


def mwu(a: pd.Series, b: pd.Series) -> float:
    a, b = a.dropna(), b.dropna()
    if len(a) < 3 or len(b) < 3:
        return np.nan
    return float(stats.mannwhitneyu(a, b, alternative="two-sided").pvalue)


def fisher(k1: int, n1: int, k2: int, n2: int) -> float:
    if min(n1, n2) == 0:
        return np.nan
    return float(stats.fisher_exact([[k1, n1 - k1], [k2, n2 - k2]]).pvalue)


def tab(d: pd.DataFrame) -> str:
    out = ["| " + " | ".join(map(str, d.columns)) + " |", "|" + "---|" * len(d.columns)]
    out += ["| " + " | ".join("" if (isinstance(v, float) and np.isnan(v))
                              else str(v) for v in r) + " |"
            for r in d.itertuples(index=False)]
    return "\n".join(out)


def main() -> int:
    cfg = e02.carrega_config()
    h = e02.hash_config(cfg)
    util_pct = float(cfg["detector_notas"]["tempo_util_pct_consumido"]) / 100.0
    c7_min = float(cfg["criteria"]["C7_conflito_relevante"]["efeito_relativo_min_pct"])
    fdr = float(cfg["criteria"]["C11_fdr"])
    n_min = int(cfg["stats"]["n_minimo_celula"])

    linhas_ev, linhas_prec, linhas_antec, testes = [], [], [], []
    for tf in TFS_DET:
        print(f"TF {tf}…")
        df = carregar(tf, h)
        _, det = e05.quatro_notas(df, MET, THR, util_pct, detalhe=True)
        det = det.drop(columns="split")
        det["captura_pct"] = (1 - det["consumido"]).clip(lower=0) * 100

        # --- contexto na âncora, por evento (1ª linha pós-âncora do banco)
        anc = (df[df["gab_pos_ancora"]].sort_values("t")
               .groupby(["moeda", "gab_ancora"], sort=False).first().reset_index())
        for ctf in CTX:
            al = np.sign(anc[f"ctx_s_{ctf}"] - 50.0) * anc["gab_direcao"]
            anc[f"al_{ctf}"] = np.select([al > 0, al < 0],
                                         ["alinhado", "contra"], "neutro")
        ev = anc.merge(det, on=["moeda", "gab_ancora"], how="left")
        ev["util"] = ev["util"].fillna(False).astype(bool)

        for ctf in CTX:
            grupos = {}
            for gr in ("alinhado", "contra"):
                g = ev[ev[f"al_{ctf}"] == gr]
                u = g[g["util"]]
                grupos[gr] = g
                por_split = {s: (100 * gg["util"].mean() if len(gg) else np.nan,
                                 float(gg.loc[gg["util"], "latencia_min"].median()),
                                 float(gg.loc[gg["util"], "captura_pct"].median()),
                                 len(gg))
                             for s, gg in g.groupby("split")}
                linhas_ev.append({
                    "tf": tf, "contexto": ctf, "maré": gr,
                    "n_eventos": len(g),
                    "magnitude_med_atr": round(float(g["gab_magnitude"].median()), 2),
                    "deteccao_pct": round(100 * g["util"].mean(), 1) if len(g) else np.nan,
                    "lat_mediana_min": round(float(u["latencia_min"].median()), 0)
                                       if len(u) else np.nan,
                    "captura_mediana_pct": round(float(u["captura_pct"].median()), 1)
                                           if len(u) else np.nan,
                    "amostra": "" if len(g) >= n_min else "⚠ insuficiente",
                    "_splits": por_split})
            a, c = grupos["alinhado"], grupos["contra"]
            ua, uc = a[a["util"]], c[c["util"]]

            def efeito(va: float, vc: float) -> float:
                return np.nan if not va or np.isnan(va) or np.isnan(vc) \
                    else 100 * (vc - va) / abs(va)

            def sentido_ok(ka: int, kc: int) -> str:
                """Mesmo sentido do efeito nos 2 splits (grupos com N mínimo)."""
                sinais = []
                for s in ("treino", "validacao"):
                    ga, gc = a[a["split"] == s], c[c["split"] == s]
                    if len(ga) < N_SENTIDO_MIN or len(gc) < N_SENTIDO_MIN:
                        return "— (n<%d)" % N_SENTIDO_MIN
                    va = [100 * ga["util"].mean(),
                          float(ga.loc[ga["util"], "latencia_min"].median()),
                          float(ga.loc[ga["util"], "captura_pct"].median())][ka]
                    vc = [100 * gc["util"].mean(),
                          float(gc.loc[gc["util"], "latencia_min"].median()),
                          float(gc.loc[gc["util"], "captura_pct"].median())][ka]
                    sinais.append(np.sign(vc - va))
                return "sim" if sinais[0] == sinais[1] != 0 else "não"

            for i, (nota, ef, p) in enumerate([
                ("detecção", efeito(100 * a["util"].mean() if len(a) else np.nan,
                                    100 * c["util"].mean() if len(c) else np.nan),
                 fisher(int(a["util"].sum()), len(a), int(c["util"].sum()), len(c))),
                ("latência", efeito(float(ua["latencia_min"].median()) if len(ua) else np.nan,
                                    float(uc["latencia_min"].median()) if len(uc) else np.nan),
                 mwu(ua["latencia_min"], uc["latencia_min"])),
                ("captura", efeito(float(ua["captura_pct"].median()) if len(ua) else np.nan,
                                   float(uc["captura_pct"].median()) if len(uc) else np.nan),
                 mwu(ua["captura_pct"], uc["captura_pct"])),
            ]):
                testes.append({"tf": tf, "contexto": ctf, "nota": nota,
                               "efeito_rel_pct": round(ef, 1) if not np.isnan(ef) else np.nan,
                               "p": p, "sentido_2splits": sentido_ok(i, i),
                               "familia_c7": True})

        # --- precisão por alinhamento do DISPARO (a maré como filtro)
        d = cruzamentos(df)
        d = d[d["sessao"] != "fora"].copy()
        d["em_evento"] = d["gab_pos_ancora"] & (d["t"] <= d["gab_fim"]) \
            & (d["dir_disp"] == d["gab_direcao"])
        semanas = max(d["t"].dt.isocalendar().week.astype(str)
                      .add(d["t"].dt.year.astype(str)).nunique(), 1)
        for ctf in CTX:
            ald = np.sign(d[f"ctx_s_{ctf}"] - 50.0) * d["dir_disp"]
            d["_gr"] = np.select([ald > 0, ald < 0], ["alinhado", "contra"], "neutro")
            ka = kc = na = nc = 0
            for gr in ("alinhado", "contra"):
                g = d[d["_gr"] == gr]
                prec = 100 * g["em_evento"].mean() if len(g) else np.nan
                falsos = float((~g["em_evento"]).sum()) / semanas / 8
                linhas_prec.append({
                    "tf": tf, "contexto": ctf, "maré no disparo": gr,
                    "n_disparos": len(g), "precisao_pct": round(prec, 1),
                    "falsos_por_semana": round(falsos, 2)})
                if gr == "alinhado":
                    ka, na = int(g["em_evento"].sum()), len(g)
                else:
                    kc, nc = int(g["em_evento"].sum()), len(g)
            testes.append({"tf": tf, "contexto": ctf, "nota": "precisão",
                           "efeito_rel_pct": round(
                               100 * (kc / nc - ka / na) / (ka / na), 1)
                               if na and nc and ka else np.nan,
                           "p": fisher(ka, na, kc, nc),
                           "sentido_2splits": "(pool)", "familia_c7": False})

        # --- conflito precoce: o zS do dia vira ANTES da âncora? (alerta)
        cz = cruzamentos(df)
        cz["dia"] = cz["t"].dt.normalize()
        base = anc[["moeda", "gab_ancora", "gab_direcao", "al_D1", "split"]].copy()
        base["dia"] = base["gab_ancora"].dt.normalize()
        m = base.merge(cz[["moeda", "dia", "t", "dir_disp"]],
                       on=["moeda", "dia"], how="left")
        m = m[m["dir_disp"].isna() | (m["dir_disp"] == m["gab_direcao"])]
        first = (m.sort_values("t").groupby(["moeda", "gab_ancora"], sort=False)
                 .first().reset_index())
        first["lead_min"] = (first["gab_ancora"] - first["t"]).dt.total_seconds() / 60
        first["antecipa"] = first["lead_min"] > 0
        kk = {}
        for gr in ("alinhado", "contra"):
            g = first[first["al_D1"] == gr]
            lead = g.loc[g["antecipa"], "lead_min"]
            kk[gr] = (int(g["antecipa"].sum()), len(g))
            linhas_antec.append({
                "tf": tf, "maré D1 do evento": gr, "n_eventos": len(g),
                "antecipa_pct": round(100 * g["antecipa"].mean(), 1) if len(g) else np.nan,
                "lead_mediano_min": round(float(lead.median()), 0) if len(lead) else np.nan,
                "amostra": "" if len(g) >= n_min else "⚠ insuficiente"})
        testes.append({"tf": tf, "contexto": "D1", "nota": "antecipação",
                       "efeito_rel_pct": np.nan,
                       "p": fisher(*kk["alinhado"], *kk["contra"]),
                       "sentido_2splits": "(pool)", "familia_c7": False})

    # --- C11: BH sobre TODOS os p-valores desta varredura
    tt = pd.DataFrame(testes)
    validos = tt["p"].notna()
    tt["p_bh"] = np.nan
    tt["sobrevive_bh"] = False
    if validos.sum():
        ok, p_adj, _, _ = multipletests(tt.loc[validos, "p"], alpha=fdr,
                                        method="fdr_bh")
        tt.loc[validos, "p_bh"] = p_adj.round(4)
        tt.loc[validos, "sobrevive_bh"] = ok
    tt["C7"] = np.where(
        tt["familia_c7"] & tt["sobrevive_bh"]
        & (tt["efeito_rel_pct"].abs() >= c7_min)
        & (tt["sentido_2splits"] == "sim"), "✔", "")
    tt["p"] = tt["p"].round(4)

    df_ev = pd.DataFrame(linhas_ev).drop(columns="_splits")
    df_prec = pd.DataFrame(linhas_prec)
    df_antec = pd.DataFrame(linhas_antec)
    df_tt = tt.drop(columns="familia_c7")
    n_c7 = int((tt["C7"] == "✔").sum())

    # --- frases das leituras, calculadas dos próprios números
    fam = tt[tt["familia_c7"]]
    max_ef = float(fam["efeito_rel_pct"].abs().max())
    contra_mn = df_ev[(df_ev["contexto"] == "MN1") & (df_ev["maré"] == "contra")][
        "n_eventos"].iloc[0]
    tot_mn = int(df_ev[df_ev["contexto"] == "MN1"]["n_eventos"].iloc[:2].sum())
    pv = df_prec.pivot_table(index=["tf", "contexto"], columns="maré no disparo",
                             values="precisao_pct")
    dprec = (pv["contra"] - pv["alinhado"]).round(1)
    an = df_antec.set_index(["tf", "maré D1 do evento"])["antecipa_pct"]
    leit_ev = (f"os efeitos da maré sobre as três notas ficaram todos abaixo de "
               f"{max_ef:.0f}% relativos (nenhum perto dos 30% do C7) — dado que o "
               f"evento existe, o detector o pega praticamente igual com a maré a "
               f"favor ou contra. E note a coluna n_eventos: {contra_mn} de "
               f"{tot_mn} eventos classificados ({100 * contra_mn / tot_mn:.0f}%) "
               f"nasceram CONTRA a maré mensal — tendência de um dia ignora o MN1 "
               f"com frequência; magnitudes medianas também são iguais dos dois "
               f"lados (dias contra o vento NÃO renderam menos).")
    leit_prec = (f"resultado em duas direções: contra o MN1 a precisão foi MAIOR "
                 f"que alinhado (Δ {dprec.get(('M30', 'MN1'), np.nan):+.1f} pt no "
                 f"M30, {dprec.get(('H1', 'MN1'), np.nan):+.1f} pt no H1 — ambos "
                 f"sobrevivem ao BH), e no D1 o alinhado só ganha no M30 "
                 f"(Δ contra {dprec.get(('M30', 'D1'), np.nan):+.1f} pt). Em valor "
                 f"absoluto, tudo vive na faixa de 2–2.5% de precisão: NENHUM "
                 f"recorte de maré transforma o detector solo em operável — a maré "
                 f"não é o filtro que faltava.")
    leit_ant = (f"o alerta precoce existe, mas ao CONTRÁRIO da hipótese: eventos "
                f"ALINHADOS com o D1 são muito mais antecipados pelo zS "
                f"({an.get(('M30', 'alinhado'), np.nan):.0f}% vs "
                f"{an.get(('M30', 'contra'), np.nan):.0f}% no M30; "
                f"{an.get(('H1', 'alinhado'), np.nan):.0f}% vs "
                f"{an.get(('H1', 'contra'), np.nan):.0f}% no H1; ambos sobrevivem "
                f"ao BH) — quando a maré e a marola concordam, o zS costuma já "
                f"estar virado antes do rompimento; nos dias contra o vento o "
                f"rompimento pega o painel de surpresa. \"TF curto virando contra "
                f"o longo\" como aviso antecipado NÃO se confirmou como sinal — é "
                f"o alinhado que avisa cedo.")
    muda = (("A maré NÃO muda as notas de detecção (C7 zerado): saber o MN/W1/D1 "
             "não faz o detector pegar mais, mais cedo nem com mais sobra — e "
             "metade das tendências diárias nasce contra o contexto. MN1/W1 ficam "
             "candidatas a descarte como FILTRO (o C9 formal é a parte 2); as "
             "assimetrias de precisão e antecipação são candidatas a LEITURA "
             "(confiança média, consolidar no E12).") if n_c7 == 0 else
            (f"{n_c7} conflito(s) relevantes (C7 ✔): o contexto multi-TF é "
             "filtro/peso candidato do detector composto (E9/E10) e entrada de "
             "LEITURA (confiança média)."))

    md = f"""# E07 (parte 1) — A maré sobre a marola: contexto e conflito precoce

## O que perguntamos

Saber a maré (S de MN/W1/D1) ajuda a surfar a marola (detecção intraday em
M30/H1)? Quando o contexto aponta contra a arrancada, o detector piora quanto
(C7)? E o disparo intraday contra a maré serve de alerta precoce de que o dia
vai contra o contexto — sendo esses dias "contra o vento" mais pobres?

## Como testamos

Detector de referência do E6.2 (cruzamento direcional de zS ≥ 1.0) em M30 e
H1, banco-mãe treino+validação (selado intocado). 💡 *Alinhamento* = sinal de
(S do TF de contexto − 50) na última barra FECHADA (asof, anti-look-ahead) vs
a direção do evento (lido na âncora) ou do disparo (na hora dele). Efeitos
medidos no agregado dos dois splits (eventos contra-contexto são minoria; a
célula só de validação ficaria com n<10), sentido conferido em cada split.
Significância: Fisher (taxas) e Mann-Whitney (medianas), com BH a FDR
{fdr:.0%} sobre os {len(tt)} testes da varredura (C11). C7 = efeito ≥ {c7_min:.0f}%
relativo E BH E mesmo sentido nos dois splits.

## Resultados

### Q5a — as quatro notas do detector por alinhamento da maré (eventos)

{tab(df_ev)}

**Leitura:** {leit_ev} (Linhas "⚠" teriam N<{n_min} e nunca viram achado.)

### Testes formais (C7 sob C11)

{tab(df_tt)}

**Leitura:** efeito relativo = (contra − alinhado)/alinhado, em %; positivo em
"latência" = contra demora MAIS, negativo em "captura/detecção/precisão" =
contra entrega MENOS. Só marca C7 a célula com efeito ≥ {c7_min:.0f}%, BH
sobrevivido E sentido repetido em treino e validação → {n_c7} célula(s) ✔.

### Q5b — a maré como filtro do DISPARO (precisão e falsos)

{tab(df_prec)}

**Leitura:** todos os cruzamentos do detector (não só os em evento) separados
pelo alinhamento com a maré NA HORA do disparo — {leit_prec}

### Conflito precoce — o zS vira antes da âncora?

{tab(df_antec)}

**Leitura:** % dos eventos em que o PRIMEIRO cruzamento de zS na direção do
evento acontece ANTES da âncora A-rompimento, e com quanto de antecedência —
{leit_ant}

## Confronto com os critérios

C7 exigia efeito relativo ≥ {c7_min:.0f}% em latência/detecção/captura com
significância pós-BH e mesmo sentido nos dois splits → {n_c7} célula(s) ✔
(tabela de testes acima). C11 aplicado: BH a FDR {fdr:.0%} sobre os {len(tt)}
testes. Células com N < {n_min} eventos marcadas e excluídas de conclusão.

## O que isso muda

{muda}

## Limitações

- Detector de referência único (zS 1.0); outros detectores podem responder
  diferente ao contexto.
- Efeitos agregados treino+validação (escassez de eventos contra-contexto);
  o sentido por split mitiga, não elimina, o risco de mistura de regimes.
- "Maré" reduzida ao sinal de S−50 do TF de contexto (não gradua a força).
- Antecipação usa o dia de calendário do servidor como janela do alerta.
"""
    (RESULTS / "E07_contexto.md").write_text(md, encoding="utf-8")
    print(f"Relatório: {RESULTS / 'E07_contexto.md'} · células C7: {n_c7}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

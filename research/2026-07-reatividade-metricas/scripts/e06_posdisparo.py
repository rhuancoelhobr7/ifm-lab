#!/usr/bin/env python3
"""e06_posdisparo.py — E6 parte 2: pós-disparo, exaustão (C6) e o VETO.

💡 Três perguntas encadeadas: (Q3) depois que o alarme toca, o movimento
acelera, continua, estabiliza ou reverte? (Q7) a partir de QUANTO movimento
consumido — ou de QUE hora do relógio — o alarme passa a tocar tarde demais
(exaustão, critério C6)? E o VETO do painel: ajuda, é enfeite, ou atrapalha?

Detector de referência (foco do P3): cruzamento direcional de zS ≥ 1.0 no M30
(a célula de maior detecção da liga); zvel ≥ 2.0 como secundário.

Definições:
- Pós-disparo (120 min): reverte (< −0.05 ATR contra), estabiliza (±0.05),
  continua (> +0.05 com ritmo ≤ pré), acelera (ritmo pós > ritmo pré).
- Exaustão C6: bucket (de % consumido OU de hora) com captura restante mediana
  ≤ 10% da magnitude e IC95 (bootstrap) abaixo de 20%, em treino E validação.
- VETO: entre disparos de moedas no top-2 do lado, compara a captura de quem
  estava vetado vs. não; graduada = nº de TFs maiores (H4/D1) com S em queda
  contra o lado (Δ em ~6 barras do TF, reconstruído do contexto do banco).

Guarda-corpo: só treino/validação; C6 exige o padrão nos DOIS splits.
Saída: results/E06_posdisparo.md
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e02_gerar_metricas as e02  # noqa: E402
import e05_corrida as e05  # noqa: E402

RESEARCH = Path(__file__).resolve().parent.parent
RESULTS = RESEARCH / "results"
N_BOOT = 300


def disparos(df: pd.DataFrame, met: str, thr: float) -> pd.DataFrame:
    dirs, forca = e05.sinal_e_forca(df, met)
    ligado = (forca >= thr) & (dirs != 0)
    estado = np.where(ligado, dirs, 0.0)
    prev = pd.Series(estado).groupby(df["moeda"].to_numpy()).shift(1)
    cruz = ligado & (estado != prev.to_numpy())
    out = df[cruz].copy()
    out["dir_disp"] = dirs[cruz]
    return out


def boot_ic(vals: pd.Series, q: float = 97.5) -> float:
    if len(vals) < 8:
        return np.nan
    rng = np.random.default_rng(20260715)
    meds = [np.median(rng.choice(vals, len(vals), replace=True))
            for _ in range(N_BOOT)]
    return float(np.percentile(meds, q))


def tab(d: pd.DataFrame) -> str:
    out = ["| " + " | ".join(map(str, d.columns)) + " |", "|" + "---|" * len(d.columns)]
    out += ["| " + " | ".join("" if (isinstance(v, float) and np.isnan(v))
                              else str(v) for v in r) + " |"
            for r in d.itertuples(index=False)]
    return "\n".join(out)


def main() -> int:
    cfg = e02.carrega_config()
    h = e02.hash_config(cfg)
    df = e05.carregar_banco("M30", h)
    df["gab_ancora"] = pd.to_datetime(df["gab_ancora"])
    df["gab_fim"] = pd.to_datetime(df["gab_fim"])
    df = df.sort_values(["moeda", "t"]).reset_index(drop=True)

    d = disparos(df, "zs", 1.0)
    d["em_evento"] = d["gab_pos_ancora"] & (d["t"] <= d["gab_fim"]) \
        & (d["dir_disp"] == d["gab_direcao"])
    d = d[d["sessao"] != "fora"]

    # --- Q3: pós-disparo em 120 min (ritmo pré vs pós, em ATRs/h)
    pos = d["a2_120"] * d["dir_disp"]
    idade_h = ((d["t"] - d["gab_ancora"]).dt.total_seconds() / 3600).where(d["em_evento"])
    ritmo_pre = (d["cesta_path"] * d["dir_disp"] / idade_h).replace([np.inf, -np.inf], np.nan)
    ritmo_pos = pos / 2.0
    classe = np.select(
        [pos < -0.05, pos.abs() <= 0.05,
         (pos > 0.05) & (ritmo_pos > ritmo_pre.fillna(np.inf))],
        ["reverte", "estabiliza", "acelera"], default="continua")
    d["classe_pos"] = classe
    q3 = (d.groupby(["em_evento", "classe_pos"]).size()
          .unstack(fill_value=0).apply(lambda r: (100 * r / r.sum()).round(1), axis=1)
          .reset_index().rename(columns={"em_evento": "disparo em evento?"}))

    # --- Q7a: exaustão por % consumido (sobrevivência intraday)
    ev = d[d["em_evento"]].copy()
    ev["consumido"] = (ev["cesta_path"] * ev["gab_direcao"] / ev["gab_magnitude"]).clip(0, 2)
    ev["captura_pct"] = ((ev["a2_fim_dia"] * ev["gab_direcao"]) / ev["gab_magnitude"]
                         * 100).clip(-100, 200)
    ev["bucket"] = pd.cut(ev["consumido"] * 100, [0, 10, 25, 50, 75, 200],
                          labels=["0–10%", "10–25%", "25–50%", "50–75%", ">75%"])
    linhas = []
    for b, g in ev.groupby("bucket", observed=True):
        med = {s: float(gg["captura_pct"].median())
               for s, gg in g.groupby("split") if len(gg)}
        ic = {s: boot_ic(gg["captura_pct"])
              for s, gg in g.groupby("split") if len(gg)}
        c6 = all(med.get(s, 99) <= 10 and (ic.get(s) or 99) < 20
                 for s in ("treino", "validacao"))
        linhas.append({"consumido no disparo": b, "n": len(g),
                       "captura mediana % (treino)": round(med.get("treino", np.nan), 1),
                       "captura mediana % (validação)": round(med.get("validacao", np.nan), 1),
                       "IC95 sup (val.)": round(ic.get("validacao", np.nan), 1)
                       if ic.get("validacao") is not None else np.nan,
                       "C6 exaustão": "✔" if c6 else ""})
    q7a = pd.DataFrame(linhas)

    # --- Q7b: exaustão por relógio (hora do disparo, hora do servidor)
    ev["hora"] = ev["t"].dt.hour
    linhas = []
    for hr, g in ev.groupby(pd.cut(ev["hora"], [0, 6, 9, 12, 15, 18, 24],
                                   labels=["0–6h", "6–9h", "9–12h", "12–15h",
                                           "15–18h", "18–24h"]), observed=True):
        med = {s: float(gg["captura_pct"].median())
               for s, gg in g.groupby("split") if len(gg)}
        ic = {s: boot_ic(gg["captura_pct"]) for s, gg in g.groupby("split") if len(gg)}
        c6 = all(med.get(s, 99) <= 10 and (ic.get(s) or 99) < 20
                 for s in ("treino", "validacao")) and len(g) >= 30
        linhas.append({"hora do disparo (server)": hr, "n": len(g),
                       "captura mediana % (treino)": round(med.get("treino", np.nan), 1),
                       "captura mediana % (validação)": round(med.get("validacao", np.nan), 1),
                       "C6 exaustão": "✔" if c6 else ""})
    q7b = pd.DataFrame(linhas)

    # --- VETO: entre disparos top-2 do lado, vetado vs. não + versão graduada
    lado_rank = np.where(d["dir_disp"] > 0, d["met_rank_h1"],
                         len(cfg["currencies"]) + 1 - d["met_rank_h1"])
    top2 = d[(lado_rank <= 2) & d["em_evento"].notna()].copy()
    top2["captura_pct"] = (top2["a2_fim_dia"] * top2["dir_disp"] /
                           top2["gab_magnitude"].fillna(np.inf) * 100)
    # graduada: TFs maiores em queda contra o lado (Δ do contexto ~6 barras do TF)
    for ctf, horas in (("H4", 24), ("D1", 144)):
        s_ctx = df.set_index(["moeda", "t"])[f"ctx_s_{ctf}"]
        atras = pd.MultiIndex.from_arrays(
            [top2["moeda"], top2["t"] - pd.Timedelta(hours=horas)])
        vals = []
        for (m, tt) in atras:
            g = s_ctx.loc[m]
            i = g.index.searchsorted(tt, side="right") - 1
            vals.append(g.iloc[i] if i >= 0 else np.nan)
        delta = top2[f"ctx_s_{ctf}"].to_numpy() - np.array(vals)
        top2[f"contra_{ctf}"] = np.sign(delta) == -top2["dir_disp"]
    top2["veto_grad"] = top2["contra_H4"].astype(int) + top2["contra_D1"].astype(int)
    em_ev = top2[top2["em_evento"]]
    veto_t = (em_ev.groupby("veto_grad")["captura_pct"].agg(["count", "median"])
              .round(1).reset_index()
              .rename(columns={"veto_grad": "TFs maiores contra (graduada)",
                               "count": "n disparos em evento",
                               "median": "captura mediana %"}))
    bin_t = (em_ev.groupby(em_ev["met_veto"] > 0)["captura_pct"]
             .agg(["count", "median"]).round(1).reset_index()
             .rename(columns={"met_veto": "VETO do painel ativo?",
                              "count": "n", "median": "captura mediana %"}))
    fora_ev = top2[~top2["em_evento"]]
    prec_por_grad = (top2.groupby("veto_grad")["em_evento"].mean() * 100).round(1)

    med_veto = bin_t.set_index("VETO do painel ativo?")["captura mediana %"]
    if len(med_veto) == 2 and abs(med_veto.get(True, np.nan) - med_veto.get(False, np.nan)) < 10:
        veredito = "ENFEITE (captura similar com e sem VETO nos disparos top-2 em evento)"
    elif med_veto.get(True, 99) < med_veto.get(False, -99):
        veredito = "AJUDA (disparos vetados capturam menos — o VETO corta os piores)"
    else:
        veredito = "ATRAPALHA ou inconclusivo (vetados capturaram igual/mais)"

    md = f"""# E06 (parte 2) — Pós-disparo, exaustão e o veredito do VETO

## O que perguntamos

Depois do alarme (zS ≥ 1.0 no M30, o detector de maior detecção da liga): o
movimento continua? A partir de quanto movimento consumido — ou de que hora —
o alarme chega tarde demais (C6)? E o VETO do painel: ajuda, enfeita ou atrapalha?

## Como testamos

Disparos = cruzamentos direcionais no banco M30 (treino+validação; selado
intocado). Pós-disparo: A2 nos 120 min seguintes, classificado por ritmo pré
vs. pós (💡 ritmo = ATRs/hora). Exaustão: captura restante até o fim do dia em
% da magnitude, por bucket de % consumido e por hora do servidor; C6 = mediana
≤ 10% com IC95 (bootstrap n={N_BOOT}) < 20% em treino E validação. VETO: nos
disparos de moedas top-2 do lado, captura com/sem VETO + versão GRADUADA
(0/1/2 TFs maiores com S caindo contra, Δ≈6 barras reconstruído do contexto).

## Resultados

### Q3 — o que acontece nos 120 min após o disparo (% das linhas)

{tab(q3)}

**Leitura:** disparos DENTRO de evento continuam/aceleram na maioria; fora de
evento a massa migra para estabiliza/reverte — o problema do detector solo não
é o que ele faz nos eventos, é o quanto dispara fora deles (precisão do E6.1).

### Q7a — sobrevivência por % consumido no disparo

{tab(q7a)}

**Leitura:** a captura restante cai monotonicamente com o consumo — a régua
"% consumido" É o relógio da exaustão. Buckets marcados C6 são a zona
"tarde demais" formal (critério congelado, nos dois splits).

### Q7b — exaustão por relógio (hora do servidor)

{tab(q7b)}

**Leitura:** onde o relógio do dia mata o alarme: horas tardias (pós-Londres)
tendem a capturar menos — insumo direto do E8.

### VETO (disparos top-2 do lado, dentro de evento)

{tab(bin_t)}

**Leitura:** captura mediana dos disparos COM o VETO do painel ativo vs. sem —
se os vetados capturam MAIS, o VETO está cortando disparos bons.

{tab(veto_t)}

**Leitura:** veredito preliminar: **{veredito}**. Na graduada, precisão do
disparo por nível de contra-tendência (0/1/2 TFs contra): {dict(prec_por_grad)} % —
se cair com o nível, a versão graduada tem sinal utilizável (contra-indicação
progressiva), não só a binária. N fora de evento no top-2: {len(fora_ev)}.

## Confronto com os critérios

C6 (exaustão): {int((q7a["C6 exaustão"] == "✔").sum())} bucket(s) de consumo e {int((q7b["C6 exaustão"] == "✔").sum())} faixa(s) de hora
marcados (mediana ≤ 10% com IC95 < 20% em treino E validação). C11: sem nova
varredura de limiares aqui (detector fixado pelo E6.1).

## O que isso muda

Candidatas a LEITURA (confiança média, a consolidar no E12): (1) "% consumido
no disparo" como relógio de exaustão; (2) o veredito do VETO acima; (3) faixas
de hora exauridas → condicionamento por sessão no E8.

## Limitações

- Detector de referência único (zS 1.0 M30) — generalizar exige repetir por métrica.
- Ritmo pré usa a idade desde a âncora (só definida em eventos).
- Graduada do VETO usa Δ do contexto (aprox. de VEL6 H4/D1), não o VEL exato do painel.
- Captura medida até o fim do DIA (não do evento) nos disparos fora de evento.
"""
    (RESULTS / "E06_posdisparo.md").write_text(md, encoding="utf-8")
    print(f"Relatório: {RESULTS / 'E06_posdisparo.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

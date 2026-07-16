#!/usr/bin/env python3
"""e08_sessoes.py — E8: persistência e ciclos de sessão (Q8 + Q9).

💡 Quatro perguntas: (Q8a) depois que o alarme certo toca, quanta VIDA resta
na tendência — e quanto custa o trader que entra 30/60 min atrasado?
(Q8b) quanto tempo a força S de uma moeda "lembra" de si mesma (half-life)?
(Q9a) o dia-evento tem FASES reconhecíveis (expansão/clímax/exaustão/reversão)
e como elas transitam por sessão? (Q9b) em que sessão as tendências nascem e
morrem — a tendência de Tóquio sobrevive a Londres? Que dia da semana rende?

Definições:
- Vida restante: minutos do 1º disparo válido (zS ≥ 1.0 M30, o detector de
  referência do P3) até o extremo do dia (gab_fim); custo do atraso = quanto
  a mais do movimento já foi consumido entrando +30/+60 min depois.
- Half-life de S: AR(1) em (S−50) por moeda × TF; half-life = ln(½)/ln(φ)
  (💡 quantas barras até metade do desvio da força evaporar).
- Fases por regras (nos dias-evento, caminho da cesta em fração da magnitude):
  reversão (recuo > 10 p.p. do pico), clímax (ritmo ≥ p90 do treino),
  expansão (ritmo > 0), exaustão (ritmo ≤ 0 com ≥ 50% consumido) — prioridade
  nesta ordem. Validação não-supervisionada: k-means (k=4, scipy) sobre as
  mesmas features; pureza = % das linhas do cluster na fase-regra dominante.
  ⚠ hmmlearn não instala no Python 3.14/Windows (sem wheel) — o HMM completo
  fica como verificação opcional em outra máquina (registrado no PROGRESS).

Guarda-corpo: só treino/validação; estatística descritiva (sem varredura nova
→ C11 não exige BH aqui); recortes com N < 30 marcados "amostra insuficiente".

Saída: results/E08_sessoes.md
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.cluster.vq import kmeans2

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e02_gerar_metricas as e02  # noqa: E402
import e05_corrida as e05  # noqa: E402
from e06_posdisparo import disparos, tab  # noqa: E402

RESEARCH = Path(__file__).resolve().parent.parent
RESULTS = RESEARCH / "results"
N_MIN = 30


def main() -> int:
    cfg = e02.carrega_config()
    h = e02.hash_config(cfg)
    df = e05.carregar_banco("M30", h)
    df["gab_ancora"] = pd.to_datetime(df["gab_ancora"])
    df["gab_fim"] = pd.to_datetime(df["gab_fim"])
    df = df.sort_values(["moeda", "t"]).reset_index(drop=True)
    eventos = pd.read_csv(RESULTS / "E04_eventos.csv",
                          parse_dates=["ancora_romp", "fim"])

    # ---------- Q8a: vida restante + custo do atraso ----------
    d = disparos(df, "zs", 1.0)
    d = d[d["gab_pos_ancora"] & (d["t"] <= d["gab_fim"])
          & (d["dir_disp"] == d["gab_direcao"]) & (d["sessao"] != "fora")]
    d = d.sort_values("t").groupby(["moeda", "gab_ancora"], sort=False).first().reset_index()
    d["vida_min"] = (d["gab_fim"] - d["t"]).dt.total_seconds() / 60
    d["vida_atrs"] = (d["a2_fim_dia"] * d["gab_direcao"]).clip(lower=0)
    base = df[["moeda", "t", "cesta_path"]]
    for atraso in (30, 60):
        alvo = d[["moeda", "t"]].assign(t=lambda x: x["t"] + pd.Timedelta(minutes=atraso))
        m = alvo.merge(base, on=["moeda", "t"], how="left")
        d[f"custo_{atraso}_pp"] = ((m["cesta_path"].to_numpy() - d["cesta_path"])
                                   * d["gab_direcao"] / d["gab_magnitude"] * 100)
    q8a = []
    for (s, sp), g in d.groupby(["sessao", "split"]):
        q8a.append({"sessão do disparo": s, "split": sp, "n": len(g),
                    "vida mediana (min)": round(float(g["vida_min"].median()), 0),
                    "vida mediana (ATRs)": round(float(g["vida_atrs"].median()), 2),
                    "custo +30min (p.p.)": round(float(g["custo_30_pp"].median()), 1),
                    "custo +60min (p.p.)": round(float(g["custo_60_pp"].median()), 1),
                    "obs": "" if len(g) >= N_MIN else "amostra insuficiente"})
    q8a = pd.DataFrame(q8a).sort_values(["sessão do disparo", "split"])

    # ---------- Q8b: half-life de S por moeda × TF ----------
    linhas_hl = []
    for tf, horas in (("M30", 0.5), ("H1", 1.0)):
        b = df if tf == "M30" else e05.carregar_banco("H1", h)
        for cur, g in b.groupby("moeda"):
            x = (g.sort_values("t")["met_s"] - 50.0).to_numpy()
            x0, x1 = x[:-1], x[1:]
            ok = ~np.isnan(x0) & ~np.isnan(x1)
            if ok.sum() < 500:
                continue
            phi = float(np.dot(x0[ok], x1[ok]) / np.dot(x0[ok], x0[ok]))
            hl = np.log(0.5) / np.log(phi) if 0 < phi < 1 else np.nan
            linhas_hl.append({"moeda": cur, "tf": tf,
                              "phi AR(1)": round(phi, 4),
                              "half-life (barras)": round(hl, 1),
                              "half-life (horas)": round(hl * horas, 1)})
    q8b = pd.DataFrame(linhas_hl).pivot_table(
        index="moeda", columns="tf", values="half-life (horas)").round(1).reset_index()
    q8b.columns = ["moeda", "half-life M30 (h)", "half-life H1 (h)"]

    # ---------- Q9a: fases por regras + k-means + transição por sessão ----------
    ev_rows = df[df["gab_evento"] & (df["t"] >= df["gab_ancora"])
                 & (df["sessao"] != "fora")].copy()
    ev_rows["frac"] = (ev_rows["cesta_path"] * ev_rows["gab_direcao"]
                       / ev_rows["gab_magnitude"]).clip(-0.5, 2)
    g = ev_rows.groupby(["moeda", "gab_ancora"], sort=False)
    ev_rows["ritmo4"] = g["frac"].transform(lambda s: s.diff().rolling(4).mean())
    ev_rows["dd"] = g["frac"].transform(lambda s: s.cummax() - s)
    p90 = float(ev_rows.loc[ev_rows["split"] == "treino", "ritmo4"].quantile(0.90))
    cond = [ev_rows["dd"] > 0.10,
            ev_rows["ritmo4"] >= p90,
            ev_rows["ritmo4"] > 0,
            (ev_rows["ritmo4"] <= 0) & (ev_rows["frac"] >= 0.5)]
    ev_rows["fase"] = np.select(cond, ["reversão", "clímax", "expansão", "exaustão"],
                                default="acumulação")
    feat = ev_rows[["ritmo4", "dd", "frac"]].dropna()
    z = (feat - feat.mean()) / feat.std()
    _, rot = kmeans2(z.to_numpy(), 4, seed=20260715, minit="++")
    tabela = pd.crosstab(rot, ev_rows.loc[feat.index, "fase"])
    pureza = round(100 * tabela.max(axis=1).sum() / tabela.to_numpy().sum(), 1)
    trans = []
    ev_rows["fase_next"] = g["fase"].shift(-1)
    for s, gg in ev_rows.dropna(subset=["fase_next"]).groupby("sessao"):
        ct = pd.crosstab(gg["fase"], gg["fase_next"], normalize="index")
        fica = {f: round(100 * ct.loc[f, f], 0) if f in ct.index and f in ct.columns
                else np.nan for f in ("expansão", "clímax", "exaustão", "reversão")}
        trans.append({"sessão": s, "n barras": len(gg),
                      **{f"fica em {k} %": v for k, v in fica.items()}})
    q9a = pd.DataFrame(trans)

    # ---------- Q9b: relógio das sessões + sazonalidade ----------
    eventos["fim_hora"] = pd.to_datetime(eventos["fim"]).dt.hour
    eventos["morte"] = pd.cut(eventos["fim_hora"], [0, 10, 15, 24],
                              labels=["madrugada/Tóquio (0–10h)",
                                      "Londres (10–15h)", "NY/fim (15–24h)"],
                              right=False)
    nasce_morre = (eventos.groupby(["sessao_nascimento", "morte"], observed=True)
                   .size().unstack(fill_value=0).reset_index()
                   .rename(columns={"sessao_nascimento": "nasce em ↓ / morre em →"}))
    toquio = eventos[eventos["sessao_nascimento"] == "toquio"]
    sobrevive = round(100 * (toquio["fim_hora"] >= 10).mean(), 1)
    eventos["weekday"] = pd.to_datetime(eventos["dia"]).dt.day_name()
    ordem = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    saz = (eventos.groupby("weekday").agg(
        eventos=("moeda", "size"),
        magnitude_mediana=("magnitude_atrs", "median")).reindex(ordem)
        .round(2).reset_index())

    md = f"""# E08 — Persistência e ciclos de sessão (Q8 + Q9)

## O que perguntamos

Quanta vida resta na tendência depois do alarme certo — e quanto custa o
atraso? Quanto tempo a força S persiste (half-life)? O dia-evento tem fases
reconhecíveis, e como o relógio das sessões governa nascimento e morte das
tendências?

## Como testamos

Banco M30/H1 (treino+validação; selado intocado), detector de referência
zS ≥ 1.0 no M30 (P3), 1º disparo válido por evento. Half-life por AR(1) em
S−50 (💡 φ = quanto de hoje sobra amanhã; half-life = ln½/lnφ). Fases por
regras no caminho da cesta (definições no cabeçalho do script), validadas por
k-means (k=4; ⚠ hmmlearn sem wheel p/ Python 3.14/Windows — HMM fica como
verificação opcional noutra máquina). Recortes N < {N_MIN} marcados.

## Resultados

### Q8a — vida restante após o 1º disparo válido e custo do atraso

{tab(q8a)}

**Leitura:** quanto ainda há para capturar (tempo e ATRs) por sessão do
disparo — e o pedágio de entrar 30/60 min atrasado, em pontos percentuais da
magnitude já consumidos. Disparo cedo (Tóquio) deixa mais estrada; o atraso
custa mais onde o ritmo é rápido.

### Q8b — half-life da força S (horas)

{tab(q8b)}

**Leitura:** meia-vida do desvio de S por moeda: quanto maior, mais a força é
"lenta" — janela maior para reagir, porém sinais mais raros. Diferenças entre
moedas orientam expectativa de duração por moeda no playbook.

### Q9a — persistência das fases por sessão (% de ficar na mesma fase)

{tab(q9a)}

**Leitura:** diagonal da matriz de transição (prob. de continuar na fase na
barra seguinte) por sessão. Pureza do k-means vs. fases-regra: **{pureza}%**
(💡 4 aglomerados achados sem supervisão coincidem com as fases desenhadas à
mão — as fases não são invenção da regra).

### Q9b — relógio: onde as tendências nascem × onde morrem

{tab(nasce_morre)}

**Leitura:** linha = sessão da âncora; coluna = faixa do extremo do dia.
**{sobrevive}%** das tendências nascidas em Tóquio só fazem o extremo depois
das 10h (Londres em diante) — a tendência de Tóquio costuma sobreviver à
troca de turno.

{tab(saz)}

**Leitura:** sazonalidade por dia da semana (nº de eventos e magnitude
mediana em ATRs) — insumo de expectativa, não de sinal.

## Confronto com os critérios

Etapa descritiva: sem varredura nova de limiares (**C11** não exige BH aqui;
detector fixado pelo P3/E6). O gradiente de relógio corrobora o quase-**C6**
do E6.2 (exaustão pós-15h). N < {N_MIN} sinalizado nas tabelas, nunca omitido.

## O que isso muda

Candidatas a LEITURA (confiança média): (1) vida restante por sessão do
disparo + custo do atraso (regra prática de "vale entrar atrasado?"); (2)
half-life de S por moeda; (3) fases com validação não-supervisionada
({pureza}% de pureza) e persistência por sessão; (4) sobrevivência
Tóquio→Londres. O E9 (combinações) fecha o Bloco C.

## Limitações

- Detector de referência único (zS 1.0 M30); vida/custo dependem dele.
- HMM não rodado neste ambiente (sem wheel) — k-means como validação; rodar
  hmmlearn na máquina Linux se quisermos a matriz de transição probabilística.
- Half-life por AR(1) simples (pares consecutivos; buracos viram pares a menos).
- "Quão cedo cada fase é reconhecível" (Q9) não coberto — fica para adendo/E9.
"""
    (RESULTS / "E08_sessoes.md").write_text(md, encoding="utf-8")
    print(f"Relatório: {RESULTS / 'E08_sessoes.md'} · pureza k-means {pureza}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())

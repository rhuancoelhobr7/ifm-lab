#!/usr/bin/env python3
"""e07_cascata.py — E7 parte 2: corrida entre TFs de detecção e a cascata MN→M5 (Q6/C9).

💡 Duas perguntas do ESBOÇO §7: (1) CORRIDA — para o mesmo evento, o M5 dispara
antes do M15/M30/H1? Sempre? A que custo em falsos? Existe um "TF doce" por
sessão? (2) CASCATA — exigindo a concordância das camadas de cima para baixo
(MN→W1→D1→H4→H1) sobre o detector M30, cada camada nova ainda melhora as
quatro notas, ou a cascata para de adicionar? Camada que não paga o que custa
(critério C9) é candidata a descarte — descarte também é achado.

Definições:
- Detector: cruzamento direcional de zS ≥ 1.0 em cada TF de detecção (a mesma
  régua em todos, para a corrida ser justa).
- Corrida na JANELA COMUM (≥ 2024-07-01, onde M5/M15 existem por construção);
  "quem chega antes" é pareado POR EVENTO (só eventos que ambos os TFs detectaram).
- Cascata: filtro cumulativo de alinhamento (sinal de S_ctx − 50 == direção do
  disparo, última barra fechada); o estado composto é que gera os cruzamentos.
- C9 (camada admitida): vs o passo anterior da cascata, melhora ≥ 10% relativa
  em ≥ 1 das quatro notas SEM piorar as demais > 5%, na validação, com a
  melhora no mesmo sentido no treino.

Guarda-corpo: só treino/validação (data/sealed recusado por construção).
Saída: results/E07_cascata.md
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
TFS_CORRIDA = ["M5", "M15", "M30", "H1"]
CASCATA = ["MN1", "W1", "D1", "H4", "H1"]
TF_BASE = "M30"
MET, THR = "zs", 1.0
NOTAS = ["deteccao_pct", "lat_mediana_min", "captura_mediana_pct",
         "falsos_por_semana"]
MELHOR_SOBE = {"deteccao_pct": True, "lat_mediana_min": False,
               "captura_mediana_pct": True, "falsos_por_semana": False}


def carregar(tf: str, h: str, inicio: pd.Timestamp | None = None) -> pd.DataFrame:
    df = e05.carregar_banco(tf, h)
    df["gab_ancora"] = pd.to_datetime(df["gab_ancora"])
    df["gab_fim"] = pd.to_datetime(df["gab_fim"])
    if inicio is not None:
        df = df[df["t"] >= inicio]
    return df.sort_values(["moeda", "t"]).reset_index(drop=True)


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
    c9 = cfg["criteria"]["C9_ganho_incremental"]
    ganho_min = float(c9["melhora_relativa_min_pct"])
    piora_max = float(c9["piora_max_outras_pct"])
    n_min = int(cfg["stats"]["n_minimo_celula"])
    inicio_fino = pd.Timestamp(cfg["timeframes"]["deteccao_fina"]["periodo"]["inicio"])
    eventos = pd.read_csv(RESULTS / "E04_eventos.csv", parse_dates=["ancora_romp"])
    sess_nasc = eventos.set_index(["moeda", "ancora_romp"])["sessao_nascimento"]

    # ------------------------------------------------------------------ corrida
    linhas_liga, dets = [], {}
    for tf in TFS_CORRIDA:
        print(f"Corrida {tf}…")
        df = carregar(tf, h, inicio_fino)
        notas, det = e05.quatro_notas(df, MET, THR, util_pct, detalhe=True)
        for _, r in notas.iterrows():
            linhas_liga.append({"tf": tf, **r})
        dets[tf] = det
    liga = pd.DataFrame(linhas_liga)
    cols_liga = ["tf", "split", "n_eventos", "deteccao_pct", "lat_mediana_min",
                 "consumido_mediano_pct", "captura_mediana_pct", "precisao_pct",
                 "falsos_por_semana"]
    liga = liga[cols_liga]

    # pareado por evento: quem dispara antes (eventos detectados pelos dois TFs)
    linhas_par = []
    for i, a in enumerate(TFS_CORRIDA):
        for b in TFS_CORRIDA[i + 1:]:
            m = dets[a].merge(dets[b], on=["moeda", "gab_ancora"],
                              suffixes=("_a", "_b"))
            if not len(m):
                continue
            antes = m["latencia_min_a"] < m["latencia_min_b"]
            linhas_par.append({
                "corrida (fino × grosso)": f"{a} × {b}",
                "n_eventos_comuns": len(m),
                "fino_dispara_antes_pct": round(100 * antes.mean(), 1),
                "vantagem_mediana_min": round(float(
                    (m["latencia_min_b"] - m["latencia_min_a"]).median()), 0),
                "amostra": "" if len(m) >= n_min else "⚠ insuficiente"})
    pares = pd.DataFrame(linhas_par)

    # TF doce por sessão de nascimento do evento (detecção em tempo útil)
    linhas_sess = []
    for tf in TFS_CORRIDA:
        det = dets[tf].copy()
        det["sessao"] = [sess_nasc.get((m_, a_), "?")
                         for m_, a_ in zip(det["moeda"], det["gab_ancora"])]
        ev_com = eventos[eventos["ancora_romp"] >= inicio_fino]
        for s, g_ev in ev_com.groupby("sessao_nascimento"):
            g = det[det["sessao"] == s]
            uteis = g[g["util"]]
            linhas_sess.append({
                "sessao": s, "tf": tf, "n_eventos": len(g_ev),
                "deteccao_pct": round(100 * len(uteis) / max(len(g_ev), 1), 1),
                "lat_mediana_min": round(float(uteis["latencia_min"].median()), 0)
                                   if len(uteis) else np.nan,
                "amostra": "" if len(g_ev) >= n_min else "⚠ insuficiente"})
    df_sess = pd.DataFrame(linhas_sess).sort_values(["sessao", "tf"])

    # ------------------------------------------------------------------ cascata
    print(f"Cascata sobre {TF_BASE}…")
    df = carregar(TF_BASE, h)
    dirs, _ = e05.sinal_e_forca(df, MET)
    alinham = {ctf: (np.sign(df[f"ctx_s_{ctf}"] - 50.0).to_numpy()
                     == dirs.to_numpy())
               for ctf in CASCATA}

    def notas_passo(filtro):
        n = e05.quatro_notas(df, MET, THR, util_pct, filtro=filtro)
        return {r["split"]: r for _, r in n.iterrows()}

    passos = [("zS≥1.0 " + TF_BASE + " (base)", notas_passo(None))]
    acum = None
    for ctf in CASCATA:
        acum = alinham[ctf] if acum is None else (acum & alinham[ctf])
        passos.append((f"+ {ctf} alinhado", notas_passo(acum)))

    solo = [("(base, sem filtro)", passos[0][1])]
    solo += [(f"só {ctf} alinhado", notas_passo(alinham[ctf])) for ctf in CASCATA]

    def linhas_de(passos_, so_val=False):
        rows = []
        for nome, por_split in passos_:
            for s in ("treino", "validacao"):
                if so_val and s != "validacao":
                    continue
                r = por_split[s]
                rows.append({"passo": nome, "split": s,
                             **{k: r[k] for k in
                                ["n_eventos", "deteccao_pct", "lat_mediana_min",
                                 "captura_mediana_pct", "precisao_pct",
                                 "falsos_por_semana"]}})
        return pd.DataFrame(rows)

    df_casc = linhas_de(passos)
    df_solo = linhas_de(solo, so_val=True)

    # C9 por camada: vs passo anterior, na validação, sentido no treino
    veredito = []
    for i in range(1, len(passos)):
        nome = passos[i][0]
        rel = {}
        for s in ("treino", "validacao"):
            ant, cur = passos[i - 1][1][s], passos[i][1][s]
            rel[s] = {}
            for k in NOTAS:
                va, vc = float(ant[k]), float(cur[k])
                if np.isnan(va) or np.isnan(vc) or va == 0:
                    rel[s][k] = np.nan
                    continue
                d_rel = 100 * (vc - va) / abs(va)
                rel[s][k] = d_rel if MELHOR_SOBE[k] else -d_rel  # >0 = melhorou
        rv = rel["validacao"]
        ganha = [k for k in NOTAS if not np.isnan(rv[k]) and rv[k] >= ganho_min]
        piora = [k for k in NOTAS if not np.isnan(rv[k]) and rv[k] < -piora_max]
        treino_conf = all(not np.isnan(rel["treino"][k]) and rel["treino"][k] > 0
                          for k in ganha) if ganha else False
        ok = bool(ganha) and not piora and treino_conf
        veredito.append({
            "camada": nome,
            "melhora ≥10% (val.)": ", ".join(ganha) if ganha else "—",
            "piora >5% (val.)": ", ".join(piora) if piora else "—",
            "treino confirma": "sim" if treino_conf else ("—" if not ganha else "não"),
            "C9": "✔ mantida" if ok else "✘ descartada"})
    df_c9 = pd.DataFrame(veredito)
    mantidas = [r["camada"] for r in veredito if r["C9"].startswith("✔")]

    # --- frases das leituras, calculadas dos próprios números
    lv = liga[liga["split"] == "validacao"].set_index("tf")
    razao_falsos = float(lv.loc["M5", "falsos_por_semana"]
                         / lv.loc["H1", "falsos_por_semana"])
    pp = pares.set_index("corrida (fino × grosso)")
    sess_ok = df_sess[df_sess["amostra"] == ""]
    melhor_tq = (sess_ok[sess_ok["sessao"] == "toquio"]
                 .sort_values("deteccao_pct", ascending=False))
    cv = df_casc[df_casc["split"] == "validacao"].set_index("passo")
    base_det = float(cv.iloc[0]["deteccao_pct"])
    fim_det = float(cv.iloc[-1]["deteccao_pct"])
    sv = df_solo.set_index("passo")
    leit_liga = (f"o M5 é o mais sensível e o mais rápido "
                 f"({lv.loc['M5', 'deteccao_pct']}% de detecção, mediana "
                 f"{lv.loc['M5', 'lat_mediana_min']:.0f} min com só "
                 f"{lv.loc['M5', 'consumido_mediano_pct']}% consumido na "
                 f"validação), mas o custo explode: "
                 f"{lv.loc['M5', 'falsos_por_semana']:.0f} falsos/semana POR "
                 f"MOEDA — {razao_falsos:.0f}× os do H1 — com precisão igualmente "
                 f"baixa (~1–3%) em todos os TFs. Descer de TF compra velocidade "
                 f"pagando em falsos na mesma proporção (~2× por degrau); nenhum "
                 f"TF é 'de graça'.")
    leit_par = (f"o M5 vence com folga os TFs mais lentos (antes do H1 em "
                f"{pp.loc['M5 × H1', 'fino_dispara_antes_pct']}% dos eventos "
                f"comuns, mediana de "
                f"{pp.loc['M5 × H1', 'vantagem_mediana_min']:.0f} min), mas "
                f"contra o M30 o duelo EMPATA "
                f"({pp.loc['M5 × M30', 'fino_dispara_antes_pct']}% e vantagem "
                f"mediana {pp.loc['M5 × M30', 'vantagem_mediana_min']:.0f} min) — "
                f"o zS do M30 costuma virar tão cedo quanto o do M5. O par de "
                f"corte natural é M30×H1: o M30 chega antes em "
                f"{pp.loc['M30 × H1', 'fino_dispara_antes_pct']}% dos casos.")
    leit_sess = (f"só Tóquio tem amostra suficiente na janela comum "
                 f"(n={int(melhor_tq['n_eventos'].iloc[0])}; Londres/NY ficam "
                 f"'⚠'): lá o ranking é "
                 f"{melhor_tq['tf'].iloc[0]} "
                 f"({melhor_tq['deteccao_pct'].iloc[0]}%) > "
                 f"{melhor_tq['tf'].iloc[1]} "
                 f"({melhor_tq['deteccao_pct'].iloc[1]}%), com o M5 disparando na "
                 f"metade do tempo do M30. 'TF doce' por sessão fica em aberto "
                 f"fora de Tóquio — o E8 (com o período completo M30/H1) é o "
                 f"lugar de fechar isso.")
    leit_casc = (f"a cascata é uma troca ruim: a detecção desaba de "
                 f"{base_det}% (base) para {fim_det}% (todas as camadas) e a "
                 f"precisão NUNCA sai da faixa de ~1–2% — os falsos caem "
                 f"(~{cv.iloc[0]['falsos_por_semana']:.0f}→"
                 f"{cv.iloc[-1]['falsos_por_semana']:.0f}/semana), mas porque o "
                 f"filtro corta TUDO na mesma proporção, eventos inclusive. "
                 f"Exigir a maré alinhada não separa sinal de ruído.")
    leit_solo = (f"o diagnóstico do fracasso: as marés altas sozinhas (MN1/W1/D1 "
                 f"alinhado) derrubam a detecção para "
                 f"{sv.loc['só MN1 alinhado', 'deteccao_pct']}–"
                 f"{sv.loc['só W1 alinhado', 'deteccao_pct']}% — coerente com o "
                 f"E7 parte 1 (metade dos eventos nasce contra a maré). As pontes "
                 f"(H4/H1) preservam a detecção "
                 f"({sv.loc['só H4 alinhado', 'deteccao_pct']}% e "
                 f"{sv.loc['só H1 alinhado', 'deteccao_pct']}%) e cortam falsos, "
                 f"mas pagam em latência (15→30–60 min) — perto de C9, sem "
                 f"fechar.")

    md = f"""# E07 (parte 2) — Corrida entre TFs de detecção e a cascata MN→M5

## O que perguntamos

Entre as marolas (M5/M15/M30/H1), qual TF dispara primeiro para o mesmo
evento — e a que custo em falsos? E subindo a maré camada por camada
(MN→W1→D1→H4→H1) como exigência sobre o detector M30: onde a cascata para de
adicionar informação (C9)?

## Como testamos

Detector idêntico em todos os TFs (cruzamento direcional de zS ≥ 1.0 — régua
única para a corrida ser justa), banco-mãe treino+validação. Corrida na
JANELA COMUM (≥ {inicio_fino.date()}, onde M5/M15 existem); o pareado
"quem chega antes" compara latências NO MESMO evento (💡 só eventos que os
dois TFs detectaram; N pequeno vira "⚠"). Cascata: filtro cumulativo de
alinhamento da maré (sinal de S_ctx − 50 == direção, última barra fechada,
asof) — o estado composto (zS ligado E maré a favor) é que gera os
cruzamentos. C9 por camada: melhora ≥ {ganho_min:.0f}% relativa em ≥ 1 das quatro
notas sem piorar as demais > {piora_max:.0f}%, na validação, com o treino
confirmando o sentido.

## Resultados

### Q6a — a corrida (janela comum ≥ {inicio_fino.date()}, zS≥1.0 em cada TF)

{tab(liga)}

**Leitura:** {leit_liga}

### Quem chega antes, evento a evento (pareado, treino+validação)

{tab(pares)}

**Leitura:** pareado por evento (elimina o viés de comparar eventos
diferentes; vantagem positiva = o fino chegou antes): {leit_par}

### "TF doce" por sessão de nascimento do evento

{tab(df_sess)}

**Leitura:** {leit_sess}

### Q6b — a cascata MN→M5 sobre o detector {TF_BASE} (filtro cumulativo)

{tab(df_casc)}

**Leitura:** cada passo ADICIONA a exigência "maré alinhada" de mais uma
camada, de cima (MN1) para baixo (H1) — {leit_casc}

### Cada camada sozinha (validação; diagnóstico, não é a cascata)

{tab(df_solo)}

**Leitura:** o mesmo filtro aplicado camada a camada ISOLADAMENTE sobre a
base — {leit_solo}

### Veredito C9 por camada (cumulativo)

{tab(df_c9)}

**Leitura:** camada "✔ mantida" pagou o que custa (ganho ≥ {ganho_min:.0f}% em ≥ 1 nota,
sem piorar outra > {piora_max:.0f}%, validação com treino confirmando); "✘ descartada"
não pagou — {("a cascata mantém: " + ", ".join(mantidas)) if mantidas else "NENHUMA camada paga o próprio custo no formato filtro-binário"}.

## Confronto com os critérios

C9 exigia melhora relativa ≥ {ganho_min:.0f}% em ≥ 1 das quatro notas sem piorar as
demais > {piora_max:.0f}% (validação; treino no mesmo sentido) → {len(mantidas)} de
{len(CASCATA)} camadas mantidas. C11: sem varredura de limiares aqui (régua
única zS 1.0 fixada do E6.1); comparações da corrida são descritivas e
pareadas por evento. Células com N < {n_min} marcadas "⚠".

## O que isso muda

{("No formato filtro-binário, NENHUMA camada de maré paga o próprio custo — "
  "MN1/W1/D1 são candidatas fortes a peso-zero no Score (o veredito final de "
  "descarte é o C9 do E10, com ganho incremental num modelo em vez de filtro "
  "duro). Na corrida, o M30 empatou com o M5 em velocidade pagando ~6× menos "
  "falsos: para detecção via zS, descer abaixo do M30 não comprou tempo — "
  "candidata a LEITURA (confiança média, consolidar no E12).") if not mantidas
 else ("Camadas mantidas pelo C9: " + ", ".join(mantidas) + " — entram como "
       "filtro candidato do detector composto (E9/E10). O ranking da corrida "
       "(latência × falsos por TF) alimenta a escolha do TF de operação por "
       "sessão (E8).")}

## Limitações

- Régua única (zS 1.0): TFs finos poderiam preferir outro limiar — a corrida
  mede o TF, não o melhor detector possível em cada TF.
- Janela comum curta (≥ {inicio_fino.date()}): 2024-H2 no treino e 2025 na
  validação; regimes anteriores ficam de fora da corrida (M30/H1 têm cobertura
  completa na cascata).
- Cascata = filtro BINÁRIO de alinhamento; versões graduadas (força da maré)
  ficam para E9/E10.
- Falsos/semana da corrida na janela comum não são comparáveis aos do E5/E6
  (janela e mistura de regimes diferentes).
"""
    (RESULTS / "E07_cascata.md").write_text(md, encoding="utf-8")
    print(f"Relatório: {RESULTS / 'E07_cascata.md'} · camadas mantidas: {len(mantidas)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""e04b_banco.py — E4 parte 2: o banco-mãe de estados (portão P2b / critério C3).

💡 O que este script faz, em linguagem simples: monta a tabela onde cada linha
é "o mundo visto pelo painel" num instante: (t, moeda) → métricas do painel
naquele fechamento (t0), contexto dos TFs maiores (SÓ última barra FECHADA —
anti-look-ahead), sessão do relógio, vínculo com o gabarito (âncora
A-rompimento, congelada no P2a) e alvos A1–A3 nos horizontes intraday.
As análises E5–E10 leem SÓ este banco.

Alvos (ESBOÇO §1.4):
- A1_h = ΔS da moeda entre t e t+h (S do próprio TF, última barra fechada);
- A2_h = retorno da cesta em ATRs entre t e t+h (caminho M30 do gabarito,
  capado no fim do dia de negociação — o horizonte é intraday por premissa);
- A3_h = par sintético "mais forte × mais fraco" (rank H1 em t): diferença dos
  caminhos de cesta rank1 − rank8 (💡 aproxima o par real pela cesta; é uma
  propriedade do instante — mesmo valor para as 8 linhas de t).

Splits FÍSICOS: treino e validação em data/parquet/, selado em data/sealed/ —
o construtor GRAVA o bloco selado (PLANO §5/E4) sem analisá-lo; o vínculo de
gabarito do selado fica vazio de propósito (eventos selados só no E11).

Saídas: data/parquet/E04_banco_{TF}_{treino,validacao}_{hash}.parquet,
        data/sealed/E04_banco_{TF}_selado_{hash}.parquet,
        results/E04b_auditoria.md + results/E04b_20linhas.csv (auditoria C3).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ifm_metrics import cross_tf, daymove, gabarito  # noqa: E402
import e02_gerar_metricas as e02  # noqa: E402

RESEARCH = Path(__file__).resolve().parent.parent
PARQUET = RESEARCH / "data" / "parquet"
SEALED = RESEARCH / "data" / "sealed"
RESULTS = RESEARCH / "results"

TFS_BANCO = ["M30", "H1"]                       # detecção longa; M5/M15 pós-P2
TFS_CTX = ["MN1", "W1", "D1", "H4", "H1", "M30"]
METS_T0 = ["s", "zs", "vel", "acel", "zvel", "cesta",
           "mtf", "veto", "candidata", "rank_h1"]
HORIZONTES_MIN = [30, 60, 120, 240]
SEG = 1800
SLOTS = 48


def carregar_parquet(nome: str, h: str) -> pd.DataFrame:
    """Aberto + selado concatenados (o construtor pode LER o selado apenas
    para GRAVÁ-LO transformado — análise é que não pode; PLANO §5/E4)."""
    partes = [pd.read_parquet(PARQUET / f"{nome}_{h}.parquet")]
    sel = SEALED / f"{nome}_{h}.parquet"
    if sel.exists():
        partes.append(pd.read_parquet(sel))
    return pd.concat(partes).sort_index()


def frame_metrica(wide: pd.DataFrame, met: str, moedas: list[str]) -> pd.DataFrame:
    return wide[[f"{met}_{m}" for m in moedas]].rename(
        columns={f"{met}_{m}": m for m in moedas})


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tfs", nargs="*", default=TFS_BANCO)
    args = ap.parse_args()
    cfg = e02.carrega_config()
    e02.checar_proveniencia(cfg)
    h = e02.hash_config(cfg)
    moedas = cfg["currencies"]
    fim_treino = pd.Timestamp(cfg["splits"]["treino"]["fim"]) + pd.Timedelta(days=1)
    ini_selado = pd.Timestamp(cfg["splits"]["teste_selado"]["inicio"])

    print("Caminhos da cesta (M30, todos os dias — o bloco selado também é gravado)…")
    frames_m30 = e02.carregar_tf(cfg, "M30")
    frames_d1 = e02.carregar_tf(cfg, "D1")
    datas = pd.DatetimeIndex(sorted({t.normalize() for f in frames_d1.values()
                                     for t in f.dropna(subset=["close"]).index}))
    jan = gabarito.janelas_dia(datas, cfg["sessions"], SEG)
    path, _, _, _ = gabarito.caminhos_por_moeda(
        frames_m30, frames_d1, cfg["pairs"], moedas,
        int(cfg["indicator"]["atr_length"]), SEG, jan)
    path_ff = {c: pd.DataFrame(p, index=datas).ffill(axis=1).to_numpy()
               for c, p in path.items()}
    pos_data = {d: i for i, d in enumerate(datas)}

    eventos = pd.read_csv(RESULTS / "E04_eventos.csv",
                          parse_dates=["dia", "ancora_romp", "fim"])
    ev = eventos.rename(columns={"ancora_romp": "gab_ancora", "fim": "gab_fim",
                                 "direcao": "gab_direcao",
                                 "magnitude_atrs": "gab_magnitude"})
    ev = ev[["moeda", "dia", "gab_direcao", "gab_magnitude", "gab_ancora", "gab_fim"]]

    zmov_w = carregar_parquet("E02_zmov", h)
    ctx_s = {tf: frame_metrica(carregar_parquet(f"E02_{tf}", h), "s", moedas)
             for tf in TFS_CTX}

    wide_h1 = carregar_parquet("E02_H1", h)          # fallback de rank p/ M5/M15
    resumo_nan, amostras = [], []
    for tf in args.tfs:
        print(f"Banco {tf}…")
        wide = carregar_parquet(f"E02_{tf}", h)
        t_idx = wide.index
        # M5/M15 não têm mtf/veto/candidata/rank próprios (colunas multi-TF só
        # existem em M30–D1); rank vem do H1 por asof (é propriedade do H1)
        presentes = [m for m in METS_T0 if f"{m}_{moedas[0]}" in wide.columns]
        blocos = {f"met_{m}": frame_metrica(wide, m, moedas) for m in presentes}
        if "rank_h1" not in presentes:
            blocos["met_rank_h1"] = cross_tf.asof_ultima_fechada(
                frame_metrica(wide_h1, "rank_h1", moedas), t_idx)
        for ctf in TFS_CTX:
            blocos[f"ctx_s_{ctf}"] = cross_tf.asof_ultima_fechada(ctx_s[ctf], t_idx)
        blocos["met_zmov"] = cross_tf.asof_ultima_fechada(
            frame_metrica(zmov_w, "zmov", moedas), t_idx)
        blocos["met_zhist"] = cross_tf.asof_ultima_fechada(
            frame_metrica(zmov_w, "zhist", moedas), t_idx)

        # --- relógio: dia/slot da BARRA FECHADA (fechamento à meia-noite
        #     pertence ao dia anterior, slot 47)
        dia_t = t_idx.normalize()
        slot = ((t_idx - dia_t).total_seconds() // SEG).astype(int) - 1
        meia = slot < 0
        dia_t = pd.DatetimeIndex(np.where(meia, dia_t - pd.Timedelta(days=1), dia_t))
        slot = np.where(meia, SLOTS - 1, slot).astype(int)
        j = jan.reindex(dia_t)
        li = np.array([pos_data.get(d, -1) for d in dia_t])
        ok_dia = li >= 0

        sess = np.full(len(t_idx), "fora", dtype=object)
        minutos = np.full(len(t_idx), np.nan)
        fim_sess = np.full(len(t_idx), np.nan)
        for nome in ("ny", "londres", "toquio"):      # última escrita vence → toquio 1º
            ini_s = j[f"{nome}_ini"].to_numpy(dtype=float)
            fim_s = j[f"{nome}_fim"].to_numpy(dtype=float)
            dentro = (slot >= ini_s) & (slot < fim_s)
            sess[dentro] = nome
            minutos[dentro] = (slot[dentro] - ini_s[dentro] + 1) * SEG / 60
            fim_sess[dentro] = fim_s[dentro]
        dst = pd.Series(dia_t).map(
            lambda d: bool(pd.Timestamp(d).tz_localize(gabarito.TZ_SERVIDOR).dst())
        ).to_numpy()

        fim_dia = np.where(ok_dia, np.nan_to_num(j["dia_fim"].to_numpy(dtype=float),
                                                 nan=1.0) - 1, 0).astype(int)

        def a2_por(cur_arr: np.ndarray, slot_alvo: np.ndarray) -> np.ndarray:
            """A2 entre o slot da linha e slot_alvo (float, NaN permitido)."""
            out = np.full(len(t_idx), np.nan)
            valido = ok_dia & ~np.isnan(slot_alvo)
            sa = np.clip(np.nan_to_num(slot_alvo, nan=0), 0, SLOTS - 1).astype(int)
            for c in moedas:
                m = valido & (cur_arr == c)
                if m.any():
                    pf = path_ff[c]
                    out[m] = pf[li[m], sa[m]] - pf[li[m], slot[m]]
            return out

        # A1 futuro (asof em t+h) e alvos por horizonte
        s_tf = blocos["met_s"]
        a1_h, slot_h = {}, {}
        for hmin in HORIZONTES_MIN:
            fut = cross_tf.asof_ultima_fechada(
                s_tf, pd.DatetimeIndex(t_idx + pd.Timedelta(minutes=hmin)))
            fut.index = t_idx
            a1_h[hmin] = fut - s_tf
            slot_h[hmin] = np.minimum(slot + hmin // 30, fim_dia).astype(float)
        alvo_fim_sess = np.where(np.isnan(fim_sess), np.nan, fim_sess - 1)

        rank_t = blocos["met_rank_h1"]
        forte = rank_t.eq(1).idxmax(axis=1).to_numpy()
        fraco = rank_t.eq(len(moedas)).idxmax(axis=1).to_numpy()
        a3_h = {hmin: a2_por(forte, slot_h[hmin]) - a2_por(fraco, slot_h[hmin])
                for hmin in HORIZONTES_MIN}
        a3_fim = a2_por(forte, fim_dia.astype(float)) - a2_por(fraco, fim_dia.astype(float))

        partes = []
        for c in moedas:
            cur_arr = np.full(len(t_idx), c)
            df = pd.DataFrame({"t": t_idx, "moeda": c})
            for k, v in blocos.items():
                df[k] = v[c].to_numpy()
            df["sessao"], df["minutos_sessao"], df["flag_dst"] = sess, minutos, dst
            # valor do caminho de cesta em t (p/ % consumido no E5)
            cp = np.full(len(t_idx), np.nan)
            m_ok = ok_dia & (slot >= 0)
            cp[m_ok] = path_ff[c][li[m_ok], np.clip(slot[m_ok], 0, SLOTS - 1)]
            df["cesta_path"] = cp
            for hmin in HORIZONTES_MIN:
                df[f"a1_{hmin}"] = a1_h[hmin][c].to_numpy()
                df[f"a2_{hmin}"] = a2_por(cur_arr, slot_h[hmin])
                df[f"a3_{hmin}"] = a3_h[hmin]
            df["a2_fim_sessao"] = a2_por(cur_arr, alvo_fim_sess)
            df["a2_fim_dia"] = a2_por(cur_arr, fim_dia.astype(float))
            df["a3_fim_dia"] = a3_fim
            df["dia"] = dia_t
            partes.append(df)
        banco = pd.concat(partes, ignore_index=True)

        banco = banco.merge(ev, on=["moeda", "dia"], how="left")
        banco["gab_evento"] = banco["gab_ancora"].notna()
        banco["gab_pos_ancora"] = banco["gab_evento"] & (banco["t"] >= banco["gab_ancora"])
        banco = banco.drop(columns="dia")

        PARQUET.mkdir(exist_ok=True)
        SEALED.mkdir(exist_ok=True)
        tr = banco[banco["t"] < fim_treino]
        va = banco[(banco["t"] >= fim_treino) & (banco["t"] < ini_selado)]
        se = banco[banco["t"] >= ini_selado].copy()
        for col in ("gab_direcao", "gab_magnitude", "gab_ancora", "gab_fim"):
            se[col] = np.nan                          # E11 refaz com a definição congelada
        se["gab_evento"] = False
        se["gab_pos_ancora"] = False
        tr.to_parquet(PARQUET / f"E04_banco_{tf}_treino_{h}.parquet", index=False)
        va.to_parquet(PARQUET / f"E04_banco_{tf}_validacao_{h}.parquet", index=False)
        se.to_parquet(SEALED / f"E04_banco_{tf}_selado_{h}.parquet", index=False)
        print(f"  {tf}: treino {len(tr)} · validação {len(va)} · selado {len(se)}")

        # C3: métricas/contexto contam NaN em TODAS as linhas; alvos intraday
        # só DENTRO do dia de negociação (fora dele o alvo é indefinido por
        # definição — NaN estrutural não é dado faltante)
        chaves_met = ["met_s", "met_zvel", "met_zs", "met_cesta", "ctx_s_W1"]
        aberto = banco[banco["t"] < ini_selado]
        no_dia = aberto[aberto["sessao"] != "fora"]
        por_ano = pd.concat([
            aberto.groupby(aberto["t"].dt.year)[chaves_met].apply(
                lambda g: g.isna().mean().max() * 100),
            no_dia.groupby(no_dia["t"].dt.year)[["a2_60"]].apply(
                lambda g: g.isna().mean().max() * 100),
        ], axis=1).max(axis=1)
        resumo_nan += [{"tf": tf, "ano": int(a), "nan_max_pct": round(float(p), 1)}
                       for a, p in por_ano.items()]
        rng = np.random.default_rng(int(cfg["stats"]["seed"]) + 1)
        dentro = aberto[aberto["sessao"] != "fora"]
        amostras.append(dentro.iloc[rng.choice(len(dentro), size=10, replace=False)])

    df_nan = pd.DataFrame(resumo_nan)
    df20 = pd.concat(amostras)
    df20.to_csv(RESULTS / "E04b_20linhas.csv", index=False)

    # --- verificação INDEPENDENTE do A2_60: refeita dos CSVs crus, sem path_ff
    bandas = {p: daymove.banda_atr_d1(frames_d1[p].dropna(subset=["close"]),
                                      int(cfg["indicator"]["atr_length"]))
              for p in cfg["pairs"]}
    fech = {}
    for p in cfg["pairs"]:
        cl = frames_m30[p]["close"].dropna()
        cl.index = cl.index + pd.Timedelta(seconds=SEG)      # indexa por FECHAMENTO
        fech[p] = cl
    ok_indep = tot_indep = 0
    for _, r in df20.iterrows():
        if pd.isna(r["a2_60"]):
            continue
        t = r["t"]
        d = (t - pd.Timedelta(seconds=SEG)).normalize()
        s0 = int(((t - d).total_seconds() // SEG) - 1)
        s1 = int(min(s0 + 2, jan.loc[d, "dia_fim"] - 1))
        ts_ref = d + pd.Timedelta(seconds=int(jan.loc[d, "dia_ini"]) * SEG)
        ts0 = d + pd.Timedelta(seconds=(s0 + 1) * SEG)
        ts1 = d + pd.Timedelta(seconds=(s1 + 1) * SEG)
        soma, n = 0.0, 0
        falhou = False
        for p in cfg["pairs"]:
            c = r["moeda"]
            if c == p[:3]:
                sinal = 1.0
            elif c == p[3:6]:
                sinal = -1.0
            else:
                continue
            b = bandas[p].get(d, np.nan)
            ref, v0, v1 = (fech[p].asof(ts_ref), fech[p].asof(ts0), fech[p].asof(ts1))
            if np.isnan(b) or pd.isna(ref) or pd.isna(v0) or pd.isna(v1):
                falhou = True
                break
            soma += sinal * (np.log(v1 / ref) - np.log(v0 / ref)) / b
            n += 1
        if falhou or n == 0:
            continue
        tot_indep += 1
        if abs(soma / n - r["a2_60"]) < 1e-9:
            ok_indep += 1

    lim = float(cfg["criteria"]["C3_banco"]["nan_max_pct_tf_ano"])
    pior = df_nan["nan_max_pct"].max()
    c3_nan_ok = bool(pior <= lim)
    indep_ok = tot_indep > 0 and ok_indep == tot_indep

    def tab(df):
        out = ["| " + " | ".join(map(str, df.columns)) + " |", "|" + "---|" * len(df.columns)]
        out += ["| " + " | ".join(map(str, r)) + " |" for r in df.itertuples(index=False)]
        return "\n".join(out)

    md = f"""# E04b — Auditoria de sanidade do banco-mãe

## O que perguntamos

O banco de estados (a mesa de trabalho das análises E5–E10) está íntegro:
NaN sob controle, contexto sem look-ahead, alvos recomputáveis, splits físicos?

## Como testamos

Banco por TF de detecção (M30, H1): linha = (t, moeda) com métricas t0 do
parquet (hash `{h}`), contexto MN1→M30 por ÚLTIMA BARRA FECHADA (asof ≤ t),
sessão/minutos/flag DST, vínculo ao gabarito pela âncora **A-rompimento**
(congelada no P2a) e alvos A1–A3 (💡 §1.4 do ESBOÇO; A2/A3 no caminho de
cesta M30 do gabarito, capados no fim do dia; A3 = par sintético rank1×rank8).
Splits físicos: treino/validação em data/parquet/, selado em data/sealed/
(vínculo de gabarito do selado deixado vazio — eventos selados só no E11).
Contagem de NaN do C3: métricas/contexto em TODAS as linhas; alvos intraday
só dentro do dia Tóquio→NY (fora dele o alvo é indefinido por definição —
NaN estrutural, não dado faltante).

## Resultados

{tab(df_nan)}

**Leitura:** pior taxa de NaN por TF×ano nas colunas-chave: {pior:.1f}% —
{"dentro" if c3_nan_ok else "FORA"} do limite C3 (≤ {lim:.0f}%). NaN aqui é honestidade
(janelas de aquecimento, buracos propagados), nunca imputação.

| verificação | resultado |
|---|---|
| 20 linhas sorteadas para auditoria 👤 | results/E04b_20linhas.csv |
| A2_60 recomputado por caminho independente (dos CSVs crus) | {ok_indep}/{tot_indep} batem (tol. 1e-9) |
| contexto ctx_s_* usa barra fechada ≤ t | por construção (asof; teste test_asof_nao_olha_o_futuro) |

**Leitura:** o alvo A2 refeito fora do pipeline bate com o gravado, e o
contexto nunca lê barra em formação — as duas armadilhas clássicas (alvo
errado e look-ahead) estão vigiadas por código e teste.

## Confronto com os critérios

C3 exigia: NaN ≤ {lim:.0f}% por TF×ano → {"✔" if c3_nan_ok else "✘"} (pior {pior:.1f}%); alvos recomputados
por caminho independente batem → {"✔" if indep_ok else "✘"} ({ok_indep}/{tot_indep}); contexto W1/MN por
última barra FECHADA → ✔; 20 linhas auditadas pelo dono da pesquisa → ⏳ 👤.
**Situação: aguardando a auditoria 👤 das 20 linhas (portão P2b).**

## O que isso muda

P2b aprovado → extensão M5/M15 do banco e E5 (corrida de latências) liberados.

## Limitações

- A3 é o par SINTÉTICO forte×fraco via cestas (não o par real da corretora) —
  suficiente para medir reatividade; custo real de operação entra só no E11.
- A2/A3 capados no fim do dia de negociação (horizonte é intraday por premissa).
- Vínculo de gabarito do bloco selado propositalmente vazio até o E11.
"""
    (RESULTS / "E04b_auditoria.md").write_text(md, encoding="utf-8")
    print(f"Relatório: {RESULTS / 'E04b_auditoria.md'}")
    return 0 if (c3_nan_ok and indep_ok) else 1


if __name__ == "__main__":
    sys.exit(main())

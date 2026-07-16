"""gabarito.py — detecção dos eventos de tendência diária (E4, ESBOÇO §1.1–1.2).

💡 O que é o gabarito, em linguagem simples: o catálogo das "tendências que
realmente aconteceram" — a resposta certa da prova contra a qual toda métrica
do painel será cronometrada (E5+). Ele é construído EX-POST (com o dia inteiro
conhecido): pode olhar o futuro à vontade porque não é sinal, é régua — e por
isso NUNCA vira feature (ESBOÇO §1.5).

Definição candidata (config `event`, congela no portão P2a):
- unidade = (moeda, dia de negociação), dia = abertura de Tóquio → fechamento
  de NY (janelas congeladas em fuso IANA local; convertidas para hora do
  servidor via DST europeu medido no E1);
- caminho da cesta: por par, r(t) = ±log(close(t)/close(abertura de Tóquio)) /
  banda ATR diária (mesma banda do zMov); cesta = média dos 7 pares da moeda;
- EVENTO se |cesta no fim do dia| ≥ 1.0 (ATRs médios) E ≥ 6/7 pares fecharam o
  dia na direção da moeda E razão de eficiência de Kaufman ≥ 0.30
  (💡 |deslocamento líquido| ÷ soma dos zigue-zagues — perto de 1 andou reto);
- âncoras candidatas: A-20/10 (primeiro candle em que o acumulado atinge 20%
  da magnitude final e nunca mais recua abaixo de 10% — o "ponto sem retorno")
  e A-rompimento (último cruzamento do nível de abertura antes do trecho
  final — depois dele o caminho não volta mais ao zero).

Resolução da régua (decisão Léo 2026-07-16, adendo P2a): caminho em M30 para
TODO o período (régua única 2021→2025); M15 recalculado como SENSIBILIDADE
nos dias 2024-07+ (o config definia a A-20/10 em M15, mas M15 só existe de
2024-07 em diante — a comparação M30×M15 no E04a mede o custo da régua).

Buracos: fechamentos são ffilled DENTRO da grade (mesma semântica do iBarShift
do painel); um dia só é válido se ≥80% das barras da janela existem em todos
os pares e a banda ATR + referência de abertura existem para os 7 pares.
"""

from __future__ import annotations

from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from . import daymove

# fuso do servidor: DST europeu UTC+2/+3, medido no E1 (config
# mt5.server_timezone). Europe/Athens segue exatamente essa regra.
TZ_SERVIDOR = ZoneInfo("Europe/Athens")


def _para_servidor(datas: pd.DatetimeIndex, hora: str, tz: str) -> pd.Series:
    """Instante `hora` local `tz` de cada data → timestamp ingênuo do servidor."""
    loc = pd.DatetimeIndex([pd.Timestamp(f"{d.date()} {hora}", tz=tz) for d in datas])
    return pd.Series(loc.tz_convert(TZ_SERVIDOR).tz_localize(None), index=datas)


def janelas_dia(datas: pd.DatetimeIndex, sessions_cfg: dict, seg_slot: int
                ) -> pd.DataFrame:
    """Por data: slots [ini, fim) do dia de negociação e de cada sessão.

    Slot = índice da barra do dia (fechamento em (slot+1)×seg_slot). O slot de
    um instante t é ceil(t/seg_slot) − 1 arredondado para o FECHAMENTO ≥ t…
    convenção usada: um instante t pertence ao slot floor(t/seg_slot).
    """
    slots_dia = 86400 // seg_slot
    out = {"data": datas}

    def col(nome, hora, tz):
        srv = _para_servidor(datas, hora, tz)
        segundos = (srv.to_numpy() - datas.to_numpy()).astype("timedelta64[s]").astype(int)
        out[nome] = np.clip(segundos // seg_slot, 0, slots_dia)

    ses = sessions_cfg
    col("dia_ini", ses["toquio"]["abre"], ses["toquio"]["tz"])
    col("dia_fim", ses["ny"]["fecha"], ses["ny"]["tz"])
    for nome in ("toquio", "londres", "ny"):
        col(f"{nome}_ini", ses[nome]["abre"], ses[nome]["tz"])
        col(f"{nome}_fim", ses[nome]["fecha"], ses[nome]["tz"])
    return pd.DataFrame(out).set_index("data")


def matriz_fechamentos(closes: pd.Series, datas: pd.DatetimeIndex, seg_slot: int
                       ) -> tuple[np.ndarray, np.ndarray]:
    """(C_ffill, presente): fechamentos por (data × slot), ffilled na grade
    achatada (último fechamento conhecido ≤ aquele slot), + máscara de barras
    realmente presentes. `closes` indexado pela ABERTURA da barra."""
    slots_dia = 86400 // seg_slot
    ot = pd.DatetimeIndex(closes.index)
    dia = ot.normalize()
    slot = ((ot - dia).total_seconds() // seg_slot).astype(int)
    mat = (pd.DataFrame({"d": dia, "s": slot, "c": closes.to_numpy()})
           .pivot_table(index="d", columns="s", values="c", aggfunc="last")
           .reindex(columns=range(slots_dia)).reindex(datas))
    bruto = mat.to_numpy()
    flat = pd.Series(bruto.ravel()).ffill().to_numpy()
    return flat.reshape(bruto.shape), ~np.isnan(bruto)


def caminhos_por_moeda(frames: dict[str, pd.DataFrame], d1: dict[str, pd.DataFrame],
                       pairs: list[str], currencies: list[str], atr_len: int,
                       seg_slot: int, janelas: pd.DataFrame
                       ) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray],
                                  np.ndarray, pd.DatetimeIndex]:
    """Caminhos da cesta por moeda + sinais de fim de dia por par.

    Retorna (path: {moeda → (dias×slots) em ATRs}, fim_sinal: {moeda →
    (dias×7) sinais dos pares dela}, dia_valido: (dias,), datas).
    """
    datas = janelas.index
    slots_dia = 86400 // seg_slot
    ini = janelas["dia_ini"].to_numpy()
    fim = janelas["dia_fim"].to_numpy()
    col_idx = np.arange(slots_dia)[None, :]
    na_janela = (col_idx >= ini[:, None]) & (col_idx < fim[:, None])

    r_par: dict[str, np.ndarray] = {}
    presenca: list[np.ndarray] = []
    banda_ok = np.ones(len(datas), dtype=bool)
    for p in pairs:
        closes = frames[p]["close"].dropna()
        c, presente = matriz_fechamentos(closes, datas, seg_slot)
        banda = daymove.banda_atr_d1(d1[p].dropna(subset=["close"]), atr_len)
        b = banda.reindex(datas).to_numpy()
        # referência = último fechamento ≤ abertura de Tóquio (slot dia_ini-1,
        # via ffill — pode vir do dia anterior se a 1ª barra faltar)
        ref = c[np.arange(len(datas)), np.maximum(ini - 1, 0)]
        ref = np.where(ini >= 1, ref, np.nan)
        with np.errstate(divide="ignore", invalid="ignore"):
            r = np.log(c / ref[:, None]) / b[:, None]
        r[~((c > 0) & (ref[:, None] > 0) & (b[:, None] > 0))] = np.nan
        r_par[p] = r
        banda_ok &= ~np.isnan(b) & ~np.isnan(ref)
        # presença: fração de barras existentes DENTRO da janela do dia
        pres = np.where(na_janela, presente, np.nan)
        presenca.append(np.nanmean(pres, axis=1))

    dia_valido = banda_ok & (np.vstack(presenca).min(axis=0) >= 0.80) & (fim > ini)

    path: dict[str, np.ndarray] = {}
    fim_sinal: dict[str, np.ndarray] = {}
    ult = np.maximum(fim - 1, 0)
    linhas = np.arange(len(datas))
    for cur in currencies:
        meus = [(p, 1.0 if p[:3] == cur else -1.0)
                for p in pairs if cur in (p[:3], p[3:6])]
        acc = np.zeros((len(datas), slots_dia))
        for p, sinal in meus:
            acc += sinal * r_par[p]
        path[cur] = np.where(na_janela, acc / len(meus), np.nan)
        fim_sinal[cur] = np.stack(
            [np.sign(sinal * r_par[p][linhas, ult]) for p, sinal in meus], axis=1)
    return path, fim_sinal, dia_valido, datas


def ancora_20_10(path: np.ndarray, mag: np.ndarray,
                 atinge: float, nunca_recua: float) -> np.ndarray:
    """A-20/10 vetorizada: slot do 'ponto sem retorno' por dia (-1 se não há).

    frac = caminho/magnitude final; âncora = primeiro slot com frac ≥ `atinge`
    cujo mínimo dali até o fim ≥ `nunca_recua`.
    """
    with np.errstate(invalid="ignore", divide="ignore"):
        frac = path / mag[:, None]
    frac_rev = np.where(np.isnan(frac[:, ::-1]), np.inf, frac[:, ::-1])
    min_suf = np.minimum.accumulate(frac_rev, axis=1)[:, ::-1]   # mínimo do sufixo
    cond = (frac >= atinge) & (min_suf >= nunca_recua)
    tem = cond.any(axis=1)
    return np.where(tem, cond.argmax(axis=1), -1)


def ancora_rompimento(path: np.ndarray, mag: np.ndarray) -> np.ndarray:
    """A-rompimento vetorizada: primeiro slot APÓS o último toque/cruzamento do
    nível de abertura (frac ≤ 0) — dali em diante o caminho não volta ao zero.
    Se o caminho nunca toca o zero, âncora = primeiro slot válido do dia."""
    with np.errstate(invalid="ignore", divide="ignore"):
        frac = path / mag[:, None]
    slots = np.arange(path.shape[1])[None, :]
    errado = np.where(np.isnan(frac), False, frac <= 0.0)
    ultimo_errado = np.where(errado, slots, -1).max(axis=1)
    primeiro_valido = np.where(~np.isnan(frac), slots, np.inf).min(axis=1)
    anc = np.where(ultimo_errado >= 0, ultimo_errado + 1, primeiro_valido)
    # se o "último errado" for o fim do dia, não há âncora coerente (defesa)
    anc = np.where(anc >= path.shape[1], -1, anc)
    return anc.astype(int)


def eficiencia_kaufman(path: np.ndarray) -> np.ndarray:
    """|deslocamento líquido| ÷ soma dos |passos| do caminho (NaN ignorado).

    O caminho começa implicitamente em 0 (o nível de abertura do dia): o passo
    do zero até o primeiro ponto conta no denominador."""
    p = pd.DataFrame(path).ffill(axis=1).to_numpy()
    p0 = np.concatenate([np.zeros((p.shape[0], 1)), p], axis=1)
    primeiro = np.argmax(~np.isnan(p), axis=1)                # 1º ponto válido
    p0[np.arange(len(p)), 0] = 0.0                            # início no zero
    passos = np.abs(np.diff(np.where(np.isnan(p0), np.nan, p0), axis=1))
    # o passo 0→primeiro ponto: diff dá NaN se houver NaN antes; injeta à mão
    passos[np.arange(len(p)), primeiro] = np.abs(
        p[np.arange(len(p)), primeiro])
    soma = np.nansum(passos, axis=1)
    liq = np.abs(np.array([row[~np.isnan(row)][-1] if (~np.isnan(row)).any()
                           else np.nan for row in p]))
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(soma > 0, liq / soma, np.nan)


def detectar(path: dict[str, np.ndarray], fim_sinal: dict[str, np.ndarray],
             dia_valido: np.ndarray, datas: pd.DatetimeIndex,
             janelas: pd.DataFrame, cfg_event: dict, seg_slot: int
             ) -> pd.DataFrame:
    """Aplica a definição do evento e devolve a tabela do gabarito."""
    linhas = []
    ini = janelas["dia_ini"].to_numpy()
    fim = janelas["dia_fim"].to_numpy()
    idx_l = np.arange(len(datas))
    ult = np.maximum(fim - 1, 0)
    for cur, p in path.items():
        p_ff = pd.DataFrame(p).ffill(axis=1).to_numpy()
        mag = p_ff[idx_l, ult]
        direcao = np.sign(mag)
        alinhados = (fim_sinal[cur] == direcao[:, None]).sum(axis=1)
        er = eficiencia_kaufman(p)
        evento = (dia_valido & ~np.isnan(mag)
                  & (np.abs(mag) >= float(cfg_event["magnitude_min_atr"]))
                  & (alinhados >= int(cfg_event["unanimidade_min_pares"]))
                  & (er >= float(cfg_event["eficiencia_min"])))
        a_cfg = cfg_event["ancoras_candidatas"]["a_20_10"]
        anc_a = ancora_20_10(p_ff, mag, a_cfg["atinge_pct"] / 100.0,
                             a_cfg["nunca_recua_abaixo_pct"] / 100.0)
        anc_b = ancora_rompimento(p_ff, mag)
        # fim do evento = última ocorrência do extremo na direção do dia
        alvo = p_ff * direcao[:, None]
        alvo = np.where(np.isnan(alvo), -np.inf, alvo)
        pico = np.where(alvo >= (np.max(alvo, axis=1)[:, None] - 1e-12),
                        np.arange(p.shape[1])[None, :], -1).max(axis=1)
        for i in np.flatnonzero(evento):
            d = datas[i]
            def ts(slot):
                return d + pd.Timedelta(seconds=int(slot + 1) * seg_slot)
            sessoes = [n for n in ("toquio", "londres", "ny")
                       if not (pico[i] < janelas.iloc[i][f"{n}_ini"]
                               or max(anc_a[i], 0) >= janelas.iloc[i][f"{n}_fim"])]
            nascimento = next(
                (n for n in ("toquio", "londres", "ny")
                 if janelas.iloc[i][f"{n}_ini"] <= anc_a[i] < janelas.iloc[i][f"{n}_fim"]),
                "entre-sessões") if anc_a[i] >= 0 else "sem-âncora"
            linhas.append({
                "moeda": cur, "dia": d.date(), "direcao": int(direcao[i]),
                "magnitude_atrs": round(abs(mag[i]), 4),
                "n_pares_alinhados": int(alinhados[i]),
                "eficiencia": round(er[i], 4),
                "ancora_a2010": ts(anc_a[i]) if anc_a[i] >= 0 else pd.NaT,
                "ancora_romp": ts(anc_b[i]) if anc_b[i] >= 0 else pd.NaT,
                "fim": ts(pico[i]),
                "duracao_min_a2010": int((pico[i] - anc_a[i]) * seg_slot // 60)
                                     if anc_a[i] >= 0 else np.nan,
                "sessoes_cobertas": "+".join(sessoes),
                "sessao_nascimento": nascimento,
            })
    return pd.DataFrame(linhas).sort_values(["dia", "moeda"]).reset_index(drop=True)

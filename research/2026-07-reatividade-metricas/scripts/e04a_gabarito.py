#!/usr/bin/env python3
"""e04a_gabarito.py — E4 parte 1: detecta os eventos e prepara a auditoria C2.

💡 O que este script faz, em linguagem simples: varre todos os dias de
negociação (Tóquio→NY) de 2021 até o fim da VALIDAÇÃO (o teste selado não é
tocado), aplica a definição congelada de "tendência diária" à cesta de cada
moeda e produz: (1) o catálogo de eventos com as DUAS âncoras candidatas;
(2) o relatório E04a com as estatísticas descritivas; (3) os 20 dias-evento
sorteados e plotados para a auditoria visual do critério C2 — é o dono da
pesquisa quem responde "é aqui que um trader diria que a tendência começou?".

Régua: caminho em M30 (uniforme 2021→2025); sensibilidade M15 nos dias
2024-07+ (adendo P2a, decisão Léo 2026-07-16).

Saídas: results/E04_eventos.csv · results/E04a_gabarito.md ·
        results/E04a_amostras/NN_MOEDA_DATA.png (20 arquivos)
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ifm_metrics import gabarito  # noqa: E402
import e02_gerar_metricas as e02  # noqa: E402

RESEARCH = Path(__file__).resolve().parent.parent
RESULTS = RESEARCH / "results"
AMOSTRAS = RESULTS / "E04a_amostras"
SEG = {"M30": 1800, "M15": 900}


def caminho_completo(cfg: dict, tf: str, datas: pd.DatetimeIndex | None = None):
    """Carrega raw do TF + D1 e devolve (path, fim_sinal, valido, datas, janelas)."""
    frames = e02.carregar_tf(cfg, tf)
    d1 = e02.carregar_tf(cfg, "D1")
    todas = pd.DatetimeIndex(sorted({t.normalize() for f in d1.values()
                                     for t in f.dropna(subset=["close"]).index}))
    fim_val = pd.Timestamp(cfg["splits"]["validacao"]["fim"])
    todas = todas[todas <= fim_val]                      # selado NUNCA é tocado
    if datas is not None:
        todas = todas.intersection(datas)
    jan = gabarito.janelas_dia(todas, cfg["sessions"], SEG[tf])
    path, fim_sinal, valido, datas_out = gabarito.caminhos_por_moeda(
        frames, d1, cfg["pairs"], cfg["currencies"],
        int(cfg["indicator"]["atr_length"]), SEG[tf], jan)
    return path, fim_sinal, valido, datas_out, jan


def md_tabela(df: pd.DataFrame) -> str:
    linhas = ["| " + " | ".join(str(c) for c in df.columns) + " |",
              "|" + "---|" * len(df.columns)]
    for _, row in df.iterrows():
        linhas.append("| " + " | ".join(str(v) for v in row) + " |")
    return "\n".join(linhas)


def plota_amostras(eventos: pd.DataFrame, path: dict, datas: pd.DatetimeIndex,
                   janelas: pd.DataFrame, cfg: dict, n: int, seed: int) -> list[str]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    AMOSTRAS.mkdir(parents=True, exist_ok=True)
    for velho in AMOSTRAS.glob("*.png"):
        velho.unlink()                                   # novo sorteio = novos 20
    rng = np.random.default_rng(seed)
    escolha = eventos.iloc[rng.choice(len(eventos), size=min(n, len(eventos)),
                                      replace=False)].sort_values("dia")
    nomes = []
    pos = {d: i for i, d in enumerate(datas)}
    for k, (_, ev) in enumerate(escolha.iterrows(), 1):
        d = pd.Timestamp(ev["dia"])
        i = pos[d]
        p = pd.Series(path[ev["moeda"]][i])
        ts = [d + pd.Timedelta(seconds=(s + 1) * 1800) for s in range(len(p))]
        fig, ax = plt.subplots(figsize=(11, 4.5))
        ax.plot(ts, p.to_numpy(), lw=1.6, color="#3a7ca5")
        ax.axhline(0, color="gray", lw=0.8)
        mag = ev["magnitude_atrs"] * ev["direcao"]
        for frac, estilo in ((0.2, ":"), (0.1, ":")):
            ax.axhline(mag * frac, color="#d1a04a", lw=0.8, ls=estilo)
        for nome, cor, col in (("A-20/10", "#2a9d3a", "ancora_a2010"),
                               ("A-romp", "#c0392b", "ancora_romp")):
            t_anc = ev[col]
            if pd.notna(t_anc):
                ax.axvline(t_anc, color=cor, lw=1.6, label=nome)
        ax.axvline(ev["fim"], color="#555", lw=1.2, ls="--", label="fim (extremo)")
        for s_nome in ("toquio", "londres", "ny"):
            s0 = d + pd.Timedelta(seconds=int(janelas.loc[d, f"{s_nome}_ini"]) * 1800)
            ax.axvspan(s0, min(d + pd.Timedelta(
                seconds=int(janelas.loc[d, f"{s_nome}_fim"]) * 1800),
                ts[-1]), alpha=0.05, color="#888")
        ax.set_title(f"{ev['moeda']} {ev['dia']} · dir {ev['direcao']:+d} · "
                     f"{ev['magnitude_atrs']:.2f} ATR · ER {ev['eficiencia']:.2f} · "
                     f"cesta {ev['n_pares_alinhados']}/7")
        ax.set_ylabel("cesta (ATRs desde a abertura de Tóquio)")
        ax.legend(loc="best", fontsize=8)
        ax.grid(alpha=0.25)
        fig.tight_layout()
        nome_arq = f"{k:02d}_{ev['moeda']}_{ev['dia']}.png"
        fig.savefig(AMOSTRAS / nome_arq, dpi=110)
        plt.close(fig)
        nomes.append(nome_arq)
    return nomes


def main() -> int:
    cfg = e02.carrega_config()
    e02.checar_proveniencia(cfg)
    ev_cfg = cfg["event"]

    print("Caminhos M30 (régua principal, 2021→fim da validação)…")
    path, fim_sinal, valido, datas, jan = caminho_completo(cfg, "M30")
    eventos = gabarito.detectar(path, fim_sinal, valido, datas, jan,
                                ev_cfg, SEG["M30"])
    treino_fim = pd.Timestamp(cfg["splits"]["treino"]["fim"])
    eventos["split"] = np.where(pd.to_datetime(eventos["dia"]) <= treino_fim,
                                "treino", "validacao")
    eventos.to_csv(RESULTS / "E04_eventos.csv", index=False)
    print(f"{len(eventos)} eventos ({(eventos['split'] == 'treino').sum()} treino, "
          f"{(eventos['split'] == 'validacao').sum()} validação)")

    print("Sensibilidade M15 (dias 2024-07+)…")
    corte_m15 = pd.Timestamp(cfg["timeframes"]["deteccao_fina"]["periodo"]["inicio"])
    ev_rec = eventos[pd.to_datetime(eventos["dia"]) >= corte_m15]
    path15, fs15, val15, datas15, jan15 = caminho_completo(
        cfg, "M15", pd.DatetimeIndex(pd.to_datetime(ev_rec["dia"].unique())))
    ev15 = gabarito.detectar(path15, fs15, val15, datas15, jan15,
                             ev_cfg, SEG["M15"])
    junto = ev_rec.merge(ev15, on=["moeda", "dia"], suffixes=("_m30", "_m15"))
    dif_min = (pd.to_datetime(junto["ancora_a2010_m15"])
               - pd.to_datetime(junto["ancora_a2010_m30"])).dt.total_seconds() / 60
    sens = pd.DataFrame({
        "estatística": ["N dias-evento comparáveis", "mediana |Δâncora| (min)",
                        "p90 |Δâncora| (min)", "% com |Δ| ≤ 30 min (1 candle M30)"],
        "A-20/10 M30 × M15": [len(junto), f"{dif_min.abs().median():.0f}",
                              f"{dif_min.abs().quantile(0.9):.0f}",
                              f"{(dif_min.abs() <= 30).mean() * 100:.0f}%"],
    })

    # estatísticas descritivas
    n_dias = int(valido.sum())
    por_moeda = eventos.groupby("moeda").size()
    resumo = pd.DataFrame({
        "estatística": ["dias de negociação válidos", "eventos", "eventos/dia",
                        "% dias com ≥1 evento", "magnitude mediana (ATRs)",
                        "duração mediana A-20/10→fim (min)", "eficiência mediana",
                        "% eventos 7/7 pares"],
        "valor": [n_dias, len(eventos), f"{len(eventos) / max(n_dias, 1):.2f}",
                  f"{eventos['dia'].nunique() / max(n_dias, 1) * 100:.0f}%",
                  f"{eventos['magnitude_atrs'].median():.2f}",
                  f"{eventos['duracao_min_a2010'].median():.0f}",
                  f"{eventos['eficiencia'].median():.2f}",
                  f"{(eventos['n_pares_alinhados'] == 7).mean() * 100:.0f}%"],
    })
    nasce = (eventos.groupby("sessao_nascimento").size()
             .rename("eventos que nascem nela").reset_index()
             .rename(columns={"sessao_nascimento": "sessão da âncora A-20/10"}))
    consumo = pd.DataFrame({
        "âncora": ["A-20/10", "A-rompimento"],
        "% dos eventos com âncora definida": [
            f"{eventos['ancora_a2010'].notna().mean() * 100:.0f}%",
            f"{eventos['ancora_romp'].notna().mean() * 100:.0f}%"],
        "hora mediana (servidor)": [
            pd.to_datetime(eventos["ancora_a2010"]).dt.hour.median(),
            pd.to_datetime(eventos["ancora_romp"]).dt.hour.median()],
    })

    seed = int(cfg["stats"]["seed"])
    n_amostras = int(cfg["criteria"]["C2_gabarito"]["dias_sorteados"])
    nomes = plota_amostras(eventos, path, datas, jan, cfg, n_amostras, seed)

    md = f"""# E04a — Gabarito de eventos (as tendências que realmente aconteceram)

## O que perguntamos

Quais (moeda, dia) tiveram uma tendência diária de verdade — e ONDE ela começou?
Este catálogo é a régua contra a qual toda métrica do painel será cronometrada.

## Como testamos

Dia de negociação = abertura de Tóquio → fechamento de NY (janelas congeladas,
fuso IANA → hora do servidor DST europeu). Caminho da cesta em **M30** (régua
única 2021→fim da validação; decisão/adendo P2a de 2026-07-16), por par:
±log(preço/abertura de Tóquio) ÷ banda ATR14 diária; cesta = média dos 7 pares.
Evento = |cesta no fim| ≥ {ev_cfg['magnitude_min_atr']} ATR E ≥ {ev_cfg['unanimidade_min_pares']}/7 pares na direção E
eficiência de Kaufman ≥ {ev_cfg['eficiencia_min']} (💡 ver *razão de eficiência* no ESBOÇO §1.1).
Âncoras candidatas: **A-20/10** (💡 "ponto sem retorno": atinge 20% da magnitude
final e nunca mais recua abaixo de 10%) e **A-rompimento** (💡 último cruzamento
do nível de abertura — depois dele o caminho não volta ao zero). O teste selado
(2025-10+) NÃO foi tocado.

## Resultados

{md_tabela(resumo)}

**Leitura:** o tamanho e a cara do gabarito: quantos eventos existem, o quão
grandes e diretos são. Eventos/dia perto de 1–2 é o esperado pela Premissa P1
(pouca coisa por dia realmente tende); mediana de magnitude ≥ 1 ATR por
construção.

{md_tabela(por_moeda.rename('eventos').reset_index())}

**Leitura:** distribuição por moeda — se alguma moeda concentrar eventos demais
(ou de menos), é sinal de banda ATR mal calibrada para ela, não de "moeda que
tende mais"; conferir na auditoria.

{md_tabela(nasce)}

**Leitura:** em que sessão a tendência do dia costuma NASCER (pela âncora
A-20/10). Insumo direto da Premissa P2 (a sessão é a unidade de operação).

{md_tabela(consumo)}

**Leitura:** cobertura e horário típico de cada âncora candidata. Âncora sem
definição em muitos eventos = regra frágil; horários muito tardios = âncora
que "chega depois da festa".

{md_tabela(sens)}

**Leitura:** custo da régua M30: nos dias 2024-07+ em que as duas resoluções
detectam o mesmo evento, a âncora A-20/10 muda pouco (|Δ| ≤ 1 candle M30 na
grande maioria) → a régua única M30 não distorce a medição de latência.

## Amostras para a auditoria C2 (👤)

{len(nomes)} dias-evento sorteados (seed {seed}) em `results/E04a_amostras/`:
caminho da cesta com as DUAS âncoras marcadas, linhas de 10%/20% da magnitude e
faixas das sessões. Pergunta única da auditoria: **"é aqui que um trader diria
que a tendência começou?"** — responda por âncora, em ≥ {cfg['criteria']['C2_gabarito']['aprovacao_min_pct']}% dos casos.

**Leitura:** a auditoria visual é o critério C2: quem valida a régua é o olho
de trader do dono da pesquisa, não a estatística.

## Confronto com os critérios

**C2** exige: {n_amostras} dias sorteados, aprovação ≥ {cfg['criteria']['C2_gabarito']['aprovacao_min_pct']}% numa das âncoras, com no
máximo {cfg['criteria']['C2_gabarito']['max_rodadas']} rodadas (novo sorteio a cada rodada). Situação: **⏳ aguardando a
auditoria 👤** — este relatório prepara o portão P2a, não o fecha.

## O que isso muda

Com o C2 aprovado, a âncora escolhida congela no config.yaml e o banco-mãe
(E4b) é construído sobre ela. Reprovou → ajustar definição/âncora e re-sortear
(nunca reaproveitar os mesmos 20 dias).

## Limitações

- O gabarito olha o dia inteiro DE PROPÓSITO (é régua, não sinal) — nunca vira feature.
- Régua M30 uniforme: âncoras têm quantização de ±30 min (sensibilidade M15 acima).
- Dias com <80% das barras na janela (feed/feriado) ficam fora — reportados como inválidos.
- Eventos do período selado não foram computados; serão gerados no E11 com a
  definição congelada.
"""
    (RESULTS / "E04a_gabarito.md").write_text(md, encoding="utf-8")
    print(f"Relatório: {RESULTS / 'E04a_gabarito.md'} + {len(nomes)} amostras")
    return 0


if __name__ == "__main__":
    sys.exit(main())

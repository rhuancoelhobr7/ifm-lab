# ExportGoldenIFM — export do replay do indicador (Etapa E3 / portão P1)

Script MQL5 que gera os **valores-verdade (golden)** da verificação de paridade:
os números que o painel do IFM v1.0 calcularia, gravados em CSV para comparar
ponto a ponto com a reimplementação Python da pesquisa (critério **C1**).

💡 **Por que essa ferramenta existe:** paridade é comparar duas calculadoras.
A "calculadora original" é o indicador — mas ele só desenha na tela, não grava
nada. Este script contém uma **cópia literal** das funções de cálculo do
`src/IFM.mq5` v1.0 (IFM Light, força S, vel/acel/zvel, zS, cesta, mtf, VETO,
rank H1, zMov/zHist) e as executa sobre o histórico, despejando os resultados
em CSV com todos os parâmetros registrados (`golden_meta.csv`) — proveniência
nunca mais é mistério. *(Os `golden_*.csv` antigos que apareceram no primeiro
export eram de uma ferramenta da geração V2 do projeto, anterior a esta
pesquisa, e foram descartados por origem desconhecida.)*

## Como rodar (mesmo fluxo do exportador de barras)

1. Copiar `ExportGoldenIFM.mq5` para a pasta `Scripts` do MetaEditor e compilar (`F7`).
2. **Estar logado na conta MetaQuotes-Demo** (a mesma dos dados da pesquisa).
3. Arrastar o script para um gráfico qualquer; aceitar os parâmetros default
   (são os defaults da v1.0 — não mexer, a paridade compara contra eles).
4. Aguardar (minutos; o progresso aparece no gráfico).
5. Copiar os 5 arquivos de `MQL5\Files\IFM_golden\` para
   `research/2026-07-reatividade-metricas/data/raw/`.
6. Avisar o Claude Code → ele roda a comparação e gera `results/E03_paridade.md`.

## O que sai

| Arquivo | Conteúdo | Âncora |
|---|---|---|
| `golden_meta.csv` | ferramenta, data, servidor, offset, TODOS os parâmetros | — |
| `golden_strength.csv` | S por moeda × TF (M30,H1,H4,D1) × âncora 1..80 | por shift |
| `golden_derivadas.csv` | vel, acel, zvel, zS, cesta idem | por shift |
| `golden_pares.csv` | IFM Light por par × TF × âncora (localiza divergências) | por shift |
| `golden_cross.csv` | cadeia cruzada: S dos 4 TFs, zS, mtf, VETO, rank H1, zMov, zHist, candidata (12 amostras de tempo) | por tempo (replay) |

NaN do painel é gravado como `nan` — a regra C1 exige que os NaN do Python
caiam nos MESMOS pontos.

⚠ **Se `src/IFM.mq5` mudar, este script precisa ser regenerado** — a cópia
literal é a garantia da paridade, e cópia desatualizada é paridade contra a
versão errada.

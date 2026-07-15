# ExportBarsG8 — exportador de barras (Etapa E1 da pesquisa reatividade-metricas)

Script MQL5 que exporta as barras (OHLC + tick volume) dos **28 pares G8** em
**8 timeframes** (M5, M15, M30, H1, H4, D1, W1, MN1) para arquivos CSV — a
matéria-prima da pesquisa `research/2026-07-reatividade-metricas/`.

💡 **O que ele faz, em uma frase:** para cada par e cada timeframe, ele pede ao
MetaTrader o histórico de velas do período configurado e grava tudo num arquivo
de texto simples (CSV), um arquivo por par×TF — 224 arquivos no total — mais um
`_manifest.csv` que resume o que foi exportado e anota a diferença entre o
relógio do servidor e o GMT (usada depois para calibrar as sessões).

## Passo a passo (não precisa saber programar)

1. **Abra o MetaEditor:** no MetaTrader 5, aperte `F4` (ou menu Ferramentas →
   Editor de Linguagem MetaQuotes).
2. **Copie o script para dentro:** no painel esquerdo do MetaEditor (Navegador),
   clique com o botão direito em `Scripts` → `Abrir pasta`. Copie o arquivo
   `ExportBarsG8.mq5` para lá.
3. **Compile:** de volta ao MetaEditor, abra o arquivo copiado e aperte `F7`.
   Deve aparecer `0 errors, 0 warnings` na aba de baixo. Se aparecer erro ou
   warning, copie a mensagem e reporte.
4. **Prepare o terminal (uma vez só):**
   - Ferramentas → Opções → aba **Gráficos** → "Máximo de barras no gráfico" =
     **Unlimited** (ou o maior valor disponível). Sem isso o histórico vem cortado.
   - Confira que está conectado ao servidor (canto inferior direito verde).
5. **Rode o script:** no MetaTrader, abra um gráfico qualquer (ex.: EURUSD),
   ache `ExportBarsG8` no Navegador (`Ctrl+N`, seção Scripts) e **arraste para o
   gráfico**. Vai abrir a janela de parâmetros — os valores padrão já são os da
   pesquisa (períodos por camada de TF). Clique OK.
6. **Aguarde.** O progresso aparece no canto superior esquerdo do gráfico
   (`12/224 EURUSD H1 ...`) e no diário (aba "Especialistas"). A primeira rodada
   pode demorar: o MT5 baixa histórico aos poucos.
7. **Se houver FALHAS** (o resumo final no diário diz quantas): **rode o script
   de novo**, com o parâmetro "Pular arquivos que ja existem" = `true` (padrão).
   Ele só refaz o que faltou. Repita até o resumo dizer `0 falhas`.
8. **Pegue os arquivos:** no MetaTrader, Arquivo → **Abrir Pasta de Dados** →
   pasta `MQL5` → `Files` → `IFM_export`. Lá estão os 224 CSVs + `_manifest.csv`.
9. **Copie tudo** (incluindo o `_manifest.csv`) para:
   `research/2026-07-reatividade-metricas/data/raw/`
   (essa pasta é gitignorada — os dados brutos não sobem para o repo, regra 4 do
   CLAUDE.md).
10. **Avise o Claude Code** para rodar o inventário de cobertura
    (`scripts/e01_inventario.py`), que confere buracos e gera o relatório
    `results/E01_inventario.md` — inclusive a figura que calibra as sessões no
    horário do servidor.

## Parâmetros (defaults = config.yaml da pesquisa)

| Parâmetro | Default | O que é |
|---|---|---|
| Inicio MN e W1 | 2016-01-01 | Camada de contexto (leve, histórico longo) |
| Inicio D1, H4, H1, M30 | 2021-01-01 | Contexto próximo + detecção longa |
| Inicio M15 e M5 | 2024-07-01 | Detecção fina (2 anos, pelo volume de dados) |
| Fim | 2026-06-30 | Comum a todos os TFs |
| TFs a exportar | M5…MN1 | Pode reduzir para reexportar um TF específico |
| Subpasta | IFM_export | Dentro de MQL5\Files |
| Pular arquivos que ja existem | true | Rodadas seguintes só completam o que falta |

## Formato dos CSVs

Uma linha por barra, do mais antigo para o mais novo:

```
time_epoch,time_server,open,high,low,close,tick_volume,spread
1719878400,2024.07.02 00:00,1.07435,1.07461,1.07398,1.07422,1543,12
```

- `time_epoch`: hora de ABERTURA da barra em segundos Unix, **no fuso do servidor**
  (é o `time` cru do MT5; a conversão para UTC usa o offset do `_manifest.csv`).
- `time_server`: a mesma hora, legível.
- `spread`: o MT5 **não guarda spread histórico confiável em barras** — a coluna
  vem por completude, mas o custo por par entra na pesquisa como constante
  documentada (limitação registrada no ESBOÇO, Q10).

## Solução de problemas

- **`FALHA` persistente num par×TF:** abra um gráfico daquele par naquele TF e
  role para trás (Ctrl+End, depois arraste) para forçar o download do histórico;
  rode o script de novo.
- **Poucos anos de M5/M15:** normal — brokers limitam histórico fino. O
  inventário reporta a cobertura real e a pesquisa registra a limitação.
- **Menos de 28 pares detectados:** confira no Observatório de Mercado
  (Ctrl+M → botão direito → "Mostrar Todos") que os cruzados existem na conta.

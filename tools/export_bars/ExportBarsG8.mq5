//+------------------------------------------------------------------+
//|                                               ExportBarsG8.mq5   |
//|  ifm-lab · Pesquisa 2026-07-reatividade-metricas · Etapa E1      |
//|                                                                  |
//|  v2.00 — exporta TUDO DO ZERO, em duas fases por serie:          |
//|    1) SINCRONIZA: pede a serie ao terminal e ESPERA o download   |
//|       do historico profundo terminar (progresso no grafico e no  |
//|       diario; paciencia configuravel, default 5 min por serie).  |
//|       Era aqui que as versoes anteriores falhavam: com o cache   |
//|       frio (troca de servidor), o CopyRates era chamado antes de |
//|       o historico existir localmente e travava ou desistia.      |
//|    2) COPIA: com a serie ja local, CopyRates em fatias anuais    |
//|       (rapido e sem bloqueio) e grava o CSV.                     |
//|                                                                  |
//|  Exporta OHLC + tick volume dos 28 pares G8 nos TFs M5, M15,     |
//|  M30, H1, H4, D1, W1, MN1 — um CSV por par × TF em               |
//|  MQL5\Files\<InpFolder>\ + _manifest.csv (resumo + offset        |
//|  servidor↔GMT). Esquema identico ao consumido pelo               |
//|  e01_inventario.py. NAO toca em arquivos de outros nomes         |
//|  (golden_*.csv, server_meta.csv).                                |
//|                                                                  |
//|  Periodos por camada (espelham o config.yaml da pesquisa):       |
//|    MN, W1 .............. InpFromCtx  (default 2016-01-01)        |
//|    D1, H4, H1, M30 ..... InpFromMid  (default 2021-01-01)        |
//|    M15, M5 ............. InpFromFine (default 2024-07-01)        |
//|                                                                  |
//|  DEFAULTS = "tudo do zero": sobrescreve os CSVs existentes.      |
//|  Se precisar interromper e retomar, rode de novo com             |
//|  "Pular arquivos que ja existem" = true.                         |
//|                                                                  |
//|  Uso passo a passo para leigos: ver README.md nesta pasta.       |
//+------------------------------------------------------------------+
#property copyright   "ifm-lab"
#property version     "2.00"
#property description "Exporta barras dos 28 pares G8 (8 TFs) para CSV, sincronizando o historico antes"
#property script_show_inputs

input datetime InpFromCtx     = D'2016.01.01 00:00';               // Inicio MN e W1
input datetime InpFromMid     = D'2021.01.01 00:00';               // Inicio D1, H4, H1, M30
input datetime InpFromFine    = D'2024.07.01 00:00';               // Inicio M15 e M5
input datetime InpTo          = D'2026.06.30 23:59';               // Fim (comum a todos os TFs)
input string   InpTFs         = "M5,M15,M30,H1,H4,D1,W1,MN1";      // TFs a exportar (separados por virgula)
input string   InpFolder      = "IFM_export";                      // Subpasta em MQL5\Files
input bool     InpOnlyMissing = false;                             // Pular arquivos que ja existem (retomada)
input int      InpSyncTimeout = 300;                               // Paciencia p/ baixar historico (seg por serie)

//--- moedas G8, na mesma ordem do indicador (g_cur em src/IFM.mq5)
string g_cur[8] = {"USD","EUR","GBP","JPY","CHF","CAD","AUD","NZD"};

//+------------------------------------------------------------------+
int CurIdx(const string c)
  {
   for(int i = 0; i < 8; i++)
      if(c == g_cur[i])
         return i;
   return -1;
  }

//+------------------------------------------------------------------+
ENUM_TIMEFRAMES TfFromName(const string name)
  {
   if(name == "M5")                    return PERIOD_M5;
   if(name == "M15")                   return PERIOD_M15;
   if(name == "M30")                   return PERIOD_M30;
   if(name == "H1")                    return PERIOD_H1;
   if(name == "H4")                    return PERIOD_H4;
   if(name == "D1")                    return PERIOD_D1;
   if(name == "W1")                    return PERIOD_W1;
   if(name == "MN" || name == "MN1")   return PERIOD_MN1;
   return PERIOD_CURRENT; // sinaliza nome invalido
  }

//+------------------------------------------------------------------+
datetime FromForTf(const ENUM_TIMEFRAMES tf)
  {
   if(tf == PERIOD_MN1 || tf == PERIOD_W1)  return InpFromCtx;
   if(tf == PERIOD_M15 || tf == PERIOD_M5)  return InpFromFine;
   return InpFromMid;
  }

//+------------------------------------------------------------------+
datetime Jan1(const int year)
  {
   return StringToTime(StringFormat("%04d.01.01 00:00", year));
  }

//+------------------------------------------------------------------+
//| Detecta os pares G8 no Observatorio (mesma logica do IFM.mq5)    |
//+------------------------------------------------------------------+
int DetectG8Pairs(string &pairs[])
  {
   bool seen[64];
   for(int i = 0; i < 64; i++) seen[i] = false;
   int n = 0;
   int total = SymbolsTotal(false);
   for(int s = 0; s < total; s++)
     {
      string sym = SymbolName(s, false);
      int bi = CurIdx(SymbolInfoString(sym, SYMBOL_CURRENCY_BASE));
      int qi = CurIdx(SymbolInfoString(sym, SYMBOL_CURRENCY_PROFIT));
      if(bi < 0 || qi < 0 || bi == qi) continue;
      int key = (bi < qi) ? bi*8 + qi : qi*8 + bi;
      if(seen[key]) continue;
      if(!SymbolSelect(sym, true)) continue;
      ArrayResize(pairs, n + 1);
      pairs[n] = sym;
      n++;
      seen[key] = true;
     }
   return n;
  }

//+------------------------------------------------------------------+
//| FASE 1 — sincroniza o historico da serie ate 'from'.             |
//| Cutuca o download com CopyTime e espera, reportando progresso.   |
//| Retorno:  1 = historico cobre 'from';                            |
//|           0 = server nao tem tao fundo OU download estagnou —    |
//|               'from' e ajustado para a 1a barra disponivel;      |
//|          -1 = timeout sem nenhuma barra local (falha).           |
//+------------------------------------------------------------------+
int SyncHistory(const string sym, const ENUM_TIMEFRAMES tf, const string tfName,
                datetime &from, const string progresso)
  {
   ulong deadline    = GetTickCount64() + (ulong)InpSyncTimeout * 1000;
   ulong lastImprove = GetTickCount64();
   datetime lastFirst = 0;

   while(!IsStopped())
     {
      datetime first    = (datetime)SeriesInfoInteger(sym, tf, SERIES_FIRSTDATE);
      datetime srvFirst = (datetime)SeriesInfoInteger(sym, tf, SERIES_SERVER_FIRSTDATE);

      if(first > 0 && first <= from)
         return 1; // historico local ja cobre o periodo pedido

      // o SERVIDOR nao tem historico tao fundo: aceita a partir do que existe
      if(first > 0 && srvFirst > 0 && srvFirst > from &&
         (long)first <= (long)srvFirst + PeriodSeconds(tf))
        {
         from = first;
         return 0;
        }

      // cutuca o download: pedir 1 barra na data alvo dispara a sincronizacao
      datetime tmp[];
      CopyTime(sym, tf, from, 1, tmp);

      if(first != lastFirst && first > 0)
        {
         lastFirst = first;
         lastImprove = GetTickCount64();
        }

      Comment(StringFormat("ExportBarsG8 %s | sincronizando %s %s\n1a barra local: %s | alvo: %s | restam %ds",
                           progresso, sym, tfName,
                           (first > 0) ? TimeToString(first, TIME_DATE) : "(nenhuma ainda)",
                           TimeToString(from, TIME_DATE),
                           (int)((deadline - GetTickCount64()) / 1000)));

      // download parou de avancar ha 60s mas JA ha barras: exporta o que ha
      if(first > 0 && GetTickCount64() - lastImprove > 60000)
        {
         PrintFormat("ExportBarsG8: %s %s — download estagnou; exportando desde %s (parcial).",
                     sym, tfName, TimeToString(first, TIME_DATE));
         from = first;
         return 0;
        }
      if(GetTickCount64() > deadline)
         return (first > 0) ? 0 : -1;

      Sleep(1000);
     }
   return -1;
  }

//+------------------------------------------------------------------+
//| FASE 2 — CopyRates de uma fatia (serie ja sincronizada).         |
//| Retorno: n>0 barras; 0 = fatia vazia; -1 = falha apos retries.   |
//+------------------------------------------------------------------+
int CopyChunk(const string sym, const ENUM_TIMEFRAMES tf,
              const datetime from, const datetime to, MqlRates &rates[])
  {
   for(int attempt = 1; attempt <= 20 && !IsStopped(); attempt++)
     {
      ResetLastError();
      int copied = CopyRates(sym, tf, from, to, rates);
      if(copied >= 0) return copied;
      Sleep(500);
     }
   return -1;
  }

//+------------------------------------------------------------------+
//| Exporta um par × TF. rows=-1: pulado (ja existia).               |
//| status de saida: ok | ok_parcial_... | pulado_existia | FALHA... |
//+------------------------------------------------------------------+
bool ExportOne(const string sym, const ENUM_TIMEFRAMES tf, const string tfName,
               const string progresso,
               int &rows, datetime &firstBar, datetime &lastBar,
               string &file, string &status)
  {
   rows = 0; firstBar = 0; lastBar = 0; status = "ok";
   file = InpFolder + "\\" + sym + "_" + tfName + ".csv";

   if(InpOnlyMissing && FileIsExist(file)) { rows = -1; status = "pulado_existia"; return true; }

   //--- FASE 1: garantir o historico local
   datetime from = FromForTf(tf);
   int sync = SyncHistory(sym, tf, tfName, from, progresso);
   if(sync < 0)
     {
      status = "FALHA_sync";
      PrintFormat("ExportBarsG8: FALHA de sincronizacao em %s %s — rode de novo depois "
                  "(com 'Pular arquivos' = true para retomar).", sym, tfName);
      return false;
     }
   if(sync == 0)
      status = "ok_parcial_desde_" + TimeToString(from, TIME_DATE);

   //--- FASE 2: copiar em fatias anuais e gravar
   int digits = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
   int h = FileOpen(file, FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(h == INVALID_HANDLE)
     {
      status = "FALHA_arquivo";
      PrintFormat("ExportBarsG8: nao consegui criar %s (erro %d).", file, GetLastError());
      return false;
     }
   FileWrite(h, "time_epoch,time_server,open,high,low,close,tick_volume,spread");

   MqlDateTime st;
   TimeToStruct(from, st);
   datetime lastWritten = 0;

   for(int year = st.year; year <= 2100 && !IsStopped(); year++)
     {
      datetime a = from > Jan1(year) ? from : Jan1(year);
      datetime b = InpTo < Jan1(year + 1) ? InpTo : (datetime)((long)Jan1(year + 1) - 1);
      if(a > InpTo) break;

      Comment(StringFormat("ExportBarsG8 %s | copiando %s %s — %d", progresso, sym, tfName, year));

      MqlRates rates[];
      int copied = CopyChunk(sym, tf, a, b, rates);
      if(copied < 0)
        {
         FileClose(h);
         FileDelete(file); // arquivo parcial fora — a proxima rodada refaz inteiro
         status = "FALHA_copy";
         PrintFormat("ExportBarsG8: FALHA de copia em %s %s (fatia %d, erro %d).",
                     sym, tfName, year, GetLastError());
         return false;
        }
      for(int i = 0; i < copied; i++)
        {
         if(rates[i].time <= lastWritten) continue; // dedup na emenda das fatias
         FileWrite(h, StringFormat("%I64d,%s,%s,%s,%s,%s,%I64d,%d",
                                   (long)rates[i].time,
                                   TimeToString(rates[i].time, TIME_DATE|TIME_MINUTES),
                                   DoubleToString(rates[i].open,  digits),
                                   DoubleToString(rates[i].high,  digits),
                                   DoubleToString(rates[i].low,   digits),
                                   DoubleToString(rates[i].close, digits),
                                   rates[i].tick_volume,
                                   (int)rates[i].spread));
         lastWritten = rates[i].time;
         if(firstBar == 0) firstBar = rates[i].time;
         lastBar = rates[i].time;
         rows++;
        }
     }
   FileClose(h);

   if(rows == 0)
     {
      FileDelete(file);
      status = "FALHA_vazio";
      PrintFormat("ExportBarsG8: %s %s veio VAZIO (broker sem historico no periodo).", sym, tfName);
      return false;
     }
   return true;
  }

//+------------------------------------------------------------------+
void OnStart()
  {
   //--- pares
   string pairs[];
   int np = DetectG8Pairs(pairs);
   if(np == 0)
     {
      Alert("ExportBarsG8: nenhum par G8 encontrado no Observatorio de Mercado.");
      return;
     }
   if(np != 28)
      PrintFormat("ExportBarsG8: AVISO — %d pares G8 detectados (esperados 28). Prosseguindo.", np);

   //--- TFs
   string tfNames[];
   int ntf = StringSplit(InpTFs, ',', tfNames);
   if(ntf <= 0)
     {
      Alert("ExportBarsG8: lista de TFs vazia ou invalida: ", InpTFs);
      return;
     }
   for(int t = 0; t < ntf; t++)
     {
      StringTrimLeft(tfNames[t]);
      StringTrimRight(tfNames[t]);
      if(TfFromName(tfNames[t]) == PERIOD_CURRENT)
        {
         Alert("ExportBarsG8: TF desconhecido: '", tfNames[t], "'. Use M5,M15,M30,H1,H4,D1,W1,MN1.");
         return;
        }
     }

   //--- manifest (resumo + offset servidor↔GMT para a calibracao das sessoes)
   double offsetH = ((double)((long)TimeTradeServer() - (long)TimeGMT())) / 3600.0;
   int hm = FileOpen(InpFolder + "\\_manifest.csv", FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(hm == INVALID_HANDLE)
     {
      Alert("ExportBarsG8: nao consegui criar o _manifest.csv (erro ", GetLastError(), ").");
      return;
     }
   FileWrite(hm, StringFormat("# ExportBarsG8 v2.00 | exportado_em_local=%s",
                              TimeToString(TimeLocal(), TIME_DATE|TIME_SECONDS)));
   FileWrite(hm, StringFormat("# server_time=%s | gmt_time=%s | offset_server_gmt_h=%.1f",
                              TimeToString(TimeTradeServer(), TIME_DATE|TIME_SECONDS),
                              TimeToString(TimeGMT(),         TIME_DATE|TIME_SECONDS),
                              offsetH));
   FileWrite(hm, StringFormat("# broker=%s | conta_servidor=%s",
                              TerminalInfoString(TERMINAL_COMPANY),
                              AccountInfoString(ACCOUNT_SERVER)));
   FileWrite(hm, "symbol,tf,rows,first_bar,last_bar,status,file");

   //--- exporta tudo
   int total = np * ntf, done = 0, nOk = 0, nParcial = 0, nSkip = 0, nFail = 0;
   for(int p = 0; p < np && !IsStopped(); p++)
     {
      for(int t = 0; t < ntf && !IsStopped(); t++)
        {
         done++;
         string progresso = StringFormat("%d/%d (ok=%d parciais=%d pulados=%d falhas=%d)",
                                         done, total, nOk, nParcial, nSkip, nFail);

         int rows; datetime fb, lb; string file, status;
         bool ok = ExportOne(pairs[p], TfFromName(tfNames[t]), tfNames[t], progresso,
                             rows, fb, lb, file, status);

         if(!ok)                                      nFail++;
         else if(rows == -1)                          nSkip++;
         else if(StringFind(status, "parcial") >= 0)  nParcial++;
         else                                         nOk++;

         FileWrite(hm, StringFormat("%s,%s,%d,%s,%s,%s,%s",
                                    pairs[p], tfNames[t], rows,
                                    (fb > 0) ? TimeToString(fb, TIME_DATE|TIME_MINUTES) : "",
                                    (lb > 0) ? TimeToString(lb, TIME_DATE|TIME_MINUTES) : "",
                                    status, file));
        }
     }
   FileClose(hm);
   Comment("");

   PrintFormat("ExportBarsG8 v2.00: FIM — %d ok, %d parciais, %d pulados, %d falhas (de %d).",
               nOk, nParcial, nSkip, nFail, total);
   if(nFail > 0)
      Print("ExportBarsG8: houve FALHAS — rode de novo com 'Pular arquivos que ja existem' = true "
            "para retomar so o que faltou.");
   if(nParcial > 0)
      Print("ExportBarsG8: series PARCIAIS (broker sem historico ate o inicio pedido) estao marcadas "
            "no _manifest.csv — o inventario (e01) vai reportar a cobertura real.");
   if(nFail == 0)
      Print("ExportBarsG8: exporte concluido. Copie a pasta MQL5\\Files\\", InpFolder,
            " para research/2026-07-reatividade-metricas/data/raw/ (ver README).");
  }
//+------------------------------------------------------------------+

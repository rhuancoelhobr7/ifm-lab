//+------------------------------------------------------------------+
//|                                               ExportBarsG8.mq5   |
//|  ifm-lab · Pesquisa 2026-07-reatividade-metricas · Etapa E1      |
//|                                                                  |
//|  Exporta OHLC + tick volume dos 28 pares G8 para CSV, nos TFs    |
//|  M5, M15, M30, H1, H4, D1, W1, MN1 (um arquivo por par × TF).    |
//|  Saída em MQL5\Files\<InpFolder>\, mais um _manifest.csv com o   |
//|  resumo de cada arquivo e o offset servidor↔GMT no momento do    |
//|  export (usado na calibração das sessões — config.yaml).         |
//|                                                                  |
//|  Períodos por camada (espelham o config.yaml da pesquisa):       |
//|    MN, W1 .............. InpFromCtx  (default 2016-01-01)        |
//|    D1, H4, H1, M30 ..... InpFromMid  (default 2021-01-01)        |
//|    M15, M5 ............. InpFromFine (default 2024-07-01)        |
//|                                                                  |
//|  Uso passo a passo para leigos: ver README.md nesta pasta.       |
//+------------------------------------------------------------------+
#property copyright   "ifm-lab"
#property version     "1.10"  // v1.10: fatias anuais no CopyRates (corrige travamento em W1/MN 2016)
#property description "Exporta barras dos 28 pares G8 (8 TFs) para CSV — pesquisa reatividade-metricas (E1)"
#property script_show_inputs

input datetime InpFromCtx     = D'2016.01.01 00:00';               // Inicio MN e W1
input datetime InpFromMid     = D'2021.01.01 00:00';               // Inicio D1, H4, H1, M30
input datetime InpFromFine    = D'2024.07.01 00:00';               // Inicio M15 e M5
input datetime InpTo          = D'2026.06.30 23:59';               // Fim (comum a todos os TFs)
input string   InpTFs         = "M5,M15,M30,H1,H4,D1,W1,MN1";      // TFs a exportar (separados por virgula)
input string   InpFolder      = "IFM_export";                      // Subpasta em MQL5\Files
input bool     InpOnlyMissing = true;                              // Pular arquivos que ja existem

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
//| 1º de janeiro do ano dado, como datetime                          |
//+------------------------------------------------------------------+
datetime Jan1(const int year)
  {
   return StringToTime(StringFormat("%04d.01.01 00:00", year));
  }

//+------------------------------------------------------------------+
//| CopyRates de UMA FATIA, com paciencia e log de vida.              |
//| Fatias pequenas (1 ano) evitam o bloqueio do CopyRates em faixas  |
//| longas de historico profundo (causa do travamento em W1/MN 2016). |
//| Retorno: n>0 barras; 0 = fatia legitimamente vazia; -1 = falha.   |
//+------------------------------------------------------------------+
int CopyChunkRetry(const string sym, const ENUM_TIMEFRAMES tf, const string tfName,
                   const datetime from, const datetime to, MqlRates &rates[])
  {
   for(int attempt = 1; attempt <= 40 && !IsStopped(); attempt++)
     {
      ResetLastError();
      int copied = CopyRates(sym, tf, from, to, rates);
      if(copied > 0) return copied;
      int err = GetLastError();
      // 4001 BARS_NOT_FOUND com historico ja sincronizado = fatia vazia (antes
      // do inicio da serie no broker) — nao e falha.
      if(copied == 0) return 0;
      if(attempt % 10 == 0)
         PrintFormat("ExportBarsG8: aguardando historico %s %s (%s..%s) tentativa %d/40 erro=%d",
                     sym, tfName, TimeToString(from, TIME_DATE), TimeToString(to, TIME_DATE),
                     attempt, err);
      Sleep(500); // aguarda a sincronizacao e tenta de novo
     }
   return -1;
  }

//+------------------------------------------------------------------+
//| Exporta um par × TF em fatias anuais. rows=-1: pulado (existia). |
//+------------------------------------------------------------------+
bool ExportOne(const string sym, const ENUM_TIMEFRAMES tf, const string tfName,
               int &rows, datetime &firstBar, datetime &lastBar, string &file)
  {
   rows = 0; firstBar = 0; lastBar = 0;
   file = InpFolder + "\\" + sym + "_" + tfName + ".csv";

   if(InpOnlyMissing && FileIsExist(file)) { rows = -1; return true; }

   int digits = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
   int h = FileOpen(file, FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(h == INVALID_HANDLE)
     {
      PrintFormat("ExportBarsG8: nao consegui criar %s (erro %d).", file, GetLastError());
      return false;
     }
   FileWrite(h, "time_epoch,time_server,open,high,low,close,tick_volume,spread");

   datetime from = FromForTf(tf);
   MqlDateTime st;
   TimeToStruct(from, st);
   datetime lastWritten = 0;

   for(int year = st.year; !IsStopped(); year++)
     {
      datetime a = from > Jan1(year) ? from : Jan1(year);
      datetime b = InpTo < Jan1(year + 1) ? InpTo : (datetime)((long)Jan1(year + 1) - 1);
      if(a > InpTo) break;

      MqlRates rates[];
      int copied = CopyChunkRetry(sym, tf, tfName, a, b, rates);
      if(copied < 0)
        {
         FileClose(h);
         FileDelete(file); // arquivo parcial fora — a proxima rodada refaz inteiro
         PrintFormat("ExportBarsG8: FALHA em %s %s (fatia %d) — rode o script de novo depois.",
                     sym, tfName, year);
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
      if(year >= 2100) break; // guarda-corpo
     }
   FileClose(h);

   if(rows == 0)
     {
      FileDelete(file);
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
   FileWrite(hm, StringFormat("# ExportBarsG8 v1.00 | exportado_em_local=%s",
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
   int total = np * ntf, done = 0, nOk = 0, nSkip = 0, nFail = 0;
   for(int p = 0; p < np && !IsStopped(); p++)
     {
      for(int t = 0; t < ntf && !IsStopped(); t++)
        {
         done++;
         Comment(StringFormat("ExportBarsG8: %d/%d  %s %s  (ok=%d pulados=%d falhas=%d)",
                              done, total, pairs[p], tfNames[t], nOk, nSkip, nFail));

         int rows; datetime fb, lb; string file;
         bool ok = ExportOne(pairs[p], TfFromName(tfNames[t]), tfNames[t], rows, fb, lb, file);

         string status;
         if(!ok)              { status = "FALHA";           nFail++; }
         else if(rows == -1)  { status = "pulado_existia";  nSkip++; }
         else                 { status = "ok";              nOk++;   }

         FileWrite(hm, StringFormat("%s,%s,%d,%s,%s,%s,%s",
                                    pairs[p], tfNames[t], rows,
                                    (fb > 0) ? TimeToString(fb, TIME_DATE|TIME_MINUTES) : "",
                                    (lb > 0) ? TimeToString(lb, TIME_DATE|TIME_MINUTES) : "",
                                    status, file));
        }
     }
   FileClose(hm);
   Comment("");

   PrintFormat("ExportBarsG8: FIM — %d ok, %d pulados, %d falhas (de %d).", nOk, nSkip, nFail, total);
   if(nFail > 0)
      Print("ExportBarsG8: houve FALHAS — rode o script de novo (com 'Pular arquivos' = true) ate zerar; "
            "o historico baixa aos poucos.");
   else
      Print("ExportBarsG8: tudo exportado. Copie a pasta MQL5\\Files\\", InpFolder,
            " para research/2026-07-reatividade-metricas/data/raw/ (ver README).");
  }
//+------------------------------------------------------------------+

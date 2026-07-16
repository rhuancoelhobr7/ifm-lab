//+------------------------------------------------------------------+
//|                                             ExportGoldenIFM.mq5  |
//|  ifm-lab · Pesquisa 2026-07-reatividade-metricas · Etapa E3      |
//|                                                                  |
//|  Gera o "export do replay do indicador" — os valores-verdade     |
//|  (golden) da verificacao de paridade C1. As funcoes de calculo   |
//|  abaixo sao COPIA LITERAL de src/IFM.mq5 v1.0 (IFM Light, forca  |
//|  S, vel/acel/zvel, zS, cesta, mtf, VETO, rank H1, zMov/zHist).   |
//|  Qualquer edicao no indicador exige regenerar este arquivo.      |
//|                                                                  |
//|  Saida em MQL5\Files\<InpFolder>\:                               |
//|    golden_meta.csv       parametros, versao, servidor, offset     |
//|    golden_strength.csv   S por moeda × TF × ancora (ring t0)      |
//|    golden_derivadas.csv  vel/acel/zvel/zS/cesta por moeda×TF×anc  |
//|    golden_pares.csv      IFM Light por par × TF × ancora (t0)     |
//|    golden_cross.csv      zS/mtf/VETO/rank/zMov/zHist/candidata    |
//|                          em amostras de tempo (cadeia cruzada)    |
//|  NaN e gravado como "nan" (EMPTY_VALUE do painel).               |
//|                                                                  |
//|  Ancoragem: golden_strength/derivadas/pares usam ancora POR      |
//|  SHIFT (shift s em cada par, como o painel ao vivo em s=1);      |
//|  golden_cross usa ancora POR TEMPO (ultima barra fechada <= T,   |
//|  semantica do replay do indicador).                              |
//+------------------------------------------------------------------+
#property copyright   "ifm-lab"
#property version     "1.00"
#property description "Golden do IFM v1.0 para a paridade E3 (codigo copiado literalmente do indicador)"
#property script_show_inputs

//--- escopo do export
input string   InpTFs          = "M30,H1,H4,D1";   // TFs do golden (grade do painel)
input int      InpAnchors      = 80;               // ancoras por TF (shifts 1..N)
input int      InpCrossSamples = 12;               // amostras de tempo da cadeia cruzada
input int      InpCrossStepH1  = 24;               // passo entre amostras (barras H1)
input string   InpFolder       = "IFM_golden";     // subpasta em MQL5\Files

//--- parametros do indicador (DEFAULTS DA v1.0 — logados no golden_meta.csv)
input bool     InpZCore          = true;   // InpZCore
input int      InpCCILength      = 20;     // InpCCILength
input int      InpMFCVolLength   = 20;     // InpMFCVolLength
input int      InpEMAFallbackLen = 21;     // InpEMAFallbackLen
input int      InpMetVelK        = 6;      // InpMetVelK
input int      InpZVelN          = 32;     // InpZVelN
input int      InpZMovN          = 20;     // InpZMovN
input double   InpZThrVel        = 2.0;    // InpZThrVel
input double   InpZThrS          = 1.0;    // InpZThrS
input int      InpMetThrCesta    = 5;      // InpMetThrCesta
input int      InpMetThrMTF      = 2;      // InpMetThrMTF

#define LIGHT_WINDOW   60
#define MET_RING       64
#define MET_MAXP       32

//--- universo (mesma ordem e deteccao do indicador)
string g_cur[8] = {"USD","EUR","GBP","JPY","CHF","CAD","AUD","NZD"};
string g_pair[];
int    g_baseIdx[];
int    g_quoteIdx[];
int    g_cnt[8];
int    g_pairsN = 0;

//--- rings correntes (equivalentes a g_metS/g_metCesta do indicador,
//    mas para 4 TFs construidos na MESMA ancora de tempo — cadeia cruzada)
#define XTFN 4
ENUM_TIMEFRAMES g_xTFs[XTFN]  = {PERIOD_M30, PERIOD_H1, PERIOD_H4, PERIOD_D1};
string          g_xName[XTFN] = {"M30","H1","H4","D1"};
#define XT_M30 0
#define XT_H1  1
#define XT_H4  2
#define XT_D1  3
double g_S[XTFN][8][MET_RING];
double g_cesta[XTFN][8];
double g_ifmNow[XTFN][MET_MAXP];
double g_zMov[8], g_zMovH[8];

//+------------------------------------------------------------------+
//| ===== COPIA LITERAL de src/IFM.mq5 v1.0 (nao editar aqui) ===== |
//+------------------------------------------------------------------+
double Clamp(double v, double lo, double hi) { return MathMax(lo, MathMin(hi, v)); }

// EMA manual a partir de MqlRates (as-series: 0 = mais novo)
double EmaFromRates(const MqlRates &rates[], int period, int atIdx, int total)
{
   int seedStart = MathMin(atIdx + period * 3, total - 1);
   double ema = rates[seedStart].close;
   double k = 2.0 / (period + 1.0);
   for(int i = seedStart - 1; i >= atIdx; i--)
      ema = rates[i].close * k + ema * (1.0 - k);
   return ema;
}

// CCI-Lambert manual (as-series)
double CciFromRates(const MqlRates &rates[], int period, int atIdx)
{
   double sumTP = 0;
   for(int i = atIdx; i < atIdx + period; i++)
      sumTP += (rates[i].high + rates[i].low + rates[i].close) / 3.0;
   double smaTP = sumTP / period;
   double tpNow = (rates[atIdx].high + rates[atIdx].low + rates[atIdx].close) / 3.0;
   double sumDev = 0;
   for(int i = atIdx; i < atIdx + period; i++)
   {
      double tp = (rates[i].high + rates[i].low + rates[i].close) / 3.0;
      sumDev += MathAbs(tp - smaTP);
   }
   double meanDev = sumDev / period;
   if(meanDev == 0) return 0;
   return (tpNow - smaTP) / (0.015 * meanDev);
}

// z-score verdadeiro do typical price: (TP0 - SMA) / desvio-PADRAO populacional.
double TpZScore(const MqlRates &rates[], int period, int atIdx)
{
   double sum = 0;
   for(int i = atIdx; i < atIdx + period; i++)
      sum += (rates[i].high + rates[i].low + rates[i].close) / 3.0;
   double sma = sum / period;
   double ss = 0;
   for(int i = atIdx; i < atIdx + period; i++)
   {
      double tp = (rates[i].high + rates[i].low + rates[i].close) / 3.0;
      ss += (tp - sma) * (tp - sma);
   }
   double sd = MathSqrt(ss / period);
   if(sd == 0) return 0;
   double tp0 = (rates[atIdx].high + rates[atIdx].low + rates[atIdx].close) / 3.0;
   return (tp0 - sma) / sd;
}

double VolFromRates(const MqlRates &r)
{
   if(r.real_volume > 0) return (double)r.real_volume;
   if(r.tick_volume > 0) return (double)r.tick_volume;
   return 1.0;
}

// IFM Light num índice arbitrário de array as-series já copiado.
double CalcIFMLightAt(const MqlRates &rates[], int atIdx, int copiedTotal)
{
   int copied = MathMin(copiedTotal - atIdx, LIGHT_WINDOW);
   if(copied < MathMax(InpCCILength, InpEMAFallbackLen) + 5) return 50.0;

   //--- Module 1: Pivot Points
   int scorePivot = 0;
   if(copied >= 2)
   {
      double pp = (rates[atIdx+1].high + rates[atIdx+1].low + rates[atIdx+1].close) / 3.0;
      double r1 = 2.0 * pp - rates[atIdx+1].low;
      double s1 = 2.0 * pp - rates[atIdx+1].high;
      double c  = rates[atIdx].close;
      if(c > pp && c > r1)      scorePivot =  2;
      else if(c > pp)           scorePivot =  1;
      else if(c < pp && c < s1) scorePivot = -2;
      else if(c < pp)           scorePivot = -1;
   }

   //--- Module 2: Market Profile (EMA fallback)
   int scoreMP = 0;
   if(copied >= InpEMAFallbackLen * 3 + 2)
   {
      double ema0 = EmaFromRates(rates, InpEMAFallbackLen, atIdx,   atIdx + copied);
      double ema1 = EmaFromRates(rates, InpEMAFallbackLen, atIdx+1, atIdx + copied);
      double vah  = ema0 * 1.01;
      double val  = ema0 * 0.99;
      double c    = rates[atIdx].close;
      if(c > vah && ema0 > ema1)       scoreMP =  2;
      else if(c > vah)                 scoreMP =  1;
      else if(c < val && ema0 < ema1)  scoreMP = -2;
      else if(c < val)                 scoreMP = -1;
   }

   //--- Module 3: MFC
   int scoreMFC = 0;
   if(copied >= InpMFCVolLength + 2)
   {
      double vol0  = VolFromRates(rates[atIdx]);
      double vol1  = VolFromRates(rates[atIdx+1]);
      double mfc0  = vol0 > 0 ? (rates[atIdx].high - rates[atIdx].low) / vol0 : 0;
      double mfc1  = vol1 > 0 ? (rates[atIdx+1].high - rates[atIdx+1].low) / vol1 : 0;
      double avgVol = 0;
      int cnt = 0;
      for(int j = 0; j < MathMin(InpMFCVolLength, copied); j++)
      { avgVol += VolFromRates(rates[atIdx+j]); cnt++; }
      avgVol = cnt > 0 ? avgVol / cnt : 1;
      bool varPreco  = mfc0 > mfc1;
      bool varVolume = vol0 > avgVol;
      if(varPreco && varVolume)        scoreMFC =  1;
      else if(!varPreco && varVolume)  scoreMFC = -1;
   }

   //--- Module 5: CCI — variante Z: z-score contínuo do TP, clampado em ±2
   double scoreCCI = 0;
   if(copied >= InpCCILength + 2)
   {
      if(InpZCore)
         scoreCCI = Clamp(TpZScore(rates, InpCCILength, atIdx), -2.0, 2.0);
      else
      {
         double cci = CciFromRates(rates, InpCCILength, atIdx);
         if(cci > 0 && cci > 100)   scoreCCI =  2;
         else if(cci > 0)           scoreCCI =  1;
         else if(cci < 0 && cci < -100) scoreCCI = -2;
         else if(cci < 0)           scoreCCI = -1;
      }
   }

   //--- Aggregation: Pivot×2 + MP×2 + MFC×1 + CCI×3 = max ±15
   double bruto = scorePivot * 2.0 + scoreMP * 2.0 + scoreMFC * 1.0 + scoreCCI * 3.0;
   double ifmFinal = (bruto + 15.0) / 30.0 * 100.0;
   return Clamp(ifmFinal, 0, 100);
}

int MetSign(double x) { return x > 0 ? 1 : (x < 0 ? -1 : 0); }
bool MetIsNan(double v) { return v == EMPTY_VALUE; }

bool MetSliceOk(const double &s[], int fromIdx)
{
   for(int i = fromIdx; i < MET_RING; i++) if(MetIsNan(s[i])) return false;
   return true;
}

double MetVel(const double &s[], int k)
{
   if(k + 1 > MET_RING || !MetSliceOk(s, MET_RING - 1 - k)) return EMPTY_VALUE;
   return s[MET_RING-1] - s[MET_RING-1-k];
}

double MetAcel(const double &s[], int k)
{
   if(2*k + 1 > MET_RING || !MetSliceOk(s, MET_RING - 1 - 2*k)) return EMPTY_VALUE;
   return (s[MET_RING-1] - s[MET_RING-1-k]) - (s[MET_RING-1-k] - s[MET_RING-1-2*k]);
}

double MetZVel(const double &s[], int k, int n)
{
   double v = MetVel(s, k);
   if(MetIsNan(v)) return EMPTY_VALUE;
   if(n + 1 > MET_RING || !MetSliceOk(s, MET_RING - 1 - n)) return EMPTY_VALUE;
   double sum = 0, ss = 0; int m = 0;
   for(int i = MET_RING - n; i < MET_RING; i++)
   { double d = s[i] - s[i-1]; sum += d; ss += d*d; m++; }
   double mean = sum / m;
   double sd = MathSqrt(MathMax(ss / m - mean*mean, 0.0));
   double den = sd * MathSqrt((double)k);
   if(den < 1e-9) return EMPTY_VALUE;
   return v / den;
}
//+------------------------------------------------------------------+
//| ===== fim da copia literal ===== |
//+------------------------------------------------------------------+

//+------------------------------------------------------------------+
//| Deteccao dos pares G8 (mesma logica do OnInit do indicador)      |
//+------------------------------------------------------------------+
int CurIdx(const string c)
{
   for(int i = 0; i < 8; i++) if(c == g_cur[i]) return i;
   return -1;
}

bool DetectG8()
{
   ArrayInitialize(g_cnt, 0);
   g_pairsN = 0;
   bool seen[64];
   for(int s = 0; s < 64; s++) seen[s] = false;
   int totalSym = SymbolsTotal(false);
   for(int s = 0; s < totalSym; s++)
   {
      string sym = SymbolName(s, false);
      int bi = CurIdx(SymbolInfoString(sym, SYMBOL_CURRENCY_BASE));
      int qi = CurIdx(SymbolInfoString(sym, SYMBOL_CURRENCY_PROFIT));
      if(bi < 0 || qi < 0 || bi == qi) continue;
      int key = (bi < qi) ? bi*8+qi : qi*8+bi;
      if(seen[key]) continue;
      if(!SymbolSelect(sym, true)) continue;
      int n = g_pairsN + 1;
      ArrayResize(g_pair, n); ArrayResize(g_baseIdx, n); ArrayResize(g_quoteIdx, n);
      g_pair[g_pairsN] = sym;
      g_baseIdx[g_pairsN] = bi;
      g_quoteIdx[g_pairsN] = qi;
      g_cnt[bi]++; g_cnt[qi]++; g_pairsN++;
      seen[key] = true;
   }
   return g_pairsN > 0;
}

//+------------------------------------------------------------------+
//| Ancora por TEMPO (semantica do replay do indicador)              |
//+------------------------------------------------------------------+
int AnchorAt(const string sym, const ENUM_TIMEFRAMES tf, const datetime t)
{
   int bars = Bars(sym, tf, t, TimeCurrent());
   return MathMax(1, bars);
}

//+------------------------------------------------------------------+
//| Constroi o ring de S/cesta de UM TF (estrutura do MetRebuild).   |
//| anchorMode: -1 = ancora por tempo tAnchor; >=1 = shift fixo.     |
//+------------------------------------------------------------------+
void BuildRings(const int xt, const int shiftFixo, const datetime tAnchor)
{
   ENUM_TIMEFRAMES tf = g_xTFs[xt];
   double acc[8][MET_RING];
   int    okc[8][MET_RING];
   for(int c = 0; c < 8; c++)
      for(int j = 0; j < MET_RING; j++) { acc[c][j] = 0.0; okc[c][j] = 0; }
   for(int p = 0; p < MET_MAXP; p++) g_ifmNow[xt][p] = EMPTY_VALUE;

   for(int p = 0; p < g_pairsN && p < MET_MAXP; p++)
   {
      int anchor = (shiftFixo >= 1) ? shiftFixo : AnchorAt(g_pair[p], tf, tAnchor);
      MqlRates rates[];
      ArraySetAsSeries(rates, true);
      int copied = CopyRates(g_pair[p], tf, anchor, LIGHT_WINDOW + MET_RING - 1, rates);
      if(copied <= 0) continue;
      for(int j = 0; j < MET_RING; j++)
      {
         int atIdx = MET_RING - 1 - j;
         if(copied - atIdx < LIGHT_WINDOW) continue;  // janela incompleta => NaN
         double ifm = CalcIFMLightAt(rates, atIdx, copied);
         double dir = (ifm - 50.0) / 50.0;
         acc[g_baseIdx[p]][j]  += dir;  okc[g_baseIdx[p]][j]++;
         acc[g_quoteIdx[p]][j] -= dir;  okc[g_quoteIdx[p]][j]++;
         if(j == MET_RING - 1) g_ifmNow[xt][p] = ifm;
      }
   }
   for(int c = 0; c < 8; c++)
      for(int j = 0; j < MET_RING; j++)
         g_S[xt][c][j] = (g_cnt[c] > 0 && okc[c][j] == g_cnt[c])
                         ? 50.0 + (acc[c][j] / g_cnt[c]) * 50.0
                         : EMPTY_VALUE;

   // CESTA no t0 (lado-consciente, denominador = nº de pares da moeda)
   for(int c = 0; c < 8; c++)
   {
      double s0 = g_S[xt][c][MET_RING-1];
      int lado = MetIsNan(s0) ? 0 : MetSign(s0 - 50.0);
      if(lado == 0 || g_cnt[c] == 0) { g_cesta[xt][c] = EMPTY_VALUE; continue; }
      int conf = 0;
      bool bad = false;
      for(int p = 0; p < g_pairsN && p < MET_MAXP; p++)
      {
         if(g_baseIdx[p] != c && g_quoteIdx[p] != c) continue;
         if(MetIsNan(g_ifmNow[xt][p])) { bad = true; break; }
         int pside = MetSign(g_ifmNow[xt][p] - 50.0);
         if(pside == 0) continue;
         if((g_baseIdx[p] == c) ? (pside == lado) : (pside == -lado)) conf++;
      }
      g_cesta[xt][c] = bad ? EMPTY_VALUE : (double)conf / g_cnt[c];
   }
}

//+------------------------------------------------------------------+
//| zMov/zHist na ancora de tempo tAnchor (bloco do MetRebuild com   |
//| MetAnchorShift substituido pela ancora por tempo)                |
//+------------------------------------------------------------------+
void BuildZMov(const datetime tAnchor)
{
   datetime barT = iTime(g_pair[0], PERIOD_M30, AnchorAt(g_pair[0], PERIOD_M30, tAnchor));
   datetime dayStart = barT - (datetime)((long)barT % 86400);
   long tod = ((long)barT + PeriodSeconds(PERIOD_M30)) - (long)dayStart;
   int nH = (int)MathMin(MathMax(InpZMovN, 5), 38);

   double movDay[8][40];
   int    cntDay[8][40];
   bool   badDay[8][40];
   for(int c = 0; c < 8; c++)
      for(int i = 0; i <= nH; i++)
      { movDay[c][i] = 0.0; cntDay[c][i] = 0; badDay[c][i] = false; }

   for(int p = 0; p < g_pairsN && p < MET_MAXP; p++)
   {
      int shD = AnchorAt(g_pair[p], PERIOD_D1, tAnchor);
      for(int i = 0; i <= nH; i++)
      {
         int d1sh = shD + i;
         datetime ds = iTime(g_pair[p], PERIOD_D1, d1sh);
         bool pOk = (ds > 0);
         double r = 0;
         if(pOk)
         {
            double atr = 0; int nOk = 0;
            for(int j = d1sh + 1; j <= d1sh + 14; j++)
            {
               double hi = iHigh(g_pair[p], PERIOD_D1, j), lo = iLow(g_pair[p], PERIOD_D1, j);
               double pc = iClose(g_pair[p], PERIOD_D1, j + 1);
               if(hi <= 0 || lo <= 0 || pc <= 0) break;
               atr += MathMax(hi - lo, MathMax(MathAbs(hi - pc), MathAbs(lo - pc)));
               nOk++;
            }
            double refC = iClose(g_pair[p], PERIOD_D1, d1sh + 1);
            int sh0 = iBarShift(g_pair[p], PERIOD_M30, ds - 1, false);
            int sh1 = iBarShift(g_pair[p], PERIOD_M30, (datetime)((long)ds + tod - 1), false);
            double c0 = (sh0 >= 0) ? iClose(g_pair[p], PERIOD_M30, sh0) : 0.0;
            double c1 = (sh1 >= 0) ? iClose(g_pair[p], PERIOD_M30, sh1) : 0.0;
            pOk = (nOk == 14 && refC > 0 && c0 > 0 && c1 > 0 && atr > 0);
            if(pOk) r = MathLog(c1 / c0) / ((atr / 14.0) / refC);
         }
         if(pOk) { movDay[g_baseIdx[p]][i] += r;  cntDay[g_baseIdx[p]][i]++;
                   movDay[g_quoteIdx[p]][i] -= r; cntDay[g_quoteIdx[p]][i]++; }
         else    { badDay[g_baseIdx[p]][i] = true; badDay[g_quoteIdx[p]][i] = true; }
      }
   }

   double m0[8]; bool ok0[8];
   for(int c = 0; c < 8; c++)
   {
      ok0[c] = (!badDay[c][0] && g_cnt[c] > 0 && cntDay[c][0] == g_cnt[c]);
      m0[c] = ok0[c] ? movDay[c][0] : 0.0;

      double sum = 0, ss = 0; int m = 0;
      for(int i = 1; i <= nH; i++)
      {
         if(badDay[c][i] || cntDay[c][i] != g_cnt[c]) continue;
         sum += movDay[c][i]; ss += movDay[c][i] * movDay[c][i]; m++;
      }
      if(ok0[c] && m >= 10)
      {
         double mean = sum / m;
         double sd = MathSqrt(MathMax(ss / m - mean * mean, 0.0));
         g_zMovH[c] = (sd < 1e-9) ? EMPTY_VALUE : (m0[c] - mean) / sd;
      }
      else g_zMovH[c] = EMPTY_VALUE;
   }

   double sum8 = 0, ss8 = 0; int m8 = 0;
   for(int c = 0; c < 8; c++)
      if(ok0[c]) { sum8 += m0[c]; ss8 += m0[c] * m0[c]; m8++; }
   double mean8 = (m8 > 0) ? sum8 / m8 : 0.0;
   double sd8 = (m8 >= 4) ? MathSqrt(MathMax(ss8 / m8 - mean8 * mean8, 0.0)) : 0.0;
   for(int c = 0; c < 8; c++)
      g_zMov[c] = (ok0[c] && sd8 > 1e-9) ? (m0[c] - mean8) / sd8 : EMPTY_VALUE;
}

//+------------------------------------------------------------------+
//| Rank H1 (copia de MetRankH1, sobre g_S/g_cesta do slot H1)       |
//+------------------------------------------------------------------+
void RankH1(int &rank[])
{
   int ord[8];
   for(int i = 0; i < 8; i++) ord[i] = i;
   for(int i = 0; i < 8; i++)
      for(int j = i + 1; j < 8; j++)
      {
         int a = ord[i], b = ord[j];
         double sa = g_S[XT_H1][a][MET_RING-1], sb = g_S[XT_H1][b][MET_RING-1];
         double ca = g_cesta[XT_H1][a], cb = g_cesta[XT_H1][b];
         double sa2 = MetIsNan(sa) ? -1e9 : sa, sb2 = MetIsNan(sb) ? -1e9 : sb;
         double ca2 = MetIsNan(ca) ? -1.0 : ca, cb2 = MetIsNan(cb) ? -1.0 : cb;
         bool swap = (sb2 > sa2) ||
                     (sb2 == sa2 && cb2 > ca2) ||
                     (sb2 == sa2 && cb2 == ca2 && StringCompare(g_cur[b], g_cur[a]) < 0);
         if(swap) { ord[i] = b; ord[j] = a; }
      }
   for(int i = 0; i < 8; i++) rank[ord[i]] = i + 1;
}

//+------------------------------------------------------------------+
string Num(const double v)
{
   if(MetIsNan(v)) return "nan";
   return DoubleToString(v, 10);
}

//+------------------------------------------------------------------+
void OnStart()
{
   if(!DetectG8()) { Alert("ExportGoldenIFM: nenhum par G8 no Observatorio."); return; }
   if(g_pairsN != 28)
      PrintFormat("ExportGoldenIFM: AVISO — %d pares (esperados 28).", g_pairsN);

   string tfNames[];
   int ntf = StringSplit(InpTFs, ',', tfNames);

   //--- meta (proveniencia NUNCA mais desconhecida)
   int hm = FileOpen(InpFolder + "\\golden_meta.csv", FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(hm == INVALID_HANDLE) { Alert("ExportGoldenIFM: erro criando golden_meta.csv"); return; }
   FileWrite(hm, "chave,valor");
   FileWrite(hm, "ferramenta,ExportGoldenIFM v1.00 (copia literal de src/IFM.mq5 v1.0)");
   FileWrite(hm, "gerado_em_local," + TimeToString(TimeLocal(), TIME_DATE|TIME_SECONDS));
   FileWrite(hm, "server_time," + TimeToString(TimeTradeServer(), TIME_DATE|TIME_SECONDS));
   FileWrite(hm, StringFormat("offset_server_gmt_h,%.1f",
             ((double)((long)TimeTradeServer() - (long)TimeGMT())) / 3600.0));
   FileWrite(hm, "conta_servidor," + AccountInfoString(ACCOUNT_SERVER));
   FileWrite(hm, StringFormat("zcore,%s", InpZCore ? "true" : "false"));
   FileWrite(hm, StringFormat("cci_length,%d", InpCCILength));
   FileWrite(hm, StringFormat("mfc_vol_length,%d", InpMFCVolLength));
   FileWrite(hm, StringFormat("ema_fallback_len,%d", InpEMAFallbackLen));
   FileWrite(hm, StringFormat("vel_k,%d", InpMetVelK));
   FileWrite(hm, StringFormat("zvel_sigma_n,%d", InpZVelN));
   FileWrite(hm, StringFormat("zmov_days_n,%d", InpZMovN));
   FileWrite(hm, StringFormat("pares,%d", g_pairsN));
   FileWrite(hm, StringFormat("ancoras,%d", InpAnchors));
   FileWrite(hm, StringFormat("cross_samples,%d passo %d barras H1", InpCrossSamples, InpCrossStepH1));
   FileClose(hm);

   //--- golden por SHIFT: strength, derivadas single-TF e IFM por par
   int hs = FileOpen(InpFolder + "\\golden_strength.csv",  FILE_WRITE|FILE_TXT|FILE_ANSI);
   int hd = FileOpen(InpFolder + "\\golden_derivadas.csv", FILE_WRITE|FILE_TXT|FILE_ANSI);
   int hp = FileOpen(InpFolder + "\\golden_pares.csv",     FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(hs == INVALID_HANDLE || hd == INVALID_HANDLE || hp == INVALID_HANDLE)
   { Alert("ExportGoldenIFM: erro criando CSVs."); return; }
   FileWrite(hs, "tf,anchor_shift,bar_time,currency,S");
   FileWrite(hd, "tf,anchor_shift,bar_time,currency,vel,acel,zvel,zS,cesta");
   FileWrite(hp, "tf,anchor_shift,bar_time,pair,ifm_light");

   for(int t = 0; t < ntf; t++)
   {
      StringTrimLeft(tfNames[t]); StringTrimRight(tfNames[t]);
      int xt = -1;
      for(int i = 0; i < XTFN; i++) if(g_xName[i] == tfNames[t]) xt = i;
      if(xt < 0) { Print("ExportGoldenIFM: TF fora da grade cross (", tfNames[t], ") — pulado."); continue; }

      for(int s = 1; s <= InpAnchors && !IsStopped(); s++)
      {
         Comment(StringFormat("ExportGoldenIFM: %s ancora %d/%d", tfNames[t], s, InpAnchors));
         BuildRings(xt, s, 0);
         string bt = TimeToString(iTime(g_pair[0], g_xTFs[xt], s), TIME_DATE|TIME_MINUTES);

         // z transversal (copia do RenderMetrics)
         double xsMean = 50.0, xsSd = 0.0;
         {
            int m = 0; double sum = 0, ss = 0;
            for(int c2 = 0; c2 < 8; c2++)
            {
               double sv = g_S[xt][c2][MET_RING-1];
               if(MetIsNan(sv)) continue;
               sum += sv; ss += sv*sv; m++;
            }
            if(m >= 4) { xsMean = sum/m; xsSd = MathSqrt(MathMax(ss/m - xsMean*xsMean, 0.0)); }
         }

         for(int c = 0; c < 8; c++)
         {
            double serie[MET_RING];
            for(int j = 0; j < MET_RING; j++) serie[j] = g_S[xt][c][j];
            double s0   = serie[MET_RING-1];
            double vel  = MetVel(serie, InpMetVelK);
            double acel = MetAcel(serie, InpMetVelK);
            double zvel = MetZVel(serie, InpMetVelK, InpZVelN);
            double zS   = (MetIsNan(s0) || xsSd < 1e-9) ? EMPTY_VALUE : (s0 - xsMean) / xsSd;
            FileWrite(hs, StringFormat("%s,%d,%s,%s,%s", tfNames[t], s, bt, g_cur[c], Num(s0)));
            FileWrite(hd, StringFormat("%s,%d,%s,%s,%s,%s,%s,%s,%s", tfNames[t], s, bt, g_cur[c],
                                       Num(vel), Num(acel), Num(zvel), Num(zS), Num(g_cesta[xt][c])));
         }
         for(int p = 0; p < g_pairsN && p < MET_MAXP; p++)
            FileWrite(hp, StringFormat("%s,%d,%s,%s,%s", tfNames[t], s, bt, g_pair[p],
                                       Num(g_ifmNow[xt][p])));
      }
   }
   FileClose(hs); FileClose(hd); FileClose(hp);

   //--- golden CROSS: cadeia cruzada em amostras de tempo (ancora por tempo)
   int hx = FileOpen(InpFolder + "\\golden_cross.csv", FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(hx == INVALID_HANDLE) { Alert("ExportGoldenIFM: erro criando golden_cross.csv"); return; }
   FileWrite(hx, "sample_time,currency,S_M30,S_H1,S_H4,S_D1,zS_H1,mtf,veto,rank_h1,zmov,zhist,candidata_h1");

   for(int k = 0; k < InpCrossSamples && !IsStopped(); k++)
   {
      datetime tA = iTime(g_pair[0], PERIOD_H1, 1 + k * InpCrossStepH1);
      Comment(StringFormat("ExportGoldenIFM: cross %d/%d (%s)", k+1, InpCrossSamples,
                           TimeToString(tA, TIME_DATE|TIME_MINUTES)));
      for(int xt = 0; xt < XTFN; xt++) BuildRings(xt, 0, tA);
      BuildZMov(tA);
      int rankH1[8];
      RankH1(rankH1);

      // zS transversal no H1 (tsel default do painel)
      double xsMean = 50.0, xsSd = 0.0;
      {
         int m = 0; double sum = 0, ss = 0;
         for(int c2 = 0; c2 < 8; c2++)
         {
            double sv = g_S[XT_H1][c2][MET_RING-1];
            if(MetIsNan(sv)) continue;
            sum += sv; ss += sv*sv; m++;
         }
         if(m >= 4) { xsMean = sum/m; xsSd = MathSqrt(MathMax(ss/m - xsMean*xsMean, 0.0)); }
      }

      for(int c = 0; c < 8; c++)
      {
         double s0H1 = g_S[XT_H1][c][MET_RING-1];
         double zS = (MetIsNan(s0H1) || xsSd < 1e-9) ? EMPTY_VALUE : (s0H1 - xsMean) / xsSd;

         // MTF_sign sobre M30/H1/H4/D1, ref = H1 (copia do RenderMetrics)
         int refSide = MetIsNan(s0H1) ? 0 : MetSign(s0H1 - 50.0);
         int mtfSign = -1;
         if(refSide != 0)
         {
            mtfSign = 0;
            for(int t2 = 0; t2 < XTFN; t2++)
            {
               double sv = g_S[t2][c][MET_RING-1];
               if(!MetIsNan(sv) && MetSign(sv - 50.0) == refSide) mtfSign++;
            }
         }

         // VETO (copia do RenderMetrics)
         double sr6H4[MET_RING], sr6D1[MET_RING];
         for(int j = 0; j < MET_RING; j++)
         { sr6H4[j] = g_S[XT_H4][c][j]; sr6D1[j] = g_S[XT_D1][c][j]; }
         double vH4 = MetVel(sr6H4, 6), vD1 = MetVel(sr6D1, 6);
         bool vetoOn = false;
         if(refSide != 0 && !MetIsNan(vH4) && !MetIsNan(vD1))
         {
            int rSided = (refSide > 0) ? rankH1[c] : (9 - rankH1[c]);
            if(rSided <= 2)
               vetoOn = (refSide > 0) ? (vH4 < 0 && vD1 < 0) : (vH4 > 0 && vD1 > 0);
         }

         // candidata no H1 (copia do RenderMetrics, tsel = H1)
         double serieH1[MET_RING];
         for(int j = 0; j < MET_RING; j++) serieH1[j] = g_S[XT_H1][c][j];
         double zvelH1 = MetZVel(serieH1, InpMetVelK, InpZVelN);
         double cestaH1 = g_cesta[XT_H1][c];
         bool cand = !MetIsNan(zvelH1) && MathAbs(zvelH1) >= InpZThrVel &&
                     !MetIsNan(zS) && MathAbs(zS) >= InpZThrS &&
                     !MetIsNan(cestaH1) && cestaH1 * g_cnt[c] >= InpMetThrCesta - 1e-9 &&
                     mtfSign >= InpMetThrMTF && !vetoOn && refSide != 0;

         FileWrite(hx, StringFormat("%s,%s,%s,%s,%s,%s,%s,%d,%d,%d,%s,%s,%d",
                   TimeToString(tA, TIME_DATE|TIME_MINUTES), g_cur[c],
                   Num(g_S[XT_M30][c][MET_RING-1]), Num(s0H1),
                   Num(g_S[XT_H4][c][MET_RING-1]), Num(g_S[XT_D1][c][MET_RING-1]),
                   Num(zS), mtfSign, vetoOn ? 1 : 0, rankH1[c],
                   Num(g_zMov[c]), Num(g_zMovH[c]), cand ? 1 : 0));
      }
   }
   FileClose(hx);
   Comment("");
   Print("ExportGoldenIFM: FIM. Copie MQL5\\Files\\", InpFolder,
         " para research/2026-07-reatividade-metricas/data/raw/ (arquivos golden_*.csv).");
}
//+------------------------------------------------------------------+

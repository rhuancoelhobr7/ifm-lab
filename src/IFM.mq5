//+------------------------------------------------------------------+
//|                 IFM - Índice de Força da Moeda                   |
//+------------------------------------------------------------------+
#property copyright   "IFM - Índice de Força da Moeda"
#property link        ""
#property version     "1.2"
#property description ""
#property strict

//--- Indicator window (subjanela — objetos gráficos + buffers do motor ML)
#property indicator_separate_window
#property indicator_buffers 4
#property indicator_plots   4
#property indicator_type1   DRAW_NONE
#property indicator_label1  "IFM_ML"
#property indicator_type2   DRAW_NONE
#property indicator_label2  "ML_RSI"
#property indicator_type3   DRAW_NONE
#property indicator_label3  "Rank"
#property indicator_type4   DRAW_NONE
#property indicator_label4  "Conf"

//+------------------------------------------------------------------+
//|                        INPUTS                                     |
//+------------------------------------------------------------------+
input group           "═══════ ML Brain (Par Ativo) ═══════"
input int             InpRSILength      = 14;       // RSI Base Length
input int             InpMemoryDepth    = 400;      // Memory Depth (bars)
input int             InpKNeighbors     = 8;        // Analog Count (k)
input double          InpATRFactor      = 0.5;      // Learning Sensitivity (xATR)
input bool            InpAutoOptimize   = true;     // Auto-Optimize Weights
input double          InpAdaptSpeed     = 1.0;      // Adaptation Speed
input int             InpGateRank       = 60;       // Min Rank for ML Score +2/-2
input int             InpGateConf       = 50;       // Min Confidence for ML Score +2/-2

input group           "═══════ IFM Modules ═══════"
input int             InpCCILength      = 20;       // CCI Length
input int             InpMFCVolLength   = 20;       // MFC Volume Average Length
input int             InpEMAFallbackLen = 21;       // Market Profile Fallback EMA

input group           "═══════ Painel ═══════"
input int             InpFont           = 9;        // Fonte do painel
input bool            InpShowMatrix     = true;     // Mostrar Matriz 8x8 ao lado
input int             InpRefreshSec     = 60;       // Atualizacao automatica (segundos)

input group           "═══════ Metricas (V2) ═══════"
input int             InpMetVelK    = 6;            // k da VEL/ACEL exibidas
input int             InpMetPersN   = 12;           // N de PERS/EFIC
input double          InpMetThrVel  = 17.6;         // Limiar destaque |VEL| (F3 p75)
input double          InpMetThrPers = 0.58;         // Limiar destaque PERS (F3 p75)
input int             InpMetThrCesta= 5;            // Limiar destaque CESTA (de 7)
input int             InpMetThrMTF  = 2;            // (v1.2: fora da candidata — mtf so exibicao)

input group           "═══════ Z-Score (variante exploratoria) ═══════"
input bool            InpZCore      = true;         // Nucleo IFM-Z: CCI = z-score continuo
input int             InpZVelN      = 32;           // Janela do sigma de dS (zvel)
input double          InpZThrVel    = 2.0;          // Limiar destaque |zvel|
input double          InpZThrS      = 1.0;          // Limiar destaque |zS| (transversal)
input int             InpZMovN      = 20;           // Dias do z historico do movATR

input group           "═══════ v1.2 — Alerta / Score (pesquisa reatividade) ═══════"
input bool            InpShowScore  = true;         // Colunas SCORE (E10) e dia% no painel
input int             InpLateHour   = 15;           // Hora server que esmaece ALERTAS novos (NY)


//+------------------------------------------------------------------+
//|                      CONSTANTS                                    |
//+------------------------------------------------------------------+
#define LIGHT_WINDOW   60     // Bars needed for IFM Light calculation
#define IFM_STRONG     65.0
#define IFM_WEAK       35.0
#define TOPBAR_H       30     // faixa reservada para os botões

// Motor ML (par ativo)
#define STEP_LEN       3
#define WIN_LEN        100
#define HORIZON_BARS   4
#define SPACING_BARS   4
#define TREND_LEN      50
#define CHOP_CUT       0.5
#define VOL_BAND_LO    20
#define VOL_BAND_HI    85
#define AUTO_FLOOR     0.5
#define AUTO_MIN_ROWS  60
#define SMOOTH_LEN     10
#define BANK_COLS      9
#define ST_ATR_LEN     10
#define ST_MULT_BASE   1.5

// Timeframes da vista MÉTRICAS e da MATRIZ (compartilhados)
#define MET_TFN        6
#define MET_RING       64
#define MET_MAXP       32
// Índices fixos usados por MTF/VETO/rank (referências do spec):
#define TF_M30_IDX     2
#define TF_H1_IDX      3
#define TF_H4_IDX      4
#define TF_D1_IDX      5


//+------------------------------------------------------------------+
//|            INDICATOR BUFFERS (motor ML — DRAW_NONE)                |
//+------------------------------------------------------------------+
double IFMBuf[];      // IFM completo (5 juizes) do par ativo
double MLRSIBuf[];    // ML RSI (RSI + tilt do motor)
double RankBuf[];     // Rank do setup (0-100)
double ConfBuf[];     // Confidence do sinal (0-100)


//+------------------------------------------------------------------+
//|                  INDICATOR HANDLES (active pair)                   |
//+------------------------------------------------------------------+
int g_hRsiBase, g_hRsiFast, g_hRsiSlow;
int g_hATR14, g_hATR10;
int g_hCCI;
int g_hEmaRsi20, g_hEmaRsi5;
int g_hEmaClose5, g_hEmaClose50, g_hEmaClose21;


//+------------------------------------------------------------------+
//|                 WORKING ARRAYS (active pair ML)                    |
//+------------------------------------------------------------------+
double g_rsiBase[], g_rsiFast[], g_rsiSlow[];
double g_atr14[], g_atr10[];
double g_cci[];
double g_emaRsi20[], g_emaRsi5[];
double g_emaClose5[], g_emaClose50[], g_emaClose21[];
double g_rsiSlope[], g_rsiAccel[];
double g_rsiStd[], g_rsiSpread[], g_rsiReg[];
double g_fVal[], g_fSlp[], g_fAcc[], g_fMid[];
double g_fPct[], g_fChn[], g_fSpr[], g_fReg[];
double g_stLong[], g_stShort[], g_stDir[];
double g_convSmooth[], g_emaRank[], g_mlRsiArr[];


//+------------------------------------------------------------------+
//|                 FEATURE BANK (ML engine)                           |
//+------------------------------------------------------------------+
double g_bank[];
int    g_bankCapacity, g_bankSize, g_bankNext, g_lastBankBar;
double g_autoW[8], g_weights[8];
int    g_stanceState, g_stanceAge, g_lastEntryBar;

// Estado ML corrente do par ativo (última barra fechada)
double g_activeIFM = 50, g_activeRank = 0, g_activeConf = 0;
int    g_activeBias = 0;


//+------------------------------------------------------------------+
//|                 PAIR DETECTION & CURRENCY DATA                     |
//+------------------------------------------------------------------+
string g_cur[8]    = {"USD","EUR","GBP","JPY","CHF","CAD","AUD","NZD"};
color  g_colArr[8] = {clrLime,clrDodgerBlue,clrRed,clrMagenta,
                      clrSilver,clrOrange,clrGold,clrAqua};
string g_pair[];
int    g_baseIdx[], g_quoteIdx[];
int    g_pairsN = 0;
int    g_cnt[8];              // pares por moeda

//--- Prefixos de objetos
string PFX  = "IFMZM_";       // topbar / botões
string MPFX = "IFMZM_mx_";    // matriz
string TPFX = "IFMZM_mt_";    // métricas

//--- Estado
bool   g_ready     = false;
bool   g_mtxShow   = true;    // matriz visível (toggle no botão)
int    g_mtxTFIdx  = 3;       // TF da matriz (índice em g_metTFs; default H1)
int    g_metTFIdx  = 3;       // aba da vista métricas (default H1)
datetime g_lastUpdate = 0;    // hora local da última atualização de dados
int    g_secCount  = 0;       // segundos desde o último refresh (timer)
int    g_statusX   = 0;       // posição x do label de status na topbar
bool   g_computing = false;   // guarda contra reentrância durante rebuild

//--- Replay system (âncora temporal — navega barras fechadas do TF do gráfico)
bool     g_replayOn    = false;
int      g_replayShift = 1;     // barras para trás no TF do gráfico (1 = última fechada)
datetime g_replayTime  = 0;     // tempo absoluto do ponto de replay

ENUM_TIMEFRAMES g_metTFs[MET_TFN] =
   {PERIOD_M5, PERIOD_M15, PERIOD_M30, PERIOD_H1, PERIOD_H4, PERIOD_D1};
string g_metTfName[MET_TFN] = {"M5","M15","M30","H1","H4","D1"};

//--- Cache MÉTRICAS
double g_metS[8][MET_TFN][MET_RING];   // série S cronológica (63 = t0); EMPTY_VALUE = NaN
double g_metCesta[8][MET_TFN];         // CESTA no t0 de cada TF
double g_metZMov[8];                   // z TRANSVERSAL do movATR
double g_metZMovH[8];                  // z HISTORICO do movATR
double g_metScore[8];                  // SCORE 0-100 (detector E10; base M30, indep. da aba)
double g_metConsumo[8];                // % do dia típico já consumido (cesta D1/M30)
bool   g_metDirty  = true;

//--- Cache MATRIZ
double g_mtxVal[64];
bool   g_mtxOk[64];
double g_mtxStr[8];
int    g_mtxGood    = 0;
int    g_mtxCacheTF = -1;              // -1 = dirty


//+------------------------------------------------------------------+
//|                  HELPER FUNCTIONS                                  |
//+------------------------------------------------------------------+
double Clamp(double v, double lo, double hi) { return MathMax(lo, MathMin(hi, v)); }
int CurIdx(string code) { for(int i=0; i<8; i++) if(g_cur[i]==code) return i; return -1; }
ENUM_TIMEFRAMES Rtf(ENUM_TIMEFRAMES tf) { return (tf==PERIOD_CURRENT)?(ENUM_TIMEFRAMES)_Period:tf; }
string TfStr(ENUM_TIMEFRAMES tf)
{
   string s = EnumToString(Rtf(tf));
   StringReplace(s, "PERIOD_", "");
   return s;
}

// Replay: converte g_replayTime em shift de barras para qualquer TF
// (baseado no símbolo do gráfico — usado pela MATRIZ, paridade com v2.11)
int ShiftForTF(ENUM_TIMEFRAMES tf)
{
   if(!g_replayOn) return 1;
   int sh = MathMax(1, Bars(_Symbol, tf, g_replayTime, TimeCurrent()));
   datetime bo = iTime(_Symbol, tf, sh);
   if(bo > 0 && (long)bo + PeriodSeconds(tf) > (long)g_replayTime)
      sh++;   // barra ainda formando em g_replayTime -> recua p/ a última FECHADA
   return sh;
}

// Atualiza g_replayTime a partir do g_replayShift atual
void SyncReplayTime()
{
   datetime t[];
   if(CopyTime(_Symbol, _Period, g_replayShift, 1, t) == 1)
      g_replayTime = t[0];
}

// Âncora por par ANCORADA NO TEMPO (paridade com a pesquisa: cada par usa a
// própria última barra fechada; em replay, a última fechada até g_replayTime).
int MetAnchorShift(string sym, ENUM_TIMEFRAMES tf)
{
   if(!g_replayOn) return 1;
   int sh = MathMax(1, Bars(sym, tf, g_replayTime, TimeCurrent()));
   datetime bo = iTime(sym, tf, sh);
   if(bo > 0 && (long)bo + PeriodSeconds(tf) > (long)g_replayTime)
      sh++;   // barra ainda formando em g_replayTime -> recua p/ a última FECHADA
   return sh;
}


//+------------------------------------------------------------------+
//|              ML HELPERS (par ativo)                                |
//+------------------------------------------------------------------+
double Scale01(const double &arr[], int idx, int len)
{
   int start = MathMax(0, idx - len + 1);
   double lo = arr[start], hi = arr[start];
   for(int j = start + 1; j <= idx; j++)
   {
      if(arr[j] < lo) lo = arr[j];
      if(arr[j] > hi) hi = arr[j];
   }
   return (hi == lo) ? 0.5 : (arr[idx] - lo) / (hi - lo);
}

double Compress(double d) { return MathLog(1.0 + MathAbs(d)); }

double PercentRank(const double &arr[], int idx, int len)
{
   int start = MathMax(0, idx - len + 1);
   int count = 0, total = 0;
   double val = arr[idx];
   for(int j = start; j <= idx; j++) { total++; if(arr[j] < val) count++; }
   return total > 1 ? (double)count / (double)(total - 1) * 100.0 : 50.0;
}

double CalcStdev(const double &arr[], int idx, int len)
{
   int start = MathMax(0, idx - len + 1);
   int n = idx - start + 1;
   if(n < 2) return 0;
   double sum = 0;
   for(int j = start; j <= idx; j++) sum += arr[j];
   double mean = sum / n;
   double sq = 0;
   for(int j = start; j <= idx; j++) sq += (arr[j] - mean) * (arr[j] - mean);
   return MathSqrt(sq / n);
}

double GetVolume(const long &tick_vol[], const long &real_vol[], int i)
{
   if(real_vol[i] > 0) return (double)real_vol[i];
   if(tick_vol[i] > 0) return (double)tick_vol[i];
   return 1.0;
}

int ClassifyOutcome(const double &close[], const double &atr[], int i, int horizon, double factor)
{
   if(i < horizon) return 0;
   double moveFwd = close[i] - close[i - horizon];
   double band = factor * atr[i - horizon];
   if(band <= 0) band = 0.0001;
   if(moveFwd >  2.0 * band) return  3;
   if(moveFwd >  band)       return  2;
   if(moveFwd >  0)          return  1;
   if(moveFwd < -2.0 * band) return -3;
   if(moveFwd < -band)       return -2;
   if(moveFwd <  0)          return -1;
   return 0;
}

double WeightSum(const double &w[])
{
   double s = 0;
   for(int j = 0; j < 8; j++) s += w[j];
   return s;
}


//+------------------------------------------------------------------+
//|              FEATURE BANK OPERATIONS                               |
//+------------------------------------------------------------------+
void BankInit(int capacity)
{
   g_bankCapacity = capacity;
   g_bankSize = 0;
   g_bankNext = 0;
   g_lastBankBar = -1;
   ArrayResize(g_bank, capacity * BANK_COLS);
   ArrayInitialize(g_bank, 0);
}

void BankPush(const double &feat8[], double outcome)
{
   int base = g_bankNext * BANK_COLS;
   for(int c = 0; c < 8; c++) g_bank[base + c] = feat8[c];
   g_bank[base + 8] = outcome;
   g_bankNext = (g_bankNext + 1) % g_bankCapacity;
   if(g_bankSize < g_bankCapacity) g_bankSize++;
}

void BankGetRow(int logIdx, double &row9[])
{
   int phys = (g_bankNext - 1 - logIdx + g_bankCapacity * 2) % g_bankCapacity;
   int base = phys * BANK_COLS;
   for(int c = 0; c < BANK_COLS; c++) row9[c] = g_bank[base + c];
}


//+------------------------------------------------------------------+
//|              ML ENGINE — Fisher Auto Weights                       |
//+------------------------------------------------------------------+
void ComputeFisherWeights()
{
   if(g_bankSize < AUTO_MIN_ROWS) return;
   double sumB[8], sumBe[8], sqB[8], sqBe[8];
   ArrayInitialize(sumB, 0); ArrayInitialize(sumBe, 0);
   ArrayInitialize(sqB, 0);  ArrayInitialize(sqBe, 0);
   int cntB = 0, cntBe = 0;
   double row[9];
   for(int i = 0; i < g_bankSize; i++)
   {
      BankGetRow(i, row);
      if(row[8] == 0) continue;
      bool isB = (row[8] > 0);
      for(int j = 0; j < 8; j++)
      {
         double v = row[j];
         if(isB) { sumB[j] += v; sqB[j] += v * v; }
         else    { sumBe[j] += v; sqBe[j] += v * v; }
      }
      if(isB) cntB++; else cntBe++;
   }
   if(cntB < 3 || cntBe < 3) return;
   double maxF = 0;
   double fish[8];
   for(int j = 0; j < 8; j++)
   {
      double mB = sumB[j]/cntB, mBe = sumBe[j]/cntBe;
      double vB = MathMax(0.0, sqB[j]/cntB - mB*mB);
      double vBe = MathMax(0.0, sqBe[j]/cntBe - mBe*mBe);
      fish[j] = MathPow(mB - mBe, 2) / (vB + vBe + 1e-6);
      if(fish[j] > maxF) maxF = fish[j];
   }
   for(int j = 0; j < 8; j++)
   {
      double norm = maxF > 0 ? fish[j]/maxF : 1.0;
      double target = MathMax(AUTO_FLOOR, norm * 10.0);
      g_autoW[j] = g_autoW[j] + InpAdaptSpeed * (target - g_autoW[j]);
   }
}


//+------------------------------------------------------------------+
//|              ML ENGINE — kNN Search + Voting                       |
//+------------------------------------------------------------------+
struct SNeighbor { double gap; int cls; };
struct SEngine   { double analogScore; int biasDir; double agreeFrac; double gapTight; int k; };

double GapTo(const double &feat[], const double &row[], const double &wts[])
{
   double d = 0;
   for(int j = 0; j < 8; j++) d += wts[j] * Compress(feat[j] - row[j]);
   return d;
}

SEngine RunKNN(const double &feat[], const double &wts[])
{
   SEngine eng;
   eng.analogScore = 0; eng.biasDir = 0; eng.agreeFrac = 0;
   eng.gapTight = 0; eng.k = 0;
   if(g_bankSize < 2) return eng;
   SNeighbor nbrs[];
   ArrayResize(nbrs, 0);
   int scanEnd = MathMin(g_bankSize - 1, InpMemoryDepth - 1);
   double row[9];
   for(int idx = 0; idx <= scanEnd; idx++)
   {
      if(idx % SPACING_BARS != 0) continue;
      BankGetRow(idx, row);
      double g = GapTo(feat, row, wts);
      if(ArraySize(nbrs) < InpKNeighbors)
      {
         int sz = ArraySize(nbrs);
         ArrayResize(nbrs, sz + 1);
         nbrs[sz].gap = g; nbrs[sz].cls = (int)row[8];
      }
      else
      {
         int worst = 0; double worstGap = nbrs[0].gap;
         for(int j = 1; j < ArraySize(nbrs); j++)
            if(nbrs[j].gap > worstGap) { worstGap = nbrs[j].gap; worst = j; }
         if(g < worstGap) { nbrs[worst].gap = g; nbrs[worst].cls = (int)row[8]; }
      }
   }
   int kCount = ArraySize(nbrs);
   eng.k = kCount;
   if(kCount == 0) return eng;
   double totalW = 0, scoreW = 0, bullW = 0, bearW = 0, gapSum = 0;
   for(int j = 0; j < kCount; j++)
   {
      double w = 1.0 / (1.0 + nbrs[j].gap);
      totalW += w; scoreW += nbrs[j].cls * w;
      if(nbrs[j].cls > 0) bullW += w;
      else if(nbrs[j].cls < 0) bearW += w;
      gapSum += nbrs[j].gap;
   }
   eng.analogScore = totalW > 0 ? scoreW/totalW : 0;
   eng.biasDir = eng.analogScore > 0.15 ? 1 : eng.analogScore < -0.15 ? -1 : 0;
   if(totalW > 0 && eng.biasDir != 0)
      eng.agreeFrac = (eng.biasDir == 1 ? bullW : bearW) / totalW;
   double avgGap = kCount > 0 ? gapSum/kCount : 0;
   double gapScale = WeightSum(wts) * 0.45 + 1e-9;
   eng.gapTight = Clamp(1.0 - avgGap/gapScale, 0, 1);
   return eng;
}


//+------------------------------------------------------------------+
//|              RANK & CONFIDENCE                                     |
//+------------------------------------------------------------------+
double RankScore(const SEngine &eng, bool trendAligned, double atrPct,
                 bool volHealthy, bool chopRaw, bool slopeFit,
                 bool stretched, double oscReg, bool oscSmoothUp,
                 int stanceAge, bool earlyFlip)
{
   if(eng.biasDir == 0) return 0;
   double pAgree  = 25.0 * eng.agreeFrac;
   double pGap    = 15.0 * eng.gapTight;
   double pStruct = (slopeFit ? 10.0 : 0.0) + (stretched ? 0.0 : 5.0);
   double pTrend  = trendAligned ? 10.0 : 0.0;
   double pVol    = volHealthy ? 10.0 : atrPct < VOL_BAND_LO ? 5.0 : 3.0;
   bool regFit = (eng.biasDir == 1 && oscReg > 55) || (eng.biasDir == -1 && oscReg < 45);
   double pReg = regFit ? 10.0 : (oscReg >= 45 && oscReg <= 55) ? 4.0 : 6.0;
   double pSmooth = ((eng.biasDir==1 && oscSmoothUp) || (eng.biasDir==-1 && !oscSmoothUp)) ? 5.0 : 0.0;
   double pHold   = MathMin(5.0, (double)stanceAge);
   double pPen = MathMin(20.0,
      (chopRaw ? 8.0 : 0.0) + (stretched ? 6.0 : 0.0) +
      (earlyFlip ? 6.0 : 0.0) +
      (eng.k < InpKNeighbors ? 5.0*(InpKNeighbors-eng.k)/(double)InpKNeighbors : 0.0));
   return Clamp(pAgree+pGap+pStruct+pTrend+pVol+pReg+pSmooth+pHold-pPen, 0, 100);
}

double ConfScore(const SEngine &eng, bool slopeFit, int stanceAge, bool earlyFlip)
{
   if(eng.biasDir == 0) return 0;
   double raw = 40.0*eng.agreeFrac + 25.0*eng.gapTight
              + 15.0*MathMin(1.0, stanceAge/5.0) + 10.0*(slopeFit?1.0:0.0)
              - (earlyFlip?15.0:0.0)
              - (eng.k<InpKNeighbors ? 10.0*(InpKNeighbors-eng.k)/(double)InpKNeighbors : 0.0);
   return Clamp(raw, 0, 100);
}


//+------------------------------------------------------------------+
//|             IFM MODULES — Active Pair (full, from chart data)      |
//+------------------------------------------------------------------+
int CalcPivotScore(const double &high[], const double &low[], const double &close[], int i)
{
   if(i < 1) return 0;
   double pp = (high[i-1] + low[i-1] + close[i-1]) / 3.0;
   double r1 = 2.0 * pp - low[i-1];
   double s1 = 2.0 * pp - high[i-1];
   double c = close[i];
   if(c > pp && c > r1)      return  2;
   if(c > pp)                return  1;
   if(c < pp && c < s1)      return -2;
   if(c < pp)                return -1;
   return 0;
}

int CalcMPScore(const double &close[], const double &ema21[], int i)
{
   if(i < 1) return 0;
   double poc = ema21[i], pocP = ema21[i-1];
   double vah = poc * 1.01, val = poc * 0.99;
   double c = close[i];
   if(c > vah && poc > pocP)  return  2;
   if(c > vah)                return  1;
   if(c < val && poc < pocP)  return -2;
   if(c < val)                return -1;
   return 0;
}

int CalcMFCScore(const double &high[], const double &low[],
                 const long &tick_vol[], const long &real_vol[],
                 int i, int volLen, int &mfcColor)
{
   mfcColor = 3;
   if(i < 1) return 0;
   double vol  = GetVolume(tick_vol, real_vol, i);
   double volP = GetVolume(tick_vol, real_vol, i - 1);
   double mfc  = vol > 0 ? (high[i] - low[i]) / vol : 0;
   double mfcP = volP > 0 ? (high[i-1] - low[i-1]) / volP : 0;
   double avgVol = 0; int cnt = 0;
   int start = MathMax(0, i - volLen + 1);
   for(int j = start; j <= i; j++) { avgVol += GetVolume(tick_vol, real_vol, j); cnt++; }
   avgVol = cnt > 0 ? avgVol / cnt : 1;
   bool varPreco = mfc > mfcP, varVolume = GetVolume(tick_vol, real_vol, i) > avgVol;
   if(varPreco && varVolume)    { mfcColor = 0; return  1; }
   if(!varPreco && varVolume)   { mfcColor = 1; return -1; }
   if(varPreco && !varVolume)   { mfcColor = 2; return  0; }
   mfcColor = 3; return 0;
}

int CalcCCIScore(const double &cci[], int i)
{
   double c = cci[i];
   if(c > 0 && c > 100)   return  2;
   if(c > 0)              return  1;
   if(c < 0 && c < -100)  return -2;
   if(c < 0)              return -1;
   return 0;
}

int CalcMLRSIScore(int biasDir, double rank, double conf)
{
   if(biasDir== 1 && rank>=InpGateRank && conf>=InpGateConf) return  2;
   if(biasDir== 1)                                           return  1;
   if(biasDir==-1 && rank>=InpGateRank && conf>=InpGateConf) return -2;
   if(biasDir==-1)                                           return -1;
   return 0;
}


//+------------------------------------------------------------------+
//|       IFM LIGHT ENGINE — Modules from CopyRates (any pair)        |
//+------------------------------------------------------------------+

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
// Contínuo — remove a quantização de ~0.476 da força S.
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
// Janela efetiva LIMITADA a LIGHT_WINDOW (paridade com src/metrics.py do V2).
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

   //--- Module 2 (Market Profile): REMOVIDO na v1.2 — era código morto:
   //    o guard exigia 3×21+2 = 65 barras com a janela capada em LIGHT_WINDOW
   //    (60) → o voto era SEMPRE 0 (arqueologia E2 da pesquisa 2026-07).
   //    A escala ±15 da agregação é MANTIDA (continuidade numérica: S idêntico
   //    ao v1.0/v1.1 e à paridade P1 da pesquisa). O guard de barras mínimas
   //    acima também mantém InpEMAFallbackLen DE PROPÓSITO (mesmo motivo).

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

   //--- Aggregation: Pivot×2 + MFC×1 + CCI×3 (escala ±15 mantida — o slot do
   //    MP morto continua contando no denominador para preservar os números)
   double bruto = scorePivot * 2.0 + scoreMFC * 1.0 + scoreCCI * 3.0;
   double ifmFinal = (bruto + 15.0) / 30.0 * 100.0;
   return Clamp(ifmFinal, 0, 100);
}

// Wrapper: copia LIGHT_WINDOW barras e computa no índice 0.
double CalcIFMLight(string pair, ENUM_TIMEFRAMES tf, int shift)
{
   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   int copied = CopyRates(pair, tf, shift, LIGHT_WINDOW, rates);
   if(copied <= 0) return 50.0;
   return CalcIFMLightAt(rates, 0, copied);
}


//+------------------------------------------------------------------+
//|         CURRENCY STRENGTH AGGREGATION (rodapé da matriz)           |
//+------------------------------------------------------------------+
int ComputeCurrencyStrength(ENUM_TIMEFRAMES tf, int shift, double &out[])
{
   double acc[8];
   ArrayInitialize(acc, 0);
   int good = 0;

   for(int p = 0; p < g_pairsN; p++)
   {
      double ifm = CalcIFMLight(g_pair[p], tf, shift);
      if(ifm < 0) continue;
      good++;
      double dir = (ifm - 50.0) / 50.0;   // -1 a +1
      acc[g_baseIdx[p]]  += dir;
      acc[g_quoteIdx[p]] -= dir;
   }

   for(int c = 0; c < 8; c++)
   {
      if(g_cnt[c] > 0) out[c] = 50.0 + (acc[c] / g_cnt[c]) * 50.0;
      else             out[c] = 50.0;
   }
   return good;
}


//+------------------------------------------------------------------+
//|              PANEL UI — Drawing primitives (modern style)           |
//+------------------------------------------------------------------+
#define COL_BG_MAIN     C'16,16,24'
#define COL_BG_CARD     C'24,26,36'
#define COL_BG_CELL     C'32,34,44'
#define COL_BG_STRONG   C'14,72,34'
#define COL_BG_WEAK     C'92,18,24'
#define COL_ACCENT      C'66,135,245'
#define COL_GOLD        C'218,175,62'
#define COL_BORDER      C'44,46,58'
#define COL_TEXT        C'210,212,220'
#define COL_TEXT_DIM    C'130,132,142'
#define COL_TEXT_MUTED  C'90,92,100'

void Lbl(string nm, int win, int x, int y, string txt, color cl, int fontSize=-1,
         int anchor=ANCHOR_LEFT_UPPER, string font="Segoe UI")
{
   if(ObjectFind(0,nm)<0) ObjectCreate(0,nm,OBJ_LABEL,win,0,0);
   ObjectSetInteger(0,nm,OBJPROP_XDISTANCE,x);
   ObjectSetInteger(0,nm,OBJPROP_YDISTANCE,y);
   ObjectSetInteger(0,nm,OBJPROP_CORNER,CORNER_LEFT_UPPER);
   ObjectSetInteger(0,nm,OBJPROP_ANCHOR,anchor);
   ObjectSetString (0,nm,OBJPROP_TEXT,txt);
   ObjectSetString (0,nm,OBJPROP_FONT,font);
   ObjectSetInteger(0,nm,OBJPROP_FONTSIZE, fontSize>0 ? fontSize : InpFont);
   ObjectSetInteger(0,nm,OBJPROP_COLOR,cl);
   ObjectSetInteger(0,nm,OBJPROP_BACK,false);
   ObjectSetInteger(0,nm,OBJPROP_SELECTABLE,false);
}

// Interpola linearmente entre duas cores (t em 0..1)
color LerpColor(color a, color b, double t)
{
   t = Clamp(t, 0.0, 1.0);
   int ar = (int)(a & 0xFF),  ag = (int)((a >> 8) & 0xFF),  ab = (int)((a >> 16) & 0xFF);
   int br = (int)(b & 0xFF),  bg = (int)((b >> 8) & 0xFF),  bb = (int)((b >> 16) & 0xFF);
   int r = ar + (int)MathRound((br - ar) * t);
   int g = ag + (int)MathRound((bg - ag) * t);
   int bl= ab + (int)MathRound((bb - ab) * t);
   return (color)((bl << 16) | (g << 8) | r);
}

// Gradiente de força 0-100: vermelho <- neutro (50) -> verde
color GradeColor(double v)
{
   double t = Clamp((v - 50.0) / 50.0, -1.0, 1.0);
   if(t >= 0) return LerpColor(COL_BG_CELL, C'10,124,58',  t);
   else       return LerpColor(COL_BG_CELL, C'160,32,40', -t);
}

void Rect(string nm, int win, int x, int y, int w, int hgt, color bg, color border=COL_BORDER)
{
   if(ObjectFind(0,nm)<0) ObjectCreate(0,nm,OBJ_RECTANGLE_LABEL,win,0,0);
   ObjectSetInteger(0,nm,OBJPROP_XDISTANCE,x);
   ObjectSetInteger(0,nm,OBJPROP_YDISTANCE,y);
   ObjectSetInteger(0,nm,OBJPROP_XSIZE,w);
   ObjectSetInteger(0,nm,OBJPROP_YSIZE,hgt);
   ObjectSetInteger(0,nm,OBJPROP_BGCOLOR,bg);
   ObjectSetInteger(0,nm,OBJPROP_BORDER_TYPE,BORDER_FLAT);
   ObjectSetInteger(0,nm,OBJPROP_COLOR,border);
   ObjectSetInteger(0,nm,OBJPROP_CORNER,CORNER_LEFT_UPPER);
   ObjectSetInteger(0,nm,OBJPROP_BACK,false);
   ObjectSetInteger(0,nm,OBJPROP_SELECTABLE,false);
}

// Flat button = rect + label centralizado ("_t" removido no OnChartEvent)
void FlatBtn(string nm, int win, int x, int y, int w, int h,
             string txt, bool active, color activeBg, int fs=8)
{
   color bg  = active ? activeBg : C'38,40,52';
   color brd = active ? activeBg : COL_BORDER;
   color tc  = active ? clrBlack : COL_TEXT;
   Rect(nm, win, x, y, w, h, bg, brd);
   string ln = nm + "_t";
   if(ObjectFind(0,ln) < 0) ObjectCreate(0,ln,OBJ_LABEL,win,0,0);
   ObjectSetInteger(0,ln,OBJPROP_CORNER,CORNER_LEFT_UPPER);
   ObjectSetInteger(0,ln,OBJPROP_ANCHOR,ANCHOR_CENTER);
   ObjectSetInteger(0,ln,OBJPROP_XDISTANCE,x + w/2);
   ObjectSetInteger(0,ln,OBJPROP_YDISTANCE,y + h/2);
   ObjectSetString (0,ln,OBJPROP_TEXT,txt);
   ObjectSetString (0,ln,OBJPROP_FONT,"Segoe UI Semibold");
   ObjectSetInteger(0,ln,OBJPROP_FONTSIZE,fs);
   ObjectSetInteger(0,ln,OBJPROP_COLOR,tc);
   ObjectSetInteger(0,ln,OBJPROP_BACK,false);
   ObjectSetInteger(0,ln,OBJPROP_SELECTABLE,false);
}

void DelBtn(string nm) { ObjectDelete(0,nm); ObjectDelete(0,nm+"_t"); }


//+------------------------------------------------------------------+
//|     VISTA MÉTRICAS — METRICS_SPEC v1.0 (+ abas M5/M15)             |
//+------------------------------------------------------------------+
// Série S CRONOLÓGICA s[0..n-1], s[n-1] = t0. EMPTY_VALUE sinaliza NaN
// (dado insuficiente/par faltante) e propaga — nunca imputar neutro.

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

// z-score de passeio aleatório da velocidade: VEL(k) / (sigma(dS) * sqrt(k)).
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
//|  SCORE 0-100 (v1.2) — pesos CONGELADOS da pesquisa 2026-07        |
//|  reatividade-metricas, etapa E10 (results/E10_score_pesos.csv).   |
//|  Score = 100·sigmoide(Σ coef·(x−média)/desvio + intercepto).      |
//|  Aprovado no teste selado como DETECTOR (C10/P4) — NÃO é sinal    |
//|  de entrada. NÃO recalibrar sem novo período selado.              |
//+------------------------------------------------------------------+
#define SCORE_NF 14
// ordem das features: zs, zvel, vel, acel, zmov, zhist, cesta, mtf,
//                     hora, min_sessao, alin_MN1, alin_W1, alin_D1, alin_H4
double SCORE_MU[SCORE_NF] =
   {0.836276, 0.2892, 7.77755, 5.676939, 0.000504, -0.005809, 0.764245,
    2.913547, 0.531649, 0.610749, 0.505671, 0.504983, 0.439879, 0.606155};
double SCORE_SD[SCORE_NF] =
   {0.548117, 0.520756, 14.041791, 25.917648, 0.999322, 1.180584, 0.181649,
    0.879155, 0.260911, 0.261333, 0.499968, 0.499976, 0.496373, 0.488602};
double SCORE_W[SCORE_NF] =
   {0.317396, -0.088382, -0.043696, -0.01642, 0.122806, -0.006475, 0.242093,
    0.124421, -0.557324, -0.054429, -0.113431, 0.078104, -0.160426, 0.258546};
#define SCORE_B    (-4.990688)   // intercepto
#define SCORE_CUT  3.4036        // corte p97 congelado, em pontos 0-100

// Frações de coluna da vista MÉTRICAS (12 col. com SCORE/dia%; 10 sem)
double MET_COLX12[12] = {0.02, 0.09, 0.185, 0.255, 0.325, 0.395, 0.465,
                         0.535, 0.605, 0.675, 0.765, 0.855};
double MET_COLX10[10] = {0.02, 0.10, 0.225, 0.315, 0.40, 0.495, 0.585,
                         0.675, 0.765, 0.865};
double ColXf(int i) { return InpShowScore ? MET_COLX12[i] : MET_COLX10[i]; }

// --- DST em nível de DIA (paridade com o flag_dst do banco da pesquisa:
//     dst() da meia-noite da data). Server = Europe/Athens (DST europeu).
int DowOf(int y, int m, int d)
{
   MqlDateTime st;
   st.year = y; st.mon = m; st.day = d;
   st.hour = 0; st.min = 0; st.sec = 0;
   datetime t = StructToTime(st);
   TimeToStruct(t, st);
   return st.day_of_week;
}

int LastSundayDom(int y, int m)
{
   for(int d = 31; d >= 25; d--)
      if(DowOf(y, m, d) == 0) return d;
   return 25;
}

int NthSundayDom(int y, int m, int n)
{
   int seen = 0;
   for(int d = 1; d <= 28; d++)
      if(DowOf(y, m, d) == 0) { seen++; if(seen == n) return d; }
   return 1;
}

// DST europeu ativo na meia-noite da data? (vira no último domingo de mar/out)
bool EuDstDay(int y, int m, int d)
{
   if(m < 3 || m > 10) return false;
   if(m > 3 && m < 10) return true;
   if(m == 3)  return d > LastSundayDom(y, 3);
   return d <= LastSundayDom(y, 10);          // outubro
}

// DST americano ativo na meia-noite da data? (2º dom/mar → 1º dom/nov)
bool UsDstDay(int y, int m, int d)
{
   if(m < 3 || m > 11) return false;
   if(m > 3 && m < 11) return true;
   if(m == 3)  return d > NthSundayDom(y, 3, 2);
   return d <= NthSundayDom(y, 11, 1);        // novembro
}

// Sessão/minutos/hora da barra FECHADA em barClose (hora do servidor).
// Slots de 30 min com prioridade Tóquio > Londres > NY e janelas calibradas
// no E1 da pesquisa (Tóquio desliza com o DST europeu; NY com o descasamento
// EUA×Europa). sessIdx: 0=Tóquio 1=Londres 2=NY, -1=fora.
void SessionOf(datetime barClose, int &sessIdx, double &minSess, double &horaFrac)
{
   long sec = (long)barClose % 86400;
   horaFrac = MathFloor((double)sec / 3600.0) / 24.0;   // t.hour/24 (do fechamento)
   datetime day = barClose - (datetime)sec;
   int slot = (int)(sec / 1800) - 1;
   if(slot < 0) { slot = 47; day -= 86400; }
   MqlDateTime st;
   TimeToStruct(day, st);
   bool eu = EuDstDay(st.year, st.mon, st.day);
   bool us = UsDstDay(st.year, st.mon, st.day);
   int tqIni = eu ? 6 : 4;                    // 09:00 Tóquio em hora server
   int tqFim = tqIni + 18;                    // 9h de sessão = 18 slots
   int loIni = 20, loFim = 38;                // Londres: estável (DST UK = EU)
   int nyIni = 2 * (12 + (us ? 0 : 1) + (eu ? 3 : 2));   // 08:00 NY -> server
   int nyFim = MathMin(nyIni + 18, 48);
   sessIdx = -1;
   int ini = 0;
   if(slot >= nyIni && slot < nyFim) { sessIdx = 2; ini = nyIni; }
   if(slot >= loIni && slot < loFim) { sessIdx = 1; ini = loIni; }
   if(slot >= tqIni && slot < tqFim) { sessIdx = 0; ini = tqIni; }
   minSess = (sessIdx >= 0) ? (slot - ini + 1) * 30.0 : 0.0;
}

// Força S por moeda no t0 de um TF fora do ring (W1/MN1 — contexto do Score).
// Mesma regra de NaN do ring: só vale com TODOS os pares da moeda presentes.
void CtxStrength(ENUM_TIMEFRAMES tf, double &out[])
{
   double acc[8];
   int okc[8];
   ArrayInitialize(acc, 0.0);
   ArrayInitialize(okc, 0);
   for(int p = 0; p < g_pairsN && p < MET_MAXP; p++)
   {
      int anchor = MetAnchorShift(g_pair[p], tf);
      MqlRates rates[];
      ArraySetAsSeries(rates, true);
      int copied = CopyRates(g_pair[p], tf, anchor, LIGHT_WINDOW, rates);
      if(copied < LIGHT_WINDOW) continue;     // janela incompleta => par não conta
      double ifm = CalcIFMLightAt(rates, 0, copied);
      double dir = (ifm - 50.0) / 50.0;
      acc[g_baseIdx[p]]  += dir;  okc[g_baseIdx[p]]++;
      acc[g_quoteIdx[p]] -= dir;  okc[g_quoteIdx[p]]++;
   }
   for(int c = 0; c < 8; c++)
      out[c] = (g_cnt[c] > 0 && okc[c] == g_cnt[c])
               ? 50.0 + (acc[c] / g_cnt[c]) * 50.0
               : EMPTY_VALUE;
}

// Rebuild completo do ring: por par/TF, UMA cópia de 60+64-1 barras e IFM em
// todos os offsets do mesmo array. Âncora = última barra FECHADA (shift 1).
void MetRebuild()
{
   for(int t = 0; t < MET_TFN; t++)
   {
      ENUM_TIMEFRAMES tf = g_metTFs[t];
      double acc[8][MET_RING];
      int    okc[8][MET_RING];
      for(int c = 0; c < 8; c++)
         for(int j = 0; j < MET_RING; j++) { acc[c][j] = 0.0; okc[c][j] = 0; }
      double ifmNow[MET_MAXP];
      for(int p = 0; p < MET_MAXP; p++) ifmNow[p] = EMPTY_VALUE;

      for(int p = 0; p < g_pairsN && p < MET_MAXP; p++)
      {
         int anchor = MetAnchorShift(g_pair[p], tf);
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
            if(j == MET_RING - 1) ifmNow[p] = ifm;
         }
      }
      for(int c = 0; c < 8; c++)
         for(int j = 0; j < MET_RING; j++)
            g_metS[c][t][j] = (g_cnt[c] > 0 && okc[c][j] == g_cnt[c])
                              ? 50.0 + (acc[c][j] / g_cnt[c]) * 50.0
                              : EMPTY_VALUE;

      // CESTA no t0 (lado-consciente, denominador = nº de pares da moeda)
      for(int c = 0; c < 8; c++)
      {
         double s0 = g_metS[c][t][MET_RING-1];
         int lado = MetIsNan(s0) ? 0 : MetSign(s0 - 50.0);
         if(lado == 0 || g_cnt[c] == 0) { g_metCesta[c][t] = EMPTY_VALUE; continue; }
         int conf = 0;
         bool bad = false;
         for(int p = 0; p < g_pairsN && p < MET_MAXP; p++)
         {
            if(g_baseIdx[p] != c && g_quoteIdx[p] != c) continue;
            if(MetIsNan(ifmNow[p])) { bad = true; break; }
            int pside = MetSign(ifmNow[p] - 50.0);
            if(pside == 0) continue;
            if((g_baseIdx[p] == c) ? (pside == lado) : (pside == -lado)) conf++;
         }
         g_metCesta[c][t] = bad ? EMPTY_VALUE : (double)conf / g_cnt[c];
      }
   }

   // zMov / zMovH: z-scores do movimento de cesta desde 00:00 em ATRs.
   // Cada dia passado é medido ATÉ A MESMA HORA decorrida do dia atual.
   // Dia 0 = a última barra D1 FECHADA (intradiário: ontem) — semântica
   // OFICIAL do cálculo (decisão 2026-07-16; o GUIA §10 a descreve).
   {
      datetime barT = iTime(g_pair[0], PERIOD_M30, MetAnchorShift(g_pair[0], PERIOD_M30));
      datetime dayStart = barT - (datetime)((long)barT % 86400);
      long tod = ((long)barT + PeriodSeconds(PERIOD_M30)) - (long)dayStart; // até o CLOSE da âncora
      int nH = (int)MathMin(MathMax(InpZMovN, 5), 38);

      double movDay[8][40];
      int    cntDay[8][40];
      bool   badDay[8][40];
      double movFull[8][40];        // v1.2: movimento do dia CHEIO (p/ o típico)
      double movHoje[8];            // v1.2: movimento do dia CORRENTE até a âncora
      int    cntHoje[8];
      bool   badHoje[8];
      for(int c = 0; c < 8; c++)
      {
         movHoje[c] = 0.0; cntHoje[c] = 0; badHoje[c] = false;
         for(int i = 0; i <= nH; i++)
         { movDay[c][i] = 0.0; cntDay[c][i] = 0; badDay[c][i] = false; movFull[c][i] = 0.0; }
      }

      for(int p = 0; p < g_pairsN && p < MET_MAXP; p++)
      {
         int shD = MetAnchorShift(g_pair[p], PERIOD_D1);
         for(int i = 0; i <= nH; i++)
         {
            int d1sh = shD + i;
            datetime ds = iTime(g_pair[p], PERIOD_D1, d1sh);
            bool pOk = (ds > 0);
            double r = 0, rFull = 0;
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
               double cD = iClose(g_pair[p], PERIOD_D1, d1sh);   // v1.2: fechamento do dia CHEIO
               pOk = (nOk == 14 && refC > 0 && c0 > 0 && c1 > 0 && cD > 0 && atr > 0);
               if(pOk)
               {
                  double band = (atr / 14.0) / refC;
                  r     = MathLog(c1 / c0) / band;
                  rFull = MathLog(cD / refC) / band;
               }
            }
            if(pOk) { movDay[g_baseIdx[p]][i] += r;      cntDay[g_baseIdx[p]][i]++;
                      movDay[g_quoteIdx[p]][i] -= r;     cntDay[g_quoteIdx[p]][i]++;
                      movFull[g_baseIdx[p]][i] += rFull;
                      movFull[g_quoteIdx[p]][i] -= rFull; }
            else    { badDay[g_baseIdx[p]][i] = true; badDay[g_quoteIdx[p]][i] = true; }
         }

         // v1.2 — dia CORRENTE (em formação) até a âncora M30: consumo do dia.
         // "Preço atual" = fechamento da âncora M30 do par (respeita o replay;
         // sem look-ahead). Referência = fechamento do dia anterior, como no zMov.
         {
            int shT = shD - 1;
            datetime dsT = (shT >= 0) ? iTime(g_pair[p], PERIOD_D1, shT) : 0;
            bool tOk = (dsT > 0);
            double rT = 0;
            if(tOk)
            {
               double atr = 0; int nOk = 0;
               for(int j = shT + 1; j <= shT + 14; j++)
               {
                  double hi = iHigh(g_pair[p], PERIOD_D1, j), lo = iLow(g_pair[p], PERIOD_D1, j);
                  double pc = iClose(g_pair[p], PERIOD_D1, j + 1);
                  if(hi <= 0 || lo <= 0 || pc <= 0) break;
                  atr += MathMax(hi - lo, MathMax(MathAbs(hi - pc), MathAbs(lo - pc)));
                  nOk++;
               }
               double refC = iClose(g_pair[p], PERIOD_D1, shT + 1);
               int sh0 = iBarShift(g_pair[p], PERIOD_M30, dsT - 1, false);
               int shN = MetAnchorShift(g_pair[p], PERIOD_M30);
               double c0 = (sh0 >= 0) ? iClose(g_pair[p], PERIOD_M30, sh0) : 0.0;
               double cN = iClose(g_pair[p], PERIOD_M30, shN);
               tOk = (nOk == 14 && refC > 0 && c0 > 0 && cN > 0 && atr > 0);
               if(tOk) rT = MathLog(cN / c0) / ((atr / 14.0) / refC);
            }
            if(tOk) { movHoje[g_baseIdx[p]] += rT;  cntHoje[g_baseIdx[p]]++;
                      movHoje[g_quoteIdx[p]] -= rT; cntHoje[g_quoteIdx[p]]++; }
            else    { badHoje[g_baseIdx[p]] = true; badHoje[g_quoteIdx[p]] = true; }
         }
      }

      double m0[8]; bool ok0[8];
      for(int c = 0; c < 8; c++)
      {
         ok0[c] = (!badDay[c][0] && g_cnt[c] > 0 && cntDay[c][0] == g_cnt[c]);
         m0[c] = ok0[c] ? movDay[c][0] : 0.0;

         // z histórico da própria moeda
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
            g_metZMovH[c] = (sd < 1e-9) ? EMPTY_VALUE : (m0[c] - mean) / sd;
         }
         else g_metZMovH[c] = EMPTY_VALUE;
      }

      // z transversal do dia corrente
      double sum8 = 0, ss8 = 0; int m8 = 0;
      for(int c = 0; c < 8; c++)
         if(ok0[c]) { sum8 += m0[c]; ss8 += m0[c] * m0[c]; m8++; }
      double mean8 = (m8 > 0) ? sum8 / m8 : 0.0;
      double sd8 = (m8 >= 4) ? MathSqrt(MathMax(ss8 / m8 - mean8 * mean8, 0.0)) : 0.0;
      for(int c = 0; c < 8; c++)
         g_metZMov[c] = (ok0[c] && sd8 > 1e-9) ? (m0[c] - mean8) / sd8 : EMPTY_VALUE;

      // v1.2 — consumo do dia: |movimento de HOJE até agora| ÷ média dos
      // |dias cheios| válidos (últimos nH). 💡 O relógio de exaustão da
      // pesquisa (E6/E8): captura restante despenca conforme o dia se consome.
      for(int c = 0; c < 8; c++)
      {
         g_metConsumo[c] = EMPTY_VALUE;
         if(badHoje[c] || g_cnt[c] == 0 || cntHoje[c] != g_cnt[c]) continue;
         double sumF = 0; int mF = 0;
         for(int i = 0; i < nH; i++)
         {
            if(badDay[c][i] || cntDay[c][i] != g_cnt[c]) continue;
            sumF += MathAbs(movFull[c][i]); mF++;
         }
         if(mF < 10 || sumF < 1e-9) continue;
         g_metConsumo[c] = MathAbs(movHoje[c]) / (sumF / mF) * 100.0;
      }
   }

   // --- v1.2: SCORE 0-100 (E10) — base M30, mesma linha de features da
   //     pesquisa; qualquer feature indisponível (NaN) => Score indefinido.
   for(int c = 0; c < 8; c++) g_metScore[c] = EMPTY_VALUE;
   if(InpShowScore)
   {
      double sW1[8], sMN[8];
      CtxStrength(PERIOD_W1, sW1);
      CtxStrength(PERIOD_MN1, sMN);

      // z transversal do S no M30 (mesma regra do render: >= 4 moedas válidas)
      double sum30 = 0, ss30 = 0; int m30 = 0;
      for(int c = 0; c < 8; c++)
      {
         double sv = g_metS[c][TF_M30_IDX][MET_RING-1];
         if(MetIsNan(sv)) continue;
         sum30 += sv; ss30 += sv * sv; m30++;
      }
      double mean30 = (m30 > 0) ? sum30 / m30 : 50.0;
      double sd30 = (m30 >= 4) ? MathSqrt(MathMax(ss30 / m30 - mean30 * mean30, 0.0)) : 0.0;

      // relógio da âncora M30 (hora do fechamento + minutos da sessão)
      datetime barT30 = (g_pairsN > 0)
                        ? iTime(g_pair[0], PERIOD_M30, MetAnchorShift(g_pair[0], PERIOD_M30)) : 0;
      int sessIdx = -1; double minSess = 0, horaFrac = 0;
      if(barT30 > 0)
         SessionOf(barT30 + PeriodSeconds(PERIOD_M30), sessIdx, minSess, horaFrac);

      if(m30 >= 4 && sd30 > 1e-9 && sessIdx >= 0)   // fora do dia de negociação: sem Score
      for(int c = 0; c < 8; c++)
      {
         double serie[MET_RING];
         for(int j = 0; j < MET_RING; j++) serie[j] = g_metS[c][TF_M30_IDX][j];
         double s0 = serie[MET_RING-1];
         if(MetIsNan(s0)) continue;
         double zs = (s0 - mean30) / sd30;
         int lado = MetSign(zs);
         if(lado == 0) continue;
         double vel   = MetVel(serie, InpMetVelK);
         double acel  = MetAcel(serie, InpMetVelK);
         double zvel  = MetZVel(serie, InpMetVelK, InpZVelN);
         double cesta = g_metCesta[c][TF_M30_IDX];
         double zmv   = g_metZMov[c];
         double zmh   = g_metZMovH[c];
         double sH1   = g_metS[c][TF_H1_IDX][MET_RING-1];
         double sH4   = g_metS[c][TF_H4_IDX][MET_RING-1];
         double sD1   = g_metS[c][TF_D1_IDX][MET_RING-1];
         if(MetIsNan(vel) || MetIsNan(acel) || MetIsNan(zvel) || MetIsNan(cesta) ||
            MetIsNan(zmv) || MetIsNan(zmh) || MetIsNan(sH1) || MetIsNan(sH4) ||
            MetIsNan(sD1) || MetIsNan(sW1[c]) || MetIsNan(sMN[c])) continue;
         int refSide = MetSign(sH1 - 50.0);
         if(refSide == 0) continue;                  // mtf indefinido
         int mtf = 0;
         for(int t2 = TF_M30_IDX; t2 <= TF_D1_IDX; t2++)
         {
            double sv = g_metS[c][t2][MET_RING-1];
            if(!MetIsNan(sv) && MetSign(sv - 50.0) == refSide) mtf++;
         }
         double x[SCORE_NF];
         x[0]  = zs * lado;                          // features assinadas pelo lado
         x[1]  = zvel * lado;
         x[2]  = vel * lado;
         x[3]  = acel * lado;
         x[4]  = zmv * lado;
         x[5]  = zmh * lado;
         x[6]  = cesta;                              // fração 0-1
         x[7]  = mtf;
         x[8]  = horaFrac;
         x[9]  = minSess / 540.0;
         x[10] = (MetSign(sMN[c] - 50.0) == lado) ? 1.0 : 0.0;
         x[11] = (MetSign(sW1[c] - 50.0) == lado) ? 1.0 : 0.0;
         x[12] = (MetSign(sD1 - 50.0) == lado) ? 1.0 : 0.0;
         x[13] = (MetSign(sH4 - 50.0) == lado) ? 1.0 : 0.0;
         double z = SCORE_B;
         for(int f = 0; f < SCORE_NF; f++)
            z += SCORE_W[f] * (x[f] - SCORE_MU[f]) / SCORE_SD[f];
         g_metScore[c] = 100.0 / (1.0 + MathExp(-z));
      }
   }
   g_metDirty = false;
}

// Rank 1 = mais forte por S em H1; desempate: CESTA desc, depois alfabética.
void MetRankH1(int &rank[])
{
   int ord[8];
   for(int i = 0; i < 8; i++) ord[i] = i;
   for(int i = 0; i < 8; i++)
      for(int j = i + 1; j < 8; j++)
      {
         int a = ord[i], b = ord[j];
         double sa = g_metS[a][TF_H1_IDX][MET_RING-1], sb = g_metS[b][TF_H1_IDX][MET_RING-1];
         double ca = g_metCesta[a][TF_H1_IDX], cb = g_metCesta[b][TF_H1_IDX];
         double sa2 = MetIsNan(sa) ? -1e9 : sa, sb2 = MetIsNan(sb) ? -1e9 : sb;
         double ca2 = MetIsNan(ca) ? -1.0 : ca, cb2 = MetIsNan(cb) ? -1.0 : cb;
         bool swap = (sb2 > sa2) ||
                     (sb2 == sa2 && cb2 > ca2) ||
                     (sb2 == sa2 && cb2 == ca2 && StringCompare(g_cur[b], g_cur[a]) < 0);
         if(swap) { ord[i] = b; ord[j] = a; }
      }
   for(int i = 0; i < 8; i++) rank[ord[i]] = i + 1;
}

string MetNum(double v, int digits, bool forceSign)
{
   if(MetIsNan(v)) return ShortToString(0x2014);   // "—"
   string s = DoubleToString(v, digits);
   if(forceSign && v > 0) s = "+" + s;
   return s;
}

void RenderMetrics(int win, int x, int y, int w, int h)
{
   if(g_metDirty) MetRebuild();

   Rect(TPFX+"bg", win, x, y, w, h, COL_BG_CARD, COL_BORDER);
   Rect(TPFX+"accent", win, x, y, w, 2, C'0,190,210', C'0,190,210');

   int pad  = 6;
   int slot = (int)Clamp((h - pad*3) / 12.0, 13, 42);
   int fs   = (int)Clamp(slot * 0.40, 7, 14);

   // Abas compactas (pills de largura fixa, alinhadas à esquerda):
   // M5 / M15 / M30 / H1 / H4 / D1
   int segY   = y + pad + 2;
   int pillW  = (int)Clamp((w - pad*2) / (double)MET_TFN - 4, 34, 64);
   for(int t = 0; t < MET_TFN; t++)
   {
      int bx0 = x + pad + t * (pillW + 4);
      FlatBtn(TPFX+"tf"+(string)t, win, bx0, segY, pillW, slot,
              g_metTfName[t], t == g_metTFIdx, C'0,190,210', (int)Clamp(fs-1, 6, 12));
   }

   int tsel = g_metTFIdx;
   // Título na mesma linha das abas (à direita), economizando um slot vertical
   Lbl(TPFX+"hd", win, x + pad + MET_TFN*(pillW+4) + 10, segY + slot/2,
       StringFormat("METRICAS-Z %s %s", ShortToString(0x00B7), g_metTfName[tsel]),
       COL_TEXT_DIM, fs, ANCHOR_LEFT);

   // Largura útil da tabela: limita para as colunas não "esticarem" demais
   // em janelas muito largas (mantém a leitura compacta à esquerda)
   int tblW = InpShowScore
              ? (int)MathMin((double)(w - pad*2), MathMax(900.0, fs * 108.0))
              : (int)MathMin((double)(w - pad*2), MathMax(760.0, fs * 92.0));

   // Colunas (frações da largura útil via ColXf) — col 0 = "#/moeda";
   // v1.2 acrescenta dia% (consumo) e SCORE (E10) quando InpShowScore
   int nCols = InpShowScore ? 12 : 10;
   string hdr[12] = {"moeda","força","zS","vel","zvel","acel","zMov","zHist",
                     "cesta","mtf","dia%","SCORE"};
   int yHdr = segY + slot + 4;
   Rect(TPFX+"hdbg", win, x+2, yHdr, w-4, slot-1, C'30,32,44', C'30,32,44');
   for(int i = 0; i < nCols; i++)
      Lbl(TPFX+"ch"+(string)i, win, x + pad + (int)(ColXf(i)*tblW),
          yHdr + slot/2, hdr[i], COL_TEXT_MUTED, fs-1, ANCHOR_LEFT);

   int gridY = yHdr + slot;
   int gridH = (y + h - pad) - gridY - slot;

   int rankH1[8];
   MetRankH1(rankH1);

   // z transversal: média e sigma (populacional) dos S válidos no t0 do TF.
   double xsMean = 50.0, xsSd = 0.0;
   {
      int m = 0; double sum = 0, ss = 0;
      for(int c2 = 0; c2 < 8; c2++)
      {
         double sv = g_metS[c2][tsel][MET_RING-1];
         if(MetIsNan(sv)) continue;
         sum += sv; ss += sv*sv; m++;
      }
      if(m >= 4) { xsMean = sum/m; xsSd = MathSqrt(MathMax(ss/m - xsMean*xsMean, 0.0)); }
   }

   int movLeader = -1;
   for(int c2 = 0; c2 < 8; c2++)
      if(g_metZMov[c2] != EMPTY_VALUE &&
         (movLeader < 0 || MathAbs(g_metZMov[c2]) > MathAbs(g_metZMov[movLeader])))
         movLeader = c2;

   // Ordena por S desc do TF selecionado (NaN por último)
   int ord[8];
   for(int i = 0; i < 8; i++) ord[i] = i;
   for(int i = 0; i < 8; i++)
      for(int j = i + 1; j < 8; j++)
      {
         double sa = g_metS[ord[i]][tsel][MET_RING-1], sb = g_metS[ord[j]][tsel][MET_RING-1];
         if((MetIsNan(sa) ? -1e9 : sa) < (MetIsNan(sb) ? -1e9 : sb))
         { int tmp = ord[i]; ord[i] = ord[j]; ord[j] = tmp; }
      }

   string up = ShortToString(0x25B2), dn = ShortToString(0x25BC);
   string upH = ShortToString(0x25BD), dnH = ShortToString(0x25B3);  // ocos

   // v1.2 — relógio do ALERTA: hora do fechamento da âncora do TF exibido;
   // depois de InpLateHour (abertura de NY) o alerta esmaece (pesquisa E6/E8:
   // captura restante despenca no fim do dia).
   bool tardeSel = false;
   if(g_pairsN > 0)
   {
      datetime aOpen = iTime(g_pair[0], g_metTFs[tsel], MetAnchorShift(g_pair[0], g_metTFs[tsel]));
      if(aOpen > 0)
      {
         long secC = ((long)aOpen + PeriodSeconds(g_metTFs[tsel])) % 86400;
         tardeSel = ((int)(secC / 3600) >= InpLateHour);
      }
   }

   for(int r = 0; r < 8; r++)
   {
      int c = ord[r];
      int ry0 = gridY + (r*gridH)/8;
      int ry1 = gridY + ((r+1)*gridH)/8;
      string rid = (string)r;

      double serie[MET_RING];
      for(int j = 0; j < MET_RING; j++) serie[j] = g_metS[c][tsel][j];
      double s0    = serie[MET_RING-1];
      double vel   = MetVel(serie, InpMetVelK);
      double acel  = MetAcel(serie, InpMetVelK);
      double zvel  = MetZVel(serie, InpMetVelK, InpZVelN);
      double zS    = (MetIsNan(s0) || xsSd < 1e-9) ? EMPTY_VALUE : (s0 - xsMean) / xsSd;
      double cesta = g_metCesta[c][tsel];

      // MTF_sign: multi-TF por definição sobre M30/H1/H4/D1 (ignora M5/M15
      // para preservar a semântica "de 4" do spec); ref = H1
      double sH1 = g_metS[c][TF_H1_IDX][MET_RING-1];
      int refSide = MetIsNan(sH1) ? 0 : MetSign(sH1 - 50.0);
      int mtfSign = -1;
      if(refSide != 0)
      {
         mtfSign = 0;
         for(int t2 = TF_M30_IDX; t2 <= TF_D1_IDX; t2++)
         {
            double sv = g_metS[c][t2][MET_RING-1];
            if(!MetIsNan(sv) && MetSign(sv - 50.0) == refSide) mtfSign++;
         }
      }

      // VETO (espelhado p/ moeda fraca): top-2 pelo lado + VEL6 contrária em H4 E D1.
      // v1.2: INFORMATIVO apenas (✕ na coluna mtf) — NÃO anula mais a candidata
      // (pesquisa E6.2: vetados capturaram 74% vs 36% — o VETO cortava pullbacks bons)
      double sr6H4[MET_RING], sr6D1[MET_RING];
      for(int j = 0; j < MET_RING; j++)
      { sr6H4[j] = g_metS[c][TF_H4_IDX][j]; sr6D1[j] = g_metS[c][TF_D1_IDX][j]; }
      double vH4 = MetVel(sr6H4, 6), vD1 = MetVel(sr6D1, 6);
      bool vetoOn = false;
      if(refSide != 0 && !MetIsNan(vH4) && !MetIsNan(vD1))
      {
         int rSided = (refSide > 0) ? rankH1[c] : (9 - rankH1[c]);
         if(rSided <= 2)
            vetoOn = (refSide > 0) ? (vH4 < 0 && vD1 < 0) : (vH4 > 0 && vD1 > 0);
      }

      // v1.2 — sinal em DOIS NÍVEIS (pesquisa 2026-07 reatividade):
      // CONFIRMAÇÃO = candidata ENXUTA (sem VETO e sem mtf — ambos reprovados:
      // VETO corta pullbacks bons, mtf só atrasa) — destaque forte.
      // ALERTA = |zS| >= limiar com lado definido (o sismógrafo: pega cedo,
      // com pouca precisão — atenção, NÃO gatilho) — tinta suave; esmaece
      // depois de InpLateHour (alerta tardio = provável exaustão).
      bool cand = !MetIsNan(zvel) && MathAbs(zvel) >= InpZThrVel &&
                  !MetIsNan(zS) && MathAbs(zS) >= InpZThrS &&
                  !MetIsNan(cesta) && cesta * g_cnt[c] >= InpMetThrCesta - 1e-9 &&
                  !MetIsNan(s0) && MetSign(s0 - 50.0) != 0;
      bool alerta = !cand && !MetIsNan(zS) && MathAbs(zS) >= InpZThrS &&
                    !MetIsNan(s0) && MetSign(s0 - 50.0) != 0;
      color rowBg = (r % 2 == 0) ? COL_BG_CARD : C'28,30,40';   // zebra
      if(cand)        rowBg = (MetSign(s0 - 50.0) > 0) ? C'18,62,32' : C'70,26,26';
      else if(alerta) rowBg = tardeSel ? C'40,38,26'
                              : ((MetSign(s0 - 50.0) > 0) ? C'20,42,30' : C'48,26,28');
      Rect(TPFX+"row"+rid, win, x+2, ry0, w-4, ry1-ry0-1, rowBg, rowBg);

      int bx = x + pad;
      int iw = tblW;
      int cy = (ry0 + ry1) / 2;

      // # rank (posição na aba atual) + moeda
      Lbl(TPFX+"rk"+rid, win, bx + (int)(ColXf(0)*iw), cy,
          StringFormat("%d", r+1), COL_TEXT_MUTED, fs-2, ANCHOR_LEFT, "Consolas");
      Lbl(TPFX+"m"+rid, win, bx + (int)(ColXf(0)*iw) + fs + 6, cy,
          g_cur[c], g_colArr[c], fs, ANCHOR_LEFT);

      string fTxt = MetIsNan(s0) ? ShortToString(0x2014)
                    : DoubleToString(s0, 1) + (MetSign(s0-50.0) >= 0 ? up : dn);
      color fCol = MetIsNan(s0) ? COL_TEXT_MUTED
                   : (MetSign(s0-50.0) >= 0 ? C'80,220,120' : C'240,90,90');
      Lbl(TPFX+"f"+rid, win, bx + (int)(ColXf(1)*iw), cy, fTxt, fCol, fs, ANCHOR_LEFT, "Consolas");

      // Mini-barra de força sob o valor (comprimento = |S-50|/50)
      {
         int barMax = (int)(ColXf(2)*iw) - (int)(ColXf(1)*iw) - 14;
         int barH2  = MathMax(2, (ry1-ry0)/8);
         int barW2  = MetIsNan(s0) ? 0
                      : (int)MathRound(barMax * MathMin(MathAbs(s0-50.0)/50.0, 1.0));
         color barc = MetIsNan(s0) ? COL_TEXT_MUTED
                      : (s0 >= 50 ? C'66,200,110' : C'235,85,75');
         Rect(TPFX+"fb"+rid, win, bx + (int)(ColXf(1)*iw), ry1 - barH2 - 2,
              MathMax(barW2,1), barH2, barc, barc);
      }

      color zsc = MetIsNan(zS) ? COL_TEXT_MUTED : (zS >= 0 ? C'80,220,120' : C'240,90,90');
      Lbl(TPFX+"zs"+rid, win, bx + (int)(ColXf(2)*iw), cy, MetNum(zS, 2, true), zsc, fs, ANCHOR_LEFT, "Consolas");

      color vc = MetIsNan(vel) ? COL_TEXT_MUTED : (vel >= 0 ? C'80,220,120' : C'240,90,90');
      Lbl(TPFX+"v"+rid, win, bx + (int)(ColXf(3)*iw), cy, MetNum(vel, 1, true), vc, fs, ANCHOR_LEFT, "Consolas");

      color zvc = MetIsNan(zvel) ? COL_TEXT_MUTED
                  : (MathAbs(zvel) >= InpZThrVel ? COL_GOLD
                     : (zvel >= 0 ? C'80,220,120' : C'240,90,90'));
      Lbl(TPFX+"zv"+rid, win, bx + (int)(ColXf(4)*iw), cy, MetNum(zvel, 2, true), zvc, fs, ANCHOR_LEFT, "Consolas");

      string aArr = MetIsNan(acel) ? "" : (acel >= 0 ? ShortToString(0x2191) : ShortToString(0x2193));
      color ac = MetIsNan(acel) ? COL_TEXT_MUTED : (acel >= 0 ? C'80,220,120' : C'240,90,90');
      Lbl(TPFX+"a"+rid, win, bx + (int)(ColXf(5)*iw), cy, MetNum(acel, 1, true) + aArr, ac, fs, ANCHOR_LEFT, "Consolas");

      double zmv = g_metZMov[c];
      string mvTxt = MetIsNan(zmv) ? ShortToString(0x2014)
                     : ((c == movLeader ? ShortToString(0x2605) : "") + MetNum(zmv, 2, true));
      color mvc = MetIsNan(zmv) ? COL_TEXT_MUTED
                  : (c == movLeader ? COL_GOLD : (zmv >= 0 ? C'80,220,120' : C'240,90,90'));
      Lbl(TPFX+"mv"+rid, win, bx + (int)(ColXf(6)*iw), cy, mvTxt, mvc, fs, ANCHOR_LEFT, "Consolas");

      double zmh = g_metZMovH[c];
      color mhc = MetIsNan(zmh) ? COL_TEXT_MUTED
                  : (MathAbs(zmh) >= 2.0 ? COL_GOLD : (zmh >= 0 ? C'80,220,120' : C'240,90,90'));
      Lbl(TPFX+"mh"+rid, win, bx + (int)(ColXf(7)*iw), cy, MetNum(zmh, 2, true), mhc, fs, ANCHOR_LEFT, "Consolas");

      string cTxt = MetIsNan(cesta) ? ShortToString(0x2014)
                    : StringFormat("%d/%d", (int)MathRound(cesta * g_cnt[c]), g_cnt[c]);
      Lbl(TPFX+"c"+rid, win, bx + (int)(ColXf(8)*iw), cy, cTxt,
          MetIsNan(cesta) ? COL_TEXT_MUTED : COL_TEXT_DIM, fs, ANCHOR_LEFT, "Consolas");

      string mTxt;
      if(vetoOn)             mTxt = ShortToString(0x2715) + " ";  // ✕ sobrepõe
      if(mtfSign < 0)        mTxt += ShortToString(0x2014);
      else
      {
         string filled = (refSide >= 0) ? up : dn;
         string hollow = (refSide >= 0) ? upH : dnH;
         for(int k2 = 0; k2 < 4; k2++) mTxt += (k2 < mtfSign) ? filled : hollow;
      }
      color mc = vetoOn ? C'240,90,90'
                 : (refSide > 0 ? C'80,220,120' : (refSide < 0 ? C'240,90,90' : COL_TEXT_MUTED));
      Lbl(TPFX+"t"+rid, win, bx + (int)(ColXf(9)*iw), cy, mTxt, mc, fs, ANCHOR_LEFT);

      // v1.2 — dia% (consumo do dia vs. típico) e SCORE 0-100 (detector E10)
      if(InpShowScore)
      {
         double cons = g_metConsumo[c];
         string dcT = MetIsNan(cons) ? ShortToString(0x2014)
                      : StringFormat("%.0f%%", MathMin(cons, 999.0));
         color dcC = MetIsNan(cons) ? COL_TEXT_MUTED
                     : (cons >= 75.0 ? C'240,90,90'
                        : (cons >= 50.0 ? COL_GOLD
                           : (cons >= 25.0 ? COL_TEXT_DIM : C'80,220,120')));
         Lbl(TPFX+"dc"+rid, win, bx + (int)(ColXf(10)*iw), cy, dcT, dcC, fs,
             ANCHOR_LEFT, "Consolas");

         double sco = g_metScore[c];
         string scT = MetIsNan(sco) ? ShortToString(0x2014)
                      : ((sco >= SCORE_CUT ? ShortToString(0x25CF) : "")
                         + DoubleToString(sco, 1));
         color scC = MetIsNan(sco) ? COL_TEXT_MUTED
                     : (sco >= SCORE_CUT ? COL_GOLD : COL_TEXT_DIM);
         Lbl(TPFX+"sc"+rid, win, bx + (int)(ColXf(11)*iw), cy, scT, scC, fs,
             ANCHOR_LEFT, "Consolas");
      }
   }

   // Rodapé (v1.2: dois níveis de sinal; VETO informativo; Score E10)
   Lbl(TPFX+"ft", win, x+pad, y+h-pad-slot/2,
       StringFormat("alerta: |zS|%s%.1f (esmaece %s%02dh) | confirmacao: +|zvel|%s%.1f +CESTA%s%d/7 | VETO %s informativo | SCORE corte %s%.1f (detector, nao gatilho) | k=%d sigma N=%d | zHist N=%d | nucleo %s",
                    ShortToString(0x2265), InpZThrS, ShortToString(0x2265), InpLateHour,
                    ShortToString(0x2265), InpZThrVel,
                    ShortToString(0x2265), InpMetThrCesta,
                    ShortToString(0x2715), ShortToString(0x2265), SCORE_CUT,
                    InpMetVelK, InpZVelN, InpZMovN,
                    InpZCore ? "IFM-Z" : "IFM classico"),
       COL_TEXT_MUTED, fs-1, ANCHOR_LEFT);
}


//+------------------------------------------------------------------+
//|              MATRIX — 8x8 responsive, fills its whole area         |
//+------------------------------------------------------------------+
void RenderMatrix(int win, int x, int y, int w, int h)
{
   // Card background + accent
   Rect(MPFX+"bg", win, x, y, w, h, COL_BG_CARD, COL_BORDER);
   Rect(MPFX+"accent", win, x, y, w, 2, COL_GOLD, COL_GOLD);

   if(g_mtxTFIdx < 0 || g_mtxTFIdx >= MET_TFN) g_mtxTFIdx = 0;
   ENUM_TIMEFRAMES tf = g_metTFs[g_mtxTFIdx];

   // Layout vertical: seletor + título + header + 8 linhas + rodapé = 12 slots
   int pad  = 6;
   int slot = (int)Clamp((h - pad*3) / 12.0, 13, 42);
   int fs   = (int)Clamp(slot * 0.40, 7, 14);

   // Seletor de TF segmentado: M5 / M15 / M30 / H1 / H4 / D1
   int segY = y + pad + 2;
   int segW = w - pad*2;
   for(int t = 0; t < MET_TFN; t++)
   {
      int bx0 = x + pad + (t*segW)/MET_TFN;
      int bx1 = x + pad + ((t+1)*segW)/MET_TFN;
      FlatBtn(MPFX+"tf"+(string)t, win, bx0, segY, bx1-bx0-2, slot,
              g_metTfName[t], t == g_mtxTFIdx, COL_GOLD, (int)Clamp(fs-1, 6, 12));
   }

   // Refresh cached data when the TF changed or a new update invalidated it
   if(g_mtxCacheTF != g_mtxTFIdx)
   {
      int mShift = ShiftForTF(tf);
      for(int i = 0; i < 64; i++) { g_mtxVal[i] = 50.0; g_mtxOk[i] = false; }
      for(int p = 0; p < g_pairsN; p++)
      {
         double ifm = CalcIFMLight(g_pair[p], tf, mShift);
         if(ifm < 0) continue;
         int a = g_baseIdx[p], b = g_quoteIdx[p];
         g_mtxVal[a*8+b] = ifm;         g_mtxOk[a*8+b] = true;
         g_mtxVal[b*8+a] = 100.0-ifm;   g_mtxOk[b*8+a] = true;
      }
      g_mtxGood = ComputeCurrencyStrength(tf, mShift, g_mtxStr);
      g_mtxCacheTF = g_mtxTFIdx;
   }

   // Title
   int yTitle = segY + slot + 2;
   Lbl(MPFX+"hd", win, x+pad, yTitle + slot/2,
       StringFormat("MATRIZ 8x8   %s", TfStr(tf)), COL_TEXT, fs, ANCHOR_LEFT);

   // Grid fills the remaining space exactly
   int hdrw  = fs*3 + 8;
   int gridX = x + pad + hdrw;
   int gridW = w - pad*2 - hdrw;
   int yHdr  = yTitle + slot;
   int gridY = yHdr + slot;
   int footH = slot;
   int gridH = (y + h - pad) - gridY - footH;
   if(gridH < 80) gridH = 80;

   // Column headers
   for(int b = 0; b < 8; b++)
   {
      int cx0 = gridX + (b*gridW)/8;
      int cx1 = gridX + ((b+1)*gridW)/8;
      Lbl(MPFX+"ch"+(string)b, win, (cx0+cx1)/2, yHdr + slot/2,
          g_cur[b], g_colArr[b], fs-1, ANCHOR_CENTER);
   }

   // Grid cells
   for(int a = 0; a < 8; a++)
   {
      int ry0 = gridY + (a*gridH)/8;
      int ry1 = gridY + ((a+1)*gridH)/8;
      int cH  = ry1 - ry0 - 1;
      Lbl(MPFX+"rh"+(string)a, win, x+pad, (ry0+ry1)/2, g_cur[a], g_colArr[a], fs-1, ANCHOR_LEFT);
      for(int b = 0; b < 8; b++)
      {
         string nc = MPFX+"c"+(string)a+"_"+(string)b;
         string nl = MPFX+"l"+(string)a+"_"+(string)b;
         int cx0 = gridX + (b*gridW)/8;
         int cx1 = gridX + ((b+1)*gridW)/8;
         int cw  = cx1 - cx0 - 1;
         if(a == b)
         {
            Rect(nc, win, cx0, ry0, cw, cH, C'26,28,36', C'26,28,36');
            Lbl(nl, win, (cx0+cx1)/2, (ry0+ry1)/2, "-", COL_TEXT_MUTED, fs-1, ANCHOR_CENTER);
            continue;
         }
         if(!g_mtxOk[a*8+b])
         {
            Rect(nc, win, cx0, ry0, cw, cH, C'36,38,46', C'36,38,46');
            Lbl(nl, win, (cx0+cx1)/2, (ry0+ry1)/2, "?", COL_TEXT_MUTED, fs-1, ANCHOR_CENTER);
            continue;
         }
         double vv = g_mtxVal[a*8+b];
         // Heatmap contínuo: intensidade proporcional à distância de 50
         color cbg = GradeColor(vv);
         color ctx = (MathAbs(vv - 50.0) >= 15.0) ? clrWhite : COL_TEXT_DIM;
         Rect(nc, win, cx0, ry0, cw, cH, cbg, cbg);
         Lbl(nl, win, (cx0+cx1)/2, (ry0+ry1)/2, StringFormat("%.0f", vv), ctx, fs-1, ANCHOR_CENTER, "Consolas");
      }
   }

   // Footer: strongest / weakest
   if(g_mtxGood > 0)
   {
      int hi=-1, lo=-1;
      for(int c = 0; c < 8; c++)
      {
         if(g_cnt[c] <= 0) continue;
         if(hi < 0 || g_mtxStr[c] > g_mtxStr[hi]) hi = c;
         if(lo < 0 || g_mtxStr[c] < g_mtxStr[lo]) lo = c;
      }
      if(hi >= 0 && lo >= 0)
         Lbl(MPFX+"ft", win, x+pad, y+h-pad-footH/2,
             StringFormat("Forte: %s %.0f %s   |   Fraca: %s %.0f %s",
                    g_cur[hi], g_mtxStr[hi], ShortToString(0x25B2),
                    g_cur[lo], g_mtxStr[lo], ShortToString(0x25BC)),
             COL_TEXT_DIM, fs-1, ANCHOR_LEFT);
   }
}


//+------------------------------------------------------------------+
//|              BUTTONS — Modern flat top bar                         |
//+------------------------------------------------------------------+
void DrawButtons(int win)
{
   int chartW = (int)ChartGetInteger(0, CHART_WIDTH_IN_PIXELS);

   Rect(PFX+"topbar",    win, 0, 0, chartW, TOPBAR_H, COL_BG_MAIN, COL_BG_MAIN);
   Rect(PFX+"topbar_ln", win, 0, TOPBAR_H-1, chartW, 1, COL_BORDER, COL_BORDER);

   int by = 4, bh = TOPBAR_H - 8, x = 6;

   Lbl(PFX+"title", win, x, TOPBAR_H/2, "IFM", COL_TEXT, InpFont, ANCHOR_LEFT);
   x += 110;

   // Toggle da matriz (métricas ocupam a largura toda quando oculta)
   FlatBtn(PFX+"btnMtx", win, x, by, 62, bh, "MATRIZ", g_mtxShow, COL_GOLD);
   x += 68;

   // Atualização manual
   FlatBtn(PFX+"btnRefresh", win, x, by, 84, bh, "ATUALIZAR", false, COL_ACCENT);
   x += 92;

   // Replay: toggle + navegação (setas só visíveis com replay ativo)
   if(g_replayOn) FlatBtn(PFX+"btnReplay", win, x, by, 62, bh, "LIVE",   true,  C'50,205,80');
   else           FlatBtn(PFX+"btnReplay", win, x, by, 62, bh, "REPLAY", false, COL_ACCENT);
   x += 68;

   if(g_replayOn)
   {
      string l1 = ShortToString(0x25C4), r1 = ShortToString(0x25BA);
      FlatBtn(PFX+"btnPrev10", win, x,     by, 34, bh, l1+l1, false, COL_ACCENT);
      FlatBtn(PFX+"btnPrev",   win, x+38,  by, 30, bh, l1,    false, COL_ACCENT);
      FlatBtn(PFX+"btnNext",   win, x+72,  by, 30, bh, r1,    false, COL_ACCENT);
      FlatBtn(PFX+"btnNext10", win, x+106, by, 34, bh, r1+r1, false, COL_ACCENT);
      x += 144;
   }
   else
   {
      DelBtn(PFX+"btnPrev");   DelBtn(PFX+"btnNext");
      DelBtn(PFX+"btnPrev10"); DelBtn(PFX+"btnNext10");
   }

   g_statusX = x + 4;
   UpdateStatusLabel(win);
}

// Atualiza SÓ o texto de status (barato — chamado a cada segundo pelo timer)
void UpdateStatusLabel(int win)
{
   string upd;
   color  cl = COL_TEXT_DIM;
   if(g_replayOn)
   {
      upd = StringFormat("REPLAY  %s  %s  shift: %d (%s)  %s  auto pausado",
                         TimeToString(g_replayTime, TIME_DATE|TIME_MINUTES),
                         ShortToString(0x00B7), g_replayShift, TfStr((ENUM_TIMEFRAMES)_Period),
                         ShortToString(0x00B7));
      cl = COL_GOLD;
   }
   else if(g_lastUpdate == 0)
      upd = "carregando...";
   else
   {
      int remain = MathMax(MathMax(InpRefreshSec, 10) - g_secCount, 0);
      upd = StringFormat("ultima: %s   %s   proxima em %02d:%02d",
                         TimeToString(g_lastUpdate, TIME_SECONDS),
                         ShortToString(0x00B7), remain / 60, remain % 60);
   }
   Lbl(PFX+"upd", win, g_statusX, TOPBAR_H/2, upd, cl, InpFont-1, ANCHOR_LEFT, "Consolas");
}


//+------------------------------------------------------------------+
//|              COMPUTE — Data (heavy) / Render (light)               |
//+------------------------------------------------------------------+
void MarkDirty()
{
   g_metDirty   = true;   // força MetRebuild no próximo render
   g_mtxCacheTF = -1;     // força recomputo da matriz no próximo render
   g_lastUpdate = TimeLocal();
}

// Redesenha tudo a partir dos caches — barato o suficiente para resize
void RenderAll()
{
   int win = ChartWindowFind();
   if(win < 0) return;

   int chartW = (int)ChartGetInteger(0, CHART_WIDTH_IN_PIXELS);
   int chartH = (int)ChartGetInteger(0, CHART_HEIGHT_IN_PIXELS, win);
   if(chartW < 140 || chartH < TOPBAR_H + 60) return;

   int margin = 6;
   int x0 = margin;
   int y0 = TOPBAR_H + margin;
   int availW = chartW - margin*2;
   int availH = chartH - y0 - margin;

   bool showMtx = (InpShowMatrix && g_mtxShow);
   int gap   = showMtx ? margin : 0;
   int sideW = 0;
   if(showMtx)
   {
      sideW = (int)(availW * 0.38);
      if(sideW > 560) sideW = 560;
      if(sideW < 280) sideW = (int)MathMin(280.0, availW * 0.5);
   }
   int metW = availW - sideW - gap;

   // Métricas à esquerda; matriz à direita (quando visível)
   RenderMetrics(win, x0, y0, metW, availH);
   if(showMtx)
      RenderMatrix(win, x0 + metW + gap, y0, sideW, availH);
   else
      ObjectsDeleteAll(0, MPFX);

   DrawButtons(win);   // desenhado por último: sempre no topo
   ChartRedraw();
}

bool Compute()
{
   if(g_computing) return g_ready;
   g_computing = true;

   MarkDirty();
   RenderAll();   // dispara MetRebuild + recomputo da matriz
   g_secCount = 0;

   // Pronto quando pelo menos metade das moedas tem força válida em H1
   int valid = 0;
   for(int c = 0; c < 8; c++)
      if(!MetIsNan(g_metS[c][TF_H1_IDX][MET_RING-1])) valid++;
   bool ready = (g_pairsN > 0 && valid >= 4);
   Comment(ready ? "" : "IFM: carregando dados dos pares...");

   g_computing = false;
   return ready;
}


//+------------------------------------------------------------------+
//|                        OnInit                                      |
//+------------------------------------------------------------------+
int OnInit()
{
   //--- Validate ML inputs
   if(InpRSILength < 2 || InpMemoryDepth < 50 || InpKNeighbors < 1)
   {
      Print("IFM: Invalid ML input parameters");
      return INIT_PARAMETERS_INCORRECT;
   }

   SetIndexBuffer(0, IFMBuf,   INDICATOR_DATA);
   SetIndexBuffer(1, MLRSIBuf, INDICATOR_DATA);
   SetIndexBuffer(2, RankBuf,  INDICATOR_DATA);
   SetIndexBuffer(3, ConfBuf,  INDICATOR_DATA);
   PlotIndexSetDouble(0, PLOT_EMPTY_VALUE, EMPTY_VALUE);
   PlotIndexSetDouble(1, PLOT_EMPTY_VALUE, EMPTY_VALUE);
   PlotIndexSetDouble(2, PLOT_EMPTY_VALUE, EMPTY_VALUE);
   PlotIndexSetDouble(3, PLOT_EMPTY_VALUE, EMPTY_VALUE);

   IndicatorSetString(INDICATOR_SHORTNAME,
      StringFormat("IFM (auto %ds)", MathMax(InpRefreshSec, 10)));
   IndicatorSetInteger(INDICATOR_DIGITS, 1);

   //--- Create indicator handles (active pair — motor ML)
   int rsiFastLen = MathMax(2, (int)MathRound(InpRSILength / 2.0));
   int rsiSlowLen = InpRSILength * 2;
   g_hRsiBase   = iRSI(NULL, 0, InpRSILength, PRICE_CLOSE);
   g_hRsiFast   = iRSI(NULL, 0, rsiFastLen,   PRICE_CLOSE);
   g_hRsiSlow   = iRSI(NULL, 0, rsiSlowLen,   PRICE_CLOSE);
   g_hATR14     = iATR(NULL, 0, 14);
   g_hATR10     = iATR(NULL, 0, ST_ATR_LEN);
   g_hCCI       = iCCI(NULL, 0, InpCCILength, PRICE_TYPICAL);
   g_hEmaRsi20  = iMA(NULL, 0, 20, 0, MODE_EMA, g_hRsiBase);
   g_hEmaRsi5   = iMA(NULL, 0, 5,  0, MODE_EMA, g_hRsiBase);
   g_hEmaClose5 = iMA(NULL, 0, 5,  0, MODE_EMA, PRICE_CLOSE);
   g_hEmaClose50= iMA(NULL, 0, TREND_LEN, 0, MODE_EMA, PRICE_CLOSE);
   g_hEmaClose21= iMA(NULL, 0, InpEMAFallbackLen, 0, MODE_EMA, PRICE_CLOSE);

   if(g_hRsiBase==INVALID_HANDLE || g_hRsiFast==INVALID_HANDLE ||
      g_hRsiSlow==INVALID_HANDLE || g_hATR14==INVALID_HANDLE ||
      g_hATR10==INVALID_HANDLE   || g_hCCI==INVALID_HANDLE ||
      g_hEmaRsi20==INVALID_HANDLE || g_hEmaRsi5==INVALID_HANDLE ||
      g_hEmaClose5==INVALID_HANDLE || g_hEmaClose50==INVALID_HANDLE ||
      g_hEmaClose21==INVALID_HANDLE)
   {
      Print("IFM: Failed to create indicator handles");
      return INIT_FAILED;
   }

   //--- Initialize ML bank
   BankInit(InpMemoryDepth);
   ArrayInitialize(g_autoW, 1.0);
   ArrayInitialize(g_weights, 1.0);
   g_stanceState = 0; g_stanceAge = 0; g_lastEntryBar = -100;

   //--- Detect G8 pairs
   ArrayInitialize(g_cnt, 0);
   g_pairsN = 0;
   bool seen[64]; for(int s=0;s<64;s++) seen[s]=false;
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
   Print("IFM: ", g_pairsN, " pares G8 detectados.");

   //--- Estado inicial
   g_ready     = false;
   g_mtxShow   = InpShowMatrix;
   g_metTFIdx  = TF_M30_IDX;  // v1.2: MÉTRICAS abrem em M30 — o "TF doce" da
                              // pesquisa (M5 não compra tempo; H1 chega depois)
   g_mtxTFIdx  = TF_H1_IDX;   // default: MATRIZ em H1
   g_metDirty  = true;
   g_mtxCacheTF = -1;
   g_lastUpdate = 0;

   //--- Replay init
   g_replayOn = false;
   g_replayShift = 1;
   g_replayTime = 0;

   //--- Timer de 1s: carga inicial + auto-refresh a cada InpRefreshSec
   EventSetTimer(1);
   return INIT_SUCCEEDED;
}


//+------------------------------------------------------------------+
//|                        OnDeinit                                    |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   EventKillTimer();
   Comment("");
   ObjectsDeleteAll(0, PFX);
   ObjectsDeleteAll(0, MPFX);
   ObjectsDeleteAll(0, TPFX);
   if(g_hRsiBase   != INVALID_HANDLE) IndicatorRelease(g_hRsiBase);
   if(g_hRsiFast   != INVALID_HANDLE) IndicatorRelease(g_hRsiFast);
   if(g_hRsiSlow   != INVALID_HANDLE) IndicatorRelease(g_hRsiSlow);
   if(g_hATR14     != INVALID_HANDLE) IndicatorRelease(g_hATR14);
   if(g_hATR10     != INVALID_HANDLE) IndicatorRelease(g_hATR10);
   if(g_hCCI       != INVALID_HANDLE) IndicatorRelease(g_hCCI);
   if(g_hEmaRsi20  != INVALID_HANDLE) IndicatorRelease(g_hEmaRsi20);
   if(g_hEmaRsi5   != INVALID_HANDLE) IndicatorRelease(g_hEmaRsi5);
   if(g_hEmaClose5 != INVALID_HANDLE) IndicatorRelease(g_hEmaClose5);
   if(g_hEmaClose50!= INVALID_HANDLE) IndicatorRelease(g_hEmaClose50);
   if(g_hEmaClose21!= INVALID_HANDLE) IndicatorRelease(g_hEmaClose21);
}


//+------------------------------------------------------------------+
//|                        OnTimer                                     |
//+------------------------------------------------------------------+
void OnTimer()
{
   static int tries = 0;

   if(g_computing) return;   // rebuild ainda em andamento — não empilha

   // Fase de carga inicial: tenta a cada 2s até os dados dos pares chegarem
   if(!g_ready)
   {
      tries++;
      if(tries % 2 == 0)
      {
         g_ready = Compute();
         if(tries > 30) g_ready = true;   // desiste após ~30s (mostra o que houver)
      }
      g_secCount = 0;
      return;
   }

   // Em replay: dados ancorados no passado — pausa a auto-atualização
   if(g_replayOn) { g_secCount = 0; return; }

   // Contagem regressiva ao vivo + refresh no zero
   g_secCount++;
   if(g_secCount >= MathMax(InpRefreshSec, 10))
   {
      g_secCount = 0;
      Compute();
   }
   else
   {
      int win = ChartWindowFind();
      if(win >= 0) { UpdateStatusLabel(win); ChartRedraw(); }
   }
}


//+------------------------------------------------------------------+
//|                     OnChartEvent                                   |
//+------------------------------------------------------------------+
void OnChartEvent(const int id, const long &lparam,
                  const double &dparam, const string &sparam)
{
   // Responsive: redesenha ao redimensionar a janela
   if(id == CHARTEVENT_CHART_CHANGE)
   {
      static long lastW = 0, lastH = 0;
      int win = ChartWindowFind();
      long w = ChartGetInteger(0, CHART_WIDTH_IN_PIXELS);
      long h = ChartGetInteger(0, CHART_HEIGHT_IN_PIXELS, win < 0 ? 0 : win);
      if(w != lastW || h != lastH)
      {
         lastW = w; lastH = h;
         RenderAll();
      }
      return;
   }

   if(id != CHARTEVENT_OBJECT_CLICK) return;

   // Flat buttons são pares rect+label; clique no label ("_t") também conta
   string nm = sparam;
   if(StringLen(nm) > 2 && StringSubstr(nm, StringLen(nm)-2) == "_t")
      nm = StringSubstr(nm, 0, StringLen(nm)-2);

   // Toggle da matriz
   if(nm == PFX+"btnMtx")
   {
      g_mtxShow = !g_mtxShow;
      ObjectsDeleteAll(0, TPFX);   // largura das métricas muda
      ObjectsDeleteAll(0, MPFX);
      RenderAll();
      return;
   }

   // Atualização manual imediata
   if(nm == PFX+"btnRefresh")
   {
      Compute();
      return;
   }

   // REPLAY toggle (entra na última barra fechada; sair volta ao LIVE)
   if(nm == PFX+"btnReplay")
   {
      g_replayOn = !g_replayOn;
      if(g_replayOn)
      {
         g_replayShift = 1;
         SyncReplayTime();
      }
      Compute();
      return;
   }

   // Navegação do replay (◄◄ -10 | ◄ -1 | ► +1 | ►► +10 barras do TF do gráfico)
   if(nm == PFX+"btnPrev" || nm == PFX+"btnPrev10" ||
      nm == PFX+"btnNext" || nm == PFX+"btnNext10")
   {
      if(!g_replayOn) return;
      if(nm == PFX+"btnPrev")   g_replayShift++;
      if(nm == PFX+"btnPrev10") g_replayShift += 10;
      if(nm == PFX+"btnNext")   g_replayShift = MathMax(1, g_replayShift - 1);
      if(nm == PFX+"btnNext10") g_replayShift = MathMax(1, g_replayShift - 10);
      SyncReplayTime();
      Compute();
      return;
   }

   // Abas de TF da vista MÉTRICAS (M5/M15/M30/H1/H4/D1)
   if(StringFind(nm, TPFX+"tf") == 0)
   {
      int ti = (int)StringToInteger(StringSubstr(nm, StringLen(TPFX+"tf")));
      if(ti >= 0 && ti < MET_TFN && ti != g_metTFIdx)
      {
         g_metTFIdx = ti;
         RenderAll();
      }
      return;
   }

   // Abas de TF da MATRIZ (M5/M15/M30/H1/H4/D1)
   if(StringFind(nm, MPFX+"tf") == 0)
   {
      int ti = (int)StringToInteger(StringSubstr(nm, StringLen(MPFX+"tf")));
      if(ti >= 0 && ti < MET_TFN && ti != g_mtxTFIdx)
      {
         g_mtxTFIdx = ti;
         RenderAll();   // cache da matriz é por TF, se atualiza sozinho
      }
      return;
   }
}


//+------------------------------------------------------------------+
//|                    OnCalculate                                     |
//+------------------------------------------------------------------+
int OnCalculate(const int rates_total,
                const int prev_calculated,
                const datetime &time[],
                const double &open[],
                const double &high[],
                const double &low[],
                const double &close[],
                const long &tick_volume[],
                const long &volume[],
                const int &spread[])
{
   // Nova barra no gráfico dispara uma atualização do painel (além do timer).
   static datetime lastBar = 0;
   datetime t0[];
   if(CopyTime(_Symbol, _Period, 0, 1, t0) == 1)
   {
      if(t0[0] != lastBar)
      {
         lastBar = t0[0];
         if(g_ready && !g_replayOn) Compute();   // em replay a âncora é fixa
      }
   }

   //=== MOTOR ML — par ativo (incremental) ===
   //--- Minimum bars
   int warmup = MathMax(InpRSILength * 2 + 10, WIN_LEN) + HORIZON_BARS + STEP_LEN * 2 + 5;
   if(rates_total < warmup + 20) return 0;

   //--- Check handles ready
   if(BarsCalculated(g_hRsiBase)  < rates_total) return 0;
   if(BarsCalculated(g_hRsiFast)  < rates_total) return 0;
   if(BarsCalculated(g_hRsiSlow)  < rates_total) return 0;
   if(BarsCalculated(g_hATR14)    < rates_total) return 0;
   if(BarsCalculated(g_hATR10)    < rates_total) return 0;
   if(BarsCalculated(g_hCCI)      < rates_total) return 0;
   if(BarsCalculated(g_hEmaRsi20) < rates_total) return 0;
   if(BarsCalculated(g_hEmaRsi5)  < rates_total) return 0;
   if(BarsCalculated(g_hEmaClose5)< rates_total) return 0;
   if(BarsCalculated(g_hEmaClose50)<rates_total) return 0;
   if(BarsCalculated(g_hEmaClose21)<rates_total) return 0;

   //--- Set arrays: 0 = oldest
   ArraySetAsSeries(open, false);  ArraySetAsSeries(high, false);
   ArraySetAsSeries(low, false);   ArraySetAsSeries(close, false);
   ArraySetAsSeries(tick_volume, false); ArraySetAsSeries(volume, false);
   ArraySetAsSeries(time, false);

   //--- Resize working arrays
   int rt = rates_total;
   ArrayResize(g_rsiBase, rt);  ArrayResize(g_rsiFast, rt);
   ArrayResize(g_rsiSlow, rt);  ArrayResize(g_atr14, rt);
   ArrayResize(g_atr10, rt);    ArrayResize(g_cci, rt);
   ArrayResize(g_emaRsi20, rt); ArrayResize(g_emaRsi5, rt);
   ArrayResize(g_emaClose5, rt); ArrayResize(g_emaClose50, rt);
   ArrayResize(g_emaClose21, rt);
   ArrayResize(g_rsiSlope, rt); ArrayResize(g_rsiAccel, rt);
   ArrayResize(g_rsiStd, rt);  ArrayResize(g_rsiSpread, rt);
   ArrayResize(g_rsiReg, rt);
   ArrayResize(g_fVal, rt); ArrayResize(g_fSlp, rt);
   ArrayResize(g_fAcc, rt); ArrayResize(g_fMid, rt);
   ArrayResize(g_fPct, rt); ArrayResize(g_fChn, rt);
   ArrayResize(g_fSpr, rt); ArrayResize(g_fReg, rt);
   ArrayResize(g_stLong, rt); ArrayResize(g_stShort, rt); ArrayResize(g_stDir, rt);
   ArrayResize(g_convSmooth, rt); ArrayResize(g_emaRank, rt); ArrayResize(g_mlRsiArr, rt);

   //--- Set working arrays: 0 = oldest
   ArraySetAsSeries(g_rsiBase,false); ArraySetAsSeries(g_rsiFast,false);
   ArraySetAsSeries(g_rsiSlow,false); ArraySetAsSeries(g_atr14,false);
   ArraySetAsSeries(g_atr10,false);   ArraySetAsSeries(g_cci,false);
   ArraySetAsSeries(g_emaRsi20,false); ArraySetAsSeries(g_emaRsi5,false);
   ArraySetAsSeries(g_emaClose5,false); ArraySetAsSeries(g_emaClose50,false);
   ArraySetAsSeries(g_emaClose21,false);

   //--- Copy indicator data
   CopyBuffer(g_hRsiBase,    0, 0, rt, g_rsiBase);
   CopyBuffer(g_hRsiFast,    0, 0, rt, g_rsiFast);
   CopyBuffer(g_hRsiSlow,    0, 0, rt, g_rsiSlow);
   CopyBuffer(g_hATR14,      0, 0, rt, g_atr14);
   CopyBuffer(g_hATR10,      0, 0, rt, g_atr10);
   CopyBuffer(g_hCCI,        0, 0, rt, g_cci);
   CopyBuffer(g_hEmaRsi20,   0, 0, rt, g_emaRsi20);
   CopyBuffer(g_hEmaRsi5,    0, 0, rt, g_emaRsi5);
   CopyBuffer(g_hEmaClose5,  0, 0, rt, g_emaClose5);
   CopyBuffer(g_hEmaClose50, 0, 0, rt, g_emaClose50);
   CopyBuffer(g_hEmaClose21, 0, 0, rt, g_emaClose21);

   //--- Determine start
   int start;
   if(prev_calculated == 0)
   {
      start = 0;
      BankInit(InpMemoryDepth);
      g_stanceState = 0; g_stanceAge = 0; g_lastEntryBar = -100;
      ArrayInitialize(IFMBuf, EMPTY_VALUE);
      ArrayInitialize(MLRSIBuf, EMPTY_VALUE);
      ArrayInitialize(RankBuf, EMPTY_VALUE);
      ArrayInitialize(ConfBuf, EMPTY_VALUE);
   }
   else
   {
      start = prev_calculated - 1;
   }

   //=== PHASE 1: Intermediate features ===
   int phase1Start = MathMax(start, STEP_LEN * 2);
   for(int i = phase1Start; i < rt; i++)
   {
      g_rsiSlope[i]  = (i >= STEP_LEN) ? g_rsiBase[i] - g_rsiBase[i - STEP_LEN] : 0;
      double slopePrev = (i >= STEP_LEN*2) ? g_rsiBase[i-STEP_LEN] - g_rsiBase[i-STEP_LEN*2] : 0;
      g_rsiAccel[i]  = g_rsiSlope[i] - slopePrev;
      g_rsiStd[i]    = CalcStdev(g_rsiBase, i, 14);
      g_rsiSpread[i] = g_rsiFast[i] - g_rsiSlow[i];
      g_rsiReg[i]    = g_emaRsi20[i] - 50.0;
   }

   //=== PHASE 2: Main processing (active pair) ===
   int mainStart = MathMax(start, warmup);
   double kEmaSmooth = 2.0 / (SMOOTH_LEN + 1.0);
   double kEma3 = 2.0 / (3.0 + 1.0);

   for(int i = mainStart; i < rt; i++)
   {
      //--- Features
      double feat[8];
      feat[0] = g_rsiBase[i] / 100.0;
      feat[1] = Scale01(g_rsiSlope, i, WIN_LEN);
      feat[2] = Scale01(g_rsiAccel, i, WIN_LEN);
      feat[3] = MathAbs(g_rsiBase[i] - 50.0) / 50.0;
      feat[4] = PercentRank(g_rsiBase, i, WIN_LEN) / 100.0;
      feat[5] = Scale01(g_rsiStd, i, WIN_LEN);
      feat[6] = Scale01(g_rsiSpread, i, WIN_LEN);
      feat[7] = Scale01(g_rsiReg, i, WIN_LEN);

      g_fVal[i]=feat[0]; g_fSlp[i]=feat[1]; g_fAcc[i]=feat[2]; g_fMid[i]=feat[3];
      g_fPct[i]=feat[4]; g_fChn[i]=feat[5]; g_fSpr[i]=feat[6]; g_fReg[i]=feat[7];

      //--- Bank insertion (delayed)
      bool isConfirmed = (i < rt - 1);
      if(isConfirmed && i >= warmup + HORIZON_BARS && i > g_lastBankBar)
      {
         int pastIdx = i - HORIZON_BARS;
         if(pastIdx >= warmup && pastIdx < rt)
         {
            double featPast[8];
            featPast[0]=g_fVal[pastIdx]; featPast[1]=g_fSlp[pastIdx];
            featPast[2]=g_fAcc[pastIdx]; featPast[3]=g_fMid[pastIdx];
            featPast[4]=g_fPct[pastIdx]; featPast[5]=g_fChn[pastIdx];
            featPast[6]=g_fSpr[pastIdx]; featPast[7]=g_fReg[pastIdx];
            int outcome = ClassifyOutcome(close, g_atr14, i, HORIZON_BARS, InpATRFactor);
            BankPush(featPast, (double)outcome);
            g_lastBankBar = i;
         }
      }

      //--- Fisher auto-optimize
      if(InpAutoOptimize && isConfirmed && g_bankSize >= AUTO_MIN_ROWS)
         ComputeFisherWeights();
      if(InpAutoOptimize) ArrayCopy(g_weights, g_autoW);

      //--- kNN
      SEngine eng = RunKNN(feat, g_weights);

      //--- Supertrend
      double hl2 = (high[i] + low[i]) / 2.0;
      double convInst = Clamp(eng.analogScore / 1.5, -1, 1);
      if(i == mainStart) g_convSmooth[i] = convInst;
      else g_convSmooth[i] = convInst * kEmaSmooth + g_convSmooth[i-1] * (1.0 - kEmaSmooth);
      double mlDrive = Clamp(MathAbs(g_convSmooth[i])*0.5 + eng.gapTight*0.3 + eng.agreeFrac*0.2, 0, 1);
      double trendForce = g_atr14[i] > 0 ? MathAbs(g_emaClose5[i] - g_emaClose50[i]) / g_atr14[i] : 0;
      bool chopRaw = trendForce < CHOP_CUT;
      if(chopRaw) mlDrive *= 0.35;
      double adaptMult = ST_MULT_BASE * (1.0 + 1.0 * (1.0 - mlDrive));
      double stAtr = g_atr10[i];
      double upBand = hl2 - adaptMult * stAtr;
      double dnBand = hl2 + adaptMult * stAtr;
      if(i == mainStart)
      { g_stLong[i] = upBand; g_stShort[i] = dnBand; g_stDir[i] = 1; }
      else
      {
         g_stLong[i] = (close[i-1] > g_stLong[i-1]) ? MathMax(upBand, g_stLong[i-1]) : upBand;
         g_stShort[i] = (close[i-1] < g_stShort[i-1]) ? MathMin(dnBand, g_stShort[i-1]) : dnBand;
         if(g_stDir[i-1]==-1 && close[i]>g_stShort[i-1])      g_stDir[i] = 1;
         else if(g_stDir[i-1]==1 && close[i]<g_stLong[i-1])    g_stDir[i] = -1;
         else                                                    g_stDir[i] = g_stDir[i-1];
      }

      //--- Context
      bool upTrend = (g_stDir[i]==1), downTrend = (g_stDir[i]==-1);
      double atrPct = PercentRank(g_atr14, i, 100);
      bool volHealthy = (atrPct >= VOL_BAND_LO && atrPct <= VOL_BAND_HI);
      bool slopeUp = (i >= STEP_LEN) ? g_rsiBase[i] > g_rsiBase[i-STEP_LEN] : true;
      bool slopeFit = (eng.biasDir==1 && slopeUp) || (eng.biasDir==-1 && !slopeUp);
      bool stretched = (eng.biasDir==1 && g_rsiBase[i]>70) || (eng.biasDir==-1 && g_rsiBase[i]<30);
      double oscReg = g_emaRsi20[i];
      bool oscSmoothUp = (i > 0) ? g_emaRsi5[i] > g_emaRsi5[i-1] : true;
      bool trendAligned = (eng.biasDir==1 && upTrend) || (eng.biasDir==-1 && downTrend);

      //--- Stance
      bool gatesPass = trendAligned && volHealthy && !chopRaw;
      int prevStance = g_stanceState;
      if(eng.biasDir==1 && gatesPass)       g_stanceState = 1;
      else if(eng.biasDir==-1 && gatesPass) g_stanceState = -1;
      bool stanceChanged = (g_stanceState != prevStance);
      if(stanceChanged) g_stanceAge = 0; else g_stanceAge++;
      bool earlyFlip = stanceChanged && g_stanceAge < 4;

      //--- Rank & Confidence
      double rank = RankScore(eng, trendAligned, atrPct, volHealthy, chopRaw,
                              slopeFit, stretched, oscReg, oscSmoothUp, g_stanceAge, earlyFlip);
      double conf = ConfScore(eng, slopeFit, g_stanceAge, earlyFlip);

      //--- ML RSI
      if(i == mainStart) g_emaRank[i] = rank;
      else g_emaRank[i] = rank * kEma3 + g_emaRank[i-1] * (1.0 - kEma3);
      double intensity = Clamp(g_emaRank[i] / 100.0, 0, 1);
      double mlTilt = Clamp(g_convSmooth[i], -1, 1) * intensity * 18.0;
      double rawMlRsi = Clamp(g_rsiBase[i] + mlTilt, 0, 100);
      if(i == mainStart) g_mlRsiArr[i] = rawMlRsi;
      else g_mlRsiArr[i] = rawMlRsi * kEma3 + g_mlRsiArr[i-1] * (1.0 - kEma3);

      //--- IFM Module Scores (5 juizes do par ativo)
      int scorePivot = CalcPivotScore(high, low, close, i);
      int scoreMP = CalcMPScore(close, g_emaClose21, i);
      int mfcColor = 3;
      int scoreMFC = CalcMFCScore(high, low, tick_volume, volume, i, InpMFCVolLength, mfcColor);
      int scoreMLRSI = CalcMLRSIScore(eng.biasDir, rank, conf);
      int scoreCCI = CalcCCIScore(g_cci, i);

      //--- Aggregation
      double ifmBruto = scorePivot*2.0 + scoreMP*2.0 + scoreMFC*1.0 + scoreMLRSI*3.0 + scoreCCI*3.0;
      double ifmFinal = Clamp((ifmBruto + 21.0) / 42.0 * 100.0, 0, 100);

      //--- Set buffers
      IFMBuf[i]   = ifmFinal;
      MLRSIBuf[i] = g_mlRsiArr[i];
      RankBuf[i]  = rank;
      ConfBuf[i]  = conf;

      //--- Cache active pair ML info (last closed bar)
      if(i == rt - 2)
      {
         g_activeIFM  = ifmFinal;
         g_activeRank = rank;
         g_activeConf = conf;
         g_activeBias = eng.biasDir;
      }
   }

   return rates_total;
}
//+------------------------------------------------------------------+

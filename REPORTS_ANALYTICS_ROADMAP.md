# 📊 Reports & Analytics Page - Product Roadmap

**Date:** January 21, 2026  
**Status:** 🚀 PLANNED  
**Objective:** Complete visibility into trading performance with market context analysis

---

## 🎯 High-Level Vision

Build a comprehensive **Reports & Analytics Dashboard** that shows:

1. **📈 Trade-by-Trade Analysis**
   - Every trade executed with full details
   - Entry/exit conditions, P&L, duration
   - Market context at execution time
   - Strategy used and confidence score

2. **🤖 Strategy Performance Analytics**
   - Win rate per strategy
   - Win rate per strategy + market context combination
   - Profitability metrics (gross P&L, Sharpe ratio)
   - Volume traded per strategy
   - Comparison: expected vs actual

3. **📊 Market Context Insights**
   - When each context was active
   - How strategies performed in each context
   - Strategy activation/skipping decisions
   - Context detection accuracy

4. **💾 Exportable Reports**
   - PDF summaries (daily, weekly, monthly)
   - CSV data for external analysis
   - Performance charts and graphs

---

## 📋 Detailed Feature Breakdown

### 1️⃣ **TRADES TAB - Trade History with Context**

#### Display All Trades (Sortable, Filterable)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Trade ID │ Time │ Bot/AI │ Symbol │ Side │ Entry │ Exit │ P&L │ %    │
├─────────────────────────────────────────────────────────────────────────┤
│ TRD-001  │ 14:32│ GridT  │ BTCUSDT│ BUY │ 43,250│ 43,500│+$250│+0.58%│
│ TRD-002  │ 14:45│ MeanRev│ ETHUSDT│ BUY │ 2,250 │ 2,240 │-$10 │-0.44%│
│ TRD-003  │ 15:10│ Scalp  │ SOLUSDT│ BUY │ 142.5 │ 142.8 │+$30 │+0.21%│
└─────────────────────────────────────────────────────────────────────────┘

Click on each row → See full details
```

#### Trade Details Panel (When Clicked)

```
═══════════════════════════════════════════════════════════════════════

TRADE TRD-001 - GridTrading BTCUSDT

📊 Trade Info
  Entry Time: 2026-01-21 14:32:15 UTC
  Exit Time:  2026-01-21 15:12:45 UTC
  Duration: 40 minutes 30 seconds
  Strategy: GridTrading (v1.2)
  Confidence: 78%

📈 Price Action
  Entry Price: $43,250.00
  Exit Price:  $43,500.00
  High: $43,620.00
  Low: $43,150.00
  Profit: $250.00 (+0.58%)

🎯 Risk Management
  Stop Loss (Target): $42,095.00
  Stop Loss (Hit): Not hit
  Take Profit (Target): $44,405.00
  Take Profit (Partial): $43,500.00 (hit)

📍 Market Context at Entry
  Context: STRONG_BULLISH
  SMA20: $43,200 | SMA50: $42,800 | SMA200: $41,500
  Alignment Score: 85%
  Volatility: 1.8x (vs average)
  Volume: 2.1x (vs average)
  Context Confidence: 92%

🤖 Execution Details
  Risk Manager: ✅ Approved
    - Position size: 5% of portfolio
    - No duplicate position found
    - Daily limit OK
  
  AI Analysis: (if applicable)
    - Technical confidence: 75%
    - ML confidence: 82%
    - Final confidence: 78%

═══════════════════════════════════════════════════════════════════════
```

#### Filters & Sorting

```
Filters:
  ├─ Date Range: [From] [To]
  ├─ Strategy: [GridTrading] [MeanReversion] [Scalping] [TrendFollowing] [All]
  ├─ Symbol: [BTCUSDT] [ETHUSDT] [SOLUSDT] [Search...]
  ├─ Market Context: [STRONG_BULLISH] [WEAK_BULLISH] [CHOPPY] [All]
  ├─ P&L: [Profitable] [Loss] [Breakeven] [All]
  ├─ Status: [Closed] [Open] [Partially Closed]
  └─ Min/Max P&L: [$___] to [$___]

Sorting:
  ├─ By Entry Time (newest/oldest)
  ├─ By Profit (highest/lowest)
  ├─ By Duration (longest/shortest)
  ├─ By Strategy
  └─ By Context
```

---

### 2️⃣ **STRATEGIES TAB - Performance by Strategy & Context**

#### Strategy Performance Matrix

```
┌────────────────────────────────────────────────────────────┐
│              STRATEGY PERFORMANCE ANALYSIS                 │
├────────────────────────────────────────────────────────────┤
│ Strategy      │ Trades │ Win %  │ Avg P&L │ Total P&L │ SR │
├────────────────────────────────────────────────────────────┤
│ GridTrading   │  16    │ 70%    │ +$32    │ +$512    │ 1.8│
│ MeanReversion │  8     │ 52%    │ +$18    │ +$144    │ 1.2│
│ Scalping      │  12    │ 41%    │ -$2     │ -$24     │ 0.6│
│ TrendFollowing│  5     │ 35%    │ -$14    │ -$70     │ 0.2│
│ TOTAL         │  41    │ 54%    │ +$18    │ +$562    │ 1.3│
└────────────────────────────────────────────────────────────┘

Metrics Explained:
  • Win %: (Profitable trades / Total trades) × 100
  • Avg P&L: Average profit/loss per trade
  • Total P&L: Sum of all profits and losses
  • SR: Sharpe Ratio (risk-adjusted returns)
```

#### Strategy by Market Context

```
┌──────────────────────────────────────────────────────────────────────┐
│        MEANREVERSION WIN RATE BY MARKET CONTEXT                      │
├──────────────────────────────────────────────────────────────────────┤
│ Context        │ Trades │ Win % │ Avg P&L │ Best Trade │ Worst Trade│
├──────────────────────────────────────────────────────────────────────┤
│ STRONG_BULLISH │   0    │  N/A  │   N/A   │    N/A     │     N/A    │
│ WEAK_BULLISH   │   4    │ 75%   │ +$24    │   +$62     │    -$18    │
│ CHOPPY         │   0    │  N/A  │   N/A   │    N/A     │     N/A    │
│ WEAK_BEARISH   │   3    │ 33%   │ +$8     │   +$25     │    -$15    │
│ STRONG_BEARISH │   0    │  N/A  │   N/A   │    N/A     │     N/A    │
│ UNKNOWN*       │   1    │  0%   │ -$10    │   -$10     │     N/A    │
└──────────────────────────────────────────────────────────────────────┘

*UNKNOWN = Context not recorded (trades before StrategyContextManager)
```

#### Individual Strategy Details

```
═════════════════════════════════════════════════════════════

GRIDTRADING PERFORMANCE DASHBOARD

📊 Summary Metrics
  Total Trades: 16
  Win Rate: 70% (11 profitable / 5 losses)
  Profit Factor: 3.2x (Wins / Losses)
  Average Win: +$45
  Average Loss: -$15
  Largest Win: +$120 (TRD-001)
  Largest Loss: -$35 (TRD-012)
  
  Gross P&L: +$512
  Net Return: +5.12% (of portfolio)
  Sharpe Ratio: 1.8 (good risk-adjusted returns)
  Max Drawdown: -8.5% (acceptable)
  Recovery Time: 3 trades

📈 Symbols Performance
  BTCUSDT: 8 trades, 75% win, +$320
  ETHUSDT: 5 trades, 70% win, +$145
  SOLUSDT: 3 trades, 60% win, +$47

📍 Context Performance
  ✅ STRONG_BULLISH: 8 trades, 75% win (best context)
  ✅ WEAK_BULLISH: 5 trades, 68% win
  ⚠️  CHOPPY: 3 trades, 50% win (worst context)

⏰ Time Analysis
  Best Hour: 14:00-15:00 UTC (5 trades, 80% win)
  Worst Hour: 21:00-22:00 UTC (2 trades, 25% win)
  Average Trade Duration: 45 minutes

═════════════════════════════════════════════════════════════
```

---

### 3️⃣ **MARKET CONTEXT TAB - Context Timeline & Analysis**

#### Context Timeline

```
┌───────────────────────────────────────────────────────────────────────┐
│              MARKET CONTEXT TIMELINE (Last 7 Days)                    │
├───────────────────────────────────────────────────────────────────────┤
│
│ Jan 21 10:00-12:00 ▓▓▓▓▓▓ STRONG_BULLISH (92% confidence)
│                     Trades: 5 | Win: 80% | Strategies Active: Grid, Trend
│
│ Jan 21 12:00-14:00 ░░░░░░ WEAK_BULLISH (68% confidence)
│                     Trades: 8 | Win: 62% | Strategies Active: Grid, Mean
│
│ Jan 21 14:00-16:00 ▓▓▓▓▓▓ STRONG_BULLISH (85% confidence)
│                     Trades: 12 | Win: 75% | Strategies Active: Grid, Scalp
│
│ Jan 21 16:00-18:00 ░░░░░░ WEAK_BULLISH (55% confidence)
│                     Trades: 3 | Win: 33% | Strategies Active: Grid
│
│ Jan 21 18:00-20:00 ███░░░ CHOPPY (40% confidence)
│                     Trades: 2 | Win: 0% | Strategies Active: None
│
│ Jan 21 20:00-22:00 ▓▓▓▓▓▓ STRONG_BEARISH (78% confidence)
│                     Trades: 4 | Win: 50% | Strategies Active: Trend, Scalp
│
└───────────────────────────────────────────────────────────────────────┘

Legend:
  ▓▓▓ STRONG trend (all SMAs aligned) - Best for TrendFollowing
  ░░░ WEAK trend (choppy pullbacks) - Best for MeanReversion
  ███ CHOPPY (conflicting signals) - Avoid most strategies
```

#### Context Statistics

```
═════════════════════════════════════════════════════════════

MARKET CONTEXT ANALYSIS (Last 7 Days)

📊 Context Distribution
  STRONG_BULLISH:  35% of time (52h) | 88 trades | 72% win rate
  WEAK_BULLISH:    28% of time (42h) | 65 trades | 58% win rate
  WEAK_BEARISH:    18% of time (27h) | 42 trades | 45% win rate
  STRONG_BEARISH:  12% of time (18h) | 28 trades | 50% win rate
  CHOPPY:          7%  of time (11h) | 5 trades  | 20% win rate

📈 Win Rate by Context (SORTED)
  1st ⭐ STRONG_BULLISH:  72% (best for all strategies)
  2nd ⭐ WEAK_BULLISH:    58% (best for MeanReversion)
  3rd   STRONG_BEARISH:  50% (workable for TrendFollowing)
  4th   WEAK_BEARISH:    45% (contrarian opportunity)
  5th   CHOPPY:          20% (avoid trading)

📍 Strategy Activation in Contexts
  When STRONG_BULLISH:
    ✅ GridTrading: Always active | Wins: 42/56 (75%)
    ❌ MeanReversion: Disabled by design
    ✅ TrendFollowing: Active | Wins: 18/24 (75%)
    ✅ Scalping: If volatility spike | Wins: 8/12 (67%)
    
  When WEAK_BULLISH:
    ✅ GridTrading: Always active | Wins: 38/55 (69%)
    ✅ MeanReversion: Active | Wins: 18/25 (72%)
    ❌ TrendFollowing: Disabled by design
    ⚠️  Scalping: Rarely triggered (low volatility)

🎯 Context Detection Accuracy
  STRONG_BULLISH: SMA20>50>200 in 94% of cases (reliable)
  WEAK_BULLISH: Price>50>200 in 91% of cases (reliable)
  CHOPPY: Conflicting signals detected in 87% of cases (reliable)

═════════════════════════════════════════════════════════════
```

---

### 4️⃣ **KEY PERFORMANCE INDICATORS (KPI) CARDS**

```
┌──────────────────┬──────────────────┬──────────────────┬──────────────────┐
│  Win Rate        │  Profit Factor   │  Sharpe Ratio    │  Max Drawdown    │
│  ┌────────────┐  │  ┌────────────┐  │  ┌────────────┐  │  ┌────────────┐  │
│  │    54%     │  │  │    2.1x    │  │  │    1.3     │  │  │   -8.5%    │  │
│  │   ↑ 12%   │  │  │   ↑ 15%   │  │  │   ↑ 8%    │  │  │   ↓ 2%    │  │
│  └────────────┘  │  └────────────┘  │  └────────────┘  │  └────────────┘  │
│  vs 38.2% before │  vs 1.8x before  │  vs 0.8 before   │  vs -10% before  │
└──────────────────┴──────────────────┴──────────────────┴──────────────────┘

┌──────────────────┬──────────────────┬──────────────────┬──────────────────┐
│  Total P&L       │  Avg Trade P&L   │  Trading Volume  │  Return on Risk  │
│  ┌────────────┐  │  ┌────────────┐  │  ┌────────────┐  │  ┌────────────┐  │
│  │   +$562    │  │  │   +$13.70  │  │  │   $8,420   │  │  │    6.6x    │  │
│  │   ↑ $412  │  │  │   ↑ $8.15 │  │  │   ↑ $3,200 │  │  │   ↑ 2.1x   │  │
│  └────────────┘  │  └────────────┘  │  └────────────┘  │  └────────────┘  │
│  41 trades total │  YTD average      │  Capital used    │  Profit/Risk     │
└──────────────────┴──────────────────┴──────────────────┴──────────────────┘
```

---

## 🛠️ Technical Implementation Plan

### Backend Changes Required

#### 1. Extend Trade Model (Database)

```python
# In app/models/database_models.py

class Trade(Base):
    __tablename__ = "trades"
    
    # Existing fields...
    id = Column(UUID, primary_key=True)
    user_id = Column(UUID, ForeignKey("users.id"))
    
    # NEW FIELDS FOR REPORTING:
    market_context = Column(String)          # STRONG_BULLISH, etc.
    context_confidence = Column(Float)       # 0-100%
    sma_20 = Column(Float)                   # Entry context
    sma_50 = Column(Float)                   # Entry context
    sma_200 = Column(Float)                  # Entry context
    volatility_ratio = Column(Float)         # 1.8x, 2.1x, etc.
    volume_ratio = Column(Float)             # 1.5x, 2.0x, etc.
    strategy_name = Column(String)           # "GridTrading", etc.
    ai_confidence = Column(Float)            # ML + technical blend
    risk_manager_check = Column(String)      # APPROVED, BLOCKED, etc.
    entry_conditions = Column(JSON)          # {rsi: 35, bb_lower: true}
    exit_reason = Column(String)             # "TP_HIT", "SL_HIT", "MANUAL"
    
    # Calculated fields
    duration_minutes = Column(Integer)       # Exit - Entry
    win_loss = Column(String)                # WIN, LOSS, BREAKEVEN
```

#### 2. New API Endpoints

```python
# Route 1: Get detailed trade history with context
GET /api/trades/history
  params:
    - from_date: datetime
    - to_date: datetime
    - strategy: string (optional)
    - symbol: string (optional)
    - market_context: string (optional)
    - status: string (optional)
    - limit: int
  returns:
    - trades: [{
        id, symbol, side, entry_price, exit_price, pnl, pnl_percent,
        entry_time, exit_time, duration_seconds,
        strategy_name, ai_confidence, risk_check,
        market_context, context_confidence, 
        sma_20, sma_50, sma_200,
        volatility_ratio, volume_ratio,
        entry_conditions, exit_reason
      }]

# Route 2: Get strategy performance by context
GET /api/strategies/performance
  params:
    - strategy: string (optional)
    - market_context: string (optional)
    - from_date: datetime
  returns:
    - strategies: [{
        name, total_trades, win_rate, win_count, loss_count,
        avg_profit, total_profit, avg_loss, total_loss,
        profit_factor, sharpe_ratio, max_drawdown,
        best_trade, worst_trade,
        by_context: [{
          context, trades, win_rate, avg_profit
        }]
      }]

# Route 3: Get market context timeline
GET /api/market/context-timeline
  params:
    - from_date: datetime
    - to_date: datetime
  returns:
    - timeline: [{
        timestamp, context, confidence,
        sma_20, sma_50, sma_200,
        volatility_ratio, volume_ratio,
        active_strategies: [names],
        trades_in_period: count,
        win_rate_in_period: percent
      }]

# Route 4: Get KPI summary
GET /api/reports/kpi-summary
  returns:
    - win_rate: percent
    - profit_factor: float
    - sharpe_ratio: float
    - max_drawdown: percent
    - total_pnl: float
    - avg_trade_pnl: float
    - win_loss_ratio: float
    - return_on_risk: float
```

#### 3. Update Trade Creation (Capture Context)

When a trade is created, capture market context:

```python
# In bot_engine.py _execute_buy()

# Capture market context at trade entry
trade = Trade(
    # ... existing fields ...
    
    # NEW: Market context
    market_context=context_analysis.market_context.value,
    context_confidence=context_analysis.confidence,
    sma_20=context_analysis.sma_20,
    sma_50=context_analysis.sma_50,
    sma_200=context_analysis.sma_200,
    volatility_ratio=context_analysis.volatility_ratio,
    volume_ratio=context_analysis.volume_ratio,
    
    # NEW: Strategy metadata
    strategy_name=bot_state.get("strategy", "unknown"),
    ai_confidence=ai_validation.get("confidence", 0) if ai_validation else None,
    entry_conditions={
        "rsi": market_data.get("indicators", {}).get("rsi"),
        "bb_lower_hit": market_data.get("close") <= market_data.get("indicators", {}).get("bb_lower"),
        "price_below_sma50": market_data.get("close") < context_analysis.sma_50
    }
)
```

---

### Frontend Changes Required

#### 1. New Route: `/reports`

```
/reports
├─ /reports/trades          ← Trade history with filters
├─ /reports/strategies      ← Strategy performance analysis
├─ /reports/context         ← Market context insights
└─ /reports/dashboard       ← KPI summary + charts
```

#### 2. React Components

```
components/reports/
├─ TradeHistoryTable.jsx        (sortable, filterable table)
│   ├─ Columns: Time, Bot, Symbol, Side, Entry, Exit, P&L, %
│   ├─ Row click → TradeDetailsPanel
│   └─ Filters: Date, Strategy, Symbol, Context, P&L
│
├─ TradeDetailsPanel.jsx        (detailed view when clicked)
│   ├─ Trade info (entry/exit times, duration)
│   ├─ Price action (OHLC, profit)
│   ├─ Risk management (SL, TP)
│   ├─ Market context (SMAs, alignment, volatility)
│   ├─ AI analysis (if applicable)
│   └─ Execution details
│
├─ StrategyPerformanceTable.jsx  (summary table)
│   ├─ Strategy | Trades | Win % | Avg P&L | Total P&L | Sharpe
│   └─ Row click → StrategyDetailsPanel
│
├─ StrategyDetailsPanel.jsx      (drill-down view)
│   ├─ Summary metrics (trades, win rate, profit factor)
│   ├─ By symbol breakdown
│   ├─ By context performance matrix
│   ├─ Time analysis (best/worst hours)
│   └─ Charts (equity curve, drawdown)
│
├─ ContextTimeline.jsx           (horizontal timeline)
│   ├─ Visual timeline of market contexts
│   ├─ Trades executed per context
│   ├─ Win rate per context period
│   └─ Strategy activation per context
│
├─ ContextStatsTable.jsx         (context performance)
│   ├─ Context | Time % | Trades | Win % | Avg P&L
│   └─ Strategy activation per context
│
├─ KPICards.jsx                  (dashboard header)
│   ├─ Win Rate | Profit Factor | Sharpe | Max Drawdown
│   ├─ Total P&L | Avg P&L | Volume | ROR
│   └─ Trending indicators (up/down vs previous)
│
├─ ReportsPage.jsx               (main page with tabs)
│   ├─ Tabs: Trades | Strategies | Context | Dashboard
│   ├─ Date range picker
│   ├─ Export button (PDF/CSV)
│   └─ Refresh data button
│
└─ ChartLibrary.jsx              (Recharts visualizations)
    ├─ EquityCurve.jsx           (cumulative P&L over time)
    ├─ DrawdownChart.jsx         (peak-to-trough losses)
    ├─ WinRateByContext.jsx      (bar chart)
    ├─ StrategyComparison.jsx    (multi-strategy comparison)
    └─ ContextDistribution.jsx   (pie chart of context time)
```

#### 3. Filters Component

```jsx
<ReportFilters
  dateFrom={dateFrom}
  dateTo={dateTo}
  selectedStrategies={[]}  // Multi-select
  selectedSymbols={[]}     // Multi-select
  selectedContexts={[]}    // Multi-select
  minPnL={null}
  maxPnL={null}
  onFilter={handleFilter}
/>
```

---

## 📊 Sample Data Structure (API Response)

```json
{
  "trades": [
    {
      "id": "TRD-001",
      "timestamp": "2026-01-21T14:32:15Z",
      "symbol": "BTCUSDT",
      "side": "BUY",
      "entry_price": 43250.00,
      "exit_price": 43500.00,
      "quantity": 0.025,
      "pnl": 6.25,
      "pnl_percent": 0.58,
      "duration_seconds": 2430,
      "strategy_name": "GridTrading",
      "ai_confidence": 78.5,
      "risk_check": "APPROVED",
      "market_context": "STRONG_BULLISH",
      "context_confidence": 92.0,
      "sma_20": 43200.00,
      "sma_50": 42800.00,
      "sma_200": 41500.00,
      "volatility_ratio": 1.8,
      "volume_ratio": 2.1,
      "entry_conditions": {
        "rsi": 42,
        "bb_lower_hit": false,
        "price_below_sma50": false
      },
      "exit_reason": "TP_HIT"
    }
  ],
  "summary": {
    "total_trades": 41,
    "win_rate": 54.0,
    "profit_factor": 2.1,
    "total_pnl": 562.50,
    "avg_pnl": 13.70,
    "sharpe_ratio": 1.3,
    "max_drawdown": -8.5
  }
}
```

---

## 🎯 Priority & Phases

### **Phase 1: MVP (Week 1-2)**
Priority: HIGH - Core functionality
- [ ] Extend Trade model with context fields
- [ ] Create /api/trades/history endpoint
- [ ] Create TradeHistoryTable component
- [ ] Create TradeDetailsPanel component
- [ ] Add basic filters (date, strategy, symbol)
- [ ] Create ReportsPage with Trades tab

### **Phase 2: Strategy Analytics (Week 2-3)**
Priority: HIGH - Core insights
- [ ] Create /api/strategies/performance endpoint
- [ ] Create StrategyPerformanceTable component
- [ ] Create StrategyDetailsPanel component
- [ ] Add by-context performance matrix
- [ ] Create charts (win rate by context)

### **Phase 3: Market Context (Week 3-4)**
Priority: MEDIUM - Deep analysis
- [ ] Create /api/market/context-timeline endpoint
- [ ] Create ContextTimeline component
- [ ] Create ContextStatsTable component
- [ ] Add context distribution pie chart

### **Phase 4: Dashboard & Export (Week 4-5)**
Priority: MEDIUM - Polish
- [ ] Create /api/reports/kpi-summary endpoint
- [ ] Create KPICards component
- [ ] Create EquityCurve and DrawdownChart
- [ ] Add PDF/CSV export functionality

---

## 💡 Key Features by Tab

### Trades Tab
✅ See every trade with full details  
✅ Filter by date, strategy, symbol, context  
✅ Sort by entry time, profit, duration  
✅ Click to see market context at entry  
✅ See strategy activation decision  

### Strategies Tab
✅ Compare all strategies side-by-side  
✅ See win rate by context for each strategy  
✅ Identify best/worst performing strategies  
✅ Track which contexts favor which strategies  
✅ Chart equity curve per strategy  

### Context Tab
✅ See when each market context was active  
✅ Track strategy performance per context  
✅ Identify optimal market conditions  
✅ See strategy activation/skipping decisions  

### Dashboard Tab
✅ High-level KPI cards (win rate, Sharpe, etc.)  
✅ Equity curve chart  
✅ Drawdown analysis  
✅ Strategy comparison chart  
✅ Context distribution  

---

## 🚀 Expected Outcomes

After implementing this Reports & Analytics page, you'll have:

1. **Complete Visibility** - See every trade's full context
2. **Data-Driven Decisions** - Identify which strategies work in which contexts
3. **Continuous Improvement** - Track win rates and optimize parameters
4. **Context Validation** - Confirm that StrategyContextManager is working correctly
5. **Export Capability** - Share reports with stakeholders or external analysis

---

## 📝 Notes

- All timestamps in UTC
- All monetary values in USDT
- Percentages rounded to 2 decimals
- Charts use Recharts library (already in project)
- Responsive design (mobile-friendly)
- Dark mode compatible

---

**Status:** Ready to prioritize tasks in your todo list!

Would you like me to start with Phase 1 (Trade History)? That's the foundation for everything else.

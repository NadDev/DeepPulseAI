# 📊 REPORTING & ANALYTICS PLAN

## 📋 TABLE DES MATIÈRES
1. [Overview](#overview)
2. [Database Schema](#database-schema)
3. [API Endpoints](#api-endpoints)
4. [Frontend Components](#frontend-components)
5. [Report Types](#report-types)
6. [Export Formats](#export-formats)
7. [Real-time Streaming](#real-time-streaming)
8. [Analytics Pipeline](#analytics-pipeline)
9. [Performance Queries](#performance-queries)

---

## 🎯 OVERVIEW

### Objectifs
- 📈 **Suivi complet** : Tous les trades, signaux, événements
- 🔍 **Audit trail** : Traçabilité 100% de toutes les opérations
- 📊 **Comparaison stratégies** : Quelle stratégie performe le mieux?
- 💰 **Analytics financières** : Sharpe, Drawdown, Profit Factor, etc.
- 📤 **Exports** : CSV, Excel, PDF pour analyses externes
- ⚡ **Real-time** : Dashboard live sans délai

### Architecture
```
Database (PostgreSQL)
    ↓
API Backend (FastAPI)
    ├── Endpoints de lecture (rapports)
    ├── Endpoints d'export (CSV/Excel/PDF)
    └── WebSocket (streaming temps réel)
    ↓
Frontend (React)
    ├── Dashboard Résumé
    ├── Trades Table avec filtres
    ├── Stratégies Comparaison
    ├── Charts Performance
    └── Risk Events
```

---

## 💾 DATABASE SCHEMA

### 1. Table Maîtresse: TRADES

```sql
CREATE TABLE trades (
    -- Identifiers
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bot_id UUID NOT NULL REFERENCES bots(id) ON DELETE CASCADE,
    exchange_order_id VARCHAR UNIQUE,  -- ID du broker
    
    -- Strategy Info
    strategy_name VARCHAR NOT NULL,  -- 'trend_following', 'breakout', etc.
    strategy_version VARCHAR,  -- Pour tracking d'évolutions
    
    -- Asset Info
    symbol VARCHAR NOT NULL,  -- 'BTC/USD', 'ETH/USDT'
    asset_class VARCHAR,  -- 'crypto', 'forex', 'stock'
    
    -- Entry Information
    entry_time TIMESTAMP NOT NULL,
    entry_price NUMERIC(20,8) NOT NULL,
    entry_signal VARCHAR NOT NULL,  -- 'RSI_OVERSOLD', 'BREAKOUT_CONFIRMED', 'ELLIOTT_WAVE_5'
    entry_timeframe VARCHAR,  -- '1h', '4h', '1d'
    
    -- Position Info
    position_size NUMERIC(20,8) NOT NULL,
    position_value NUMERIC(20,2),  -- position_size * entry_price
    
    -- Risk Parameters
    stop_loss_price NUMERIC(20,8) NOT NULL,
    stop_loss_percent NUMERIC(5,2),  -- Distance en %
    
    -- Take Profit Levels (JSON array for multiple TP)
    take_profit_levels JSONB DEFAULT '[
        {"level": 0.02, "quantity": 0.5},
        {"level": 0.05, "quantity": 0.3},
        {"level": 0.12, "quantity": 0.2}
    ]'::jsonb,
    
    -- Exit Information (null si trade ouvert)
    exit_time TIMESTAMP,
    exit_price NUMERIC(20,8),
    exit_reason VARCHAR,  -- 'TAKE_PROFIT_1', 'STOP_LOSS', 'MANUAL_EXIT', 'SIGNAL_EXIT'
    exit_timeframe VARCHAR,
    partial_exits JSONB DEFAULT '[]'::jsonb,  -- [{"time": "...", "price": "...", "qty": "..."}]
    
    -- Performance Metrics
    pnl NUMERIC(20,2),  -- Profit & Loss en $
    pnl_percent NUMERIC(7,3),  -- % de retour sur position
    pnl_percent_account NUMERIC(7,3),  -- % de retour sur compte
    
    -- Trade Duration & Timing
    duration_hours NUMERIC(10,2),
    duration_minutes NUMERIC(10,2),
    time_to_profit INTERVAL,  -- Temps avant profit
    
    -- Execution Quality
    slippage NUMERIC(7,3),  -- Différence entry vs réelle
    execution_time_ms INT,  -- Latence d'exécution
    
    -- Status & Classification
    status VARCHAR NOT NULL CHECK (status IN ('OPEN', 'CLOSED', 'CANCELLED', 'ERROR')),
    trade_type VARCHAR,  -- 'LONG', 'SHORT'
    win_loss VARCHAR,  -- 'WIN', 'LOSS', 'BREAK_EVEN', 'OPEN'
    
    -- Metadata
    notes TEXT,
    tags JSONB DEFAULT '[]'::jsonb,  -- ["manual_adjustment", "high_volatility"]
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    closed_at TIMESTAMP,
    
    -- Indexing for performance
    CONSTRAINT valid_prices CHECK (exit_price IS NULL OR exit_price > 0),
    INDEX trades_bot_id ON trades(bot_id),
    INDEX trades_strategy_name ON trades(strategy_name),
    INDEX trades_symbol ON trades(symbol),
    INDEX trades_created_at ON trades(created_at),
    INDEX trades_status ON trades(status)
);
```

### 2. Table: TRADE_EVENTS (Audit Trail)

```sql
CREATE TABLE trade_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trade_id UUID NOT NULL REFERENCES trades(id) ON DELETE CASCADE,
    
    -- Event Info
    event_type VARCHAR NOT NULL CHECK (event_type IN (
        'ENTRY', 'PARTIAL_EXIT', 'FULL_EXIT', 
        'STOP_LOSS_TRIGGERED', 'TAKE_PROFIT_TRIGGERED',
        'PRICE_UPDATE', 'SIGNAL_CHANGE', 'MANUAL_ADJUSTMENT',
        'ERROR', 'POSITION_RESIZE'
    )),
    event_time TIMESTAMP NOT NULL,
    
    -- Trade Data at Event Time
    price NUMERIC(20,8) NOT NULL,
    quantity NUMERIC(20,8),
    
    -- Event Details
    reason VARCHAR,  -- Why this event happened
    details JSONB,  -- {"slippage": 5, "execution_time": 150, "broker_latency": 45, ...}
    
    -- Actor Info
    triggered_by VARCHAR,  -- 'bot', 'manual', 'broker', 'system'
    actor_id VARCHAR,  -- User ID if manual
    
    created_at TIMESTAMP DEFAULT now(),
    
    INDEX trade_events_trade_id ON trade_events(trade_id),
    INDEX trade_events_event_type ON trade_events(event_type),
    INDEX trade_events_created_at ON trade_events(created_at)
);
```

### 3. Table: STRATEGY_PERFORMANCE (Stats Agrégées)

```sql
CREATE TABLE strategy_performance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Identifiers
    strategy_name VARCHAR NOT NULL,
    bot_id UUID REFERENCES bots(id),
    
    -- Time Window
    period_start TIMESTAMP NOT NULL,
    period_end TIMESTAMP NOT NULL,
    period_type VARCHAR,  -- 'DAILY', 'WEEKLY', 'MONTHLY', 'ALL_TIME'
    
    -- Trade Statistics
    total_trades INT DEFAULT 0,
    winning_trades INT DEFAULT 0,
    losing_trades INT DEFAULT 0,
    break_even_trades INT DEFAULT 0,
    
    -- Performance Metrics
    win_rate NUMERIC(5,4),  -- 0-1 (0.58 = 58%)
    profit_factor NUMERIC(10,3),  -- total_wins / total_losses
    expectancy NUMERIC(10,2),  -- Average PnL per trade
    
    -- Returns
    total_pnl NUMERIC(20,2),
    total_return_percent NUMERIC(8,3),
    avg_win NUMERIC(10,2),
    avg_loss NUMERIC(10,2),
    largest_win NUMERIC(20,2),
    largest_loss NUMERIC(20,2),
    
    -- Risk Metrics
    max_drawdown NUMERIC(8,3),  -- Maximum peak-to-trough decline
    current_drawdown NUMERIC(8,3),
    
    -- Advanced Metrics
    sharpe_ratio NUMERIC(8,3),  -- Risk-adjusted returns
    sortino_ratio NUMERIC(8,3),  -- Downside deviation only
    calmar_ratio NUMERIC(8,3),  -- Return / Max Drawdown
    
    -- Trade Duration
    avg_trade_duration_hours NUMERIC(10,2),
    longest_trade_hours NUMERIC(10,2),
    shortest_trade_hours NUMERIC(10,2),
    
    -- Execution Quality
    avg_slippage NUMERIC(7,3),
    avg_execution_time_ms INT,
    
    -- Streak Analysis
    current_streak INT,  -- Positive = wins, negative = losses
    longest_win_streak INT,
    longest_loss_streak INT,
    
    -- Updated timestamp
    last_updated TIMESTAMP DEFAULT now(),
    
    UNIQUE(strategy_name, bot_id, period_start, period_type),
    INDEX strategy_perf_strategy ON strategy_performance(strategy_name),
    INDEX strategy_perf_period ON strategy_performance(period_start, period_end)
);
```

### 4. Table: RISK_EVENTS (Risk Tracking)

```sql
CREATE TABLE risk_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bot_id UUID REFERENCES bots(id),
    
    -- Event Classification
    event_type VARCHAR NOT NULL CHECK (event_type IN (
        'DRAWDOWN_WARNING', 'DRAWDOWN_CRITICAL',
        'DAILY_LOSS_WARNING', 'DAILY_LOSS_CRITICAL',
        'MAX_POSITIONS_REACHED', 'CORRELATION_HIGH',
        'POSITION_OVER_SIZE', 'VOLATILITY_SPIKE',
        'API_ERROR', 'EXECUTION_ERROR'
    )),
    severity VARCHAR NOT NULL CHECK (severity IN ('INFO', 'WARNING', 'CRITICAL')),
    
    -- Event Data
    value NUMERIC(10,3),  -- Current value
    threshold NUMERIC(10,3),  -- Limit that was breached
    metric_name VARCHAR,  -- 'drawdown', 'daily_loss', 'correlation'
    
    -- Action Taken
    action_taken VARCHAR,  -- "Reduced position sizes by 50%"
    action_successful BOOLEAN,
    
    -- Context
    details JSONB,  -- Additional context
    affected_trades JSONB,  -- IDs of affected trades
    
    timestamp TIMESTAMP DEFAULT now(),
    resolved_at TIMESTAMP,
    
    INDEX risk_events_bot_id ON risk_events(bot_id),
    INDEX risk_events_severity ON risk_events(severity),
    INDEX risk_events_timestamp ON risk_events(timestamp)
);
```

### 5. Table: BOT_METRICS (Time Series)

```sql
CREATE TABLE bot_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bot_id UUID NOT NULL REFERENCES bots(id) ON DELETE CASCADE,
    
    -- Timestamp (1 data point par 5 minutes)
    timestamp TIMESTAMP NOT NULL,
    
    -- Portfolio Status
    account_balance NUMERIC(20,2),
    portfolio_value NUMERIC(20,2),
    cash NUMERIC(20,2),
    
    -- Position Status
    open_positions INT,
    total_exposure NUMERIC(20,2),
    
    -- Running Metrics
    daily_pnl NUMERIC(20,2),
    daily_return_percent NUMERIC(8,3),
    monthly_pnl NUMERIC(20,2),
    cumulative_pnl NUMERIC(20,2),
    
    -- Risk Metrics
    current_drawdown NUMERIC(8,3),
    
    created_at TIMESTAMP DEFAULT now(),
    
    INDEX bot_metrics_bot_id ON bot_metrics(bot_id),
    INDEX bot_metrics_timestamp ON bot_metrics(timestamp)
);

-- Retention: Keep 5 years of data (5 min granularity = ~500K rows/year)
-- After 1 year, compress to 1h intervals via materialized view
```

### 6. Materialized View: STRATEGY_COMPARISON

```sql
CREATE MATERIALIZED VIEW strategy_comparison_view AS
SELECT 
    sp.strategy_name,
    COUNT(DISTINCT sp.bot_id) as active_bots,
    SUM(sp.total_trades) as total_trades,
    AVG(sp.win_rate) as avg_win_rate,
    AVG(sp.profit_factor) as avg_profit_factor,
    SUM(sp.total_pnl) as total_pnl,
    AVG(sp.sharpe_ratio) as avg_sharpe_ratio,
    AVG(sp.max_drawdown) as avg_max_drawdown,
    MAX(sp.last_updated) as last_updated
FROM strategy_performance sp
WHERE sp.period_type = 'ALL_TIME'
GROUP BY sp.strategy_name
ORDER BY total_pnl DESC;

-- Refresh daily at midnight
-- REFRESH MATERIALIZED VIEW strategy_comparison_view;
```

---

## 🔌 API ENDPOINTS

### Authentication (All endpoints require JWT)
```
Authorization: Bearer <token>
Content-Type: application/json
```

### 1. TRADES ENDPOINTS

#### GET /api/reports/trades
**Get all trades with filters**
```bash
curl -X GET "http://localhost:8000/api/reports/trades?bot_id=bot_123&status=CLOSED&days=30&limit=100"

Response:
{
  "total": 150,
  "page": 1,
  "limit": 100,
  "trades": [
    {
      "id": "trade_123",
      "symbol": "BTC/USD",
      "entry_time": "2025-12-05T10:30:00Z",
      "entry_price": 50000,
      "entry_signal": "RSI_OVERSOLD",
      "position_size": 1.0,
      "exit_time": "2025-12-05T14:30:00Z",
      "exit_price": 51000,
      "exit_reason": "TAKE_PROFIT_1",
      "pnl": 1000,
      "pnl_percent": 2.0,
      "duration_hours": 4,
      "status": "CLOSED",
      "strategy": "trend_following",
      "win_loss": "WIN",
      "slippage": 0.5
    }
  ]
}
```

**Query Parameters:**
- `bot_id` (optional) : Filter by bot
- `strategy` (optional) : Filter by strategy name
- `symbol` (optional) : Filter by crypto symbol
- `status` (optional) : OPEN, CLOSED, ALL
- `days` (optional) : Last N days (default: 30)
- `start_date` (optional) : ISO datetime
- `end_date` (optional) : ISO datetime
- `win_loss` (optional) : WIN, LOSS, BREAK_EVEN
- `limit` (default: 100, max: 1000)
- `offset` (default: 0) : For pagination

#### GET /api/reports/trades/{trade_id}
**Get detailed info for single trade**
```bash
curl -X GET "http://localhost:8000/api/reports/trades/trade_123"

Response:
{
  "trade": {
    "id": "trade_123",
    "symbol": "BTC/USD",
    "strategy": "trend_following",
    "entry_time": "2025-12-05T10:30:00Z",
    "entry_price": 50000,
    "entry_signal": "RSI_OVERSOLD",
    "entry_details": {
      "rsi_value": 28.5,
      "sma_20": 49800,
      "sma_50": 49500,
      "volume_spike": 1.5
    },
    "position_size": 1.0,
    "stop_loss": 49000,
    "take_profit_levels": [
      {"level": 0.02, "quantity": 0.5, "hit": true},
      {"level": 0.05, "quantity": 0.3, "hit": true},
      {"level": 0.12, "quantity": 0.2, "hit": false}
    ],
    "exit_time": "2025-12-05T14:30:00Z",
    "exit_price": 51000,
    "exit_reason": "TAKE_PROFIT_1",
    "pnl": 1000,
    "pnl_percent": 2.0,
    "duration_hours": 4.0,
    "slippage": 0.5,
    "execution_time_ms": 150
  },
  "events": [
    {
      "timestamp": "2025-12-05T10:30:00Z",
      "event_type": "ENTRY",
      "price": 50000,
      "quantity": 1.0,
      "reason": "RSI oversold signal confirmed"
    },
    {
      "timestamp": "2025-12-05T12:00:00Z",
      "event_type": "PRICE_UPDATE",
      "price": 50500,
      "details": {"high": 50800, "low": 49950}
    },
    {
      "timestamp": "2025-12-05T12:30:00Z",
      "event_type": "PARTIAL_EXIT",
      "price": 50520,
      "quantity": 0.5,
      "reason": "Take profit 1 hit (2% gain)"
    },
    {
      "timestamp": "2025-12-05T14:30:00Z",
      "event_type": "PARTIAL_EXIT",
      "price": 51000,
      "quantity": 0.5,
      "reason": "Take profit 2 hit (5% gain)"
    }
  ],
  "metrics": {
    "entry_accuracy": 0.95,  // 0-1 score
    "execution_quality": 0.92,
    "risk_reward_ratio": 2.0,
    "time_to_tp1": "1h 30m",
    "best_price_hit": 51200,
    "best_price_percent": 2.4
  }
}
```

### 2. STRATEGY PERFORMANCE ENDPOINTS

#### GET /api/reports/strategies
**Compare all strategies**
```bash
curl -X GET "http://localhost:8000/api/reports/strategies?period=30d&bot_id=bot_123"

Response:
{
  "period": "Last 30 days",
  "strategies": [
    {
      "name": "trend_following",
      "total_trades": 45,
      "win_rate": 0.58,
      "profit_factor": 1.8,
      "expectancy": 500,
      "total_pnl": 22500,
      "total_return": 45.0,
      "avg_win": 1000,
      "avg_loss": 600,
      "largest_win": 5000,
      "largest_loss": 2000,
      "sharpe_ratio": 1.5,
      "max_drawdown": -15.2,
      "current_drawdown": -3.5,
      "avg_trade_duration": "4.5h",
      "longest_trade": "28h",
      "win_streak": 5,
      "loss_streak": 2
    },
    {
      "name": "breakout",
      "total_trades": 32,
      "win_rate": 0.52,
      "profit_factor": 1.3,
      "expectancy": 250,
      "total_pnl": 8000,
      "total_return": 16.0,
      "avg_win": 800,
      "avg_loss": 700,
      "largest_win": 3000,
      "largest_loss": 2500,
      "sharpe_ratio": 0.9,
      "max_drawdown": -22.1,
      "current_drawdown": -8.0,
      "avg_trade_duration": "2.5h",
      "longest_trade": "16h",
      "win_streak": 3,
      "loss_streak": 4
    }
  ],
  "best_performer": "trend_following",
  "total_combined_pnl": 30500
}
```

#### GET /api/reports/strategies/{strategy_name}
**Detailed strategy analysis**
```bash
curl -X GET "http://localhost:8000/api/reports/strategies/trend_following"

Response:
{
  "strategy": {
    "name": "trend_following",
    "description": "Follows market trends using SMA crossover",
    "version": "2.1.0",
    "created_at": "2025-10-01T00:00:00Z",
    "parameters": {
      "sma_fast": 20,
      "sma_slow": 50,
      "rsi_period": 14,
      "risk_percent": 1.5
    }
  },
  "statistics": {
    "total_trades": 45,
    "win_rate": 0.58,
    "profit_factor": 1.8,
    "total_pnl": 22500,
    "sharpe_ratio": 1.5
  },
  "by_symbol": [
    {"symbol": "BTC/USD", "trades": 20, "win_rate": 0.65, "pnl": 15000},
    {"symbol": "ETH/USD", "trades": 15, "win_rate": 0.53, "pnl": 5000},
    {"symbol": "XRP/USD", "trades": 10, "win_rate": 0.50, "pnl": 2500}
  ],
  "by_timeframe": [
    {"timeframe": "1h", "trades": 15, "win_rate": 0.60, "pnl": 8000},
    {"timeframe": "4h", "trades": 20, "win_rate": 0.60, "pnl": 12000},
    {"timeframe": "1d", "trades": 10, "win_rate": 0.50, "pnl": 2500}
  ],
  "hourly_performance": [...],  // Performance by hour of day
  "seasonal_performance": [...]  // Performance by month
}
```

### 3. DASHBOARD ENDPOINTS

#### GET /api/reports/dashboard
**Get summary for main dashboard**
```bash
curl -X GET "http://localhost:8000/api/reports/dashboard"

Response:
{
  "today": {
    "date": "2025-12-05",
    "trades_opened": 5,
    "trades_closed": 3,
    "winning_trades": 2,
    "losing_trades": 1,
    "daily_pnl": 2500,
    "daily_return_percent": 2.5,
    "trades": [...]
  },
  "week": {
    "total_trades": 28,
    "win_rate": 0.57,
    "weekly_pnl": 12000,
    "weekly_return": 12.0,
    "best_trade": 5000,
    "worst_trade": -2000
  },
  "month": {
    "total_trades": 120,
    "win_rate": 0.54,
    "monthly_pnl": 45000,
    "monthly_return": 45.0,
    "profit_factor": 1.7,
    "sharpe_ratio": 1.4
  },
  "portfolio": {
    "total_value": 145000,
    "peak_value": 150000,
    "drawdown_percent": -3.3,
    "active_positions": 5,
    "cash": 50000,
    "invested": 95000
  },
  "by_strategy": [
    {"name": "trend_following", "trades": 50, "pnl": 30000, "win_rate": 0.60},
    {"name": "breakout", "trades": 40, "pnl": 12000, "win_rate": 0.50},
    {"name": "elliott_wave", "trades": 30, "pnl": 3000, "win_rate": 0.47}
  ],
  "alerts": [
    {"severity": "INFO", "message": "3 trades closed with profit", "timestamp": "..."},
    {"severity": "WARNING", "message": "Drawdown reached -3.3%, watch correlation", "timestamp": "..."}
  ],
  "chart_data": {
    "equity_curve": [{timestamp: "...", value: 100000}, ...],
    "daily_returns": [{date: "2025-12-05", return: 2.5}, ...],
    "drawdown_chart": [{timestamp: "...", drawdown: -3.3}, ...]
  }
}
```

### 4. RISK EVENTS ENDPOINTS

#### GET /api/reports/risk-events
**Get all risk events**
```bash
curl -X GET "http://localhost:8000/api/reports/risk-events?severity=WARNING&days=7"

Response:
{
  "total": 15,
  "events": [
    {
      "id": "event_123",
      "timestamp": "2025-12-05T14:30:00Z",
      "event_type": "DRAWDOWN_WARNING",
      "severity": "WARNING",
      "value": -18.5,
      "threshold": -20.0,
      "metric_name": "drawdown",
      "action_taken": "Reduced position sizes by 50%",
      "action_successful": true,
      "affected_trades": ["trade_1", "trade_2", "trade_3"]
    }
  ]
}
```

### 5. EXPORT ENDPOINTS

#### GET /api/reports/export/csv
**Export trades to CSV**
```bash
curl -X GET "http://localhost:8000/api/reports/export/csv?bot_id=bot_123&days=30" \
  -H "Accept: text/csv" \
  > trades_2025_12.csv

# CSV Format:
# trade_id,symbol,entry_time,entry_price,exit_time,exit_price,pnl,pnl_percent,duration_hours,status
# trade_123,BTC/USD,2025-12-05 10:30,50000,2025-12-05 14:30,51000,1000,2.0,4.0,CLOSED
# ...
```

#### GET /api/reports/export/excel
**Export to Excel with multiple sheets**
```bash
curl -X GET "http://localhost:8000/api/reports/export/excel?bot_id=bot_123&days=30" \
  -H "Accept: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" \
  > trades_2025_12.xlsx

# Sheets:
# - Summary (overview, metrics)
# - Trades (detailed table)
# - Performance (by strategy)
# - Risk Events (events timeline)
# - Charts (embedded)
```

#### GET /api/reports/export/pdf
**Export to PDF report**
```bash
curl -X GET "http://localhost:8000/api/reports/export/pdf?bot_id=bot_123&days=30" \
  -H "Accept: application/pdf" \
  > trading_report_2025_12.pdf

# PDF Sections:
# 1. Executive Summary
# 2. Performance Metrics (charts)
# 3. Trade Analysis
# 4. Risk Management
# 5. Strategy Comparison
# 6. Detailed Trade Log
```

### 6. REAL-TIME STREAMING

#### WebSocket: /ws/reports/live

```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8000/ws/reports/live?bot_id=bot_123');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'TRADE_OPENED') {
    console.log('New trade:', data.trade);
    // Update UI
  }
  
  if (data.type === 'TRADE_CLOSED') {
    console.log('Trade closed:', data.trade);
    // Update UI
  }
  
  if (data.type === 'METRICS_UPDATE') {
    console.log('Portfolio update:', data.metrics);
    // Update dashboard
  }
  
  if (data.type === 'PRICE_UPDATE') {
    console.log('Price update:', data.prices);
    // Update live prices
  }
};

// Messages sent (every 5 seconds or on event):
{
  "type": "METRICS_UPDATE",
  "timestamp": "2025-12-05T14:30:00Z",
  "metrics": {
    "account_balance": 145000,
    "daily_pnl": 2500,
    "open_positions": 5,
    "active_drawdown": -3.3
  }
}

{
  "type": "TRADE_OPENED",
  "trade": {
    "id": "trade_123",
    "symbol": "BTC/USD",
    "entry_price": 50000,
    "position_size": 1.0
  }
}

{
  "type": "TRADE_CLOSED",
  "trade": {
    "id": "trade_123",
    "exit_price": 51000,
    "pnl": 1000,
    "pnl_percent": 2.0
  }
}
```

---

## 🎨 FRONTEND COMPONENTS

### Layout Structure
```jsx
// pages/ReportsDashboard.jsx
export default function ReportsDashboard() {
  return (
    <div className="reports-dashboard">
      {/* Header with filters */}
      <ReportsHeader />
      
      {/* Summary cards */}
      <SummaryCards />
      
      {/* Main tabs */}
      <ReportsTabs>
        <Tab label="Dashboard" value="dashboard">
          <DashboardTab />
        </Tab>
        <Tab label="Trades" value="trades">
          <TradesTab />
        </Tab>
        <Tab label="Strategies" value="strategies">
          <StrategiesTab />
        </Tab>
        <Tab label="Performance" value="performance">
          <PerformanceTab />
        </Tab>
        <Tab label="Risk" value="risk">
          <RiskTab />
        </Tab>
        <Tab label="Export" value="export">
          <ExportTab />
        </Tab>
      </ReportsTabs>
    </div>
  );
}
```

### 1. Dashboard Tab
```jsx
function DashboardTab() {
  return (
    <div className="dashboard-tab">
      <Grid cols={4}>
        <Card title="Today's PnL" value="$2,500" change="+2.5%" />
        <Card title="Win Rate" value="58%" change="↑ from 54%" />
        <Card title="Active Positions" value="5" change="-2 vs yesterday" />
        <Card title="Drawdown" value="-3.3%" status="warning" />
      </Grid>
      
      <Grid cols={2}>
        <Chart title="Equity Curve" type="line" data={equityData} />
        <Chart title="Daily Returns" type="bar" data={dailyReturns} />
      </Grid>
      
      <Grid cols={2}>
        <Chart title="Drawdown Over Time" type="area" data={drawdownData} />
        <Chart title="Win/Loss Distribution" type="pie" data={winLossData} />
      </Grid>
      
      <RecentTrades limit={5} />
    </div>
  );
}
```

### 2. Trades Tab
```jsx
function TradesTab() {
  const [filters, setFilters] = useState({
    status: 'ALL',
    strategy: '',
    symbol: '',
    days: 30
  });
  
  const { trades, loading } = useFetchTrades(filters);
  
  return (
    <div className="trades-tab">
      <TradesFilters value={filters} onChange={setFilters} />
      
      <TradesTable 
        columns={[
          'Symbol',
          'Entry Time',
          'Entry Price',
          'Exit Price',
          'PnL',
          'PnL %',
          'Duration',
          'Status',
          'Strategy'
        ]}
        rows={trades}
        onRowClick={(trade) => showTradeDetail(trade)}
        loading={loading}
      />
    </div>
  );
}

// Detail modal
function TradeDetailModal({ trade, onClose }) {
  return (
    <Modal onClose={onClose}>
      <div className="trade-detail">
        <h2>{trade.symbol}</h2>
        
        <Grid cols={2}>
          <Section>
            <h3>Entry</h3>
            <p>Time: {formatTime(trade.entry_time)}</p>
            <p>Price: ${formatPrice(trade.entry_price)}</p>
            <p>Signal: {trade.entry_signal}</p>
            <p>Position: {trade.position_size} {trade.symbol.split('/')[0]}</p>
          </Section>
          
          <Section>
            <h3>Exit</h3>
            <p>Time: {formatTime(trade.exit_time)}</p>
            <p>Price: ${formatPrice(trade.exit_price)}</p>
            <p>Reason: {trade.exit_reason}</p>
            <p>P&L: ${trade.pnl} ({trade.pnl_percent}%)</p>
          </Section>
        </Grid>
        
        <Section>
          <h3>Trade Timeline</h3>
          <Timeline events={trade.events} />
        </Section>
        
        <Section>
          <h3>Metrics</h3>
          <Grid cols={3}>
            <Metric label="Duration" value={`${trade.duration_hours}h`} />
            <Metric label="Slippage" value={`${trade.slippage}%`} />
            <Metric label="Win/Loss" value={trade.win_loss} />
          </Grid>
        </Section>
      </div>
    </Modal>
  );
}
```

### 3. Strategies Tab
```jsx
function StrategiesTab() {
  const { strategies } = useFetchStrategies();
  
  return (
    <div className="strategies-tab">
      <Grid cols={1}>
        <h2>Strategy Performance Comparison</h2>
      </Grid>
      
      <StrategyComparisonTable
        strategies={strategies}
        metrics={[
          'total_trades',
          'win_rate',
          'profit_factor',
          'sharpe_ratio',
          'total_pnl',
          'max_drawdown'
        ]}
      />
      
      <Grid cols={2}>
        <Chart 
          title="Win Rate by Strategy" 
          type="bar" 
          data={strategies.map(s => ({name: s.name, value: s.win_rate}))}
        />
        <Chart 
          title="Total PnL by Strategy" 
          type="bar" 
          data={strategies.map(s => ({name: s.name, value: s.total_pnl}))}
        />
      </Grid>
      
      <Accordion>
        {strategies.map(strategy => (
          <AccordionItem key={strategy.name} title={strategy.name}>
            <StrategyDetails strategy={strategy} />
          </AccordionItem>
        ))}
      </Accordion>
    </div>
  );
}
```

### 4. Performance Tab
```jsx
function PerformanceTab() {
  return (
    <div className="performance-tab">
      <Grid cols={1}>
        <h2>Advanced Performance Analysis</h2>
      </Grid>
      
      <Grid cols={2}>
        <Chart title="Monthly Returns" type="bar" />
        <Chart title="Profit Factor Trend" type="line" />
      </Grid>
      
      <Grid cols={2}>
        <Chart title="Win Rate Trend" type="line" />
        <Chart title="Drawdown Evolution" type="area" />
      </Grid>
      
      <Grid cols={3}>
        <Chart title="Return by Hour of Day" type="heatmap" />
        <Chart title="Return by Day of Week" type="bar" />
        <Chart title="Return by Month" type="bar" />
      </Grid>
    </div>
  );
}
```

### 5. Risk Tab
```jsx
function RiskTab() {
  const { riskEvents } = useFetchRiskEvents();
  
  return (
    <div className="risk-tab">
      <Grid cols={4}>
        <Card title="Warnings" value={countBySeverity('WARNING')} status="warning" />
        <Card title="Critical" value={countBySeverity('CRITICAL')} status="critical" />
        <Card title="Current Drawdown" value="-3.3%" />
        <Card title="Daily Loss" value="-$500" />
      </Grid>
      
      <RiskEventsList events={riskEvents} />
      
      <Grid cols={2}>
        <Chart title="Risk Events Timeline" type="timeline" />
        <Chart title="Event Types Distribution" type="pie" />
      </Grid>
    </div>
  );
}
```

### 6. Export Tab
```jsx
function ExportTab() {
  const [exportFormat, setExportFormat] = useState('csv');
  
  return (
    <div className="export-tab">
      <h2>Export Reports</h2>
      
      <Grid cols={2}>
        <Card>
          <h3>Export Format</h3>
          <Radio 
            options={[
              {value: 'csv', label: 'CSV (Excel)'},
              {value: 'excel', label: 'Excel (.xlsx)'},
              {value: 'pdf', label: 'PDF Report'}
            ]}
            value={exportFormat}
            onChange={setExportFormat}
          />
        </Card>
        
        <Card>
          <h3>Options</h3>
          <Checkbox label="Include Charts" defaultChecked />
          <Checkbox label="Include Risk Analysis" defaultChecked />
          <Checkbox label="Include Trade Details" defaultChecked />
        </Card>
      </Grid>
      
      <Button onClick={handleExport} className="primary large">
        Download {exportFormat.toUpperCase()}
      </Button>
    </div>
  );
}
```

---

## 📈 REPORT TYPES

### 1. Daily Trade Summary
- Open trades
- Closed trades (with P&L)
- Win/Loss count
- Daily P&L & return

### 2. Weekly Performance
- Total trades
- Win rate
- Best & worst trade
- Weekly P&L

### 3. Monthly Statement
- Complete trade log
- Performance by strategy
- Risk metrics
- Comparison to previous months

### 4. Strategy Analysis
- Win rate by symbol
- Win rate by timeframe
- Hourly performance
- Seasonal patterns

### 5. Risk Report
- Drawdown history
- Daily loss events
- Position size violations
- API errors & recovery

### 6. Comparison Report
- Strategy vs Strategy
- This month vs Previous months
- Expected vs Actual performance

---

## 📤 EXPORT FORMATS

### CSV Export
Simple, lightweight, opens in Excel

### Excel Export
Multiple sheets, charts, formatting

### PDF Report
Professional, printer-friendly, emails

---

## ⚡ REAL-TIME STREAMING

Via WebSocket for live updates:
- New trades opened
- Trades closed
- Price updates
- Portfolio metrics
- Risk alerts

---

## 🔧 ANALYTICS PIPELINE

```
Raw Trade Data (PostgreSQL)
    ↓
Aggregation Service (Every 5 min)
    ├── Calculate metrics
    ├── Update strategy_performance
    ├── Update bot_metrics
    └── Detect risk events
    ↓
Redis Cache
    ├── Latest metrics
    ├── Charts data
    └── Dashboard summary
    ↓
Frontend (Real-time via WebSocket)
```

---

## ⚡ PERFORMANCE OPTIMIZATION

### Indexes for Fast Queries
```sql
CREATE INDEX ON trades(bot_id, created_at DESC);
CREATE INDEX ON trades(strategy_name, created_at DESC);
CREATE INDEX ON strategy_performance(strategy_name, period_start DESC);
CREATE INDEX ON bot_metrics(bot_id, timestamp DESC);
```

### Caching Strategy
```
Redis Cache TTL:
- Dashboard: 30 seconds
- Trade list: 1 minute
- Strategy stats: 5 minutes
- Charts: 5 minutes
```

### Query Optimization
- Use materialized views for complex aggregations
- Compress old data (> 1 year) to hourly intervals
- Archive trades older than 7 years to cold storage

---

**Last Updated** : 2025-12-05  
**Version** : 1.0

**Next Steps** :
- [ ] Implement database schema
- [ ] Create API endpoints
- [ ] Build frontend components
- [ ] Setup real-time WebSocket
- [ ] Create export functionality
- [ ] Test with sample data

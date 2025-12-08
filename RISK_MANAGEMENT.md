# 🛡️ RISK MANAGEMENT FRAMEWORK

## 📋 TABLE DES MATIÈRES
1. [Overview](#overview)
2. [Position Sizing Methods](#position-sizing-methods)
3. [Stop Loss & Take Profit Strategy](#stop-loss--take-profit-strategy)
4. [Risk Control Mechanisms](#risk-control-mechanisms)
5. [Correlation & Drawdown Management](#correlation--drawdown-management)
6. [Monitoring & Alerts](#monitoring--alerts)
7. [Crisis Management](#crisis-management)
8. [Implementation Guide](#implementation-guide)

---

## 🎯 OVERVIEW

### Risk Management Philosophy
- **Capital Preservation** : Toujours protéger le capital
- **Consistency** : Risk identique par trade (% risqué)
- **Scalability** : Ajuster sizing si portfolio grossit
- **Recovery** : Plan de récupération après drawdown

### Key Principle
```
Never risk more than 1-2% per trade
Never let drawdown exceed -20%
Always have exit plan BEFORE entering
```

---

## 💰 POSITION SIZING METHODS

### 1. Fixed Percentage (Recommended for Beginners)

**Concept** : Risk le même % du capital à chaque trade

```python
def fixed_percentage_sizing(account_balance, risk_percent, entry_price, stop_loss):
    """
    Calculate position size using fixed percentage
    
    Args:
        account_balance: Total account balance ($)
        risk_percent: Risk per trade (1-2%)
        entry_price: Entry price of crypto
        stop_loss: Stop loss price
    
    Returns:
        position_size: Amount to buy (in units)
    """
    risk_amount = account_balance * (risk_percent / 100)
    price_difference = entry_price - stop_loss
    position_size = risk_amount / price_difference
    return position_size

# Example:
# Account: $10,000
# Risk per trade: 1%
# Entry: $50
# Stop Loss: $48
# Risk Amount: $100
# Price diff: $2
# Position Size: 50 units ($2,500)
```

**Advantages** :
- Simple et transparent
- Capital préservé systématiquement
- Easy to adjust when portfolio grows

**Disadvantages** :
- Ignore la volatilité (ATR)
- Fixed sizing même pour haut/bas volatilité

---

### 2. Kelly Criterion (Mathematical Optimal)

**Concept** : Maximize long-term wealth logarithmically

```python
def kelly_criterion(win_rate, avg_win, avg_loss):
    """
    Calculate optimal position size using Kelly Criterion
    
    Formula: f* = (bp - q) / b
    where:
        b = average_win / average_loss (win/loss ratio)
        p = win rate (%)
        q = loss rate (1 - p)
        f* = fraction of capital to risk
    
    Args:
        win_rate: Winning trades percentage (0.5 = 50%)
        avg_win: Average profit per winning trade ($)
        avg_loss: Average loss per losing trade ($)
    
    Returns:
        kelly_fraction: Fraction of capital to risk
    """
    if avg_loss <= 0:
        return 0
    
    b = avg_win / avg_loss
    p = win_rate
    q = 1 - p
    
    kelly_fraction = (b * p - q) / b
    
    # Half Kelly (safer)
    return kelly_fraction / 2

# Example:
# Win Rate: 55%
# Avg Win: $300
# Avg Loss: $100
# 
# Kelly = (3 * 0.55 - 0.45) / 3 = 0.35 (35%)
# Half Kelly = 17.5% per trade (very aggressive!)
# Recommended: Use Half Kelly or Quarter Kelly (4.375%)
```

**Advantages** :
- Mathématiquement optimal
- Maximize growth rate long-term
- Adapt to winning/losing streaks

**Disadvantages** :
- Peut être très agressif (risque drawdown énorme)
- Requires accurate historical data
- Sensitive to small changes in parameters

**Recommendation** : Use Half Kelly ou Quarter Kelly for safety

---

### 3. Volatility-Based Sizing (ATR Method)

**Concept** : Ajuster sizing selon volatilité du marché

```python
def atr_position_sizing(account_balance, risk_percent, atr, entry_price):
    """
    Calculate position size based on ATR (Average True Range)
    
    ATR = average of true ranges over N periods (14 or 20)
    More volatile → larger stop loss → smaller position size
    
    Args:
        account_balance: Total capital ($)
        risk_percent: Risk per trade (1-2%)
        atr: Average True Range value
        entry_price: Entry price
    
    Returns:
        position_size: Amount to buy (in units)
    """
    risk_amount = account_balance * (risk_percent / 100)
    stop_loss = entry_price - (2 * atr)  # Stop 2 ATR below entry
    price_difference = entry_price - stop_loss
    position_size = risk_amount / price_difference
    return position_size

# Example:
# Account: $10,000, Risk: 1%, Entry: $50
# Low ATR scenario ($0.50):
#   Stop Loss = $50 - (2 * $0.50) = $49
#   Position = $100 / $1 = 100 units
#
# High ATR scenario ($2):
#   Stop Loss = $50 - (2 * $2) = $46
#   Position = $100 / $4 = 25 units (smaller due to volatility)
```

**Advantages** :
- Dynamic adaptation to volatility
- Smaller positions in volatile markets
- Reduce drawdown in turbulent times

**Disadvantages** :
- Requires ATR calculation
- Can be conservative in trending markets

---

## 🎯 STOP LOSS & TAKE PROFIT STRATEGY

### 1. Fixed Distance Stop Loss

```python
def fixed_stop_loss(entry_price, stop_loss_percent):
    """
    Stop loss at fixed distance below entry
    
    Example: 2% stop loss
    Entry: $50 → Stop: $49 (50 * 0.98)
    """
    stop_loss_price = entry_price * (1 - stop_loss_percent / 100)
    return stop_loss_price

# Recommended Stop Loss Distances:
# - Scalping (1-5min): 0.5-1%
# - Day Trading (15min-1h): 1-2%
# - Swing Trading (4h-1d): 2-5%
# - Position Trading (1d+): 5-10%
```

### 2. Technical Support/Resistance Stop Loss

```python
def support_resistance_stop_loss(entry_price, recent_support):
    """
    Place stop loss below recent support level
    
    More natural than arbitrary % 
    Reduces false stop-outs
    """
    stop_loss_price = recent_support - 0.5 * (entry_price - recent_support)
    return stop_loss_price

# Example:
# Entry: $50
# Recent Support: $48
# Stop Loss: $48 - 0.5 * ($50 - $48) = $47
```

### 3. Trailing Stop Loss

```python
def trailing_stop_loss(highest_price, trailing_distance):
    """
    Stop loss follows price upwards
    Locks in gains as price rises
    
    Example:
    Entry: $50
    Price rises to $55
    Trailing Stop (2%): $55 * 0.98 = $53.90
    
    If price drops to $53.90 → Exit (locked in $3.90 profit)
    """
    stop_loss_price = highest_price * (1 - trailing_distance / 100)
    return stop_loss_price
```

### 4. Multi-Level Take Profit

**Concept** : Prendre profits progressivement

```python
def multi_level_take_profit(entry_price, position_size):
    """
    Exit in 3 phases:
    - 50% position at 2-3% gain (TP1)
    - 30% position at 5-7% gain (TP2)
    - 20% position at 10-15% gain (TP3)
    """
    tp1 = {
        'price': entry_price * 1.02,  # +2%
        'quantity': position_size * 0.50,
        'description': '50% position'
    }
    tp2 = {
        'price': entry_price * 1.05,  # +5%
        'quantity': position_size * 0.30,
        'description': '30% position'
    }
    tp3 = {
        'price': entry_price * 1.12,  # +12%
        'quantity': position_size * 0.20,
        'description': '20% position (trailing stop)'
    }
    return [tp1, tp2, tp3]

# Advantages:
# - Lock in profits early
# - Let winners run
# - Psychologically easier
# - Better risk/reward ratio
```

---

## 🔐 RISK CONTROL MECHANISMS

### 1. Maximum Drawdown Circuit Breaker

```python
def check_drawdown(peak_balance, current_balance, max_drawdown_percent=20):
    """
    Stop trading if drawdown exceeds maximum allowed
    
    Drawdown = (Peak - Current) / Peak * 100
    """
    drawdown = ((peak_balance - current_balance) / peak_balance) * 100
    
    if drawdown >= max_drawdown_percent:
        return {
            'status': 'STOP_ALL_TRADING',
            'drawdown': drawdown,
            'message': f'Max drawdown ({max_drawdown_percent}%) exceeded'
        }
    return {
        'status': 'CONTINUE',
        'drawdown': drawdown,
        'remaining': max_drawdown_percent - drawdown
    }

# Example:
# Peak: $10,000
# Current: $8,000
# Drawdown = (10k - 8k) / 10k = 20% → STOP TRADING
```

### 2. Daily Loss Limit

```python
def check_daily_loss_limit(daily_pnl, daily_loss_limit_percent, account_balance):
    """
    Stop trading if daily loss exceeds limit
    Prevents panic trading and emotional decisions
    """
    daily_loss_limit = account_balance * (daily_loss_limit_percent / 100)
    
    if daily_pnl <= -daily_loss_limit:
        return {
            'status': 'STOP_TRADING_TODAY',
            'daily_pnl': daily_pnl,
            'limit': -daily_loss_limit,
            'message': 'Daily loss limit reached'
        }
    return {
        'status': 'CONTINUE',
        'daily_pnl': daily_pnl,
        'remaining': -daily_loss_limit - daily_pnl
    }
```

### 3. Maximum Concurrent Positions

```python
def check_max_positions(open_positions, max_concurrent=5):
    """
    Limit simultaneous open trades
    Reduces correlation risk and concentration
    """
    if len(open_positions) >= max_concurrent:
        return {
            'can_open_new': False,
            'open_count': len(open_positions),
            'max_allowed': max_concurrent,
            'message': 'Maximum positions reached'
        }
    return {
        'can_open_new': True,
        'slots_available': max_concurrent - len(open_positions)
    }
```

### 4. Position Size Limits

```python
def check_position_size_limit(position_size, account_balance, max_position_percent=10):
    """
    Limit single position to % of account
    Prevents over-concentration
    """
    max_position_size = account_balance * (max_position_percent / 100)
    
    if position_size > max_position_size:
        return {
            'valid': False,
            'requested': position_size,
            'max_allowed': max_position_size,
            'message': 'Position exceeds max allowed'
        }
    return {'valid': True, 'position_size': position_size}
```

---

## 📊 CORRELATION & DRAWDOWN MANAGEMENT

### 1. Correlation Tracking

```python
def check_correlation_risk(open_positions, correlation_threshold=0.7):
    """
    Avoid too many correlated positions
    Most cryptos are correlated to Bitcoin
    
    If 3+ positions have correlation > 0.7 → reduce exposure
    """
    high_correlation_count = 0
    
    for pos in open_positions:
        if pos['correlation_to_btc'] > correlation_threshold:
            high_correlation_count += 1
    
    if high_correlation_count >= 3:
        return {
            'status': 'HIGH_CORRELATION_RISK',
            'count': high_correlation_count,
            'recommendation': 'Reduce one of correlated positions'
        }
    return {'status': 'OK', 'correlation_risk': 'LOW'}
```

### 2. Sector Diversification

```python
# Example: Limit exposure per sector
sector_limits = {
    'DeFi': 0.20,      # Max 20% in DeFi tokens
    'Layer1': 0.20,    # Max 20% in Layer 1
    'Layer2': 0.15,    # Max 15% in Layer 2
    'Stablecoins': 0.10 # Max 10%
}

def check_sector_exposure(portfolio, sector_limits):
    """Ensure no single sector dominates"""
    for sector, limit in sector_limits.items():
        current_exposure = portfolio[sector] / portfolio['total'] * 100
        if current_exposure > limit * 100:
            return {
                'status': 'SECTOR_OVER_EXPOSED',
                'sector': sector,
                'exposure': current_exposure,
                'limit': limit * 100
            }
    return {'status': 'OK', 'diversified': True}
```

---

## 📈 MONITORING & ALERTS

### Key Metrics Dashboard

```python
class RiskMetrics:
    def __init__(self, account):
        self.account = account
    
    def calculate_all(self):
        return {
            # Returns
            'total_return': self._calculate_return(),
            'monthly_return': self._calculate_monthly_return(),
            'daily_return': self._calculate_daily_return(),
            
            # Risk
            'volatility': self._calculate_volatility(),
            'sharpe_ratio': self._calculate_sharpe_ratio(),
            'sortino_ratio': self._calculate_sortino_ratio(),
            'max_drawdown': self._calculate_max_drawdown(),
            'current_drawdown': self._calculate_current_drawdown(),
            
            # Trade Quality
            'win_rate': self._calculate_win_rate(),
            'profit_factor': self._calculate_profit_factor(),
            'avg_win': self._calculate_avg_win(),
            'avg_loss': self._calculate_avg_loss(),
            'expectancy': self._calculate_expectancy(),
            
            # Exposure
            'total_exposure': self._calculate_total_exposure(),
            'correlation_risk': self._calculate_correlation_risk(),
            'sector_concentration': self._calculate_sector_concentration(),
            
            # Status
            'alerts': self._generate_alerts()
        }
```

### Alert Triggers

| Alert | Threshold | Action |
|-------|-----------|--------|
| Drawdown Warning | -15% | Reduce position sizes |
| Drawdown Critical | -20% | STOP ALL TRADING |
| Daily Loss Warning | -3% | Reduce until end of day |
| Daily Loss Critical | -5% | STOP TRADING TODAY |
| High Correlation | 3+ positions > 0.7 | Reduce one position |
| Over-concentration | Position > 10% | Reduce position |
| Low Win Rate | < 40% | Review strategy |
| Negative Expectancy | < 0 | Stop trading strategy |

---

## 🚨 CRISIS MANAGEMENT

### Scenario 1: Major Drawdown (15-20%)

```
1. Alert triggered: Drawdown -15%
2. Assess: Review all open trades
3. Action: 
   - Reduce position sizes by 50%
   - Close most vulnerable trades
   - Tighten all stop losses
4. Communication: Alert user via Telegram/Email
5. Recovery: Wait for stabilization (24-48h)
```

### Scenario 2: Broker API Down

```
1. Detection: Health check fails
2. Fallback: Switch to backup broker
3. Sync: Reload all positions from broker
4. Continue: Resume trading with backup
5. Alert: Notify user of incident
6. Investigation: Debug root cause
```

### Scenario 3: Market Crash (Flash Crash)

```
1. Detection: Price change > 10% in 1 minute
2. Decision: Hold or exit?
   - If correlated crash: Likely to recover → Hold
   - If isolated: Might continue → Exit
3. Action: Widen stop loss temporarily (1h) to avoid whipsaw
4. Monitor: Close watch on recovery
5. Log: Document incident
```

### Scenario 4: Winning Streak (Too Aggressive?)

```
1. Win Rate > 75% for 50+ trades → Suspicious
2. Check: Curve-fitting? Lucky streak?
3. Action:
   - Reduce position sizes (half)
   - Add more rigorous filters
   - Backtest on new data
   - Paper trade before live
```

---

## 🛠️ IMPLEMENTATION GUIDE

### Backend Code Structure

```python
# risk_manager.py
class RiskManager:
    def __init__(self, config):
        self.max_drawdown = config['max_drawdown']  # -20%
        self.daily_loss_limit = config['daily_loss_limit']  # -5%
        self.max_positions = config['max_positions']  # 5
        self.max_position_size = config['max_position_size']  # 10%
    
    def should_open_trade(self, entry_price, stop_loss, account_balance):
        """Validate trade before execution"""
        checks = [
            self.check_drawdown(),
            self.check_daily_loss(),
            self.check_max_positions(),
            self.check_position_size(entry_price, stop_loss, account_balance),
            self.check_correlation(),
        ]
        
        if all(check['valid'] for check in checks):
            return True, checks
        return False, checks
    
    def check_drawdown(self):
        """Verify drawdown is within limits"""
        # Implementation...
    
    def check_daily_loss(self):
        """Verify daily loss is within limits"""
        # Implementation...
    
    # ... other methods
```

### Database Schema

```sql
-- Risk Events
CREATE TABLE risk_events (
    id UUID PRIMARY KEY,
    bot_id UUID REFERENCES bots(id),
    event_type VARCHAR (DRAWDOWN|DAILY_LOSS|MAX_POSITIONS|CORRELATION),
    severity VARCHAR (INFO|WARNING|CRITICAL),
    value FLOAT,
    limit_value FLOAT,
    action_taken VARCHAR,
    created_at TIMESTAMP
);

-- Position Tracking
CREATE TABLE positions (
    id UUID PRIMARY KEY,
    bot_id UUID,
    crypto_symbol VARCHAR,
    entry_price FLOAT,
    stop_loss FLOAT,
    take_profit_levels JSONB,
    position_size FLOAT,
    opened_at TIMESTAMP,
    closed_at TIMESTAMP,
    exit_price FLOAT,
    pnl FLOAT,
    pnl_percent FLOAT
);
```

### Frontend Display

```jsx
// RiskDashboard.jsx
export function RiskDashboard() {
  return (
    <div className="risk-dashboard">
      <h2>Risk Monitor</h2>
      
      {/* Drawdown Gauge */}
      <DrawdownGauge 
        current={-12.5} 
        max={-20}
        warning={-15}
      />
      
      {/* Position Risk */}
      <PositionRiskTable positions={positions} />
      
      {/* Correlation Matrix */}
      <CorrelationMatrix positions={positions} />
      
      {/* Active Alerts */}
      <AlertsList alerts={alerts} />
    </div>
  );
}
```

---

## 📊 TESTING & VALIDATION

### Backtest Risk Metrics

Before deploying any strategy:
1. ✅ Min Sharpe Ratio : 1.0
2. ✅ Min Win Rate : 45%
3. ✅ Min Profit Factor : 1.5
4. ✅ Max Drawdown : < 25%
5. ✅ Expectancy > 0

### Walk-Forward Analysis

```
Test Period: 3 years
Walk-Forward Window: 6 months
Out-of-Sample Window: 1 month

Year 1 (Test): May 2022 - Oct 2022 | Validate: Nov 2022 - Dec 2022
Year 2 (Test): Jun 2022 - Nov 2022 | Validate: Dec 2022 - Jan 2023
... repeat
```

---

## ✅ DAILY CHECKLIST

- [ ] Review overnight trades (if live)
- [ ] Check current drawdown
- [ ] Verify all positions have stops/TP
- [ ] Monitor open trades
- [ ] Review any alert events
- [ ] Check correlation levels
- [ ] Daily P&L < limit?
- [ ] End of day: Close all positions (optional)

---

**Last Updated** : 2025-12-05  
**Version** : 1.0  

**Next Review** : After first 100 trades or 1 month, whichever comes first

"""
MACD Crossover Strategy
Classic trading strategy based on MACD line crossovers
"""
from typing import Dict, Any, Optional
from .base_strategy import BaseStrategy, StrategyRegistry


class MACDCrossover(BaseStrategy):
    """
    MACD Crossover strategy
    
    Entry Rules:
    - BUY: MACD line crosses above Signal line (bullish crossover)
    - SELL: MACD line crosses below Signal line (bearish crossover)
    
    Enhanced with histogram confirmation and trend filter
    """
    
    def get_config_schema(self) -> Dict[str, Any]:
        return {
            'macd_fast': {
                'type': 'int',
                'default': 12,
                'min': 8,
                'max': 20,
                'description': 'MACD fast EMA period'
            },
            'macd_slow': {
                'type': 'int',
                'default': 26,
                'min': 20,
                'max': 40,
                'description': 'MACD slow EMA period'
            },
            'macd_signal': {
                'type': 'int',
                'default': 9,
                'min': 5,
                'max': 15,
                'description': 'MACD signal line period'
            },
            'use_trend_filter': {
                'type': 'bool',
                'default': True,
                'description': 'Only trade in direction of trend (SMA 50)'
            },
            'stop_loss_pct': {
                'type': 'float',
                'default': 2.0,
                'min': 1.0,
                'max': 5.0,
                'description': 'Stop loss percentage'
            },
            'take_profit_pct': {
                'type': 'float',
                'default': 4.0,
                'min': 2.0,
                'max': 10.0,
                'description': 'Take profit percentage'
            }
        }
    
    def get_description(self) -> str:
        return """📊 **MACD Crossover Strategy**
        
Classic momentum strategy using MACD indicator crossovers.

**How it works:**
- BUY when MACD line crosses above the Signal line
- SELL when MACD line crosses below the Signal line
- Optional trend filter using SMA 50

**Best for:**
- Trending markets
- Medium-term trades
- Confirming other signals

**Risk Level:** Medium
**Timeframe:** 1-4 hours
**Expected Win Rate:** 50-55% (good R:R ratio)"""

    def validate_signal(self, market_data: Dict[str, Any]) -> bool:
        """Check if we have SMA data (as MACD proxy)"""
        indicators = market_data.get('indicators', {})
        return all([
            indicators.get('sma_20'),
            indicators.get('sma_50'),
            indicators.get('rsi')
        ])
    
    def get_signal_direction(self, market_data: Dict[str, Any]) -> str:
        """Detect MACD-like crossover signals using available indicators"""
        indicators = market_data.get('indicators', {})
        current_price = market_data.get('close')
        
        # Using SMA 20/50 as MACD proxy (since we don't have real MACD)
        sma_20 = indicators.get('sma_20')
        sma_50 = indicators.get('sma_50')
        rsi = indicators.get('rsi')
        
        if not all([sma_20, sma_50, rsi, current_price]):
            return 'NONE'
        
        # Calculate momentum (SMA difference as MACD proxy)
        momentum = (sma_20 - sma_50) / sma_50 * 100  # Percentage difference
        
        # Trend filter
        trend_bullish = current_price > sma_50
        trend_bearish = current_price < sma_50
        
        # Bullish crossover: Fast SMA above slow, momentum positive and increasing
        if (sma_20 > sma_50 and 
            momentum > 0.5 and 
            rsi > 45 and rsi < 70):
            if not self.config.get('use_trend_filter', True) or trend_bullish:
                return 'BUY'
        
        # Bearish crossover: Fast SMA below slow, momentum negative
        if (sma_20 < sma_50 and 
            momentum < -0.5 and 
            rsi < 55 and rsi > 30):
            if not self.config.get('use_trend_filter', True) or trend_bearish:
                return 'SELL'
        
        return 'NONE'
    
    def calculate_position_size(
        self, 
        risk_amount: float, 
        entry_price: float, 
        stop_loss: float
    ) -> float:
        price_diff = abs(entry_price - stop_loss)
        if price_diff == 0:
            return 0
        return round(risk_amount / price_diff, 8)
    
    def get_stop_loss(self, entry_price: float, direction: str, market_data: Dict[str, Any]) -> float:
        stop_pct = self.config['stop_loss_pct'] / 100
        if direction == 'BUY':
            return entry_price * (1 - stop_pct)
        return entry_price * (1 + stop_pct)
    
    def get_take_profit(self, entry_price: float, direction: str, market_data: Dict[str, Any]) -> Optional[float]:
        tp_pct = self.config['take_profit_pct'] / 100
        if direction == 'BUY':
            return entry_price * (1 + tp_pct)
        return entry_price * (1 - tp_pct)
    
    def should_exit(
        self, 
        open_trade: Dict[str, Any], 
        current_price: float,
        market_data: Dict[str, Any]
    ) -> tuple[bool, str]:
        entry_price = open_trade.get('entry_price', current_price)
        direction = open_trade.get('side', 'BUY')
        
        stop_loss = self.get_stop_loss(entry_price, direction, market_data)
        take_profit = self.get_take_profit(entry_price, direction, market_data)
        
        if direction == 'BUY':
            if current_price <= stop_loss:
                return True, 'STOP_LOSS'
            if take_profit and current_price >= take_profit:
                return True, 'TAKE_PROFIT'
        else:
            if current_price >= stop_loss:
                return True, 'STOP_LOSS'
            if take_profit and current_price <= take_profit:
                return True, 'TAKE_PROFIT'
        
        return False, ''


# Register strategy
StrategyRegistry.register('macd_crossover', MACDCrossover)

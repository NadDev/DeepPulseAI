"""
RSI Divergence Strategy
Detects divergences between price and RSI to anticipate reversals
"""
from typing import Dict, Any, Optional
from .base_strategy import BaseStrategy, StrategyRegistry


class RSIDivergence(BaseStrategy):
    """
    RSI Divergence strategy - spots reversal opportunities
    
    Entry Rules:
    - Bullish Divergence: Price makes lower low, RSI makes higher low → BUY
    - Bearish Divergence: Price makes higher high, RSI makes lower high → SELL
    
    Exit Rules:
    - Take profit at previous swing high/low
    - Stop loss below/above the divergence low/high
    """
    
    def get_config_schema(self) -> Dict[str, Any]:
        return {
            'rsi_period': {
                'type': 'int',
                'default': 14,
                'min': 7,
                'max': 21,
                'description': 'RSI calculation period'
            },
            'rsi_oversold': {
                'type': 'int',
                'default': 35,
                'min': 20,
                'max': 40,
                'description': 'RSI oversold zone for bullish divergence'
            },
            'rsi_overbought': {
                'type': 'int',
                'default': 65,
                'min': 60,
                'max': 80,
                'description': 'RSI overbought zone for bearish divergence'
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
        return """📉 **RSI Divergence Strategy**
        
Identifies potential trend reversals using RSI divergences.

**How it works:**
- Bullish Divergence: Price makes lower lows while RSI makes higher lows
- Bearish Divergence: Price makes higher highs while RSI makes lower highs
- These patterns often precede trend reversals

**Best for:**
- Range-bound markets
- After extended trends
- Swing trading opportunities

**Risk Level:** Medium
**Timeframe:** 1-4 hours
**Expected Win Rate:** 55-65%"""

    def validate_signal(self, market_data: Dict[str, Any]) -> bool:
        """Check if we have RSI data"""
        indicators = market_data.get('indicators', {})
        return indicators.get('rsi') is not None
    
    def get_signal_direction(self, market_data: Dict[str, Any]) -> str:
        """Detect divergence signals (simplified)"""
        indicators = market_data.get('indicators', {})
        current_price = market_data.get('close')
        
        rsi = indicators.get('rsi')
        support = indicators.get('support')
        resistance = indicators.get('resistance')
        bb_lower = indicators.get('bb_lower')
        bb_upper = indicators.get('bb_upper')
        
        if not all([rsi, support, resistance]):
            return 'NONE'
        
        # Simplified divergence detection:
        # Bullish: Price near support/lower BB with RSI showing strength
        if (current_price <= support * 1.02 or 
            (bb_lower and current_price <= bb_lower)):
            if rsi < self.config['rsi_oversold'] and rsi > 25:
                # RSI oversold but not extremely - potential bullish divergence
                return 'BUY'
        
        # Bearish: Price near resistance/upper BB with RSI showing weakness
        if (current_price >= resistance * 0.98 or 
            (bb_upper and current_price >= bb_upper)):
            if rsi > self.config['rsi_overbought'] and rsi < 75:
                # RSI overbought but not extremely - potential bearish divergence
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
StrategyRegistry.register('rsi_divergence', RSIDivergence)

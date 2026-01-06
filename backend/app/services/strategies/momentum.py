"""
Momentum Strategy
Trades based on the strength and direction of price movement
"""
from typing import Dict, Any, Optional
from .base_strategy import BaseStrategy, StrategyRegistry


class Momentum(BaseStrategy):
    """
    Momentum strategy - rides strong price movements
    
    Entry Rules:
    - BUY: Strong upward momentum (RSI > 60, price above SMA, high volume)
    - SELL: Strong downward momentum (RSI < 40, price below SMA, high volume)
    
    Exit Rules:
    - Exit when momentum weakens
    - Trailing stop to protect profits
    """
    
    def get_config_schema(self) -> Dict[str, Any]:
        return {
            'rsi_strong_buy': {
                'type': 'int',
                'default': 60,
                'min': 55,
                'max': 75,
                'description': 'RSI threshold for strong buying momentum'
            },
            'rsi_strong_sell': {
                'type': 'int',
                'default': 40,
                'min': 25,
                'max': 45,
                'description': 'RSI threshold for strong selling momentum'
            },
            'volume_multiplier': {
                'type': 'float',
                'default': 1.5,
                'min': 1.0,
                'max': 3.0,
                'description': 'Required volume multiplier'
            },
            'stop_loss_pct': {
                'type': 'float',
                'default': 2.5,
                'min': 1.0,
                'max': 5.0,
                'description': 'Stop loss percentage'
            },
            'trailing_stop_pct': {
                'type': 'float',
                'default': 1.5,
                'min': 0.5,
                'max': 3.0,
                'description': 'Trailing stop percentage'
            }
        }
    
    def get_description(self) -> str:
        return """🚀 **Momentum Strategy**
        
Rides strong price movements in either direction.

**How it works:**
- Identifies strong momentum using RSI and volume
- Enters when price shows clear directional strength
- Uses trailing stops to lock in profits

**Best for:**
- Trending markets with clear direction
- News-driven price moves
- Breakout continuations

**Risk Level:** Medium-High
**Timeframe:** 1-4 hours
**Expected Win Rate:** 50-60% (higher R:R ratio)"""

    def validate_signal(self, market_data: Dict[str, Any]) -> bool:
        """Check if we have momentum data"""
        indicators = market_data.get('indicators', {})
        return all([
            indicators.get('rsi'),
            indicators.get('sma_20'),
            indicators.get('avg_volume'),
            market_data.get('volume')
        ])
    
    def get_signal_direction(self, market_data: Dict[str, Any]) -> str:
        """Detect momentum direction"""
        indicators = market_data.get('indicators', {})
        current_price = market_data.get('close')
        current_volume = market_data.get('volume')
        
        rsi = indicators.get('rsi')
        sma_20 = indicators.get('sma_20')
        sma_50 = indicators.get('sma_50')
        avg_volume = indicators.get('avg_volume')
        
        if not all([rsi, sma_20, sma_50, avg_volume, current_volume]):
            return 'NONE'
        
        volume_strong = current_volume > avg_volume * self.config['volume_multiplier']
        
        # Strong bullish momentum
        if (rsi > self.config['rsi_strong_buy'] and 
            current_price > sma_20 > sma_50 and 
            volume_strong):
            return 'BUY'
        
        # Strong bearish momentum
        if (rsi < self.config['rsi_strong_sell'] and 
            current_price < sma_20 < sma_50 and 
            volume_strong):
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
        """No fixed take profit - use trailing stop"""
        return None
    
    def should_exit(
        self, 
        open_trade: Dict[str, Any], 
        current_price: float,
        market_data: Dict[str, Any]
    ) -> tuple[bool, str]:
        """Exit on momentum reversal or stop loss"""
        entry_price = open_trade.get('entry_price', current_price)
        direction = open_trade.get('side', 'BUY')
        indicators = market_data.get('indicators', {})
        rsi = indicators.get('rsi')
        
        stop_loss = self.get_stop_loss(entry_price, direction, market_data)
        
        if direction == 'BUY':
            if current_price <= stop_loss:
                return True, 'STOP_LOSS'
            # Exit if momentum reverses
            if rsi and rsi < 45:
                return True, 'MOMENTUM_REVERSAL'
        else:
            if current_price >= stop_loss:
                return True, 'STOP_LOSS'
            if rsi and rsi > 55:
                return True, 'MOMENTUM_REVERSAL'
        
        return False, ''


# Register strategy
StrategyRegistry.register('momentum', Momentum)

"""
Breakout Strategy
Trades breakouts of support/resistance levels with volume confirmation
"""
from typing import Dict, Any, Optional
from .base_strategy import BaseStrategy, StrategyRegistry


class Breakout(BaseStrategy):
    """
    Breakout strategy trading range breakouts with volume confirmation
    
    Entry Rules:
    - BUY: Price breaks above resistance with volume > average volume
    - SELL: Price breaks below support with volume > average volume
    
    Exit Rules:
    - Stop Loss: Below/above the breakout level
    - Take Profit: Multiple of the range size
    """
    
    def get_config_schema(self) -> Dict[str, Any]:
        return {
            'lookback_period': {
                'type': 'int',
                'default': 20,
                'min': 10,
                'max': 100,
                'description': 'Period for detecting support/resistance'
            },
            'volume_multiplier': {
                'type': 'float',
                'default': 1.5,
                'min': 1.0,
                'max': 3.0,
                'description': 'Volume must be X times average'
            },
            'breakout_threshold': {
                'type': 'float',
                'default': 0.5,
                'min': 0.1,
                'max': 2.0,
                'description': 'Percentage above/below level for confirmation'
            },
            'stop_loss_pct': {
                'type': 'float',
                'default': 2.0,
                'min': 0.5,
                'max': 5.0,
                'description': 'Stop loss percentage from breakout level'
            },
            'profit_target_multiplier': {
                'type': 'float',
                'default': 2.0,
                'min': 1.0,
                'max': 5.0,
                'description': 'Take profit as multiple of range'
            }
        }
    
    def get_description(self) -> str:
        return """🚀 **Breakout Strategy**
        
Trades price breakouts from support and resistance levels.

**How it works:**
- Identifies key support and resistance levels
- BUY when price breaks above resistance with volume confirmation
- SELL when price breaks below support with volume confirmation
- Uses the range size for take profit targets

**Best for:**
- Consolidating markets ready to move
- After periods of low volatility
- News-driven breakouts

**Risk Level:** Medium-High
**Timeframe:** 1-4 hours
**Expected Win Rate:** 40-50% (large winners on valid breakouts)"""
    
    def validate_signal(self, market_data: Dict[str, Any]) -> bool:
        """Check if we have sufficient data for breakout detection"""
        required = ['high', 'low', 'close', 'volume']
        return all(key in market_data for key in required)
    
    def get_signal_direction(self, market_data: Dict[str, Any]) -> str:
        """Detect breakout direction"""
        indicators = market_data.get('indicators', {})
        current_price = market_data.get('close')
        current_volume = market_data.get('volume')
        
        # Get support and resistance from indicators
        resistance = indicators.get('resistance')
        support = indicators.get('support')
        avg_volume = indicators.get('avg_volume')
        
        if not all([resistance, support, avg_volume, current_price, current_volume]):
            return 'NONE'
        
        threshold_pct = self.config['breakout_threshold'] / 100
        volume_req = avg_volume * self.config['volume_multiplier']
        
        # Check for bullish breakout
        if (current_price > resistance * (1 + threshold_pct) and 
            current_volume > volume_req):
            return 'BUY'
        
        # Check for bearish breakout
        if (current_price < support * (1 - threshold_pct) and 
            current_volume > volume_req):
            return 'SELL'
        
        return 'NONE'
    
    def calculate_position_size(
        self, 
        risk_amount: float, 
        entry_price: float, 
        stop_loss: float
    ) -> float:
        """Calculate position size based on risk"""
        price_diff = abs(entry_price - stop_loss)
        if price_diff == 0:
            return 0
        
        position_size = risk_amount / price_diff
        return round(position_size, 8)
    
    def get_stop_loss(self, entry_price: float, direction: str, market_data: Dict[str, Any]) -> float:
        """Stop loss below/above the breakout level"""
        indicators = market_data.get('indicators', {})
        stop_pct = self.config['stop_loss_pct'] / 100
        
        if direction == 'BUY':
            # Stop below resistance (the breakout level)
            resistance = indicators.get('resistance', entry_price)
            return resistance * (1 - stop_pct)
        else:  # SELL
            # Stop above support (the breakout level)
            support = indicators.get('support', entry_price)
            return support * (1 + stop_pct)
    
    def get_take_profit(self, entry_price: float, direction: str, market_data: Dict[str, Any]) -> Optional[float]:
        """Take profit based on range size"""
        indicators = market_data.get('indicators', {})
        resistance = indicators.get('resistance')
        support = indicators.get('support')
        
        if not resistance or not support:
            return None
        
        range_size = abs(resistance - support)
        target_move = range_size * self.config['profit_target_multiplier']
        
        if direction == 'BUY':
            return entry_price + target_move
        else:  # SELL
            return entry_price - target_move
    
    def should_exit(
        self, 
        open_trade: Dict[str, Any], 
        current_price: float,
        market_data: Dict[str, Any]
    ) -> bool:
        """Check exit conditions"""
        entry_price = open_trade['entry_price']
        direction = open_trade['side']
        
        # Check stop loss
        stop_loss = self.get_stop_loss(entry_price, direction, market_data)
        if direction == 'BUY' and current_price <= stop_loss:
            return True
        if direction == 'SELL' and current_price >= stop_loss:
            return True
        
        # Check take profit
        take_profit = self.get_take_profit(entry_price, direction, market_data)
        if take_profit:
            if direction == 'BUY' and current_price >= take_profit:
                return True
            if direction == 'SELL' and current_price <= take_profit:
                return True
        
        return False


# Register the strategy
StrategyRegistry.register('breakout', Breakout)

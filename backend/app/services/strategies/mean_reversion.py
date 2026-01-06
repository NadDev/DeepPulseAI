"""
Mean Reversion Strategy
Trades market pullbacks expecting return to mean
"""
from typing import Dict, Any, Optional
from .base_strategy import BaseStrategy, StrategyRegistry


class MeanReversion(BaseStrategy):
    """
    Mean Reversion strategy using Bollinger Bands
    
    Entry Rules:
    - BUY: Price touches lower Bollinger Band AND RSI oversold
    - SELL: Price touches upper Bollinger Band AND RSI overbought
    
    Exit Rules:
    - Take profit at middle band (SMA)
    - Stop loss at X% beyond the band
    """
    
    def get_config_schema(self) -> Dict[str, Any]:
        return {
            'bb_period': {
                'type': 'int',
                'default': 20,
                'min': 10,
                'max': 50,
                'description': 'Bollinger Bands period'
            },
            'bb_std': {
                'type': 'float',
                'default': 2.0,
                'min': 1.0,
                'max': 3.0,
                'description': 'Bollinger Bands standard deviation'
            },
            'rsi_period': {
                'type': 'int',
                'default': 14,
                'min': 5,
                'max': 30,
                'description': 'RSI period'
            },
            'rsi_oversold': {
                'type': 'int',
                'default': 30,
                'min': 10,
                'max': 40,
                'description': 'RSI oversold threshold'
            },
            'rsi_overbought': {
                'type': 'int',
                'default': 70,
                'min': 60,
                'max': 90,
                'description': 'RSI overbought threshold'
            },
            'stop_loss_pct': {
                'type': 'float',
                'default': 3.0,
                'min': 1.0,
                'max': 10.0,
                'description': 'Stop loss percentage beyond band'
            },
            'take_profit_band': {
                'type': 'str',
                'default': 'middle',
                'description': 'Take profit at: middle, upper, lower'
            }
        }
    
    def get_description(self) -> str:
        return """🔄 **Mean Reversion Strategy**
        
Trades pullbacks expecting price to return to the mean.

**How it works:**
- Uses Bollinger Bands to identify overbought/oversold conditions
- BUY when price touches lower band with RSI oversold
- SELL when price touches upper band with RSI overbought
- Takes profit when price returns to the middle band

**Best for:**
- Range-bound markets
- After overextended moves
- Stable, liquid assets

**Risk Level:** Medium
**Timeframe:** 1-4 hours
**Expected Win Rate:** 55-65% (frequent smaller wins)"""
    
    def validate_signal(self, market_data: Dict[str, Any]) -> bool:
        """Check if we have required indicators"""
        indicators = market_data.get('indicators', {})
        required = ['bb_upper', 'bb_middle', 'bb_lower', 'rsi']
        return all(indicators.get(key) is not None for key in required)
    
    def get_signal_direction(self, market_data: Dict[str, Any]) -> str:
        """Detect mean reversion opportunities"""
        indicators = market_data.get('indicators', {})
        current_price = market_data.get('close')
        
        bb_upper = indicators.get('bb_upper')
        bb_middle = indicators.get('bb_middle')
        bb_lower = indicators.get('bb_lower')
        rsi = indicators.get('rsi')
        
        if not all([bb_upper, bb_middle, bb_lower, rsi, current_price]):
            return 'NONE'
        
        # BUY signal: Price at lower band and RSI oversold
        if (current_price <= bb_lower and 
            rsi < self.config['rsi_oversold']):
            return 'BUY'
        
        # SELL signal: Price at upper band and RSI overbought
        if (current_price >= bb_upper and 
            rsi > self.config['rsi_overbought']):
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
        """Stop loss beyond the Bollinger Band"""
        indicators = market_data.get('indicators', {})
        stop_pct = self.config['stop_loss_pct'] / 100
        
        if direction == 'BUY':
            # Stop below lower band
            bb_lower = indicators.get('bb_lower', entry_price)
            return bb_lower * (1 - stop_pct)
        else:  # SELL
            # Stop above upper band
            bb_upper = indicators.get('bb_upper', entry_price)
            return bb_upper * (1 + stop_pct)
    
    def get_take_profit(self, entry_price: float, direction: str, market_data: Dict[str, Any]) -> Optional[float]:
        """Take profit at middle band (mean)"""
        indicators = market_data.get('indicators', {})
        
        target_band = self.config.get('take_profit_band', 'middle')
        
        if target_band == 'middle':
            return indicators.get('bb_middle')
        elif target_band == 'upper' and direction == 'BUY':
            return indicators.get('bb_upper')
        elif target_band == 'lower' and direction == 'SELL':
            return indicators.get('bb_lower')
        
        return indicators.get('bb_middle')
    
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
        
        # Exit if price crosses to opposite band
        indicators = market_data.get('indicators', {})
        if direction == 'BUY':
            bb_upper = indicators.get('bb_upper')
            if bb_upper and current_price >= bb_upper:
                return True
        else:  # SELL
            bb_lower = indicators.get('bb_lower')
            if bb_lower and current_price <= bb_lower:
                return True
        
        return False


# Register the strategy
StrategyRegistry.register('mean_reversion', MeanReversion)

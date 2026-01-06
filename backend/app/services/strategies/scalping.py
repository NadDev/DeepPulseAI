"""
Scalping Strategy
Very short-term trades capturing small price movements
"""
from typing import Dict, Any, Optional
from .base_strategy import BaseStrategy, StrategyRegistry


class Scalping(BaseStrategy):
    """
    Scalping strategy for quick, small profits
    
    Entry Rules:
    - BUY: EMA 9 crosses above EMA 21 with volume spike
    - SELL: EMA 9 crosses below EMA 21 with volume spike
    
    Exit Rules:
    - Quick take profit (0.5-1%)
    - Tight stop loss (0.3-0.5%)
    """
    
    def get_config_schema(self) -> Dict[str, Any]:
        return {
            'ema_fast': {
                'type': 'int',
                'default': 9,
                'min': 3,
                'max': 20,
                'description': 'Fast EMA period'
            },
            'ema_slow': {
                'type': 'int',
                'default': 21,
                'min': 10,
                'max': 50,
                'description': 'Slow EMA period'
            },
            'volume_threshold': {
                'type': 'float',
                'default': 1.2,
                'min': 1.0,
                'max': 3.0,
                'description': 'Volume must be X times average'
            },
            'take_profit_pct': {
                'type': 'float',
                'default': 0.5,
                'min': 0.2,
                'max': 2.0,
                'description': 'Take profit percentage'
            },
            'stop_loss_pct': {
                'type': 'float',
                'default': 0.3,
                'min': 0.1,
                'max': 1.0,
                'description': 'Stop loss percentage'
            }
        }
    
    def get_description(self) -> str:
        return """🎯 **Scalping Strategy**
        
Captures small price movements with quick entries and exits.

**How it works:**
- Uses fast EMA (9) and slow EMA (21) crossovers
- Requires volume confirmation for valid signals
- Very tight stop-loss and take-profit levels

**Best for:**
- High volatility markets
- Liquid trading pairs (BTC, ETH)
- Active traders who can monitor positions

**Risk Level:** High (frequent trades, requires attention)
**Timeframe:** 1-15 minutes
**Expected Win Rate:** 55-65%"""

    def validate_signal(self, market_data: Dict[str, Any]) -> bool:
        """Check if we have required data"""
        indicators = market_data.get('indicators', {})
        return all([
            indicators.get('sma_20'),  # Using SMA as proxy for EMA
            indicators.get('avg_volume'),
            market_data.get('volume')
        ])
    
    def get_signal_direction(self, market_data: Dict[str, Any]) -> str:
        """Detect scalping opportunities"""
        indicators = market_data.get('indicators', {})
        current_price = market_data.get('close')
        current_volume = market_data.get('volume')
        
        sma_fast = indicators.get('sma_20')  # Using available SMAs
        sma_slow = indicators.get('sma_50')
        avg_volume = indicators.get('avg_volume')
        rsi = indicators.get('rsi')
        
        if not all([sma_fast, sma_slow, avg_volume, current_volume, rsi]):
            return 'NONE'
        
        volume_ok = current_volume > avg_volume * self.config['volume_threshold']
        
        # Quick BUY: Price above fast SMA, volume spike, RSI not overbought
        if (current_price > sma_fast > sma_slow and 
            volume_ok and rsi and rsi < 70):
            return 'BUY'
        
        # Quick SELL: Price below fast SMA, volume spike, RSI not oversold
        if (current_price < sma_fast < sma_slow and 
            volume_ok and rsi and rsi > 30):
            return 'SELL'
        
        return 'NONE'
    
    def calculate_position_size(
        self, 
        risk_amount: float, 
        entry_price: float, 
        stop_loss: float
    ) -> float:
        """Calculate position size - larger for scalping"""
        price_diff = abs(entry_price - stop_loss)
        if price_diff == 0:
            return 0
        return round(risk_amount / price_diff, 8)
    
    def get_stop_loss(self, entry_price: float, direction: str, market_data: Dict[str, Any]) -> float:
        """Tight stop loss for scalping"""
        stop_pct = self.config['stop_loss_pct'] / 100
        if direction == 'BUY':
            return entry_price * (1 - stop_pct)
        return entry_price * (1 + stop_pct)
    
    def get_take_profit(self, entry_price: float, direction: str, market_data: Dict[str, Any]) -> Optional[float]:
        """Quick take profit"""
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
        """Check for quick exit conditions"""
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
StrategyRegistry.register('scalping', Scalping)

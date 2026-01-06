"""
DCA (Dollar Cost Averaging) Strategy
Systematic buying to average entry price over time
"""
from typing import Dict, Any, Optional
from .base_strategy import BaseStrategy, StrategyRegistry


class DCA(BaseStrategy):
    """
    DCA Strategy - reduces timing risk through systematic buying
    
    How it works:
    - Buys at regular intervals or on price dips
    - Averages the entry price over time
    - Best for long-term accumulation
    
    Enhanced with smart entry points (buy on dips)
    """
    
    def get_config_schema(self) -> Dict[str, Any]:
        return {
            'dip_threshold_pct': {
                'type': 'float',
                'default': 3.0,
                'min': 1.0,
                'max': 10.0,
                'description': 'Buy when price dips X% below average'
            },
            'rsi_buy_threshold': {
                'type': 'int',
                'default': 40,
                'min': 20,
                'max': 50,
                'description': 'RSI level to trigger buy'
            },
            'max_positions': {
                'type': 'int',
                'default': 10,
                'min': 3,
                'max': 50,
                'description': 'Maximum number of DCA positions'
            },
            'take_profit_pct': {
                'type': 'float',
                'default': 10.0,
                'min': 5.0,
                'max': 50.0,
                'description': 'Take profit on total position (%)'
            },
            'stop_loss_pct': {
                'type': 'float',
                'default': 15.0,
                'min': 5.0,
                'max': 30.0,
                'description': 'Stop loss on total position (%)'
            }
        }
    
    def get_description(self) -> str:
        return """💰 **DCA (Dollar Cost Averaging) Strategy**
        
Systematic buying strategy that reduces timing risk.

**How it works:**
- Buys regularly or when price shows weakness (dips)
- Averages your entry price over multiple purchases
- Smart DCA: buys more when RSI indicates oversold conditions
- Aims for long-term accumulation at good average prices

**Best for:**
- Long-term investors
- Reducing emotional trading
- Building positions in quality assets

**Risk Level:** Low
**Timeframe:** Days to weeks
**Expected Win Rate:** 60-70% (time in market wins)"""

    def validate_signal(self, market_data: Dict[str, Any]) -> bool:
        """DCA works with basic indicators"""
        indicators = market_data.get('indicators', {})
        return indicators.get('rsi') is not None
    
    def get_signal_direction(self, market_data: Dict[str, Any]) -> str:
        """DCA is always looking to buy on dips"""
        indicators = market_data.get('indicators', {})
        current_price = market_data.get('close')
        
        rsi = indicators.get('rsi')
        bb_lower = indicators.get('bb_lower')
        bb_middle = indicators.get('bb_middle')
        sma_50 = indicators.get('sma_50')
        
        if not all([rsi, current_price]):
            return 'NONE'
        
        # Smart DCA: Buy when conditions are favorable
        conditions_met = 0
        
        # Condition 1: RSI shows oversold/weakness
        if rsi < self.config['rsi_buy_threshold']:
            conditions_met += 1
        
        # Condition 2: Price at or below lower Bollinger Band
        if bb_lower and current_price <= bb_lower * 1.01:
            conditions_met += 1
        
        # Condition 3: Price below 50 SMA (buying the dip)
        if sma_50 and current_price < sma_50:
            conditions_met += 1
        
        # Condition 4: Price significantly below middle BB
        if bb_middle and current_price < bb_middle * (1 - self.config['dip_threshold_pct'] / 100):
            conditions_met += 1
        
        # Need at least 2 conditions for BUY signal
        if conditions_met >= 2:
            return 'BUY'
        
        # DCA rarely sells, but exit if extremely overbought
        if rsi and rsi > 80:
            return 'SELL'
        
        return 'NONE'
    
    def calculate_position_size(
        self, 
        risk_amount: float, 
        entry_price: float, 
        stop_loss: float
    ) -> float:
        # DCA uses fixed amount per buy
        max_positions = self.config['max_positions']
        amount_per_buy = risk_amount / max_positions
        return round(amount_per_buy / entry_price, 8)
    
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
        indicators = market_data.get('indicators', {})
        rsi = indicators.get('rsi')
        
        stop_loss = self.get_stop_loss(entry_price, direction, market_data)
        take_profit = self.get_take_profit(entry_price, direction, market_data)
        
        # DCA is patient - primarily exits on take profit
        if direction == 'BUY':
            if current_price <= stop_loss:
                return True, 'STOP_LOSS'
            if take_profit and current_price >= take_profit:
                return True, 'TAKE_PROFIT'
            # Exit if extremely overbought
            if rsi and rsi > 85:
                profit_pct = (current_price - entry_price) / entry_price * 100
                if profit_pct > 5:  # Only if in profit
                    return True, 'OVERBOUGHT_EXIT'
        
        return False, ''


# Register strategy
StrategyRegistry.register('dca', DCA)

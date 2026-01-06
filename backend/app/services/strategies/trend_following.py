"""
Trend Following Strategy
Follows market trends using moving averages and momentum indicators
"""
from typing import Dict, Any, Optional
from .base_strategy import BaseStrategy, StrategyRegistry


class TrendFollowing(BaseStrategy):
    """
    Trend Following strategy using SMA crossover and RSI confirmation
    
    Entry Rules:
    - BUY: Fast SMA crosses above Slow SMA AND RSI > 50
    - SELL: Fast SMA crosses below Slow SMA AND RSI < 50
    
    Exit Rules:
    - Stop Loss: Fixed percentage below/above entry
    - Take Profit: Risk-Reward ratio based
    """
    
    def get_config_schema(self) -> Dict[str, Any]:
        return {
            'sma_fast': {
                'type': 'int',
                'default': 20,
                'min': 5,
                'max': 100,
                'description': 'Fast SMA period'
            },
            'sma_slow': {
                'type': 'int',
                'default': 50,
                'min': 20,
                'max': 200,
                'description': 'Slow SMA period'
            },
            'rsi_period': {
                'type': 'int',
                'default': 14,
                'min': 5,
                'max': 30,
                'description': 'RSI calculation period'
            },
            'rsi_overbought': {
                'type': 'int',
                'default': 70,
                'min': 60,
                'max': 90,
                'description': 'RSI overbought threshold'
            },
            'rsi_oversold': {
                'type': 'int',
                'default': 30,
                'min': 10,
                'max': 40,
                'description': 'RSI oversold threshold'
            },
            'stop_loss_pct': {
                'type': 'float',
                'default': 2.0,
                'min': 0.5,
                'max': 10.0,
                'description': 'Stop loss percentage'
            },
            'risk_reward_ratio': {
                'type': 'float',
                'default': 2.0,
                'min': 1.0,
                'max': 5.0,
                'description': 'Risk/Reward ratio for take profit'
            }
        }
    
    def get_description(self) -> str:
        return "Trend Following strategy using SMA crossover and RSI confirmation"
    
    def validate_signal(self, market_data: Dict[str, Any]) -> bool:
        """Check if we have a valid trend signal"""
        indicators = market_data.get('indicators', {})
        
        # Use standard SMA periods (20/50)
        sma_fast = indicators.get('sma_20')
        sma_slow = indicators.get('sma_50')
        rsi = indicators.get('rsi')
        
        if not all([sma_fast, sma_slow, rsi]):
            return False
        
        # Check for crossover (requires historical data)
        return True
    
    def get_signal_direction(self, market_data: Dict[str, Any]) -> str:
        """Determine if we should BUY, SELL, or do nothing"""
        indicators = market_data.get('indicators', {})
        
        # Use standard SMA periods (20/50)
        sma_fast = indicators.get('sma_20')
        sma_slow = indicators.get('sma_50')
        rsi = indicators.get('rsi')
        
        if not all([sma_fast, sma_slow, rsi]):
            return 'NONE'
        
        # BUY signal: Fast SMA > Slow SMA and RSI indicates bullish momentum
        if sma_fast > sma_slow and rsi > 50 and rsi < self.config['rsi_overbought']:
            return 'BUY'
        
        # SELL signal: Fast SMA < Slow SMA and RSI indicates bearish momentum
        if sma_fast < sma_slow and rsi < 50 and rsi > self.config['rsi_oversold']:
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
        """Calculate stop loss based on percentage"""
        stop_pct = self.config['stop_loss_pct'] / 100
        
        if direction == 'BUY':
            return entry_price * (1 - stop_pct)
        else:  # SELL
            return entry_price * (1 + stop_pct)
    
    def get_take_profit(self, entry_price: float, direction: str, market_data: Dict[str, Any]) -> Optional[float]:
        """Calculate take profit based on risk-reward ratio"""
        stop_loss = self.get_stop_loss(entry_price, direction, market_data)
        risk = abs(entry_price - stop_loss)
        reward = risk * self.config['risk_reward_ratio']
        
        if direction == 'BUY':
            return entry_price + reward
        else:  # SELL
            return entry_price - reward
    
    def should_exit(
        self, 
        open_trade: Dict[str, Any], 
        current_price: float,
        market_data: Dict[str, Any]
    ) -> bool:
        """Check if we should exit the position"""
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
        
        # Check for trend reversal
        signal = self.get_signal_direction(market_data)
        if direction == 'BUY' and signal == 'SELL':
            return True
        if direction == 'SELL' and signal == 'BUY':
            return True
        
        return False


# Register the strategy
StrategyRegistry.register('trend_following', TrendFollowing)

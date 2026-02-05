"""
Grid Trading Strategy
Places buy and sell orders at regular price intervals
"""
import logging
from typing import Dict, Any, Optional
from .base_strategy import BaseStrategy, StrategyRegistry

logger = logging.getLogger(__name__)


class GridTrading(BaseStrategy):
    """
    Grid Trading strategy - profits from market oscillations
    
    How it works:
    - Defines a price range with multiple grid levels
    - BUY when price drops to lower grid levels
    - SELL when price rises to upper grid levels
    
    Best for sideways/ranging markets
    """
    
    def get_config_schema(self) -> Dict[str, Any]:
        return {
            'grid_levels': {
                'type': 'int',
                'default': 5,
                'min': 3,
                'max': 20,
                'description': 'Number of grid levels'
            },
            'grid_spacing_pct': {
                'type': 'float',
                'default': 1.0,
                'min': 0.5,
                'max': 5.0,
                'description': 'Spacing between grid levels (%)'
            },
            'take_profit_pct': {
                'type': 'float',
                'default': 2.5,  # Changed from 1.0 to improve R:R
                'min': 0.5,
                'max': 3.0,
                'description': 'Take profit per grid trade (%)'
            },
            'stop_loss_pct': {
                'type': 'float',
                'default': 2.0,  # Changed from 5.0 to improve R:R
                'min': 2.0,
                'max': 15.0,
                'description': 'Overall stop loss (%)'
            }
        }
    
    def get_description(self) -> str:
        return """📈 **Grid Trading Strategy**
        
Profits from natural market oscillations in ranging markets.

**How it works:**
- Creates a "grid" of price levels above and below current price
- Buys when price drops to lower levels
- Sells when price rises to upper levels
- Profits from the natural up/down movement

**Best for:**
- Sideways/ranging markets
- Stable coins or established cryptos
- Automated trading 24/7

**Risk Level:** Low-Medium (in ranging markets)
**Timeframe:** Continuous
**Expected Win Rate:** 70-80% (many small profits)"""

    def validate_signal(self, market_data: Dict[str, Any]) -> bool:
        """Grid trading works with basic price data"""
        return market_data.get('close') is not None
    
    def get_signal_direction(self, market_data: Dict[str, Any]) -> str:
        """Determine grid trading signal based on price position"""
        indicators = market_data.get('indicators', {})
        current_price = market_data.get('close')
        open_position = market_data.get('open_position')
        
        support = indicators.get('support')
        resistance = indicators.get('resistance')
        bb_lower = indicators.get('bb_lower')
        bb_upper = indicators.get('bb_upper')
        bb_middle = indicators.get('bb_middle')
        
        if not current_price:
            return 'NONE'
        
        # Use Bollinger Bands as dynamic grid
        if all([bb_lower, bb_middle, bb_upper]):
            range_size = bb_upper - bb_lower
            grid_step = range_size / self.config['grid_levels']
            
            # Calculate position in range (0 = at lower band, 1 = at upper band)
            position_in_range = (current_price - bb_lower) / range_size if range_size > 0 else 0.5
            
            # BUY in lower third of range - ONLY if no position open
            if position_in_range < 0.33:
                if not open_position:
                    logger.info(f"📊 [GRID-SIGNAL] BUY | position_in_range={position_in_range:.2f} | Price: ${current_price:.8f}")
                    return 'BUY'
                else:
                    logger.debug(f"📊 [GRID-SKIP-BUY] Already have open position (side={open_position.get('side')}) at ${current_price:.8f}")
                    return 'NONE'
            
            # SELL in upper third of range - but ONLY if we have an open BUY position
            if position_in_range > 0.67:
                if open_position and open_position.get('side') == 'BUY':
                    logger.info(f"📊 [GRID-SIGNAL] SELL | position_in_range={position_in_range:.2f} | Entry: ${open_position.get('entry_price'):.8f} | Current: ${current_price:.8f}")
                    return 'SELL'
                else:
                    logger.debug(f"📊 [GRID-SKIP-SELL] position_in_range={position_in_range:.2f}, no open BUY position at ${current_price:.8f}")
                    return 'NONE'
        
            # Middle range - no signal
            logger.debug(f"📊 [GRID-NEUTRAL] position_in_range={position_in_range:.2f} (no signal in middle range) at ${current_price:.8f}")
            return 'NONE'
        
        # Fallback: use support/resistance if Bollinger Bands unavailable
        elif all([support, resistance]):
            range_size = resistance - support
            if range_size > 0:
                position_in_range = (current_price - support) / range_size
                
                if position_in_range < 0.3:
                    if not open_position:
                        logger.info(f"📊 [GRID-SIGNAL-FBALL] BUY | position_in_range={position_in_range:.2f} (using support/resistance)")
                        return 'BUY'
                    else:
                        logger.debug(f"📊 [GRID-SKIP-BUY-FBALL] Already have open position at ${current_price:.8f}")
                        return 'NONE'
                        
                if position_in_range > 0.7:
                    if open_position and open_position.get('side') == 'BUY':
                        logger.info(f"📊 [GRID-SIGNAL-FBALL] SELL | position_in_range={position_in_range:.2f} (using support/resistance)")
                        return 'SELL'
                    else:
                        logger.debug(f"📊 [GRID-SKIP-SELL-FBALL] No open BUY position at ${current_price:.8f}")
                        return 'NONE'
        
        logger.debug(f"📊 [GRID-NO-INDICATORS] No indicators available for grid calculation at ${current_price:.8f}")
        return 'NONE'
    
    def calculate_position_size(
        self, 
        risk_amount: float, 
        entry_price: float, 
        stop_loss: float
    ) -> float:
        # Grid trading uses smaller positions per grid level
        grid_levels = self.config['grid_levels']
        amount_per_grid = risk_amount / grid_levels
        price_diff = abs(entry_price - stop_loss)
        if price_diff == 0:
            return 0
        return round(amount_per_grid / price_diff, 8)
    
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
StrategyRegistry.register('grid_trading', GridTrading)

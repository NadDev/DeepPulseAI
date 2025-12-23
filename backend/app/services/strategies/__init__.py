# Strategy module initialization
from .base_strategy import BaseStrategy, StrategyRegistry
from .trend_following import TrendFollowing
from .breakout import Breakout
from .mean_reversion import MeanReversion

__all__ = [
    'BaseStrategy', 
    'StrategyRegistry',
    'TrendFollowing',
    'Breakout',
    'MeanReversion'
]

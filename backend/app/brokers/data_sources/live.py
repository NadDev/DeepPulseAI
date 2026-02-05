"""
LiveDataSource - Real market data from a live broker.

This data source delegates all market data queries to an upstream live broker
(typically Binance), while allowing the PaperBroker to simulate order execution.

This is the default mode for paper trading in production: real market prices,
simulated orders.
"""

from typing import List

from .base import DataSource
from ..base import Candle, Ticker, BaseBroker


class LiveDataSource(DataSource):
    """
    Data source that fetches real-time market data from a live broker.
    
    The PaperBroker uses this to get real market prices while simulating
    order execution. This provides the most realistic paper trading experience
    without actually placing orders on the exchange.
    
    Example:
        >>> binance = BinanceBroker()
        >>> live_source = LiveDataSource(binance)
        >>> paper_broker = PaperBroker(live_source, initial_balance=10000)
        >>> # paper_broker now has real market data but simulated trading
    """
    
    def __init__(self, upstream_broker: BaseBroker):
        """
        Initialize live data source.
        
        Args:
            upstream_broker: A live broker (e.g., BinanceBroker) to fetch data from
        """
        self.upstream = upstream_broker
    
    async def get_candles(
        self,
        symbol: str,
        interval: str,
        limit: int
    ) -> List[Candle]:
        """
        Fetch candles from the upstream broker.
        
        Delegates directly to the upstream broker's get_candles method.
        """
        return await self.upstream.get_candles(symbol, interval, limit)
    
    async def get_ticker(self, symbol: str) -> Ticker:
        """
        Fetch ticker from the upstream broker.
        
        Delegates directly to the upstream broker's get_ticker method.
        """
        return await self.upstream.get_ticker(symbol)
    
    async def get_latest_price(self, symbol: str) -> float:
        """
        Get latest price from the upstream broker.
        
        Delegates directly to the upstream broker's get_latest_price method.
        """
        return await self.upstream.get_latest_price(symbol)

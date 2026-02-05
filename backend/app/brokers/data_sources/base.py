"""
DataSource - Abstract base class for market data sources.

DataSources provide market data to the PaperBroker. Different implementations
allow for different testing scenarios:
- LiveDataSource: Real market data from a live broker (e.g., Binance)
- FileDataSource: Historical data from CSV/JSON files (backtesting)
- DBDataSource: Pre-loaded data from database (reproducible tests)
"""

from abc import ABC, abstractmethod
from typing import List

from ..base import Candle, Ticker


class DataSource(ABC):
    """
    Abstract base class for market data sources.
    
    PaperBroker uses a DataSource to fetch market prices for order simulation.
    This allows the same PaperBroker to work with:
    - Live market data (LiveDataSource)
    - Historical data files (FileDataSource)
    - Database snapshots (DBDataSource)
    """
    
    @abstractmethod
    async def get_candles(
        self,
        symbol: str,
        interval: str,
        limit: int
    ) -> List[Candle]:
        """
        Fetch OHLCV candles for a symbol.
        
        Args:
            symbol: Trading pair
            interval: Time interval (e.g., '1h', '1d')
            limit: Number of candles
            
        Returns:
            List of Candle objects
        """
        pass
    
    @abstractmethod
    async def get_ticker(self, symbol: str) -> Ticker:
        """
        Fetch 24h ticker for a symbol.
        
        Args:
            symbol: Trading pair
            
        Returns:
            Ticker object with 24h data
        """
        pass
    
    @abstractmethod
    async def get_latest_price(self, symbol: str) -> float:
        """
        Get the latest price for a symbol.
        
        Args:
            symbol: Trading pair
            
        Returns:
            Current price as float
        """
        pass

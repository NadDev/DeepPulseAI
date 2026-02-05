"""
Broker abstraction layer - unified interface for all exchanges.

This package provides:
- BaseBroker: Abstract base class with unified interface
- BinanceBroker: Live Binance implementation
- PaperBroker: Simulated paper trading
- Data sources: Live, File-based, DB-based market data
- Factory: BrokerFactory for instantiation based on user config
"""

from .base import (
    BaseBroker,
    OrderSide,
    OrderType,
    OrderStatus,
    Candle,
    Ticker,
    OrderResult,
    AccountBalance,
    SymbolInfo,
)
from .binance_broker import BinanceBroker
from .paper_broker import PaperBroker
from .factory import BrokerFactory
from .data_sources import DataSource, LiveDataSource

__all__ = [
    "BaseBroker",
    "BinanceBroker",
    "PaperBroker",
    "BrokerFactory",
    "DataSource",
    "LiveDataSource",
    "OrderSide",
    "OrderType",
    "OrderStatus",
    "Candle",
    "Ticker",
    "OrderResult",
    "AccountBalance",
    "SymbolInfo",
]

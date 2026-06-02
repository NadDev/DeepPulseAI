"""
Data sources for PaperBroker market data.

Available sources:
- LiveDataSource: Real-time data from a live broker
- MockDataSource: Fully local synthetic data (no external API)
- FileDataSource: Historical data from CSV/JSON (future)
- DBDataSource: Pre-loaded database snapshots (future)
"""

from .base import DataSource
from .live import LiveDataSource
from .mock import MockDataSource

__all__ = [
    "DataSource",
    "LiveDataSource",
    "MockDataSource",
]

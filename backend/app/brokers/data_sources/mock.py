"""
MockDataSource - Fully local synthetic market data source.

Used as a safe fallback when no broker is configured.
No external API calls, deterministic-enough pseudo-random candles per symbol.
"""

from datetime import datetime, timedelta
from typing import List
import hashlib
import random

from .base import DataSource
from ..base import Candle, Ticker


class MockDataSource(DataSource):
    """Local fake data source for paper/fallback mode."""

    def _seed(self, symbol: str, interval: str) -> int:
        payload = f"{symbol}:{interval}".encode()
        return int(hashlib.md5(payload).hexdigest()[:8], 16)

    def _base_price(self, symbol: str) -> float:
        symbol = symbol.upper()
        if "BTC" in symbol:
            return 68000.0
        if "ETH" in symbol:
            return 3400.0
        if "SOL" in symbol:
            return 160.0
        if "BNB" in symbol:
            return 600.0
        if "DOGE" in symbol:
            return 0.18
        return 100.0

    async def get_candles(self, symbol: str, interval: str, limit: int) -> List[Candle]:
        limit = max(1, min(limit, 1000))
        seed = self._seed(symbol, interval)
        rng = random.Random(seed)

        step_minutes = {
            "1m": 1,
            "3m": 3,
            "5m": 5,
            "15m": 15,
            "30m": 30,
            "1h": 60,
            "2h": 120,
            "4h": 240,
            "6h": 360,
            "12h": 720,
            "1d": 1440,
            "1w": 10080,
        }.get(interval, 60)

        now = datetime.utcnow()
        price = self._base_price(symbol)
        candles: List[Candle] = []

        for idx in range(limit):
            drift = rng.uniform(-0.004, 0.004)
            noise = rng.uniform(-0.002, 0.002)
            open_price = price
            close_price = max(0.0001, price * (1 + drift + noise))
            high_price = max(open_price, close_price) * (1 + rng.uniform(0.0005, 0.004))
            low_price = min(open_price, close_price) * (1 - rng.uniform(0.0005, 0.004))
            volume = abs(rng.gauss(1200, 450))

            ts = now - timedelta(minutes=step_minutes * (limit - idx))
            candles.append(
                Candle(
                    timestamp=ts,
                    open=float(open_price),
                    high=float(high_price),
                    low=float(low_price),
                    close=float(close_price),
                    volume=float(volume),
                )
            )
            price = close_price

        return candles

    async def get_ticker(self, symbol: str) -> Ticker:
        candles = await self.get_candles(symbol, "1h", 48)
        closes = [c.close for c in candles]
        if len(closes) < 2:
            price = self._base_price(symbol)
            return Ticker(
                symbol=symbol.upper(),
                price=price,
                high_24h=price,
                low_24h=price,
                volume_24h=0.0,
                change_24h_pct=0.0,
            )

        first = closes[0]
        last = closes[-1]
        change_pct = ((last - first) / first) * 100 if first else 0.0
        volume_24h = sum(c.volume for c in candles[-24:])

        return Ticker(
            symbol=symbol.upper(),
            price=last,
            high_24h=max(closes),
            low_24h=min(closes),
            volume_24h=volume_24h,
            change_24h_pct=change_pct,
        )

    async def get_latest_price(self, symbol: str) -> float:
        ticker = await self.get_ticker(symbol)
        return float(ticker.price)

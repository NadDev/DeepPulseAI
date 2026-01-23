"""
Market Data Collector Service
Handles real-time market data collection from various sources (WebSocket, APIs)
"""
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import httpx
import logging

logger = logging.getLogger(__name__)


class MarketDataCollector:
    """
    Collects market data from various sources (Binance, Coingecko, etc.)
    Supports both real-time WebSocket and historical data
    """
    
    def __init__(self):
        self.cache: Dict[str, Any] = {}
        self.update_times: Dict[str, datetime] = {}
        self.cache_ttl = 60  # seconds
        
    async def get_candles(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get OHLCV candles for a symbol
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            timeframe: Candle timeframe (1m, 5m, 15m, 1h, 4h, 1d)
            limit: Number of candles to return
            
        Returns:
            List of candle data [{timestamp, open, high, low, close, volume}, ...]
        """
        cache_key = f"candles_{symbol}_{timeframe}"
        
        # Check cache
        if cache_key in self.cache:
            if self._is_cache_valid(cache_key):
                logger.debug(f"Cache hit for {cache_key}")
                return self.cache[cache_key]
        
        try:
            # Fetch from Binance API
            candles = await self._fetch_binance_candles(symbol, timeframe, limit)
            self.cache[cache_key] = candles
            self.update_times[cache_key] = datetime.now()
            return candles
        except Exception as e:
            logger.error(f"Error fetching candles for {symbol}: {str(e)}")
            return []
    
    async def get_latest_price(self, symbol: str) -> Optional[float]:
        """
        Get the latest price for a symbol
        
        Args:
            symbol: Trading pair (e.g., 'BTC')
            
        Returns:
            Latest price or None if error
        """
        cache_key = f"price_{symbol}"
        
        if cache_key in self.cache and self._is_cache_valid(cache_key):
            return self.cache[cache_key]
        
        try:
            async with httpx.AsyncClient() as client:
                # Coingecko API
                response = await client.get(
                    f"https://api.coingecko.com/api/v3/simple/price",
                    params={
                        "ids": symbol.lower(),
                        "vs_currencies": "usd"
                    },
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    price = data.get(symbol.lower(), {}).get("usd")
                    if price:
                        self.cache[cache_key] = price
                        self.update_times[cache_key] = datetime.now()
                        return price
        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {str(e)}")
        
        return None
    
    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Get ticker data (latest candle) for a trading pair from Binance
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            
        Returns:
            Dictionary with {close, open, high, low, volume} or empty dict on error
        """
        cache_key = f"ticker_{symbol}"
        
        if cache_key in self.cache and self._is_cache_valid(cache_key):
            return self.cache[cache_key]
        
        try:
            # Fetch the latest 1-minute candle (most recent price)
            candles = await self._fetch_binance_candles(symbol, "1m", 1)
            
            if candles:
                candle = candles[0]
                ticker_data = {
                    "close": candle["close"],
                    "open": candle["open"],
                    "high": candle["high"],
                    "low": candle["low"],
                    "volume": candle["volume"],
                }
                self.cache[cache_key] = ticker_data
                self.update_times[cache_key] = datetime.now()
                return ticker_data
        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol}: {str(e)}")
        
        return {}
    
    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """
        Get comprehensive market data for a symbol
        
        Args:
            symbol: Symbol (BTC, ETH, etc.)
            
        Returns:
            Dictionary with price, change_24h, market_cap, volume, etc.
        """
        cache_key = f"market_{symbol}"
        
        if cache_key in self.cache and self._is_cache_valid(cache_key):
            return self.cache[cache_key]
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.coingecko.com/api/v3/coins/{symbol.lower()}",
                    params={"localization": "false"},
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    market_data = {
                        "symbol": symbol,
                        "price": data.get("market_data", {}).get("current_price", {}).get("usd", 0),
                        "change_24h": data.get("market_data", {}).get("price_change_percentage_24h", 0),
                        "market_cap": data.get("market_data", {}).get("market_cap", {}).get("usd", 0),
                        "volume_24h": data.get("market_data", {}).get("total_volume", {}).get("usd", 0),
                        "ath": data.get("market_data", {}).get("ath", {}).get("usd", 0),
                        "atl": data.get("market_data", {}).get("atl", {}).get("usd", 0),
                    }
                    
                    self.cache[cache_key] = market_data
                    self.update_times[cache_key] = datetime.now()
                    return market_data
        except Exception as e:
            logger.error(f"Error fetching market data for {symbol}: {str(e)}")
        
        return {"symbol": symbol, "error": "Failed to fetch market data"}
    
    async def _fetch_binance_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Fetch candles from Binance API"""
        # Ensure symbol format for Binance (e.g BTC -> BTCUSDT, BTC/USDT -> BTCUSDT)
        symbol = symbol.upper().strip()
        # Remove any slashes
        symbol = symbol.replace('/', '')
        # Add USDT if missing
        if not symbol.endswith("USDT"):
            symbol = f"{symbol}USDT"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.binance.com/api/v3/klines",
                    params={
                        "symbol": symbol,
                        "interval": timeframe,
                        "limit": limit
                    },
                    timeout=10
                )
                
                if response.status_code == 200:
                    candles_raw = response.json()
                    candles = []
                    
                    for candle in candles_raw:
                        candles.append({
                            "timestamp": candle[0],
                            "open": float(candle[1]),
                            "high": float(candle[2]),
                            "low": float(candle[3]),
                            "close": float(candle[4]),
                            "volume": float(candle[7]),
                        })
                    
                    return candles
        except Exception as e:
            logger.error(f"Error fetching Binance candles for {symbol}: {str(e)}")
        
        return []
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is still valid"""
        if cache_key not in self.update_times:
            return False
        
        age = (datetime.now() - self.update_times[cache_key]).total_seconds()
        return age < self.cache_ttl
    
    def clear_cache(self, cache_key: Optional[str] = None):
        """Clear cache entries"""
        if cache_key:
            self.cache.pop(cache_key, None)
            self.update_times.pop(cache_key, None)
        else:
            self.cache.clear()
            self.update_times.clear()


# Global instance
market_data_collector = MarketDataCollector()

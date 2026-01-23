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
        Get the latest price for a symbol using Binance (unified source)
        
        Args:
            symbol: Trading pair (e.g., 'BTC' or 'BTCUSDT')
            
        Returns:
            Latest price or None if error
        """
        # Normalize to Binance format
        symbol_normalized = symbol.upper()
        if not symbol_normalized.endswith("USDT"):
            symbol_normalized = f"{symbol_normalized}USDT"
        
        ticker_24h = await self.get_ticker_24h(symbol_normalized)
        
        if "error" not in ticker_24h:
            return ticker_24h.get("price")
        
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
    
    async def get_ticker_24h(self, symbol: str) -> Dict[str, Any]:
        """
        Get 24-hour ticker data from Binance API (single source of truth)
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            
        Returns:
            Dictionary with price, change_24h, high_24h, low_24h, volume_24h
        """
        cache_key = f"ticker_24h_{symbol}"
        
        if cache_key in self.cache and self._is_cache_valid(cache_key):
            return self.cache[cache_key]
        
        try:
            async with httpx.AsyncClient() as client:
                # Normalize symbol to Binance format
                symbol = symbol.upper()
                if not symbol.endswith("USDT"):
                    symbol = f"{symbol}USDT"
                
                response = await client.get(
                    f"https://api.binance.com/api/v3/ticker/24hr",
                    params={"symbol": symbol},
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    ticker_24h = {
                        "symbol": symbol,
                        "price": float(data.get("lastPrice", 0)),
                        "change_24h": float(data.get("priceChangePercent", 0)),
                        "high_24h": float(data.get("highPrice", 0)),
                        "low_24h": float(data.get("lowPrice", 0)),
                        "volume_24h": float(data.get("volume", 0)),
                        "quote_asset_volume": float(data.get("quoteAssetVolume", 0)),
                        "number_of_trades": int(data.get("count", 0)),
                    }
                    
                    self.cache[cache_key] = ticker_24h
                    self.update_times[cache_key] = datetime.now()
                    return ticker_24h
        except Exception as e:
            logger.error(f"Error fetching 24h ticker for {symbol}: {str(e)}")
        
        return {"symbol": symbol, "error": "Failed to fetch 24h ticker"}
    
    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """
        Get comprehensive market data from Binance (unified source)
        Uses get_ticker_24h as single source of truth
        
        Args:
            symbol: Symbol (BTC, ETH, etc. or BTCUSDT format)
            
        Returns:
            Dictionary with price, change_24h, volume, etc.
        """
        # Normalize to Binance format
        symbol_normalized = symbol.upper()
        if not symbol_normalized.endswith("USDT"):
            symbol_normalized = f"{symbol_normalized}USDT"
        
        # Use get_ticker_24h as unified source
        ticker_24h = await self.get_ticker_24h(symbol_normalized)
        
        if "error" not in ticker_24h:
            return {
                "symbol": symbol.upper(),
                "price": ticker_24h.get("price", 0),
                "change_24h": ticker_24h.get("change_24h", 0),
                "high_24h": ticker_24h.get("high_24h", 0),
                "low_24h": ticker_24h.get("low_24h", 0),
                "volume_24h": ticker_24h.get("quote_asset_volume", 0),
                "number_of_trades": ticker_24h.get("number_of_trades", 0),
                "source": "binance"
            }
        
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

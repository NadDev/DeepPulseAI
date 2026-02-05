"""
CoinGecko API Client
Fetches market cap, ATH price, and other fundamental data.

API: https://api.coingecko.com/api/v3/
Free tier: 50 calls/minute (no API key required)

Used by LongTermManager to filter coins by:
- Market cap (survival, $500M min)
- ATH distance (rebound potential, -50% to -90% ideal)
"""

import logging
import aiohttp
from typing import Dict, Optional
from datetime import datetime, timedelta
import asyncio

logger = logging.getLogger(__name__)


class CoinGeckoClient:
    """
    CoinGecko API wrapper with caching.
    Fetches symbols dynamically from watchlist + fallback to top 10 mapping.
    """
    
    BASE_URL = "https://api.coingecko.com/api/v3"
    CACHE_TTL = 600  # 10 minutes cache
    
    # Mapping Binance symbols -> CoinGecko IDs (TOP 10 only, rest fetched dynamically)
    BASE_SYMBOL_MAP = {
        "BTCUSDT": "bitcoin",
        "ETHUSDT": "ethereum",
        "BNBUSDT": "binancecoin",
        "SOLUSDT": "solana",
        "XRPUSDT": "ripple",
        "ADAUSDT": "cardano",
        "DOGEUSDT": "dogecoin",
        "MATICUSDT": "matic-network",
        "DOTUSDT": "polkadot",
        "AVAXUSDT": "avalanche-2"
    }
    
    def __init__(self, db_session=None):
        self.cache = {}  # {coin_id: {"data": {...}, "timestamp": datetime}}
        self.session: Optional[aiohttp.ClientSession] = None
        self.db_session = db_session
        self.dynamic_map = {}  # Runtime discovered mappings
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    def map_symbol_to_id(self, binance_symbol: str) -> Optional[str]:
        """
        Convert Binance symbol (ex: BTCUSDT) to CoinGecko ID (ex: bitcoin).
        
        Strategy:
        1. Check base mapping (top 10)
        2. Check dynamic runtime mapping
        3. Try lowercase base currency (BTCUSDT -> bitcoin)
        
        Returns:
            CoinGecko coin ID or None if not found
        """
        # 1. Base mapping
        if binance_symbol in self.BASE_SYMBOL_MAP:
            return self.BASE_SYMBOL_MAP[binance_symbol]
        
        # 2. Dynamic mapping
        if binance_symbol in self.dynamic_map:
            return self.dynamic_map[binance_symbol]
        
        # 3. Heuristic: extract base currency and lowercase it
        # BTCUSDT -> BTC -> bitcoin (works for many top coins)
        base_currency = binance_symbol.replace("USDT", "").replace("BUSD", "").replace("USD", "")
        coin_id_guess = base_currency.lower()
        
        # Store guess in dynamic map for future use
        self.dynamic_map[binance_symbol] = coin_id_guess
        logger.debug(f"🔍 Auto-mapped {binance_symbol} -> {coin_id_guess} (heuristic)")
        
        return coin_id_guess
    
    async def get_coin_data(self, coin_id: str, use_cache: bool = True) -> Optional[Dict]:
        """
        Fetch coin data from CoinGecko API.
        
        Args:
            coin_id: CoinGecko coin ID (ex: "bitcoin")
            use_cache: Whether to use cached data
        
        Returns:
            Dict with keys: id, symbol, name, market_data (current_price, market_cap, ath, ath_date, ath_change_percentage)
        """
        # Check cache
        if use_cache and coin_id in self.cache:
            cached = self.cache[coin_id]
            if datetime.now() - cached["timestamp"] < timedelta(seconds=self.CACHE_TTL):
                logger.debug(f"📦 CoinGecko cache hit: {coin_id}")
                return cached["data"]
        
        # Fetch from API
        try:
            url = f"{self.BASE_URL}/coins/{coin_id}"
            params = {
                "localization": "false",
                "tickers": "false",
                "market_data": "true",
                "community_data": "false",
                "developer_data": "false",
                "sparkline": "false"
            }
            
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            logger.debug(f"🌐 Fetching CoinGecko data for {coin_id}...")
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Cache result
                    self.cache[coin_id] = {
                        "data": data,
                        "timestamp": datetime.now()
                    }
                    
                    logger.info(f"✅ Fetched {data.get('name')} data from CoinGecko")
                    return data
                
                elif response.status == 429:
                    logger.error("❌ CoinGecko rate limit exceeded (50 calls/min)")
                    return None
                
                else:
                    logger.error(f"❌ CoinGecko API error {response.status}")
                    return None
        
        except Exception as e:
            logger.error(f"❌ CoinGecko API request failed: {e}")
            return None
    
    async def get_market_cap(self, binance_symbol: str) -> Optional[float]:
        """
        Get market cap for a symbol.
        
        Args:
            binance_symbol: Ex: "BTCUSDT"
        
        Returns:
            Market cap in USD or None
        """
        coin_id = self.map_symbol_to_id(binance_symbol)
        if not coin_id:
            logger.warning(f"Symbol {binance_symbol} not mapped to CoinGecko")
            return None
        
        coin_data = await self.get_coin_data(coin_id)
        if not coin_data:
            return None
        
        try:
            market_cap = coin_data.get("market_data", {}).get("market_cap", {}).get("usd")
            return float(market_cap) if market_cap else None
        except:
            return None
    
    async def get_ath_data(self, binance_symbol: str) -> Optional[Dict]:
        """
        Get ATH (All-Time High) data for a symbol.
        
        Args:
            binance_symbol: Ex: "BTCUSDT"
        
        Returns:
            Dict with keys: ath_price, ath_date, ath_change_percentage, current_price, time_since_ath_days, rebound_potential
        """
        coin_id = self.map_symbol_to_id(binance_symbol)
        if not coin_id:
            logger.warning(f"Symbol {binance_symbol} not mapped to CoinGecko")
            return None
        
        coin_data = await self.get_coin_data(coin_id)
        if not coin_data:
            return None
        
        try:
            market_data = coin_data.get("market_data", {})
            
            ath_price = market_data.get("ath", {}).get("usd")
            ath_date_str = market_data.get("ath_date", {}).get("usd")
            ath_change_pct = market_data.get("ath_change_percentage", {}).get("usd")
            current_price = market_data.get("current_price", {}).get("usd")
            
            if not all([ath_price, ath_date_str, current_price]):
                return None
            
            # Parse ATH date
            ath_date = datetime.fromisoformat(ath_date_str.replace("Z", "+00:00"))
            time_since_ath = datetime.now(ath_date.tzinfo) - ath_date
            
            # Calculate rebound potential
            rebound_potential = ath_price / current_price if current_price > 0 else 0
            
            return {
                "ath_price": float(ath_price),
                "ath_date": ath_date.strftime("%Y-%m-%d"),
                "ath_change_percentage": float(ath_change_pct) if ath_change_pct else None,
                "current_price": float(current_price),
                "time_since_ath_days": time_since_ath.days,
                "rebound_potential": round(rebound_potential, 2)
            }
        
        except Exception as e:
            logger.error(f"Error parsing ATH data for {binance_symbol}: {e}")
            return None
    
    async def get_market_cap_and_ath(self, binance_symbol: str) -> Optional[Dict]:
        """
        Get both market cap AND ATH data in a single call.
        More efficient than calling separately.
        
        Returns:
            Dict with keys: market_cap, ath_price, ath_date, current_price, ath_distance_pct, time_since_ath_days, rebound_potential
        """
        coin_id = self.map_symbol_to_id(binance_symbol)
        if not coin_id:
            logger.warning(f"Symbol {binance_symbol} not mapped to CoinGecko")
            return None
        
        coin_data = await self.get_coin_data(coin_id)
        if not coin_data:
            return None
        
        try:
            market_data = coin_data.get("market_data", {})
            
            market_cap = market_data.get("market_cap", {}).get("usd")
            ath_price = market_data.get("ath", {}).get("usd")
            ath_date_str = market_data.get("ath_date", {}).get("usd")
            ath_change_pct = market_data.get("ath_change_percentage", {}).get("usd")
            current_price = market_data.get("current_price", {}).get("usd")
            
            if not all([market_cap, ath_price, ath_date_str, current_price]):
                return None
            
            # Parse ATH date
            ath_date = datetime.fromisoformat(ath_date_str.replace("Z", "+00:00"))
            time_since_ath = datetime.now(ath_date.tzinfo) - ath_date
            
            # Calculate rebound potential
            rebound_potential = ath_price / current_price if current_price > 0 else 0
            
            return {
                "market_cap": float(market_cap),
                "ath_price": float(ath_price),
                "ath_date": ath_date.strftime("%Y-%m-%d"),
                "current_price": float(current_price),
                "ath_distance_pct": float(ath_change_pct) if ath_change_pct else None,
                "time_since_ath_days": time_since_ath.days,
                "rebound_potential": round(rebound_potential, 2)
            }
        
        except Exception as e:
            logger.error(f"Error parsing market cap/ATH data for {binance_symbol}: {e}")
            return None
    
    def clear_cache(self):
        """Clear all cached data."""
        self.cache = {}
        logger.info("🗑️ CoinGecko cache cleared")
    
    async def load_watchlist_symbols(self, user_id: str = None):
        """
        Load symbols from watchlist and populate dynamic mapping.
        Call this on startup or when watchlist changes.
        
        Args:
            user_id: If provided, load only this user's watchlist. Otherwise load all active symbols.
        """
        if not self.db_session:
            logger.warning("⚠️ Cannot load watchlist: no DB session provided")
            return
        
        try:
            from app.models.database_models import WatchlistItem
            
            query = self.db_session.query(WatchlistItem).filter(WatchlistItem.is_active == True)
            if user_id:
                query = query.filter(WatchlistItem.user_id == user_id)
            
            watchlist_items = query.all()
            
            for item in watchlist_items:
                symbol = item.symbol.replace("/", "")  # BTC/USDT -> BTCUSDT
                
                # Skip if already in base map
                if symbol in self.BASE_SYMBOL_MAP:
                    continue
                
                # Auto-map using heuristic
                if symbol not in self.dynamic_map:
                    base_currency = symbol.replace("USDT", "").replace("BUSD", "").replace("USD", "")
                    coin_id_guess = base_currency.lower()
                    self.dynamic_map[symbol] = coin_id_guess
            
            logger.info(f"✅ Loaded {len(watchlist_items)} symbols from watchlist ({len(self.dynamic_map)} dynamic mappings)")
        
        except Exception as e:
            logger.error(f"❌ Failed to load watchlist symbols: {e}")


# Global instance
_coingecko_client: Optional[CoinGeckoClient] = None


def get_coingecko_client(db_session=None) -> CoinGeckoClient:
    """Get or create the global CoinGecko client."""
    global _coingecko_client
    if _coingecko_client is None:
        _coingecko_client = CoinGeckoClient(db_session=db_session)
    return _coingecko_client

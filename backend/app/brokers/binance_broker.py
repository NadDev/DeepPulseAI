"""
BinanceBroker - Live Binance implementation of BaseBroker.

Encapsulates ALL Binance API HTTP calls that were previously scattered across:
- market_data.py
- ml_engine.py  
- routes/crypto.py
- portfolio_sync_service.py

Supports both testnet and live Binance API.
"""

import hashlib
import hmac
import time
import httpx
from datetime import datetime
from typing import List, Optional

from .base import (
    BaseBroker,
    Candle,
    Ticker,
    OrderResult,
    AccountBalance,
    SymbolInfo,
    OrderSide,
    OrderType,
    OrderStatus,
)


class BinanceBroker(BaseBroker):
    """
    Binance broker implementation.
    
    Handles:
    - Market data (candles, tickers, prices)
    - Order execution (market, limit, stop-loss)
    - Account balance queries
    - Symbol info and constraints
    
    Authentication via HMAC-SHA256 signed requests.
    """
    
    # API URLs
    LIVE_URL = "https://api.binance.com"
    TESTNET_URL = "https://testnet.binance.vision"
    
    # Interval mapping (internal format -> Binance format)
    INTERVAL_MAP = {
        "1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m", "30m": "30m",
        "1h": "1h", "2h": "2h", "4h": "4h", "6h": "6h", "8h": "8h",
        "12h": "12h", "1d": "1d", "3d": "3d", "1w": "1w", "1M": "1M"
    }
    
    def __init__(
        self,
        api_key: str = "",
        api_secret: str = "",
        testnet: bool = True
    ):
        """
        Initialize Binance broker.
        
        Args:
            api_key: Binance API key (optional for market data only)
            api_secret: Binance API secret (optional for market data only)
            testnet: Use testnet if True, live if False
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.base_url = self.TESTNET_URL if testnet else self.LIVE_URL
    
    # ========================================================================
    # IDENTIFICATION
    # ========================================================================
    
    @property
    def name(self) -> str:
        """Broker name with testnet indicator"""
        return "binance_testnet" if self.testnet else "binance"
    
    @property
    def is_paper(self) -> bool:
        """This is a live broker (even testnet is 'real' Binance)"""
        return False
    
    # ========================================================================
    # MARKET DATA
    # ========================================================================
    
    async def get_candles(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 100
    ) -> List[Candle]:
        """
        Fetch OHLCV candles from Binance.
        
        Refactored from: market_data.py::MarketDataCollector._fetch_binance_candles()
        Endpoint: GET /api/v3/klines
        """
        url = f"{self.base_url}/api/v3/klines"
        params = {
            "symbol": self.normalize_symbol(symbol),
            "interval": self.INTERVAL_MAP.get(interval, interval),
            "limit": limit
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
        
        candles = []
        for k in data:
            candles.append(Candle(
                timestamp=datetime.utcfromtimestamp(k[0] / 1000),
                open=float(k[1]),
                high=float(k[2]),
                low=float(k[3]),
                close=float(k[4]),
                volume=float(k[5])
            ))
        return candles
    
    async def get_ticker(self, symbol: str) -> Ticker:
        """
        Fetch 24h ticker from Binance.
        
        Refactored from: market_data.py::MarketDataCollector.get_ticker_24h()
        Endpoint: GET /api/v3/ticker/24hr
        """
        url = f"{self.base_url}/api/v3/ticker/24hr"
        params = {"symbol": self.normalize_symbol(symbol)}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
        
        return Ticker(
            symbol=data["symbol"],
            price=float(data["lastPrice"]),
            high_24h=float(data["highPrice"]),
            low_24h=float(data["lowPrice"]),
            volume_24h=float(data["volume"]),
            change_24h_pct=float(data["priceChangePercent"])
        )
    
    async def get_latest_price(self, symbol: str) -> float:
        """
        Get the latest price for a symbol.
        
        Refactored from: 
        - market_data.py::get_latest_price()
        - routes/crypto.py (direct httpx.get)
        
        Endpoint: GET /api/v3/ticker/price
        """
        url = f"{self.base_url}/api/v3/ticker/price"
        params = {"symbol": self.normalize_symbol(symbol)}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
        return float(data["price"])
    
    # ========================================================================
    # ORDERS
    # ========================================================================
    
    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[float] = None
    ) -> OrderResult:
        """
        Place an order on Binance.
        
        NEW implementation (previously not in codebase).
        Endpoint: POST /api/v3/order (HMAC-SHA256 signed)
        
        Args:
            symbol: Trading pair
            side: BUY or SELL
            quantity: Amount to trade
            order_type: MARKET, LIMIT, STOP_LOSS, STOP_LIMIT
            price: Required for LIMIT orders
            
        Returns:
            OrderResult with execution details
            
        Raises:
            httpx.HTTPStatusError: If API returns error
        """
        if not self.api_key or not self.api_secret:
            raise ValueError("API key and secret required for order placement")
        
        url = f"{self.base_url}/api/v3/order"
        
        # Build parameters
        params = {
            "symbol": self.normalize_symbol(symbol),
            "side": side.value,
            "type": order_type.value,
            "quantity": f"{quantity:.8f}",
            "timestamp": int(time.time() * 1000),
            "recvWindow": 5000
        }
        
        # Add price for LIMIT orders
        if order_type == OrderType.LIMIT and price:
            params["price"] = f"{price:.8f}"
            params["timeInForce"] = "GTC"  # Good Till Cancelled
        
        # Sign request with HMAC-SHA256
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        signature = hmac.new(
            self.api_secret.encode(),
            query_string.encode(),
            hashlib.sha256
        ).hexdigest()
        params["signature"] = signature
        
        headers = {"X-MBX-APIKEY": self.api_key}
        
        # Execute order
        async with httpx.AsyncClient() as client:
            response = await client.post(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
        
        # Parse response into OrderResult
        executed_qty = float(data.get("executedQty", 0))
        quote_qty = float(data.get("cummulativeQuoteQty", 0))
        fill_price = quote_qty / max(executed_qty, 0.00001) if executed_qty > 0 else 0
        
        return OrderResult(
            order_id=str(data["orderId"]),
            symbol=data["symbol"],
            side=OrderSide(data["side"]),
            order_type=OrderType(data["type"]),
            status=self._map_binance_status(data["status"]),
            requested_quantity=quantity,
            filled_quantity=executed_qty,
            requested_price=price,
            fill_price=fill_price,
            commission=self._extract_commission(data),
            commission_asset=self._extract_commission_asset(data),
            raw_response=data
        )
    
    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """
        Cancel an open order on Binance.
        
        Endpoint: DELETE /api/v3/order (HMAC-SHA256 signed)
        """
        if not self.api_key or not self.api_secret:
            raise ValueError("API key and secret required for order cancellation")
        
        url = f"{self.base_url}/api/v3/order"
        
        params = {
            "symbol": self.normalize_symbol(symbol),
            "orderId": order_id,
            "timestamp": int(time.time() * 1000),
            "recvWindow": 5000
        }
        
        # Sign request
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        signature = hmac.new(
            self.api_secret.encode(),
            query_string.encode(),
            hashlib.sha256
        ).hexdigest()
        params["signature"] = signature
        
        headers = {"X-MBX-APIKEY": self.api_key}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(url, params=params, headers=headers, timeout=30)
                response.raise_for_status()
            return True
        except httpx.HTTPStatusError:
            return False
    
    async def get_order_status(self, symbol: str, order_id: str) -> OrderResult:
        """
        Query order status from Binance.
        
        Endpoint: GET /api/v3/order (HMAC-SHA256 signed)
        """
        if not self.api_key or not self.api_secret:
            raise ValueError("API key and secret required for order status query")
        
        url = f"{self.base_url}/api/v3/order"
        
        params = {
            "symbol": self.normalize_symbol(symbol),
            "orderId": order_id,
            "timestamp": int(time.time() * 1000),
            "recvWindow": 5000
        }
        
        # Sign request
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        signature = hmac.new(
            self.api_secret.encode(),
            query_string.encode(),
            hashlib.sha256
        ).hexdigest()
        params["signature"] = signature
        
        headers = {"X-MBX-APIKEY": self.api_key}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
        
        # Parse response
        executed_qty = float(data.get("executedQty", 0))
        quote_qty = float(data.get("cummulativeQuoteQty", 0))
        fill_price = quote_qty / max(executed_qty, 0.00001) if executed_qty > 0 else float(data.get("price", 0))
        
        return OrderResult(
            order_id=str(data["orderId"]),
            symbol=data["symbol"],
            side=OrderSide(data["side"]),
            order_type=OrderType(data["type"]),
            status=self._map_binance_status(data["status"]),
            requested_quantity=float(data["origQty"]),
            filled_quantity=executed_qty,
            requested_price=float(data.get("price", 0)) if data.get("price") else None,
            fill_price=fill_price,
            commission=0,  # Not included in order query response
            raw_response=data
        )
    
    # ========================================================================
    # ACCOUNT
    # ========================================================================
    
    async def get_account_balance(self) -> AccountBalance:
        """
        Fetch account balance from Binance.
        
        Refactored from: portfolio_sync_service.py (binance.account)
        Endpoint: GET /api/v3/account (HMAC-SHA256 signed)
        """
        if not self.api_key or not self.api_secret:
            raise ValueError("API key and secret required for account balance query")
        
        url = f"{self.base_url}/api/v3/account"
        
        params = {
            "timestamp": int(time.time() * 1000),
            "recvWindow": 5000
        }
        
        # Sign request
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        signature = hmac.new(
            self.api_secret.encode(),
            query_string.encode(),
            hashlib.sha256
        ).hexdigest()
        params["signature"] = signature
        
        headers = {"X-MBX-APIKEY": self.api_key}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
        
        # Parse balances
        assets = {}
        total_usdt = 0.0
        free_usdt = 0.0
        locked_usdt = 0.0
        
        for balance in data.get("balances", []):
            asset = balance["asset"]
            free = float(balance["free"])
            locked = float(balance["locked"])
            
            if free <= 0 and locked <= 0:
                continue
            
            if asset == "USDT":
                free_usdt = free
                locked_usdt = locked
                total_usdt += free + locked
                assets[asset] = {"free": free, "locked": locked, "value_usdt": free + locked}
            else:
                # Convert other assets to USDT value
                try:
                    price = await self.get_latest_price(f"{asset}USDT")
                    value_usdt = (free + locked) * price
                    total_usdt += value_usdt
                    assets[asset] = {"free": free, "locked": locked, "value_usdt": value_usdt}
                except:
                    # Skip assets we can't price
                    pass
        
        return AccountBalance(
            total_value_usdt=total_usdt,
            free_usdt=free_usdt,
            locked_usdt=locked_usdt,
            assets=assets
        )
    
    # ========================================================================
    # SYMBOL INFO
    # ========================================================================
    
    async def get_symbol_info(self, symbol: str) -> SymbolInfo:
        """
        Get trading constraints for a symbol from Binance.
        
        Endpoint: GET /api/v3/exchangeInfo
        """
        url = f"{self.base_url}/api/v3/exchangeInfo"
        params = {"symbol": self.normalize_symbol(symbol)}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
        
        if not data.get("symbols"):
            raise ValueError(f"Symbol {symbol} not found on Binance")
        
        symbol_data = data["symbols"][0]
        
        # Extract filters
        lot_size_filter = next((f for f in symbol_data["filters"] if f["filterType"] == "LOT_SIZE"), {})
        notional_filter = next((f for f in symbol_data["filters"] if f["filterType"] == "NOTIONAL"), {})
        price_filter = next((f for f in symbol_data["filters"] if f["filterType"] == "PRICE_FILTER"), {})
        
        return SymbolInfo(
            symbol=symbol_data["symbol"],
            base_asset=symbol_data["baseAsset"],
            quote_asset=symbol_data["quoteAsset"],
            min_quantity=float(lot_size_filter.get("minQty", 0)),
            max_quantity=float(lot_size_filter.get("maxQty", 9000)),
            step_size=float(lot_size_filter.get("stepSize", 0.00001)),
            min_notional=float(notional_filter.get("minNotional", 10)),
            tick_size=float(price_filter.get("tickSize", 0.01)),
            status=symbol_data["status"]
        )
    
    def normalize_symbol(self, symbol: str) -> str:
        """
        Normalize symbol to Binance format (no separator).
        
        Examples:
            BTC/USDT -> BTCUSDT
            BTC-USDT -> BTCUSDT
            btcusdt -> BTCUSDT
        """
        s = symbol.upper().replace("/", "").replace("-", "").replace("_", "")
        
        # Auto-append USDT if no quote asset specified
        if not s.endswith("USDT") and not s.endswith("BTC") and not s.endswith("ETH"):
            s += "USDT"
        
        return s
    
    def get_supported_intervals(self) -> List[str]:
        """Return list of supported intervals"""
        return list(self.INTERVAL_MAP.keys())
    
    # ========================================================================
    # HELPERS
    # ========================================================================
    
    def _map_binance_status(self, status: str) -> OrderStatus:
        """Map Binance order status to OrderStatus enum"""
        mapping = {
            "NEW": OrderStatus.PENDING,
            "PARTIALLY_FILLED": OrderStatus.PARTIALLY_FILLED,
            "FILLED": OrderStatus.FILLED,
            "CANCELED": OrderStatus.CANCELLED,
            "PENDING_CANCEL": OrderStatus.PENDING,
            "REJECTED": OrderStatus.REJECTED,
            "EXPIRED": OrderStatus.EXPIRED
        }
        return mapping.get(status, OrderStatus.PENDING)
    
    def _extract_commission(self, order_data: dict) -> float:
        """Extract commission from order response"""
        fills = order_data.get("fills", [])
        if fills:
            return sum(float(f.get("commission", 0)) for f in fills)
        return 0.0
    
    def _extract_commission_asset(self, order_data: dict) -> str:
        """Extract commission asset from order response"""
        fills = order_data.get("fills", [])
        if fills and fills[0].get("commissionAsset"):
            return fills[0]["commissionAsset"]
        return "USDT"

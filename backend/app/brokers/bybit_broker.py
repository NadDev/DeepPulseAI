"""
BybitBroker - Live Bybit implementation of BaseBroker.

Uses Bybit V5 API. Works from cloud providers (no IP geo-restrictions).

Testnet:  https://api-testnet.bybit.com  (free account at testnet.bybit.com)
Mainnet:  https://api.bybit.com

Auth: HMAC-SHA256 signed requests (api_key + timestamp + recv_window + body)
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


class BybitBroker(BaseBroker):
    """
    Bybit V5 broker implementation.

    Handles:
    - Market data (candles, tickers, prices)
    - Account balance queries
    - Order execution

    Works from Railway/AWS/GCP without geo-restrictions.
    """

    LIVE_URL = "https://api.bybit.com"
    TESTNET_URL = "https://api-testnet.bybit.com"

    # Bybit interval mapping
    INTERVAL_MAP = {
        "1m": "1",  "3m": "3",  "5m": "5",  "15m": "15", "30m": "30",
        "1h": "60", "2h": "120","4h": "240","6h": "360", "12h": "720",
        "1d": "D",  "1w": "W",  "1M": "M",
    }

    def __init__(
        self,
        api_key: str = "",
        api_secret: str = "",
        testnet: bool = True,
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.base_url = self.TESTNET_URL if testnet else self.LIVE_URL
        self._recv_window = 5000

    # ========================================================================
    # IDENTIFICATION
    # ========================================================================

    @property
    def name(self) -> str:
        return "bybit_testnet" if self.testnet else "bybit"

    @property
    def is_paper(self) -> bool:
        return False

    # ========================================================================
    # AUTH HELPER
    # ========================================================================

    def _sign(self, params: dict) -> dict:
        """
        Add HMAC-SHA256 signature to a request params dict.
        Bybit V5 signature: HMAC of (timestamp + api_key + recv_window + query_string)
        """
        ts = str(int(time.time() * 1000))
        recv_window = str(self._recv_window)

        # Build query string from params (sorted)
        query = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        sign_payload = f"{ts}{self.api_key}{recv_window}{query}"

        signature = hmac.new(
            self.api_secret.encode(),
            sign_payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        return {
            "api_key": self.api_key,
            "timestamp": ts,
            "recv_window": recv_window,
            "sign": signature,
            **params,
        }

    def _auth_headers(self, params: dict) -> dict:
        """Return headers for a signed request (Bybit V5 header-based auth)."""
        ts = str(int(time.time() * 1000))
        recv_window = str(self._recv_window)

        # Build query string from params
        query = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        sign_payload = f"{ts}{self.api_key}{recv_window}{query}"

        signature = hmac.new(
            self.api_secret.encode(),
            sign_payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        return {
            "X-BAPI-API-KEY": self.api_key,
            "X-BAPI-TIMESTAMP": ts,
            "X-BAPI-RECV-WINDOW": recv_window,
            "X-BAPI-SIGN": signature,
        }

    # ========================================================================
    # MARKET DATA  (public, no auth required)
    # ========================================================================

    def normalize_symbol(self, symbol: str) -> str:
        symbol = symbol.upper().replace("/", "")
        if not symbol.endswith("USDT"):
            symbol = f"{symbol}USDT"
        return symbol

    async def get_candles(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 100,
    ) -> List[Candle]:
        """GET /v5/market/kline"""
        url = f"{self.base_url}/v5/market/kline"
        params = {
            "category": "spot",
            "symbol": self.normalize_symbol(symbol),
            "interval": self.INTERVAL_MAP.get(interval, "60"),
            "limit": min(limit, 1000),
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

        if data.get("retCode") != 0:
            raise RuntimeError(f"Bybit API error: {data.get('retMsg')}")

        candles = []
        for k in reversed(data["result"]["list"]):
            # k = [startTime, open, high, low, close, volume, turnover]
            candles.append(
                Candle(
                    timestamp=datetime.utcfromtimestamp(int(k[0]) / 1000),
                    open=float(k[1]),
                    high=float(k[2]),
                    low=float(k[3]),
                    close=float(k[4]),
                    volume=float(k[5]),
                )
            )
        return candles

    async def get_ticker(self, symbol: str) -> Ticker:
        """GET /v5/market/tickers"""
        url = f"{self.base_url}/v5/market/tickers"
        params = {"category": "spot", "symbol": self.normalize_symbol(symbol)}

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

        if data.get("retCode") != 0:
            raise RuntimeError(f"Bybit API error: {data.get('retMsg')}")

        t = data["result"]["list"][0]
        return Ticker(
            symbol=t["symbol"],
            price=float(t["lastPrice"]),
            high_24h=float(t["highPrice24h"]),
            low_24h=float(t["lowPrice24h"]),
            volume_24h=float(t["volume24h"]),
            change_24h_pct=float(t["price24hPcnt"]) * 100,
        )

    async def get_latest_price(self, symbol: str) -> float:
        """GET /v5/market/tickers – last price"""
        ticker = await self.get_ticker(symbol)
        return ticker.price

    # ========================================================================
    # ACCOUNT  (authenticated)
    # ========================================================================

    async def get_account_balance(self) -> AccountBalance:
        """
        GET /v5/account/wallet-balance
        Tries UNIFIED first (full account), falls back to SPOT.
        """
        if not self.api_key or not self.api_secret:
            raise ValueError("API key and secret required for account balance query")

        url = f"{self.base_url}/v5/account/wallet-balance"

        # Try UNIFIED first, fall back to SPOT (testnet often uses SPOT)
        for account_type in ("UNIFIED", "SPOT"):
            params = {"accountType": account_type}
            headers = self._auth_headers(params)

            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, headers=headers, timeout=10)
                response.raise_for_status()
                data = response.json()

            if data.get("retCode") == 0 and data["result"]["list"]:
                break
        else:
            raise RuntimeError(f"Bybit account balance error: {data.get('retMsg')}")

        # Parse the UNIFIED wallet
        total_usdt = 0.0
        free_usdt = 0.0
        locked_usdt = 0.0
        assets: dict = {}

        for account in data["result"]["list"]:
            for coin in account.get("coin", []):
                asset = coin["coin"]
                free = float(coin.get("availableToWithdraw") or coin.get("free") or 0)
                locked = float(coin.get("locked") or 0)
                usd_value = float(coin.get("usdValue") or 0)

                if usd_value <= 0 and free <= 0 and locked <= 0:
                    continue

                if asset == "USDT":
                    free_usdt = free
                    locked_usdt = locked
                    total_usdt += free + locked
                    assets[asset] = {"free": free, "locked": locked, "value_usdt": free + locked}
                else:
                    total_usdt += usd_value
                    assets[asset] = {"free": free, "locked": locked, "value_usdt": usd_value}

        return AccountBalance(
            total_value_usdt=total_usdt,
            free_usdt=free_usdt,
            locked_usdt=locked_usdt,
            assets=assets,
        )

    # ========================================================================
    # ORDERS
    # ========================================================================

    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[float] = None,
    ) -> OrderResult:
        """POST /v5/order/create"""
        if not self.api_key or not self.api_secret:
            raise ValueError("API key and secret required for order placement")

        url = f"{self.base_url}/v5/order/create"
        body = {
            "category": "spot",
            "symbol": self.normalize_symbol(symbol),
            "side": side.value.capitalize(),   # "Buy" or "Sell"
            "orderType": "Market" if order_type == OrderType.MARKET else "Limit",
            "qty": str(quantity),
        }
        if price and order_type != OrderType.MARKET:
            body["price"] = str(price)

        # Build signed headers using the body as query string
        headers = self._auth_headers(body)
        headers["Content-Type"] = "application/json"

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=body, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()

        if data.get("retCode") != 0:
            raise RuntimeError(f"Bybit order error {data.get('retCode')}: {data.get('retMsg')}")

        result = data["result"]
        return OrderResult(
            order_id=result.get("orderId", ""),
            symbol=self.normalize_symbol(symbol),
            side=side,
            order_type=order_type,
            status=OrderStatus.PENDING,
            requested_quantity=quantity,
            filled_quantity=0.0,
            requested_price=price,
            fill_price=price or 0.0,
            timestamp=datetime.utcnow(),
            raw_response=data,
        )

    async def get_symbol_info(self, symbol: str) -> SymbolInfo:
        """GET /v5/market/instruments-info"""
        url = f"{self.base_url}/v5/market/instruments-info"
        params = {"category": "spot", "symbol": self.normalize_symbol(symbol)}

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

        if data.get("retCode") != 0:
            raise RuntimeError(f"Bybit API error: {data.get('retMsg')}")

        info = data["result"]["list"][0]
        lot = info.get("lotSizeFilter", {})
        price_f = info.get("priceFilter", {})

        return SymbolInfo(
            symbol=info["symbol"],
            base_asset=info["baseCoin"],
            quote_asset=info["quoteCoin"],
            min_quantity=float(lot.get("minOrderQty", 0)),
            max_quantity=float(lot.get("maxOrderQty", 0)),
            step_size=float(lot.get("basePrecision", 0.00000001)),
            min_notional=float(lot.get("minOrderAmt", 1)),
            tick_size=float(price_f.get("tickSize", 0.01)),
        )

    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """POST /v5/order/cancel"""
        url = f"{self.base_url}/v5/order/cancel"
        body = {
            "category": "spot",
            "symbol": self.normalize_symbol(symbol),
            "orderId": order_id,
        }
        headers = self._auth_headers(body)
        headers["Content-Type"] = "application/json"

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=body, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()

        return data.get("retCode") == 0

    async def get_order_status(self, symbol: str, order_id: str) -> OrderResult:
        """GET /v5/order/realtime"""
        url = f"{self.base_url}/v5/order/realtime"
        params = {
            "category": "spot",
            "symbol": self.normalize_symbol(symbol),
            "orderId": order_id,
        }
        headers = self._auth_headers(params)

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()

        if data.get("retCode") != 0:
            raise RuntimeError(f"Bybit order status error: {data.get('retMsg')}")

        o = data["result"]["list"][0]
        status_map = {
            "New": OrderStatus.PENDING,
            "PartiallyFilled": OrderStatus.PARTIALLY_FILLED,
            "Filled": OrderStatus.FILLED,
            "Cancelled": OrderStatus.CANCELLED,
            "Rejected": OrderStatus.REJECTED,
        }
        return OrderResult(
            order_id=o["orderId"],
            symbol=o["symbol"],
            side=OrderSide.BUY if o["side"] == "Buy" else OrderSide.SELL,
            order_type=OrderType.MARKET if o["orderType"] == "Market" else OrderType.LIMIT,
            status=status_map.get(o["orderStatus"], OrderStatus.PENDING),
            requested_quantity=float(o["qty"]),
            filled_quantity=float(o.get("cumExecQty", 0)),
            requested_price=float(o["price"]) if o.get("price") else None,
            fill_price=float(o.get("avgPrice") or o.get("price") or 0),
            timestamp=datetime.utcfromtimestamp(int(o["createdTime"]) / 1000),
            raw_response=o,
        )

    def get_supported_intervals(self) -> list:
        return list(self.INTERVAL_MAP.keys())

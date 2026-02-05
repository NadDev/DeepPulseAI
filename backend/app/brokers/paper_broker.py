"""
PaperBroker - Simulated paper trading broker.

Provides realistic paper trading simulation with:
- Virtual porfolio tracking
- Configurable slippage and commissions
- Order rejection (insufficient balance)
- Pluggable data sources (live, file, DB)

Orders are executed instantly at simulated prices, with no actual
exchange API calls for order placement.
"""

from typing import List, Optional
from datetime import datetime

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
from .data_sources.base import DataSource


class PaperBroker(BaseBroker):
    """
    Paper trading broker with virtual portfolio simulation.
    
    Key features:
    - Simulates order execution with configurable slippage
    - Tracks virtual balance (USDT + crypto assets)
    - Applies realistic commission fees
    - Rejects orders on insufficient balance
    - Uses DataSource for market prices (live, file, or DB)
    
    The paper broker behaves identically to a live broker from the service layer
    perspective, making it easy to switch between paper and live trading.
    
    Example:
        >>> from brokers import BinanceBroker, PaperBroker
        >>> from brokers.data_sources import LiveDataSource
        >>> 
        >>> # Create paper broker with live data
        >>> binance = BinanceBroker()
        >>> data_source = LiveDataSource(binance)
        >>> paper = PaperBroker(data_source, initial_balance=10000)
        >>> 
        >>> # Place simulated order
        >>> result = await paper.place_order("BTCUSDT", OrderSide.BUY, 0.01)
        >>> print(f"Order {result.order_id}: {result.status}")
    """
    
    def __init__(
        self,
        data_source: DataSource,
        initial_balance: float = 10000.0,
        slippage_pct: float = 0.05,
        commission_pct: float = 0.1,
    ):
        """
        Initialize paper broker.
        
        Args:
            data_source: Source for market data (LiveDataSource, FileDataSource, etc.)
            initial_balance: Starting USDT balance (default: 10,000)
            slippage_pct: Simulated slippage percentage (default: 0.05%)
            commission_pct: Commission percentage per trade (default: 0.1%)
        """
        self.data_source = data_source
        self.slippage_pct = slippage_pct
        self.commission_pct = commission_pct
        
        # Virtual portfolio
        self._balance = {"USDT": initial_balance}
        self._orders: List[OrderResult] = []
        self._order_counter = 0
    
    # ========================================================================
    # IDENTIFICATION
    # ========================================================================
    
    @property
    def name(self) -> str:
        """Broker name identifier"""
        return "paper"
    
    @property
    def is_paper(self) -> bool:
        """This is a paper/simulated broker"""
        return True
    
    # ========================================================================
    # MARKET DATA (Delegated to DataSource)
    # ========================================================================
    
    async def get_candles(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 100
    ) -> List[Candle]:
        """Fetch candles from data source"""
        return await self.data_source.get_candles(symbol, interval, limit)
    
    async def get_ticker(self, symbol: str) -> Ticker:
        """Fetch ticker from data source"""
        return await self.data_source.get_ticker(symbol)
    
    async def get_latest_price(self, symbol: str) -> float:
        """Get latest price from data source"""
        return await self.data_source.get_latest_price(symbol)
    
    # ========================================================================
    # ORDERS (Simulated)
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
        Simulate order execution with slippage and commission.
        
        The order is executed instantly at a simulated price:
        - BUY orders: market_price * (1 + slippage%)
        - SELL orders: market_price * (1 - slippage%)
        
        Commission is applied to the total cost.
        
        Args:
            symbol: Trading pair
            side: BUY or SELL
            quantity: Amount to trade
            order_type: MARKET or LIMIT
            price: Limit price (optional, for LIMIT orders)
            
        Returns:
            OrderResult with FILLED or REJECTED status
        """
        # Get current market price
        market_price = await self.get_latest_price(symbol)
        
        # Calculate fill price with slippage
        if order_type == OrderType.MARKET:
            if side == OrderSide.BUY:
                fill_price = market_price * (1 + self.slippage_pct / 100)
            else:
                fill_price = market_price * (1 - self.slippage_pct / 100)
        else:
            # LIMIT orders fill at specified price
            fill_price = price or market_price
        
        # Calculate commission and total cost
        commission = fill_price * quantity * (self.commission_pct / 100)
        total_cost = fill_price * quantity + commission
        
        # Extract base asset (e.g., "BTC" from "BTCUSDT")
        base_asset = symbol.replace("USDT", "").replace("BUSD", "").replace("USD", "")
        
        # Check balance and execute
        if side == OrderSide.BUY:
            # Check if enough USDT
            if self._balance.get("USDT", 0) < total_cost:
                return OrderResult(
                    order_id=self._next_order_id(),
                    symbol=symbol,
                    side=side,
                    order_type=order_type,
                    status=OrderStatus.REJECTED,
                    requested_quantity=quantity,
                    filled_quantity=0,
                    requested_price=price,
                    fill_price=0,
                    commission=0
                )
            
            # Deduct USDT, add crypto asset
            self._balance["USDT"] -= total_cost
            self._balance[base_asset] = self._balance.get(base_asset, 0) + quantity
        
        elif side == OrderSide.SELL:
            # Check if enough crypto asset
            if self._balance.get(base_asset, 0) < quantity:
                return OrderResult(
                    order_id=self._next_order_id(),
                    symbol=symbol,
                    side=side,
                    order_type=order_type,
                    status=OrderStatus.REJECTED,
                    requested_quantity=quantity,
                    filled_quantity=0,
                    requested_price=price,
                    fill_price=0,
                    commission=0
                )
            
            # Deduct crypto asset, add USDT (minus commission)
            self._balance[base_asset] -= quantity
            self._balance["USDT"] += (fill_price * quantity) - commission
        
        # Create filled order result
        result = OrderResult(
            order_id=self._next_order_id(),
            symbol=symbol,
            side=side,
            order_type=order_type,
            status=OrderStatus.FILLED,
            requested_quantity=quantity,
            filled_quantity=quantity,
            requested_price=price,
            fill_price=fill_price,
            commission=commission,
            commission_asset="USDT"
        )
        
        self._orders.append(result)
        return result
    
    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """
        Cancel order (no-op for paper broker, orders fill instantly).
        
        Always returns True since orders are executed immediately.
        """
        return True
    
    async def get_order_status(self, symbol: str, order_id: str) -> OrderResult:
        """
        Get order status by ID.
        
        Searches the order history for the specified order.
        """
        for order in self._orders:
            if order.order_id == order_id:
                return order
        return None
    
    # ========================================================================
    # ACCOUNT
    # ========================================================================
    
    async def get_account_balance(self) -> AccountBalance:
        """
        Get virtual account balance.
        
        Calculates total portfolio value by:
        1. USDT balance (direct)
        2. Other assets * current_price (from data source)
        
        Returns:
            AccountBalance with total portfolio value in USDT
        """
        total_usdt = 0.0
        assets = {}
        
        for asset, qty in self._balance.items():
            if qty <= 0:
                continue
            
            if asset == "USDT":
                total_usdt += qty
                assets[asset] = {"free": qty, "locked": 0, "value_usdt": qty}
            else:
                # Get current price and calculate value
                try:
                    price = await self.get_latest_price(f"{asset}USDT")
                    value_usdt = qty * price
                    total_usdt += value_usdt
                    assets[asset] = {"free": qty, "locked": 0, "value_usdt": value_usdt}
                except:
                    # Skip assets we can't price
                    pass
        
        return AccountBalance(
            total_value_usdt=total_usdt,
            free_usdt=self._balance.get("USDT", 0),
            locked_usdt=0,
            assets=assets
        )
    
    # ========================================================================
    # SYMBOL INFO
    # ========================================================================
    
    async def get_symbol_info(self, symbol: str) -> SymbolInfo:
        """
        Get symbol info (generic defaults for paper trading).
        
        Returns generic trading constraints suitable for paper trading.
        For production, these would be fetched from the upstream exchange.
        """
        base_asset = symbol.replace("USDT", "").replace("BUSD", "").replace("USD", "")
        
        return SymbolInfo(
            symbol=symbol,
            base_asset=base_asset,
            quote_asset="USDT",
            min_quantity=0.00001,
            max_quantity=10000.0,
            step_size=0.00001,
            min_notional=10.0,
            tick_size=0.01,
            status="TRADING"
        )
    
    def normalize_symbol(self, symbol: str) -> str:
        """
        Normalize symbol (removes separators, uppercase).
        
        Examples:
            BTC/USDT -> BTCUSDT
            btc-usdt -> BTCUSDT
        """
        return symbol.upper().replace("/", "").replace("-", "").replace("_", "")
    
    def get_supported_intervals(self) -> List[str]:
        """Return list of supported intervals (standard set)"""
        return [
            "1m", "3m", "5m", "15m", "30m",
            "1h", "2h", "4h", "6h", "8h", "12h",
            "1d", "3d", "1w", "1M"
        ]
    
    # ========================================================================
    # HELPERS
    # ========================================================================
    
    def _next_order_id(self) -> str:
        """Generate next paper order ID"""
        self._order_counter += 1
        return f"PAPER-{self._order_counter:08d}"
    
    def get_order_history(self) -> List[OrderResult]:
        """Get all executed orders (useful for testing/debugging)"""
        return self._orders.copy()
    
    def reset_balance(self, usdt: float = 10000.0):
        """Reset paper portfolio (useful for testing)"""
        self._balance = {"USDT": usdt}
        self._orders = []
        self._order_counter = 0

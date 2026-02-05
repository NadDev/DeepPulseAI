"""
BaseBroker - Abstract base class and dataclasses for all broker implementations.

This module provides the unified interface for all brokers (Binance, Kraken, Paper, etc.)
and the common data structures shared across all implementations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


# ============================================================================
# ENUMS - Order Types & Statuses
# ============================================================================

class OrderSide(str, Enum):
    """Side of an order - BUY or SELL"""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    """Type of order"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    STOP_LIMIT = "STOP_LIMIT"


class OrderStatus(str, Enum):
    """Status of an order"""
    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


# ============================================================================
# DATACLASSES - Unified Data Structures
# ============================================================================

@dataclass
class Candle:
    """OHLCV candle - unified format across all exchanges"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume
        }


@dataclass
class Ticker:
    """24h ticker information - unified format"""
    symbol: str
    price: float
    high_24h: float
    low_24h: float
    volume_24h: float
    change_24h_pct: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "symbol": self.symbol,
            "price": self.price,
            "high_24h": self.high_24h,
            "low_24h": self.low_24h,
            "volume_24h": self.volume_24h,
            "change_24h_pct": self.change_24h_pct,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class OrderResult:
    """Result of an order execution - same format for paper and live"""
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    status: OrderStatus
    requested_quantity: float
    filled_quantity: float
    requested_price: Optional[float]  # None for MARKET orders
    fill_price: float  # Actual execution price
    commission: float = 0.0
    commission_asset: str = "USDT"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    raw_response: Optional[dict] = None  # Raw exchange response
    
    @property
    def is_filled(self) -> bool:
        """Check if order is fully filled"""
        return self.status == OrderStatus.FILLED
    
    @property
    def total_cost(self) -> float:
        """Total cost including commission"""
        return self.fill_price * self.filled_quantity + self.commission
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "order_type": self.order_type.value,
            "status": self.status.value,
            "requested_quantity": self.requested_quantity,
            "filled_quantity": self.filled_quantity,
            "requested_price": self.requested_price,
            "fill_price": self.fill_price,
            "commission": self.commission,
            "commission_asset": self.commission_asset,
            "timestamp": self.timestamp.isoformat(),
            "total_cost": self.total_cost
        }


@dataclass
class AccountBalance:
    """Account balance information - unified format"""
    total_value_usdt: float  # Portfolio value in USDT
    free_usdt: float  # Available USDT balance
    locked_usdt: float  # Locked/reserved USDT
    assets: Dict[str, dict] = field(default_factory=dict)
    # assets = {"BTC": {"free": 1.0, "locked": 0.5, "value_usdt": 95000.0}}
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "total_value_usdt": self.total_value_usdt,
            "free_usdt": self.free_usdt,
            "locked_usdt": self.locked_usdt,
            "assets": self.assets,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class SymbolInfo:
    """Trading constraints and info for a symbol"""
    symbol: str
    base_asset: str  # e.g., BTC
    quote_asset: str  # e.g., USDT
    min_quantity: float  # Minimum order quantity
    max_quantity: float  # Maximum order quantity
    step_size: float  # Quantity precision
    min_notional: float  # Minimum order value in quote asset
    tick_size: float  # Price precision
    status: str = "TRADING"  # TRADING, HALT, BREAK
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "symbol": self.symbol,
            "base_asset": self.base_asset,
            "quote_asset": self.quote_asset,
            "min_quantity": self.min_quantity,
            "max_quantity": self.max_quantity,
            "step_size": self.step_size,
            "min_notional": self.min_notional,
            "tick_size": self.tick_size,
            "status": self.status
        }


# ============================================================================
# ABSTRACT BASE CLASS - BaseBroker
# ============================================================================

class BaseBroker(ABC):
    """
    Abstract base class for all broker implementations (live and paper).
    
    Services (BotEngine, AIAgent, LongTermManager) use ONLY this interface.
    Each broker implementation (Binance, Paper, Kraken) inherits from this
    and implements all abstract methods.
    
    This ensures:
    1. Unified interface regardless of exchange
    2. Easy switching between paper/live/testnet
    3. Easy addition of new exchanges
    """
    
    # ========================================================================
    # IDENTIFICATION
    # ========================================================================
    
    @property
    @abstractmethod
    def name(self) -> str:
        """
        Broker name identifier.
        Examples: 'binance', 'binance_testnet', 'paper', 'kraken'
        """
        pass
    
    @property
    @abstractmethod
    def is_paper(self) -> bool:
        """True if this is a paper/simulated broker, False if live"""
        pass
    
    # ========================================================================
    # MARKET DATA
    # ========================================================================
    
    @abstractmethod
    async def get_candles(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 100
    ) -> List[Candle]:
        """
        Fetch OHLCV candles for a symbol.
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            interval: Time interval (e.g., '1m', '5m', '1h', '1d')
            limit: Number of candles to fetch
            
        Returns:
            List of Candle objects, ordered oldest to newest
            
        Raises:
            Exception: If symbol not found or API error
        """
        pass
    
    @abstractmethod
    async def get_ticker(self, symbol: str) -> Ticker:
        """
        Fetch 24h ticker for a symbol.
        
        Args:
            symbol: Trading pair
            
        Returns:
            Ticker object with latest 24h data
            
        Raises:
            Exception: If symbol not found or API error
        """
        pass
    
    @abstractmethod
    async def get_latest_price(self, symbol: str) -> float:
        """
        Get the latest price for a symbol (convenience method).
        
        Args:
            symbol: Trading pair
            
        Returns:
            Float price in quote asset
            
        Raises:
            Exception: If symbol not found or API error
        """
        pass
    
    # ========================================================================
    # ORDERS
    # ========================================================================
    
    @abstractmethod
    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[float] = None
    ) -> OrderResult:
        """
        Place a new order.
        
        Args:
            symbol: Trading pair
            side: BUY or SELL
            quantity: Amount to trade
            order_type: MARKET, LIMIT, STOP_LOSS, or STOP_LIMIT
            price: Required for LIMIT/STOP_LIMIT, optional for MARKET
            
        Returns:
            OrderResult with execution details
            
        Raises:
            Exception: If order fails (insufficient balance, invalid params, etc.)
        """
        pass
    
    @abstractmethod
    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """
        Cancel an open order.
        
        Args:
            symbol: Trading pair
            order_id: Order ID to cancel
            
        Returns:
            True if cancelled successfully, False if already executed/not found
            
        Raises:
            Exception: If API error
        """
        pass
    
    @abstractmethod
    async def get_order_status(self, symbol: str, order_id: str) -> OrderResult:
        """
        Get the status of an existing order.
        
        Args:
            symbol: Trading pair
            order_id: Order ID to check
            
        Returns:
            OrderResult with current status
            
        Raises:
            Exception: If order not found or API error
        """
        pass
    
    # ========================================================================
    # ACCOUNT
    # ========================================================================
    
    @abstractmethod
    async def get_account_balance(self) -> AccountBalance:
        """
        Fetch current account balance and portfolio value.
        
        Returns:
            AccountBalance with all assets and values
            
        Raises:
            Exception: If API error or not authenticated
        """
        pass
    
    # ========================================================================
    # SYMBOL INFO & VALIDATION
    # ========================================================================
    
    @abstractmethod
    async def get_symbol_info(self, symbol: str) -> SymbolInfo:
        """
        Get trading constraints for a symbol.
        
        Args:
            symbol: Trading pair
            
        Returns:
            SymbolInfo with min/max quantities, price precision, etc.
            
        Raises:
            Exception: If symbol not found or API error
        """
        pass
    
    @abstractmethod
    def normalize_symbol(self, symbol: str) -> str:
        """
        Normalize a symbol to the broker's format.
        
        Each broker has different symbol formats:
        - Binance: BTCUSDT (no separator)
        - Kraken: XBT/USD (with separator)
        - Coinbase: BTC-USD (with dash)
        
        This method converts internal format (BTCUSDT) to broker format.
        
        Args:
            symbol: Symbol to normalize
            
        Returns:
            Normalized symbol for this broker
        """
        pass
    
    @abstractmethod
    def get_supported_intervals(self) -> List[str]:
        """
        Get list of supported timeframes/intervals for this broker.
        
        Returns:
            List of interval strings (e.g., ['1m', '5m', '15m', '1h', '4h', '1d'])
        """
        pass

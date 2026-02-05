"""
TradingLimitsGuard - Middleware for enforcing trading limits.

Wraps a broker and validates all trades against ExchangeConfig limits BEFORE execution:
- max_trade_size: Maximum position size in quote currency
- max_daily_trades: Maximum number of trades per day
- allowed_symbols: Whitelist of tradable symbols (if defined)

Usage:
    broker = BrokerFactory.from_user(user_id, db)
    guarded_broker = TradingLimitsGuard(broker, user_id, db_session_factory)
    
    # All trades automatically validated
    result = await guarded_broker.place_order(...)
"""

import json
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

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

logger = logging.getLogger(__name__)


class TradingLimitViolation(Exception):
    """Raised when a trade violates configured limits"""
    pass


class TradingLimitsGuard(BaseBroker):
    """
    Broker wrapper that enforces trading limits from ExchangeConfig.
    
    Acts as a transparent proxy for all market data methods,
    but validates place_order() against user-configured limits.
    """
    
    def __init__(
        self,
        upstream_broker: BaseBroker,
        user_id: str,
        db_session_factory,
        config_id: Optional[str] = None
    ):
        """
        Initialize TradingLimitsGuard.
        
        Args:
            upstream_broker: The actual broker to wrap
            user_id: User ID for loading limits
            db_session_factory: Factory for database sessions
            config_id: Optional specific ExchangeConfig ID (if None, loads default)
        """
        self.upstream = upstream_broker
        self.user_id = user_id
        self.db_session_factory = db_session_factory
        self.config_id = config_id
        
        # Cache limits (loaded on first trade)
        self._limits_loaded = False
        self._max_trade_size = None
        self._max_daily_trades = None
        self._allowed_symbols = None
    
    def _load_limits(self, db: Session):
        """
        Load trading limits from ExchangeConfig.
        
        Args:
            db: Database session
        """
        if self._limits_loaded:
            return
        
        from app.models.database_models import ExchangeConfig
        
        try:
            # Load config
            if self.config_id:
                config = db.query(ExchangeConfig).filter(
                    ExchangeConfig.id == self.config_id
                ).first()
            else:
                # Load default or first active config
                config = db.query(ExchangeConfig).filter(
                    ExchangeConfig.user_id == self.user_id,
                    ExchangeConfig.is_active == True
                ).order_by(ExchangeConfig.is_default.desc()).first()
            
            if config:
                self._max_trade_size = config.max_trade_size
                self._max_daily_trades = config.max_daily_trades
                
                # Parse allowed_symbols JSON
                if config.allowed_symbols:
                    try:
                        self._allowed_symbols = json.loads(config.allowed_symbols)
                    except:
                        self._allowed_symbols = None
                
                logger.info(f"🛡️ Loaded limits for user {self.user_id}: "
                           f"max_size=${self._max_trade_size}, "
                           f"max_daily={self._max_daily_trades}, "
                           f"symbols={len(self._allowed_symbols) if self._allowed_symbols else 'all'}")
            else:
                logger.warning(f"⚠️ No ExchangeConfig found for user {self.user_id} - no limits enforced")
            
            self._limits_loaded = True
            
        except Exception as e:
            logger.error(f"❌ Failed to load trading limits: {e}")
            self._limits_loaded = True  # Don't retry on every trade
    
    def _validate_trade_size(self, symbol: str, quantity: float, price: Optional[float]):
        """
        Validate trade size against max_trade_size.
        
        Args:
            symbol: Trading symbol
            quantity: Order quantity
            price: Order price (None for MARKET orders)
            
        Raises:
            TradingLimitViolation: If trade size exceeds limit
        """
        if self._max_trade_size is None:
            return
        
        # Estimate trade value
        if price:
            trade_value = quantity * price
        else:
            # For MARKET orders, we'd need current price from broker
            logger.warning(f"⚠️ Cannot validate MARKET order size without price - skipping size check")
            return
        
        if trade_value > self._max_trade_size:
            raise TradingLimitViolation(
                f"Trade value ${trade_value:.2f} exceeds max_trade_size ${self._max_trade_size:.2f} "
                f"(symbol={symbol}, qty={quantity}, price={price})"
            )
        
        logger.debug(f"✅ Trade size ${trade_value:.2f} within limit ${self._max_trade_size:.2f}")
    
    def _validate_symbol(self, symbol: str):
        """
        Validate symbol against allowed_symbols whitelist.
        
        Args:
            symbol: Trading symbol
            
        Raises:
            TradingLimitViolation: If symbol not in whitelist
        """
        if self._allowed_symbols is None:
            return  # No whitelist = all symbols allowed
        
        # Normalize symbol for comparison (remove slashes, uppercase)
        normalized = symbol.replace("/", "").replace("-", "").upper()
        
        # Check if symbol in whitelist (try both formats)
        allowed = False
        for allowed_sym in self._allowed_symbols:
            allowed_norm = allowed_sym.replace("/", "").replace("-", "").upper()
            if normalized == allowed_norm:
                allowed = True
                break
        
        if not allowed:
            raise TradingLimitViolation(
                f"Symbol {symbol} not in allowed_symbols whitelist: {self._allowed_symbols}"
            )
        
        logger.debug(f"✅ Symbol {symbol} in whitelist")
    
    def _validate_daily_trades(self, db: Session):
        """
        Validate daily trade count against max_daily_trades.
        
        Args:
            db: Database session
            
        Raises:
            TradingLimitViolation: If daily limit reached
        """
        if self._max_daily_trades is None:
            return
        
        from app.models.database_models import Trade
        
        # Count trades created TODAY (UTC)
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        daily_count = db.query(func.count(Trade.id)).filter(
            Trade.user_id == self.user_id,
            Trade.entry_time >= today_start
        ).scalar()
        
        if daily_count >= self._max_daily_trades:
            raise TradingLimitViolation(
                f"Daily trade limit reached: {daily_count}/{self._max_daily_trades} trades today"
            )
        
        logger.debug(f"✅ Daily trades: {daily_count}/{self._max_daily_trades}")
    
    # ========================================================================
    # IDENTIFICATION (Proxy to upstream)
    # ========================================================================
    
    @property
    def name(self) -> str:
        return f"{self.upstream.name}_guarded"
    
    @property
    def is_paper(self) -> bool:
        return self.upstream.is_paper
    
    # ========================================================================
    # MARKET DATA (Proxy to upstream - no validation needed)
    # ========================================================================
    
    async def get_candles(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 100
    ) -> List[Candle]:
        """Proxy to upstream broker"""
        return await self.upstream.get_candles(symbol, interval, limit)
    
    async def get_ticker(self, symbol: str) -> Ticker:
        """Proxy to upstream broker"""
        return await self.upstream.get_ticker(symbol)
    
    async def get_latest_price(self, symbol: str) -> float:
        """Proxy to upstream broker"""
        return await self.upstream.get_latest_price(symbol)
    
    # ========================================================================
    # ORDER EXECUTION (WITH VALIDATION)
    # ========================================================================
    
    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: str = "GTC"
    ) -> OrderResult:
        """
        Place order with validation against trading limits.
        
        Validates:
        1. Trade size <= max_trade_size
        2. Symbol in allowed_symbols (if defined)
        3. Daily trades < max_daily_trades
        
        Args:
            symbol: Trading pair (e.g., BTCUSDT)
            side: BUY or SELL
            order_type: MARKET, LIMIT, STOP_LOSS, etc.
            quantity: Order quantity in base currency
            price: Limit price (required for LIMIT orders)
            stop_price: Stop price (required for STOP_LOSS orders)
            time_in_force: GTC, IOC, FOK
            
        Returns:
            OrderResult with order details
            
        Raises:
            TradingLimitViolation: If any limit violated
        """
        db = self.db_session_factory()
        try:
            # Load limits on first trade
            self._load_limits(db)
            
            # ✅ VALIDATION 1: Trade size
            self._validate_trade_size(symbol, quantity, price)
            
            # ✅ VALIDATION 2: Symbol whitelist
            self._validate_symbol(symbol)
            
            # ✅ VALIDATION 3: Daily trade count
            self._validate_daily_trades(db)
            
            # All checks passed - execute trade
            logger.info(f"🛡️ Trade validated - executing: {side.value} {quantity} {symbol}")
            return await self.upstream.place_order(
                symbol, side, order_type, quantity, price, stop_price, time_in_force
            )
            
        except TradingLimitViolation:
            logger.warning(f"🚫 Trade blocked by TradingLimitsGuard: {symbol} {side.value} {quantity}")
            raise
        finally:
            db.close()
    
    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """Proxy to upstream broker (no validation needed for cancels)"""
        return await self.upstream.cancel_order(symbol, order_id)
    
    async def get_order_status(self, symbol: str, order_id: str) -> OrderStatus:
        """Proxy to upstream broker"""
        return await self.upstream.get_order_status(symbol, order_id)
    
    # ========================================================================
    # ACCOUNT INFO (Proxy to upstream)
    # ========================================================================
    
    async def get_account_balance(self) -> AccountBalance:
        """Proxy to upstream broker"""
        return await self.upstream.get_account_balance()
    
    async def get_symbol_info(self, symbol: str) -> SymbolInfo:
        """Proxy to upstream broker"""
        return await self.upstream.get_symbol_info(symbol)

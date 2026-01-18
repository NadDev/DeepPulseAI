"""
Risk Manager - Centralized Trade Validation
Validates trades before execution for both Bot Engine and AI Agent
"""
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.database_models import Trade, Portfolio, Bot

logger = logging.getLogger(__name__)


# ============================================================================
# HARDCODED LIMITS (Cannot be changed by users - safety net)
# ============================================================================
ABSOLUTE_MAX_POSITION_PCT = 25.0      # Never more than 25% per trade
ABSOLUTE_MAX_DAILY_TRADES = 100       # Max 100 trades/day
ABSOLUTE_MIN_CASH_BUFFER = 50.0       # Always keep $50 minimum
ABSOLUTE_MAX_OPEN_POSITIONS = 50      # Never more than 50 open positions


# ============================================================================
# DEFAULT LIMITS (Applied to all users)
# ============================================================================
@dataclass
class RiskLimits:
    """Default risk limits for all users"""
    max_position_size_pct: float = 10.0     # Max 10% of portfolio per trade
    max_open_positions: int = 15            # Max 15 open positions
    max_daily_trades: int = 30              # Max 30 trades per day
    max_drawdown_pct: float = 20.0          # Stop if drawdown > 20%
    min_cash_buffer: float = 100.0          # Keep $100 minimum
    min_confidence: int = 65                # Min 65% confidence for AI trades
    no_duplicate_symbols: bool = True       # Only 1 position per symbol per source
    slippage_buffer_pct: float = 5.0        # 5% buffer for slippage


@dataclass  
class AITradeConfig:
    """Configuration for AI-initiated trades"""
    # Position Sizing
    position_size_pct: float = 5.0          # 5% of portfolio per AI trade
    
    # Stop Loss Configuration
    sl_method: str = "FIXED_PCT"            # "ATR", "FIXED_PCT" - Changed to FIXED_PCT as primary
    sl_atr_multiplier: float = 2.0          # 2 × ATR below entry
    sl_fixed_pct: float = 2.0               # -2.0% if fixed (FIXED from 3.0 to prevent SL=Entry on small prices)
    sl_min_distance: float = 0.01           # Minimum absolute SL distance ($0.01) to handle micro-prices
    
    # Take Profit Configuration  
    tp_method: str = "FIXED_PCT"            # "ATR", "FIXED_PCT", "NONE" - Changed to FIXED_PCT as primary
    tp_atr_multiplier: float = 3.0          # 3 × ATR above entry (1:1.5 R:R)
    tp_fixed_pct: float = 4.0               # +4% if fixed (adjusted to maintain 2:1 R:R ratio)
    
    # Minimum Risk:Reward ratio
    min_risk_reward: float = 1.5            # Reject if R:R < 1.5


@dataclass
class RiskValidation:
    """Result of trade validation"""
    allowed: bool
    reason: str
    adjusted_amount: Optional[float] = None  # Vol-adjusted position size
    warnings: List[str] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class RiskManager:
    """
    Centralized Risk Manager for trade validation
    Used by both Bot Engine and AI Agent
    """
    
    def __init__(self, db_session_factory=None):
        self.db_session_factory = db_session_factory or get_db
        self.limits = RiskLimits()
        self.ai_config = AITradeConfig()
    
    async def validate_trade(
        self,
        user_id: UUID,
        symbol: str,
        side: str,
        entry_price: float,
        source: str,  # "BOT", "AI_AGENT", "MANUAL"
        confidence: Optional[int] = None,
        bot_id: Optional[UUID] = None,
        market_data: Optional[Dict[str, Any]] = None
    ) -> RiskValidation:
        """
        Validate a proposed trade against all risk rules
        
        Args:
            user_id: User's UUID
            symbol: Trading pair (e.g., "BTCUSDT")
            side: "BUY" or "SELL"
            entry_price: Proposed entry price
            source: Trade source ("BOT", "AI_AGENT", "MANUAL")
            confidence: AI confidence (required for AI_AGENT)
            bot_id: Bot ID (required for BOT source)
            market_data: Market data with indicators (for ATR calculation)
            
        Returns:
            RiskValidation with allowed status and details
        """
        db = self.db_session_factory()
        warnings = []
        
        try:
            # ================================================================
            # 1. Get Portfolio
            # ================================================================
            portfolio = db.query(Portfolio).filter(
                Portfolio.user_id == user_id
            ).first()
            
            if not portfolio:
                return RiskValidation(
                    allowed=False,
                    reason="Portfolio not found"
                )
            
            cash_balance = float(portfolio.cash_balance)
            total_value = float(portfolio.total_value) if portfolio.total_value else cash_balance
            
            # ================================================================
            # 2. SELL Validation (simpler path)
            # ================================================================
            if side == "SELL":
                return await self._validate_sell(
                    db, user_id, symbol, source, bot_id
                )
            
            # ================================================================
            # 3. BUY Validation - Check all rules
            # ================================================================
            
            # 3.1 Minimum Cash Buffer
            effective_min_buffer = max(self.limits.min_cash_buffer, ABSOLUTE_MIN_CASH_BUFFER)
            if cash_balance < effective_min_buffer:
                return RiskValidation(
                    allowed=False,
                    reason=f"Cash balance ${cash_balance:.2f} below minimum ${effective_min_buffer:.2f}"
                )
            
            # 3.2 AI Confidence Check (for AI trades)
            if source == "AI_AGENT":
                if confidence is None:
                    return RiskValidation(
                        allowed=False,
                        reason="AI confidence required for AI trades"
                    )
                if confidence < self.limits.min_confidence:
                    return RiskValidation(
                        allowed=False,
                        reason=f"AI confidence {confidence}% below minimum {self.limits.min_confidence}%"
                    )
            
            # 3.3 Check Duplicate Positions
            if self.limits.no_duplicate_symbols:
                duplicate = await self._check_duplicate_position(
                    db, user_id, symbol, source, bot_id
                )
                if duplicate:
                    return RiskValidation(
                        allowed=False,
                        reason=f"Already have open position for {symbol}"
                    )
            
            # 3.4 Max Open Positions
            open_positions_count = await self._count_open_positions(db, user_id, source, bot_id)
            max_positions = min(self.limits.max_open_positions, ABSOLUTE_MAX_OPEN_POSITIONS)
            if open_positions_count >= max_positions:
                return RiskValidation(
                    allowed=False,
                    reason=f"Max open positions reached ({open_positions_count}/{max_positions})"
                )
            
            # 3.5 Daily Trade Limit
            daily_trades = await self._count_daily_trades(db, user_id, source)
            max_daily = min(self.limits.max_daily_trades, ABSOLUTE_MAX_DAILY_TRADES)
            if daily_trades >= max_daily:
                return RiskValidation(
                    allowed=False,
                    reason=f"Daily trade limit reached ({daily_trades}/{max_daily})"
                )
            
            # 3.6 Drawdown Check
            drawdown = await self._calculate_current_drawdown(db, user_id, portfolio)
            if drawdown > self.limits.max_drawdown_pct:
                return RiskValidation(
                    allowed=False,
                    reason=f"Max drawdown exceeded ({drawdown:.1f}% > {self.limits.max_drawdown_pct}%)"
                )
            elif drawdown > self.limits.max_drawdown_pct * 0.8:
                warnings.append(f"Approaching max drawdown ({drawdown:.1f}%)")
            
            # ================================================================
            # 4. Calculate Position Size
            # ================================================================
            position_size_pct = self.ai_config.position_size_pct if source == "AI_AGENT" else self.limits.max_position_size_pct
            position_size_pct = min(position_size_pct, ABSOLUTE_MAX_POSITION_PCT)
            
            position_value = total_value * (position_size_pct / 100)
            
            # Add slippage buffer
            slippage_buffer = position_value * (self.limits.slippage_buffer_pct / 100)
            total_required = position_value + slippage_buffer
            
            # Check if enough cash
            available_cash = cash_balance - effective_min_buffer
            if total_required > available_cash:
                # Adjust position size to fit
                adjusted_value = available_cash * 0.95  # 95% of available
                if adjusted_value < 10:  # Minimum $10 trade
                    return RiskValidation(
                        allowed=False,
                        reason=f"Insufficient funds: need ${total_required:.2f}, have ${available_cash:.2f}"
                    )
                position_value = adjusted_value
                warnings.append(f"Position reduced to ${position_value:.2f} due to balance")
            
            # ================================================================
            # 5. Calculate SL/TP (for AI trades)
            # ================================================================
            stop_loss = None
            take_profit = None
            
            if source == "AI_AGENT":
                sl_tp = self._calculate_sl_tp(entry_price, market_data)
                stop_loss = sl_tp["stop_loss"]
                take_profit = sl_tp["take_profit"]
                
                # Check Risk:Reward ratio
                if stop_loss and take_profit:
                    risk = entry_price - stop_loss
                    reward = take_profit - entry_price
                    if risk > 0:
                        rr_ratio = reward / risk
                        if rr_ratio < self.ai_config.min_risk_reward:
                            return RiskValidation(
                                allowed=False,
                                reason=f"Risk:Reward {rr_ratio:.2f} below minimum {self.ai_config.min_risk_reward}"
                            )
            
            # ================================================================
            # 6. All checks passed
            # ================================================================
            quantity = position_value / entry_price
            
            logger.info(f"✅ [RISK] {source} {symbol} BUY validated: "
                       f"${position_value:.2f} ({position_size_pct:.1f}%), "
                       f"SL: {stop_loss}, TP: {take_profit}")
            
            return RiskValidation(
                allowed=True,
                reason="All risk checks passed",
                adjusted_amount=quantity,
                warnings=warnings,
                stop_loss=stop_loss,
                take_profit=take_profit
            )
            
        except Exception as e:
            logger.error(f"❌ [RISK] Validation error: {str(e)}")
            return RiskValidation(
                allowed=False,
                reason=f"Validation error: {str(e)}"
            )
        finally:
            db.close()
    
    async def _validate_sell(
        self,
        db: Session,
        user_id: UUID,
        symbol: str,
        source: str,
        bot_id: Optional[UUID]
    ) -> RiskValidation:
        """Validate a SELL order"""
        
        # For BOT source, check bot's own position
        if source == "BOT" and bot_id:
            open_position = db.query(Trade).filter(
                Trade.bot_id == bot_id,
                Trade.symbol == symbol,
                Trade.status == "OPEN",
                Trade.side == "BUY"
            ).first()
        else:
            # For AI_AGENT, check any AI position for this symbol
            open_position = db.query(Trade).filter(
                Trade.user_id == user_id,
                Trade.symbol == symbol,
                Trade.status == "OPEN",
                Trade.side == "BUY"
            ).first()
        
        if not open_position:
            return RiskValidation(
                allowed=False,
                reason=f"No open position to sell for {symbol}"
            )
        
        return RiskValidation(
            allowed=True,
            reason="Position found to close"
        )
    
    async def _check_duplicate_position(
        self,
        db: Session,
        user_id: UUID,
        symbol: str,
        source: str,
        bot_id: Optional[UUID]
    ) -> bool:
        """
        Check if duplicate position exists.
        Only checks OPEN positions (CLOSED/CANCELLED are finalized).
        """
        
        if source == "BOT" and bot_id:
            # Bot checks its own positions only
            existing = db.query(Trade).filter(
                Trade.bot_id == bot_id,
                Trade.symbol == symbol,
                Trade.status == "OPEN",
                Trade.side == "BUY"
            ).first()
            if existing:
                logger.info(f"🚫 [DUP-CHECK-BOT] {symbol}: Found existing {existing.status} position (trade_id={existing.id})")
        elif source == "AI_AGENT":
            # AI Agent checks all AI positions for user
            existing = db.query(Trade).filter(
                Trade.user_id == user_id,
                Trade.symbol == symbol,
                Trade.status == "OPEN",
                Trade.strategy == "AI_AGENT"
            ).first()
            if existing:
                logger.info(f"🚫 [DUP-CHECK-AI] {symbol}: Found existing {existing.status} AI position (trade_id={existing.id})")
        else:
            # Manual checks all positions for user
            existing = db.query(Trade).filter(
                Trade.user_id == user_id,
                Trade.symbol == symbol,
                Trade.status == "OPEN"
            ).first()
            if existing:
                logger.info(f"🚫 [DUP-CHECK-MANUAL] {symbol}: Found existing {existing.status} position (trade_id={existing.id})")
        
        return existing is not None
    
    async def _count_open_positions(
        self,
        db: Session,
        user_id: UUID,
        source: str,
        bot_id: Optional[UUID]
    ) -> int:
        """Count open positions"""
        
        if source == "BOT" and bot_id:
            return db.query(Trade).filter(
                Trade.bot_id == bot_id,
                Trade.status == "OPEN"
            ).count()
        else:
            # Count all user's positions for AI/Manual
            return db.query(Trade).filter(
                Trade.user_id == user_id,
                Trade.status == "OPEN"
            ).count()
    
    async def _count_daily_trades(
        self,
        db: Session,
        user_id: UUID,
        source: str
    ) -> int:
        """Count trades executed today"""
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        query = db.query(Trade).filter(
            Trade.user_id == user_id,
            Trade.entry_time >= today_start
        )
        
        if source == "AI_AGENT":
            query = query.filter(Trade.strategy == "AI_AGENT")
        
        return query.count()
    
    async def _calculate_current_drawdown(
        self,
        db: Session,
        user_id: UUID,
        portfolio: Portfolio
    ) -> float:
        """Calculate current drawdown percentage"""
        
        # Get initial capital (hardcoded for now, TODO: make configurable)
        initial_capital = 100000.0
        
        current_value = float(portfolio.total_value) if portfolio.total_value else float(portfolio.cash_balance)
        
        # Simple drawdown: (initial - current) / initial * 100
        if current_value >= initial_capital:
            return 0.0
        
        drawdown = ((initial_capital - current_value) / initial_capital) * 100
        return round(drawdown, 2)
    
    def _calculate_sl_tp(
        self,
        entry_price: float,
        market_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Optional[float]]:
        """Calculate Stop Loss and Take Profit levels with proper validation"""
        
        atr = None
        if market_data and 'indicators' in market_data:
            atr = market_data['indicators'].get('atr')
        
        stop_loss = None
        take_profit = None
        
        # ===== STOP LOSS CALCULATION =====
        # Bug Fix #1: Changed primary method to FIXED_PCT to avoid ATR edge cases
        if self.ai_config.sl_method == "ATR" and atr and atr > 0:
            stop_loss = entry_price - (atr * self.ai_config.sl_atr_multiplier)
        else:
            # Primary: Fixed percentage calculation
            stop_loss = entry_price * (1 - self.ai_config.sl_fixed_pct / 100)
        
        # Bug Fix #2: Enforce minimum SL distance for small-price assets (e.g., WALUSDT=$0.16)
        # Without this, 2% SL on $0.16 = $0.1568, which rounds to $0.16 = entry price
        min_sl = entry_price - self.ai_config.sl_min_distance
        if stop_loss and stop_loss > min_sl:
            # SL is too close to entry, enforce minimum distance
            stop_loss = min_sl
        
        # Bug Fix #3: Validate SL is not equal to entry price (would close immediately)
        if stop_loss and abs(stop_loss - entry_price) < 0.0001:  # Accounting for float precision
            logger.warning(f"⚠️ SL too close to Entry (diff < $0.0001), applying minimum distance")
            stop_loss = entry_price - self.ai_config.sl_min_distance
        
        # ===== TAKE PROFIT CALCULATION =====
        if self.ai_config.tp_method == "NONE":
            take_profit = None
        elif self.ai_config.tp_method == "ATR" and atr and atr > 0:
            take_profit = entry_price + (atr * self.ai_config.tp_atr_multiplier)
        else:
            # Primary: Fixed percentage calculation
            take_profit = entry_price * (1 + self.ai_config.tp_fixed_pct / 100)
        
        # Round to 8 decimals (max crypto precision)
        sl_rounded = round(stop_loss, 8) if stop_loss else None
        tp_rounded = round(take_profit, 8) if take_profit else None
        
        logger.info(f"📊 SL/TP Calculation: Entry=${entry_price:.8f} | SL=${sl_rounded} (offset: ${entry_price - sl_rounded if sl_rounded else 'N/A'}) | TP=${tp_rounded}")
        
        return {
            "stop_loss": sl_rounded,
            "take_profit": tp_rounded
        }
    
    def get_trade_parameters(
        self,
        entry_price: float,
        market_data: Optional[Dict[str, Any]],
        portfolio_value: float
    ) -> Dict[str, Any]:
        """
        Get all trade parameters for AI Agent
        
        Returns:
            {
                "position_size": float (quantity),
                "position_value": float ($),
                "stop_loss": float,
                "take_profit": float,
                "risk_amount": float ($)
            }
        """
        # Position size
        position_value = portfolio_value * (self.ai_config.position_size_pct / 100)
        quantity = position_value / entry_price
        
        # SL/TP
        sl_tp = self._calculate_sl_tp(entry_price, market_data)
        
        # Risk amount (what we lose if SL hit)
        risk_per_unit = entry_price - sl_tp["stop_loss"] if sl_tp["stop_loss"] else entry_price * 0.03
        risk_amount = quantity * risk_per_unit
        
        return {
            "position_size": round(quantity, 8),
            "position_value": round(position_value, 2),
            "stop_loss": sl_tp["stop_loss"],
            "take_profit": sl_tp["take_profit"],
            "risk_amount": round(risk_amount, 2)
        }


# Singleton instance
_risk_manager: Optional[RiskManager] = None

def get_risk_manager() -> RiskManager:
    """Get or create RiskManager singleton"""
    global _risk_manager
    if _risk_manager is None:
        _risk_manager = RiskManager()
    return _risk_manager

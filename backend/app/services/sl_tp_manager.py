"""
SL/TP Manager - Intelligent Stop Loss and Take Profit Management
================================================================

This module provides intelligent SL/TP calculation and management based on:
1. Technical invalidation points (ATR, structure levels)
2. User-defined risk profiles (PRUDENT, BALANCED, AGGRESSIVE)
3. Dynamic trailing stops
4. Trade phases (PENDING → VALIDATED → TRAILING)
5. Fractional take profit (partial exits)

Designed to integrate with:
- BotEngine (current)
- AIAgent (current)
- TradeExecutionService (future)

Author: CRBot Team
Date: January 18, 2026
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Tuple, List
from enum import Enum
from uuid import UUID
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


# ============================================
# Enums
# ============================================

class SLMethod(Enum):
    """Stop Loss calculation methods"""
    ATR = "ATR"              # Based on Average True Range
    STRUCTURE = "STRUCTURE"  # Based on swing high/low
    FIXED_PCT = "FIXED_PCT"  # Fixed percentage
    HYBRID = "HYBRID"        # Combines ATR + Structure


class TradePhase(Enum):
    """Trade lifecycle phases"""
    PENDING = "PENDING"      # Just opened, SL at invalidation point
    VALIDATED = "VALIDATED"  # Moved in our favor, SL at breakeven
    TRAILING = "TRAILING"    # Profit protected, trailing SL active


class ExitReason(Enum):
    """Why the trade was closed"""
    SL_HIT = "SL_HIT"                    # Stop loss triggered
    TP_FULL = "TP_FULL"                  # Full take profit hit
    TP_PARTIAL = "TP_PARTIAL"            # Partial take profit hit
    TRAILING_SL = "TRAILING_SL"          # Trailing stop triggered
    SIGNAL = "SIGNAL"                    # Strategy signal (SELL)
    TIME_OUT = "TIME_OUT"                # Max holding time exceeded
    MANUAL = "MANUAL"                    # User closed manually
    INVALIDATION = "INVALIDATION"        # Technical invalidation (non-price)


# ============================================
# Data Classes
# ============================================

@dataclass
class SLTPConfig:
    """Configuration for a trade's SL/TP"""
    # Stop Loss
    stop_loss: float
    sl_method: SLMethod
    sl_initial: float              # Original SL (never changes)
    sl_current: float              # Current SL (may be trailed)
    sl_distance_pct: float         # Distance from entry in %
    
    # Take Profit
    take_profit_1: float           # Partial TP (e.g., 50% exit)
    take_profit_2: Optional[float] # Runner TP (remaining position)
    tp1_exit_pct: float           # % of position to exit at TP1
    
    # Validation
    validation_price: Optional[float] = None  # Price to move to breakeven
    
    # Risk/Reward
    risk_amount: float = 0.0       # $ at risk
    reward_1: float = 0.0          # $ potential at TP1
    reward_2: float = 0.0          # $ potential at TP2
    risk_reward_1: float = 0.0     # R:R ratio for TP1
    risk_reward_2: float = 0.0     # R:R ratio for TP2


@dataclass
class TradeState:
    """Current state of an active trade"""
    trade_id: str
    symbol: str
    side: str                      # BUY or SELL
    entry_price: float
    quantity: float
    
    # SL/TP
    sl_initial: float
    sl_current: float
    tp1: float
    tp2: Optional[float]
    tp1_exit_pct: float
    
    # Phase
    phase: TradePhase = TradePhase.PENDING
    validation_price: Optional[float] = None
    validated_at: Optional[datetime] = None
    
    # Partial exits
    tp1_hit: bool = False
    tp1_hit_at: Optional[datetime] = None
    quantity_remaining: Optional[float] = None
    
    # Trailing
    trailing_active: bool = False
    highest_price: Optional[float] = None  # For BUY trades
    lowest_price: Optional[float] = None   # For SELL trades


@dataclass
class TradeUpdate:
    """Result of updating a trade's SL/TP"""
    should_close: bool = False
    close_reason: Optional[ExitReason] = None
    close_quantity: Optional[float] = None  # For partial closes
    
    # Updates to apply
    new_sl: Optional[float] = None
    new_phase: Optional[TradePhase] = None
    new_highest_price: Optional[float] = None
    
    # Logging info
    log_message: str = ""


@dataclass  
class UserSLTPSettings:
    """User's SL/TP preferences (from database)"""
    sl_tp_profile: str = "BALANCED"
    sl_method: str = "ATR"
    sl_atr_multiplier: float = 1.5
    sl_fixed_pct: float = 2.5
    sl_min_distance: float = 0.01
    sl_max_pct: float = 5.0
    tp1_risk_reward: float = 1.5
    tp1_exit_pct: float = 50.0
    tp2_risk_reward: float = 3.0
    enable_trailing_sl: bool = True
    trailing_activation_pct: float = 1.5
    trailing_distance_pct: float = 1.0
    enable_trade_phases: bool = True
    validation_threshold_pct: float = 0.5
    move_sl_to_breakeven: bool = True
    enable_partial_tp: bool = True
    max_position_pct: float = 25.0


# ============================================
# SL/TP Manager Class
# ============================================

class SLTPManager:
    """
    Intelligent SL/TP calculation and management.
    
    Features:
    - ATR-based stop loss (adapts to volatility)
    - Structure-based stop loss (swing lows/highs)
    - Trade phases with automatic breakeven
    - Dynamic trailing stops
    - Fractional take profit
    
    Usage:
        manager = SLTPManager(market_data_service, technical_analysis)
        
        # At trade entry:
        sl_tp_config = await manager.calculate_sl_tp(
            user_id, symbol, entry_price, "BUY", market_data
        )
        
        # During monitoring loop:
        update = await manager.update_trade(
            trade_state, current_price, market_data, user_settings
        )
    """
    
    def __init__(self, market_data_service=None, technical_analysis=None, db_session_factory=None):
        """
        Initialize SL/TP Manager.
        
        Args:
            market_data_service: Service to fetch market data (for ATR calculation)
            technical_analysis: Service for technical indicators
            db_session_factory: Function to create DB sessions (for user settings)
        """
        self.market_data = market_data_service
        self.ta = technical_analysis
        self.db_session_factory = db_session_factory
    
    # ============================================
    # Public Methods - SL/TP Calculation
    # ============================================
    
    async def calculate_sl_tp(
        self,
        user_id: UUID,
        symbol: str,
        entry_price: float,
        side: str,
        market_data: Dict[str, Any],
        position_size: Optional[float] = None
    ) -> SLTPConfig:
        """
        Calculate intelligent SL/TP for a new trade.
        
        This is called at trade ENTRY to determine initial SL/TP levels.
        
        Args:
            user_id: User's UUID for fetching their settings
            symbol: Trading pair (e.g., BTCUSDT)
            entry_price: Entry price of the trade
            side: "BUY" or "SELL"
            market_data: Dict with indicators (support, resistance, ATR, etc.)
            position_size: Optional quantity (for risk calculation)
            
        Returns:
            SLTPConfig with calculated SL/TP levels
        """
        # 1. Get user settings
        settings = await self._get_user_settings(user_id)
        
        # 2. Calculate Stop Loss based on method
        sl_price, sl_method_used = await self._calculate_stop_loss(
            entry_price=entry_price,
            side=side,
            market_data=market_data,
            settings=settings
        )
        
        # 3. Calculate SL distance
        if side == "BUY":
            sl_distance = entry_price - sl_price
            sl_distance_pct = (sl_distance / entry_price) * 100
        else:  # SELL
            sl_distance = sl_price - entry_price
            sl_distance_pct = (sl_distance / entry_price) * 100
        
        # 4. Calculate Take Profits based on R:R
        tp1, tp2 = self._calculate_take_profits(
            entry_price=entry_price,
            sl_distance=sl_distance,
            side=side,
            settings=settings
        )
        
        # 5. Calculate validation price (for phase transition)
        validation_price = self._calculate_validation_price(
            entry_price=entry_price,
            side=side,
            settings=settings
        )
        
        # 6. Calculate risk amounts if position size provided
        risk_amount = 0.0
        reward_1 = 0.0
        reward_2 = 0.0
        
        if position_size:
            risk_amount = sl_distance * position_size
            if side == "BUY":
                reward_1 = (tp1 - entry_price) * position_size if tp1 else 0
                reward_2 = (tp2 - entry_price) * position_size if tp2 else 0
            else:
                reward_1 = (entry_price - tp1) * position_size if tp1 else 0
                reward_2 = (entry_price - tp2) * position_size if tp2 else 0
        
        config = SLTPConfig(
            stop_loss=sl_price,
            sl_method=sl_method_used,
            sl_initial=sl_price,
            sl_current=sl_price,
            sl_distance_pct=sl_distance_pct,
            take_profit_1=tp1,
            take_profit_2=tp2,
            tp1_exit_pct=settings.tp1_exit_pct,
            validation_price=validation_price,
            risk_amount=risk_amount,
            reward_1=reward_1,
            reward_2=reward_2,
            risk_reward_1=settings.tp1_risk_reward,
            risk_reward_2=settings.tp2_risk_reward
        )
        
        # Log the calculation
        logger.info(f"📊 [SLTP-CALC] {symbol} {side}")
        logger.info(f"├─ Entry: ${entry_price:.4f}")
        logger.info(f"├─ SL: ${sl_price:.4f} ({sl_method_used.value}) | -{sl_distance_pct:.2f}%")
        logger.info(f"├─ TP1: ${tp1:.4f} (R:R {settings.tp1_risk_reward}:1) | Exit {settings.tp1_exit_pct}%")
        if tp2:
            logger.info(f"├─ TP2: ${tp2:.4f} (R:R {settings.tp2_risk_reward}:1) | Runner")
        logger.info(f"└─ Validation: ${validation_price:.4f} (+{settings.validation_threshold_pct}%)")
        
        return config
    
    async def update_trade(
        self,
        trade_state: TradeState,
        current_price: float,
        market_data: Dict[str, Any],
        user_settings: Optional[UserSLTPSettings] = None
    ) -> TradeUpdate:
        """
        Update a trade's SL/TP based on current price.
        
        This is called in the monitoring loop to manage active trades.
        
        Args:
            trade_state: Current state of the trade
            current_price: Current market price
            market_data: Current market data with indicators
            user_settings: User's SL/TP settings (optional, will fetch if None)
            
        Returns:
            TradeUpdate with actions to take
        """
        update = TradeUpdate()
        side = trade_state.side
        symbol = trade_state.symbol
        
        # Get settings if not provided
        if user_settings is None:
            # For now, use defaults - in production, fetch from DB
            user_settings = UserSLTPSettings()
        
        # ============================================
        # 1. Check Stop Loss Hit
        # ============================================
        if side == "BUY" and current_price <= trade_state.sl_current:
            update.should_close = True
            update.close_reason = ExitReason.SL_HIT if trade_state.phase == TradePhase.PENDING else ExitReason.TRAILING_SL
            update.close_quantity = trade_state.quantity_remaining or trade_state.quantity
            update.log_message = f"🛑 [SL-HIT] {symbol} | ${current_price:.4f} ≤ SL ${trade_state.sl_current:.4f}"
            return update
        
        elif side == "SELL" and current_price >= trade_state.sl_current:
            update.should_close = True
            update.close_reason = ExitReason.SL_HIT if trade_state.phase == TradePhase.PENDING else ExitReason.TRAILING_SL
            update.close_quantity = trade_state.quantity_remaining or trade_state.quantity
            update.log_message = f"🛑 [SL-HIT] {symbol} | ${current_price:.4f} ≥ SL ${trade_state.sl_current:.4f}"
            return update
        
        # ============================================
        # 2. Check TP1 (Partial Take Profit)
        # ============================================
        if not trade_state.tp1_hit and user_settings.enable_partial_tp:
            if side == "BUY" and current_price >= trade_state.tp1:
                update.should_close = True
                update.close_reason = ExitReason.TP_PARTIAL
                update.close_quantity = trade_state.quantity * (trade_state.tp1_exit_pct / 100)
                update.log_message = f"💰 [TP1-HIT] {symbol} | ${current_price:.4f} ≥ TP1 ${trade_state.tp1:.4f} | Selling {trade_state.tp1_exit_pct}%"
                
                # Also update SL to TP1 level (lock in profit)
                update.new_sl = trade_state.tp1
                update.new_phase = TradePhase.TRAILING
                return update
            
            elif side == "SELL" and current_price <= trade_state.tp1:
                update.should_close = True
                update.close_reason = ExitReason.TP_PARTIAL
                update.close_quantity = trade_state.quantity * (trade_state.tp1_exit_pct / 100)
                update.log_message = f"💰 [TP1-HIT] {symbol} | ${current_price:.4f} ≤ TP1 ${trade_state.tp1:.4f} | Selling {trade_state.tp1_exit_pct}%"
                update.new_sl = trade_state.tp1
                update.new_phase = TradePhase.TRAILING
                return update
        
        # ============================================
        # 3. Check TP2 (Full Take Profit)
        # ============================================
        if trade_state.tp2:
            if side == "BUY" and current_price >= trade_state.tp2:
                update.should_close = True
                update.close_reason = ExitReason.TP_FULL
                update.close_quantity = trade_state.quantity_remaining or trade_state.quantity
                update.log_message = f"💎 [TP2-HIT] {symbol} | ${current_price:.4f} ≥ TP2 ${trade_state.tp2:.4f} | Full exit"
                return update
            
            elif side == "SELL" and current_price <= trade_state.tp2:
                update.should_close = True
                update.close_reason = ExitReason.TP_FULL
                update.close_quantity = trade_state.quantity_remaining or trade_state.quantity
                update.log_message = f"💎 [TP2-HIT] {symbol} | ${current_price:.4f} ≤ TP2 ${trade_state.tp2:.4f} | Full exit"
                return update
        
        # ============================================
        # 4. Phase Transition: PENDING → VALIDATED
        # ============================================
        if trade_state.phase == TradePhase.PENDING and user_settings.enable_trade_phases:
            if trade_state.validation_price:
                if side == "BUY" and current_price >= trade_state.validation_price:
                    update.new_phase = TradePhase.VALIDATED
                    if user_settings.move_sl_to_breakeven:
                        update.new_sl = trade_state.entry_price
                        update.log_message = f"✅ [VALIDATED] {symbol} | Price ${current_price:.4f} ≥ ${trade_state.validation_price:.4f} | SL → Breakeven ${trade_state.entry_price:.4f}"
                    else:
                        update.log_message = f"✅ [VALIDATED] {symbol} | Price ${current_price:.4f} ≥ ${trade_state.validation_price:.4f}"
                    return update
                
                elif side == "SELL" and current_price <= trade_state.validation_price:
                    update.new_phase = TradePhase.VALIDATED
                    if user_settings.move_sl_to_breakeven:
                        update.new_sl = trade_state.entry_price
                        update.log_message = f"✅ [VALIDATED] {symbol} | Price ${current_price:.4f} ≤ ${trade_state.validation_price:.4f} | SL → Breakeven ${trade_state.entry_price:.4f}"
                    else:
                        update.log_message = f"✅ [VALIDATED] {symbol} | Price ${current_price:.4f} ≤ ${trade_state.validation_price:.4f}"
                    return update
        
        # ============================================
        # 5. Trailing Stop Logic
        # ============================================
        if user_settings.enable_trailing_sl and trade_state.phase in [TradePhase.VALIDATED, TradePhase.TRAILING]:
            new_sl = self._calculate_trailing_sl(
                trade_state=trade_state,
                current_price=current_price,
                settings=user_settings
            )
            
            if new_sl and new_sl != trade_state.sl_current:
                update.new_sl = new_sl
                
                # Track highest/lowest for trailing
                if side == "BUY":
                    if trade_state.highest_price is None or current_price > trade_state.highest_price:
                        update.new_highest_price = current_price
                
                update.log_message = f"📈 [TRAIL-SL] {symbol} | SL: ${trade_state.sl_current:.4f} → ${new_sl:.4f}"
                
                if trade_state.phase != TradePhase.TRAILING:
                    update.new_phase = TradePhase.TRAILING
                
                return update
        
        # No updates needed
        return update
    
    # ============================================
    # Public Methods - Position Sizing
    # ============================================
    
    def calculate_position_size_from_sl(
        self,
        portfolio_value: float,
        entry_price: float,
        stop_loss: float,
        risk_percent: float = 2.0,
        max_position_pct: float = 25.0
    ) -> Tuple[float, float]:
        """
        Calculate position size based on SL distance (risk-first approach).
        
        Instead of: "I want to buy X amount, what's my risk?"
        We use: "I want to risk Y%, what position size does that allow?"
        
        Args:
            portfolio_value: Total portfolio value
            entry_price: Entry price
            stop_loss: Stop loss price
            risk_percent: Max % of portfolio to risk (e.g., 2%)
            max_position_pct: Max % of portfolio for single position
            
        Returns:
            Tuple of (quantity, cost)
        """
        # Calculate SL distance
        sl_distance = abs(entry_price - stop_loss)
        
        if sl_distance <= 0:
            logger.warning(f"⚠️ Invalid SL distance: {sl_distance}")
            return 0.0, 0.0
        
        # Max $ we're willing to risk
        max_risk = portfolio_value * (risk_percent / 100)
        
        # Position size = Max Risk / SL Distance
        quantity = max_risk / sl_distance
        cost = quantity * entry_price
        
        # Apply max position limit
        max_cost = portfolio_value * (max_position_pct / 100)
        if cost > max_cost:
            cost = max_cost
            quantity = cost / entry_price
            logger.info(f"📊 [POS-SIZE] Capped to {max_position_pct}% of portfolio: ${cost:.2f}")
        
        logger.info(f"📊 [POS-SIZE] Risk ${max_risk:.2f} ({risk_percent}%) | SL dist ${sl_distance:.4f} | Qty: {quantity:.6f} | Cost: ${cost:.2f}")
        
        return quantity, cost
    
    # ============================================
    # Private Methods - SL Calculation
    # ============================================
    
    async def _calculate_stop_loss(
        self,
        entry_price: float,
        side: str,
        market_data: Dict[str, Any],
        settings: UserSLTPSettings
    ) -> Tuple[float, SLMethod]:
        """
        Calculate stop loss based on user's preferred method.
        
        Returns:
            Tuple of (sl_price, method_used)
        """
        method = SLMethod(settings.sl_method)
        
        if method == SLMethod.ATR:
            sl_price = self._calculate_atr_sl(entry_price, side, market_data, settings)
            method_used = SLMethod.ATR
            
        elif method == SLMethod.STRUCTURE:
            sl_price = self._calculate_structure_sl(entry_price, side, market_data, settings)
            method_used = SLMethod.STRUCTURE
            
        elif method == SLMethod.FIXED_PCT:
            sl_price = self._calculate_fixed_pct_sl(entry_price, side, settings)
            method_used = SLMethod.FIXED_PCT
            
        elif method == SLMethod.HYBRID:
            # Use the tighter of ATR and Structure
            atr_sl = self._calculate_atr_sl(entry_price, side, market_data, settings)
            struct_sl = self._calculate_structure_sl(entry_price, side, market_data, settings)
            
            if side == "BUY":
                sl_price = max(atr_sl, struct_sl)  # Higher = tighter for BUY
            else:
                sl_price = min(atr_sl, struct_sl)  # Lower = tighter for SELL
            
            method_used = SLMethod.HYBRID
        else:
            # Fallback to fixed %
            sl_price = self._calculate_fixed_pct_sl(entry_price, side, settings)
            method_used = SLMethod.FIXED_PCT
        
        # Apply min/max constraints
        sl_price = self._apply_sl_constraints(entry_price, sl_price, side, settings)
        
        return sl_price, method_used
    
    def _calculate_atr_sl(
        self,
        entry_price: float,
        side: str,
        market_data: Dict[str, Any],
        settings: UserSLTPSettings
    ) -> float:
        """
        Calculate SL based on ATR (Average True Range).
        
        ATR adapts to volatility:
        - High volatility → wider SL
        - Low volatility → tighter SL
        """
        # Get ATR from market data or calculate
        indicators = market_data.get("indicators", {})
        atr = indicators.get("atr") or indicators.get("atr_14")
        
        if not atr:
            # Estimate ATR from high-low range if not available
            high = market_data.get("high", entry_price * 1.02)
            low = market_data.get("low", entry_price * 0.98)
            atr = abs(high - low) * 0.5  # Rough estimate
        
        # Validate ATR value (must be positive)
        if not atr or atr <= 0:
            # Fallback to fixed percentage if ATR is invalid
            return self._calculate_fixed_pct_sl(entry_price, side, settings)
        
        # SL distance = ATR * multiplier
        sl_distance = atr * settings.sl_atr_multiplier
        
        if side == "BUY":
            return entry_price - sl_distance
        else:  # SELL
            return entry_price + sl_distance
    
    def _calculate_structure_sl(
        self,
        entry_price: float,
        side: str,
        market_data: Dict[str, Any],
        settings: UserSLTPSettings
    ) -> float:
        """
        Calculate SL based on structure levels (support/resistance).
        
        For BUY: SL just below recent support
        For SELL: SL just above recent resistance
        """
        indicators = market_data.get("indicators", {})
        
        if side == "BUY":
            # Find support level
            support = indicators.get("support")
            if support:
                # Place SL slightly below support (0.5% buffer)
                return support * 0.995
            else:
                # Fallback to low of period
                low = market_data.get("low", entry_price * 0.98)
                return low * 0.995
        
        else:  # SELL
            # Find resistance level
            resistance = indicators.get("resistance")
            if resistance:
                # Place SL slightly above resistance
                return resistance * 1.005
            else:
                # Fallback to high of period
                high = market_data.get("high", entry_price * 1.02)
                return high * 1.005
    
    def _calculate_fixed_pct_sl(
        self,
        entry_price: float,
        side: str,
        settings: UserSLTPSettings
    ) -> float:
        """Calculate SL based on fixed percentage."""
        sl_pct = settings.sl_fixed_pct / 100
        
        if side == "BUY":
            return entry_price * (1 - sl_pct)
        else:
            return entry_price * (1 + sl_pct)
    
    def _apply_sl_constraints(
        self,
        entry_price: float,
        sl_price: float,
        side: str,
        settings: UserSLTPSettings
    ) -> float:
        """
        Apply min/max constraints to SL.
        
        - Ensures minimum distance (for small price assets)
        - Caps maximum distance (for risk control)
        """
        if side == "BUY":
            sl_distance = entry_price - sl_price
            
            # Minimum distance
            if sl_distance < settings.sl_min_distance:
                sl_price = entry_price - settings.sl_min_distance
                logger.info(f"📐 [SL-MIN] Applied min distance: ${settings.sl_min_distance}")
            
            # Maximum distance (% based)
            max_distance = entry_price * (settings.sl_max_pct / 100)
            if sl_distance > max_distance:
                sl_price = entry_price - max_distance
                logger.info(f"📐 [SL-MAX] Capped to {settings.sl_max_pct}%: ${max_distance:.4f}")
        
        else:  # SELL
            sl_distance = sl_price - entry_price
            
            if sl_distance < settings.sl_min_distance:
                sl_price = entry_price + settings.sl_min_distance
            
            max_distance = entry_price * (settings.sl_max_pct / 100)
            if sl_distance > max_distance:
                sl_price = entry_price + max_distance
        
        return sl_price
    
    # ============================================
    # Private Methods - TP Calculation
    # ============================================
    
    def _calculate_take_profits(
        self,
        entry_price: float,
        sl_distance: float,
        side: str,
        settings: UserSLTPSettings
    ) -> Tuple[float, Optional[float]]:
        """
        Calculate TP1 and TP2 based on Risk:Reward ratios.
        
        TP1 = Entry + (SL_distance * R:R_1)
        TP2 = Entry + (SL_distance * R:R_2)
        """
        tp1_distance = sl_distance * settings.tp1_risk_reward
        tp2_distance = sl_distance * settings.tp2_risk_reward
        
        if side == "BUY":
            tp1 = entry_price + tp1_distance
            tp2 = entry_price + tp2_distance if settings.enable_partial_tp else None
        else:  # SELL
            tp1 = entry_price - tp1_distance
            tp2 = entry_price - tp2_distance if settings.enable_partial_tp else None
        
        return tp1, tp2
    
    def _calculate_validation_price(
        self,
        entry_price: float,
        side: str,
        settings: UserSLTPSettings
    ) -> float:
        """
        Calculate the price at which trade becomes "validated".
        
        When price reaches this level, we move SL to breakeven.
        """
        threshold = settings.validation_threshold_pct / 100
        
        if side == "BUY":
            return entry_price * (1 + threshold)
        else:
            return entry_price * (1 - threshold)
    
    # ============================================
    # Private Methods - Trailing SL
    # ============================================
    
    def _calculate_trailing_sl(
        self,
        trade_state: TradeState,
        current_price: float,
        settings: UserSLTPSettings
    ) -> Optional[float]:
        """
        Calculate new trailing SL level.
        
        Only raises SL (for BUY) or lowers SL (for SELL), never goes backwards.
        """
        side = trade_state.side
        entry = trade_state.entry_price
        current_sl = trade_state.sl_current
        
        # Calculate current profit %
        if side == "BUY":
            profit_pct = ((current_price - entry) / entry) * 100
        else:
            profit_pct = ((entry - current_price) / entry) * 100
        
        # Only activate trailing after threshold
        if profit_pct < settings.trailing_activation_pct:
            return None
        
        # Calculate trailing SL
        trailing_distance = current_price * (settings.trailing_distance_pct / 100)
        
        if side == "BUY":
            new_sl = current_price - trailing_distance
            # Only raise SL, never lower
            if new_sl > current_sl:
                return round(new_sl, 8)
        else:
            new_sl = current_price + trailing_distance
            # Only lower SL, never raise
            if new_sl < current_sl:
                return round(new_sl, 8)
        
        return None
    
    # ============================================
    # Private Methods - User Settings
    # ============================================
    
    async def _get_user_settings(self, user_id: UUID) -> UserSLTPSettings:
        """
        Fetch user's SL/TP settings from database.
        
        Returns defaults if not found.
        """
        if not self.db_session_factory:
            logger.debug("No DB session factory, using default settings")
            return UserSLTPSettings()
        
        try:
            from app.models.database_models import UserTradingSettings
            
            db = self.db_session_factory()
            try:
                settings = db.query(UserTradingSettings).filter(
                    UserTradingSettings.user_id == user_id
                ).first()
                
                if settings:
                    return UserSLTPSettings(
                        sl_tp_profile=settings.sl_tp_profile,
                        sl_method=settings.sl_method,
                        sl_atr_multiplier=settings.sl_atr_multiplier,
                        sl_fixed_pct=settings.sl_fixed_pct,
                        sl_min_distance=settings.sl_min_distance,
                        sl_max_pct=settings.sl_max_pct,
                        tp1_risk_reward=settings.tp1_risk_reward,
                        tp1_exit_pct=settings.tp1_exit_pct,
                        tp2_risk_reward=settings.tp2_risk_reward,
                        enable_trailing_sl=settings.enable_trailing_sl,
                        trailing_activation_pct=settings.trailing_activation_pct,
                        trailing_distance_pct=settings.trailing_distance_pct,
                        enable_trade_phases=settings.enable_trade_phases,
                        validation_threshold_pct=settings.validation_threshold_pct,
                        move_sl_to_breakeven=settings.move_sl_to_breakeven,
                        enable_partial_tp=settings.enable_partial_tp,
                        max_position_pct=settings.max_position_pct
                    )
                else:
                    logger.debug(f"No settings found for user {user_id}, using defaults")
                    return UserSLTPSettings()
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error fetching user settings: {e}")
            return UserSLTPSettings()


# ============================================
# Factory function for easy instantiation
# ============================================

def create_sltp_manager(
    market_data_service=None,
    technical_analysis=None,
    db_session_factory=None
) -> SLTPManager:
    """
    Factory function to create SLTPManager with dependencies.
    
    Usage:
        from app.services.sl_tp_manager import create_sltp_manager
        from app.db.database import SessionLocal
        
        sltp_manager = create_sltp_manager(
            market_data_service=market_data,
            technical_analysis=ta_service,
            db_session_factory=SessionLocal
        )
    """
    return SLTPManager(
        market_data_service=market_data_service,
        technical_analysis=technical_analysis,
        db_session_factory=db_session_factory
    )

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
    sl_fixed_pct: float = 2.0  # Changed from 2.5 to 2.0 (tighter SL for better R:R)
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
        
        # ============================================
        # VALIDATION: Check for NaN/Invalid values
        # ============================================
        import math
        
        errors = []
        
        # Check SL
        if not isinstance(sl_price, (int, float)) or math.isnan(sl_price) or math.isinf(sl_price):
            errors.append(f"Invalid SL: {sl_price}")
            sl_price = self._calculate_fixed_pct_sl(entry_price, side, settings)
            logger.warning(f"⚠️ [SLTP-FIX] SL was invalid, using FIXED_PCT fallback: ${sl_price:.4f}")
        
        # Check TP1
        if not isinstance(tp1, (int, float)) or math.isnan(tp1) or math.isinf(tp1):
            errors.append(f"Invalid TP1: {tp1}")
            # Fallback: TP1 = Entry + (SL_distance * 1.5)
            fallback_distance = abs(entry_price - sl_price) * 1.5
            tp1 = entry_price + fallback_distance if side == "BUY" else entry_price - fallback_distance
            logger.warning(f"⚠️ [SLTP-FIX] TP1 was invalid, using fallback: ${tp1:.4f}")
        
        # Check TP2
        if tp2 and (not isinstance(tp2, (int, float)) or math.isnan(tp2) or math.isinf(tp2)):
            errors.append(f"Invalid TP2: {tp2}")
            # Fallback: TP2 = Entry + (SL_distance * 3.0)
            fallback_distance = abs(entry_price - sl_price) * 3.0
            tp2 = entry_price + fallback_distance if side == "BUY" else entry_price - fallback_distance
            logger.warning(f"⚠️ [SLTP-FIX] TP2 was invalid, using fallback: ${tp2:.4f}")
        
        # Check validation price
        if not isinstance(validation_price, (int, float)) or math.isnan(validation_price) or math.isinf(validation_price):
            validation_price = self._calculate_validation_price(entry_price, side, settings)
            logger.warning(f"⚠️ [SLTP-FIX] Validation price was invalid, recalculated: ${validation_price:.4f}")
        
        # Check distances
        if not isinstance(sl_distance_pct, (int, float)) or math.isnan(sl_distance_pct) or math.isinf(sl_distance_pct):
            sl_distance_pct = abs((sl_price - entry_price) / entry_price) * 100
            logger.warning(f"⚠️ [SLTP-FIX] SL distance was invalid, recalculated: {sl_distance_pct:.2f}%")
        
        if errors:
            logger.error(f"❌ [SLTP-VALIDATION] Fixed {len(errors)} invalid value(s): {', '.join(errors)}")
        
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
        
        DT-007: DYNAMIC ATR MULTIPLIER
        ATR adapts to volatility:
        - Low volatility (ATR < 0.8x avg) → Tighter SL (1.0x multiplier)
        - Normal volatility (0.8x-1.2x avg) → Standard SL (1.5x multiplier)
        - High volatility (ATR > 1.2x avg) → Wider SL (2.0x multiplier)
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
        
        # ===== DT-007: DYNAMIC ATR MULTIPLIER =====
        # Calculate dynamic multiplier based on market volatility
        dynamic_multiplier = self._calculate_dynamic_atr_multiplier(
            atr=atr,
            entry_price=entry_price,
            market_data=market_data,
            base_multiplier=settings.sl_atr_multiplier
        )
        # ===== END DYNAMIC ATR MULTIPLIER =====
        
        # SL distance = ATR * dynamic multiplier
        sl_distance = atr * dynamic_multiplier
        
        # Log the adjustment
        if dynamic_multiplier != settings.sl_atr_multiplier:
            logger.info(f"📊 [ATR-DYNAMIC] Multiplier adjusted: {settings.sl_atr_multiplier:.1f}x → {dynamic_multiplier:.1f}x based on volatility")
        
        if side == "BUY":
            return entry_price - sl_distance
        else:  # SELL
            return entry_price + sl_distance
    
    def _calculate_dynamic_atr_multiplier(
        self,
        atr: float,
        entry_price: float,
        market_data: Dict[str, Any],
        base_multiplier: float
    ) -> float:
        """
        DT-007: Calculate dynamic ATR multiplier based on market volatility.
        
        Compares current ATR to average ATR to determine relative volatility:
        - Volatility < 0.8x avg → Low vol → Tighter SL (1.0x)
        - Volatility 0.8-1.2x avg → Normal → Standard SL (1.5x)
        - Volatility > 1.2x avg → High vol → Wider SL (2.0x)
        
        Args:
            atr: Current ATR value
            entry_price: Current entry price
            market_data: Dict with candles/indicators
            base_multiplier: User's configured base multiplier
            
        Returns:
            Adjusted ATR multiplier (1.0, 1.5, or 2.0)
        """
        try:
            # Calculate ATR as percentage of price (normalized)
            atr_pct = (atr / entry_price) * 100
            
            # Get historical ATR values to calculate average
            candles = market_data.get("candles", [])
            
            if candles and len(candles) >= 50:
                # Calculate average ATR over last 50 periods
                atr_values = []
                for i in range(max(0, len(candles) - 50), len(candles)):
                    candle = candles[i]
                    high = float(candle.get("high", 0))
                    low = float(candle.get("low", 0))
                    close = float(candle.get("close", 0))
                    
                    if high > 0 and low > 0 and close > 0:
                        # True Range = max(high-low, |high-prev_close|, |low-prev_close|)
                        if i > 0:
                            prev_close = float(candles[i-1].get("close", close))
                            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
                        else:
                            tr = high - low
                        
                        atr_values.append(tr)
                
                if atr_values:
                    avg_atr = sum(atr_values) / len(atr_values)
                    avg_atr_pct = (avg_atr / entry_price) * 100
                    
                    # Calculate volatility ratio (current ATR / average ATR)
                    volatility_ratio = atr_pct / avg_atr_pct if avg_atr_pct > 0 else 1.0
                    
                    # Determine multiplier based on volatility
                    if volatility_ratio < 0.8:
                        # LOW VOLATILITY: Market is calm, use tighter SL
                        multiplier = 1.0
                        vol_label = "LOW"
                    elif volatility_ratio > 1.2:
                        # HIGH VOLATILITY: Market is volatile, use wider SL
                        multiplier = 2.0
                        vol_label = "HIGH"
                    else:
                        # NORMAL VOLATILITY: Use standard SL
                        multiplier = 1.5
                        vol_label = "NORMAL"
                    
                    logger.debug(f"📊 [ATR-VOL] Current: {atr_pct:.3f}% | Avg: {avg_atr_pct:.3f}% | "
                               f"Ratio: {volatility_ratio:.2f}x | Multiplier: {multiplier}x ({vol_label})")
                    
                    return multiplier
            
            # Fallback: Not enough data, use base multiplier
            logger.debug(f"⚠️ [ATR-VOL] Insufficient candles ({len(candles)}), using base multiplier {base_multiplier}x")
            return base_multiplier
            
        except Exception as e:
            logger.warning(f"⚠️ [ATR-VOL] Error calculating dynamic multiplier: {e}, using base {base_multiplier}x")
            return base_multiplier
    
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


# ============================================
# Global Trade Monitor (includes AI_AGENT trades)
# ============================================

class GlobalTradeMonitor:
    """
    Monitors ALL open trades including AI_AGENT trades (bot_id=NULL).
    
    This solves the architecture gap where BotEngine only monitors trades
    with an associated bot_id, leaving AI_AGENT trades unmonitored.
    
    Usage:
        monitor = GlobalTradeMonitor(
            sltp_manager=sltp_manager,
            db_session_factory=SessionLocal,
            market_data_service=market_data
        )
        await monitor.start()  # Runs every 60s
    """
    
    def __init__(
        self,
        sltp_manager: SLTPManager,
        db_session_factory,
        market_data_service
    ):
        self.sltp_manager = sltp_manager
        self.db_session_factory = db_session_factory
        self.market_data = market_data_service
        self._running = False
        self._task = None
    
    async def start(self):
        """Start the global trade monitoring loop"""
        if self._running:
            logger.warning("⚠️ GlobalTradeMonitor already running")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("🔄 GlobalTradeMonitor started - monitoring ALL trades including AI_AGENT")
    
    async def stop(self):
        """Stop the monitoring loop"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("🛑 GlobalTradeMonitor stopped")
    
    async def _monitor_loop(self):
        """Main monitoring loop - checks ALL open trades every 60 seconds"""
        logger.info("🔄 GlobalTradeMonitor loop started (60s interval)")
        
        while self._running:
            try:
                await self._check_all_trades()
                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"❌ Error in GlobalTradeMonitor loop: {e}")
                await asyncio.sleep(60)
    
    async def _check_all_trades(self):
        """Check all open trades for SL/TP hits"""
        from app.models.database_models import Trade, Portfolio
        from uuid import UUID
        
        db = self.db_session_factory()
        try:
            # Get ALL open trades (including AI_AGENT with bot_id=NULL)
            open_trades = db.query(Trade).filter(
                Trade.status == "OPEN"
            ).all()
            
            if not open_trades:
                return
            
            # Group by strategy for logging
            ai_trades = [t for t in open_trades if t.strategy == "AI_AGENT"]
            bot_trades = [t for t in open_trades if t.strategy != "AI_AGENT"]
            
            logger.info(f"🔍 [GLOBAL-MONITOR] Checking {len(open_trades)} trades ({len(ai_trades)} AI_AGENT, {len(bot_trades)} Bot)")
            
            for trade in open_trades:
                await self._check_trade(db, trade)
            
            db.commit()
            
        except Exception as e:
            logger.error(f"❌ Error checking trades: {e}")
            db.rollback()
        finally:
            db.close()
    
    async def _check_trade(self, db, trade):
        """Check a single trade for SL/TP and apply updates"""
        from app.models.database_models import Portfolio
        from uuid import UUID
        
        try:
            symbol = trade.symbol
            
            # Fetch current price
            candles = await self.market_data.get_candles(symbol, timeframe="1m", limit=1)
            if not candles:
                logger.warning(f"⚠️ Could not fetch price for {symbol}")
                return
            
            current_price = candles[-1]['close']
            entry_price = float(trade.entry_price)
            sl = float(trade.stop_loss_price) if trade.stop_loss_price else None
            tp = float(trade.take_profit_price) if trade.take_profit_price else None
            tp2 = float(trade.take_profit_2) if hasattr(trade, 'take_profit_2') and trade.take_profit_2 else None
            
            # Calculate PnL %
            pnl_pct = ((current_price - entry_price) / entry_price) * 100 if trade.side == "BUY" else ((entry_price - current_price) / entry_price) * 100
            
            # ===== BUG FIX: Detect and fix misconfigured SL =====
            if sl and trade.side == "BUY" and sl >= entry_price:
                logger.error(f"🚨 [BUG] {symbol}: SL ${sl:.4f} >= Entry ${entry_price:.4f}! Auto-fixing...")
                sl = current_price * 0.97  # 3% below current
                trade.stop_loss_price = sl
                logger.warning(f"🔧 [AUTO-FIX] {symbol}: SL set to ${sl:.4f}")
            
            # Log status for AI_AGENT trades (more verbose)
            if trade.strategy == "AI_AGENT":
                logger.info(f"📊 [AI-TRADE] {symbol}: Entry=${entry_price:.4f} | Current=${current_price:.4f} ({pnl_pct:+.2f}%) | SL=${sl} | TP=${tp}")
            
            # Build TradeState for SLTPManager
            trade_state = TradeState(
                trade_id=str(trade.id),
                symbol=symbol,
                side=trade.side,
                entry_price=entry_price,
                quantity=float(trade.quantity),
                sl_initial=sl or entry_price * 0.97,
                sl_current=sl or entry_price * 0.97,
                tp1=tp or entry_price * 1.03,
                tp2=tp2,
                tp1_exit_pct=50.0,
                phase=TradePhase(trade.trade_phase) if hasattr(trade, 'trade_phase') and trade.trade_phase else TradePhase.PENDING,
                tp1_hit=getattr(trade, 'tp1_partial_executed', False) if hasattr(trade, 'tp1_partial_executed') else False
            )
            
            # Get market data for SLTPManager
            market_data = {
                'close': current_price,
                'high': candles[-1].get('high', current_price),
                'low': candles[-1].get('low', current_price),
                'indicators': {}
            }
            
            # Call SLTPManager
            update = await self.sltp_manager.update_trade(
                trade_state=trade_state,
                current_price=current_price,
                market_data=market_data,
                user_settings=None
            )
            
            # Apply SL updates
            if update.new_sl and update.new_sl != trade.stop_loss_price:
                old_sl = trade.stop_loss_price
                trade.stop_loss_price = update.new_sl
                logger.info(f"📈 [SL-UPDATE] {symbol} | SL: ${old_sl} → ${update.new_sl:.4f}")
            
            # Apply phase updates
            if update.new_phase and hasattr(trade, 'trade_phase'):
                trade.trade_phase = update.new_phase.value
                logger.info(f"✅ [PHASE] {symbol} | → {update.new_phase.value}")
            
            # Handle closes
            if update.should_close:
                logger.info(f"{update.log_message}")
                await self._close_trade(db, trade, current_price, update.close_reason.value if update.close_reason else "SL_TP")
                
        except Exception as e:
            logger.error(f"❌ Error checking trade {trade.symbol}: {e}")
    
    async def _close_trade(self, db, trade, exit_price: float, reason: str):
        """Close a trade and update portfolio"""
        from app.models.database_models import Portfolio
        from uuid import UUID
        from datetime import datetime
        
        try:
            # Calculate PnL
            entry_price = float(trade.entry_price)
            quantity = float(trade.quantity)
            
            if trade.side == "BUY":
                pnl = (exit_price - entry_price) * quantity
            else:
                pnl = (entry_price - exit_price) * quantity
            
            pnl_percent = (pnl / (entry_price * quantity)) * 100
            
            # Update trade
            trade.status = "CLOSED"
            trade.exit_price = exit_price
            trade.exit_time = datetime.utcnow()
            trade.pnl = pnl
            trade.pnl_percent = pnl_percent
            
            # Update portfolio
            portfolio = db.query(Portfolio).filter(
                Portfolio.user_id == trade.user_id
            ).first()
            
            if portfolio:
                # Return cost + PnL to cash
                trade_value = entry_price * quantity
                portfolio.cash_balance = float(portfolio.cash_balance) + trade_value + pnl
                portfolio.total_pnl = float(portfolio.total_pnl or 0) + pnl
                portfolio.daily_pnl = float(portfolio.daily_pnl or 0) + pnl
            
            emoji = "💰" if pnl >= 0 else "📉"
            logger.info(f"{emoji} [CLOSED] {trade.symbol} | {reason} | PnL: ${pnl:.2f} ({pnl_percent:+.2f}%)")
            
        except Exception as e:
            logger.error(f"❌ Error closing trade: {e}")


# Import asyncio at module level for GlobalTradeMonitor
import asyncio


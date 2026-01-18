"""
Trading Settings Routes
=======================
API endpoints for managing user trading preferences (SL/TP profiles, risk limits).

Endpoints:
- GET  /api/settings/trading          - Get user's trading settings
- PUT  /api/settings/trading          - Update user's trading settings
- GET  /api/settings/trading/profiles - Get available profile presets
- POST /api/settings/trading/reset    - Reset to profile defaults
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
import logging

from app.db.database import get_db
from app.auth.supabase_auth import get_current_user
from app.models.database_models import (
    UserTradingSettings, 
    SLTPProfilePreset,
    SLTP_PROFILE_PRESETS
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/settings", tags=["settings"])


# ============================================
# Pydantic Models
# ============================================

class TradingSettingsResponse(BaseModel):
    """Response model for user trading settings"""
    user_id: str
    sl_tp_profile: str
    
    # SL Config
    sl_method: str
    sl_atr_multiplier: float
    sl_fixed_pct: float
    sl_min_distance: float
    sl_max_pct: float
    
    # TP Config
    tp1_risk_reward: float
    tp1_exit_pct: float
    tp2_risk_reward: float
    
    # Trailing Config
    enable_trailing_sl: bool
    trailing_activation_pct: float
    trailing_distance_pct: float
    
    # Phase Config
    enable_trade_phases: bool
    validation_threshold_pct: float
    move_sl_to_breakeven: bool
    
    # Partial TP
    enable_partial_tp: bool
    
    # Risk Limits
    max_position_pct: float
    max_daily_loss_pct: float
    max_trades_per_day: int
    
    class Config:
        from_attributes = True


class TradingSettingsUpdate(BaseModel):
    """Request model for updating trading settings"""
    sl_tp_profile: Optional[str] = Field(None, pattern="^(PRUDENT|BALANCED|AGGRESSIVE)$")
    
    # SL Config (optional overrides)
    sl_method: Optional[str] = Field(None, pattern="^(ATR|STRUCTURE|FIXED_PCT|HYBRID)$")
    sl_atr_multiplier: Optional[float] = Field(None, ge=0.5, le=5.0)
    sl_fixed_pct: Optional[float] = Field(None, ge=0.5, le=10.0)
    sl_min_distance: Optional[float] = Field(None, ge=0.001, le=1.0)
    sl_max_pct: Optional[float] = Field(None, ge=1.0, le=15.0)
    
    # TP Config
    tp1_risk_reward: Optional[float] = Field(None, ge=0.5, le=5.0)
    tp1_exit_pct: Optional[float] = Field(None, ge=10.0, le=100.0)
    tp2_risk_reward: Optional[float] = Field(None, ge=1.0, le=10.0)
    
    # Trailing Config
    enable_trailing_sl: Optional[bool] = None
    trailing_activation_pct: Optional[float] = Field(None, ge=0.5, le=5.0)
    trailing_distance_pct: Optional[float] = Field(None, ge=0.25, le=3.0)
    
    # Phase Config
    enable_trade_phases: Optional[bool] = None
    validation_threshold_pct: Optional[float] = Field(None, ge=0.1, le=2.0)
    move_sl_to_breakeven: Optional[bool] = None
    
    # Partial TP
    enable_partial_tp: Optional[bool] = None
    
    # Risk Limits
    max_position_pct: Optional[float] = Field(None, ge=5.0, le=50.0)
    max_daily_loss_pct: Optional[float] = Field(None, ge=1.0, le=20.0)
    max_trades_per_day: Optional[int] = Field(None, ge=1, le=100)


class ProfilePresetResponse(BaseModel):
    """Response model for profile presets"""
    profile_name: str
    display_name: str
    description: str
    sl_atr_multiplier: float
    sl_fixed_pct: float
    sl_max_pct: float
    tp1_risk_reward: float
    tp1_exit_pct: float
    tp2_risk_reward: float
    trailing_activation_pct: float
    trailing_distance_pct: float
    validation_threshold_pct: float


# ============================================
# Endpoints
# ============================================

@router.get("/trading", response_model=TradingSettingsResponse)
async def get_trading_settings(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's current trading settings.
    Creates default settings if none exist.
    """
    user_id = UUID(current_user["id"])
    
    # Try to get existing settings
    settings = db.query(UserTradingSettings).filter(
        UserTradingSettings.user_id == user_id
    ).first()
    
    # Create default settings if not exists
    if not settings:
        logger.info(f"📝 Creating default trading settings for user {user_id}")
        settings = UserTradingSettings(
            user_id=user_id,
            sl_tp_profile="BALANCED"
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    
    return TradingSettingsResponse(
        user_id=str(settings.user_id),
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
        max_position_pct=settings.max_position_pct,
        max_daily_loss_pct=settings.max_daily_loss_pct,
        max_trades_per_day=settings.max_trades_per_day
    )


@router.put("/trading", response_model=TradingSettingsResponse)
async def update_trading_settings(
    update_data: TradingSettingsUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update user's trading settings.
    
    If sl_tp_profile is changed, applies the profile defaults first,
    then applies any other specified overrides.
    """
    user_id = UUID(current_user["id"])
    
    # Get or create settings
    settings = db.query(UserTradingSettings).filter(
        UserTradingSettings.user_id == user_id
    ).first()
    
    if not settings:
        settings = UserTradingSettings(user_id=user_id)
        db.add(settings)
    
    # If profile is changing, apply profile defaults first
    if update_data.sl_tp_profile and update_data.sl_tp_profile != settings.sl_tp_profile:
        profile = SLTP_PROFILE_PRESETS.get(update_data.sl_tp_profile)
        if profile:
            logger.info(f"📊 User {user_id} changing profile to {update_data.sl_tp_profile}")
            settings.sl_tp_profile = update_data.sl_tp_profile
            settings.sl_atr_multiplier = profile["sl_atr_multiplier"]
            settings.sl_fixed_pct = profile["sl_fixed_pct"]
            settings.sl_max_pct = profile["sl_max_pct"]
            settings.tp1_risk_reward = profile["tp1_risk_reward"]
            settings.tp1_exit_pct = profile["tp1_exit_pct"]
            settings.tp2_risk_reward = profile["tp2_risk_reward"]
            settings.trailing_activation_pct = profile["trailing_activation_pct"]
            settings.trailing_distance_pct = profile["trailing_distance_pct"]
            settings.validation_threshold_pct = profile["validation_threshold_pct"]
    
    # Apply any specific overrides
    update_dict = update_data.model_dump(exclude_unset=True, exclude_none=True)
    for field, value in update_dict.items():
        if field != "sl_tp_profile":  # Already handled above
            setattr(settings, field, value)
    
    db.commit()
    db.refresh(settings)
    
    logger.info(f"✅ Trading settings updated for user {user_id}")
    
    return TradingSettingsResponse(
        user_id=str(settings.user_id),
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
        max_position_pct=settings.max_position_pct,
        max_daily_loss_pct=settings.max_daily_loss_pct,
        max_trades_per_day=settings.max_trades_per_day
    )


@router.get("/trading/profiles", response_model=List[ProfilePresetResponse])
async def get_profile_presets(
    current_user: dict = Depends(get_current_user)
):
    """
    Get available SL/TP profile presets.
    Returns PRUDENT, BALANCED, and AGGRESSIVE profiles with their configurations.
    """
    profiles = []
    for name, config in SLTP_PROFILE_PRESETS.items():
        profiles.append(ProfilePresetResponse(
            profile_name=name,
            **config
        ))
    
    # Sort: PRUDENT, BALANCED, AGGRESSIVE
    order = {"PRUDENT": 0, "BALANCED": 1, "AGGRESSIVE": 2}
    profiles.sort(key=lambda p: order.get(p.profile_name, 99))
    
    return profiles


@router.post("/trading/reset", response_model=TradingSettingsResponse)
async def reset_to_profile_defaults(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Reset user's trading settings to their current profile's defaults.
    Useful when user wants to undo custom overrides.
    """
    user_id = UUID(current_user["id"])
    
    settings = db.query(UserTradingSettings).filter(
        UserTradingSettings.user_id == user_id
    ).first()
    
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")
    
    profile = SLTP_PROFILE_PRESETS.get(settings.sl_tp_profile)
    if not profile:
        raise HTTPException(status_code=400, detail="Invalid profile")
    
    # Reset to profile defaults
    settings.sl_atr_multiplier = profile["sl_atr_multiplier"]
    settings.sl_fixed_pct = profile["sl_fixed_pct"]
    settings.sl_max_pct = profile["sl_max_pct"]
    settings.tp1_risk_reward = profile["tp1_risk_reward"]
    settings.tp1_exit_pct = profile["tp1_exit_pct"]
    settings.tp2_risk_reward = profile["tp2_risk_reward"]
    settings.trailing_activation_pct = profile["trailing_activation_pct"]
    settings.trailing_distance_pct = profile["trailing_distance_pct"]
    settings.validation_threshold_pct = profile["validation_threshold_pct"]
    
    # Reset toggles to defaults
    settings.enable_trailing_sl = True
    settings.enable_trade_phases = True
    settings.move_sl_to_breakeven = True
    settings.enable_partial_tp = True
    settings.sl_method = "ATR"
    settings.sl_min_distance = 0.01
    settings.max_position_pct = 25.0
    settings.max_daily_loss_pct = 5.0
    settings.max_trades_per_day = 10
    
    db.commit()
    db.refresh(settings)
    
    logger.info(f"🔄 Trading settings reset to {settings.sl_tp_profile} defaults for user {user_id}")
    
    return TradingSettingsResponse(
        user_id=str(settings.user_id),
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
        max_position_pct=settings.max_position_pct,
        max_daily_loss_pct=settings.max_daily_loss_pct,
        max_trades_per_day=settings.max_trades_per_day
    )


@router.get("/trading/profile/{profile_name}", response_model=ProfilePresetResponse)
async def get_profile_details(
    profile_name: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get details for a specific profile preset.
    """
    profile_name_upper = profile_name.upper()
    
    if profile_name_upper not in SLTP_PROFILE_PRESETS:
        raise HTTPException(
            status_code=404, 
            detail=f"Profile '{profile_name}' not found. Available: PRUDENT, BALANCED, AGGRESSIVE"
        )
    
    config = SLTP_PROFILE_PRESETS[profile_name_upper]
    
    return ProfilePresetResponse(
        profile_name=profile_name_upper,
        **config
    )

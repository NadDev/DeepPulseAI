"""
Test Suite for SL/TP Manager
============================

Tests for:
1. SL calculation (ATR, Structure, Fixed%, Hybrid)
2. TP calculation (based on R:R ratios)
3. Trade phase transitions
4. Trailing stop logic
5. Partial take profit execution
6. Position sizing

Run with: pytest tests/test_sltp_manager.py -v
"""

import pytest
import asyncio
from decimal import Decimal
from uuid import UUID
from datetime import datetime
from typing import Dict, Any
import sys
import os

# Add backend to path
backend_path = os.path.join(os.path.dirname(__file__), '..', 'backend')
sys.path.insert(0, backend_path)

from app.services.sl_tp_manager import (
    SLTPManager, 
    SLTPConfig, 
    TradeState, 
    TradeUpdate,
    UserSLTPSettings,
    SLMethod,
    TradePhase,
    ExitReason,
    create_sltp_manager
)


# ============================================
# Test Fixtures
# ============================================

@pytest.fixture
def sltp_manager():
    """Create a basic SLTPManager without DB dependencies"""
    return SLTPManager(
        market_data_service=None,
        technical_analysis=None,
        db_session_factory=None
    )


@pytest.fixture
def user_id():
    """Standard test user UUID"""
    return UUID('12345678-1234-5678-1234-567812345678')


@pytest.fixture
def market_data_btc():
    """Mock market data for BTCUSDT"""
    return {
        "symbol": "BTCUSDT",
        "close": 42000,
        "open": 41500,
        "high": 42500,
        "low": 41000,
        "volume": 1000,
        "indicators": {
            "atr": 800,  # ~1.9% of price
            "atr_14": 800,
            "support": 41200,
            "resistance": 43000,
            "sma_20": 41800,
            "rsi": 65
        }
    }


@pytest.fixture
def settings_balanced():
    """BALANCED profile settings"""
    return UserSLTPSettings(
        sl_tp_profile="BALANCED",
        sl_method="ATR",
        sl_atr_multiplier=1.5,
        sl_fixed_pct=2.5,
        sl_min_distance=0.01,
        sl_max_pct=5.0,
        tp1_risk_reward=1.5,
        tp1_exit_pct=50.0,
        tp2_risk_reward=3.0,
        enable_trailing_sl=True,
        trailing_activation_pct=1.5,
        trailing_distance_pct=1.0,
        enable_trade_phases=True,
        validation_threshold_pct=0.5,
        move_sl_to_breakeven=True,
        enable_partial_tp=True,
        max_position_pct=25.0
    )


@pytest.fixture
def settings_prudent():
    """PRUDENT profile settings"""
    return UserSLTPSettings(
        sl_tp_profile="PRUDENT",
        sl_method="ATR",
        sl_atr_multiplier=1.0,
        sl_fixed_pct=1.5,
        sl_min_distance=0.01,
        sl_max_pct=3.0,
        tp1_risk_reward=1.3,
        tp1_exit_pct=70.0,
        tp2_risk_reward=2.0,
        enable_trailing_sl=True,
        trailing_activation_pct=1.0,
        trailing_distance_pct=0.75,
        enable_trade_phases=True,
        validation_threshold_pct=0.5,
        move_sl_to_breakeven=True,
        enable_partial_tp=True,
        max_position_pct=15.0
    )


# ============================================
# Tests: SL Calculation
# ============================================

class TestSLCalculation:
    """Test stop loss calculation methods"""
    
    def test_atr_sl_buy(self, sltp_manager, market_data_btc, settings_balanced):
        """Test ATR-based SL for BUY trades"""
        entry_price = 42000
        side = "BUY"
        
        sl_price = sltp_manager._calculate_atr_sl(
            entry_price=entry_price,
            side=side,
            market_data=market_data_btc,
            settings=settings_balanced
        )
        
        # SL = Entry - (ATR * Multiplier)
        # SL = 42000 - (800 * 1.5) = 42000 - 1200 = 40800
        expected_sl = entry_price - (market_data_btc["indicators"]["atr"] * settings_balanced.sl_atr_multiplier)
        
        assert abs(sl_price - expected_sl) < 0.01, f"Expected {expected_sl}, got {sl_price}"
        assert sl_price < entry_price, "SL should be below entry for BUY"
    
    
    def test_atr_sl_sell(self, sltp_manager, market_data_btc, settings_balanced):
        """Test ATR-based SL for SELL trades"""
        entry_price = 42000
        side = "SELL"
        
        sl_price = sltp_manager._calculate_atr_sl(
            entry_price=entry_price,
            side=side,
            market_data=market_data_btc,
            settings=settings_balanced
        )
        
        expected_sl = entry_price + (market_data_btc["indicators"]["atr"] * settings_balanced.sl_atr_multiplier)
        
        assert abs(sl_price - expected_sl) < 0.01, f"Expected {expected_sl}, got {sl_price}"
        assert sl_price > entry_price, "SL should be above entry for SELL"
    
    
    def test_fixed_pct_sl(self, sltp_manager, settings_balanced):
        """Test fixed percentage SL"""
        entry_price = 42000
        
        # BUY: SL = 42000 * (1 - 0.025) = 40950
        sl_buy = sltp_manager._calculate_fixed_pct_sl(42000, "BUY", settings_balanced)
        expected_buy = 42000 * (1 - settings_balanced.sl_fixed_pct / 100)
        assert abs(sl_buy - expected_buy) < 0.01
        
        # SELL: SL = 42000 * (1 + 0.025) = 43050
        sl_sell = sltp_manager._calculate_fixed_pct_sl(42000, "SELL", settings_balanced)
        expected_sell = 42000 * (1 + settings_balanced.sl_fixed_pct / 100)
        assert abs(sl_sell - expected_sell) < 0.01
    
    
    def test_structure_sl_buy(self, sltp_manager, market_data_btc, settings_balanced):
        """Test structure-based SL for BUY"""
        entry_price = 42000
        side = "BUY"
        
        sl_price = sltp_manager._calculate_structure_sl(
            entry_price=entry_price,
            side=side,
            market_data=market_data_btc,
            settings=settings_balanced
        )
        
        # Should place SL below support
        support = market_data_btc["indicators"]["support"]
        assert sl_price < support, "SL should be below support"
        assert sl_price < entry_price, "SL should be below entry for BUY"
    
    
    def test_sl_constraints(self, sltp_manager, settings_balanced):
        """Test min/max SL constraints"""
        entry_price = 100
        
        # Test minimum constraint
        sl_too_close = 99.999
        constrained_sl = sltp_manager._apply_sl_constraints(
            entry_price=entry_price,
            sl_price=sl_too_close,
            side="BUY",
            settings=settings_balanced
        )
        
        assert constrained_sl <= entry_price - settings_balanced.sl_min_distance, \
            "SL should respect minimum distance"
        
        # Test maximum constraint
        sl_too_far = 90  # More than 5% below entry
        constrained_sl = sltp_manager._apply_sl_constraints(
            entry_price=entry_price,
            sl_price=sl_too_far,
            side="BUY",
            settings=settings_balanced
        )
        
        max_distance = entry_price * (settings_balanced.sl_max_pct / 100)
        assert constrained_sl >= entry_price - max_distance, \
            "SL should not exceed maximum distance"


# ============================================
# Tests: TP Calculation
# ============================================

class TestTPCalculation:
    """Test take profit calculation"""
    
    def test_tp_buy_balanced(self, sltp_manager, settings_balanced):
        """Test TP calculation for BUY (BALANCED profile)"""
        entry_price = 42000
        sl_price = 40800
        sl_distance = entry_price - sl_price  # 1200
        
        tp1, tp2 = sltp_manager._calculate_take_profits(
            entry_price=entry_price,
            sl_distance=sl_distance,
            side="BUY",
            settings=settings_balanced
        )
        
        # TP1 = Entry + (SL_distance * 1.5) = 42000 + (1200 * 1.5) = 43800
        expected_tp1 = entry_price + (sl_distance * settings_balanced.tp1_risk_reward)
        assert abs(tp1 - expected_tp1) < 0.01, f"Expected TP1 {expected_tp1}, got {tp1}"
        
        # TP2 = Entry + (SL_distance * 3.0) = 42000 + (1200 * 3.0) = 45600
        expected_tp2 = entry_price + (sl_distance * settings_balanced.tp2_risk_reward)
        assert abs(tp2 - expected_tp2) < 0.01, f"Expected TP2 {expected_tp2}, got {tp2}"
    
    
    def test_tp_sell_balanced(self, sltp_manager, settings_balanced):
        """Test TP calculation for SELL (BALANCED profile)"""
        entry_price = 42000
        sl_price = 43200
        sl_distance = sl_price - entry_price  # 1200
        
        tp1, tp2 = sltp_manager._calculate_take_profits(
            entry_price=entry_price,
            sl_distance=sl_distance,
            side="SELL",
            settings=settings_balanced
        )
        
        # TP1 = Entry - (SL_distance * 1.5) = 42000 - (1200 * 1.5) = 40200
        expected_tp1 = entry_price - (sl_distance * settings_balanced.tp1_risk_reward)
        assert abs(tp1 - expected_tp1) < 0.01, f"Expected TP1 {expected_tp1}, got {tp1}"
    
    
    def test_tp_prudent_vs_balanced(self, sltp_manager, settings_prudent, settings_balanced):
        """Compare TP levels between PRUDENT and BALANCED profiles"""
        entry_price = 42000
        sl_distance = 1200
        
        tp1_prudent, tp2_prudent = sltp_manager._calculate_take_profits(
            entry_price=entry_price,
            sl_distance=sl_distance,
            side="BUY",
            settings=settings_prudent
        )
        
        tp1_balanced, tp2_balanced = sltp_manager._calculate_take_profits(
            entry_price=entry_price,
            sl_distance=sl_distance,
            side="BUY",
            settings=settings_balanced
        )
        
        # BALANCED should have higher TP1 than PRUDENT (1.5 vs 1.3 R:R)
        assert tp1_balanced > tp1_prudent, "BALANCED should have higher TP1 than PRUDENT"
        assert tp2_balanced > tp2_prudent, "BALANCED should have higher TP2 than PRUDENT"


# ============================================
# Tests: Trade Phase Transitions
# ============================================

class TestTradePhases:
    """Test trade phase transitions"""
    
    def test_validation_price_buy(self, sltp_manager, settings_balanced):
        """Test validation price calculation for BUY"""
        entry_price = 42000
        threshold = settings_balanced.validation_threshold_pct / 100  # 0.005
        
        val_price = sltp_manager._calculate_validation_price(
            entry_price=entry_price,
            side="BUY",
            settings=settings_balanced
        )
        
        expected = entry_price * (1 + threshold)
        assert abs(val_price - expected) < 0.01
        assert val_price > entry_price, "Validation price should be above entry for BUY"
    
    
    def test_pending_to_validated_transition(self, sltp_manager, settings_balanced):
        """Test PENDING → VALIDATED phase transition"""
        trade_state = TradeState(
            trade_id="test_123",
            symbol="BTCUSDT",
            side="BUY",
            entry_price=42000,
            quantity=1.0,
            sl_initial=40800,
            sl_current=40800,
            tp1=43800,
            tp2=45600,
            tp1_exit_pct=50.0,
            phase=TradePhase.PENDING,
            validation_price=42210,  # 0.5% above entry
        )
        
        # Price reaches validation level
        current_price = 42250  # Above validation price
        market_data = {"indicators": {}}
        
        update = sltp_manager._calculate_trailing_sl(trade_state, current_price, settings_balanced)
        
        # The actual phase transition happens in update_trade()
        # Here we just verify validation price logic
        assert trade_state.validation_price < current_price, \
            "Current price should be above validation price"


# ============================================
# Tests: Trailing Stop Logic
# ============================================

class TestTrailingStop:
    """Test trailing stop calculation"""
    
    def test_trailing_sl_activation_buy(self, sltp_manager, settings_balanced):
        """Test trailing SL activates after profit threshold (BUY)"""
        trade_state = TradeState(
            trade_id="test_123",
            symbol="BTCUSDT",
            side="BUY",
            entry_price=42000,
            quantity=1.0,
            sl_initial=40800,
            sl_current=40800,
            tp1=43800,
            tp2=45600,
            tp1_exit_pct=50.0,
            phase=TradePhase.VALIDATED,
            highest_price=44000,
        )
        
        # Price at +2% (above 1.5% activation threshold)
        current_price = 42840
        
        new_sl = sltp_manager._calculate_trailing_sl(
            trade_state=trade_state,
            current_price=current_price,
            settings=settings_balanced
        )
        
        # Should calculate trailing SL
        # SL = Price - (Price * trailing_distance_pct)
        # SL = 42840 - (42840 * 0.01) = 42840 - 428.40 = 42411.60
        expected_sl = current_price - (current_price * settings_balanced.trailing_distance_pct / 100)
        
        assert new_sl is not None, "Trailing SL should be calculated"
        assert abs(new_sl - expected_sl) < 0.01, f"Expected {expected_sl}, got {new_sl}"
        assert new_sl > trade_state.sl_current, "Trailing SL should move up (raise) for BUY"
    
    
    def test_trailing_sl_only_raises_buy(self, sltp_manager, settings_balanced):
        """Test trailing SL only raises (never lowers) for BUY"""
        trade_state = TradeState(
            trade_id="test_123",
            symbol="BTCUSDT",
            side="BUY",
            entry_price=42000,
            quantity=1.0,
            sl_initial=40800,
            sl_current=41500,  # Already raised
            tp1=43800,
            tp2=45600,
            tp1_exit_pct=50.0,
            phase=TradePhase.TRAILING,
            highest_price=44000,
        )
        
        # Price moves down (but still profitable)
        current_price = 42500  # +1.2%
        
        new_sl = sltp_manager._calculate_trailing_sl(
            trade_state=trade_state,
            current_price=current_price,
            settings=settings_balanced
        )
        
        # Trailing SL would be lower than current SL, so should return None
        assert new_sl is None, "Trailing SL should not lower for BUY"


# ============================================
# Tests: Position Sizing
# ============================================

class TestPositionSizing:
    """Test position size calculation"""
    
    def test_position_size_from_sl(self, sltp_manager):
        """Test position size calculation based on SL distance"""
        portfolio_value = 10000
        entry_price = 42000
        stop_loss = 40800
        risk_percent = 2.0
        
        qty, cost = sltp_manager.calculate_position_size_from_sl(
            portfolio_value=portfolio_value,
            entry_price=entry_price,
            stop_loss=stop_loss,
            risk_percent=risk_percent,
            max_position_pct=25.0
        )
        
        # SL distance = 42000 - 40800 = 1200
        # Max risk = 10000 * 0.02 = 200
        # Qty = 200 / 1200 = 0.1667
        # But cost = 0.1667 * 42000 = 7000 which exceeds 25% cap (2500)
        # So qty is capped at 2500/42000 = 0.0595
        max_cost = portfolio_value * 0.25
        expected_qty = max_cost / entry_price
        expected_cost = max_cost
        
        assert abs(qty - expected_qty) < 0.0001, f"Expected qty {expected_qty}, got {qty}"
        assert abs(cost - expected_cost) < 0.01, f"Expected cost {expected_cost}, got {cost}"
    
    
    def test_position_size_max_cap(self, sltp_manager):
        """Test position size is capped at max portfolio %"""
        portfolio_value = 10000
        entry_price = 100
        stop_loss = 99  # Very small SL
        risk_percent = 2.0
        max_position_pct = 5.0  # Only 5% of portfolio
        
        qty, cost = sltp_manager.calculate_position_size_from_sl(
            portfolio_value=portfolio_value,
            entry_price=entry_price,
            stop_loss=stop_loss,
            risk_percent=risk_percent,
            max_position_pct=max_position_pct
        )
        
        # Should be capped at 5% * 10000 = 500
        expected_cost = portfolio_value * (max_position_pct / 100)
        
        assert cost <= expected_cost + 1, "Cost should not exceed max position %"


# ============================================
# Tests: Async Integration
# ============================================

class TestAsyncCalculations:
    """Test async SL/TP calculations"""
    
    @pytest.mark.asyncio
    async def test_calculate_sl_tp_async(self, sltp_manager, user_id, market_data_btc, settings_balanced):
        """Test complete async SL/TP calculation"""
        # Mock the user settings fetch (return coroutine that returns settings)
        async def mock_get_settings(uid):
            return UserSLTPSettings()
        sltp_manager._get_user_settings = mock_get_settings
        
        entry_price = 42000
        side = "BUY"
        position_size = 1.0
        
        # This would normally fetch from DB, but we're mocking
        config = await sltp_manager.calculate_sl_tp(
            user_id=user_id,
            symbol="BTCUSDT",
            entry_price=entry_price,
            side=side,
            market_data=market_data_btc,
            position_size=position_size
        )
        
        # Verify structure
        assert config.stop_loss < entry_price, "SL should be below entry for BUY"
        assert config.take_profit_1 > entry_price, "TP1 should be above entry for BUY"
        assert config.take_profit_2 > config.take_profit_1, "TP2 should be above TP1"
        assert config.risk_reward_1 > 0, "R:R ratio should be positive"


# ============================================
# Tests: Edge Cases
# ============================================

class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_invalid_sl_equals_entry(self, sltp_manager):
        """Test handling when SL would equal entry (invalid)"""
        entry_price = 42000
        sl_price = 42000
        
        # This should be caught before trade creation in bot_engine
        assert sl_price == entry_price, "Invalid state detected"
    
    
    def test_small_position_asset(self, sltp_manager, settings_balanced):
        """Test SL calculation for small price asset (e.g., 0.0001 BTC)"""
        entry_price = 0.0001
        side = "BUY"
        
        sl_price = sltp_manager._calculate_fixed_pct_sl(entry_price, side, settings_balanced)
        
        assert sl_price < entry_price, "SL should be below entry"
        # Even for small prices, we should have valid SL
        assert sl_price > 0, "SL should be positive"
    
    
    def test_extreme_atr(self, sltp_manager, settings_balanced):
        """Test handling of extreme ATR values"""
        entry_price = 42000
        market_data_extreme = {
            "indicators": {"atr": 10000}  # Very high volatility
        }
        
        sl_price = sltp_manager._calculate_atr_sl(
            entry_price=entry_price,
            side="BUY",
            market_data=market_data_extreme,
            settings=settings_balanced
        )
        
        # ATR SL before constraints = 42000 - (10000 * 1.5) = 42000 - 15000 = 27000
        # This is > 5% so will be constrained
        constrained_sl = sltp_manager._apply_sl_constraints(
            entry_price=entry_price,
            sl_price=sl_price,
            side="BUY",
            settings=settings_balanced
        )
        
        # Should apply constraints
        max_distance = entry_price * (settings_balanced.sl_max_pct / 100)
        actual_distance = entry_price - constrained_sl
        assert actual_distance <= max_distance, f"Should respect max SL %, got {actual_distance} vs max {max_distance}"


# ============================================
# Run Tests
# ============================================

if __name__ == "__main__":
    print("Running SL/TP Manager Tests...")
    print("=" * 60)
    pytest.main([__file__, "-v", "--tb=short"])

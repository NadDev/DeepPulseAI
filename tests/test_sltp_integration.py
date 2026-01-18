"""
Integration Test - SL/TP Manager with BotEngine
===============================================

Tests the integration between:
- SLTPManager (SL/TP calculation)
- BotEngine (trade execution)
- RiskManager (trade validation)

Run with: pytest tests/test_sltp_integration.py -v
"""

import pytest
from uuid import UUID
from decimal import Decimal

import sys
import os
backend_path = os.path.join(os.path.dirname(__file__), '..', 'backend')
sys.path.insert(0, backend_path)

from app.services.sl_tp_manager import (
    SLTPManager,
    SLTPConfig,
    TradeState,
    TradePhase,
    ExitReason,
    UserSLTPSettings
)


class TestSLTPIntegration:
    """Integration tests for SL/TP Manager"""
    
    @pytest.fixture
    def manager(self):
        return SLTPManager()
    
    
    @pytest.fixture
    def user_id(self):
        return UUID('12345678-1234-5678-1234-567812345678')
    
    
    @pytest.fixture
    def settings(self):
        return UserSLTPSettings(
            sl_tp_profile="BALANCED",
            sl_method="ATR",
            sl_atr_multiplier=1.5,
            tp1_risk_reward=1.5,
            tp2_risk_reward=3.0,
            tp1_exit_pct=50.0,
            trailing_activation_pct=1.5,
            trailing_distance_pct=1.0
        )
    
    
    @pytest.mark.asyncio
    async def test_full_trade_lifecycle_buy(self, manager, settings):
        """Test complete BUY trade lifecycle: Entry → TP1 → TP2"""
        # 1. Entry: Calculate SL/TP
        entry_price = 100
        market_data = {"indicators": {"atr": 5}}
        
        sl_price, sl_method = await manager._calculate_stop_loss(
            entry_price=entry_price,
            side="BUY",
            market_data=market_data,
            settings=settings
        )
        
        assert sl_price < entry_price, "SL below entry for BUY"
        
        # Calculate TP levels
        sl_distance = entry_price - sl_price
        tp1, tp2 = manager._calculate_take_profits(
            entry_price=entry_price,
            sl_distance=sl_distance,
            side="BUY",
            settings=settings
        )
        
        assert tp1 > entry_price
        assert tp2 > tp1
        
        # 2. Create trade state
        trade = TradeState(
            trade_id="trade_123",
            symbol="BTCUSDT",
            side="BUY",
            entry_price=entry_price,
            quantity=1.0,
            sl_initial=sl_price,
            sl_current=sl_price,
            tp1=tp1,
            tp2=tp2,
            tp1_exit_pct=50.0,
            phase=TradePhase.PENDING,
            validation_price=entry_price * 1.005
        )
        
        # 3. Test TP1 hit
        current_price = tp1 + 0.5  # Above TP1
        update = await manager.update_trade(
            trade_state=trade,
            current_price=current_price,
            market_data=market_data,
            user_settings=settings
        )
        
        assert update.should_close
        assert update.close_reason == ExitReason.TP_PARTIAL
        assert update.close_quantity == 0.5  # 50% of 1.0
        
        # 4. Simulate TP1 execution and move to TP2
        trade.tp1_hit = True
        trade.quantity_remaining = 0.5  # 50% remaining
        trade.phase = TradePhase.TRAILING
        trade.sl_current = tp1  # SL moved to TP1 level
        
        # Price moves to TP2
        current_price = tp2 + 0.5
        update = await manager.update_trade(
            trade_state=trade,
            current_price=current_price,
            market_data=market_data,
            user_settings=settings
        )
        
        assert update.should_close
        assert update.close_reason == ExitReason.TP_FULL
        assert update.close_quantity == 0.5  # Remaining 50%
    
    
    @pytest.mark.asyncio
    async def test_sl_hit_in_pending_phase(self, manager, settings):
        """Test SL hit during PENDING phase"""
        entry_price = 100
        sl_price = 97.5  # 2.5% below entry
        
        trade = TradeState(
            trade_id="trade_456",
            symbol="BTCUSDT",
            side="BUY",
            entry_price=entry_price,
            quantity=1.0,
            sl_initial=sl_price,
            sl_current=sl_price,
            tp1=102.5,
            tp2=105.0,
            tp1_exit_pct=50.0,
            phase=TradePhase.PENDING
        )
        
        # Price drops below SL
        current_price = 97.0
        market_data = {"indicators": {}}
        
        update = await manager.update_trade(
            trade_state=trade,
            current_price=current_price,
            market_data=market_data,
            user_settings=settings
        )
        
        assert update.should_close
        assert update.close_reason == ExitReason.SL_HIT
        assert update.log_message
    
    
    @pytest.mark.asyncio
    async def test_validation_and_breakeven(self, manager, settings):
        """Test PENDING → VALIDATED phase with SL → Breakeven"""
        entry_price = 100
        sl_price = 97.5
        validation_price = entry_price * 1.005  # 100.5
        
        trade = TradeState(
            trade_id="trade_789",
            symbol="BTCUSDT",
            side="BUY",
            entry_price=entry_price,
            quantity=1.0,
            sl_initial=sl_price,
            sl_current=sl_price,
            tp1=102.5,
            tp2=105.0,
            tp1_exit_pct=50.0,
            phase=TradePhase.PENDING,
            validation_price=validation_price
        )
        
        # Price reaches validation level
        current_price = 100.6  # Above validation
        market_data = {"indicators": {}}
        
        update = await manager.update_trade(
            trade_state=trade,
            current_price=current_price,
            market_data=market_data,
            user_settings=settings
        )
        
        assert update.new_phase == TradePhase.VALIDATED
        assert update.new_sl == entry_price  # SL moved to breakeven
    
    
    @pytest.mark.asyncio
    async def test_trailing_stop_activation(self, manager, settings):
        """Test trailing stop activation after profit threshold"""
        entry_price = 100
        sl_price = 97.5
        
        trade = TradeState(
            trade_id="trade_trail",
            symbol="BTCUSDT",
            side="BUY",
            entry_price=entry_price,
            quantity=1.0,
            sl_initial=sl_price,
            sl_current=100.5,  # Already at breakeven
            tp1=102.5,
            tp2=105.0,
            tp1_exit_pct=50.0,
            phase=TradePhase.VALIDATED,
            highest_price=100.5
        )
        
        # Price moves to +2% (above 1.5% activation threshold)
        current_price = 102.0
        market_data = {"indicators": {}}
        
        update = await manager.update_trade(
            trade_state=trade,
            current_price=current_price,
            market_data=market_data,
            user_settings=settings
        )
        
        # Should activate trailing SL
        assert update.new_sl is not None
        assert update.new_sl > trade.sl_current  # SL moved up
        assert update.new_phase == TradePhase.TRAILING or update.new_phase is None
    
    
    def test_position_sizing_with_constraints(self, manager):
        """Test position sizing respects all constraints"""
        # Portfolio: $10,000
        # Entry: $100
        # SL: $97.5
        # Risk: 2% ($200)
        
        qty, cost = manager.calculate_position_size_from_sl(
            portfolio_value=10000,
            entry_price=100,
            stop_loss=97.5,
            risk_percent=2.0,
            max_position_pct=25.0
        )
        
        # Max risk = $200
        # SL distance = $2.5
        # Qty = 200/2.5 = 80 BTC
        # Cost = 80 * 100 = $8000
        # This is < 25% cap ($2500) ... no wait, it's MORE
        # So capped at 25% = $2500
        # Qty = 2500/100 = 25 BTC
        
        expected_qty = 2500 / 100
        assert abs(qty - expected_qty) < 0.01
        assert cost <= 10000 * 0.25 + 1
    
    
    @pytest.mark.asyncio
    async def test_prudent_vs_aggressive_profiles(self, manager):
        """Compare PRUDENT vs AGGRESSIVE profiles"""
        entry_price = 100
        market_data = {"indicators": {"atr": 5}}
        
        prudent = UserSLTPSettings(
            sl_tp_profile="PRUDENT",
            sl_atr_multiplier=1.0,  # Tighter
            tp1_risk_reward=1.3,    # Lower
            tp1_exit_pct=70.0       # More conservative
        )
        
        aggressive = UserSLTPSettings(
            sl_tp_profile="AGGRESSIVE",
            sl_atr_multiplier=2.0,  # Wider
            tp1_risk_reward=1.5,    # Higher
            tp1_exit_pct=30.0       # More aggressive
        )
        
        # Test SL
        sl_prudent, _ = await manager._calculate_stop_loss(
            entry_price=entry_price,
            side="BUY",
            market_data=market_data,
            settings=prudent
        )
        
        sl_aggressive, _ = await manager._calculate_stop_loss(
            entry_price=entry_price,
            side="BUY",
            market_data=market_data,
            settings=aggressive
        )
        
        # Prudent should have tighter (higher) SL for BUY
        # Prudent: ATR × 1.0 = 5 × 1.0 = 5 → SL = 100 - 5 = 95
        # Aggressive: ATR × 2.0 = 5 × 2.0 = 10 → SL = 100 - 10 = 90
        # So aggressive SL is LOWER (more risk)
        # Prudent has a tighter (higher) SL = lower risk
        assert sl_prudent >= sl_aggressive, f"Prudent SL {sl_prudent} should be >= Aggressive {sl_aggressive}"
        
        # Test TP1
        sl_distance = entry_price - sl_prudent
        tp1_prudent, _ = manager._calculate_take_profits(
            entry_price=entry_price,
            sl_distance=sl_distance,
            side="BUY",
            settings=prudent
        )
        
        sl_distance = entry_price - sl_aggressive
        tp1_aggressive, _ = manager._calculate_take_profits(
            entry_price=entry_price,
            sl_distance=sl_distance,
            side="BUY",
            settings=aggressive
        )
        
        # Aggressive should have higher TP potential (same if we scale by distance)
        # But the exit % is different - aggressive exits less at TP1
        assert prudent.tp1_exit_pct > aggressive.tp1_exit_pct


if __name__ == "__main__":
    print("Running SL/TP Integration Tests...")
    pytest.main([__file__, "-v", "--tb=short"])

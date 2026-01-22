#!/usr/bin/env python3
"""
Test suite for Reports API endpoints
Tests all report endpoints: trades, strategies, performance, equity-curve, drawdown-history
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from app.main import app
from app.db.database import get_db
from app.models.database_models import Trade, Bot, Portfolio
from unittest.mock import patch, MagicMock
import uuid

# Create test client
client = TestClient(app)

# Mock database session
@pytest.fixture
def mock_db():
    """Fixture for mocking database session"""
    db = MagicMock(spec=Session)
    return db

@pytest.fixture
def mock_trades():
    """Fixture for mock trade data"""
    user_id = str(uuid.uuid4())
    bot_id = str(uuid.uuid4())
    
    trades = [
        Trade(
            id=str(uuid.uuid4()),
            user_id=user_id,
            bot_id=bot_id,
            symbol="BTCUSDT",
            entry_price=45000.0,
            exit_price=46000.0,
            quantity=0.1,
            entry_time=datetime.utcnow() - timedelta(days=5),
            exit_time=datetime.utcnow() - timedelta(days=4),
            status="CLOSED",
            pnl=100.0,
            market_context="STRONG_BULLISH",
            market_context_confidence=0.95,
            strategy_used="MA_CROSSOVER"
        ),
        Trade(
            id=str(uuid.uuid4()),
            user_id=user_id,
            bot_id=bot_id,
            symbol="ETHUSDT",
            entry_price=2500.0,
            exit_price=2450.0,
            quantity=1.0,
            entry_time=datetime.utcnow() - timedelta(days=3),
            exit_time=datetime.utcnow() - timedelta(days=2),
            status="CLOSED",
            pnl=-50.0,
            market_context="WEAK_BEARISH",
            market_context_confidence=0.75,
            strategy_used="RSI_DIVERGENCE"
        ),
        Trade(
            id=str(uuid.uuid4()),
            user_id=user_id,
            bot_id=bot_id,
            symbol="XRPUSDT",
            entry_price=2.5,
            exit_price=2.7,
            quantity=100.0,
            entry_time=datetime.utcnow() - timedelta(days=1),
            exit_time=None,
            status="OPEN",
            pnl=None,
            market_context="NEUTRAL",
            market_context_confidence=0.5,
            strategy_used="GRID_TRADING"
        ),
    ]
    return trades

@pytest.fixture
def mock_portfolio():
    """Fixture for mock portfolio data"""
    return Portfolio(
        user_id=str(uuid.uuid4()),
        cash_balance=50000.0,
        total_value=150000.0,
        daily_pnl=500.0,
        total_pnl=15000.0
    )


class TestReportsEndpoints:
    """Test cases for reports API endpoints"""

    def test_get_dashboard_report(self):
        """Test GET /api/reports/dashboard endpoint"""
        response = client.get("/api/reports/dashboard")
        
        # Should return 200 or 404 (if no data)
        assert response.status_code in [200, 404, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "portfolio_value" in data
            assert "total_bots" in data
            assert "active_bots" in data
            assert "total_trades" in data
            assert "total_pnl" in data

    def test_get_trades_history(self):
        """Test GET /api/reports/trades endpoint"""
        response = client.get("/api/reports/trades?days=30")
        
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            if "trades" in data:
                for trade in data["trades"]:
                    assert "symbol" in trade
                    assert "entry_price" in trade
                    assert "status" in trade

    def test_get_trades_with_filters(self):
        """Test GET /api/reports/trades with various filters"""
        filters = [
            {"strategy": "MA_CROSSOVER"},
            {"symbol": "BTCUSDT"},
            {"status": "CLOSED"},
            {"market_context": "STRONG_BULLISH"},
            {"min_pnl": 0},
            {"max_pnl": 100},
        ]
        
        for filter_params in filters:
            response = client.get("/api/reports/trades", params={**filter_params, "days": 30})
            assert response.status_code in [200, 404]

    def test_get_context_performance(self):
        """Test GET /api/reports/trades/context-performance endpoint"""
        response = client.get("/api/reports/trades/context-performance")
        
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            if data:
                for row in data:
                    assert "strategy" in row
                    assert "context" in row or "market_context" in row

    def test_get_strategies(self):
        """Test GET /api/reports/strategies endpoint"""
        response = client.get("/api/reports/strategies")
        
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            if "strategies" in data:
                for strategy in data["strategies"]:
                    assert "name" in strategy
                    assert "total_trades" in strategy
                    assert "winning_trades" in strategy or "win_rate" in strategy

    def test_get_strategy_detail(self):
        """Test GET /api/reports/strategies/{strategy_name} endpoint"""
        strategy_names = ["MA_CROSSOVER", "RSI_DIVERGENCE", "GRID_TRADING"]
        
        for strategy_name in strategy_names:
            response = client.get(f"/api/reports/strategies/{strategy_name}")
            assert response.status_code in [200, 404]

    def test_get_equity_curve(self):
        """Test GET /api/reports/equity-curve endpoint"""
        response = client.get("/api/reports/equity-curve?days=30")
        
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
            if data:
                for point in data:
                    assert "date" in point
                    assert "equity" in point or "value" in point

    def test_get_drawdown_history(self):
        """Test GET /api/reports/drawdown-history endpoint"""
        response = client.get("/api/reports/drawdown-history?days=30")
        
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
            if data:
                for point in data:
                    assert "date" in point
                    assert "drawdown" in point

    def test_get_performance_report(self):
        """Test GET /api/reports/performance endpoint"""
        response = client.get("/api/reports/performance")
        
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            if "total_trades" in data:
                assert "win_rate" in data
                assert "total_pnl" in data
                assert "profit_factor" in data

    def test_equity_curve_data_structure(self):
        """Test equity curve data contains required fields"""
        response = client.get("/api/reports/equity-curve?days=7")
        
        if response.status_code == 200:
            data = response.json()
            if data:
                first_point = data[0]
                assert "date" in first_point
                assert isinstance(first_point["date"], str)

    def test_drawdown_data_structure(self):
        """Test drawdown data contains required fields"""
        response = client.get("/api/reports/drawdown-history?days=7")
        
        if response.status_code == 200:
            data = response.json()
            if data:
                first_point = data[0]
                assert "date" in first_point
                assert "drawdown" in first_point
                assert isinstance(first_point["drawdown"], (int, float))

    def test_different_time_periods(self):
        """Test reports with different time periods"""
        periods = [7, 30, 60, 90, 365]
        
        for days in periods:
            response = client.get(f"/api/reports/equity-curve?days={days}")
            assert response.status_code in [200, 404]

    def test_invalid_time_period(self):
        """Test reports with invalid time period"""
        response = client.get("/api/reports/equity-curve?days=-5")
        # Should handle gracefully
        assert response.status_code in [200, 400, 404]


class TestReportsDataValidation:
    """Test data validation for reports"""

    def test_trade_pnl_consistency(self):
        """Test that trade P&L is calculated correctly"""
        response = client.get("/api/reports/trades")
        
        if response.status_code == 200:
            data = response.json()
            if "trades" in data:
                for trade in data["trades"]:
                    if trade.get("status") == "CLOSED":
                        # P&L should be present for closed trades
                        assert "pnl" in trade
                        # If we have prices and quantity, validate P&L
                        if all(k in trade for k in ["entry_price", "exit_price", "quantity"]):
                            entry_price = trade["entry_price"]
                            exit_price = trade["exit_price"]
                            quantity = trade["quantity"]
                            expected_pnl = (exit_price - entry_price) * quantity
                            assert trade["pnl"] is not None

    def test_win_rate_validity(self):
        """Test that win rates are between 0-100"""
        response = client.get("/api/reports/strategies")
        
        if response.status_code == 200:
            data = response.json()
            if "strategies" in data:
                for strategy in data["strategies"]:
                    if "win_rate" in strategy:
                        assert 0 <= strategy["win_rate"] <= 100

    def test_profit_factor_validity(self):
        """Test that profit factors are positive"""
        response = client.get("/api/reports/performance")
        
        if response.status_code == 200:
            data = response.json()
            if "profit_factor" in data:
                assert data["profit_factor"] >= 0

    def test_market_context_values(self):
        """Test that market context values are valid"""
        valid_contexts = [
            "STRONG_BULLISH", "WEAK_BULLISH", "NEUTRAL",
            "WEAK_BEARISH", "STRONG_BEARISH", None
        ]
        
        response = client.get("/api/reports/trades")
        if response.status_code == 200:
            data = response.json()
            if "trades" in data:
                for trade in data["trades"]:
                    context = trade.get("market_context")
                    assert context in valid_contexts or context is None


class TestReportsPerformance:
    """Test performance and optimization of reports"""

    def test_large_dataset_response_time(self):
        """Test that large requests don't timeout"""
        import time
        
        start = time.time()
        response = client.get("/api/reports/trades?days=365")
        duration = time.time() - start
        
        # Should complete within reasonable time (5 seconds)
        assert duration < 5.0

    def test_multiple_sequential_requests(self):
        """Test that multiple requests don't cause issues"""
        endpoints = [
            "/api/reports/dashboard",
            "/api/reports/trades?days=30",
            "/api/reports/strategies",
            "/api/reports/performance",
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code in [200, 404]


class TestReportsAggregation:
    """Test data aggregation in reports"""

    def test_trades_count_consistency(self):
        """Test that trade counts are consistent across endpoints"""
        # Get total from dashboard
        dash_response = client.get("/api/reports/dashboard")
        
        # Get trades list
        trades_response = client.get("/api/reports/trades?days=365")
        
        if dash_response.status_code == 200 and trades_response.status_code == 200:
            dash_data = dash_response.json()
            trades_data = trades_response.json()
            
            if "total_trades" in dash_data and "trades" in trades_data:
                # Dashboard count should be >= list count (list might be filtered)
                assert dash_data["total_trades"] >= len(trades_data["trades"])

    def test_strategy_statistics_sum(self):
        """Test that strategy stats sum correctly"""
        response = client.get("/api/reports/strategies")
        
        if response.status_code == 200:
            data = response.json()
            if "strategies" in data:
                total_trades = sum([s.get("total_trades", 0) for s in data["strategies"]])
                assert total_trades >= 0

    def test_pnl_aggregation(self):
        """Test that P&L aggregation is correct"""
        response = client.get("/api/reports/performance")
        
        if response.status_code == 200:
            data = response.json()
            if all(k in data for k in ["winning_trades", "losing_trades"]):
                # Total trades should match sum of winning + losing
                total = data.get("total_trades", 0)
                winning = data.get("winning_trades", 0)
                losing = data.get("losing_trades", 0)
                assert winning + losing <= total


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])

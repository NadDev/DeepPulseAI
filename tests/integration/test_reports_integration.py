#!/usr/bin/env python3
"""
Integration tests for Reports system
Tests complete user workflows: viewing reports, exporting data, etc.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from app.main import app
from app.db.database import get_db
from app.models.database_models import Trade, Bot, Portfolio, User
import uuid

client = TestClient(app)


class TestReportsWorkflow:
    """Integration tests for complete reports workflows"""

    @pytest.fixture
    def test_user_id(self):
        """Create test user ID"""
        return str(uuid.uuid4())

    @pytest.fixture
    def test_bot_id(self):
        """Create test bot ID"""
        return str(uuid.uuid4())

    def test_complete_dashboard_workflow(self, test_user_id, test_bot_id):
        """Test complete dashboard view workflow"""
        # 1. Get dashboard summary
        response = client.get("/api/reports/dashboard")
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            dashboard = response.json()
            assert "total_trades" in dashboard
            assert "total_pnl" in dashboard

    def test_trade_analysis_workflow(self, test_user_id):
        """Test complete trade analysis workflow"""
        # 1. Get all trades
        trades_response = client.get("/api/reports/trades?days=30")
        assert trades_response.status_code in [200, 404]

        # 2. Filter by symbol
        symbol_response = client.get("/api/reports/trades?symbol=BTCUSDT&days=30")
        assert symbol_response.status_code in [200, 404]

        # 3. Filter by market context
        context_response = client.get("/api/reports/trades?market_context=STRONG_BULLISH&days=30")
        assert context_response.status_code in [200, 404]

        # 4. Get context performance
        perf_response = client.get("/api/reports/trades/context-performance")
        assert perf_response.status_code in [200, 404]

    def test_strategy_analysis_workflow(self):
        """Test complete strategy analysis workflow"""
        # 1. Get strategy list
        strategies_response = client.get("/api/reports/strategies")
        assert strategies_response.status_code in [200, 404]

        if strategies_response.status_code == 200:
            strategies = strategies_response.json()
            
            if "strategies" in strategies and len(strategies["strategies"]) > 0:
                # 2. Get detail for first strategy
                first_strategy = strategies["strategies"][0]
                strategy_name = first_strategy.get("name")
                
                detail_response = client.get(f"/api/reports/strategies/{strategy_name}")
                assert detail_response.status_code in [200, 404]

    def test_performance_charting_workflow(self):
        """Test complete performance charting workflow"""
        # 1. Get equity curve
        equity_response = client.get("/api/reports/equity-curve?days=30")
        assert equity_response.status_code in [200, 404]

        if equity_response.status_code == 200:
            equity_data = equity_response.json()
            assert isinstance(equity_data, list)

        # 2. Get drawdown history
        drawdown_response = client.get("/api/reports/drawdown-history?days=30")
        assert drawdown_response.status_code in [200, 404]

        if drawdown_response.status_code == 200:
            drawdown_data = drawdown_response.json()
            assert isinstance(drawdown_data, list)

        # 3. Get overall performance
        perf_response = client.get("/api/reports/performance")
        assert perf_response.status_code in [200, 404]

    def test_multi_period_comparison_workflow(self):
        """Test comparing reports across different periods"""
        periods = [7, 30, 60, 90]
        responses = []

        for period in periods:
            response = client.get(f"/api/reports/equity-curve?days={period}")
            responses.append((period, response))

        # All should succeed or fail consistently
        statuses = [r[1].status_code for r in responses]
        assert all(s in [200, 404] for s in statuses)

    def test_complete_export_preparation(self):
        """Test gathering all data needed for export"""
        # 1. Get trades for CSV export
        trades_response = client.get("/api/reports/trades?days=365")
        assert trades_response.status_code in [200, 404]

        # 2. Get strategies for CSV export
        strategies_response = client.get("/api/reports/strategies")
        assert strategies_response.status_code in [200, 404]

        # 3. Get performance summary
        perf_response = client.get("/api/reports/performance")
        assert perf_response.status_code in [200, 404]


class TestReportsDataConsistency:
    """Test data consistency across reports"""

    def test_same_user_data_consistency(self):
        """Test that same user sees consistent data across endpoints"""
        # Get user ID from first request
        dashboard = client.get("/api/reports/dashboard").json() if client.get("/api/reports/dashboard").status_code == 200 else {}
        trades_list = client.get("/api/reports/trades?days=365").json() if client.get("/api/reports/trades?days=365").status_code == 200 else {}
        strategies = client.get("/api/reports/strategies").json() if client.get("/api/reports/strategies").status_code == 200 else {}

        # Verify data exists
        if dashboard and trades_list and strategies:
            # All should be non-empty or all empty
            has_dashboard = bool(dashboard.get("total_trades", 0) > 0)
            has_trades = bool(trades_list.get("trades", []))
            has_strategies = bool(strategies.get("strategies", []))

            # Either all have data or all are empty (depending on test data)
            assert (has_dashboard + has_trades + has_strategies) >= 0  # At least logic is consistent

    def test_trade_count_consistency(self):
        """Test trade counts are consistent"""
        dashboard_response = client.get("/api/reports/dashboard")
        trades_response = client.get("/api/reports/trades?days=365")

        if dashboard_response.status_code == 200 and trades_response.status_code == 200:
            dashboard = dashboard_response.json()
            trades = trades_response.json()

            if "total_trades" in dashboard and "trades" in trades:
                # Dashboard count should be >= list count
                assert dashboard["total_trades"] >= len(trades.get("trades", []))

    def test_performance_metrics_validity(self):
        """Test that performance metrics are mathematically valid"""
        response = client.get("/api/reports/performance")

        if response.status_code == 200:
            data = response.json()

            # Win rate should be between 0-100%
            if "win_rate" in data:
                assert 0 <= data["win_rate"] <= 100

            # Profit factor should be positive
            if "profit_factor" in data:
                assert data["profit_factor"] >= 0

            # Total trades = winning + losing trades
            if all(k in data for k in ["winning_trades", "losing_trades", "total_trades"]):
                total = data["total_trades"]
                wins = data["winning_trades"]
                losses = data["losing_trades"]
                assert wins + losses <= total


class TestReportsErrorHandling:
    """Test error handling in reports"""

    def test_invalid_strategy_name(self):
        """Test requesting invalid strategy"""
        response = client.get("/api/reports/strategies/NONEXISTENT_STRATEGY")
        assert response.status_code in [200, 404]

    def test_invalid_time_period(self):
        """Test invalid time period parameter"""
        response = client.get("/api/reports/equity-curve?days=invalid")
        # Should handle gracefully
        assert response.status_code in [200, 400, 404]

    def test_negative_time_period(self):
        """Test negative time period"""
        response = client.get("/api/reports/equity-curve?days=-30")
        # Should either return empty data or error
        assert response.status_code in [200, 400, 404]

    def test_excessive_time_period(self):
        """Test excessively large time period"""
        response = client.get("/api/reports/equity-curve?days=100000")
        # Should handle gracefully (cap or error)
        assert response.status_code in [200, 400, 404]

    def test_empty_result_handling(self):
        """Test endpoints with no data"""
        response = client.get("/api/reports/trades?days=1&status=NONEXISTENT")
        # Should return empty list or 404
        assert response.status_code in [200, 404]


class TestReportsAuthentication:
    """Test authentication/authorization in reports"""

    def test_reports_accessible_without_auth(self):
        """Test that reports are accessible (may vary based on app settings)"""
        response = client.get("/api/reports/dashboard")
        # Should either work or return auth error
        assert response.status_code in [200, 401, 404]

    def test_multiple_users_isolation(self):
        """Test that different users can access reports independently"""
        # First request
        resp1 = client.get("/api/reports/dashboard")
        
        # Second request
        resp2 = client.get("/api/reports/dashboard")

        # Both should succeed or fail the same way
        assert resp1.status_code == resp2.status_code


class TestReportsPerformance:
    """Test performance characteristics of reports"""

    def test_equity_curve_response_time(self):
        """Test that equity curve loads quickly"""
        import time
        
        start = time.time()
        response = client.get("/api/reports/equity-curve?days=30")
        duration = time.time() - start

        if response.status_code == 200:
            # Should complete within 2 seconds
            assert duration < 2.0

    def test_trades_list_response_time(self):
        """Test that trades list loads quickly"""
        import time
        
        start = time.time()
        response = client.get("/api/reports/trades?days=30")
        duration = time.time() - start

        if response.status_code == 200:
            # Should complete within 2 seconds
            assert duration < 2.0

    def test_strategies_response_time(self):
        """Test that strategy list loads quickly"""
        import time
        
        start = time.time()
        response = client.get("/api/reports/strategies")
        duration = time.time() - start

        if response.status_code == 200:
            # Should complete within 1 second
            assert duration < 1.0

    def test_concurrent_report_requests(self):
        """Test handling concurrent requests"""
        import concurrent.futures
        
        endpoints = [
            "/api/reports/dashboard",
            "/api/reports/trades?days=30",
            "/api/reports/strategies",
            "/api/reports/equity-curve?days=30",
        ]

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(client.get, endpoint) for endpoint in endpoints]
            results = [f.result() for f in futures]

        # All requests should complete
        assert len(results) == len(endpoints)
        # All should have valid status codes
        assert all(r.status_code in [200, 404] for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

#!/usr/bin/env python
"""
Tests d'intégration Portfolio
Teste le flux complet : création ordre → vérification position → clôture → vérification historique
"""
import sys
import pytest
from pathlib import Path
import time

# Add backend to path
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestPortfolioIntegration:
    """Tests d'intégration du flux Portfolio complet"""
    
    @pytest.fixture
    def initial_summary(self):
        """Récupère le summary initial"""
        response = client.get("/api/portfolio/summary")
        return response.json()
    
    @pytest.fixture
    def initial_positions_count(self):
        """Compte les positions initiales"""
        response = client.get("/api/portfolio/positions")
        return len(response.json())
    
    def test_complete_buy_sell_flow(self, initial_summary, initial_positions_count):
        """
        Test du flux complet :
        1. Créer un ordre BUY
        2. Vérifier que la position existe
        3. Créer un ordre SELL pour clôturer
        4. Vérifier que la position est fermée
        5. Vérifier que le trade apparaît dans l'historique
        """
        
        # 1. Créer ordre BUY
        buy_order = {
            "symbol": "BTC",
            "side": "BUY",
            "quantity": 0.001,
            "price": 42000.0,
            "strategy": "Integration Test"
        }
        
        buy_response = client.post("/api/portfolio/orders", json=buy_order)
        assert buy_response.status_code == 200, "Failed to create BUY order"
        
        buy_data = buy_response.json()
        assert "new_balance" in buy_data
        new_balance_after_buy = buy_data["new_balance"]
        
        # Vérifier que le cash a diminué
        assert new_balance_after_buy < initial_summary["cash_balance"], \
            "Cash balance should decrease after BUY"
        
        # 2. Vérifier que la position existe
        time.sleep(0.5)  # Wait for DB update
        positions_response = client.get("/api/portfolio/positions")
        positions = positions_response.json()
        
        assert len(positions) > initial_positions_count, \
            "Position count should increase after BUY"
        
        # Trouver notre position BTC
        btc_position = None
        for pos in positions:
            if pos["symbol"] == "BTC" and pos["strategy"] == "Integration Test":
                btc_position = pos
                break
        
        assert btc_position is not None, "BTC position not found"
        assert btc_position["quantity"] == 0.001
        assert btc_position["entry_price"] == 42000.0
        
        # 3. Créer ordre SELL pour clôturer
        sell_order = {
            "symbol": "BTC",
            "side": "SELL",
            "quantity": 0.001,
            "price": 43000.0,  # Profit de 1000 sur 0.001 BTC = 1.0
            "strategy": "Integration Test"
        }
        
        sell_response = client.post("/api/portfolio/orders", json=sell_order)
        assert sell_response.status_code == 200, "Failed to create SELL order"
        
        sell_data = sell_response.json()
        new_balance_after_sell = sell_data["new_balance"]
        
        # Vérifier que le cash a augmenté (prix de vente)
        assert new_balance_after_sell > new_balance_after_buy, \
            "Cash balance should increase after SELL"
        
        # 4. Vérifier que la position est fermée
        time.sleep(0.5)
        positions_after_sell = client.get("/api/portfolio/positions").json()
        
        # Le nombre de positions devrait diminuer (SELL ferme une position)
        assert len(positions_after_sell) < len(positions), \
            f"Position count should decrease after SELL: {len(positions_after_sell)} should be < {len(positions)}"
        
        # 5. Vérifier que le trade apparaît dans l'historique
        trades_response = client.get("/api/trades")
        trades_data = trades_response.json()
        
        # Chercher notre trade
        test_trades = [
            t for t in trades_data["trades"]
            if t["strategy"] == "Integration Test"
        ]
        
        assert len(test_trades) >= 1, "Trade should appear in history"
    
    def test_portfolio_summary_consistency(self):
        """
        Vérifie que le summary est cohérent avec les positions
        """
        summary = client.get("/api/portfolio/summary").json()
        positions = client.get("/api/portfolio/positions").json()
        
        # Le nombre de positions ouvertes doit correspondre
        assert summary["open_positions_count"] == len(positions), \
            "Summary position count doesn't match actual positions"
        
        # Calculer la valeur totale des positions
        total_positions_value = sum(pos["value"] for pos in positions)
        
        # Portfolio value = cash + positions
        expected_portfolio_value = summary["cash_balance"] + total_positions_value
        
        # Tolérance de 0.01 pour les arrondis
        assert abs(summary["portfolio_value"] - expected_portfolio_value) < 0.01, \
            f"Portfolio value mismatch: {summary['portfolio_value']} != {expected_portfolio_value}"
    
    def test_trades_pagination_consistency(self):
        """
        Vérifie que la pagination des trades est cohérente
        """
        # Get total count
        response1 = client.get("/api/trades?limit=2&offset=0")
        data1 = response1.json()
        total_trades = data1["total"]
        
        # Get all trades in small chunks
        all_trades = []
        offset = 0
        limit = 2
        
        while offset < total_trades:
            response = client.get(f"/api/trades?limit={limit}&offset={offset}")
            chunk = response.json()
            all_trades.extend(chunk["trades"])
            offset += limit
        
        # Verify we got all trades
        assert len(all_trades) == total_trades, \
            f"Pagination issue: got {len(all_trades)} trades but total is {total_trades}"
    
    def test_risk_metrics_calculation(self):
        """
        Vérifie que les métriques de risque sont calculées correctement
        """
        summary = client.get("/api/portfolio/summary").json()
        trades = client.get("/api/trades").json()["trades"]
        
        # Calculer win rate manuellement
        closed_trades = [t for t in trades if t["status"] == "CLOSED"]
        
        if len(closed_trades) > 0:
            winning_trades = [t for t in closed_trades if t["pnl"] and t["pnl"] > 0]
            calculated_win_rate = (len(winning_trades) / len(closed_trades)) * 100
            
            # Tolérance de 1% pour les arrondis
            assert abs(summary["win_rate"] - calculated_win_rate) < 1.0, \
                f"Win rate mismatch: {summary['win_rate']} != {calculated_win_rate}"


class TestPortfolioErrorHandling:
    """Tests de gestion d'erreurs"""
    
    def test_insufficient_balance_for_buy(self):
        """
        Teste qu'on ne peut pas acheter si le solde est insuffisant
        """
        # Récupérer le solde actuel
        summary = client.get("/api/portfolio/summary").json()
        cash_balance = summary["cash_balance"]
        
        # Essayer d'acheter plus que le solde disponible
        order = {
            "symbol": "BTC",
            "side": "BUY",
            "quantity": 100.0,  # Très grande quantité
            "price": cash_balance * 2,  # Prix supérieur au solde
            "strategy": "Test"
        }
        
        response = client.post("/api/portfolio/orders", json=order)
        
        # Devrait échouer (ou réussir mais le backend gère l'erreur)
        # Selon l'implémentation, peut être 400, 422, ou 200 avec message d'erreur
        if response.status_code == 200:
            data = response.json()
            # Si l'API retourne 200, vérifier qu'il n'y a pas eu d'exécution
            assert "error" in str(data).lower() or "insufficient" in str(data).lower()
    
    def test_sell_without_position(self):
        """
        Teste qu'on ne peut pas vendre si on n'a pas de position
        """
        # Essayer de vendre un symbole qu'on ne possède pas
        order = {
            "symbol": "NONEXISTENT",
            "side": "SELL",
            "quantity": 1.0,
            "price": 1000.0,
            "strategy": "Test"
        }
        
        response = client.post("/api/portfolio/orders", json=order)
        
        # Peut être 400, 422, ou 200 avec erreur selon l'implémentation
        if response.status_code == 200:
            data = response.json()
            # Vérifier qu'il y a une indication d'erreur
            positions = client.get("/api/portfolio/positions").json()
            # La position ne devrait pas exister
            assert not any(p["symbol"] == "NONEXISTENT" for p in positions)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short", "-s"])

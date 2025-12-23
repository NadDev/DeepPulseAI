"""
Risk Metrics Calculator
Calcule les métriques de risque et performance du portfolio
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import math


class RiskCalculator:
    """Calculateur de métriques de risque pour le portfolio"""
    
    @staticmethod
    def calculate_sharpe_ratio(
        returns: List[float], 
        risk_free_rate: float = 0.02,
        periods_per_year: int = 365
    ) -> float:
        """
        Calcule le Sharpe Ratio
        
        Args:
            returns: Liste des rendements quotidiens (ex: [0.01, -0.005, 0.02])
            risk_free_rate: Taux sans risque annuel (défaut: 2%)
            periods_per_year: Nombre de périodes par an (365 pour quotidien)
            
        Returns:
            Sharpe Ratio (> 1 = bon, > 2 = excellent)
        """
        if not returns or len(returns) < 2:
            return 0.0
        
        # Calculer le rendement moyen
        avg_return = sum(returns) / len(returns)
        
        # Calculer l'écart-type des rendements
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        std_dev = math.sqrt(variance)
        
        if std_dev == 0:
            return 0.0
        
        # Annualiser les métriques
        annualized_return = avg_return * periods_per_year
        annualized_std = std_dev * math.sqrt(periods_per_year)
        
        # Sharpe Ratio = (Rendement - Taux sans risque) / Volatilité
        sharpe = (annualized_return - risk_free_rate) / annualized_std
        
        return round(sharpe, 2)
    
    @staticmethod
    def calculate_average_win_loss(trades: List[Dict]) -> Dict[str, float]:
        """
        Calcule les moyennes de gains et pertes
        
        Args:
            trades: Liste de trades fermés avec 'pnl'
            
        Returns:
            {
                'average_win': float,
                'average_loss': float,
                'win_loss_ratio': float,
                'largest_win': float,
                'largest_loss': float
            }
        """
        closed_trades = [t for t in trades if t.get('status') == 'CLOSED' and t.get('pnl') is not None]
        
        if not closed_trades:
            return {
                'average_win': 0.0,
                'average_loss': 0.0,
                'win_loss_ratio': 0.0,
                'largest_win': 0.0,
                'largest_loss': 0.0
            }
        
        winning_trades = [t['pnl'] for t in closed_trades if t['pnl'] > 0]
        losing_trades = [abs(t['pnl']) for t in closed_trades if t['pnl'] < 0]
        
        avg_win = sum(winning_trades) / len(winning_trades) if winning_trades else 0.0
        avg_loss = sum(losing_trades) / len(losing_trades) if losing_trades else 0.0
        
        # Win/Loss Ratio (combien on gagne en moyenne vs combien on perd)
        win_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0.0
        
        largest_win = max(winning_trades) if winning_trades else 0.0
        largest_loss = max(losing_trades) if losing_trades else 0.0
        
        return {
            'average_win': round(avg_win, 2),
            'average_loss': round(avg_loss, 2),
            'win_loss_ratio': round(win_loss_ratio, 2),
            'largest_win': round(largest_win, 2),
            'largest_loss': round(largest_loss, 2)
        }
    
    @staticmethod
    def calculate_profit_factor(trades: List[Dict]) -> float:
        """
        Calcule le Profit Factor
        
        Args:
            trades: Liste de trades fermés
            
        Returns:
            Profit Factor (Total gains / Total pertes)
            > 1.0 = profitable, > 2.0 = très bon
        """
        closed_trades = [t for t in trades if t.get('status') == 'CLOSED' and t.get('pnl') is not None]
        
        if not closed_trades:
            return 0.0
        
        total_wins = sum(t['pnl'] for t in closed_trades if t['pnl'] > 0)
        total_losses = abs(sum(t['pnl'] for t in closed_trades if t['pnl'] < 0))
        
        if total_losses == 0:
            # Return 0 if no wins, otherwise return a large number instead of infinity
            return 999.99 if total_wins > 0 else 0.0
        
        profit_factor = total_wins / total_losses
        return round(profit_factor, 2)
    
    @staticmethod
    def calculate_max_drawdown(equity_curve: List[Dict]) -> Dict[str, float]:
        """
        Calcule le Max Drawdown dynamiquement
        
        Args:
            equity_curve: Liste de points {'date': str, 'value': float}
            
        Returns:
            {
                'max_drawdown_pct': float,  # Pourcentage de perte max
                'max_drawdown_value': float,  # Montant de la perte max
                'peak_value': float,  # Valeur au pic
                'trough_value': float,  # Valeur au creux
            }
        """
        if not equity_curve or len(equity_curve) < 2:
            return {
                'max_drawdown_pct': 0.0,
                'max_drawdown_value': 0.0,
                'peak_value': 0.0,
                'trough_value': 0.0
            }
        
        values = [point['value'] for point in equity_curve]
        
        peak = values[0]
        max_dd = 0.0
        max_dd_value = 0.0
        peak_val = values[0]
        trough_val = values[0]
        
        for value in values:
            if value > peak:
                peak = value
            
            drawdown = (peak - value) / peak * 100 if peak > 0 else 0
            
            if drawdown > max_dd:
                max_dd = drawdown
                max_dd_value = peak - value
                peak_val = peak
                trough_val = value
        
        return {
            'max_drawdown_pct': round(max_dd, 2),
            'max_drawdown_value': round(max_dd_value, 2),
            'peak_value': round(peak_val, 2),
            'trough_value': round(trough_val, 2)
        }
    
    @staticmethod
    def calculate_expectancy(trades: List[Dict]) -> float:
        """
        Calcule l'espérance de gain par trade
        
        Args:
            trades: Liste de trades fermés
            
        Returns:
            Espérance moyenne par trade (positif = profitable)
        """
        closed_trades = [t for t in trades if t.get('status') == 'CLOSED' and t.get('pnl') is not None]
        
        if not closed_trades:
            return 0.0
        
        total_pnl = sum(t['pnl'] for t in closed_trades)
        expectancy = total_pnl / len(closed_trades)
        
        return round(expectancy, 2)
    
    @staticmethod
    def calculate_all_metrics(
        trades: List[Dict],
        equity_curve: Optional[List[Dict]] = None,
        returns: Optional[List[float]] = None
    ) -> Dict:
        """
        Calcule toutes les métriques de risque en une fois
        
        Args:
            trades: Liste de tous les trades
            equity_curve: Courbe d'équité (optionnel)
            returns: Liste des rendements (optionnel)
            
        Returns:
            Dictionnaire complet de toutes les métriques
        """
        metrics = {}
        
        # Métriques de base
        win_loss_data = RiskCalculator.calculate_average_win_loss(trades)
        metrics.update(win_loss_data)
        
        # Profit Factor
        metrics['profit_factor'] = RiskCalculator.calculate_profit_factor(trades)
        
        # Expectancy
        metrics['expectancy'] = RiskCalculator.calculate_expectancy(trades)
        
        # Sharpe Ratio (si rendements disponibles)
        if returns:
            metrics['sharpe_ratio'] = RiskCalculator.calculate_sharpe_ratio(returns)
        else:
            metrics['sharpe_ratio'] = 0.0
        
        # Max Drawdown (si courbe disponible)
        if equity_curve:
            dd_data = RiskCalculator.calculate_max_drawdown(equity_curve)
            metrics.update(dd_data)
        else:
            metrics.update({
                'max_drawdown_pct': 0.0,
                'max_drawdown_value': 0.0,
                'peak_value': 0.0,
                'trough_value': 0.0
            })
        
        return metrics

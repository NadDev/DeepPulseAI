"""
==============================================
RISK MANAGEMENT - Trading Limits & Validation
==============================================

Valide toutes les trades avant exécution
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from app.config import settings
from dataclasses import dataclass


@dataclass
class RiskValidation:
    """Résultat de la validation de risque"""
    is_valid: bool
    reason: str = ""
    warnings: List[str] = None


class RiskManager:
    """Valide les trades avant exécution"""
    
    def __init__(self):
        self.daily_losses = {}  # {date: amount}
        self.daily_trades = {}  # {date: count}
        self.open_positions = []
    
    def validate_trade(
        self,
        symbol: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        position_size: float,
        account_balance: float,
    ) -> RiskValidation:
        """Valide une trade avant exécution"""
        
        warnings = []
        
        # 1. Vérifier la taille de position (max 5% du capital)
        position_percent = (position_size * entry_price) / account_balance * 100
        if position_percent > settings.MAX_POSITION_SIZE_PERCENT:
            return RiskValidation(
                is_valid=False,
                reason=f"Position size {position_percent:.2f}% exceeds max {settings.MAX_POSITION_SIZE_PERCENT}%"
            )
        
        # 2. Vérifier le drawdown quotidien (max 10%)
        daily_loss = self._calculate_daily_loss()
        if daily_loss > settings.MAX_DAILY_LOSS_PERCENT:
            return RiskValidation(
                is_valid=False,
                reason=f"Daily loss {daily_loss:.2f}% exceeds max {settings.MAX_DAILY_LOSS_PERCENT}%"
            )
        
        # 3. Vérifier le nombre de trades par jour
        daily_trade_count = self._get_daily_trade_count()
        if daily_trade_count >= settings.MAX_TRADES_PER_DAY:
            return RiskValidation(
                is_valid=False,
                reason=f"Max {settings.MAX_TRADES_PER_DAY} trades per day reached"
            )
        
        # 4. Vérifier le ratio risque/récompense (minimum 1:1)
        risk = entry_price - stop_loss
        reward = take_profit - entry_price
        risk_reward_ratio = reward / risk if risk > 0 else 0
        
        if risk_reward_ratio < 1.0:
            warnings.append(f"Low risk/reward ratio: {risk_reward_ratio:.2f}:1 (minimum 1:1)")
        
        # 5. Vérifier les positions existantes
        if len(self.open_positions) > 0:
            if self._has_conflicting_position(symbol):
                warnings.append(f"Position already exists for {symbol}")
        
        return RiskValidation(
            is_valid=True,
            warnings=warnings
        )
    
    def _calculate_daily_loss(self) -> float:
        """Calcule la perte du jour en %"""
        today = datetime.now().date()
        daily_loss = self.daily_losses.get(str(today), 0.0)
        return daily_loss
    
    def _get_daily_trade_count(self) -> int:
        """Compte le nombre de trades du jour"""
        today = datetime.now().date()
        return self.daily_trades.get(str(today), 0)
    
    def _has_conflicting_position(self, symbol: str) -> bool:
        """Vérifie s'il existe une position ouverte sur ce symbole"""
        return any(pos["symbol"] == symbol for pos in self.open_positions)
    
    def register_trade(self, symbol: str, entry_price: float, position_size: float):
        """Enregistre une trade exécutée"""
        self.open_positions.append({
            "symbol": symbol,
            "entry_price": entry_price,
            "position_size": position_size,
            "timestamp": datetime.now()
        })
        
        today = datetime.now().date()
        self.daily_trades[str(today)] = self.daily_trades.get(str(today), 0) + 1
    
    def close_position(self, symbol: str, exit_price: float) -> float:
        """Clôture une position et retourne le P&L"""
        position = None
        for i, pos in enumerate(self.open_positions):
            if pos["symbol"] == symbol:
                position = self.open_positions.pop(i)
                break
        
        if not position:
            return 0.0
        
        pnl = (exit_price - position["entry_price"]) * position["position_size"]
        
        # Enregistre la perte du jour
        today = datetime.now().date()
        if pnl < 0:
            loss_percent = abs(pnl) / (position["entry_price"] * position["position_size"]) * 100
            self.daily_losses[str(today)] = self.daily_losses.get(str(today), 0) + loss_percent
        
        return pnl


# Instance globale
risk_manager = RiskManager()

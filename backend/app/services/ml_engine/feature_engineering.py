"""
==============================================
ML ENGINE - Feature Engineering Module
==============================================

Crée les features (variables) pour les modèles ML
"""

import numpy as np
from typing import Dict, List, Tuple
from app.services.technical_analysis import TechnicalAnalysis


class FeatureEngineer:
    """Extrait et crée des features à partir des données"""
    
    @staticmethod
    def create_features(
        prices: List[float],
        volumes: List[float],
        sentiment_scores: List[float] = None,
        rsi_period: int = 14,
    ) -> np.ndarray:
        """
        Crée une matrice de features pour LSTM
        
        Args:
            prices: Liste des prix [open, high, low, close]
            volumes: Liste des volumes
            sentiment_scores: Scores de sentiment optionnels
            rsi_period: Période RSI
        
        Returns:
            np.ndarray de shape (n_samples, n_features)
        """
        
        features = []
        
        # 1. Prix normalisés (min-max scaling)
        close_prices = [p if isinstance(p, float) else p[-1] for p in prices]
        normalized_prices = FeatureEngineer._min_max_scale(close_prices)
        features.append(normalized_prices)
        
        # 2. Rendements (returns) - momentum
        returns = FeatureEngineer._calculate_returns(close_prices)
        features.append(returns)
        
        # 3. Volume normalisé
        normalized_volumes = FeatureEngineer._min_max_scale(volumes)
        features.append(normalized_volumes)
        
        # 4. Volume momentum
        volume_momentum = np.diff(normalized_volumes, prepend=normalized_volumes[0])
        features.append(volume_momentum)
        
        # 5. RSI
        rsi = TechnicalAnalysis.calculate_rsi(close_prices, rsi_period)
        if rsi is None or all(x is None for x in rsi):
            rsi_normalized = np.full(len(close_prices), 0.5)  # Default neutral
        else:
            # Replace None values with 50 (neutral RSI)
            rsi_array = np.array([x if x is not None else 50.0 for x in rsi])
            rsi_normalized = np.clip(rsi_array / 100.0, 0, 1)  # Normaliser 0-1
        features.append(rsi_normalized)
        
        # 6. Volatilité (rolling std)
        volatility = FeatureEngineer._calculate_volatility(close_prices, period=20)
        features.append(volatility)
        
        # 7. SMA 20/50 ratio
        sma_20 = TechnicalAnalysis.calculate_sma(close_prices, 20)
        sma_50 = TechnicalAnalysis.calculate_sma(close_prices, 50)
        
        # Handle None returns and None elements from calculate_sma
        if sma_20 is None or all(x is None for x in sma_20):
            sma_20_array = np.array(close_prices)
        else:
            sma_20_array = np.array([x if x is not None else close_prices[i] for i, x in enumerate(sma_20)])
        
        if sma_50 is None or all(x is None for x in sma_50):
            sma_50_array = np.array(close_prices)
        else:
            sma_50_array = np.array([x if x is not None else close_prices[i] for i, x in enumerate(sma_50)])
        
        sma_ratio = np.array([
            s20 / s50 if s50 > 0 else 1.0
            for s20, s50 in zip(sma_20_array, sma_50_array)
        ])
        features.append(sma_ratio)
        
        # 8. Sentiment (si disponible)
        if sentiment_scores is not None:
            sentiment_normalized = FeatureEngineer._min_max_scale(sentiment_scores)
            features.append(sentiment_normalized)
        
        # 9. Trend direction (1=up, 0=neutral, -1=down)
        trend = np.array([
            1.0 if returns[i] > 0.001 else (-1.0 if returns[i] < -0.001 else 0.0)
            for i in range(len(returns))
        ])
        features.append(trend)
        
        # Stack toutes les features
        feature_matrix = np.column_stack(features)
        
        return feature_matrix
    
    @staticmethod
    def create_sequences(
        features: np.ndarray,
        lookback: int = 60,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Crée des séquences pour LSTM
        
        Args:
            features: Feature matrix de shape (n_samples, n_features)
            lookback: Nombre de jours pour regarder en arrière
        
        Returns:
            X: (n_sequences, lookback, n_features)
            y: (n_sequences,) - prix futurs normalisés
        """
        X, y = [], []
        
        for i in range(len(features) - lookback - 1):
            X.append(features[i:i+lookback])
            # Target = prix 1 jour après la fenêtre
            y.append(features[i+lookback, 0])  # Close price
        
        return np.array(X), np.array(y)
    
    @staticmethod
    def _min_max_scale(data: List[float]) -> np.ndarray:
        """Min-max normalization [0, 1]"""
        data = np.array(data)
        min_val = np.min(data)
        max_val = np.max(data)
        
        if max_val - min_val == 0:
            return np.zeros_like(data)
        
        return (data - min_val) / (max_val - min_val)
    
    @staticmethod
    def _calculate_returns(prices: List[float]) -> np.ndarray:
        """Calcule les rendements (returns) quotidiens"""
        prices = np.array(prices)
        returns = np.diff(prices) / prices[:-1]
        return np.concatenate([[0], returns])  # Prepend 0 for first value
    
    @staticmethod
    def _calculate_volatility(prices: List[float], period: int = 20) -> np.ndarray:
        """Calcule la volatilité (rolling std des returns)"""
        returns = FeatureEngineer._calculate_returns(prices)
        volatility = []
        
        for i in range(len(returns)):
            if i < period:
                vol = np.std(returns[:i+1]) if i > 0 else 0.0
            else:
                vol = np.std(returns[i-period:i])
            volatility.append(vol)
        
        return np.array(volatility)


# Test rapide
if __name__ == "__main__":
    # Données test
    test_prices = [100 + np.sin(i/10) * 10 for i in range(200)]
    test_volumes = [1000000 + np.random.randint(-100000, 100000) for i in range(200)]
    
    fe = FeatureEngineer()
    features = fe.create_features(test_prices, test_volumes)
    print(f"Features shape: {features.shape}")  # (200, 9)
    
    X, y = fe.create_sequences(features, lookback=60)
    print(f"X shape: {X.shape}")  # (139, 60, 9)
    print(f"y shape: {y.shape}")  # (139,)

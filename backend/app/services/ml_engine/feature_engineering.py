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

    # =========================================================================
    # Fix #5 — Feature Engineering v2 (12 features au lieu de 8)
    # NOTE: Le modèle LSTM actuel (lstm_model.keras) a input_shape=(60, 8).
    #       create_features_v2() produit 12 features — INCOMPATIBLE avec le
    #       modèle existant. Utiliser UNIQUEMENT pour l'entraînement d'un
    #       nouveau modèle (weekly retrain).
    # =========================================================================
    @staticmethod
    def create_features_v2(
        prices: List[float],
        volumes: List[float],
        highs: List[float] = None,
        lows: List[float] = None,
        rsi_period: int = 14,
    ) -> np.ndarray:
        """
        Feature Engineering v2 — 12 features (MACD, Bollinger %B, ATR inclus).
        
        Features produits (12 colonnes) :
            0  normalized_prices  — prix normalisé [0, 1]
            1  returns            — log-returns quotidiens
            2  normalized_volumes — volume normalisé [0, 1]
            3  volume_momentum    — ratio volume / rolling mean 20j
            4  rsi                — RSI [0, 1]
            5  volatility         — écart-type rolling 14j des returns
            6  sma_ratio          — ratio SMA7 / SMA21
            7  trend              — pente linéaire normalisée 14j
            8  macd_histogram     — (MACD line - signal) normalisé
            9  bollinger_pct_b    — position dans les bandes [0, 1]
           10  atr_normalized     — ATR 14 normalisé par le prix
           11  price_momentum     — ROC 10 jours normalisé
        
        Args:
            prices: Liste des prix de clôture
            volumes: Liste des volumes (même longueur que prices)
            highs:  Optionnel — prix hauts (pour ATR réel). Si None, estimé.
            lows:   Optionnel — prix bas (pour ATR réel). Si None, estimé.
            rsi_period: Période RSI (défaut 14)
        
        Returns:
            np.ndarray shape (n, 12)
        """
        prices_arr = np.array(prices, dtype=np.float64)
        volumes_arr = np.array(volumes, dtype=np.float64)
        n = len(prices_arr)

        # --- Features héritées de v1 ---
        min_p, max_p = prices_arr.min(), prices_arr.max()
        price_range = max_p - min_p if max_p > min_p else max_p * 0.1
        normalized_prices = (prices_arr - min_p) / price_range

        returns = np.zeros(n)
        for i in range(1, n):
            prev = prices_arr[i - 1] if prices_arr[i - 1] != 0 else 1e-10
            returns[i] = (prices_arr[i] - prev) / prev

        min_v, max_v = volumes_arr.min(), volumes_arr.max()
        vol_range = max_v - min_v if max_v > min_v else max_v * 0.1
        normalized_volumes = (volumes_arr - min_v) / vol_range

        volume_momentum = np.ones(n)
        win = 20
        for i in range(win, n):
            rolling_mean = np.mean(volumes_arr[i - win:i])
            volume_momentum[i] = volumes_arr[i] / rolling_mean if rolling_mean > 0 else 1.0
        volume_momentum = np.clip(volume_momentum, 0.0, 5.0) / 5.0

        rsi_raw = FeatureEngineer._calculate_rsi(prices, rsi_period)
        rsi_norm = rsi_raw / 100.0

        volatility = FeatureEngineer._calculate_volatility(prices, rsi_period)

        sma_ratio = np.ones(n)
        for i in range(20, n):
            sma7  = np.mean(prices_arr[max(0, i - 7):i])
            sma21 = np.mean(prices_arr[max(0, i - 21):i])
            sma_ratio[i] = (sma7 / sma21 - 1.0) if sma21 > 0 else 0.0
        sma_ratio = np.clip(sma_ratio, -0.2, 0.2) / 0.2

        trend = np.zeros(n)
        period_t = 14
        for i in range(period_t, n):
            seg = prices_arr[i - period_t:i]
            poly = np.polyfit(np.arange(period_t), seg, 1)
            avg_price = np.mean(seg) if np.mean(seg) != 0 else 1e-10
            trend[i] = poly[0] / avg_price
        trend = np.clip(trend, -0.05, 0.05) / 0.05

        # --- Nouvelles features v2 ---

        # Feature 8: MACD histogram normalisé
        # MACD = EMA12 - EMA26 ; Signal = EMA9(MACD)
        def _ema(data: np.ndarray, span: int) -> np.ndarray:
            alpha = 2.0 / (span + 1)
            ema = np.zeros(len(data))
            ema[0] = data[0]
            for i in range(1, len(data)):
                ema[i] = alpha * data[i] + (1 - alpha) * ema[i - 1]
            return ema

        ema12 = _ema(prices_arr, 12)
        ema26 = _ema(prices_arr, 26)
        macd_line = ema12 - ema26
        signal_line = _ema(macd_line, 9)
        macd_hist = macd_line - signal_line
        hist_scale = np.std(macd_hist) * 3 + 1e-10
        macd_histogram = np.clip(macd_hist / hist_scale, -1.0, 1.0)

        # Feature 9: Bollinger %B
        # %B = (price - lower_band) / (upper_band - lower_band)
        bb_period = 20
        bollinger_pct_b = np.full(n, 0.5)
        for i in range(bb_period, n):
            seg = prices_arr[i - bb_period:i]
            mean_bb = np.mean(seg)
            std_bb  = np.std(seg) + 1e-10
            upper = mean_bb + 2 * std_bb
            lower = mean_bb - 2 * std_bb
            band_range = upper - lower if upper != lower else 1e-10
            bollinger_pct_b[i] = np.clip((prices_arr[i] - lower) / band_range, 0.0, 1.0)

        # Feature 10: ATR normalisé (Average True Range / prix)
        atr_period = 14
        atr_normalized = np.zeros(n)
        if highs is not None and lows is not None:
            highs_arr = np.array(highs, dtype=np.float64)
            lows_arr  = np.array(lows, dtype=np.float64)
        else:
            # Estimation : high/low ≈ close ± 0.5 * std des returns
            rolling_std = np.array([np.std(prices_arr[max(0, i - 14):i + 1]) for i in range(n)])
            highs_arr = prices_arr + 0.5 * rolling_std
            lows_arr  = prices_arr - 0.5 * rolling_std

        true_ranges = np.zeros(n)
        for i in range(1, n):
            tr = max(
                highs_arr[i] - lows_arr[i],
                abs(highs_arr[i] - prices_arr[i - 1]),
                abs(lows_arr[i]  - prices_arr[i - 1])
            )
            true_ranges[i] = tr
        for i in range(atr_period, n):
            atr = np.mean(true_ranges[i - atr_period:i])
            atr_normalized[i] = atr / prices_arr[i] if prices_arr[i] > 0 else 0.0
        atr_normalized = np.clip(atr_normalized * 20, 0.0, 1.0)  # scale ×20, cap à 1

        # Feature 11: Price Momentum (ROC 10 jours)
        roc_period = 10
        price_momentum = np.zeros(n)
        for i in range(roc_period, n):
            prev = prices_arr[i - roc_period]
            price_momentum[i] = (prices_arr[i] - prev) / prev if prev != 0 else 0.0
        price_momentum = np.clip(price_momentum, -0.3, 0.3) / 0.3

        # Assembler les 12 features
        features = np.column_stack([
            normalized_prices,  # 0
            returns,            # 1
            normalized_volumes, # 2
            volume_momentum,    # 3
            rsi_norm,           # 4
            volatility,         # 5
            sma_ratio,          # 6
            trend,              # 7
            macd_histogram,     # 8  NEW
            bollinger_pct_b,    # 9  NEW
            atr_normalized,     # 10 NEW
            price_momentum,     # 11 NEW
        ])

        # Remplacer les NaN/Inf résiduels
        features = np.nan_to_num(features, nan=0.0, posinf=1.0, neginf=-1.0)

        return features  # shape (n, 12)


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

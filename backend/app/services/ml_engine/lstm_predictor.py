"""
==============================================
ML ENGINE - LSTM Price Prediction
==============================================

Utilise LSTM (Long Short-Term Memory) pour prédire les prix
"""

import numpy as np
from typing import Dict, Tuple, List
import json
from datetime import datetime
from pathlib import Path


class LSTMPredictor:
    """
    LSTM pour prédiction de prix crypto
    
    Peut fonctionner en 2 modes:
    1. Avec TensorFlow (production)
    2. Mode fallback (développement)
    """
    
    def __init__(self, use_tensorflow: bool = False):
        self.use_tensorflow = use_tensorflow
        self.model = None
        self.keras = None  # Initialize as None
        self.layers = None  # Initialize as None
        self.tensorflow_available = False  # Initialize as False
        # Use absolute path relative to this file
        self.model_path = Path(__file__).parent / "models" / "lstm_model.keras"
        self.scaler_params = {}
        
        if use_tensorflow:
            self._init_tensorflow()
    
    def _init_tensorflow(self):
        """Initialise TensorFlow/Keras en mode CPU uniquement (pas de CUDA)"""
        import os
        # Désactiver GPU/CUDA avant tout import TF - évite CUDA error 303 sur Railway
        os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
        os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"  # Silence CUDA/GPU warnings
        os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
        try:
            from tensorflow import keras
            from tensorflow.keras import layers
            
            self.keras = keras
            self.layers = layers
            self.tensorflow_available = True
            print("[OK] TensorFlow loaded in CPU-only mode (no CUDA)")
        except ImportError:
            print("⚠️ TensorFlow not available. Using fallback mode.")
            self.tensorflow_available = False
    
    def build_model(self, input_shape: Tuple[int, int]) -> None:
        """
        Construit le modèle LSTM
        
        Args:
            input_shape: (lookback, n_features)
        """
        if not self.use_tensorflow or not self.tensorflow_available:
            return
        
        self.model = self.keras.Sequential([
            # Input layer (best practice for Keras)
            self.layers.Input(shape=input_shape),
            
            # LSTM layer 1 - 128 units
            self.layers.LSTM(
                128,
                activation='relu',
                return_sequences=True
            ),
            self.layers.Dropout(0.2),
            
            # LSTM layer 2 - 64 units
            self.layers.LSTM(
                64,
                activation='relu',
                return_sequences=False
            ),
            self.layers.Dropout(0.2),
            
            # Dense layers
            self.layers.Dense(32, activation='relu'),
            self.layers.Dense(16, activation='relu'),
            self.layers.Dense(1, activation='sigmoid')  # Output [0, 1] normalized
        ])
        
        self.model.compile(
            optimizer='adam',
            loss='mse',
            metrics=['mae']
        )
    
    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        epochs: int = 50,
        batch_size: int = 32,
        validation_split: float = 0.2,
        callbacks: list = None
    ) -> Dict:
        """
        Entraîne le modèle LSTM
        
        Args:
            X_train: (n_samples, lookback, n_features)
            y_train: (n_samples,) targets
            epochs: Nombre d'epochs
            batch_size: Taille du batch
            validation_split: Ratio validation
            callbacks: Liste de callbacks Keras
        
        Returns:
            Dict avec historique de training
        """
        
        if not self.use_tensorflow or not self.tensorflow_available:
            return {
                "status": "fallback",
                "message": "TensorFlow not available. Using mock predictions."
            }
        
        history = self.model.fit(
            X_train,
            y_train,
            epochs=epochs,
            batch_size=batch_size,
            validation_split=validation_split,
            verbose=0,
            shuffle=True,
            callbacks=callbacks
        )
        
        return {
            "status": "trained",
            "epochs": epochs,
            "final_loss": float(history.history['loss'][-1]),
            "final_val_loss": float(history.history['val_loss'][-1])
        }
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Prédit les prix (t+1 step)
        
        Args:
            X: (n_samples, lookback, n_features)
        
        Returns:
            np.ndarray de prix prédits [0, 1] normalisés
        """
        if not self.use_tensorflow or not self.tensorflow_available or self.model is None:
            return self._predict_fallback(X)
        
        return self.model.predict(X, verbose=0)

    def predict_with_uncertainty(self, X: np.ndarray, n_iterations: int = 20) -> tuple:
        """
        Fix #3: Monte Carlo Dropout - vraie mesure de confiance.
        Lance la prédiction N fois avec dropout activé (training=True).
        La variance des sorties = incertitude du modèle.
        
        Returns:
            (mean_prediction np.ndarray, confidence float [0, 1])
        """
        if not self.use_tensorflow or not self.tensorflow_available or self.model is None:
            preds = self._predict_fallback(X)
            return preds, 0.25  # Confiance très basse pour le fallback

        mc_preds = []
        for _ in range(n_iterations):
            # training=True active le dropout pendant l'inférence
            pred = self.model(X, training=True).numpy()
            mc_preds.append(pred)

        mc_array = np.array(mc_preds)          # (n_iter, n_samples, 1)
        mean_pred = np.mean(mc_array, axis=0)  # (n_samples, 1)
        std_pred = np.std(mc_array, axis=0)    # (n_samples, 1)

        # Coefficient de variation → confidence
        mean_abs = np.mean(np.abs(mean_pred)) + 1e-10
        cv = float(np.mean(std_pred) / mean_abs)
        # CV faible = prédictions stables = haute confiance
        confidence = float(np.clip(1.0 - cv * 8.0, 0.10, 0.92))

        return mean_pred, confidence

    def rolling_forecast(
        self,
        last_sequence: np.ndarray,
        n_steps: int,
        price_range: float,
        min_price: float
    ) -> list:
        """
        Fix #2: Prédiction auto-régressive sur n_steps horizons.
        Chaque prédiction devient le nouvel input pour la suivante.
        
        Args:
            last_sequence: Dernière séquence (lookback, n_features)
            n_steps: Nombre de pas à prédire
            price_range: max_price - min_price (pour dénormalisation)
            min_price: Prix minimum de la fenêtre
        
        Returns:
            Liste de prix prédits [prix_t1, prix_t2, ..., prix_tn]
        """
        if not self.use_tensorflow or not self.tensorflow_available or self.model is None:
            # Fallback: extrapolation linéaire de la tendance récente
            recent_trend = np.mean(np.diff(last_sequence[-10:, 0]))
            current_norm = last_sequence[-1, 0]
            return [
                float(np.clip(current_norm + recent_trend * s, 0, 1) * price_range + min_price)
                for s in range(1, n_steps + 1)
            ]

        current_seq = last_sequence.copy()  # (lookback, n_features)
        predictions = []

        for _ in range(n_steps):
            X_input = current_seq.reshape(1, *current_seq.shape)  # (1, lookback, n_features)
            pred_norm = float(self.model.predict(X_input, verbose=0)[0, 0])
            pred_price = pred_norm * price_range + min_price
            predictions.append(pred_price)

            # Shift la fenêtre: supprimer le plus ancien, ajouter la nouvelle prédiction
            new_step = current_seq[-1].copy()
            prev_norm = current_seq[-1, 0]
            new_step[0] = pred_norm  # Mettre à jour le prix normalisé
            if current_seq.shape[1] > 1:
                # Mettre à jour les returns (feature 1)
                new_step[1] = (pred_norm - prev_norm) / (prev_norm + 1e-10)
            # Les autres features (volume, RSI, etc.) restent constantes (approximation)
            current_seq = np.vstack([current_seq[1:], new_step.reshape(1, -1)])

        return predictions
    
    def _predict_fallback(self, X: np.ndarray) -> np.ndarray:
        """
        Prédiction fallback sans TensorFlow
        Utilise la moyenne historique + trend
        """
        predictions = []
        
        for sequence in X:
            # Prendre le dernier prix de la séquence
            last_price = sequence[-1, 0]  # Close price (feature 0)
            
            # Calculer le trend (moyenne des 10 derniers)
            recent_trend = np.mean(sequence[-10:, 0]) if len(sequence) >= 10 else last_price
            
            # Prédiction = moyenne derniers prix + légère tendance
            trend_direction = 1.0 if recent_trend > last_price else -1.0
            noise = np.random.normal(0, 0.02)
            
            prediction = last_price + (trend_direction * 0.01) + noise
            prediction = np.clip(prediction, 0, 1)  # Normaliser [0, 1]
            
            predictions.append(prediction)
        
        return np.array(predictions).reshape(-1, 1)
    
    def save_model(self, path: str = None):
        """Sauvegarde le modèle"""
        if self.model is None:
            return
        
        path = path or str(self.model_path)
        self.model.save(path)
    
    def load_model(self, path: str = None):
        """Charge le modèle"""
        if not self.use_tensorflow or not self.tensorflow_available or self.keras is None:
            print("[INFO] Skipping model loading - TensorFlow not available")
            return
        
        path = path or str(self.model_path)
        from pathlib import Path as _Path
        if not _Path(path).exists():
            print(f"[WARN] Model file not found at {path} → fallback mode active (predictions unreliable)")
            return
        try:
            # Try loading with compile=False to avoid metric deserialization issues
            self.model = self.keras.models.load_model(path, compile=False)
            # Recompile manually if needed for training, but for prediction it's fine
            self.model.compile(
                optimizer='adam',
                loss='mse',
                metrics=['mae']
            )
            import os
            size_kb = os.path.getsize(path) / 1024
            print(f"[OK] LSTM model loaded from {path} ({size_kb:.0f} KB) - REAL predictions active")
        except Exception as e:
            print(f"[ERROR] Failed to load model from {path}: {e} → fallback mode active")


class MLPricePredictions:
    """Résultats de prédictions ML"""
    
    def __init__(
        self,
        symbol: str,
        current_price: float,
        predictions_1h: float,
        predictions_24h: float,
        predictions_7d: float,
        confidence_1h: float,
        confidence_24h: float,
        confidence_7d: float,
    ):
        self.symbol = symbol
        self.timestamp = datetime.utcnow().isoformat()
        self.current_price = current_price
        self.predictions_1h = predictions_1h
        self.predictions_24h = predictions_24h
        self.predictions_7d = predictions_7d
        self.confidence_1h = confidence_1h
        self.confidence_24h = confidence_24h
        self.confidence_7d = confidence_7d
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "current_price": self.current_price,
            "predictions": {
                "1h": {
                    "price": self.predictions_1h,
                    "change_percent": ((self.predictions_1h - self.current_price) / self.current_price * 100),
                    "confidence": self.confidence_1h
                },
                "24h": {
                    "price": self.predictions_24h,
                    "change_percent": ((self.predictions_24h - self.current_price) / self.current_price * 100),
                    "confidence": self.confidence_24h
                },
                "7d": {
                    "price": self.predictions_7d,
                    "change_percent": ((self.predictions_7d - self.current_price) / self.current_price * 100),
                    "confidence": self.confidence_7d
                }
            },
            "trend": "uptrend" if self.predictions_7d > self.current_price else "downtrend"
        }

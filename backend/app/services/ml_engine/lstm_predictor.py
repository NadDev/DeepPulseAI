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
        # Use absolute path relative to this file
        self.model_path = Path(__file__).parent / "models" / "lstm_model.keras"
        self.scaler_params = {}
        
        if use_tensorflow:
            self._init_tensorflow()
    
    def _init_tensorflow(self):
        """Initialise TensorFlow/Keras si disponible"""
        try:
            from tensorflow import keras
            from tensorflow.keras import layers
            
            self.keras = keras
            self.layers = layers
            self.tensorflow_available = True
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
            # LSTM layer 1 - 128 units
            self.layers.LSTM(
                128,
                activation='relu',
                return_sequences=True,
                input_shape=input_shape
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
        Prédit les prix
        
        Args:
            X: (n_samples, lookback, n_features)
        
        Returns:
            np.ndarray de prix prédits [0, 1] normalisés
        """
        
        if not self.use_tensorflow or not self.tensorflow_available or self.model is None:
            # Mode fallback - utilise une moyenne simple + noise
            return self._predict_fallback(X)
        
        return self.model.predict(X, verbose=0)
    
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
        if not self.use_tensorflow:
            return
        
        path = path or str(self.model_path)
        try:
            # Try loading with compile=False to avoid metric deserialization issues
            self.model = self.keras.models.load_model(path, compile=False)
            # Recompile manually if needed for training, but for prediction it's fine
            self.model.compile(
                optimizer='adam',
                loss='mse',
                metrics=['mae']
            )
            print(f"[OK] Model loaded from {path}")
        except Exception as e:
            print(f"[ERROR] Failed to load model: {e}")


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

"""
==============================================
ML ENGINE - Main Service
==============================================

Coordonne LSTM, Pattern Recognition et Feature Engineering
"""

import asyncio
import numpy as np
import httpx
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from app.services.market_data import market_data_collector
from app.services.ml_engine.feature_engineering import FeatureEngineer
from app.services.ml_engine.lstm_predictor import LSTMPredictor, MLPricePredictions
from app.services.ml_engine.pattern_recognition import PatternRecognition
import logging

logger = logging.getLogger(__name__)


class MLEngine:
    """
    Moteur ML intégré
    - Prédictions de prix avec LSTM
    - Détection de patterns avec Transformer
    - Feature engineering automatique
    """
    
    def __init__(self):
        self.feature_engineer = FeatureEngineer()
        self.lstm_predictor = LSTMPredictor(use_tensorflow=True)  # Try TensorFlow mode
        self.lstm_predictor.load_model() # Load trained model if available
        self.pattern_recognition = PatternRecognition()
        
        # Cache des prédictions (éviter trop d'appels)
        self.prediction_cache = {}
        self.cache_ttl = 3600  # 1 heure

        # Training State
        self.training_state = {
            "status": "idle",
            "progress": 0,
            "message": "Ready to train",
            "last_run": None
        }
    
    async def get_training_status(self) -> Dict:
        """Retourne l'état de l'entraînement"""
        return self.training_state

    async def train_model(self, symbol: str = "BTCUSDT", days: int = 365) -> Dict:
        """Lance l'entraînement du modèle en arrière-plan"""
        if self.training_state["status"] == "training":
            return {"status": "error", "message": "Training already in progress"}
        
        self.training_state = {
            "status": "training",
            "progress": 0,
            "message": "Starting training...",
            "last_run": datetime.utcnow().isoformat()
        }
        
        # Run in background
        asyncio.create_task(self._run_training_pipeline(symbol, days))
        
        return {"status": "started", "message": "Training started in background"}

    async def _run_training_pipeline(self, symbol: str, days: int):
        try:
            # 1. Fetch Data
            self.training_state["message"] = f"Fetching {days} days of data for {symbol}..."
            self.training_state["progress"] = 5
            
            candles = await self._fetch_history_internal(symbol, "1h", days)
            
            if len(candles) < 1000:
                raise Exception("Not enough data to train")
                
            self.training_state["message"] = f"Data loaded: {len(candles)} points. Generating features..."
            self.training_state["progress"] = 30
            
            # Parse data
            closes = [float(c[4]) for c in candles]
            volumes = [float(c[5]) for c in candles]
            
            # 2. Feature Engineering
            features = self.feature_engineer.create_features(prices=closes, volumes=volumes)
            lookback = 60
            X, y = self.feature_engineer.create_sequences(features, lookback)
            
            split_idx = int(len(X) * 0.8)
            X_train, y_train = X[:split_idx], y[:split_idx]
            
            self.training_state["message"] = "Training LSTM model (this may take a while)..."
            self.training_state["progress"] = 40
            
            # 3. Train
            # We need to run this in a thread executor because model.fit is blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._train_wrapper, X_train, y_train)
            
            self.training_state["message"] = "Saving model..."
            self.training_state["progress"] = 90
            
            # 4. Save
            self.lstm_predictor.save_model()
            
            self.training_state["status"] = "completed"
            self.training_state["progress"] = 100
            self.training_state["message"] = "Training completed successfully"
            
        except Exception as e:
            logger.error(f"Training failed: {e}")
            self.training_state["status"] = "error"
            self.training_state["message"] = str(e)

    def _train_wrapper(self, X, y):
        """Wrapper synchrone pour l'entraînement Keras"""
        self.lstm_predictor.build_model(input_shape=(X.shape[1], X.shape[2]))
        
        callbacks = []
        epochs = 20
        
        if self.lstm_predictor.tensorflow_available:
            keras = self.lstm_predictor.keras
            
            class ProgressCallback(keras.callbacks.Callback):
                def __init__(self, engine, total_epochs):
                    self.engine = engine
                    self.total_epochs = total_epochs
                    
                def on_epoch_end(self, epoch, logs=None):
                    # Progress from 40% to 90%
                    progress_range = 50
                    current_progress = 40 + int(((epoch + 1) / self.total_epochs) * progress_range)
                    self.engine.training_state["progress"] = min(current_progress, 90)
                    loss = logs.get('loss', 0)
                    self.engine.training_state["message"] = f"Training LSTM... Epoch {epoch+1}/{self.total_epochs} (Loss: {loss:.5f})"
            
            callbacks.append(ProgressCallback(self, epochs))
            
        self.lstm_predictor.train(X, y, epochs=epochs, batch_size=32, callbacks=callbacks)

    async def _fetch_history_internal(self, symbol, interval, days):
        """Fetch historical candles with pagination"""
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
        
        all_candles = []
        current_start = start_time
        
        async with httpx.AsyncClient() as client:
            while current_start < end_time:
                try:
                    response = await client.get(
                        "https://api.binance.com/api/v3/klines",
                        params={
                            "symbol": symbol,
                            "interval": interval,
                            "startTime": current_start,
                            "limit": 1000
                        },
                        timeout=30
                    )
                    
                    if response.status_code != 200:
                        break
                        
                    data = response.json()
                    if not data:
                        break
                        
                    all_candles.extend(data)
                    
                    # Update start time for next batch
                    last_timestamp = data[-1][0]
                    current_start = last_timestamp + 1
                    
                    # Update progress roughly (5% to 30%)
                    total_time = end_time - start_time
                    elapsed = current_start - start_time
                    progress = 5 + int((elapsed / total_time) * 25)
                    self.training_state["progress"] = min(progress, 30)
                    
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Exception during fetch: {e}")
                    break
                    
        return all_candles

    async def predict_price(
        self,
        symbol: str,
        lookback_days: int = 90,
    ) -> Dict:
        """
        Prédit le prix d'une crypto
        
        Args:
            symbol: e.g., "BTC"
            lookback_days: Nombre de jours historiques
        
        Returns:
            Dict avec prédictions 1h, 24h, 7d
        """
        
        # Vérifier le cache
        cache_key = f"{symbol}_predictions"
        if cache_key in self.prediction_cache:
            cached_time, cached_data = self.prediction_cache[cache_key]
            if datetime.utcnow() - cached_time < timedelta(seconds=self.cache_ttl):
                return cached_data
        
        try:
            # 1. Récupérer les données historiques
            logger.info(f"Fetching market data for {symbol}...")
            
            # Utiliser Binance pour obtenir les candles
            candles = await market_data_collector.get_candles(
                symbol=symbol,
                timeframe="1d",
                limit=lookback_days
            )
            
            if not candles or len(candles) < 60:
                return {
                    "status": "error",
                    "message": f"Insufficient data for {symbol} (need 60+ candles)"
                }
            
            # Extraire les données
            closes = [float(c["close"]) for c in candles]
            volumes = [float(c["volume"]) for c in candles]
            current_price = closes[-1]
            
            # 2. Feature Engineering
            logger.info("Creating features...")
            features = self.feature_engineer.create_features(
                prices=closes,
                volumes=volumes,
                rsi_period=14
            )
            
            # Créer les séquences pour LSTM
            X, _ = self.feature_engineer.create_sequences(
                features=features,
                lookback=60
            )
            
            # 3. LSTM Predictions
            logger.info("Predicting with LSTM...")
            lstm_outputs = self.lstm_predictor.predict(X)
            
            # Dénormaliser les prédictions
            min_price = np.min(closes)
            max_price = np.max(closes)
            price_range = max_price - min_price if max_price > min_price else max_price * 0.1
            
            # Prédictions futures
            # Supposer que chaque output correspond à 1 jour
            pred_1d = lstm_outputs[-1, 0] * price_range + min_price if len(lstm_outputs) > 0 else current_price
            pred_7d = lstm_outputs[-1, 0] * price_range + min_price if len(lstm_outputs) > 0 else current_price
            
            # Ajouter une tendance basée sur les récents changements
            recent_trend = np.mean(np.diff(closes[-10:]))
            pred_1d = pred_1d + (recent_trend * 0.5)
            pred_7d = pred_7d + (recent_trend * 3.5)
            pred_1h = current_price + (recent_trend * 0.05)
            
            # Clamp to reasonable bounds
            pred_1h = np.clip(pred_1h, current_price * 0.95, current_price * 1.05)
            pred_7d = np.clip(pred_7d, current_price * 0.8, current_price * 1.2)
            
            # Calculer la confiance (basée sur la variance)
            lstm_variance = np.std(lstm_outputs)
            confidence_base = 1 - min(lstm_variance, 0.3) / 0.3
            
            # 4. Pattern Recognition
            logger.info("Detecting patterns...")
            patterns = self.pattern_recognition.detect_patterns(closes)
            
            # 5. Construire la réponse
            result = {
                "status": "success",
                "symbol": symbol,
                "timestamp": datetime.utcnow().isoformat(),
                "current_price": float(current_price),
                "predictions": {
                    "1h": {
                        "price": float(pred_1h),
                        "change_percent": float(((pred_1h - current_price) / current_price * 100)),
                        "confidence": float(min(confidence_base * 0.85, 0.9))
                    },
                    "24h": {
                        "price": float(pred_1d),
                        "change_percent": float(((pred_1d - current_price) / current_price * 100)),
                        "confidence": float(min(confidence_base * 0.8, 0.85))
                    },
                    "7d": {
                        "price": float(pred_7d),
                        "change_percent": float(((pred_7d - current_price) / current_price * 100)),
                        "confidence": float(min(confidence_base * 0.7, 0.75))
                    }
                },
                "patterns": patterns[:5],  # Top 5 patterns
                "trend": "uptrend" if pred_7d > current_price else "downtrend",
                "model": "LSTM + Pattern Recognition (v1.0)"
            }
            
            # Cache le résultat
            self.prediction_cache[cache_key] = (datetime.utcnow(), result)
            
            # === PHASE 1: Persister les prédictions en base de données ===
            try:
                await self._persist_prediction(symbol, result, current_price, patterns, lookback_days)
            except Exception as e:
                logger.warning(f"⚠️ Could not persist ML prediction for {symbol}: {str(e)}")
                # Ne pas bloquer la prédiction si la persistance échoue
            
            return result
            
        except Exception as e:
            logger.error(f"Error in ML prediction: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "symbol": symbol
            }
    
    async def get_multiple_predictions(
        self,
        symbols: List[str]
    ) -> Dict[str, Dict]:
        """
        Prédit pour plusieurs symboles en parallèle
        
        Args:
            symbols: Liste de symboles (e.g., ["BTC", "ETH", "ADA"])
        
        Returns:
            Dict {symbol: predictions}
        """
        
        tasks = [
            self.predict_price(symbol)
            for symbol in symbols
        ]
        
        results = await asyncio.gather(*tasks)
        
        return {
            symbol: result
            for symbol, result in zip(symbols, results)
        }
    
    async def optimize_strategy(
        self,
        symbol: str,
        strategy_type: str = "trend_following",
    ) -> Dict:
        """
        Optimise les paramètres d'une stratégie basée sur ML
        
        Args:
            symbol: Crypto symbol
            strategy_type: Type de stratégie
        
        Returns:
            Paramètres optimisés
        """
        
        try:
            # Récupérer les prédictions
            predictions = await self.predict_price(symbol)
            
            if predictions["status"] != "success":
                return {"status": "error", "message": predictions.get("message")}
            
            current_price = predictions["current_price"]
            pred_7d = predictions["predictions"]["7d"]["price"]
            confidence = predictions["predictions"]["7d"]["confidence"]
            
            # Optimiser selon la stratégie
            if strategy_type == "trend_following":
                return {
                    "status": "success",
                    "strategy": "trend_following",
                    "parameters": {
                        "entry_signal": "above_sma_50" if pred_7d > current_price else "below_sma_50",
                        "stop_loss_percent": 5.0,
                        "take_profit_percent": 15.0 if confidence > 0.75 else 10.0,
                        "position_size_percent": 3.0 if confidence > 0.8 else 1.0,
                        "confidence": confidence
                    }
                }
            
            elif strategy_type == "mean_reversion":
                return {
                    "status": "success",
                    "strategy": "mean_reversion",
                    "parameters": {
                        "entry_signal": "rsi_oversold" if pred_7d < current_price else "rsi_overbought",
                        "stop_loss_percent": 7.0,
                        "take_profit_percent": 8.0,
                        "position_size_percent": 2.0 if confidence > 0.7 else 1.0,
                        "confidence": confidence
                    }
                }
            
            else:
                return {"status": "error", "message": f"Unknown strategy: {strategy_type}"}
        
        except Exception as e:
            logger.error(f"Error optimizing strategy: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def _persist_prediction(
        self,
        symbol: str,
        prediction: Dict,
        current_price: float,
        patterns: List[str],
        lookback_days: int
    ) -> None:
        """
        Phase 1: Persist LSTM predictions to database for backtesting and accuracy measurement
        
        Args:
            symbol: Cryptocurrency symbol (e.g., "BTC")
            prediction: Prediction dict with 1h/24h/7d forecasts
            current_price: Market price at prediction time
            patterns: Detected chart patterns
            lookback_days: Days of historical data used
        """
        try:
            from app.models.database_models import MLPrediction
            from app.db.database import SessionLocal
            
            db = SessionLocal()
            
            try:
                # Use a default system user ID if not in authenticated context
                # In production, this would be passed from the API context
                system_user_id = "00000000-0000-0000-0000-000000000001"  # Placeholder
                
                prediction_data = MLPrediction(
                    user_id=system_user_id,
                    symbol=symbol,
                    timestamp=datetime.utcnow(),
                    
                    # Predictions
                    pred_1h=float(prediction["predictions"]["1h"]["price"]),
                    confidence_1h=float(prediction["predictions"]["1h"]["confidence"]),
                    
                    pred_24h=float(prediction["predictions"]["24h"]["price"]),
                    confidence_24h=float(prediction["predictions"]["24h"]["confidence"]),
                    
                    pred_7d=float(prediction["predictions"]["7d"]["price"]),
                    confidence_7d=float(prediction["predictions"]["7d"]["confidence"]),
                    
                    # Context
                    current_price=current_price,
                    patterns=patterns,
                    
                    # Metadata
                    model_version="lstm-1.0.0",
                    lookback_days=lookback_days
                )
                
                db.add(prediction_data)
                db.commit()
                
                # Store values BEFORE closing session to avoid "not bound to Session" error
                pred_1h_val = prediction_data.pred_1h
                conf_1h_val = prediction_data.confidence_1h
                
                logger.info(f"✅ Persisted LSTM prediction for {symbol}: 1h=${pred_1h_val:.2f} (±{conf_1h_val:.1%})")
                
            finally:
                db.close()
            
        except Exception as e:
            logger.error(f"Error persisting prediction for {symbol}: {str(e)}")
            # Don't raise - we don't want to break predictions if DB is unavailable
            pass


# Instance globale
ml_engine = MLEngine()

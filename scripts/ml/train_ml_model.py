import asyncio
import sys
import os
from pathlib import Path
import numpy as np
import httpx
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

try:
    from app.services.ml_engine.lstm_predictor import LSTMPredictor
    from app.services.ml_engine.feature_engineering import FeatureEngineer
except ImportError as e:
    logger.error(f"Import Error: {e}")
    logger.error("Make sure you are running this script from the root directory (c:\\CRBot)")
    sys.exit(1)

class BinanceFetcher:
    """Fetches massive historical data from Binance"""
    
    BASE_URL = "https://api.binance.com/api/v3/klines"
    
    @staticmethod
    async def fetch_history(symbol="BTCUSDT", interval="1h", days=365):
        """Fetch historical candles with pagination"""
        logger.info(f"Fetching {days} days of {interval} data for {symbol}...")
        
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
        
        all_candles = []
        current_start = start_time
        
        async with httpx.AsyncClient() as client:
            while current_start < end_time:
                try:
                    response = await client.get(
                        BinanceFetcher.BASE_URL,
                        params={
                            "symbol": symbol,
                            "interval": interval,
                            "startTime": current_start,
                            "limit": 1000
                        },
                        timeout=30
                    )
                    
                    if response.status_code != 200:
                        logger.error(f"Error fetching data: {response.text}")
                        break
                        
                    data = response.json()
                    if not data:
                        break
                        
                    all_candles.extend(data)
                    
                    # Update start time for next batch (last candle time + 1ms)
                    last_timestamp = data[-1][0]
                    current_start = last_timestamp + 1
                    
                    logger.info(f"Fetched {len(data)} candles. Total: {len(all_candles)}")
                    
                    # Rate limit protection
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Exception during fetch: {e}")
                    break
                    
        return all_candles

async def train_model():
    """Main training pipeline"""
    
    # 1. Fetch Data
    symbol = "BTCUSDT"
    days = 365 # 1 year
    
    candles = await BinanceFetcher.fetch_history(symbol, "1h", days)
    
    if len(candles) < 1000:
        logger.error("Not enough data to train.")
        return

    # Parse data
    # Binance format: [timestamp, open, high, low, close, volume, ...]
    closes = [float(c[4]) for c in candles]
    volumes = [float(c[5]) for c in candles]
    
    logger.info(f"Data loaded: {len(closes)} points")
    
    # 2. Feature Engineering
    logger.info("Generating features...")
    fe = FeatureEngineer()
    features = fe.create_features(prices=closes, volumes=volumes)
    
    # Create sequences
    lookback = 60
    X, y = fe.create_sequences(features, lookback)
    
    # Split Train/Test
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    logger.info(f"Training set: {X_train.shape}, Test set: {X_test.shape}")
    
    # 3. Initialize & Train Model
    logger.info("Initializing LSTM Model (TensorFlow)...")
    predictor = LSTMPredictor(use_tensorflow=True)
    
    if not predictor.tensorflow_available:
        logger.error("TensorFlow not available. Cannot train.")
        return

    predictor.build_model(input_shape=(lookback, X.shape[2]))
    
    logger.info("Starting training (this may take a while)...")
    history = predictor.train(
        X_train, y_train,
        epochs=20, # Reduced for demo, increase for real deep learning
        batch_size=32,
        validation_split=0.1
    )
    
    logger.info(f"Training complete. Final Loss: {history.get('final_loss')}")
    
    # 4. Save Model
    save_path = Path("backend/app/services/ml_engine/models")
    save_path.mkdir(parents=True, exist_ok=True)
    model_file = save_path / "lstm_model.keras"
    
    predictor.model.save(model_file)
    logger.info(f"Model saved to {model_file}")

if __name__ == "__main__":
    asyncio.run(train_model())

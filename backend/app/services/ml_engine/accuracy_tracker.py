"""
ML Prediction Accuracy Tracker - Phase 1
Updates actual prices and calculates accuracy for LSTM predictions

Background job that runs periodically to:
1. Fetch actual prices 1h/24h/7d after predictions
2. Calculate prediction errors
3. Validate prediction directions
4. Track model accuracy over time
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional
import logging
from app.db.database import SessionLocal
from app.models.database_models import MLPrediction
from app.services.market_data import MarketDataCollector

logger = logging.getLogger(__name__)


class MLAccuracyTracker:
    """Tracks and updates LSTM prediction accuracy"""
    
    def __init__(self):
        self.market_collector = MarketDataCollector()
        self.update_interval = 3600  # Run every hour
        self.running = False
    
    async def start(self):
        """Start the accuracy tracking loop"""
        self.running = True
        logger.info("🚀 ML Accuracy Tracker started")
        
        while self.running:
            try:
                await self.update_accuracies()
                await asyncio.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"Error in accuracy tracking loop: {str(e)}")
                await asyncio.sleep(60)  # Retry after 1 min on error
    
    def stop(self):
        """Stop the accuracy tracking loop"""
        self.running = False
        logger.info("🛑 ML Accuracy Tracker stopped")
    
    async def update_accuracies(self):
        """
        Update actual prices and accuracy metrics for LSTM predictions
        
        Process:
        1. Find predictions older than 1h (update 1h accuracy)
        2. Find predictions older than 24h (update 24h accuracy)
        3. Find predictions older than 7d (update 7d accuracy)
        4. Calculate error metrics and direction correctness
        """
        db = SessionLocal()
        try:
            now = datetime.utcnow()
            
            # === Update 1h Predictions ===
            predictions_1h = db.query(MLPrediction).filter(
                MLPrediction.correct_direction_1h == None,  # Not yet calculated
                MLPrediction.timestamp <= now - timedelta(hours=1),
                MLPrediction.timestamp > now - timedelta(days=30)  # Only recent ones
            ).limit(100).all()
            
            for pred in predictions_1h:
                await self._update_prediction_accuracy(db, pred, "1h")
            
            if predictions_1h:
                logger.info(f"✅ Updated 1h accuracy for {len(predictions_1h)} predictions")
            
            # === Update 24h Predictions ===
            predictions_24h = db.query(MLPrediction).filter(
                MLPrediction.correct_direction_24h == None,
                MLPrediction.timestamp <= now - timedelta(hours=24),
                MLPrediction.timestamp > now - timedelta(days=30)
            ).limit(100).all()
            
            for pred in predictions_24h:
                await self._update_prediction_accuracy(db, pred, "24h")
            
            if predictions_24h:
                logger.info(f"✅ Updated 24h accuracy for {len(predictions_24h)} predictions")
            
            # === Update 7d Predictions ===
            predictions_7d = db.query(MLPrediction).filter(
                MLPrediction.correct_direction_7d == None,
                MLPrediction.timestamp <= now - timedelta(days=7),
                MLPrediction.timestamp > now - timedelta(days=90)
            ).limit(50).all()
            
            for pred in predictions_7d:
                await self._update_prediction_accuracy(db, pred, "7d")
            
            if predictions_7d:
                logger.info(f"✅ Updated 7d accuracy for {len(predictions_7d)} predictions")
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Error updating accuracies: {str(e)}")
            db.rollback()
        finally:
            db.close()
    
    async def _update_prediction_accuracy(
        self,
        db,
        prediction: MLPrediction,
        timeframe: str
    ) -> None:
        """
        Update accuracy metrics for a specific timeframe
        
        Args:
            db: Database session
            prediction: MLPrediction record
            timeframe: "1h", "24h", or "7d"
        """
        try:
            # Get the predicted and current price fields
            if timeframe == "1h":
                pred_price = prediction.pred_1h
                confidence = prediction.confidence_1h
                if prediction.actual_price_1h is not None:
                    return  # Already calculated
            elif timeframe == "24h":
                pred_price = prediction.pred_24h
                confidence = prediction.confidence_24h
                if prediction.actual_price_24h is not None:
                    return
            else:  # "7d"
                pred_price = prediction.pred_7d
                confidence = prediction.confidence_7d
                if prediction.actual_price_7d is not None:
                    return
            
            if pred_price is None:
                return  # No prediction for this timeframe
            
            # Fetch actual price
            try:
                candles = await self.market_collector.get_candles(
                    prediction.symbol,
                    timeframe="1h",
                    limit=1
                )
                if not candles:
                    return
                
                actual_price = float(candles[-1]["close"])
            except Exception as e:
                logger.warning(f"Could not fetch price for {prediction.symbol}: {str(e)}")
                return
            
            # Calculate error
            error = ((actual_price - pred_price) / pred_price * 100) if pred_price != 0 else 0
            
            # Calculate direction correctness
            predicted_direction = "UP" if pred_price > prediction.current_price else "DOWN"
            actual_direction = "UP" if actual_price > prediction.current_price else "DOWN"
            correct_direction = predicted_direction == actual_direction
            
            # Update the prediction record
            if timeframe == "1h":
                prediction.actual_price_1h = actual_price
                prediction.actual_filled_at_1h = datetime.utcnow()
                prediction.error_1h = error
                prediction.correct_direction_1h = correct_direction
            elif timeframe == "24h":
                prediction.actual_price_24h = actual_price
                prediction.actual_filled_at_24h = datetime.utcnow()
                prediction.error_24h = error
                prediction.correct_direction_24h = correct_direction
            else:  # "7d"
                prediction.actual_price_7d = actual_price
                prediction.actual_filled_at_7d = datetime.utcnow()
                prediction.error_7d = error
                prediction.correct_direction_7d = correct_direction
            
            prediction.updated_at = datetime.utcnow()
            
            logger.debug(
                f"Updated {prediction.symbol} {timeframe} accuracy: "
                f"Pred=${pred_price:.2f}, Actual=${actual_price:.2f}, "
                f"Error={error:.1f}%, Direction={'✅' if correct_direction else '❌'}"
            )
            
        except Exception as e:
            logger.error(f"Error updating {prediction.symbol} {timeframe} accuracy: {str(e)}")


# Global tracker instance
accuracy_tracker: Optional[MLAccuracyTracker] = None


def get_accuracy_tracker() -> MLAccuracyTracker:
    """Get or create the global accuracy tracker"""
    global accuracy_tracker
    if accuracy_tracker is None:
        accuracy_tracker = MLAccuracyTracker()
    return accuracy_tracker


async def start_accuracy_tracker():
    """Start the background accuracy tracking job"""
    tracker = get_accuracy_tracker()
    await tracker.start()


def stop_accuracy_tracker():
    """Stop the background accuracy tracking job"""
    tracker = get_accuracy_tracker()
    tracker.stop()

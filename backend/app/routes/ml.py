from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.services.ml_engine import ml_engine
from app.models.database_models import MLPrediction, WatchlistItem
from app.db.database import get_db
from app.auth.supabase_auth import get_current_user, UserResponse
from typing import Dict, Optional, List
from datetime import datetime, timedelta

router = APIRouter(
    prefix="/api/ml",
    tags=["Machine Learning"]
)

@router.post("/train")
async def train_model(symbol: str = "BTCUSDT", days: int = 365):
    """
    Lance l'entraînement du modèle ML en arrière-plan
    """
    result = await ml_engine.train_model(symbol, days)
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@router.get("/status")
async def get_training_status():
    """
    Récupère l'état actuel de l'entraînement
    """
    return await ml_engine.get_training_status()

@router.get("/predictions/{symbol}")
async def get_latest_prediction(
    symbol: str,
    db: Session = Depends(get_db),
    current_user: Optional[UserResponse] = Depends(get_current_user)
):
    """
    Get the latest LSTM prediction for a symbol
    
    Returns:
    {
        "symbol": "BTCUSDT",
        "timestamp": "2026-01-11T16:30:00",
        "current_price": 45000.50,
        "predictions": {
            "1h": {"price": 45150.00, "confidence": 0.87},
            "24h": {"price": 46200.00, "confidence": 0.72},
            "7d": {"price": 47500.00, "confidence": 0.65}
        },
        "patterns": ["bullish_engulfing", "golden_cross"]
    }
    """
    # Get latest prediction for this symbol
    user_id = current_user.id if current_user else None
    
    query = db.query(MLPrediction).filter(
        MLPrediction.symbol == symbol.upper()
    )
    
    # If user is authenticated, prioritize their own predictions
    if user_id:
        user_pred = query.filter(MLPrediction.user_id == user_id).order_by(
            desc(MLPrediction.timestamp)
        ).first()
        if user_pred:
            prediction = user_pred
        else:
            # Fallback to system predictions
            prediction = query.order_by(desc(MLPrediction.timestamp)).first()
    else:
        # Unauthenticated: get latest system prediction
        prediction = query.order_by(desc(MLPrediction.timestamp)).first()
    
    if not prediction:
        raise HTTPException(
            status_code=404, 
            detail=f"No predictions found for {symbol}"
        )
    
    return {
        "symbol": prediction.symbol,
        "timestamp": prediction.timestamp.isoformat(),
        "current_price": prediction.current_price,
        "predictions": {
            "1h": {
                "price": prediction.pred_1h,
                "confidence": prediction.confidence_1h
            },
            "24h": {
                "price": prediction.pred_24h,
                "confidence": prediction.confidence_24h
            },
            "7d": {
                "price": prediction.pred_7d,
                "confidence": prediction.confidence_7d
            }
        },
        "patterns": prediction.patterns or [],
        "model_version": prediction.model_version,
        "lookback_days": prediction.lookback_days
    }

@router.get("/predictions/{symbol}/history")
async def get_prediction_history(
    symbol: str,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: Optional[UserResponse] = Depends(get_current_user)
):
    """
    Get historical predictions for a symbol (last N predictions)
    
    Query params:
    - limit: Number of predictions to return (default 10, max 100)
    """
    limit = min(max(1, limit), 100)  # Clamp between 1 and 100
    user_id = current_user.id if current_user else None
    
    query = db.query(MLPrediction).filter(
        MLPrediction.symbol == symbol.upper()
    )
    
    # Prioritize user's own predictions
    if user_id:
        user_preds = query.filter(
            MLPrediction.user_id == user_id
        ).order_by(desc(MLPrediction.timestamp)).limit(limit).all()
        
        if user_preds:
            predictions = user_preds
        else:
            predictions = query.order_by(
                desc(MLPrediction.timestamp)
            ).limit(limit).all()
    else:
        predictions = query.order_by(
            desc(MLPrediction.timestamp)
        ).limit(limit).all()
    
    if not predictions:
        raise HTTPException(
            status_code=404,
            detail=f"No predictions found for {symbol}"
        )
    
    return {
        "symbol": symbol.upper(),
        "count": len(predictions),
        "predictions": [
            {
                "timestamp": p.timestamp.isoformat(),
                "current_price": p.current_price,
                "pred_1h": p.pred_1h,
                "confidence_1h": p.confidence_1h,
                "pred_24h": p.pred_24h,
                "confidence_24h": p.confidence_24h,
                "pred_7d": p.pred_7d,
                "confidence_7d": p.confidence_7d,
                "patterns": p.patterns or [],
                # Accuracy if available
                "error_1h": p.error_1h,
                "correct_direction_1h": p.correct_direction_1h
            }
            for p in predictions
        ]
    }

@router.get("/predictions/{symbol}/accuracy")
async def get_prediction_accuracy(
    symbol: str,
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: Optional[UserResponse] = Depends(get_current_user)
):
    """
    Get model accuracy metrics for a symbol over the last N days
    
    Returns accuracy stats: hit_rate, avg_error, best/worst predictions
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    user_id = current_user.id if current_user else None
    
    query = db.query(MLPrediction).filter(
        MLPrediction.symbol == symbol.upper(),
        MLPrediction.timestamp >= cutoff_date,
        MLPrediction.error_1h.isnot(None)  # Only use completed predictions
    )
    
    if user_id:
        user_preds = query.filter(MLPrediction.user_id == user_id).all()
        if user_preds:
            predictions = user_preds
        else:
            predictions = query.all()
    else:
        predictions = query.all()
    
    if not predictions:
        raise HTTPException(
            status_code=404,
            detail=f"No accuracy data for {symbol} in last {days} days"
        )
    
    # Calculate accuracy metrics
    correct_1h = sum(1 for p in predictions if p.correct_direction_1h)
    correct_24h = sum(1 for p in predictions if p.correct_direction_24h)
    correct_7d = sum(1 for p in predictions if p.correct_direction_7d)
    
    errors_1h = [abs(p.error_1h) for p in predictions if p.error_1h]
    errors_24h = [abs(p.error_24h) for p in predictions if p.error_24h]
    errors_7d = [abs(p.error_7d) for p in predictions if p.error_7d]
    
    return {
        "symbol": symbol.upper(),
        "period_days": days,
        "total_predictions": len(predictions),
        "accuracy": {
            "1h": {
                "hit_rate": (correct_1h / len(predictions)) * 100 if predictions else 0,
                "avg_error_pct": sum(errors_1h) / len(errors_1h) if errors_1h else 0,
                "correct": correct_1h
            },
            "24h": {
                "hit_rate": (correct_24h / len(predictions)) * 100 if predictions else 0,
                "avg_error_pct": sum(errors_24h) / len(errors_24h) if errors_24h else 0,
                "correct": correct_24h
            },
            "7d": {
                "hit_rate": (correct_7d / len(predictions)) * 100 if predictions else 0,
                "avg_error_pct": sum(errors_7d) / len(errors_7d) if errors_7d else 0,
                "correct": correct_7d
            }
        }
    }

@router.get("/predictions/watchlist/latest")
async def get_watchlist_predictions(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Get latest LSTM predictions for ALL symbols in user's watchlist
    
    Returns predictions grouped by symbol with priorities
    
    Response:
    {
        "watchlist_count": 5,
        "predictions": [
            {
                "symbol": "BTCUSDT",
                "priority": 10,
                "timestamp": "2026-01-11T16:30:00",
                "current_price": 45000.50,
                "predictions": {...},
                "patterns": ["bullish_engulfing"]
            },
            ...
        ]
    }
    """
    user_id = current_user.id
    
    # Get user's active watchlist items
    watchlist = db.query(WatchlistItem).filter(
        WatchlistItem.user_id == user_id,
        WatchlistItem.is_active == True
    ).order_by(WatchlistItem.priority.desc()).all()
    
    if not watchlist:
        raise HTTPException(
            status_code=404,
            detail="No active symbols in your watchlist"
        )
    
    # Get latest predictions for each symbol
    predictions_list = []
    
    for item in watchlist:
        # Convert BTC/USDT to BTCUSDT format
        symbol = item.symbol.replace("/", "")
        
        # Get latest prediction for this symbol
        latest_pred = db.query(MLPrediction).filter(
            MLPrediction.symbol == symbol,
            MLPrediction.user_id == user_id
        ).order_by(desc(MLPrediction.timestamp)).first()
        
        # Fallback to system prediction if user has none
        if not latest_pred:
            latest_pred = db.query(MLPrediction).filter(
                MLPrediction.symbol == symbol
            ).order_by(desc(MLPrediction.timestamp)).first()
        
        if latest_pred:
            predictions_list.append({
                "symbol": latest_pred.symbol,
                "priority": item.priority,
                "timestamp": latest_pred.timestamp.isoformat(),
                "current_price": latest_pred.current_price,
                "predictions": {
                    "1h": {
                        "price": latest_pred.pred_1h,
                        "confidence": latest_pred.confidence_1h
                    },
                    "24h": {
                        "price": latest_pred.pred_24h,
                        "confidence": latest_pred.confidence_24h
                    },
                    "7d": {
                        "price": latest_pred.pred_7d,
                        "confidence": latest_pred.confidence_7d
                    }
                },
                "patterns": latest_pred.patterns or [],
                "model_version": latest_pred.model_version
            })
    
    return {
        "watchlist_count": len(watchlist),
        "predictions_available": len(predictions_list),
        "predictions": predictions_list
    }

@router.get("/predictions/watchlist/accuracy")
async def get_watchlist_accuracy(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Get aggregated accuracy metrics for all symbols in user's watchlist
    
    Returns combined hit_rate, avg_error across all watched symbols
    """
    user_id = current_user.id
    
    # Get user's active watchlist items
    watchlist = db.query(WatchlistItem).filter(
        WatchlistItem.user_id == user_id,
        WatchlistItem.is_active == True
    ).all()
    
    if not watchlist:
        raise HTTPException(
            status_code=404,
            detail="No active symbols in your watchlist"
        )
    
    # Collect all symbols
    symbols = [item.symbol.replace("/", "") for item in watchlist]
    
    # Get predictions for all symbols with error data
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    all_predictions = db.query(MLPrediction).filter(
        MLPrediction.symbol.in_(symbols),
        MLPrediction.user_id == user_id,
        MLPrediction.timestamp >= cutoff_date,
        MLPrediction.error_1h.isnot(None)
    ).all()
    
    # If no user predictions, get system predictions
    if not all_predictions:
        all_predictions = db.query(MLPrediction).filter(
            MLPrediction.symbol.in_(symbols),
            MLPrediction.timestamp >= cutoff_date,
            MLPrediction.error_1h.isnot(None)
        ).all()
    
    if not all_predictions:
        raise HTTPException(
            status_code=404,
            detail=f"No accuracy data for watchlist in last {days} days"
        )
    
    # Calculate aggregated metrics
    correct_1h = sum(1 for p in all_predictions if p.correct_direction_1h)
    correct_24h = sum(1 for p in all_predictions if p.correct_direction_24h)
    correct_7d = sum(1 for p in all_predictions if p.correct_direction_7d)
    
    errors_1h = [abs(p.error_1h) for p in all_predictions if p.error_1h]
    errors_24h = [abs(p.error_24h) for p in all_predictions if p.error_24h]
    errors_7d = [abs(p.error_7d) for p in all_predictions if p.error_7d]
    
    # Per-symbol accuracy breakdown
    symbol_accuracy = {}
    for symbol in symbols:
        symbol_preds = [p for p in all_predictions if p.symbol == symbol]
        if symbol_preds:
            symbol_correct_1h = sum(1 for p in symbol_preds if p.correct_direction_1h)
            symbol_accuracy[symbol] = {
                "count": len(symbol_preds),
                "hit_rate_1h": (symbol_correct_1h / len(symbol_preds)) * 100
            }
    
    return {
        "period_days": days,
        "watchlist_symbols": len(symbols),
        "total_predictions_analyzed": len(all_predictions),
        "aggregate_accuracy": {
            "1h": {
                "hit_rate": (correct_1h / len(all_predictions)) * 100 if all_predictions else 0,
                "avg_error_pct": sum(errors_1h) / len(errors_1h) if errors_1h else 0,
                "correct": correct_1h
            },
            "24h": {
                "hit_rate": (correct_24h / len(all_predictions)) * 100 if all_predictions else 0,
                "avg_error_pct": sum(errors_24h) / len(errors_24h) if errors_24h else 0,
                "correct": correct_24h
            },
            "7d": {
                "hit_rate": (correct_7d / len(all_predictions)) * 100 if all_predictions else 0,
                "avg_error_pct": sum(errors_7d) / len(errors_7d) if errors_7d else 0,
                "correct": correct_7d
            }
        },
        "per_symbol_accuracy": symbol_accuracy
    }

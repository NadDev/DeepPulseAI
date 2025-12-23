from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.services.ml_engine import ml_engine
from typing import Dict

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

from fastapi import APIRouter, HTTPException
from typing import Dict, Any

router = APIRouter(prefix="/api", tags=["translations"])

# Translations data (can be extended or loaded from database)
TRANSLATIONS = {
    "fr": {
        "error": "Erreur",
        "success": "Succès",
        "loading": "Chargement...",
        "offline": "HORS LIGNE",
        "live": "EN DIRECT",
        "portfolio_value": "Valeur du Portefeuille",
        "daily_pnl": "Résultat Quotidien",
        "win_rate": "Taux de Gain",
        "max_drawdown": "Perte Maximale",
    },
    "en": {
        "error": "Error",
        "success": "Success",
        "loading": "Loading...",
        "offline": "OFFLINE",
        "live": "LIVE",
        "portfolio_value": "Portfolio Value",
        "daily_pnl": "Daily P&L",
        "win_rate": "Win Rate",
        "max_drawdown": "Max Drawdown",
    },
    "de": {},  # To be added in Phase 2
    "es": {},  # To be added in Phase 2
    "zh": {},  # To be added in Phase 2
}

@router.get("/translations/{lang}")
async def get_translations(lang: str):
    """
    FEATURE 6.1: Get translations for a specific language
    Returns all available translations for the requested language
    Fallback to English if language not found
    """
    lang_lower = lang.lower()
    
    if lang_lower not in TRANSLATIONS:
        # Fallback to English
        lang_lower = "en"
    
    return {
        "language": lang_lower,
        "translations": TRANSLATIONS[lang_lower],
        "available_languages": ["fr", "en", "de", "es", "zh"]
    }

@router.get("/translations")
async def get_all_translations():
    """
    Get all available translations
    """
    return {
        "languages": list(TRANSLATIONS.keys()),
        "available": ["fr", "en", "de", "es", "zh"],
        "completed": ["fr", "en"],
        "translations": TRANSLATIONS
    }

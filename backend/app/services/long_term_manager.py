"""
Long Term Manager Service
Gestion de la stratégie d'a

ccumulation long terme avec sélection ULTRA-STRICTE.

Philosophie: Acheter la PEUR, vendre la GREED.
Score minimum: 80/100 pour exécuter un trade.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import numpy as np

from app.models.database_models import (
    PortfolioAllocation,
    LongTermPosition,
    LongTermTransaction,
    Portfolio
)
from app.services.market_data import MarketDataCollector
from app.services.technical_analysis import TechnicalAnalysis
from app.services.ml_engine import ML_Engine
from app.services.coingecko_client import get_coingecko_client

logger = logging.getLogger(__name__)


class LongTermManager:
    """
    Gestion du pocket Long Terme avec sélection ULTRA-STRICTE.
    
    Critères de sélection:
    1. Multi-timeframe convergence (1h, 4h, 1d, 1w)
    2. Multi-indicator agreement (6/9 minimum)
    3. ML high confidence (7d >70% BULLISH)
    4. Market context (Fear < 30)
    5. Structure analysis (support zones)
    6. Market Cap & ATH distance (survie + potentiel)
    
    Score minimum requis: 80/100
    """
    
    def __init__(
        self,
        db_session: Session,
        market_data: MarketDataCollector,
        technical_analysis: TechnicalAnalysis,
        ml_engine: Optional[ML_Engine] = None
    ):
        self.db = db_session
        self.market_data = market_data
        self.ta = technical_analysis
        self.ml_engine = ml_engine
        
        # Initialize CoinGecko client with DB session for watchlist access
        self.coingecko = get_coingecko_client(db_session=db_session)
        
        logger.info("LongTermManager initialized")
    
    async def refresh_watchlist_symbols(self, user_id: str = None):
        """
        Refresh CoinGecko symbol mappings from watchlist.
        Call this periodically or when watchlist changes.
        """
        await self.coingecko.load_watchlist_symbols(user_id)
    
    async def get_user_allocation(self, user_id: str) -> Optional[PortfolioAllocation]:
        """Récupère l'allocation de l'utilisateur."""
        return self.db.query(PortfolioAllocation).filter(
            PortfolioAllocation.user_id == user_id
        ).first()
    
    async def is_lt_enabled(self, user_id: str) -> bool:
        """Vérifie si long terme est activé (OPT-IN)."""
        allocation = await self.get_user_allocation(user_id)
        return allocation.lt_enabled if allocation else False
    
    async def get_lt_balance(self, user_id: str) -> float:
        """
        Calcule le solde disponible pour LT.
        MAX 20% du portfolio total.
        """
        allocation = await self.get_user_allocation(user_id)
        if not allocation or not allocation.lt_enabled:
            return 0.0
        
        # Get portfolio
        portfolio = self.db.query(Portfolio).filter(
            Portfolio.user_id == user_id
        ).first()
        
        if not portfolio:
            return 0.0
        
        # Calculate max LT balance (20% max)
        max_lt_balance = portfolio.total_value * 0.20  # 20% MAX absolu
        current_lt_balance = portfolio.cash_balance * (allocation.long_term_pct / 100)
        
        return min(current_lt_balance, max_lt_balance)
    
    async def get_positions(self, user_id: str, status: Optional[str] = None) -> List[LongTermPosition]:
        """Liste les positions LT de l'utilisateur."""
        query = self.db.query(LongTermPosition).filter(
            LongTermPosition.user_id == user_id
        )
        
        if status:
            query = query.filter(LongTermPosition.status == status)
        
        return query.all()
    
    async def analyze_lt_opportunity(
        self,
        symbol: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        ANALYSE MULTI-TIMEFRAME pour détecter opportunité LT.
        
        Returns dict with:
        - confidence_score: 0-100
        - criteria_met: Dict of boolean checks
        - recommendation: BUY / HOLD / SKIP
        - reason: Detailed explanation
        - details: Full analysis breakdown
        """
        
        logger.info(f"🔍 Analyzing LT opportunity for {symbol}...")
        
        try:
            # 1. Multi-timeframe analysis
            logger.info(f"📊 [1/6] Multi-timeframe analysis...")
            tf_1w = await self.market_data.get_candles(symbol, "1w", 100)
            tf_1d = await self.market_data.get_candles(symbol, "1d", 100)
            tf_4h = await self.market_data.get_candles(symbol, "4h", 100)
            tf_1h = await self.market_data.get_candles(symbol, "1h", 200)
            
            timeframe_score = self._analyze_timeframe_convergence({
                "1w": tf_1w,
                "1d": tf_1d,
                "4h": tf_4h,
                "1h": tf_1h
            })
            
            # 2. Multi-indicator convergence
            logger.info(f"📈 [2/6] Multi-indicator analysis...")
            indicators = await self._calculate_all_indicators(symbol, tf_1d)
            indicator_score = self._count_bullish_indicators(indicators)
            
            # 3. ML predictions (multi-timeframe)
            logger.info(f"🤖 [3/6] ML predictions analysis...")
            ml_predictions = await self._fetch_ml_predictions_all_tf(symbol) if self.ml_engine else {}
            ml_score = self._calculate_ml_score(ml_predictions) if ml_predictions else 0
            
            # 4. Market context (Fear/Greed, BTC dominance)
            logger.info(f"🌍 [4/6] Market context analysis...")
            market_context = await self._fetch_market_context()
            context_score = self._evaluate_market_context(market_context)
            
            # 5. Structure analysis
            logger.info(f"🏗️ [5/6] Structure analysis...")
            structure = await self._analyze_support_resistance(symbol, tf_1d)
            structure_score = self._evaluate_structure(structure)
            
            # 6. Market Cap & ATH Distance (FILTRE CRITIQUE)
            logger.info(f"💎 [6/6] Market Cap & ATH distance...")
            market_info = await self._fetch_market_cap_and_ath(symbol)
            
            if not market_info:
                return {
                    "confidence_score": 0,
                    "recommendation": "SKIP",
                    "reason": f"Could not fetch market data for {symbol}"
                }
            
            # FILTRE PRÉLIMINAIRE: Market Cap trop faible = disqualification
            if market_info["market_cap"] < 500_000_000:
                return {
                    "confidence_score": 0,
                    "recommendation": "SKIP",
                    "reason": f"Market Cap ${market_info['market_cap']/1e9:.2f}B too low (<$500M). High risk of project death."
                }
            
            market_cap_score = self._evaluate_market_cap_viability(market_info)
            
            # Calculate final score
            confidence_score = (
                timeframe_score * 0.30 +
                indicator_score * 0.25 +
                ml_score * 0.20 +
                context_score * 0.10 +
                structure_score * 0.05 +
                market_cap_score * 0.10
            )
            
            # Get user allocation settings
            allocation = await self.get_user_allocation(user_id)
            min_score = allocation.lt_min_confidence_score if allocation else 80
            
            # Determine recommendation
            recommendation = "BUY" if confidence_score >= min_score else "SKIP"
            reason = self._build_reason_string(confidence_score, min_score, {
                "timeframe": timeframe_score,
                "indicators": indicator_score,
                "ml": ml_score,
                "context": context_score,
                "structure": structure_score,
                "market_cap": market_cap_score
            })
            
            return {
                "confidence_score": round(confidence_score, 2),
                "criteria_met": {
                    "timeframe_aligned": timeframe_score >= 20,
                    "indicators_bullish": indicator_score >= 18,
                    "ml_confident": ml_score >= 15,
                    "context_favorable": context_score >= 5,
                    "structure_solid": structure_score >= 3,
                    "market_cap_safe": market_info["market_cap"] >= 500_000_000,
                    "ath_distance_good": market_info.get("ath_distance_pct", 0) <= -30
                },
                "recommendation": recommendation,
                "reason": reason,
                "details": {
                    "timeframe_analysis": timeframe_score,
                    "indicator_count": indicator_score,
                    "ml_predictions": ml_predictions,
                    "market_context": market_context,
                    "structure": structure,
                    "market_cap_info": market_info
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error analyzing LT opportunity for {symbol}: {e}")
            return {
                "confidence_score": 0,
                "recommendation": "SKIP",
                "reason": f"Analysis error: {str(e)}"
            }
    
    def _analyze_timeframe_convergence(self, timeframes: Dict) -> float:
        """
        Score 0-30 basé sur alignement des timeframes.
        CRITIQUE: 1w et 1d DOIVENT être bullish.
        """
        score = 0
        
        # 1w analysis (12 points)
        weekly_trend = self._get_trend(timeframes["1w"])
        if weekly_trend == "BULLISH":
            score += 12
        elif weekly_trend == "NEUTRAL":
            score += 6
        else:
            return 0  # 1w bearish = instant disqualification
        
        # 1d analysis (10 points)
        daily_trend = self._get_trend(timeframes["1d"])
        if daily_trend == "BULLISH":
            score += 10
        elif daily_trend == "NEUTRAL":
            score += 5
        else:
            return 0  # 1d bearish = instant disqualification
        
        # 4h analysis (5 points)
        h4_trend = self._get_trend(timeframes["4h"])
        if h4_trend in ["BULLISH", "NEUTRAL"]:
            score += 5
        
        # 1h analysis (3 points bonus)
        h1_trend = self._get_trend(timeframes["1h"])
        if h1_trend == "BULLISH":
            score += 3
        
        return score
    
    def _get_trend(self, candles: List) -> str:
        """Détermine la tendance (BULLISH, BEARISH, NEUTRAL)."""
        if not candles or len(candles) < 50:
            return "NEUTRAL"
        
        # Calculate SMAs
        closes = [float(c[4]) for c in candles[-50:]]  # Last 50 closes
        sma_20 = np.mean(closes[-20:])
        sma_50 = np.mean(closes)
        current_price = closes[-1]
        
        # Trend determination
        if current_price > sma_20 > sma_50:
            return "BULLISH"
        elif current_price < sma_20 < sma_50:
            return "BEARISH"
        else:
            return "NEUTRAL"
    
    async def _calculate_all_indicators(self, symbol: str, candles: List) -> Dict:
        """Calculate all technical indicators for the symbol."""
        if not candles or len(candles) < 200:
            return {}
        
        closes = [float(c[4]) for c in candles]
        highs = [float(c[2]) for c in candles]
        lows = [float(c[3]) for c in candles]
        volumes = [float(c[5]) for c in candles]
        
        current_price = closes[-1]
        
        # SMAs
        sma_20 = np.mean(closes[-20:])
        sma_50 = np.mean(closes[-50:])
        sma_200 = np.mean(closes[-200:])
        
        # RSI
        rsi = self._calculate_rsi(closes, 14)
        rsi_history = [self._calculate_rsi(closes[:i], 14) for i in range(len(closes)-20, len(closes))]
        
        # MACD
        macd, signal, histogram = self._calculate_macd(closes)
        macd_trend = "UP" if len(histogram) > 1 and histogram[-1] > histogram[-2] else "DOWN"
        
        # Volume
        volume_avg_20 = np.mean(volumes[-20:])
        obv = self._calculate_obv(closes, volumes)
        obv_trend = "UP" if obv[-1] > obv[-20] else "DOWN"
        
        return {
            "price": current_price,
            "sma_20": sma_20,
            "sma_50": sma_50,
            "sma_200": sma_200,
            "rsi": rsi,
            "rsi_history": rsi_history,
            "price_history": closes[-20:],
            "macd": macd,
            "macd_signal": signal,
            "macd_histogram_trend": macd_trend,
            "volume": volumes[-1],
            "volume_avg_20": volume_avg_20,
            "obv_trend": obv_trend,
            "price_bouncing_from_support": self._check_bounce(closes, sma_20, sma_50)
        }
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate RSI indicator."""
        if len(prices) < period + 1:
            return 50.0
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_macd(self, prices: List[float]) -> tuple:
        """Calculate MACD indicator."""
        if len(prices) < 26:
            return 0, 0, [0]
        
        ema_12 = self._calculate_ema(prices, 12)
        ema_26 = self._calculate_ema(prices, 26)
        macd_line = ema_12 - ema_26
        signal_line = self._calculate_ema([macd_line] * 9, 9)  # Simplified
        histogram = [macd_line - signal_line] * 5  # Last 5 values
        
        return macd_line, signal_line, histogram
    
    def _calculate_ema(self, prices: List[float], period: int) -> float:
        """Calculate EMA."""
        if len(prices) < period:
            return np.mean(prices)
        
        multiplier = 2 / (period + 1)
        ema = np.mean(prices[:period])
        
        for price in prices[period:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def _calculate_obv(self, closes: List[float], volumes: List[float]) -> List[float]:
        """Calculate On Balance Volume."""
        obv = [volumes[0]]
        for i in range(1, len(closes)):
            if closes[i] > closes[i-1]:
                obv.append(obv[-1] + volumes[i])
            elif closes[i] < closes[i-1]:
                obv.append(obv[-1] - volumes[i])
            else:
                obv.append(obv[-1])
        return obv
    
    def _check_bounce(self, prices: List[float], sma_20: float, sma_50: float) -> bool:
        """Check if price is bouncing from support."""
        current = prices[-1]
        prev = prices[-2] if len(prices) > 1 else current
        
        # Check if price touched SMA and is now above
        near_sma20 = abs(prev - sma_20) / sma_20 < 0.02  # Within 2%
        near_sma50 = abs(prev - sma_50) / sma_50 < 0.02
        
        bouncing= current > prev and (near_sma20 or near_sma50)
        
        return bouncing
    
    def _count_bullish_indicators(self, indicators: Dict) -> float:
        """
        Score 0-25 basé sur nombre d'indicateurs bullish.
        Minimum 6/9 requis.
        
        STRATÉGIE OVERSOLD: On cherche à acheter quand RSI est BAS (sous-acheté).
        """
        if not indicators:
            return 0
        
        bullish_count = 0
        bonus_points = 0
        
        # Trend indicators (4 points max)
        if indicators["price"] > indicators["sma_200"]:
            bullish_count += 1
        if indicators["sma_50"] >= indicators["sma_200"] * 0.98:  # Golden cross ou proche
            bullish_count += 1
        if indicators["macd"] > indicators["macd_signal"]:
            bullish_count += 1
        if indicators["macd_histogram_trend"] == "UP":
            bullish_count += 1
        
        # Momentum - OVERSOLD LOGIC (3 points max + bonus)
        rsi = indicators["rsi"]
        
        # ⚡ BONUS pour oversold (meilleur moment d'achat)
        if rsi < 30:  # Extreme oversold
            bullish_count += 1
            bonus_points += 3  # BONUS points (excellent timing)
        elif 30 <= rsi <= 45:  # Oversold recovery
            bullish_count += 1
            bonus_points += 2
        elif 45 < rsi <= 60:  # Neutral
            bullish_count += 1
        # Si RSI > 60 (overbought): 0 points = pénalité
        
        if self._is_rsi_trending_up(indicators["rsi_history"]):
            bullish_count += 1
        
        if self._has_bullish_divergence(indicators["rsi_history"], indicators["price_history"]):
            bullish_count += 1
            bonus_points += 2  # RSI divergence = signal fort
        
        # Support zones (2 points max)
        price = indicators["price"]
        distance_to_sma20 = abs(price - indicators["sma_20"]) / price
        distance_to_sma50 = abs(price - indicators["sma_50"]) / price
        
        if distance_to_sma20 < 0.05 or distance_to_sma50 < 0.05:  # < 5% de distance
            bullish_count += 1
            if indicators["price_bouncing_from_support"]:
                bullish_count += 1
                bonus_points += 1
        
        # Volume (2 points max)
        if indicators["volume"] > indicators["volume_avg_20"]:
            bullish_count += 1
        if indicators["obv_trend"] == "UP":
            bullish_count += 1
        
        # Score base + bonus
        base_score = (bullish_count / 9) * 25
        total_score = min(base_score + bonus_points, 25)  # Cap à 25
        
        return total_score
    
    def _is_rsi_trending_up(self, rsi_history: List[float]) -> bool:
        """Check if RSI is trending up (higher lows)."""
        if len(rsi_history) < 5:
            return False
        
        # Linear regression
        x = np.arange(len(rsi_history))
        slope = np.polyfit(x, rsi_history, 1)[0]
        
        return slope > 0
    
    def _has_bullish_divergence(self, rsi_history: List[float], price_history: List[float]) -> bool:
        """
        Détecte divergence haussière: RSI monte mais prix baisse.
        Signal fort d'accumulation.
        """
        if len(rsi_history) < 10 or len(price_history) < 10:
            return False
        
        # RSI fait higher lows
        rsi_slope = np.polyfit(range(len(rsi_history)), rsi_history, 1)[0]
        # Prix fait lower lows
        price_slope = np.polyfit(range(len(price_history)), price_history, 1)[0]
        
        return rsi_slope > 0 and price_slope < 0
    
    async def _fetch_ml_predictions_all_tf(self, symbol: str) -> Dict:
        """Fetch ML predictions for all timeframes."""
        if not self.ml_engine:
            return {}
        
        predictions = {}
        for tf in ["1h", "4h", "24h", "7d"]:
            try:
                pred = await self.ml_engine.predict(symbol, timeframe=tf)
                predictions[tf] = pred
            except:
                predictions[tf] = {"direction": "NEUTRAL", "confidence": 0}
        
        return predictions
    
    def _calculate_ml_score(self, ml_predictions: Dict) -> float:
        """
        Score 0-20 basé sur confiance ML.
        CRITIQUE: 7d >70% BULLISH requis.
        """
        if not ml_predictions:
            return 0
        
        score = 0
        
        # 7d prediction (12 points) - MOST IMPORTANT
        pred_7d = ml_predictions.get("7d", {})
        if pred_7d.get("direction") == "BULLISH" and pred_7d.get("confidence", 0) > 70:
            score += 12
        elif pred_7d.get("direction") == "BULLISH" and pred_7d.get("confidence", 0) > 60:
            score += 8
        else:
            return 0  # 7d not bullish = disqualification
        
        # 24h prediction (8 points)
        pred_24h = ml_predictions.get("24h", {})
        if pred_24h.get("direction") == "BULLISH" and pred_24h.get("confidence", 0) > 65:
            score += 8
        elif pred_24h.get("direction") == "BULLISH" and pred_24h.get("confidence", 0) > 55:
            score += 4
        
        return score
    
    async def _fetch_market_context(self) -> Dict:
        """Fetch global market context (Fear/Greed, BTC dominance)."""
        # TODO: Implement Fear & Greed Index API call
        # For now, return mock data
        return {
            "fear_greed_index": 25,  # Extreme Fear
            "btc_dominance": 42.5,
            "market_sentiment": "BEARISH"
        }
    
    def _evaluate_market_context(self, context: Dict) -> float:
        """Score 0-10 basé sur market context."""
        score = 0
        
        # Fear & Greed (5 points)
        fear_index = context.get("fear_greed_index", 50)
        if fear_index < 20:  # Extreme Fear
            score += 5
        elif fear_index < 30:  # Fear
            score += 3
        # > 30: 0 points
        
        # BTC Dominance (5 points)
        btc_dom = context.get("btc_dominance", 45)
        if 35 <= btc_dom <= 50:  # Stable range
            score += 5
        elif 30 <= btc_dom <= 55:
            score += 3
        
        return score
    
    async def _analyze_support_resistance(self, symbol: str, candles: List) -> Dict:
        """Analyze support/resistance levels."""
        if not candles or len(candles) < 50:
            return {}
        
        closes = [float(c[4]) for c in candles]
        highs = [float(c[2]) for c in candles]
        lows = [float(c[3]) for c in candles]
        
        current_price = closes[-1]
        
        # Find support levels (local minimums)
        support_levels = []
        for i in range(10, len(lows) - 10):
            if lows[i] == min(lows[i-10:i+10]):
                support_levels.append(lows[i])
        
        # Find closest support
        support_levels = sorted(set(support_levels), reverse=True)
        closest_support = None
        for level in support_levels:
            if level < current_price:
                closest_support = level
                break
        
        return {
            "current_price": current_price,
            "closest_support": closest_support,
            "distance_to_support_pct": ((current_price - closest_support) / closest_support * 100) if closest_support else 999
        }
    
    def _evaluate_structure(self, structure: Dict) -> float:
        """Score 0-5 basé on structure quality."""
        if not structure:
            return 0
        
        score = 0
        
        # Proximity to support
        dist = structure.get("distance_to_support_pct", 999)
        if dist < 5:  # Within 5% of support
            score += 5
        elif dist < 10:
            score += 3
        elif dist < 15:
            score += 2
        
        return score
    
    async def _fetch_market_cap_and_ath(self, symbol: str) -> Optional[Dict]:
        """
        Récupère Market Cap et données ATH depuis CoinGecko API.
        
        Returns:
            Dict with keys: market_cap, ath_price, ath_date, current_price, ath_distance_pct, time_since_ath_days, rebound_potential
        """
        try:
            result = await self.coingecko.get_market_cap_and_ath(symbol)
            
            if result:
                logger.debug(f"✅ CoinGecko: {symbol} - Market cap ${result['market_cap']/1e9:.2f}B, ATH distance {result['ath_distance_pct']:.1f}%")
            
            return result
        
        except Exception as e:
            logger.error(f"❌ Failed to fetch market cap/ATH for {symbol}: {e}")
            return None
    
    def _evaluate_market_cap_viability(self, market_info: Dict) -> float:
        """
        Score 0-10 basé sur Market Cap et distance ATH.
        Combine sécurité (survie) + potentiel (rebond).
        """
        score = 0
        market_cap = market_info.get("market_cap", 0)
        ath_distance_pct = market_info.get("ath_distance_pct", 0)
        
        # Market Cap scoring (0-5 points)
        if market_cap >= 10_000_000_000:  # > $10B (top 10)
            score += 3
        elif market_cap >= 2_000_000_000:  # > $2B (top 30)
            score += 2
        elif market_cap >= 500_000_000:  # > $500M (top 50)
            score += 1
        else:
            return 0  # < $500M = disqualification
        
        # ATH Distance scoring (0-7 points)
        if ath_distance_pct <= -70:  # -70% à -90%
            score += 7  # Excellent (4-10x potentiel)
        elif ath_distance_pct <= -50:  # -50% à -70%
            score += 5  # Bon (2-3x potentiel)
        elif ath_distance_pct <= -30:  # -30% à -50%
            score += 3  # Acceptable (1.5-2x potentiel)
        # < -30%: 0 points
        
        return score
    
    def _build_reason_string(self, score: float, min_score: int, breakdown: Dict) -> str:
        """Build detailed reason string."""
        if score >= min_score:
            return f"✅ All criteria met (score: {score:.1f}/{min_score}). Excellent LT opportunity."
        
        # Find which criteria failed
        failed = []
        if breakdown["timeframe"] < 20:
            failed.append("Timeframes not aligned")
        if breakdown["indicators"] < 18:
            failed.append("Insufficient bullish indicators")
        if breakdown["ml"] < 15:
            failed.append("ML not confident enough")
        if breakdown["context"] < 5:
            failed.append("Market context unfavorable")
        if breakdown["market_cap"] < 5:
            failed.append("Market cap/ATH concerns")
        
        return f"❌ SKIP (score: {score:.1f}/{min_score}). Failed: {', '.join(failed)}"
    
    async def should_execute_dca(self, user_id: str) -> Dict[str, Any]:
        """
        Vérifie si c'est le moment d'exécuter un DCA.
        
        Returns:
        {
            "should_execute": bool,
            "symbols": List of symbols to DCA,
            "amounts": Dict of symbol->amount,
            "confidence_scores": Dict of symbol->score,
            "analyses": Dict of full analyses
        }
        """
        allocation = await self.get_user_allocation(user_id)
        
        if not allocation or not allocation.lt_enabled:
            return {"should_execute": False, "reason": "Long terme not enabled (OPT-IN required)"}
        
        # Check frequency/timing
        if not self._is_dca_day(allocation):
            return {"should_execute": False, "reason": "Not DCA day"}
        
        # Analyze each configured asset
        results = {}
        for symbol in allocation.lt_assets:
            analysis = await self.analyze_lt_opportunity(symbol, user_id)
            results[symbol] = analysis
        
        # Filter: Only execute if score >= minimum
        valid_symbols = [
            symbol for symbol, analysis in results.items()
            if analysis["recommendation"] == "BUY"
        ]
        
        if not valid_symbols:
            return {
                "should_execute": False,
                "reason": "No symbol meets confidence threshold (score < 80)",
                "analyses": results
            }
        
        # Calculate amounts
        lt_balance = await self.get_lt_balance(user_id)
        dca_total = lt_balance * (allocation.lt_dca_amount_pct / 100)
        
        # Distribute by weights
        amounts = self._distribute_dca_amounts(
            valid_symbols,
            dca_total,
            allocation.lt_asset_weights
        )
        
        logger.info(f"✅ DCA ready: {len(valid_symbols)} symbols, ${dca_total:.2f} total")
        
        return {
            "should_execute": True,
            "symbols": valid_symbols,
            "amounts": amounts,
            "confidence_scores": {s: results[s]["confidence_score"] for s in valid_symbols},
            "analyses": results
        }
    
    def _is_dca_day(self, allocation: PortfolioAllocation) -> bool:
        """Check if today is a DCA day."""
        today = datetime.now()
        
        if allocation.lt_dca_frequency == "daily":
            return True
        elif allocation.lt_dca_frequency == "weekly":
            return today.weekday() == allocation.lt_dca_day
        elif allocation.lt_dca_frequency == "monthly":
            return today.day == allocation.lt_dca_day
        
        return False
    
    def _distribute_dca_amounts(
        self,
        symbols: List[str],
        total_amount: float,
        weights: Dict[str, float]
    ) -> Dict[str, float]:
        """Distribute DCA amount according to weights."""
        amounts = {}
        total_weight = sum(weights.get(s, 0) for s in symbols)
        
        if total_weight == 0:
            # Equal distribution if no weights
            amount_per_symbol = total_amount / len(symbols)
            return {s: amount_per_symbol for s in symbols}
        
        for symbol in symbols:
            weight = weights.get(symbol, 0)
            amounts[symbol] = (weight / total_weight) * total_amount
        
        return amounts
    
    async def execute_dca(
        self,
        user_id: str,
        symbol: str,
        amount: float,
        analysis: Dict
    ) -> Optional[LongTermTransaction]:
        """Execute a DCA buy."""
        try:
            # Get or create position
            position = self.db.query(LongTermPosition).filter(
                and_(
                    LongTermPosition.user_id == user_id,
                    LongTermPosition.symbol == symbol
                )
            ).first()
            
            if not position:
                # Create new position
                position = LongTermPosition(
                    user_id=user_id,
                    symbol=symbol,
                    status="ACCUMULATING",
                    market_cap_at_entry=analysis["details"]["market_cap_info"].get("market_cap"),
                    ath_price_at_entry=analysis["details"]["market_cap_info"].get("ath_price"),
                    ath_distance_pct_at_entry=analysis["details"]["market_cap_info"].get("ath_distance_pct")
                )
                self.db.add(position)
            
            # TODO: Execute actual buy via Binance
            current_price = analysis["details"]["market_cap_info"]["current_price"]
            quantity = amount / current_price
            
            # Update position
            position.total_quantity += quantity
            position.total_invested += amount
            position.dca_count += 1
            position.last_dca_at = datetime.now()
            position.avg_entry_price = position.total_invested / position.total_quantity
            
            # Create transaction record
            transaction = LongTermTransaction(
                user_id=user_id,
                position_id=position.id,
                symbol=symbol,
                side="BUY",
                quantity=quantity,
                price=current_price,
                total_value=amount,
                transaction_type="DCA_REGULAR",
                confidence_score=int(analysis["confidence_score"]),
                confidence_criteria=analysis["criteria_met"],
                market_context=analysis["details"]["market_context"].get("market_sentiment"),
                fear_greed_index=analysis["details"]["market_context"].get("fear_greed_index"),
                market_cap=analysis["details"]["market_cap_info"].get("market_cap"),
                ath_distance_pct=analysis["details"]["market_cap_info"].get("ath_distance_pct")
            )
            
            self.db.add(transaction)
            self.db.commit()
            
            logger.info(f"✅ DCA executed: {symbol} ${amount:.2f} @ ${current_price:.2f}")
            
            return transaction
            
        except Exception as e:
            logger.error(f"❌ Failed to execute DCA: {e}")
            self.db.rollback()
            return None


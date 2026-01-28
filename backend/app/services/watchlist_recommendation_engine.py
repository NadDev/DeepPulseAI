"""
WatchlistRecommendationEngine - AI-powered crypto recommendation system
Feature: RecommendationCrypto

Scoring Algorithm (100 points total):
- Momentum (30%): 7d vs 30d price change comparison
- Volume (25%): Current volume vs 30d average
- Volatility (25%): ATR-based volatility score
- RSI (20%): 14-period RSI interpretation

Actions:
- ADD: score > 70 (bullish signals)
- REMOVE: score < 30 (bearish signals)
- HOLD: 30-70 (neutral, no recommendation)
"""

import logging
import uuid
import os
import httpx
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass
class ScoreComponents:
    """Breakdown of recommendation score."""
    momentum: float      # 0-100
    volume: float        # 0-100
    volatility: float    # 0-100
    rsi: float           # 0-100
    
    def to_dict(self) -> Dict:
        return {
            "momentum": round(self.momentum, 2),
            "volume": round(self.volume, 2),
            "volatility": round(self.volatility, 2),
            "rsi": round(self.rsi, 2)
        }


@dataclass
class Recommendation:
    """Single crypto recommendation."""
    symbol: str
    score: float
    action: str  # ADD, REMOVE, HOLD
    components: ScoreComponents
    current_price: float
    price_change_7d: float
    price_change_30d: float
    reasoning: Optional[str] = None


class WatchlistRecommendationEngine:
    """
    Generates daily crypto recommendations based on technical analysis.
    
    Uses a weighted scoring algorithm combining:
    - Momentum indicators (trend strength)
    - Volume analysis (market interest)
    - Volatility metrics (opportunity/risk)
    - RSI (overbought/oversold conditions)
    """
    
    # Scoring weights (must sum to 1.0)
    WEIGHT_MOMENTUM = 0.30
    WEIGHT_VOLUME = 0.25
    WEIGHT_VOLATILITY = 0.25
    WEIGHT_RSI = 0.20
    
    # Action thresholds
    THRESHOLD_ADD = 70      # Score > 70 = recommend ADD
    THRESHOLD_REMOVE = 30   # Score < 30 = recommend REMOVE
    
    # RSI levels
    RSI_OVERSOLD = 30
    RSI_OVERBOUGHT = 70
    RSI_PERIOD = 14
    
    def __init__(self, db_session_factory):
        self.db_session_factory = db_session_factory
    
    def generate_recommendations(
        self, 
        user_id: str,
        top_n: int = 50,
        min_score: float = 0
    ) -> List[Recommendation]:
        """
        Generate top N recommendations for a user.
        
        Args:
            user_id: User UUID
            top_n: Number of recommendations to return
            min_score: Minimum score threshold
            
        Returns:
            List of Recommendation objects sorted by score
        """
        db = self.db_session_factory()
        
        try:
            # Get all symbols with sufficient data
            symbols = self._get_available_symbols(db)
            logger.info(f"[RECOMMENDATION] Analyzing {len(symbols)} symbols for user {user_id[:8]}...")
            
            recommendations = []
            
            for symbol in symbols:
                try:
                    rec = self._analyze_symbol(db, symbol)
                    if rec and rec.score >= min_score:
                        recommendations.append(rec)
                except Exception as e:
                    logger.error(f"[RECOMMENDATION] Error analyzing {symbol}: {e}")
                    continue
            
            # Sort by score (highest first for ADD, lowest first would be for REMOVE)
            recommendations.sort(key=lambda x: x.score, reverse=True)
            
            # Return top N
            top_recommendations = recommendations[:top_n]
            
            if top_recommendations:
                logger.info(f"[RECOMMENDATION] Generated {len(top_recommendations)} recommendations "
                           f"(scores: {top_recommendations[0].score:.1f} - {top_recommendations[-1].score:.1f})")
            else:
                logger.warning(f"[RECOMMENDATION] No recommendations generated (analyzed {len(symbols)} symbols, got {len(recommendations)} candidates)")
            
            return top_recommendations
            
        finally:
            db.close()
    
    def _get_available_symbols(self, db: Session) -> List[str]:
        """Get symbols that have sufficient historical data."""
        # Get symbols with ANY data (don't restrict by timeframe or timestamp)
        result = db.execute(text("""
            SELECT DISTINCT symbol
            FROM crypto_market_data
            ORDER BY symbol
        """))
        
        symbols = [row[0] for row in result.fetchall()]
        logger.info(f"[RECOMMENDATION] _get_available_symbols() found {len(symbols)} symbols")
        
        # If no symbols, that's a problem
        if not symbols:
            logger.warning("[RECOMMENDATION] ⚠️ No symbols found in crypto_market_data table!")
        
        return symbols
    
    def _analyze_symbol(self, db: Session, symbol: str) -> Optional[Recommendation]:
        """
        Analyze a single symbol and generate recommendation.
        
        Returns None if insufficient data.
        """
        # Fetch daily candles for last 35 days (need buffer for calculations)
        candles = self._get_daily_candles(db, symbol, days=35)
        
        # Require minimum 5 days of data (flexible for sparse datasets)
        if len(candles) < 5:
            return None
        
        # Calculate components
        momentum_score = self._calculate_momentum(candles)
        volume_score = self._calculate_volume(candles)
        volatility_score = self._calculate_volatility(candles)
        rsi_score = self._calculate_rsi_score(candles)
        
        # Weighted total score
        total_score = (
            momentum_score * self.WEIGHT_MOMENTUM +
            volume_score * self.WEIGHT_VOLUME +
            volatility_score * self.WEIGHT_VOLATILITY +
            rsi_score * self.WEIGHT_RSI
        )
        
        # Determine action
        if total_score >= self.THRESHOLD_ADD:
            action = "ADD"
        elif total_score <= self.THRESHOLD_REMOVE:
            action = "REMOVE"
        else:
            action = "HOLD"
        
        # Calculate price changes for display
        current_price = candles[-1]['close']
        price_7d_ago = candles[-8]['close'] if len(candles) >= 8 else candles[0]['close']
        price_30d_ago = candles[-31]['close'] if len(candles) >= 31 else candles[0]['close']
        
        price_change_7d = ((current_price - price_7d_ago) / price_7d_ago) * 100
        price_change_30d = ((current_price - price_30d_ago) / price_30d_ago) * 100
        
        components = ScoreComponents(
            momentum=momentum_score,
            volume=volume_score,
            volatility=volatility_score,
            rsi=rsi_score
        )
        
        return Recommendation(
            symbol=symbol,
            score=round(total_score, 2),
            action=action,
            components=components,
            current_price=current_price,
            price_change_7d=round(price_change_7d, 2),
            price_change_30d=round(price_change_30d, 2)
        )
    
    def _get_daily_candles(self, db: Session, symbol: str, days: int = 35) -> List[Dict]:
        """Fetch daily candles for a symbol."""
        min_timestamp = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
        
        result = db.execute(text("""
            SELECT timestamp, open, high, low, close, volume
            FROM crypto_market_data
            WHERE symbol = :symbol
            AND timeframe = '1d'
            AND timestamp >= :min_timestamp
            ORDER BY timestamp ASC
        """), {"symbol": symbol, "min_timestamp": min_timestamp})
        
        return [
            {
                "timestamp": row[0],
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": float(row[5])
            }
            for row in result.fetchall()
        ]
    
    def _calculate_momentum(self, candles: List[Dict]) -> float:
        """
        Calculate momentum score (0-100).
        
        Compares 7-day performance vs 30-day performance.
        Strong recent momentum = higher score.
        """
        if len(candles) < 30:
            return 50  # Neutral
        
        current = candles[-1]['close']
        price_7d = candles[-8]['close'] if len(candles) >= 8 else candles[0]['close']
        price_30d = candles[-31]['close'] if len(candles) >= 31 else candles[0]['close']
        
        # Calculate % changes
        change_7d = ((current - price_7d) / price_7d) * 100
        change_30d = ((current - price_30d) / price_30d) * 100
        
        # Momentum acceleration: 7d change stronger than pro-rata 30d
        expected_7d_from_30d = change_30d * (7/30)
        momentum_diff = change_7d - expected_7d_from_30d
        
        # Normalize to 0-100 scale
        # +20% acceleration = 100, -20% = 0, 0% = 50
        score = 50 + (momentum_diff * 2.5)
        
        # Also factor in absolute 7d change
        # Strong positive 7d change adds bonus
        if change_7d > 10:
            score += 15
        elif change_7d > 5:
            score += 10
        elif change_7d > 0:
            score += 5
        elif change_7d < -10:
            score -= 15
        elif change_7d < -5:
            score -= 10
        elif change_7d < 0:
            score -= 5
        
        return max(0, min(100, score))
    
    def _calculate_volume(self, candles: List[Dict]) -> float:
        """
        Calculate volume score (0-100).
        
        Compares recent volume (3d avg) vs 30d average.
        Higher recent volume = more interest = higher score.
        """
        if len(candles) < 30:
            return 50
        
        # 30-day average volume
        volumes_30d = [c['volume'] for c in candles[-30:]]
        avg_volume_30d = sum(volumes_30d) / len(volumes_30d)
        
        if avg_volume_30d == 0:
            return 50
        
        # Recent 3-day average
        volumes_3d = [c['volume'] for c in candles[-3:]]
        avg_volume_3d = sum(volumes_3d) / len(volumes_3d)
        
        # Volume ratio
        ratio = avg_volume_3d / avg_volume_30d
        
        # Normalize: ratio 2.0 = score 100, ratio 0.5 = score 25, ratio 1.0 = 50
        # Using log scale for better distribution
        import math
        score = 50 + (math.log2(ratio) * 25) if ratio > 0 else 50
        
        return max(0, min(100, score))
    
    def _calculate_volatility(self, candles: List[Dict]) -> float:
        """
        Calculate volatility score (0-100).
        
        Uses ATR (Average True Range) as percentage of price.
        Moderate volatility is ideal (not too low, not too high).
        """
        if len(candles) < 14:
            return 50
        
        # Calculate True Range for each candle
        true_ranges = []
        for i in range(1, len(candles)):
            high = candles[i]['high']
            low = candles[i]['low']
            prev_close = candles[i-1]['close']
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            true_ranges.append(tr)
        
        # ATR (14-period)
        atr_14 = sum(true_ranges[-14:]) / 14
        current_price = candles[-1]['close']
        
        if current_price == 0:
            return 50
        
        # ATR as percentage
        atr_pct = (atr_14 / current_price) * 100
        
        # Score based on ATR%
        # Sweet spot: 2-5% daily ATR = good trading opportunity
        # Too low (<1%): boring, low opportunity = score 30
        # Ideal (2-4%): great opportunity = score 80-100
        # High (5-8%): risky but opportunity = score 60
        # Very high (>10%): too risky = score 30
        
        if atr_pct < 1:
            score = 30 + (atr_pct * 20)  # 0-1% → 30-50
        elif atr_pct < 2:
            score = 50 + ((atr_pct - 1) * 30)  # 1-2% → 50-80
        elif atr_pct < 4:
            score = 80 + ((atr_pct - 2) * 10)  # 2-4% → 80-100
        elif atr_pct < 6:
            score = 100 - ((atr_pct - 4) * 15)  # 4-6% → 100-70
        elif atr_pct < 10:
            score = 70 - ((atr_pct - 6) * 10)  # 6-10% → 70-30
        else:
            score = 30 - min(20, (atr_pct - 10) * 2)  # >10% → 30-10
        
        return max(0, min(100, score))
    
    def _calculate_rsi_score(self, candles: List[Dict]) -> float:
        """
        Calculate RSI-based score (0-100).
        
        RSI interpretation for scoring:
        - RSI < 30 (oversold): HIGH score (buying opportunity)
        - RSI 30-50: MEDIUM-HIGH score (room to grow)
        - RSI 50-70: MEDIUM score (neutral)
        - RSI > 70 (overbought): LOW score (may be due for correction)
        """
        rsi = self._calculate_rsi(candles)
        
        if rsi is None:
            return 50
        
        # Convert RSI to opportunity score
        # Oversold = buying opportunity = high score
        # Overbought = selling pressure = low score
        
        if rsi <= 20:
            score = 95  # Extremely oversold = great buy
        elif rsi <= 30:
            score = 85  # Oversold
        elif rsi <= 40:
            score = 70  # Approaching oversold
        elif rsi <= 50:
            score = 60  # Neutral-bullish
        elif rsi <= 60:
            score = 50  # Neutral
        elif rsi <= 70:
            score = 40  # Neutral-bearish
        elif rsi <= 80:
            score = 25  # Overbought
        else:
            score = 10  # Extremely overbought
        
        return score
    
    def _calculate_rsi(self, candles: List[Dict], period: int = 14) -> Optional[float]:
        """Calculate RSI (Relative Strength Index)."""
        if len(candles) < period + 1:
            return None
        
        # Calculate price changes
        changes = []
        for i in range(1, len(candles)):
            changes.append(candles[i]['close'] - candles[i-1]['close'])
        
        # Separate gains and losses
        gains = [max(0, c) for c in changes]
        losses = [abs(min(0, c)) for c in changes]
        
        # Calculate average gain/loss (SMA for first, then EMA)
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100  # No losses = max RSI
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return round(rsi, 2)
    
    def save_recommendations(
        self, 
        db: Session,
        user_id: str, 
        recommendations: List[Recommendation]
    ) -> int:
        """
        Save recommendations to database.
        
        Returns number of recommendations saved.
        """
        saved = 0
        
        for rec in recommendations:
            # Only save ADD and REMOVE (not HOLD)
            if rec.action == "HOLD":
                continue
            
            try:
                rec_id = str(uuid.uuid4())
                
                db.execute(text("""
                    INSERT INTO watchlist_recommendations 
                    (id, user_id, symbol, score, action, reasoning, created_at)
                    VALUES (:id, :user_id, :symbol, :score, :action, :reasoning, NOW())
                    ON CONFLICT (user_id, symbol, DATE(created_at)) DO UPDATE SET
                        score = EXCLUDED.score,
                        action = EXCLUDED.action,
                        reasoning = EXCLUDED.reasoning
                """), {
                    "id": rec_id,
                    "user_id": user_id,
                    "symbol": rec.symbol,
                    "score": rec.score,
                    "action": rec.action,
                    "reasoning": rec.reasoning
                })
                
                # Also log score components
                log_id = str(uuid.uuid4())
                db.execute(text("""
                    INSERT INTO recommendation_score_log
                    (id, symbol, score, components, timestamp)
                    VALUES (:id, :symbol, :score, :components, NOW())
                """), {
                    "id": log_id,
                    "symbol": rec.symbol,
                    "score": rec.score,
                    "components": str(rec.components.to_dict()).replace("'", '"')
                })
                
                saved += 1
                
            except Exception as e:
                logger.error(f"[RECOMMENDATION] Error saving {rec.symbol}: {e}")
                continue
        
        db.commit()
        logger.info(f"[RECOMMENDATION] Saved {saved} recommendations for user {user_id[:8]}")
        
        return saved
    
    def get_user_pending_recommendations(
        self, 
        db: Session,
        user_id: str,
        limit: int = 50
    ) -> List[Dict]:
        """Get pending (not yet accepted/rejected) recommendations for a user."""
        result = db.execute(text("""
            SELECT id, symbol, score, action, reasoning, created_at
            FROM watchlist_recommendations
            WHERE user_id = :user_id
            AND accepted IS NULL
            AND DATE(created_at) = CURRENT_DATE
            ORDER BY score DESC
            LIMIT :limit
        """), {"user_id": user_id, "limit": limit})
        
        return [
            {
                "id": str(row[0]),
                "symbol": row[1],
                "score": row[2],
                "action": row[3],
                "reasoning": row[4],
                "created_at": row[5].isoformat() if row[5] else None
            }
            for row in result.fetchall()
        ]
    
    # ============================================
    # DeepSeek AI Integration for Reasoning
    # ============================================
    
    async def generate_reasoning_batch(
        self,
        recommendations: List[Recommendation],
        max_concurrent: int = 5
    ) -> List[Recommendation]:
        """
        Generate AI reasoning for a batch of recommendations.
        Uses DeepSeek V3 for analysis.
        
        Args:
            recommendations: List of recommendations to add reasoning to
            max_concurrent: Max concurrent API calls
            
        Returns:
            Recommendations with reasoning field populated
        """
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            logger.warning("[RECOMMENDATION] DeepSeek API key not set, skipping reasoning")
            return recommendations
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def add_reasoning(rec: Recommendation) -> Recommendation:
                async with semaphore:
                    reasoning = await self._call_deepseek(client, api_key, rec)
                    rec.reasoning = reasoning
                    return rec
            
            tasks = [add_reasoning(rec) for rec in recommendations]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out exceptions
            valid_results = []
            for r in results:
                if isinstance(r, Exception):
                    logger.error(f"[RECOMMENDATION] DeepSeek error: {r}")
                else:
                    valid_results.append(r)
            
            return valid_results
    
    async def _call_deepseek(
        self,
        client: httpx.AsyncClient,
        api_key: str,
        rec: Recommendation
    ) -> str:
        """Call DeepSeek API to generate recommendation reasoning."""
        
        prompt = f"""Crypto: {rec.symbol}
Price: ${rec.current_price:,.2f}
7d Change: {rec.price_change_7d:+.1f}%
30d Change: {rec.price_change_30d:+.1f}%
Score: {rec.score}/100
Momentum: {rec.components.momentum:.0f}/100
Volume: {rec.components.volume:.0f}/100
Volatility: {rec.components.volatility:.0f}/100
RSI Score: {rec.components.rsi:.0f}/100
Action: {rec.action}

Provide a 1-2 sentence trading recommendation in 40 words max. Be specific about why this crypto is a good {rec.action.lower()} opportunity based on the metrics above. Focus on the strongest indicator."""
        
        try:
            response = await client.post(
                "https://api.deepseek.com/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a crypto trading analyst. Give brief, actionable recommendations."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "max_tokens": 80,
                    "temperature": 0.3
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                reasoning = data["choices"][0]["message"]["content"].strip()
                logger.debug(f"[RECOMMENDATION] DeepSeek reasoning for {rec.symbol}: {reasoning[:50]}...")
                return reasoning
            else:
                logger.error(f"[RECOMMENDATION] DeepSeek API error: {response.status_code}")
                return f"{rec.action} signal: Strong {self._get_strongest_indicator(rec)} score."
                
        except Exception as e:
            logger.error(f"[RECOMMENDATION] DeepSeek call failed for {rec.symbol}: {e}")
            return f"{rec.action} signal: Strong {self._get_strongest_indicator(rec)} score."
    
    def _get_strongest_indicator(self, rec: Recommendation) -> str:
        """Get the name of the strongest indicator for fallback reasoning."""
        components = {
            "momentum": rec.components.momentum,
            "volume": rec.components.volume,
            "volatility": rec.components.volatility,
            "RSI": rec.components.rsi
        }
        return max(components, key=components.get)


# Singleton instance
_engine: Optional[WatchlistRecommendationEngine] = None


def get_recommendation_engine(db_session_factory=None) -> WatchlistRecommendationEngine:
    """Get or create the recommendation engine singleton."""
    global _engine
    
    if _engine is None:
        if db_session_factory is None:
            from app.db.database import SessionLocal
            db_session_factory = SessionLocal
        _engine = WatchlistRecommendationEngine(db_session_factory)
    
    return _engine

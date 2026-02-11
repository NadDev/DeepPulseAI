"""
Strategy Context Manager
Detects market regime (bullish/bearish/choppy) and controls strategy activation
Based on SMA alignment and technical indicators
"""

import logging
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass
from app.services.technical_analysis import TechnicalAnalysis

logger = logging.getLogger(__name__)


class MarketContext(str, Enum):
    """Market regimes based on trend alignment"""
    STRONG_BULLISH = "STRONG_BULLISH"      # All SMAs aligned upward (20>50>200)
    WEAK_BULLISH = "WEAK_BULLISH"          # Price above 50 but not all aligned
    STRONG_BEARISH = "STRONG_BEARISH"      # All SMAs aligned downward (20<50<200)
    WEAK_BEARISH = "WEAK_BEARISH"          # Price below 50 but not all aligned


@dataclass
class ContextAnalysis:
    """Market context analysis result"""
    market_context: MarketContext
    sma_20: float
    sma_50: float
    sma_200: float
    current_price: float
    price_position: str  # "above_50", "above_200", "below_50", "below_200", etc.
    sma_alignment_score: float  # 0-100 (higher = stronger alignment)
    volatility_ratio: float  # Current ATR vs historical average
    volume_ratio: float  # Current volume vs average
    confidence: float  # 0-100 confidence in context detection


class StrategyContextManager:
    """
    Manages strategy activation based on market context
    
    Strategies performance by context:
    - GridTrading: Works in all contexts (62.5% win rate)
    - MeanReversion: Works best in weak_bullish (needs pullbacks)
    - Scalping: Works in high volatility (needs ATR > 1.5x, volume > 2x)
    - TrendFollowing: Works in strong trends (bullish or bearish)
    - Momentum: Works in volume spikes with clear direction
    """
    
    def __init__(self):
        self.ta = TechnicalAnalysis()
        self.context_history: List[Dict[str, Any]] = []
        self.max_history = 100
    
    async def analyze_context(
        self,
        symbol: str,
        candles: List[Dict[str, Any]],
        current_price: float,
        atr: float,
        volume: float
    ) -> Optional[ContextAnalysis]:
        """
        Analyze market context for a symbol
        
        Args:
            symbol: Trading pair
            candles: OHLCV candles (need at least 200 for SMA200)
            current_price: Current market price
            atr: Current ATR value
            volume: Current volume
            
        Returns:
            ContextAnalysis with market regime and strategy recommendations
        """
        try:
            if not candles or len(candles) < 200:
                logger.warning(f"⚠️ Insufficient candles for {symbol}: {len(candles) if candles else 0}")
                return None
            
            # Validate input parameters
            if not current_price or current_price <= 0:
                logger.warning(f"⚠️ Invalid current_price for {symbol}: {current_price}")
                return None
            
            if not atr or atr <= 0:
                logger.warning(f"⚠️ Invalid ATR for {symbol}: {atr}")
                return None
            
            if not volume or volume <= 0:
                logger.warning(f"⚠️ Invalid volume for {symbol}: {volume}")
                return None
            
            # Extract OHLCV data
            closes = [c['close'] for c in candles]
            volumes = [c['volume'] for c in candles]
            
            # Calculate SMAs
            sma_20 = self.ta.calculate_sma(closes, 20)
            sma_50 = self.ta.calculate_sma(closes, 50)
            sma_200 = self.ta.calculate_sma(closes, 200)
            
            if not sma_20 or not sma_50 or not sma_200:
                logger.warning(f"⚠️ Could not calculate SMAs for {symbol}")
                return None
            
            # Get latest SMA values
            sma_20_val = sma_20[-1]
            sma_50_val = sma_50[-1]
            sma_200_val = sma_200[-1]
            
            # Validate values
            if not all([sma_20_val, sma_50_val, sma_200_val]):
                logger.warning(f"⚠️ Invalid SMA values for {symbol}")
                return None
            
            # ===== DETERMINE MARKET CONTEXT =====
            market_context, alignment_score = self._determine_context(
                current_price, sma_20_val, sma_50_val, sma_200_val
            )
            
            # ===== DETERMINE PRICE POSITION =====
            price_position = self._determine_price_position(
                current_price, sma_20_val, sma_50_val, sma_200_val
            )
            
            # ===== CALCULATE VOLATILITY RATIO =====
            # Calculate ATR for historical candles (last 20 periods)
            if len(candles) >= 20:
                historical_atrs = self.ta.calculate_atr(candles[-40:], 14)  # Need 14+20 candles
                atr_20_avg = self.ta.calculate_sma(historical_atrs[-20:], 20) if historical_atrs else None
            else:
                atr_20_avg = None
            
            if not atr or atr == 0:
                volatility_ratio = 1.0
            elif atr_20_avg and atr_20_avg[-1] and atr_20_avg[-1] > 0:
                volatility_ratio = atr / atr_20_avg[-1]
            else:
                volatility_ratio = 1.0
            
            # ===== CALCULATE VOLUME RATIO =====
            vol_20_avg = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else sum(volumes) / len(volumes)
            volume_ratio = volume / vol_20_avg if vol_20_avg > 0 else 1.0
            
            # ===== CALCULATE CONTEXT CONFIDENCE =====
            confidence = self._calculate_context_confidence(
                market_context, alignment_score, volatility_ratio, volume_ratio
            )
            
            analysis = ContextAnalysis(
                market_context=market_context,
                sma_20=sma_20_val,
                sma_50=sma_50_val,
                sma_200=sma_200_val,
                current_price=current_price,
                price_position=price_position,
                sma_alignment_score=alignment_score,
                volatility_ratio=volatility_ratio,
                volume_ratio=volume_ratio,
                confidence=confidence
            )
            
            # Log analysis
            logger.info(f"🎯 {symbol} Market Context: {market_context.value} | Alignment: {alignment_score:.0f}% | Volatility: {volatility_ratio:.2f}x | Volume: {volume_ratio:.2f}x | Confidence: {confidence:.0f}%")
            
            # Store in history
            self.context_history.append({
                "symbol": symbol,
                "context": market_context.value,
                "alignment_score": alignment_score,
                "volatility_ratio": volatility_ratio,
                "volume_ratio": volume_ratio,
                "confidence": confidence,
                "timestamp": candles[-1].get('time', 'unknown')
            })
            
            if len(self.context_history) > self.max_history:
                self.context_history = self.context_history[-self.max_history:]
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Error analyzing context for {symbol}: {type(e).__name__} - {str(e)}")
            import traceback
            logger.debug(f"Traceback: {traceback.format_exc()}")
            return None
    
    def _determine_context(
        self,
        price: float,
        sma_20: float,
        sma_50: float,
        sma_200: float
    ) -> tuple[MarketContext, float]:
        """
        Determine market context from SMA alignment
        
        BULLISH contexts:
        - STRONG_BULLISH: SMA20 > SMA50 > SMA200 (complete uptrend, all aligned)
        - WEAK_BULLISH: Price > SMA50 OR SMA50 > SMA200 (early/partial uptrend)
        
        BEARISH contexts:
        - STRONG_BEARISH: SMA20 < SMA50 < SMA200 (complete downtrend, all aligned)
        - WEAK_BEARISH: Price < SMA50 OR SMA50 < SMA200 (early/partial downtrend)
        
        Returns:
            (market_context, alignment_score_0_to_100)
        """
        # ===== BULLISH CONDITIONS =====
        
        # STRONG BULLISH: All SMAs perfectly aligned upward (20 > 50 > 200)
        if sma_20 > sma_50 > sma_200:
            alignment = ((sma_20 - sma_50) / sma_50 * 100) + ((sma_50 - sma_200) / sma_200 * 100)
            alignment = min(100, alignment * 10)  # Normalize to 0-100
            logger.debug(f"🎯 Context: STRONG_BULLISH (SMA20>{sma_20:.2f} > SMA50>{sma_50:.2f} > SMA200>{sma_200:.2f}) | Alignment: {alignment:.0f}%")
            return MarketContext.STRONG_BULLISH, alignment
        
        # WEAK BULLISH: Price > SMA50 > SMA200 (uptrend forming, but SMA20 not aligned yet)
        elif price > sma_50 > sma_200:
            alignment = ((sma_50 - sma_200) / sma_200 * 100)
            alignment = min(100, alignment * 10)
            logger.debug(f"🎯 Context: WEAK_BULLISH (Price>{price:.2f} > SMA50>{sma_50:.2f} > SMA200>{sma_200:.2f}) | Alignment: {alignment:.0f}%")
            return MarketContext.WEAK_BULLISH, alignment
        
        # WEAK BULLISH: Price just above SMA50 (early recovery, regardless of SMA200 position)
        elif price > sma_50:
            offset = (price - sma_50) / sma_50 * 100
            alignment = min(50, offset * 2)
            logger.debug(f"🎯 Context: WEAK_BULLISH (Price>{price:.2f} > SMA50>{sma_50:.2f}) | Alignment: {alignment:.0f}%")
            return MarketContext.WEAK_BULLISH, alignment
        
        # ===== BEARISH CONDITIONS =====
        
        # STRONG BEARISH: All SMAs perfectly aligned downward (20 < 50 < 200)
        elif sma_20 < sma_50 < sma_200:
            alignment = ((sma_50 - sma_20) / sma_50 * 100) + ((sma_200 - sma_50) / sma_200 * 100)
            alignment = min(100, alignment * 10)
            logger.debug(f"🎯 Context: STRONG_BEARISH (SMA20<{sma_20:.2f} < SMA50<{sma_50:.2f} < SMA200<{sma_200:.2f}) | Alignment: {alignment:.0f}%")
            return MarketContext.STRONG_BEARISH, alignment
        
        # WEAK BEARISH: Price < SMA50 < SMA200 (downtrend forming, but SMA20 not aligned yet)
        # This is the KEY FIX: Changed from "STRONG_BEARISH" to "WEAK_BEARISH"
        elif price < sma_50 < sma_200:
            alignment = ((sma_200 - sma_50) / sma_200 * 100)
            alignment = min(100, alignment * 10)
            logger.debug(f"🎯 Context: WEAK_BEARISH (Price<{price:.2f} < SMA50<{sma_50:.2f} < SMA200<{sma_200:.2f}) | Alignment: {alignment:.0f}%")
            return MarketContext.WEAK_BEARISH, alignment
        
        # WEAK BEARISH: Price just below SMA50 (early decline, regardless of SMA200 position)
        else:  # price < sma_50 (all other cases)
            offset = (sma_50 - price) / sma_50 * 100
            alignment = min(50, offset * 2)
            logger.debug(f"🎯 Context: WEAK_BEARISH (Price<{price:.2f} < SMA50<{sma_50:.2f}) | Alignment: {alignment:.0f}%")
            return MarketContext.WEAK_BEARISH, alignment
    
    def _determine_price_position(
        self,
        price: float,
        sma_20: float,
        sma_50: float,
        sma_200: float
    ) -> str:
        """Determine price position relative to SMAs"""
        if price > sma_20:
            return "above_all_SMAs"
        elif price > sma_50:
            return "between_20_and_50"
        elif price > sma_200:
            return "between_50_and_200"
        else:
            return "below_all_SMAs"
    
    def _calculate_context_confidence(
        self,
        market_context: MarketContext,
        alignment_score: float,
        volatility_ratio: float,
        volume_ratio: float
    ) -> float:
        """Calculate confidence in context detection"""
        base_confidence = alignment_score
        
        # Boost confidence if volume confirms move
        if volume_ratio > 1.5:
            base_confidence = min(100, base_confidence + 10)
        
        # Reduce confidence if volatility is extreme (might be breakout/anomaly)
        if volatility_ratio > 3:
            base_confidence = max(50, base_confidence - 15)
        
        return base_confidence
    
    def get_strategy_status(
        self,
        context: ContextAnalysis
    ) -> Dict[str, Dict[str, Any]]:
        """
        Determine which strategies should be active for this market context
        
        SPOT TRADING ONLY - Cannot short, therefore bearish markets = SKIP
        
        Returns:
            Dict with strategy status: {strategy_name: {enabled, reason, parameters, position_size_multiplier}}
        """
        ctx = context.market_context
        
        # ===== SPOT TRADING RULE: SKIP ALL IN BEARISH MARKETS =====
        # Cannot profit from downtrends in spot trading (no shorting)
        skip_all_bearish = ctx in [MarketContext.STRONG_BEARISH, MarketContext.WEAK_BEARISH]
        
        return {
            # ===== META FLAG FOR BEARISH CONTEXTS =====
            "_skip_all_trading": {
                "enabled": skip_all_bearish,
                "reason": "⛔ SPOT TRADING: Cannot profit from bearish trends (no shorting available)" if skip_all_bearish else "✅ Market allows trading"
            },
            
            # ===== GRID TRADING =====
            "gridtrading": {
                "enabled": not skip_all_bearish,  # Skip in bearish
                "reason": "✅ Works in ranging/oscillating markets" if not skip_all_bearish 
                          else "⛔ SPOT: Too risky in bearish downtrend",
                "position_size_multiplier": 1.0 if ctx == MarketContext.STRONG_BULLISH
                                           else 0.75,  # 75% in WEAK_BULLISH
                "parameters": {
                    "grid_levels": 5,
                    "position_size": 5  # % per level
                }
            },
            
            # ===== MEAN REVERSION =====
            "meanreversion": {
                "enabled": ctx == MarketContext.WEAK_BULLISH,  # ONLY weak bullish
                "reason": "✅ Pullbacks return to mean in weak uptrend" if ctx == MarketContext.WEAK_BULLISH
                          else "❌ SPOT: Dips may continue falling in bearish" if skip_all_bearish
                          else f"❌ Not suitable for {ctx.value} (needs pullbacks in uptrend)",
                "position_size_multiplier": 0.75,  # Always conservative
                "parameters": {
                    "sl_percent": 2.0,
                    "rsi_threshold": 35
                }
            },
            
            # ===== TREND FOLLOWING =====
            "trendfollowing": {
                "enabled": ctx == MarketContext.STRONG_BULLISH,  # ONLY strong bullish
                "reason": "✅ Ride the bullish trend" if ctx == MarketContext.STRONG_BULLISH
                          else "❌ SPOT: Can only follow BULLISH trends (no shorting)",
                "position_size_multiplier": 1.0,  # Full size in strong bull
                "parameters": {
                    "direction": "long",  # Always long in SPOT
                    "min_alignment_score": 60
                }
            },
            
            # ===== MOMENTUM =====
            "momentum": {
                "enabled": (ctx in [MarketContext.STRONG_BULLISH, MarketContext.WEAK_BULLISH]) 
                          and context.volume_ratio > 1.5 
                          and context.confidence > 60,
                "reason": "✅ Volume spike in bullish momentum" if (ctx in [MarketContext.STRONG_BULLISH, MarketContext.WEAK_BULLISH] and context.volume_ratio > 1.5)
                          else "❌ SPOT: Momentum only useful in bullish markets" if skip_all_bearish
                          else f"❌ Insufficient volume ({context.volume_ratio:.2f}x) or confidence",
                "position_size_multiplier": 0.75,
                "parameters": {
                    "min_volume_ratio": 1.5,
                    "min_confidence": 60
                }
            },
            
            # ===== BREAKOUT =====
            "breakout": {
                "enabled": ctx == MarketContext.STRONG_BULLISH and context.volatility_ratio > 1.0,
                "reason": "✅ Catch bullish breakouts" if ctx == MarketContext.STRONG_BULLISH and context.volatility_ratio > 1.0
                          else "❌ SPOT: Only trade BULLISH breakouts",
                "position_size_multiplier": 1.0,
                "parameters": {}
            },
            
            # ===== SCALPING =====
            "scalping": {
                "enabled": ctx in [MarketContext.STRONG_BULLISH, MarketContext.WEAK_BULLISH]
                          and context.volatility_ratio > 1.5 
                          and context.volume_ratio > 2.0,
                "reason": f"✅ High volatility ({context.volatility_ratio:.2f}x) + volume ({context.volume_ratio:.2f}x)" 
                          if (ctx in [MarketContext.STRONG_BULLISH, MarketContext.WEAK_BULLISH] and context.volatility_ratio > 1.5 and context.volume_ratio > 2.0)
                          else "❌ SPOT: Not in bearish" if skip_all_bearish
                          else f"❌ Volatility ({context.volatility_ratio:.2f}x) or volume ({context.volume_ratio:.2f}x) too low",
                "position_size_multiplier": 0.5,  # Small scalps
                "parameters": {
                    "min_volatility_ratio": 1.5,
                    "min_volume_ratio": 2.0,
                    "tp_percent": 0.3
                }
            },
            
            # ===== DCA (Long term accumulation) =====
            #"dca": {
             #   "enabled": True,  # DCA works everywhere (long-term accumulation)
             #   "reason": "✅ Long-term accumulation (6-12 months horizon)",
             #   "position_size_multiplier": 0.2 if skip_all_bearish else 1.0,  # Reduced in bearish for day trading
             #   "parameters": {}
          # },
            
            # ===== MACD CROSSOVER =====
            "macdcrossover": {
                "enabled": ctx in [MarketContext.STRONG_BULLISH, MarketContext.WEAK_BULLISH] and context.sma_alignment_score > 40,
                "reason": "✅ Moderate trend for MACD signals" if (ctx in [MarketContext.STRONG_BULLISH, MarketContext.WEAK_BULLISH] and context.sma_alignment_score > 40)
                          else "❌ SPOT: Not in bearish" if skip_all_bearish
                          else "❌ Insufficient trend alignment",
                "position_size_multiplier": 0.75,
                "parameters": {}
            },
            
            # ===== RSI DIVERGENCE =====
            "rsidivergence": {
                "enabled": ctx in [MarketContext.STRONG_BULLISH, MarketContext.WEAK_BULLISH] and context.confidence > 50,
                "reason": "✅ Clear market context" if (ctx in [MarketContext.STRONG_BULLISH, MarketContext.WEAK_BULLISH] and context.confidence > 50)
                          else "❌ SPOT: Not in bearish" if skip_all_bearish
                          else "❌ Low confidence",
                "position_size_multiplier": 0.5,
                "parameters": {}
            }
        }
    
    def log_strategy_decisions(self, symbol: str, context: ContextAnalysis):
        """Log which strategies are enabled/disabled and why"""
        strategies = self.get_strategy_status(context)
        
        # Check global skip flag
        skip_all = strategies.get("_skip_all_trading", {}).get("enabled", False)
        
        logger.info(f"\n📊 ===== STRATEGY ACTIVATION FOR {symbol} =====")
        logger.info(f"Market Context: {context.market_context.value} (Confidence: {context.confidence:.0f}%)")
        logger.info(f"Price Position: {context.price_position}")
        logger.info(f"SMA Alignment: {context.sma_alignment_score:.0f}% | Volatility: {context.volatility_ratio:.2f}x | Volume: {context.volume_ratio:.2f}x")
        
        if skip_all:
            logger.warning(f"\n⛔ GLOBAL SKIP: {strategies['_skip_all_trading']['reason']}")
        
        logger.info(f"\n🤖 Strategy Decisions:")
        
        for strategy_name, status in strategies.items():
            if strategy_name.startswith("_"):  # Skip meta flags
                continue
                
            enabled = "✅ ENABLED" if status["enabled"] else "❌ DISABLED"
            multiplier = status.get("position_size_multiplier", 1.0)
            multiplier_str = f" (size: {multiplier*100:.0f}%)" if status["enabled"] else ""
            
            logger.info(f"  {enabled:12} {strategy_name.upper():20}{multiplier_str:15} → {status['reason']}")
        
        logger.info(f"{'='*60}\n")
    
    def should_activate_strategy(
        self,
        strategy_name: str,
        context: ContextAnalysis
    ) -> bool:
        """Check if a specific strategy should be active"""
        strategies = self.get_strategy_status(context)
        return strategies.get(strategy_name, {}).get("enabled", False)
    
    def get_adjusted_parameters(
        self,
        strategy_name: str,
        context: ContextAnalysis,
        base_parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get strategy parameters adjusted for current market context
        
        Args:
            strategy_name: Name of strategy
            context: Market context analysis
            base_parameters: Base parameters from bot config
            
        Returns:
            Adjusted parameters for this context
        """
        strategies = self.get_strategy_status(context)
        strategy_config = strategies.get(strategy_name, {})
        
        adjusted = base_parameters.copy()
        
        # Apply context-specific adjustments
        if "parameters" in strategy_config:
            adjusted.update(strategy_config["parameters"])
        
        # Scale position size based on confidence
        if "position_size" in adjusted:
            confidence_multiplier = context.confidence / 100
            adjusted["position_size"] = adjusted["position_size"] * confidence_multiplier
        
        return adjusted
    
    def get_context_history(self, symbol: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent context analysis history"""
        if symbol:
            filtered = [h for h in self.context_history if h.get("symbol") == symbol]
            return filtered[-limit:]
        return self.context_history[-limit:]


# Global instance
strategy_context_manager: Optional[StrategyContextManager] = None


def initialize_strategy_context_manager() -> StrategyContextManager:
    """Initialize global strategy context manager"""
    global strategy_context_manager
    strategy_context_manager = StrategyContextManager()
    logger.info("✅ Strategy Context Manager initialized")
    return strategy_context_manager


def get_strategy_context_manager() -> Optional[StrategyContextManager]:
    """Get global strategy context manager"""
    return strategy_context_manager

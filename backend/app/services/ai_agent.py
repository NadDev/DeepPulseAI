"""
AI Trading Agent Service
Integrates with DeepSeek LLM to analyze markets and make trading decisions
"""
import asyncio
import json
import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)


class AITradingAgent:
    """
    AI-powered trading agent using DeepSeek LLM
    Analyzes market data and recommends trading actions
    """
    
    def __init__(self, api_key: str, model: str = "deepseek-chat", db_session_factory: Callable = None):
        """
        Initialize AI Trading Agent
        
        Args:
            api_key: DeepSeek API key
            model: DeepSeek model to use
            db_session_factory: Factory for database sessions
        """
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.deepseek.com/chat/completions"
        self.enabled = True
        self.mode = "observation"  # observation or trading
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self.db_session_factory = db_session_factory
        
        # Configuration
        self.check_interval = 300  # 5 minutes between analyses
        self.min_confidence_to_log = 50  # Minimum confidence to store in DB
        
        # Store decision history for learning
        self.decision_history: List[Dict[str, Any]] = []
        self.max_history = 100
    
    async def start(self):
        """Start the AI agent monitoring loop"""
        if self._running:
            logger.warning("⚠️ AI Agent already running")
            return
        
        self._running = True
        logger.info(f"🤖 AI Trading Agent started (mode: {self.mode})")
        self._task = asyncio.create_task(self._monitoring_loop())
    
    async def stop(self):
        """Stop the AI agent"""
        self._running = False
        logger.info("🛑 AI Trading Agent stopped")
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
    
    async def _monitoring_loop(self):
        """
        Main monitoring loop - analyzes watchlist markets periodically.
        In observation mode: logs recommendations but doesn't trade.
        In trading mode: could trigger trades (via AI Bot Controller).
        """
        logger.info(f"🔄 AI Agent monitoring loop started (interval: {self.check_interval}s)")
        
        # Initial delay to let system stabilize
        await asyncio.sleep(30)
        
        while self._running:
            try:
                logger.info("🔍 AI Agent: Starting market analysis cycle...")
                
                # Get watchlist symbols from database
                symbols = await self._get_watchlist_symbols()
                
                if not symbols:
                    logger.info("📋 No symbols in watchlist to analyze")
                else:
                    logger.info(f"📊 Analyzing {len(symbols)} symbols from watchlist")
                    
                    for symbol in symbols:
                        if not self._running:
                            break
                            
                        try:
                            # Fetch market data and indicators
                            data = await self._fetch_market_data(symbol)
                            
                            if data:
                                # Analyze with AI
                                analysis = await self.analyze_market(
                                    symbol=symbol,
                                    market_data={
                                        "close": data["close"],
                                        "high": data["high"],
                                        "low": data["low"],
                                        "volume": data["volume"],
                                        "change_24h": data.get("change_24h", 0)
                                    },
                                    indicators=data["indicators"]
                                )
                                
                                # Log recommendation
                                action = analysis.get("action", "NONE")
                                confidence = analysis.get("confidence", 0)
                                
                                # Store ALL decisions in decision_history for Bot Controller
                                analysis['timestamp'] = datetime.utcnow().isoformat()
                                analysis['symbol'] = symbol
                                self.decision_history.append(analysis)
                                if len(self.decision_history) > self.max_history:
                                    self.decision_history = self.decision_history[-self.max_history:]
                                
                                if action in ["BUY", "SELL"] and confidence >= self.min_confidence_to_log:
                                    logger.info(f"💡 {symbol}: {action} signal (confidence: {confidence}%)")
                                    
                                    # Store decision in DB
                                    await self._store_decision(analysis)
                                
                                # Small delay between analyses to avoid rate limits
                                await asyncio.sleep(2)
                                
                        except Exception as e:
                            logger.error(f"❌ Error analyzing {symbol}: {str(e)}")
                
                logger.info(f"✅ Analysis cycle complete. Next in {self.check_interval}s")
                
                # Wait for next cycle
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"❌ Error in AI monitoring loop: {str(e)}")
                await asyncio.sleep(60)  # Wait 1 min on error before retrying
    
    async def _get_watchlist_symbols(self) -> List[str]:
        """Get symbols from watchlist table"""
        if not self.db_session_factory:
            # Fallback to default symbols
            return ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"]
        
        try:
            from app.models.database_models import WatchlistItem
            
            db = self.db_session_factory()
            try:
                items = db.query(WatchlistItem).filter(
                    WatchlistItem.is_active == True
                ).order_by(WatchlistItem.priority.desc()).limit(20).all()
                
                # Convert BTC/USDT to BTCUSDT format
                symbols = [item.symbol.replace("/", "") for item in items]
                return symbols if symbols else ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error fetching watchlist: {str(e)}")
            return ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    
    async def _fetch_market_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch market data with ADVANCED technical analysis for AI decisions"""
        try:
            from app.services.market_data import market_data_collector
            from app.services.technical_analysis import TechnicalAnalysis
            
            # Ensure symbol format
            binance_symbol = symbol if symbol.endswith("USDT") else f"{symbol}USDT"
            
            # Get candles (need 100+ for Ichimoku which needs 52)
            candles = await market_data_collector.get_candles(binance_symbol, timeframe="1h", limit=150)
            
            if not candles or len(candles) < 52:
                logger.warning(f"Not enough candles for {binance_symbol}: {len(candles) if candles else 0}")
                return None
            
            # Calculate indicators
            ta = TechnicalAnalysis()
            closes = [c['close'] for c in candles]
            highs = [c['high'] for c in candles]
            lows = [c['low'] for c in candles]
            volumes = [c['volume'] for c in candles]
            
            # ============ BASIC INDICATORS ============
            sma_20 = ta.calculate_sma(closes, 20)
            sma_50 = ta.calculate_sma(closes, 50)
            ema_12 = ta.calculate_ema(closes, 12)
            ema_26 = ta.calculate_ema(closes, 26)
            rsi = ta.calculate_rsi(closes, 14)
            bb_upper, bb_middle, bb_lower = ta.calculate_bollinger_bands(closes, 20, 2)
            atr = ta.calculate_atr(candles, 14)
            
            # ============ MACD ============
            macd_line, signal_line, histogram = ta.calculate_macd(closes)
            macd_data = {
                "macd": round(macd_line[-1], 4) if macd_line[-1] else None,
                "signal": round(signal_line[-1], 4) if signal_line[-1] else None,
                "histogram": round(histogram[-1], 4) if histogram[-1] else None,
                "crossover": "bullish" if macd_line[-1] and signal_line[-1] and macd_line[-1] > signal_line[-1] else "bearish"
            }
            
            # ============ ICHIMOKU CLOUD ============
            ichimoku = ta.calculate_ichimoku(candles)
            logger.debug(f"🔍 {binance_symbol} Ichimoku: {ichimoku.get('status') if isinstance(ichimoku, dict) else type(ichimoku)}")
            
            # ============ FIBONACCI LEVELS ============
            fibonacci = ta.get_fibonacci_analysis(closes)
            logger.debug(f"🔍 {binance_symbol} Fibonacci: {fibonacci.get('status') if isinstance(fibonacci, dict) else type(fibonacci)}")
            
            # ============ ELLIOTT WAVES ============
            elliott = ta.detect_elliott_waves(closes, candles)
            logger.debug(f"🔍 {binance_symbol} Elliott: {elliott.get('status') if isinstance(elliott, dict) else type(elliott)}")
            
            # ============ TREND ANALYSIS ============
            trend = ta.analyze_trend(closes)
            logger.debug(f"🔍 {binance_symbol} Trend: {trend}")
            
            # ============ VOLUME ANALYSIS ============
            avg_volume_20 = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else sum(volumes) / len(volumes)
            current_volume = volumes[-1]
            volume_ratio = round(current_volume / avg_volume_20, 2) if avg_volume_20 > 0 else 1.0
            
            # ============ MULTI-TIMEFRAME TREND ============
            # Short-term (last 10 candles)
            short_trend = "bullish" if closes[-1] > closes[-10] else "bearish"
            short_change = round(((closes[-1] - closes[-10]) / closes[-10]) * 100, 2)
            
            # Medium-term (last 24 candles)
            medium_trend = "bullish" if closes[-1] > closes[-24] else "bearish"
            medium_change = round(((closes[-1] - closes[-24]) / closes[-24]) * 100, 2)
            
            # Long-term (last 50 candles)
            long_trend = "bullish" if len(closes) >= 50 and closes[-1] > closes[-50] else "bearish" if len(closes) >= 50 else "unknown"
            long_change = round(((closes[-1] - closes[-50]) / closes[-50]) * 100, 2) if len(closes) >= 50 else 0
            
            current = candles[-1]
            
            return {
                "symbol": binance_symbol,
                "close": current['close'],
                "high": current['high'],
                "low": current['low'],
                "volume": current['volume'],
                "change_24h": medium_change,
                "indicators": {
                    # Basic
                    "rsi": round(rsi[-1], 2) if rsi and rsi[-1] else None,
                    "sma_20": round(sma_20[-1], 2) if sma_20 and sma_20[-1] else None,
                    "sma_50": round(sma_50[-1], 2) if sma_50 and sma_50[-1] else None,
                    "ema_12": round(ema_12[-1], 2) if ema_12[-1] else None,
                    "ema_26": round(ema_26[-1], 2) if ema_26[-1] else None,
                    "bb_upper": round(bb_upper[-1], 2) if bb_upper and bb_upper[-1] else None,
                    "bb_middle": round(bb_middle[-1], 2) if bb_middle and bb_middle[-1] else None,
                    "bb_lower": round(bb_lower[-1], 2) if bb_lower and bb_lower[-1] else None,
                    "atr": round(atr[-1], 2) if atr and atr[-1] else None,
                    "resistance": max(highs[-20:]),
                    "support": min(lows[-20:]),
                    # MACD
                    "macd": macd_data,
                    # Ichimoku
                    "ichimoku": ichimoku if ichimoku.get("status") == "calculated" else None,
                    # Fibonacci
                    "fibonacci": fibonacci if fibonacci.get("status") == "analyzed" else None,
                    # Elliott Waves
                    "elliott_waves": elliott if elliott.get("status") == "detected" else None,
                    # Trend
                    "trend": trend,
                    # Volume
                    "volume_ratio": volume_ratio,
                    "volume_signal": "high" if volume_ratio > 1.5 else "low" if volume_ratio < 0.5 else "normal",
                    # Multi-timeframe
                    "mtf_trend": {
                        "short": {"direction": short_trend, "change_pct": short_change},
                        "medium": {"direction": medium_trend, "change_pct": medium_change},
                        "long": {"direction": long_trend, "change_pct": long_change}
                    }
                }
            }
        except Exception as e:
            logger.error(f"Error fetching market data for {symbol}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    async def _store_decision(self, analysis: Dict[str, Any]):
        """Store AI decision in database for tracking and learning"""
        if not self.db_session_factory:
            return
            
        try:
            from app.models.database_models import AIDecision
            
            db = self.db_session_factory()
            try:
                decision = AIDecision(
                    symbol=analysis.get("symbol", "UNKNOWN"),
                    action=analysis.get("action", "NONE"),
                    confidence=analysis.get("confidence", 0),
                    reasoning=analysis.get("reasoning", ""),
                    risk_level=analysis.get("risk_level", "MEDIUM"),
                    target_price=analysis.get("target_price"),
                    stop_loss=analysis.get("stop_loss"),
                    market_data=json.dumps(analysis),
                    mode=self.mode,
                    executed=False  # Observation mode doesn't execute
                )
                db.add(decision)
                db.commit()
                logger.debug(f"📝 Stored AI decision for {analysis.get('symbol')}")
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error storing AI decision: {str(e)}")

    async def analyze_market(
        self,
        symbol: str,
        market_data: Optional[Dict[str, Any]] = None,
        indicators: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze a crypto market using DeepSeek
        
        Args:
            symbol: Trading pair (e.g., BTCUSDT)
            market_data: Current price data (optional, will fetch if not provided)
            indicators: Technical indicators (optional, will fetch if not provided)
            
        Returns:
            Analysis with recommendation, confidence, and reasoning
        """
        try:
            # If no market data provided, fetch it with all advanced indicators
            if market_data is None or indicators is None:
                logger.debug(f"Fetching market data for {symbol}")
                full_data = await self._fetch_market_data(symbol)
                if not full_data:
                    return {
                        "symbol": symbol,
                        "action": "NONE",
                        "confidence": 0,
                        "reasoning": "Failed to fetch market data"
                    }
                
                logger.debug(f"Full data type: {type(full_data)}, keys: {full_data.keys() if isinstance(full_data, dict) else 'NOT A DICT'}")
                
                # Extract the components
                market_data = {
                    "close": full_data.get("close"),
                    "high": full_data.get("high"),
                    "low": full_data.get("low"),
                    "volume": full_data.get("volume"),
                    "change_24h": full_data.get("change_24h"),
                    "symbol": full_data.get("symbol")
                }
                indicators = full_data.get("indicators", {})
                logger.debug(f"Extracted indicators type: {type(indicators)}")
            
            logger.debug(f"Building prompt with market_data type: {type(market_data)}, indicators type: {type(indicators)}")
            
            # Count advanced indicators
            advanced_count = 0
            if indicators.get('macd') and isinstance(indicators.get('macd'), dict):
                advanced_count += 1
            if indicators.get('ichimoku'):
                advanced_count += 1
            if indicators.get('fibonacci'):
                advanced_count += 1
            if indicators.get('elliott_waves'):
                advanced_count += 1
            if indicators.get('mtf_trend'):
                advanced_count += 1
            
            logger.debug(f"🎯 {symbol} has {advanced_count}/5 advanced indicators available")
            
            # Build analysis prompt
            prompt = self._build_analysis_prompt(symbol, market_data, indicators)
            
            # Log first 500 chars of prompt to see what's being sent
            logger.debug(f"📝 Prompt preview (first 500 chars): {prompt[:500]}...")
            
            # Call DeepSeek API
            response = await self._call_deepseek(prompt)
            
            if not response:
                return {
                    "symbol": symbol,
                    "action": "NONE",
                    "confidence": 0,
                    "reasoning": "Failed to get AI response"
                }
            
            # Log the raw response
            logger.debug(f"🤖 DeepSeek raw response (first 300 chars): {response[:300]}...")
            
            # Parse response
            analysis = self._parse_analysis_response(response)
            analysis["symbol"] = symbol
            analysis["timestamp"] = datetime.utcnow().isoformat()
            
            # Store in history
            self._store_decision(analysis)
            
            logger.info(f"📊 {symbol} Analysis: {analysis['action']} (confidence: {analysis.get('confidence', 0)}%)")
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Error analyzing {symbol}: {str(e)}")
            return {
                "symbol": symbol,
                "action": "NONE",
                "confidence": 0,
                "error": str(e)
            }
    
    async def get_recommendations(
        self,
        symbols: List[str],
        market_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Get trading recommendations for multiple symbols
        
        Args:
            symbols: List of trading pairs to analyze
            market_data: Market data for all symbols
            
        Returns:
            List of recommendations ranked by confidence
        """
        recommendations = []
        
        for symbol in symbols:
            if symbol in market_data:
                # Use the new simplified API - just pass the symbol
                analysis = await self.analyze_market(symbol)
                
                if analysis["action"] != "NONE":
                    recommendations.append(analysis)
        
        # Sort by confidence
        recommendations.sort(
            key=lambda x: x.get("confidence", 0),
            reverse=True
        )
        
        return recommendations
    
    def _build_analysis_prompt(
        self,
        symbol: str,
        market_data: Dict[str, Any],
        indicators: Dict[str, Any]
    ) -> str:
        """Build ENRICHED analysis prompt for DeepSeek with advanced technical analysis"""
        
        # Add safety check
        if not isinstance(market_data, dict):
            logger.error(f"market_data is not a dict: {type(market_data)}")
            market_data = {}
        if not isinstance(indicators, dict):
            logger.error(f"indicators is not a dict: {type(indicators)}")
            indicators = {}
        
        current_price = market_data.get("close", 0)
        
        # ============ BASIC DATA ============
        basic_section = f"""## Market Data for {symbol}
- Current Price: ${current_price:,.2f}
- 24h Change: {market_data.get('change_24h', 0)}%
- Volume: {market_data.get('volume', 0):,.0f}
- High: ${market_data.get('high', 0):,.2f}
- Low: ${market_data.get('low', 0):,.2f}"""

        # ============ BASIC INDICATORS ============
        basic_indicators = f"""## Basic Technical Indicators
- RSI (14): {indicators.get('rsi', 'N/A')} {'⚠️ OVERSOLD' if indicators.get('rsi') and indicators.get('rsi') < 30 else '⚠️ OVERBOUGHT' if indicators.get('rsi') and indicators.get('rsi') > 70 else ''}
- SMA 20: ${indicators.get('sma_20', 'N/A')}
- SMA 50: ${indicators.get('sma_50', 'N/A')}
- EMA 12: ${indicators.get('ema_12', 'N/A')}
- EMA 26: ${indicators.get('ema_26', 'N/A')}
- ATR: ${indicators.get('atr', 'N/A')}
- Support: ${indicators.get('support', 'N/A')}
- Resistance: ${indicators.get('resistance', 'N/A')}"""

        # ============ BOLLINGER BANDS ============
        bb_section = f"""## Bollinger Bands
- Upper: ${indicators.get('bb_upper', 'N/A')}
- Middle: ${indicators.get('bb_middle', 'N/A')}
- Lower: ${indicators.get('bb_lower', 'N/A')}
- Price Position: {'Near Upper (Potential Resistance)' if indicators.get('bb_upper') and current_price > indicators.get('bb_upper') * 0.98 else 'Near Lower (Potential Support)' if indicators.get('bb_lower') and current_price < indicators.get('bb_lower') * 1.02 else 'Middle Range'}"""

        # ============ MACD ============
        macd = indicators.get('macd', {})
        if not isinstance(macd, dict):
            macd = {}
        macd_section = f"""## MACD Analysis
- MACD Line: {macd.get('macd', 'N/A')}
- Signal Line: {macd.get('signal', 'N/A')}
- Histogram: {macd.get('histogram', 'N/A')} {'📈 Increasing momentum' if macd.get('histogram') and macd.get('histogram') > 0 else '📉 Decreasing momentum' if macd.get('histogram') else ''}
- Crossover: {macd.get('crossover', 'N/A').upper() if isinstance(macd.get('crossover'), str) else 'N/A'}"""

        # ============ ICHIMOKU CLOUD ============
        ichimoku = indicators.get('ichimoku', {})
        if not isinstance(ichimoku, dict):
            ichimoku = {}
        ichimoku_section = ""
        if ichimoku and ichimoku.get('status') == 'calculated':
            ichimoku_section = f"""## Ichimoku Cloud Analysis
- Tenkan-sen (Conversion): ${ichimoku.get('tenkan_sen', 'N/A')}
- Kijun-sen (Base): ${ichimoku.get('kijun_sen', 'N/A')}
- Cloud Top (Senkou A): ${ichimoku.get('cloud_top', 'N/A')}
- Cloud Bottom (Senkou B): ${ichimoku.get('cloud_bottom', 'N/A')}
- TK Cross: {ichimoku.get('tk_cross', 'N/A').upper() if isinstance(ichimoku.get('tk_cross'), str) else 'N/A'}
- Price vs Cloud: {ichimoku.get('cloud_position', 'N/A').upper() if isinstance(ichimoku.get('cloud_position'), str) else 'N/A'} → Signal: {ichimoku.get('signal', 'N/A').upper() if isinstance(ichimoku.get('signal'), str) else 'N/A'}"""

        # ============ FIBONACCI ============
        fib = indicators.get('fibonacci', {})
        if not isinstance(fib, dict):
            fib = {}
        fib_section = ""
        if fib and fib.get('status') == 'analyzed':
            fib_levels = fib.get('retracement_levels', {})
            if not isinstance(fib_levels, dict):
                fib_levels = {}
            fib_section = f"""## Fibonacci Retracement Levels (Trend: {fib.get('trend', 'N/A').upper() if isinstance(fib.get('trend'), str) else 'N/A'})
- 0.0%: ${fib_levels.get('0.0', 'N/A')}
- 23.6%: ${fib_levels.get('0.236', 'N/A')}
- 38.2%: ${fib_levels.get('0.382', 'N/A')} (KEY LEVEL)
- 50.0%: ${fib_levels.get('0.5', 'N/A')}
- 61.8%: ${fib_levels.get('0.618', 'N/A')} (GOLDEN RATIO - STRONGEST)
- 78.6%: ${fib_levels.get('0.786', 'N/A')}
- Nearest Support: ${fib.get('nearest_support', 'N/A')}
- Nearest Resistance: ${fib.get('nearest_resistance', 'N/A')}
- Position in Range: {fib.get('position_in_range', 0) * 100:.1f}%"""

        # ============ ELLIOTT WAVES ============
        elliott = indicators.get('elliott_waves', {})
        if not isinstance(elliott, dict):
            elliott = {}
        elliott_section = ""
        if elliott and elliott.get('status') == 'detected':
            current_pos = elliott.get('current_position', {})
            if not isinstance(current_pos, dict):
                current_pos = {}
            prediction = elliott.get('prediction', {})
            if not isinstance(prediction, dict):
                prediction = {}
            elliott_section = f"""## Elliott Wave Analysis
- Current Phase: {current_pos.get('phase', 'N/A')} (Wave {current_pos.get('current_wave', 'N/A')})
- Next Expected Wave: {prediction.get('next_wave', 'N/A')}
- Predicted Direction: {prediction.get('direction', 'N/A').upper()}
- Target Price: ${prediction.get('target_price', 'N/A')}
- Wave Confidence: {elliott.get('confidence', 0) * 100:.0f}%"""

        # ============ VOLUME ANALYSIS ============
        volume_section = f"""## Volume Analysis
- Current Volume Ratio: {indicators.get('volume_ratio', 1.0)}x (vs 20-period avg)
- Volume Signal: {indicators.get('volume_signal', 'normal').upper()} {'🔥 High volume confirms move!' if indicators.get('volume_signal') == 'high' else '⚠️ Low volume - weak conviction' if indicators.get('volume_signal') == 'low' else ''}"""

        # ============ MULTI-TIMEFRAME ============
        mtf = indicators.get('mtf_trend', {})
        if not isinstance(mtf, dict):
            mtf = {}
        mtf_section = ""
        if mtf:
            short = mtf.get('short', {})
            if not isinstance(short, dict):
                short = {}
            medium = mtf.get('medium', {})
            if not isinstance(medium, dict):
                medium = {}
            long = mtf.get('long', {})
            if not isinstance(long, dict):
                long = {}
            
            # Trend alignment score
            trends = [short.get('direction'), medium.get('direction'), long.get('direction')]
            bullish_count = trends.count('bullish')
            alignment = "STRONG BULLISH" if bullish_count == 3 else "STRONG BEARISH" if bullish_count == 0 else "MIXED/CHOPPY"
            
            mtf_section = f"""## Multi-Timeframe Trend Analysis
- Short-term (10H): {short.get('direction', 'N/A').upper() if isinstance(short.get('direction'), str) else 'N/A'} ({short.get('change_pct', 0):+.2f}%)
- Medium-term (24H): {medium.get('direction', 'N/A').upper() if isinstance(medium.get('direction'), str) else 'N/A'} ({medium.get('change_pct', 0):+.2f}%)
- Long-term (50H): {long.get('direction', 'N/A').upper() if isinstance(long.get('direction'), str) else 'N/A'} ({long.get('change_pct', 0):+.2f}%)
- Trend Alignment: {alignment} ({'✅ All timeframes agree' if bullish_count in [0, 3] else '⚠️ Conflicting signals'})"""

        # ============ OVERALL TREND ============
        trend = indicators.get('trend', {})
        if not isinstance(trend, dict):
            trend = {}
        trend_section = f"""## Overall Trend Summary
- Direction: {trend.get('direction', 'N/A').upper() if isinstance(trend.get('direction'), str) else 'N/A'}
- Strength: {trend.get('strength', 'N/A')}
- Momentum: {trend.get('momentum', 'N/A')}"""

        # ============ COMBINED PROMPT ============
        return f"""Analyze this crypto trading opportunity using ADVANCED technical analysis and provide a precise trading recommendation.

{basic_section}

{basic_indicators}

{bb_section}

{macd_section}

{ichimoku_section}

{fib_section}

{elliott_section}

{volume_section}

{mtf_section}

{trend_section}

## Your Analysis Task
Using ALL the above technical data, provide a comprehensive analysis:

1. **Recommendation**: BUY, SELL, or HOLD
   - BUY: Multiple bullish signals aligned (RSI not overbought, price above cloud, bullish MACD, etc.)
   - SELL: Multiple bearish signals aligned (RSI overbought, price below cloud, bearish MACD, etc.)
   - HOLD: Conflicting signals or unclear direction

2. **Confidence**: 0-100% based on signal alignment
   - 80-100%: 4+ indicators aligned, strong volume, clear trend
   - 60-80%: 3 indicators aligned, decent volume
   - 40-60%: Mixed signals, wait for clarity
   - <40%: Conflicting signals, high risk

3. **Reasoning**: Cite SPECIFIC indicators that support your decision

4. **Risk Level**: Based on ATR, volatility, and trend strength

5. **Target**: Use Fibonacci extensions or resistance levels

6. **Stop Loss**: Use Fibonacci retracements or support levels

Format your response as JSON:
{{
  "action": "BUY|SELL|HOLD",
  "confidence": <0-100>,
  "reasoning": "<cite specific indicators like 'RSI at 32 shows oversold, MACD bullish crossover, price above Ichimoku cloud'>",
  "risk_level": "LOW|MEDIUM|HIGH",
  "target_price": <number based on Fib extensions or resistance>,
  "stop_loss": <number based on Fib retracements or support>,
  "timeframe": "1h|4h|1d",
  "key_levels": {{
    "resistance": <nearest resistance>,
    "support": <nearest support>
  }},
  "signals_summary": {{
    "bullish": ["<list bullish signals>"],
    "bearish": ["<list bearish signals>"]
  }}
}}

IMPORTANT GUIDELINES:
- Be BOLD: If 4+ indicators align, confidence should be 70%+
- Use SPECIFIC numbers from the data in your reasoning
- HOLD is valid when signals conflict, but if most align → take action
- Volume confirms moves: high volume = higher confidence
- Multi-timeframe alignment = higher confidence"""
    
    async def _call_deepseek(self, prompt: str) -> Optional[str]:
        """
        Call DeepSeek API with the prompt
        
        Args:
            prompt: Analysis prompt
            
        Returns:
            API response text
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.base_url,
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "system",
                                "content": """You are an elite quantitative crypto trading analyst with expertise in:
- Technical Analysis (RSI, MACD, Bollinger Bands, Moving Averages)
- Advanced Patterns (Ichimoku Cloud, Elliott Waves, Fibonacci)
- Multi-timeframe Analysis
- Volume Profile Analysis

Your job is to analyze market data and provide ACTIONABLE trading recommendations.

CRITICAL RULES:
1. Be DECISIVE - If multiple indicators align (3+), recommend BUY or SELL with high confidence
2. Cite SPECIFIC indicator values in your reasoning (e.g., "RSI at 28 is oversold")
3. HOLD only when signals genuinely conflict or market is ranging
4. Adjust confidence based on indicator alignment:
   - 4+ aligned signals = 75-90% confidence
   - 3 aligned signals = 60-75% confidence  
   - 2 aligned signals = 45-60% confidence
   - <2 aligned signals = HOLD recommendation
5. Volume confirms moves - high volume = +10% confidence
6. Multi-timeframe alignment = +10% confidence

Always respond with valid JSON only, no markdown code blocks."""
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": 0.4,  # Slightly higher for more varied responses
                        "max_tokens": 800  # More space for detailed reasoning
                    },
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    logger.error(f"DeepSeek API error: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to call DeepSeek API: {str(e)}")
            return None
    
    def _parse_analysis_response(self, response: str) -> Dict[str, Any]:
        """
        Parse DeepSeek response into structured data
        
        Args:
            response: Raw API response
            
        Returns:
            Parsed analysis dictionary
        """
        try:
            # Extract JSON from response (might be wrapped in markdown)
            json_str = response
            
            # Try to find JSON block if wrapped in markdown
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                parts = response.split("```")
                if len(parts) >= 2:
                    json_str = parts[1]
            
            # Clean up the string
            json_str = json_str.strip()
            
            # Remove any leading/trailing text before/after JSON
            if json_str.startswith("{"):
                # Find the matching closing brace
                brace_count = 0
                end_idx = 0
                for i, char in enumerate(json_str):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_idx = i + 1
                            break
                json_str = json_str[:end_idx]
            
            analysis = json.loads(json_str)
            
            # Validate required fields
            if "action" not in analysis:
                analysis["action"] = "HOLD"
            else:
                # Normalize action
                analysis["action"] = analysis["action"].upper().strip()
                if analysis["action"] not in ["BUY", "SELL", "HOLD"]:
                    analysis["action"] = "HOLD"
            
            if "confidence" not in analysis:
                analysis["confidence"] = 50
            else:
                # Ensure confidence is a number
                try:
                    analysis["confidence"] = int(float(analysis["confidence"]))
                    analysis["confidence"] = max(0, min(100, analysis["confidence"]))
                except:
                    analysis["confidence"] = 50
            
            if "reasoning" not in analysis:
                analysis["reasoning"] = "No reasoning provided"
            
            # Log the parsed analysis for debugging
            logger.info(f"📊 Parsed AI Response: action={analysis['action']}, confidence={analysis['confidence']}%")
            logger.debug(f"📝 Reasoning: {analysis.get('reasoning', 'N/A')[:200]}")
            
            return analysis
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse DeepSeek response as JSON: {str(e)}")
            logger.error(f"Raw response: {response[:500]}")
            
            # Try to extract key info using regex as fallback
            import re
            action_match = re.search(r'"action"\s*:\s*"(BUY|SELL|HOLD)"', response, re.IGNORECASE)
            conf_match = re.search(r'"confidence"\s*:\s*(\d+)', response)
            
            return {
                "action": action_match.group(1).upper() if action_match else "HOLD",
                "confidence": int(conf_match.group(1)) if conf_match else 50,
                "reasoning": "Parsed from malformed JSON response"
            }
    
    def _store_decision(self, analysis: Dict[str, Any]):
        """Store decision in history for learning"""
        self.decision_history.append(analysis)
        
        # Keep only recent decisions
        if len(self.decision_history) > self.max_history:
            self.decision_history = self.decision_history[-self.max_history:]
    
    def get_decision_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent decisions from history"""
        return self.decision_history[-limit:]
    
    def set_mode(self, mode: str):
        """
        Set agent mode
        
        Args:
            mode: 'observation' (log only) or 'trading' (execute trades)
        """
        if mode not in ["observation", "trading"]:
            logger.warning(f"Invalid mode: {mode}")
            return
        
        self.mode = mode
        logger.info(f"🤖 AI Agent mode changed to: {mode}")
    
    async def chat(self, message: str, context: Dict[str, Any] = None) -> str:
        """
        Chat with the AI agent about trading
        
        Args:
            message: User message/question
            context: Optional context (active bots, recent decisions, etc.)
            
        Returns:
            AI response text
        """
        try:
            # Build chat prompt with context
            context_str = ""
            if context:
                if context.get("active_bots"):
                    context_str += f"\n\nActive AI Bots:\n"
                    for bot in context["active_bots"][:5]:
                        context_str += f"- {bot.get('name')}: {bot.get('symbol')} ({bot.get('status')})\n"
                
                if context.get("recent_decisions"):
                    context_str += f"\n\nRecent Decisions:\n"
                    for dec in context["recent_decisions"][:3]:
                        context_str += f"- {dec.get('symbol')}: {dec.get('action')} ({dec.get('confidence')}%)\n"
            
            prompt = f"""You are an AI Trading Assistant. Answer the user's question about crypto trading.
            
Current Mode: {self.mode}
{context_str}

User Question: {message}

Provide a helpful, concise response. If asked about market conditions or specific cryptos, 
give your analysis based on general market knowledge. Be honest about uncertainty."""

            # Call DeepSeek
            response = await self._call_deepseek(prompt)
            
            if response:
                return response
            else:
                return "I'm having trouble connecting right now. Please try again later."
                
        except Exception as e:
            logger.error(f"❌ Error in AI chat: {str(e)}")
            return f"Error: {str(e)}"
    
    def get_status(self) -> Dict[str, Any]:
        """Get agent status"""
        return {
            "enabled": self.enabled,
            "mode": self.mode,
            "running": self._running,
            "model": self.model,
            "decisions_count": len(self.decision_history),
            "last_decision": self.decision_history[-1] if self.decision_history else None
        }


# Global instance
ai_agent: Optional[AITradingAgent] = None


def initialize_ai_agent(api_key: str, model: str = "deepseek-chat", db_session_factory=None, mode: str = "observation"):
    """Initialize global AI agent instance"""
    global ai_agent
    ai_agent = AITradingAgent(api_key, model, db_session_factory)
    ai_agent.mode = mode  # Set mode from environment
    return ai_agent


def get_ai_agent() -> Optional[AITradingAgent]:
    """Get global AI agent instance"""
    return ai_agent

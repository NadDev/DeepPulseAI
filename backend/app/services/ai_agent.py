"""
AI Trading Agent Service
Integrates with DeepSeek LLM to analyze markets and make trading decisions
Supports autonomous trading mode with centralized risk management
"""
import asyncio
import json
import logging
import uuid as uuid_module
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)


class AITradingAgent:
    """
    AI-powered trading agent using DeepSeek LLM
    Analyzes market data and recommends trading actions
    """
    
    def __init__(self, api_key: str, model: str = "deepseek-chat", db_session_factory: Callable = None, user_id: str = None):
        """
        Initialize AI Trading Agent
        
        Args:
            api_key: DeepSeek API key
            model: DeepSeek model to use
            db_session_factory: Factory for database sessions
            user_id: User ID this AI agent belongs to (for per-user AI)
        """
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.deepseek.com/chat/completions"
        self.enabled = True
        self.mode = "observation"  # observation, advisory, or autonomous
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self.db_session_factory = db_session_factory
        self.user_id = user_id  # Store user_id for per-user AI
        
        # Configuration
        self.check_interval = 300  # 5 minutes between analyses
        self.min_confidence_to_log = 60  # Minimum confidence to store in DB
        
        # Autonomous trading configuration
        self.autonomous_enabled = False  # Toggle for autonomous trading
        self.autonomous_config = {
            "position_size_pct": 5.0,
            "min_confidence": 60,  # Harmonized with RiskManager at 60% threshold
            "use_risk_manager_sl_tp": True,
            "notifications_enabled": True
        }
        self.risk_manager = None  # Will be initialized if autonomous mode
        
        # Store decision history for learning
        self.decision_history: List[Dict[str, Any]] = []
        self.max_history = 100
    
    def enable_autonomous_mode(self, enabled: bool = True):
        """
        Enable or disable autonomous trading mode
        When enabled, AI will execute trades directly using RiskManager
        """
        self.autonomous_enabled = enabled
        if enabled:
            self.mode = "autonomous"
            # Initialize RiskManager if not already done
            if self.risk_manager is None and self.db_session_factory:
                from app.services.risk_manager import RiskManager
                self.risk_manager = RiskManager(self.db_session_factory)
            logger.info("🤖 AI Agent: AUTONOMOUS MODE ENABLED - Will execute trades automatically")
        else:
            self.mode = "observation"
            logger.info("🤖 AI Agent: Autonomous mode disabled - Observation only")
    
    async def start(self):
        """Start the AI agent monitoring loop"""
        if self._running:
            logger.warning("⚠️ AI Agent already running")
            return
        
        self._running = True
        logger.info(f"🤖 AI Trading Agent started (mode: {self.mode})")
        self._task = asyncio.create_task(self._monitoring_loop())
        
        # ====== ARCHITECTURE CHANGE: Position monitoring now handled by SLTPManager ======
        # _position_monitoring_loop() is DEPRECATED - SLTPManager handles all exit logic
        # self._position_monitor_task = asyncio.create_task(self._position_monitoring_loop())
        logger.info("ℹ️ AI Agent: Exit monitoring delegated to SLTPManager")
    
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
        
        # Cancel position monitoring task (if running - deprecated)
        if hasattr(self, '_position_monitor_task') and self._position_monitor_task:
            self._position_monitor_task.cancel()
            try:
                await self._position_monitor_task
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
                                # === PHASE 2: Fetch ML predictions for context ===
                                ml_prediction = await self._fetch_ml_prediction(symbol)
                                if ml_prediction:
                                    logger.info(f"🧠 {symbol} ML Prediction: 7d price ${ml_prediction.get('pred_7d', 'N/A')} (confidence: {ml_prediction.get('confidence_7d', 0):.0%})")
                                
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
                                    indicators=data["indicators"],
                                    ml_prediction=ml_prediction
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
                                    decision_id = await self._store_decision(analysis)
                                    
                                    # === AUTONOMOUS MODE: Execute trade if enabled ===
                                    logger.info(f"🤖 [DEBUG] autonomous_enabled={self.autonomous_enabled}, risk_manager={self.risk_manager is not None}, user_id={self.user_id}")
                                    if self.autonomous_enabled and self.risk_manager:
                                        logger.info(f"🤖 [AUTONOMOUS] Executing {action} for {symbol} (conf: {confidence}%)")
                                        await self._execute_autonomous_trade(
                                            symbol=symbol,
                                            action=action,
                                            confidence=confidence,
                                            analysis=analysis,
                                            market_data=data,
                                            decision_id=decision_id
                                        )
                                    else:
                                        logger.info(f"ℹ️ [INFO] Autonomous trading not enabled for {symbol} (autonomous_enabled={self.autonomous_enabled}, has_rm={self.risk_manager is not None})")
                                
                                # Small delay between analyses to avoid rate limits
                                await asyncio.sleep(2)
                                
                        except Exception as e:
                            logger.error(f"❌ Error analyzing {symbol}: {str(e)}")
                
                # === ARCHITECTURE CHANGE: Position monitoring now handled by SLTPManager ===
                # _monitor_autonomous_positions() is DEPRECATED
                # SLTPManager handles all SL/TP/Trailing logic for better cohesion
                # if self.autonomous_enabled:
                #     await self._monitor_autonomous_positions()
                
                logger.info(f"✅ Analysis cycle complete. Next in {self.check_interval}s")
                
                # Wait for next cycle
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"❌ Error in AI monitoring loop: {str(e)}")
                await asyncio.sleep(60)  # Wait 1 min on error before retrying
    
    async def _position_monitoring_loop(self):
        """
        ⚡ QUICK WIN: Lightweight position monitoring every 60 seconds
        
        This loop runs INDEPENDENTLY of the 300s analysis cycle.
        It ONLY checks TP/SL for open AI_AGENT positions, no market analysis.
        
        Benefits:
        - Faster response to TP/SL triggers (60s vs 300s)
        - Doesn't affect analysis frequency
        - Minimal overhead (just price check + DB update)
        - Can coexist until full TradeExecutionService refactoring
        """
        logger.info("⚡ Position monitoring loop started (60s interval)")
        
        while self._running:
            try:
                # Only check if autonomous trading is enabled
                if self.autonomous_enabled:
                    await self._monitor_autonomous_positions()
                
                # Wait 60 seconds before next check
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"❌ Error in position monitoring loop: {str(e)}")
                await asyncio.sleep(60)
    
    async def _get_watchlist_symbols(self) -> List[str]:
        """Get symbols from watchlist table for this user"""
        if not self.db_session_factory:
            # Fallback to default symbols
            return ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"]
        
        try:
            from app.models.database_models import WatchlistItem
            from uuid import UUID
            
            db = self.db_session_factory()
            try:
                query = db.query(WatchlistItem).filter(
                    WatchlistItem.is_active == True
                )
                
                # Filter by user_id if provided (per-user AI)
                if self.user_id:
                    try:
                        query = query.filter(WatchlistItem.user_id == UUID(self.user_id))
                    except Exception as uuid_error:
                        logger.warning(f"Invalid user_id format: {self.user_id}, using all watchlist items")
                
                items = query.order_by(WatchlistItem.priority.desc()).limit(20).all()
                
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
    
    
    async def _fetch_ml_prediction(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        PHASE 2: Fetch LSTM ML predictions for symbol
        
        Args:
            symbol: Trading pair (e.g., BTCUSDT)
        
        Returns:
            ML prediction data with 1h/24h/7d forecasts and confidence scores
        """
        try:
            from app.services.ml_engine import ml_engine
            
            # Fetch latest LSTM prediction for symbol
            result = await ml_engine.predict_price(symbol=symbol.upper(), lookback_days=90)
            
            if result.get("status") == "success":
                predictions = result.get("predictions", {})
                return {
                    "pred_1h": predictions.get("1h", {}).get("price"),
                    "confidence_1h": predictions.get("1h", {}).get("confidence", 0),
                    "pred_24h": predictions.get("24h", {}).get("price"),
                    "confidence_24h": predictions.get("24h", {}).get("confidence", 0),
                    "pred_7d": predictions.get("7d", {}).get("price"),
                    "confidence_7d": predictions.get("7d", {}).get("confidence", 0),
                    "patterns": result.get("patterns", []),
                    "timestamp": result.get("timestamp")
                }
            else:
                logger.debug(f"ML prediction not available for {symbol}: {result.get('message', 'Unknown error')}")
                return None
                
        except Exception as e:
            logger.debug(f"Error fetching ML prediction for {symbol}: {str(e)}")
            return None
    
    def _calculate_ml_weighted_confidence(
        self,
        technical_confidence: float,
        ml_prediction: Optional[Dict[str, Any]],
        current_price: float,
        action: str
    ) -> Dict[str, Any]:
        """
        PHASE 2: Calculate ML-weighted confidence using proper ratios
        
        Formula: final_confidence = (technical × 0.60) + (ml_avg × 0.30) + (alignment_bonus × 0.10)
        
        Args:
            technical_confidence: Technical analysis confidence (0-100)
            ml_prediction: ML prediction data with 1h/24h/7d forecasts
            current_price: Current market price
            action: Trading action (BUY, SELL, HOLD)
        
        Returns:
            Dict with weighted confidence, ML component, alignment status
        """
        if not ml_prediction:
            return {
                "final_confidence": technical_confidence,
                "technical_component": technical_confidence,
                "ml_component": 0,
                "alignment_bonus": 0,
                "ml_available": False,
                "reasoning": "No ML prediction available - using pure technical analysis"
            }
        
       # Extract ML confidence scores (average of 3 timeframes)
        conf_1h = ml_prediction.get("confidence_1h", 0)
        conf_24h = ml_prediction.get("confidence_24h", 0)
        conf_7d = ml_prediction.get("confidence_7d", 0)
        
        # FIX: Convert to percentage if in 0-1 range (LSTM returns decimals)
        if 0 < conf_1h <= 1:
            conf_1h = conf_1h * 100
        if 0 < conf_24h <= 1:
            conf_24h = conf_24h * 100
        if 0 < conf_7d <= 1:
            conf_7d = conf_7d * 100
        
        ml_avg = (conf_1h + conf_24h + conf_7d) / 3
        
        # Determine ML direction
        pred_7d = ml_prediction.get("pred_7d", current_price)
        ml_direction = "BULLISH" if pred_7d > current_price * 1.01 else "BEARISH" if pred_7d < current_price * 0.99 else "NEUTRAL"
        
        # Determine technical direction from action
        tech_direction = "BULLISH" if action == "BUY" else "BEARISH" if action == "SELL" else "NEUTRAL"
        
        # Calculate alignment bonus (0-10%)
        alignment_bonus = 0
        alignment_status = "divergent"
        if ml_direction == tech_direction and tech_direction != "NEUTRAL":
            alignment_bonus = 10  # Full 10% bonus when aligned
            alignment_status = "aligned"
        elif ml_direction == tech_direction:
            alignment_bonus = 5  # 5% bonus for neutral consensus
            alignment_status = "neutral_consensus"
        else:
            alignment_bonus = -5  # -5% penalty when divergent
            alignment_status = "divergent"
        
        # Use ML confidence directly (already weighted appropriately in final calculation)
        ml_component = ml_avg
        
        # Final weighted calculation: 60% technical + 30% ML + 10% alignment
        final_confidence = (technical_confidence * 0.60) + (ml_component * 0.30) + alignment_bonus
        final_confidence = max(0, min(100, final_confidence))  # Clamp 0-100
        
        return {
            "final_confidence": round(final_confidence, 1),
            "technical_component": round(technical_confidence * 0.60, 1),
            "ml_component": round(ml_component * 0.30, 1),
            "alignment_bonus": alignment_bonus,
            "ml_available": True,
            "ml_direction": ml_direction,
            "technical_direction": tech_direction,
            "alignment_status": alignment_status,
            "ml_avg_confidence": round(ml_avg, 1),
            "reasoning": f"Technical ({technical_confidence}% × 0.60) + ML ({ml_component}% × 0.30) + Alignment ({alignment_bonus}%) = {final_confidence}%"
        }
    
    async def _store_decision(self, analysis: Dict[str, Any]) -> Optional[str]:
        """Store AI decision in database for tracking and learning
        
        Returns:
            Decision ID if stored successfully, None otherwise
        """
        # === CRITICAL: Only store if we have a valid user_id (per-user AI) ===
        # Check for None, string "None", empty string, etc.
        if not self.user_id or self.user_id == "None" or str(self.user_id).strip() == "":
            logger.warning(f"⚠️ Skipping decision storage - user_id missing or invalid (got: {repr(self.user_id)})")
            return None
            
        if not self.db_session_factory:
            logger.debug(f"Skipping decision storage - no DB connection")
            return None
            
        try:
            from app.models.database_models import AIDecision
            
            db = self.db_session_factory()
            try:
                decision = AIDecision(
                    user_id=self.user_id,  # Per-user AI tracking - required non-null
                    symbol=analysis.get("symbol", "UNKNOWN"),
                    action=analysis.get("action", "NONE"),
                    confidence=analysis.get("confidence", 0),
                    reasoning=analysis.get("reasoning", ""),
                    risk_level=analysis.get("risk_level", "MEDIUM"),
                    target_price=analysis.get("target_price"),
                    stop_loss=analysis.get("stop_loss"),
                    mode=self.mode,
                    executed=False  # Will be updated if autonomous trade executes
                )
                db.add(decision)
                db.commit()
                decision_id = str(decision.id)
                logger.debug(f"📝 Stored AI decision {decision_id} for {analysis.get('symbol')} (user_id={self.user_id})")
                return decision_id
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error storing AI decision: {str(e)}")
            return None

    async def _execute_autonomous_trade(
        self,
        symbol: str,
        action: str,
        confidence: int,
        analysis: Dict[str, Any],
        market_data: Dict[str, Any],
        decision_id: Optional[str] = None
    ):
        """
        Execute an autonomous trade based on AI decision
        Uses RiskManager for validation and creates trade directly
        """
        from uuid import UUID
        
        if not self.risk_manager:
            logger.warning("❌ Cannot execute autonomous trade - RiskManager not initialized")
            return
        
        if not self.user_id:
            logger.warning("❌ Cannot execute autonomous trade - user_id missing")
            return
        
        current_price = market_data.get("close", 0)
        if not current_price:
            logger.warning(f"❌ Cannot execute {action} for {symbol} - no price data")
            return
        
        logger.info(f"🤖 [AUTONOMOUS] Attempting {action} on {symbol} (confidence: {confidence}%)")
        
        try:
            # Validate trade with RiskManager
            validation = await self.risk_manager.validate_trade(
                user_id=UUID(self.user_id),
                symbol=symbol,
                side=action,
                entry_price=current_price,
                source="AI_AGENT",
                confidence=confidence,
                market_data=market_data
            )
            
            if not validation.allowed:
                logger.info(f"⚠️ [AUTONOMOUS] {symbol} {action} BLOCKED: {validation.reason}")
                # Update decision status in DB
                await self._update_decision_status(decision_id, "BLOCKED", validation.reason)
                return
            
            # Log warnings
            for warning in validation.warnings:
                logger.warning(f"⚠️ [AUTONOMOUS] {symbol}: {warning}")
            
            # Execute the trade
            if action == "BUY":
                trade_id = await self._create_ai_trade(
                    symbol=symbol,
                    side="BUY",
                    entry_price=current_price,
                    stop_loss=validation.stop_loss,
                    take_profit=validation.take_profit,
                    position_amount=validation.adjusted_amount,
                    confidence=confidence,
                    reasoning=analysis.get("reasoning", "AI Autonomous Trade")
                )
                
                if trade_id:
                    logger.info(f"✅ [AUTONOMOUS] BUY {symbol} @ ${current_price:.2f} | Trade ID: {trade_id}")
                    await self._update_decision_status(decision_id, "EXECUTED", trade_id=trade_id)
                else:
                    await self._update_decision_status(decision_id, "FAILED", "Trade creation failed")
                    
            elif action == "SELL":
                # ====== ARCHITECTURE CHANGE: SELL handled by SLTPManager ======
                # AI Agent now ONLY handles BUY signals (entry decisions)
                # All exits (SL, TP, trailing, partial TP) are managed by SLTPManager
                # This prevents conflicts between AI and SLTPManager exit logic
                logger.info(f"⏭️ [AUTONOMOUS] SELL signal for {symbol} ignored - exits handled by SLTPManager")
                await self._update_decision_status(decision_id, "SKIPPED", "SELL delegated to SLTPManager")
                    
        except Exception as e:
            logger.error(f"❌ [AUTONOMOUS] Error executing {action} on {symbol}: {str(e)}")
            await self._update_decision_status(decision_id, "FAILED", str(e))

    async def _create_ai_trade(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        stop_loss: Optional[float],
        take_profit: Optional[float],
        position_amount: Optional[float],
        confidence: int,
        reasoning: str
    ) -> Optional[str]:
        """Create a trade initiated by AI Agent"""
        if not self.db_session_factory or not self.user_id:
            return None
        
        from app.models.database_models import Trade, Portfolio
        from uuid import UUID
        
        db = self.db_session_factory()
        try:
            # ===== BUG FIX #2: Validate SL and TP before trade creation =====
            # Check 1: SL should never equal Entry (would close immediately)
            if stop_loss and abs(stop_loss - entry_price) < 0.0001:
                logger.error(f"❌ [AI TRADE VALIDATION] SL={stop_loss} equals Entry={entry_price}! Rejecting trade.")
                return None
            
            # Check 2: SL should be below Entry for BUY orders
            if side == "BUY" and stop_loss and stop_loss >= entry_price:
                logger.error(f"❌ [AI TRADE VALIDATION] SL={stop_loss} not below Entry={entry_price} for BUY! Rejecting trade.")
                return None
            
            # Check 3: TP should be above Entry for BUY orders
            if side == "BUY" and take_profit and take_profit <= entry_price:
                logger.error(f"❌ [AI TRADE VALIDATION] TP={take_profit} not above Entry={entry_price} for BUY! Rejecting trade.")
                return None
            
            # Check 4: Verify Risk:Reward ratio is acceptable (min 1:1.5)
            if stop_loss and take_profit and side == "BUY":
                risk = entry_price - stop_loss
                reward = take_profit - entry_price
                if risk > 0:
                    rr_ratio = reward / risk
                    if rr_ratio < 1.0:
                        logger.warning(f"⚠️ [AI TRADE VALIDATION] Poor R:R ratio {rr_ratio:.2f} (min 1.0). Proceeding with caution.")
            
            # Get portfolio
            portfolio = db.query(Portfolio).filter(
                Portfolio.user_id == UUID(self.user_id)
            ).first()
            
            if not portfolio:
                logger.warning(f"❌ Portfolio not found for user {self.user_id}")
                return None
            
            # Calculate quantity
            cost = position_amount if position_amount else float(portfolio.cash_balance) * 0.05
            quantity = cost / entry_price
            
            # Log trade creation with full details
            logger.info(f"✅ [AI TRADE CREATE] {symbol} {side} | Entry: ${entry_price:.8f} | SL: ${stop_loss:.8f if stop_loss else 'None'} (offset: ${entry_price - stop_loss if stop_loss else 'N/A'}) | TP: ${take_profit:.8f if take_profit else 'None'} | Qty: {quantity:.8f} | Cost: ${cost:.2f}")
            
            # Deduct from cash balance
            portfolio.cash_balance = float(portfolio.cash_balance) - cost
            
            # Create trade
            trade = Trade(
                id=uuid_module.uuid4(),
                user_id=UUID(self.user_id),
                bot_id=None,  # AI Agent trades have no bot_id
                symbol=symbol,
                side=side,
                entry_price=entry_price,
                exit_price=None,
                quantity=quantity,
                pnl=None,
                pnl_percent=None,
                status="OPEN",
                entry_time=datetime.utcnow(),
                exit_time=None,
                strategy="AI_AGENT",  # Mark as AI trade
                stop_loss_price=stop_loss,
                take_profit_price=take_profit
            )
            
            db.add(trade)
            db.add(portfolio)
            db.commit()
            
            trade_id = str(trade.id)
            logger.info(f"🤖 Created AI trade: {symbol} {side} @ ${entry_price:.2f} | Qty: {quantity:.6f} | Cost: ${cost:.2f}")
            return trade_id
            
        except Exception as e:
            logger.error(f"Error creating AI trade: {str(e)}")
            db.rollback()
            return None
        finally:
            db.close()

    async def _close_ai_position(self, symbol: str, exit_price: float, confidence: int) -> bool:
        """Close an open AI Agent position"""
        if not self.db_session_factory or not self.user_id:
            return False
        
        from app.models.database_models import Trade, Portfolio
        from uuid import UUID
        
        db = self.db_session_factory()
        try:
            # Find open AI position (bot_id is None and strategy is AI_AGENT)
            open_trade = db.query(Trade).filter(
                Trade.user_id == UUID(self.user_id),
                Trade.symbol == symbol,
                Trade.status == "OPEN",
                Trade.strategy == "AI_AGENT"
            ).first()
            
            if not open_trade:
                return False
            
            # Calculate PnL
            entry_price = float(open_trade.entry_price)
            quantity = float(open_trade.quantity)
            
            if open_trade.side == "BUY":
                pnl = (exit_price - entry_price) * quantity
            else:
                pnl = (entry_price - exit_price) * quantity
            
            pnl_percent = (pnl / (entry_price * quantity)) * 100
            
            # Update trade
            open_trade.exit_price = exit_price
            open_trade.exit_time = datetime.utcnow()
            open_trade.status = "CLOSED"
            open_trade.pnl = pnl
            open_trade.pnl_percent = pnl_percent
            
            # Return funds to portfolio
            portfolio = db.query(Portfolio).filter(
                Portfolio.user_id == UUID(self.user_id)
            ).first()
            
            if portfolio:
                # Return original cost + PnL
                original_cost = entry_price * quantity
                portfolio.cash_balance = float(portfolio.cash_balance) + original_cost + pnl
            
            db.commit()
            
            pnl_emoji = "🟢" if pnl >= 0 else "🔴"
            logger.info(f"🤖 Closed AI position: {symbol} @ ${exit_price:.2f} | PnL: {pnl_emoji} ${pnl:.2f} ({pnl_percent:.2f}%)")
            return True
            
        except Exception as e:
            logger.error(f"Error closing AI position: {str(e)}")
            db.rollback()
            return False
        finally:
            db.close()

    async def _monitor_autonomous_positions(self):
        """
        Monitor all open AI_AGENT positions and close them if TP/SL is hit.
        This should be called periodically in the monitoring loop.
        """
        if not self.db_session_factory or not self.user_id:
            return
        
        from app.models.database_models import Trade
        from uuid import UUID
        from app.services.market_data import market_data_collector
        
        db = self.db_session_factory()
        try:
            # Get all open AI_AGENT positions for this user
            open_trades = db.query(Trade).filter(
                Trade.user_id == UUID(self.user_id),
                Trade.status == "OPEN",
                Trade.strategy == "AI_AGENT"
            ).all()
            
            if not open_trades:
                return
            
            logger.info(f"🔍 Monitoring {len(open_trades)} open AI_AGENT positions...")
            
            for trade in open_trades:
                try:
                    symbol = trade.symbol
                    
                    # Fetch current price using get_candles (like BotEngine does)
                    # This is more reliable than get_ticker()
                    candles = await market_data_collector.get_candles(symbol, timeframe="1m", limit=1)
                    if not candles or len(candles) == 0:
                        logger.warning(f"⚠️ Could not fetch price for {symbol} via get_candles")
                        continue
                    
                    current_price = candles[-1]['close']
                    entry_price = float(trade.entry_price)
                    sl = float(trade.stop_loss_price) if trade.stop_loss_price else None
                    tp = float(trade.take_profit_price) if trade.take_profit_price else None
                    
                    # Calculate unrealized PnL
                    pnl_pct = ((current_price - entry_price) / entry_price) * 100 if trade.side == "BUY" else ((entry_price - current_price) / entry_price) * 100
                    
                    logger.info(f"📊 [AI-MONITOR] {symbol}: Entry=${entry_price:.4f} | Current=${current_price:.4f} ({pnl_pct:+.2f}%) | SL=${sl} | TP=${tp}")
                    
                    # ===== BUG FIX: Detect misconfigured SL (SL > Entry for BUY) =====
                    if sl and trade.side == "BUY" and sl >= entry_price:
                        logger.error(f"🚨 [BUG DETECTED] {symbol}: SL (${sl:.4f}) >= Entry (${entry_price:.4f}) for BUY trade!")
                        # Auto-fix: Set SL to 3% below current price
                        new_sl = current_price * 0.97
                        trade.stop_loss_price = new_sl
                        db.commit()
                        logger.warning(f"🔧 [AUTO-FIX] {symbol}: SL corrected to ${new_sl:.4f} (3% below current)")
                        sl = new_sl
                    
                    # Check Stop Loss (for correctly configured trades)
                    if sl and trade.side == "BUY" and current_price <= sl:
                        logger.warning(f"🛑 Stop Loss HIT for {symbol} @ ${current_price:.4f} (SL: ${sl:.4f})")
                        await self._close_ai_position(symbol, current_price, confidence=100)
                        continue
                    
                    # Check Take Profit
                    if tp and trade.side == "BUY" and current_price >= tp:
                        logger.info(f"🎯 Take Profit HIT for {symbol} @ ${current_price:.4f} (TP: ${tp:.4f})")
                        await self._close_ai_position(symbol, current_price, confidence=100)
                        continue
                    
                except Exception as e:
                    logger.error(f"❌ Error monitoring {trade.symbol}: {str(e)}")
            
        except Exception as e:
            logger.error(f"❌ Error in _monitor_autonomous_positions: {str(e)}")
        finally:
            db.close()

    async def _update_decision_status(
        self,
        decision_id: Optional[str],
        status: str,
        reason: str = None,
        trade_id: str = None
    ):
        """Update AI decision status in database"""
        if not decision_id or not self.db_session_factory:
            return
        
        try:
            from app.models.database_models import AIDecision
            from uuid import UUID
            
            db = self.db_session_factory()
            try:
                decision = db.query(AIDecision).filter(
                    AIDecision.id == UUID(decision_id)
                ).first()
                
                if decision:
                    decision.executed = (status == "EXECUTED")
                    # Store status info in reasoning if needed
                    if reason:
                        decision.reasoning = f"{decision.reasoning} | Status: {status} - {reason}"
                    
                    db.commit()
                    logger.debug(f"📝 Updated decision {decision_id}: {status}")
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error updating decision status: {str(e)}")

    async def analyze_market(
        self,
        symbol: str,
        market_data: Optional[Dict[str, Any]] = None,
        indicators: Optional[Dict[str, Any]] = None,
        ml_prediction: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze a crypto market using DeepSeek with ML predictions context
        
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
            
            # Build analysis prompt with ML predictions
            prompt = self._build_analysis_prompt(symbol, market_data, indicators, ml_prediction)
            
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
            
            # === PHASE 2: Apply ML-weighted confidence calculation ===
            current_price = market_data.get("close", 0) if market_data else 0
            technical_confidence = analysis.get("confidence", 50)
            
            ml_weighting = self._calculate_ml_weighted_confidence(
                technical_confidence=technical_confidence,
                ml_prediction=ml_prediction,
                current_price=current_price,
                action=analysis.get("action", "HOLD")
            )
            
            # Update analysis with weighted confidence
            if ml_weighting["ml_available"]:
                analysis["confidence"] = ml_weighting["final_confidence"]
                analysis["ml_weighting"] = ml_weighting
                strategy = analysis.get("suggested_strategy", "none")
                risk_level = analysis.get("risk_level", "MEDIUM")
                logger.info(f"📊 {symbol} Analysis (ML-weighted): {analysis['action']} (technical: {technical_confidence}% → final: {ml_weighting['final_confidence']}%)")
                logger.info(f"   Components: Technical×0.60={ml_weighting['technical_component']}% + ML×0.30={ml_weighting['ml_component']}% + Alignment={ml_weighting['alignment_bonus']}%")
                logger.info(f"   Strategy: {strategy.upper()} | Risk: {risk_level}")
            else:
                strategy = analysis.get("suggested_strategy", "none")
                risk_level = analysis.get("risk_level", "MEDIUM")
                logger.info(f"📊 {symbol} Analysis: {analysis['action']} (confidence: {analysis.get('confidence', 0)}%)")
                logger.info(f"   Strategy: {strategy.upper()} | Risk: {risk_level}")
            
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
        indicators: Dict[str, Any],
        ml_prediction: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build ENRICHED analysis prompt for DeepSeek with advanced technical analysis + ML predictions"""
        
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

        # ============ TREND ANALYSIS ============
        trend = indicators.get('trend', {})
        if not isinstance(trend, dict):
            trend = {}
        trend_section = f"""## Overall Trend Summary
- Direction: {trend.get('direction', 'N/A').upper() if isinstance(trend.get('direction'), str) else 'N/A'}
- Strength: {trend.get('strength', 'N/A')}
- Momentum: {trend.get('momentum', 'N/A')}"""

        # ============ ML LSTM PREDICTIONS (PHASE 2) ============
        ml_section = ""
        if ml_prediction and isinstance(ml_prediction, dict):
            pred_1h = ml_prediction.get('pred_1h', 'N/A')
            pred_24h = ml_prediction.get('pred_24h', 'N/A')
            pred_7d = ml_prediction.get('pred_7d', 'N/A')
            conf_1h = ml_prediction.get('confidence_1h', 0)
            conf_24h = ml_prediction.get('confidence_24h', 0)
            conf_7d = ml_prediction.get('confidence_7d', 0)
            
            # Calculate ML signal
            ml_direction = "BULLISH" if pred_7d and pred_7d > current_price else "BEARISH" if pred_7d else "NEUTRAL"
            
            ml_section = f"""## LSTM Model Predictions (Machine Learning)
- 1h Forecast: ${pred_1h} (confidence: {conf_1h:.0%})
- 24h Forecast: ${pred_24h} (confidence: {conf_24h:.0%})
- 7d Forecast: ${pred_7d} (confidence: {conf_7d:.0%})
- ML Direction: {ml_direction} {'📈 Price target above current' if ml_direction == 'BULLISH' else '📉 Price target below current' if ml_direction == 'BEARISH' else ''}
- ML Confidence Average: {(conf_1h + conf_24h + conf_7d) / 3:.0%}

**IMPORTANT**: ML predictions provide machine learning insights from historical LSTM training.
- Include ML forecast in your reasoning if confidence > 60%
- Weight ML confidence alongside technical indicators
- High alignment between ML forecast and technical signals = VERY HIGH confidence trade"""

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

{ml_section}

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
  "suggested_strategy": "grid_trading|trend_following|mean_reversion|momentum|scalping|breakout|rsi_divergence|macd_crossover|dca",
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
- Machine Learning Integration (LSTM price predictions)
- Trading Strategy Selection

Your job is to analyze market data and provide ACTIONABLE trading recommendations with appropriate strategy selection.

*** PHASE 2: ML INTEGRATION WITH PRECISE WEIGHTING ***
You now have access to LSTM machine learning predictions alongside technical indicators.

CONFIDENCE WEIGHTING SYSTEM (Numeric):
The AI Agent uses this precise weighting formula:
  final_confidence = (technical × 0.60) + (ml × 0.30) + (alignment_bonus × 0.10)

WHERE:
- technical: Your technical analysis confidence (0-100%)
- ml: Average of 3 timeframe ML predictions (1h, 24h, 7d)
- alignment_bonus: +10% if ML and technicals agree, -5% if divergent

YOUR ROLE IN THIS SYSTEM:
1. Provide a clear TECHNICAL CONFIDENCE (0-100%) based purely on technical indicators
   - Don't adjust for ML yet - that's the backend's job
   - If 4+ technicals align: suggest 75-85% confidence
   - If 3 technicals align: suggest 60-75% confidence
   - If <2 technicals align: suggest HOLD or <50% confidence

2. When providing reasoning, CITE BOTH sources:
   - "Technical: RSI at 32 (oversold) + MACD bullish crossover (2 signals = 65%)"
   - "ML: 7d forecast $45,200 with 72% confidence"
   - "Combined: These signals align (both bullish) = likely 75-80% final confidence"

3. Trust the backend weighting - it will:
   - Never let ML dominate (capped at tech + 20%)
   - Always require technical foundation (60% weight)
   - Boost confidence when aligned, reduce when divergent

IMPORTANT GUIDELINES FOR THIS SYSTEM:
- ALWAYS provide a clear technical confidence score
- NEVER ignore technical signals just because ML says otherwise
- If ML confidence < 60%: Treat as informational only, prioritize technicals
- If technicals and ML diverge: Your final confidence should be in 40-65% range (cautious)
- If technicals and ML align: Your confidence can go to 80-95% (strong)

*** STRATEGY SELECTION: CHOOSE FROM PRE-CONFIGURED BOTS ***
Your role is to SELECT the most appropriate strategy for current market conditions.
CRITICAL RULES:
1. Strategy selection MUST align with your BUY/SELL/HOLD action!
2. Each strategy has STRICT criteria - match ALL requirements, not just one
3. Strategies are MUTUALLY EXCLUSIVE - check exclusion rules below
4. If multiple match = pick the one with HIGHEST priority

*** PRIORITY ORDER (when multiple strategies match) ***
BUY Priority: mean_reversion (1) > trend_following (2) > momentum (3) > rsi_divergence (4) > breakout (5) > dca (6)
SELL Priority: mean_reversion (1) > trend_following (2) > momentum (3) > rsi_divergence (4) > breakout (5)

*** FOR BUY SIGNALS ***
1. **mean_reversion** - For buying at oversold extremes [HIGHEST PRIORITY]
   - WHEN: RSI < 30 (oversold) = CRITICAL requirement
   - AND: Price near/touching lower Bollinger Band
   - AND: Price at support level with reversal signals
   - EXCLUDE IF: MACD bullish crossover (use trend_following instead)
   - EXCLUDE IF: Multi-timeframe trend already bullish (use trend_following instead)
   - ACTION: BUY | Risk: MEDIUM | Best for: Counter-trend entries from oversold

2. **trend_following** - For buying in bullish trends [2ND PRIORITY]
   - WHEN: Price clearly above SMA 50
   - AND: Multi-timeframe bullish alignment (2+ timeframes up)
   - AND: MACD bullish crossover with positive momentum
   - EXCLUDE IF: RSI < 30 (use mean_reversion instead)
   - ACTION: BUY | Risk: LOW | Best for: Following established bullish trends

3. **momentum** - For buying with acceleration signals [3RD PRIORITY]
   - WHEN: MACD histogram strongly POSITIVE and INCREASING
   - AND: High volume (ratio > 1.5x) confirming bullish move
   - AND: 3+ bullish signals aligned (RSI rising, MACD up, cloud bullish)
   - EXCLUDE IF: RSI < 30 or trend_following conditions (those have priority)
   - ACTION: BUY | Risk: HIGH | Best for: Fast-moving rallies with strong volume

4. **rsi_divergence** - For buying at reversal setups [4TH PRIORITY]
   - WHEN: RSI shows bullish divergence (price lower, RSI higher)
   - AND: RSI crossing above 30 from oversold zone
   - EXCLUDE IF: RSI < 30 already (use mean_reversion instead)
   - ACTION: BUY | Risk: MEDIUM | Best for: Reversal trades at inflection points

5. **breakout** - For buying above resistance [5TH PRIORITY]
   - WHEN: Price breaks above resistance with volume spike
   - AND: Volume ratio > 1.8x confirming breakout
   - AND: Clear consolidation pattern before break
   - ACTION: BUY | Risk: HIGH | Best for: Breakout entries above resistance

6. **dca** - For conservative accumulation [LOWEST PRIORITY]
   - WHEN: Long-term bullish outlook uncertain
   - WHEN: Want to average into position gradually
   - ACTION: BUY | Risk: LOW | Best for: Long-term positions with timing uncertainty

*** FOR SELL SIGNALS ***
1. **mean_reversion** - For selling at overbought extremes [HIGHEST PRIORITY]
   - WHEN: RSI > 70 (overbought) = CRITICAL requirement
   - AND: Price near/touching upper Bollinger Band
   - AND: Price at resistance level with reversal signals
   - EXCLUDE IF: MACD bearish crossover (use trend_following instead)
   - EXCLUDE IF: Multi-timeframe trend already bearish (use trend_following instead)
   - ACTION: SELL | Risk: MEDIUM | Best for: Counter-trend exits from overbought

2. **trend_following** - For selling in bearish trends [2ND PRIORITY]
   - WHEN: Price clearly below SMA 50
   - AND: Multi-timeframe bearish alignment (2+ timeframes down)
   - AND: MACD bearish crossover with negative momentum
   - EXCLUDE IF: RSI > 70 (use mean_reversion instead)
   - ACTION: SELL | Risk: LOW | Best for: Following established bearish trends

3. **momentum** - For selling with downward acceleration [3RD PRIORITY]
   - WHEN: MACD histogram strongly NEGATIVE and DECREASING
   - AND: High volume (ratio > 1.5x) confirming bearish move
   - AND: 3+ bearish signals aligned (RSI falling, MACD down, cloud bearish)
   - EXCLUDE IF: RSI > 70 or trend_following conditions (those have priority)
   - ACTION: SELL | Risk: HIGH | Best for: Fast-moving declines with strong volume

4. **rsi_divergence** - For selling at reversal setups [4TH PRIORITY]
   - WHEN: RSI shows bearish divergence (price higher, RSI lower)
   - AND: RSI crossing below 70 from overbought zone
   - EXCLUDE IF: RSI > 70 already (use mean_reversion instead)
   - ACTION: SELL | Risk: MEDIUM | Best for: Reversal trades at inflection points

5. **breakout** - For selling below support [5TH PRIORITY]
   - WHEN: Price breaks below support with volume spike
   - AND: Volume ratio > 1.8x confirming breakdown
   - AND: Clear consolidation pattern before break
   - ACTION: SELL | Risk: HIGH | Best for: Breakdown entries below support

*** FOR HOLD SIGNALS ***
6. **grid_trading** - For holding in sideways choppy markets
   - WHEN: No clear trend (conflicting multi-timeframe signals)
   - WHEN: Price oscillating between support/resistance without directional breakout
   - WHEN: High volatility but no clear direction
   - ACTION: HOLD | Risk: MEDIUM | Best for: Range-bound consolidation

7. **macd_crossover** - For waiting on MACD confirmation
   - WHEN: Signals conflict or unclear
   - WHEN: Price at critical level but MACD not confirmed
   - ACTION: HOLD | Risk: MEDIUM | Best for: Waiting for confirmation

*** HOW TO SELECT STRATEGY (STEP-BY-STEP) ***

STEP 1: Determine ACTION (BUY/SELL/HOLD)
   - Count bullish signals: RSI < 30, MACD bullish, Price above SMA50, Cloud bullish, Elliott up
   - Count bearish signals: RSI > 70, MACD bearish, Price below SMA50, Cloud bearish, Elliott down
   - BUY: If 2+ bullish signals AND no 3+ bearish signals
   - SELL: If 2+ bearish signals AND no 3+ bullish signals  
   - HOLD: If signals conflict (e.g., 2 bullish + 2 bearish)

STEP 2: SELECT STRATEGY (check EXCLUSIONS first!)
   - Read each strategy's WHEN and EXCLUDE criteria
   - EXCLUDE filters prevent wrong strategy selection (e.g., trend_following won't match RSI < 30)
   - Match ALL "WHEN" requirements, not just one
   - If multiple strategies match = use PRIORITY ORDER (1=highest)

STRATEGY DECISION FLOWCHART FOR SELL:
   └─ RSI > 70? YES → mean_reversion (highest priority, stop here)
   └─ RSI > 70? NO → Check trend_following
      └─ Price below SMA50 + Multi-timeframe bearish? YES → trend_following
      └─ NO → Check momentum
         └─ MACD histogram negative + High volume? YES → momentum
         └─ NO → Check rsi_divergence or breakout or HOLD

STRATEGY DECISION FLOWCHART FOR BUY:
   └─ RSI < 30? YES → mean_reversion (highest priority, stop here)
   └─ RSI < 30? NO → Check trend_following
      └─ Price above SMA50 + Multi-timeframe bullish? YES → trend_following
      └─ NO → Check momentum
         └─ MACD histogram positive + High volume? YES → momentum
         └─ NO → Check rsi_divergence or breakout or HOLD

STEP 3: VERIFY EXCLUSION RULES (CRITICAL!)
   Examples of WRONG selections to AVOID:
   ❌ mean_reversion SELL when RSI = 41 (not overbought) → use trend_following instead
   ❌ mean_reversion BUY when RSI = 65 (not oversold) → use trend_following instead
   ❌ momentum when MACD histogram negative (bearish, not bullish)
   ❌ trend_following when RSI < 30 with no trend yet → use mean_reversion instead

STEP 4: Suggest target_price and stop_loss based on technical levels

CONFIDENCE CALCULATION:
- 4+ aligned signals = 75-90% confidence
- 3 aligned signals = 60-75% confidence
- 2 aligned signals = 50-65% confidence (TAKE ACTION if aligned)
- <2 aligned signals = HOLD or <50% confidence
- Add +10% if volume confirms
- Add +10% if multi-timeframe alignment

FINAL VALIDATION (before JSON response):
   1. Does strategy match action? (SELL + mean_reversion requires RSI > 70, not RSI 41!)
   2. Does reasoning cite the strategy's WHEN criteria?
   3. Are target/SL consistent with action? (SELL should have target below entry, SL above)
   4. Is confidence score justified by signal count?
   
   If ANY fails = RECONSIDER strategy selection
- Use SPECIFIC numbers in reasoning ("RSI at 28", "MACD 0.023 crossed above signal")
- Never create custom rules - just SELECT from predefined strategies

*** ML INTEGRATION CRITICAL RULES ***
If ML prediction is available:
   - ML confidence > 60% + aligns with technicals: Consider +10% confidence boost
   - ML confidence > 60% + contradicts technicals: HOLD or reduce confidence
   - ML confidence 40-60%: Use for confirmation of technical signals
   - ML confidence < 40%: Ignore ML, focus purely on technicals
    - All signals (technical + ML) aligned bullish/bearish: 80-95%
    - Technical signals strong + ML supports: 70-85%
    - Technical shows 2+ signals + ML weak: 55-70% (STILL TAKE ACTION)
    - Any major divergence: 40-55% (Can still trade if only 1 conflict)
11. **MINIMUM CONFIDENCE FOR ACTION**: 40% minimum to recommend BUY/SELL (backend will filter to 40%+)

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
                    content = data["choices"][0]["message"]["content"]
                    
                    # === DEBUG: Log full response to understand bot creation ===
                    logger.info(f"🤖 [DEEPSEEK-FULL] Response (first 800 chars):\n{content[:800]}")
                    logger.info(f"🤖 [DEEPSEEK-FIELDS] Contains suggested_strategy: {'suggested_strategy' in content}")
                    logger.debug(f"🤖 [DEEPSEEK-FIELDS] Contains risk_level: {'risk_level' in content}")
                    logger.debug(f"🤖 [DEEPSEEK-FIELDS] Contains signals_summary: {'signals_summary' in content}")
                    
                    return content
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
            
            # === DEBUG: Log what we parsed ===
            logger.info(f"🤖 [PARSED-ANALYSIS] Keys in JSON: {list(analysis.keys())}")
            logger.info(f"🤖 [PARSED-FIELDS] suggested_strategy: {analysis.get('suggested_strategy', 'MISSING')}")
            logger.info(f"🤖 [PARSED-FIELDS] risk_level: {analysis.get('risk_level', 'MISSING')}")
            logger.info(f"🤖 [PARSED-FIELDS] timeframe: {analysis.get('timeframe', 'MISSING')}")
            logger.debug(f"🤖 [PARSED-FIELDS] action: {analysis.get('action')}, confidence: {analysis.get('confidence')}")
            
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
    
    async def _store_decision_sync_duplicate_removed(self, analysis: Dict[str, Any]):
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

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
                                
                                if action in ["BUY", "SELL"] and confidence >= self.min_confidence_to_log:
                                    logger.info(f"💡 {symbol}: {action} signal (confidence: {confidence}%)")
                                    
                                    # Store decision in DB (for observation mode)
                                    if self.mode == "observation":
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
        """Fetch market data using MarketDataCollector"""
        try:
            from app.services.market_data import market_data_collector
            from app.services.technical_analysis import TechnicalAnalysis
            
            # Ensure symbol format
            binance_symbol = symbol if symbol.endswith("USDT") else f"{symbol}USDT"
            
            # Get candles
            candles = await market_data_collector.get_candles(binance_symbol, timeframe="1h", limit=100)
            
            if not candles or len(candles) < 20:
                return None
            
            # Calculate indicators
            ta = TechnicalAnalysis()
            closes = [c['close'] for c in candles]
            highs = [c['high'] for c in candles]
            lows = [c['low'] for c in candles]
            
            sma_20 = ta.calculate_sma(closes, 20)
            sma_50 = ta.calculate_sma(closes, 50)
            rsi = ta.calculate_rsi(closes, 14)
            bb_upper, bb_middle, bb_lower = ta.calculate_bollinger_bands(closes, 20, 2)
            
            current = candles[-1]
            
            return {
                "symbol": binance_symbol,
                "close": current['close'],
                "high": current['high'],
                "low": current['low'],
                "volume": current['volume'],
                "change_24h": 0,  # Simplified
                "indicators": {
                    "rsi": round(rsi[-1], 2) if rsi and rsi[-1] else None,
                    "sma_20": round(sma_20[-1], 2) if sma_20 and sma_20[-1] else None,
                    "sma_50": round(sma_50[-1], 2) if sma_50 and sma_50[-1] else None,
                    "bb_upper": round(bb_upper[-1], 2) if bb_upper and bb_upper[-1] else None,
                    "bb_middle": round(bb_middle[-1], 2) if bb_middle and bb_middle[-1] else None,
                    "bb_lower": round(bb_lower[-1], 2) if bb_lower and bb_lower[-1] else None,
                    "resistance": max(highs[-20:]),
                    "support": min(lows[-20:])
                }
            }
        except Exception as e:
            logger.error(f"Error fetching market data for {symbol}: {str(e)}")
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
        market_data: Dict[str, Any],
        indicators: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze a crypto market using DeepSeek
        
        Args:
            symbol: Trading pair (e.g., BTCUSDT)
            market_data: Current price data
            indicators: Technical indicators
            
        Returns:
            Analysis with recommendation, confidence, and reasoning
        """
        try:
            # Build analysis prompt
            prompt = self._build_analysis_prompt(symbol, market_data, indicators)
            
            # Call DeepSeek API
            response = await self._call_deepseek(prompt)
            
            if not response:
                return {
                    "symbol": symbol,
                    "action": "NONE",
                    "confidence": 0,
                    "reasoning": "Failed to analyze market"
                }
            
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
                analysis = await self.analyze_market(
                    symbol,
                    market_data[symbol].get("price_data", {}),
                    market_data[symbol].get("indicators", {})
                )
                
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
        """Build analysis prompt for DeepSeek"""
        current_price = market_data.get("close", 0)
        
        return f"""Analyze this crypto trading opportunity and provide a trading recommendation.

## Market Data for {symbol}
- Current Price: ${current_price}
- 24h Change: {market_data.get('change_24h', 0)}%
- Volume: {market_data.get('volume', 0)}
- High: ${market_data.get('high', 0)}
- Low: ${market_data.get('low', 0)}

## Technical Indicators
- RSI (14): {indicators.get('rsi', 'N/A')}
- SMA 20: {indicators.get('sma_20', 'N/A')}
- SMA 50: {indicators.get('sma_50', 'N/A')}
- BB Upper: {indicators.get('bb_upper', 'N/A')}
- BB Middle: {indicators.get('bb_middle', 'N/A')}
- BB Lower: {indicators.get('bb_lower', 'N/A')}
- Support: {indicators.get('support', 'N/A')}
- Resistance: {indicators.get('resistance', 'N/A')}

## Your Analysis Task
Based on the above data, provide:
1. **Recommendation**: BUY, SELL, or HOLD
2. **Confidence**: 0-100% confidence level
3. **Reasoning**: 2-3 sentences explaining your analysis
4. **Risk Level**: LOW, MEDIUM, or HIGH
5. **Target**: Expected price target if trading
6. **Stop Loss**: Suggested stop loss level

Format your response as JSON:
{{
  "action": "BUY|SELL|HOLD",
  "confidence": <0-100>,
  "reasoning": "<your explanation>",
  "risk_level": "LOW|MEDIUM|HIGH",
  "target_price": <number or null>,
  "stop_loss": <number or null>,
  "timeframe": "1h|4h|1d"
}}

Remember:
- Be conservative with confidence levels
- Only recommend BUY/SELL if you're > 60% confident
- Consider risk-reward ratio
- Account for market volatility"""
    
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
                                "content": "You are an expert crypto trading analyst. Provide precise, data-driven recommendations."
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": 0.3,  # Lower temp for consistency
                        "max_tokens": 500
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
                json_str = response.split("```")[1].split("```")[0]
            
            analysis = json.loads(json_str.strip())
            
            # Validate required fields
            if "action" not in analysis:
                analysis["action"] = "NONE"
            if "confidence" not in analysis:
                analysis["confidence"] = 0
            if "reasoning" not in analysis:
                analysis["reasoning"] = "No reasoning provided"
            
            return analysis
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse DeepSeek response: {str(e)}")
            return {
                "action": "NONE",
                "confidence": 0,
                "reasoning": "Failed to parse response"
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


def initialize_ai_agent(api_key: str, model: str = "deepseek-chat", db_session_factory=None):
    """Initialize global AI agent instance"""
    global ai_agent
    ai_agent = AITradingAgent(api_key, model, db_session_factory)
    return ai_agent


def get_ai_agent() -> Optional[AITradingAgent]:
    """Get global AI agent instance"""
    return ai_agent

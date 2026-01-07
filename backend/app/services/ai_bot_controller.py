"""
AI Bot Controller
Manages bots based on AI Agent decisions
Creates, starts, stops, and adjusts bots automatically
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, DBAPIError
from app.models.database_models import Bot, Trade, Portfolio, AIDecision
from app.services.ai_agent import ai_agent, AITradingAgent
import uuid
import json
import time

logger = logging.getLogger(__name__)


class AIBotController:
    """
    Controls trading bots based on AI Agent recommendations.
    Can create new bots, adjust existing bots, and stop underperforming bots.
    """
    
    def __init__(self, db_session_factory, bot_engine=None):
        """
        Initialize AI Bot Controller
        
        Args:
            db_session_factory: Factory for database sessions
            bot_engine: Reference to BotEngine for bot operations
        """
        self.db_session_factory = db_session_factory
        self.bot_engine = bot_engine
        self.enabled = False
        self.mode = "observation"  # observation, paper, live
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
        # ============================================
        # CONFIGURATION - All values are configurable
        # ============================================
        self.config = {
            # === Trading Limits ===
            "max_daily_trades": 50,           # Max trades per day (50 = ~2/hour for 24h)
            "max_active_bots": 10,            # Max concurrent AI bots
            "max_trades_per_hour": 5,         # Rate limit per hour
            
            # === Risk Management ===
            "default_risk_percent": 1.0,      # Risk per trade (1% = conservative)
            "max_risk_percent": 2.0,          # Maximum allowed risk per trade
            "max_portfolio_risk": 10.0,       # Max % of portfolio at risk across all bots
            "default_stop_loss_percent": 1.5, # Default stop loss (1.5%)
            "max_stop_loss_percent": 3.0,     # Maximum allowed stop loss
            
            # === AI Settings ===
            "min_confidence": 65,             # Minimum AI confidence to act (65-80 recommended)
            "check_interval": 300,            # Analysis interval in seconds (5 min)
            "cooldown_minutes": 30,           # Minutes between analyses
            
            # === Safety ===
            "cooldown_after_loss": 900,       # 15 min cooldown after significant loss
            "loss_threshold_for_cooldown": 3.0,  # % loss to trigger cooldown
            "default_paper_trading": True,    # Always start in paper trading
            
            # === CRITICAL SAFETY: Anti-Futures/Leverage ===
            "allow_futures": False,           # ❌ NEVER allow futures trading
            "allow_margin": False,            # ❌ NEVER allow margin trading  
            "allow_leverage": False,          # ❌ NEVER allow leveraged positions
            "max_leverage": 1.0,              # 1x = spot only, no leverage
            "allowed_market_types": ["spot"], # Only spot trading allowed
            
            # === Allowed Trading Pairs ===
            "allowed_quote_currencies": ["USDT", "USDC", "BUSD"],  # Stablecoins only
            "blocked_symbols": [],            # Blacklist specific symbols
            "watchlist_symbols": ["BTC/USDT", "ETH/USDT"],  # Symbols to analyze
        }
        
        # State tracking
        self.ai_bots: Dict[str, Dict[str, Any]] = {}  # Bots created by AI
        self.pending_recommendations: List[Dict[str, Any]] = []
        self.daily_trades = 0
        self.last_trade_date = None
        self.cooldown_until = None
    
    async def start(self):
        """Start the AI Bot Controller"""
        if self._running:
            logger.warning("⚠️ AI Bot Controller already running")
            return
        
        if not ai_agent:
            logger.error("❌ AI Agent not initialized, cannot start AI Bot Controller")
            return
        
        self._running = True
        logger.info(f"🤖 AI Bot Controller started (mode: {self.mode})")
        
        # Load existing AI-created bots
        await self._load_ai_bots()
        
        # Start control loop
        self._task = asyncio.create_task(self._control_loop())
    
    async def stop(self):
        """Stop the AI Bot Controller"""
        self._running = False
        logger.info("🛑 Stopping AI Bot Controller...")
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("✅ AI Bot Controller stopped")
    
    async def _load_ai_bots(self):
        """Load AI-created bots from database"""
        db = self.db_session_factory()
        try:
            # Find bots with AI tag in name or metadata
            bots = db.query(Bot).filter(Bot.name.like("AI-%")).all()
            
            for bot in bots:
                self.ai_bots[str(bot.id)] = {
                    "bot_id": str(bot.id),
                    "name": bot.name,
                    "symbol": bot.symbols[0] if bot.symbols else None,
                    "created_at": bot.created_at,
                    "status": bot.status,
                    "trades_count": 0,
                    "profit_loss": 0.0
                }
            
            logger.info(f"📊 Loaded {len(self.ai_bots)} AI-managed bots")
        except Exception as e:
            logger.error(f"❌ Error loading AI bots: {str(e)}")
        finally:
            db.close()
    
    async def _control_loop(self):
        """Main control loop - monitors AI recommendations and manages bots"""
        logger.info("🔄 AI Bot Controller loop started")
        
        while self._running:
            try:
                # Reset daily counter if new day
                self._check_daily_reset()
                
                # Skip if in cooldown
                if self.cooldown_until and datetime.utcnow() < self.cooldown_until:
                    await asyncio.sleep(60)
                    continue
                
                # Get AI recommendations
                if ai_agent and ai_agent.enabled:
                    recommendations = await self._get_ai_recommendations()
                    
                    # Process high-confidence recommendations
                    for rec in recommendations:
                        if rec.get("confidence", 0) >= self.config["min_confidence"]:
                            await self._process_recommendation(rec)
                
                # Monitor existing AI bots performance
                await self._monitor_ai_bots()
                
                # Wait before next check
                await asyncio.sleep(self.config["check_interval"])
                
            except Exception as e:
                logger.error(f"❌ Error in AI Bot Controller loop: {str(e)}")
                await asyncio.sleep(30)
    
    def _check_daily_reset(self):
        """Reset daily trade counter if new day"""
        today = datetime.utcnow().date()
        if self.last_trade_date != today:
            self.daily_trades = 0
            self.last_trade_date = today
            logger.info("📅 Daily trade counter reset")
    
    async def _get_ai_recommendations(self) -> List[Dict[str, Any]]:
        """Get current recommendations from AI Agent"""
        # Get top symbols to analyze
        symbols = await self._get_watchlist_symbols()
        
        if not symbols:
            return []
        
        # Get market data for symbols
        market_data = await self._fetch_market_data(symbols)
        
        # Get AI recommendations
        recommendations = await ai_agent.get_recommendations(symbols, market_data)
        
        return recommendations
    
    async def _get_watchlist_symbols(self) -> List[str]:
        """Get symbols from user watchlist + top market"""
        # Default watchlist - top cryptos by volume
        default_watchlist = [
            "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
            "ADAUSDT", "AVAXUSDT", "DOGEUSDT", "DOTUSDT", "LINKUSDT"
        ]
        
        # TODO: Load user watchlist from database
        # TODO: Add AI-suggested symbols
        
        return default_watchlist
    
    async def _fetch_market_data(self, symbols: List[str]) -> Dict[str, Any]:
        """Fetch market data for symbols"""
        from app.services.market_data import MarketDataCollector
        from app.services.technical_analysis import TechnicalAnalysis
        
        market_collector = MarketDataCollector()
        ta = TechnicalAnalysis()
        
        market_data = {}
        
        for symbol in symbols:
            try:
                # Get OHLCV data
                ohlcv = await market_collector.get_ohlcv(symbol, "1h", limit=100)
                
                if not ohlcv:
                    continue
                
                # Calculate indicators
                indicators = ta.calculate_all(ohlcv)
                
                # Get latest price
                latest = ohlcv[-1] if ohlcv else {}
                
                market_data[symbol] = {
                    "price_data": {
                        "open": latest.get("open", 0),
                        "high": latest.get("high", 0),
                        "low": latest.get("low", 0),
                        "close": latest.get("close", 0),
                        "volume": latest.get("volume", 0),
                        "change_24h": self._calculate_24h_change(ohlcv)
                    },
                    "indicators": indicators
                }
            except Exception as e:
                logger.error(f"❌ Error fetching data for {symbol}: {str(e)}")
        
        return market_data
    
    def _calculate_24h_change(self, ohlcv: List[Dict]) -> float:
        """Calculate 24h price change percentage"""
        if len(ohlcv) < 24:
            return 0.0
        
        price_24h_ago = ohlcv[-24].get("close", 0)
        current_price = ohlcv[-1].get("close", 0)
        
        if price_24h_ago == 0:
            return 0.0
        
        return ((current_price - price_24h_ago) / price_24h_ago) * 100
    
    async def _process_recommendation(self, recommendation: Dict[str, Any]):
        """Process an AI recommendation and take action"""
        symbol = recommendation.get("symbol")
        action = recommendation.get("action")
        confidence = recommendation.get("confidence", 0)
        
        logger.info(f"📊 Processing AI recommendation: {action} {symbol} (confidence: {confidence}%)")
        
        if self.mode == "observation":
            # Log only, don't execute
            logger.info(f"👁️ [OBSERVATION] Would {action} {symbol}")
            self._log_decision(recommendation, executed=False)
            return
        
        # === SECURITY VALIDATIONS ===
        
        # 1. Validate trade safety (spot only, no futures)
        trade_type = recommendation.get("market_type", "spot")
        safety_check = self._validate_trade_safety(symbol, trade_type)
        if not safety_check["valid"]:
            logger.error(f"🚫 Trade blocked: {safety_check['reason']}")
            self._log_decision(recommendation, executed=False, blocked_reason=safety_check["reason"])
            return
        
        # 2. Check rate limits
        rate_check = self._check_rate_limits()
        if not rate_check["can_trade"]:
            logger.warning(f"⚠️ Rate limit: {rate_check['reason']}")
            return
        
        # 3. Validate and clamp risk parameters
        risk_params = self._validate_risk_parameters(
            risk_percent=recommendation.get("risk_percent", self.config["default_risk_percent"]),
            stop_loss_percent=recommendation.get("stop_loss_percent", self.config["default_stop_loss_percent"]),
            leverage=recommendation.get("leverage", 1.0)
        )
        
        for warning in risk_params.get("warnings", []):
            logger.warning(warning)
        
        # Update recommendation with validated values
        recommendation["risk_percent"] = risk_params["risk_percent"]
        recommendation["stop_loss_percent"] = risk_params["stop_loss_percent"]
        recommendation["leverage"] = risk_params["leverage"]  # Should always be 1.0
        
        # Execute based on action
        if action == "BUY":
            await self._create_ai_bot(symbol, recommendation)
        elif action == "SELL":
            await self._close_ai_bot(symbol, recommendation)
        elif action == "HOLD":
            # Adjust existing bot if any
            await self._adjust_ai_bot(symbol, recommendation)
    
    async def _create_ai_bot(self, symbol: str, recommendation: Dict[str, Any]):
        """Create a new bot based on AI recommendation"""
        db = self.db_session_factory()
        
        try:
            # === FINAL SAFETY CHECK: Spot only ===
            if recommendation.get("leverage", 1.0) > 1.0:
                logger.error("🚫 BLOCKED: Attempted to create bot with leverage > 1x")
                return
            
            # Generate unique bot name
            bot_name = f"AI-{symbol}-{datetime.utcnow().strftime('%Y%m%d%H%M')}"
            
            # Determine strategy based on recommendation
            strategy = self._select_strategy(recommendation)
            
            # Build bot configuration
            config = {
                "ai_created": True,
                "ai_recommendation": recommendation,
                "entry_price": recommendation.get("entry_price"),
                "target_price": recommendation.get("target_price"),
                "stop_loss": recommendation.get("stop_loss"),
                "stop_loss_percent": recommendation.get("stop_loss_percent", self.config["default_stop_loss_percent"]),
                "timeframe": recommendation.get("timeframe", "1h"),
                "market_type": "spot",  # ALWAYS spot
                "leverage": 1.0,  # ALWAYS 1x
            }
            
            # Create bot record
            new_bot = Bot(
                id=uuid.uuid4(),
                user_id=self._get_ai_user_id(),  # System AI user
                name=bot_name,
                strategy=strategy,
                symbols=[symbol],
                paper_trading=self.config["default_paper_trading"] or self.mode == "paper",
                status="IDLE",
                risk_percent=self.config["default_risk_percent"],
                config=json.dumps(config)
            )
            
            db.add(new_bot)
            db.commit()
            
            bot_id = str(new_bot.id)
            
            # Track AI bot
            self.ai_bots[bot_id] = {
                "bot_id": bot_id,
                "name": bot_name,
                "symbol": symbol,
                "created_at": datetime.utcnow(),
                "status": "IDLE",
                "recommendation": recommendation
            }
            
            logger.info(f"🤖 Created AI bot: {bot_name}")
            
            # Auto-start if in trading mode
            if self.mode in ["paper", "live"] and self.bot_engine:
                await self.bot_engine.activate_bot(bot_id)
                self.ai_bots[bot_id]["status"] = "RUNNING"
                self.daily_trades += 1
                logger.info(f"▶️ Started AI bot: {bot_name}")
            
            # Log decision
            self._log_decision(recommendation, executed=True, bot_id=bot_id)
            
        except Exception as e:
            logger.error(f"❌ Error creating AI bot: {str(e)}")
            db.rollback()
        finally:
            db.close()
    
    async def _close_ai_bot(self, symbol: str, recommendation: Dict[str, Any]):
        """Close/stop a bot for a symbol"""
        # Find AI bot for this symbol
        bot_id = None
        for bid, bot_info in self.ai_bots.items():
            if bot_info.get("symbol") == symbol and bot_info.get("status") == "RUNNING":
                bot_id = bid
                break
        
        if not bot_id:
            logger.info(f"ℹ️ No active AI bot found for {symbol} to close")
            return
        
        # Stop the bot
        if self.bot_engine:
            await self.bot_engine.deactivate_bot(bot_id)
        
        # Update tracking
        if bot_id in self.ai_bots:
            self.ai_bots[bot_id]["status"] = "STOPPED"
            self.ai_bots[bot_id]["close_recommendation"] = recommendation
        
        logger.info(f"🛑 Closed AI bot for {symbol}")
        
        # Log decision
        self._log_decision(recommendation, executed=True, bot_id=bot_id)
    
    async def _adjust_ai_bot(self, symbol: str, recommendation: Dict[str, Any]):
        """Adjust an existing bot based on new AI recommendation"""
        # Find AI bot for this symbol
        bot_id = None
        for bid, bot_info in self.ai_bots.items():
            if bot_info.get("symbol") == symbol and bot_info.get("status") == "RUNNING":
                bot_id = bid
                break
        
        if not bot_id:
            return
        
        db = self.db_session_factory()
        try:
            bot = db.query(Bot).filter(Bot.id == bot_id).first()
            if bot:
                # Update config with new targets
                config = json.loads(bot.config) if isinstance(bot.config, str) else bot.config or {}
                config["target_price"] = recommendation.get("target_price")
                config["stop_loss"] = recommendation.get("stop_loss")
                config["last_ai_update"] = datetime.utcnow().isoformat()
                
                bot.config = json.dumps(config)
                db.commit()
                
                logger.info(f"🔄 Adjusted AI bot {bot.name}: new target={recommendation.get('target_price')}")
        except Exception as e:
            logger.error(f"❌ Error adjusting AI bot: {str(e)}")
        finally:
            db.close()
    
    async def _monitor_ai_bots(self):
        """Monitor performance of AI-created bots"""
        db = self.db_session_factory()
        try:
            for bot_id, bot_info in list(self.ai_bots.items()):
                if bot_info.get("status") != "RUNNING":
                    continue
                
                # Get bot performance
                bot = db.query(Bot).filter(Bot.id == bot_id).first()
                if not bot:
                    continue
                
                # Calculate P&L from trades
                trades = db.query(Trade).filter(
                    Trade.bot_id == bot_id,
                    Trade.status == "CLOSED"
                ).all()
                
                total_pnl = sum(float(t.pnl or 0) for t in trades)
                win_count = sum(1 for t in trades if float(t.pnl or 0) > 0)
                loss_count = sum(1 for t in trades if float(t.pnl or 0) <= 0)
                
                # Update tracking
                bot_info["total_pnl"] = total_pnl
                bot_info["win_rate"] = (win_count / len(trades) * 100) if trades else 0
                bot_info["trades_count"] = len(trades)
                
                # Auto-stop losing bots
                if total_pnl < -5.0:  # More than 5% loss
                    logger.warning(f"⚠️ AI bot {bot_info['name']} has lost {total_pnl}%, stopping")
                    await self._close_ai_bot(bot_info["symbol"], {
                        "action": "SELL",
                        "reason": "Auto-stopped due to excessive loss",
                        "pnl": total_pnl
                    })
                    
                    # Enter cooldown
                    self.cooldown_until = datetime.utcnow() + timedelta(
                        seconds=self.config["cooldown_after_loss"]
                    )
        
        except Exception as e:
            logger.error(f"❌ Error monitoring AI bots: {str(e)}")
        finally:
            db.close()
    
    def _select_strategy(self, recommendation: Dict[str, Any]) -> str:
        """Select appropriate strategy based on AI recommendation"""
        risk_level = recommendation.get("risk_level", "MEDIUM")
        timeframe = recommendation.get("timeframe", "1h")
        
        # Strategy selection logic
        if timeframe in ["5m", "15m"]:
            return "scalping"
        elif risk_level == "LOW":
            return "trend_following"
        elif risk_level == "HIGH":
            return "momentum"
        else:
            return "mean_reversion"
    
    # ============================================
    # SECURITY VALIDATIONS
    # ============================================
    
    def _validate_trade_safety(self, symbol: str, trade_type: str = "spot") -> Dict[str, Any]:
        """
        Validate a trade against all safety rules
        
        Args:
            symbol: Trading pair (e.g., BTCUSDT)
            trade_type: Type of trade (spot, futures, margin)
            
        Returns:
            Dict with 'valid' bool and 'reason' if invalid
        """
        # === CRITICAL: Block futures and margin ===
        if trade_type.lower() in ["futures", "future", "perp", "perpetual"]:
            if not self.config.get("allow_futures", False):
                return {
                    "valid": False,
                    "reason": "🚫 FUTURES TRADING IS DISABLED - Spot trading only"
                }
        
        if trade_type.lower() in ["margin", "leveraged"]:
            if not self.config.get("allow_margin", False):
                return {
                    "valid": False,
                    "reason": "🚫 MARGIN TRADING IS DISABLED - Spot trading only"
                }
        
        # Check market type whitelist
        allowed_types = self.config.get("allowed_market_types", ["spot"])
        if trade_type.lower() not in allowed_types:
            return {
                "valid": False,
                "reason": f"🚫 Market type '{trade_type}' not allowed. Allowed: {allowed_types}"
            }
        
        # === Check blocked symbols ===
        blocked = self.config.get("blocked_symbols", [])
        if symbol.upper() in [s.upper() for s in blocked]:
            return {
                "valid": False,
                "reason": f"🚫 Symbol {symbol} is blocked"
            }
        
        # === Check quote currency ===
        allowed_quotes = self.config.get("allowed_quote_currencies", ["USDT", "USDC", "BUSD"])
        symbol_upper = symbol.upper()
        valid_quote = any(symbol_upper.endswith(q) for q in allowed_quotes)
        
        if not valid_quote:
            return {
                "valid": False,
                "reason": f"🚫 Symbol {symbol} doesn't use allowed quote currency. Allowed: {allowed_quotes}"
            }
        
        return {"valid": True}
    
    def _validate_risk_parameters(
        self,
        risk_percent: float,
        stop_loss_percent: float,
        leverage: float = 1.0
    ) -> Dict[str, Any]:
        """
        Validate risk parameters against safety limits
        
        Args:
            risk_percent: Risk per trade as percentage
            stop_loss_percent: Stop loss as percentage
            leverage: Leverage multiplier (1.0 = no leverage)
            
        Returns:
            Dict with validated values (clamped to limits) and warnings
        """
        warnings = []
        
        # === CRITICAL: Block leverage ===
        max_leverage = self.config.get("max_leverage", 1.0)
        if leverage > max_leverage:
            warnings.append(f"⚠️ Leverage {leverage}x reduced to {max_leverage}x (max allowed)")
            leverage = max_leverage
        
        if leverage > 1.0 and not self.config.get("allow_leverage", False):
            warnings.append("⚠️ Leverage disabled, forcing 1x (spot)")
            leverage = 1.0
        
        # === Clamp risk percent ===
        max_risk = self.config.get("max_risk_percent", 2.0)
        if risk_percent > max_risk:
            warnings.append(f"⚠️ Risk {risk_percent}% reduced to {max_risk}% (max allowed)")
            risk_percent = max_risk
        
        if risk_percent < 0.1:
            warnings.append(f"⚠️ Risk {risk_percent}% increased to 0.1% (minimum)")
            risk_percent = 0.1
        
        # === Clamp stop loss ===
        max_sl = self.config.get("max_stop_loss_percent", 3.0)
        if stop_loss_percent > max_sl:
            warnings.append(f"⚠️ Stop loss {stop_loss_percent}% reduced to {max_sl}% (max allowed)")
            stop_loss_percent = max_sl
        
        if stop_loss_percent < 0.5:
            warnings.append(f"⚠️ Stop loss {stop_loss_percent}% increased to 0.5% (minimum)")
            stop_loss_percent = 0.5
        
        return {
            "risk_percent": risk_percent,
            "stop_loss_percent": stop_loss_percent,
            "leverage": leverage,
            "warnings": warnings
        }
    
    def _check_rate_limits(self) -> Dict[str, Any]:
        """
        Check if trade rate limits are respected
        
        Returns:
            Dict with 'can_trade' bool and 'reason' if blocked
        """
        # Daily limit
        max_daily = self.config.get("max_daily_trades", 50)
        if self.daily_trades >= max_daily:
            return {
                "can_trade": False,
                "reason": f"Daily trade limit reached ({max_daily})",
                "reset_in": "Next day"
            }
        
        # Active bots limit
        max_bots = self.config.get("max_active_bots", 10)
        active_count = sum(1 for b in self.ai_bots.values() if b.get("status") == "RUNNING")
        if active_count >= max_bots:
            return {
                "can_trade": False,
                "reason": f"Max active bots limit reached ({max_bots})",
                "active_bots": active_count
            }
        
        # Cooldown check
        if self.cooldown_until and datetime.utcnow() < self.cooldown_until:
            remaining = (self.cooldown_until - datetime.utcnow()).seconds
            return {
                "can_trade": False,
                "reason": f"In cooldown after loss",
                "cooldown_remaining_seconds": remaining
            }
        
        return {"can_trade": True}
    
    def update_config(self, new_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update configuration with validation
        
        Args:
            new_config: Dict of config keys to update
            
        Returns:
            Updated config with any corrections applied
        """
        warnings = []
        
        # === Handle special fields ===
        if "enabled" in new_config:
            self.enabled = new_config.pop("enabled")
            logger.info(f"AI Agent {'enabled' if self.enabled else 'disabled'}")
        
        if "watchlist_symbols" in new_config:
            symbols = new_config.pop("watchlist_symbols")
            if isinstance(symbols, list) and len(symbols) > 0:
                self.config["watchlist_symbols"] = symbols
                logger.info(f"Watchlist updated: {symbols}")
            else:
                warnings.append("⚠️ Watchlist must contain at least one symbol")
        
        # === CRITICAL: Never allow futures/margin via config update ===
        if new_config.get("allow_futures", False):
            warnings.append("🚫 REJECTED: Cannot enable futures trading")
            new_config["allow_futures"] = False
        
        if new_config.get("allow_margin", False):
            warnings.append("🚫 REJECTED: Cannot enable margin trading")
            new_config["allow_margin"] = False
        
        if new_config.get("allow_leverage", False):
            warnings.append("🚫 REJECTED: Cannot enable leverage")
            new_config["allow_leverage"] = False
        
        if new_config.get("max_leverage", 1.0) > 1.0:
            warnings.append("🚫 REJECTED: Leverage must be 1.0 (spot only)")
            new_config["max_leverage"] = 1.0
        
        # Validate numeric ranges
        if "max_risk_percent" in new_config:
            if new_config["max_risk_percent"] > 5.0:
                warnings.append("⚠️ max_risk_percent capped at 5%")
                new_config["max_risk_percent"] = 5.0
        
        if "max_stop_loss_percent" in new_config:
            if new_config["max_stop_loss_percent"] > 10.0:
                warnings.append("⚠️ max_stop_loss_percent capped at 10%")
                new_config["max_stop_loss_percent"] = 10.0
        
        if "max_daily_trades" in new_config:
            if new_config["max_daily_trades"] > 200:
                warnings.append("⚠️ max_daily_trades capped at 200")
                new_config["max_daily_trades"] = 200
        
        if "min_confidence" in new_config:
            confidence = new_config["min_confidence"]
            if confidence < 50 or confidence > 100:
                warnings.append("⚠️ min_confidence must be between 50-100")
                new_config["min_confidence"] = max(50, min(100, confidence))
        
        # Apply validated config
        self.config.update(new_config)
        
        logger.info(f"🔧 Config updated: {new_config}")
        if warnings:
            for w in warnings:
                logger.warning(w)
        
        return {
            "config": self.config,
            "warnings": warnings
        }
    
    def _get_ai_user_id(self) -> str:
        """Get the AI system user ID"""
        # TODO: Create/fetch AI system user from database
        # For now, return a placeholder UUID
        return "00000000-0000-0000-0000-000000000001"
    
    def _log_decision(
        self,
        recommendation: Dict[str, Any],
        executed: bool = False,
        bot_id: Optional[str] = None,
        blocked_reason: Optional[str] = None
    ):
        """
        Log AI decision to database with retry logic for Railway resilience
        
        Args:
            recommendation: AI recommendation dict
            executed: Whether the trade was executed
            bot_id: ID of bot that executed the decision (if any)
            blocked_reason: Why the trade was blocked (if any)
        """
        # Log to application logs
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "symbol": recommendation.get("symbol"),
            "action": recommendation.get("action"),
            "confidence": recommendation.get("confidence"),
            "executed": executed,
            "blocked": blocked_reason is not None,
            "blocked_reason": blocked_reason,
            "bot_id": bot_id,
            "mode": self.mode,
            "reasoning": recommendation.get("reasoning"),
            "risk_percent": recommendation.get("risk_percent"),
            "stop_loss_percent": recommendation.get("stop_loss_percent"),
        }
        
        if blocked_reason:
            logger.warning(f"🚫 AI Decision BLOCKED: {json.dumps(log_entry)}")
        else:
            logger.info(f"📝 AI Decision: {json.dumps(log_entry)}")
        
        # Store in database with retry logic for Railway resilience
        max_retries = 3
        retry_delay = 1  # Start with 1 second
        
        for attempt in range(1, max_retries + 1):
            db = self.db_session_factory()
            try:
                ai_decision = AIDecision(
                    user_id=self._get_ai_user_id(),
                    bot_id=bot_id,
                    symbol=recommendation.get("symbol"),
                    action=recommendation.get("action"),
                    confidence=recommendation.get("confidence", 0),
                    reasoning=recommendation.get("reasoning"),
                    entry_price=recommendation.get("entry_price"),
                    target_price=recommendation.get("target_price"),
                    stop_loss=recommendation.get("stop_loss"),
                    risk_level=recommendation.get("risk_level", "MEDIUM"),
                    timeframe=recommendation.get("timeframe", "1h"),
                    executed=executed,
                    blocked=blocked_reason is not None,
                    blocked_reason=blocked_reason,
                    mode=self.mode,
                    strategy_proposed=recommendation.get("strategy_proposed"),
                    ai_agrees=recommendation.get("ai_agrees"),
                    created_at=datetime.utcnow()
                )
                
                db.add(ai_decision)
                db.commit()
                
                logger.debug(f"✅ AI Decision logged to DB (attempt {attempt}): {ai_decision.id}")
                break  # Success - exit retry loop
                
            except (OperationalError, DBAPIError) as e:
                # Connection error - retry with exponential backoff
                db.rollback()
                db.close()
                
                if attempt < max_retries:
                    wait_time = retry_delay * (2 ** (attempt - 1))  # Exponential: 1s, 2s, 4s
                    logger.warning(
                        f"⚠️ Database connection error on attempt {attempt}/{max_retries}: {str(e)}. "
                        f"Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(
                        f"❌ Failed to log AI decision to DB after {max_retries} attempts. "
                        f"Decision will be lost: {json.dumps(log_entry)}"
                    )
                    
            except Exception as e:
                # Non-recoverable error - don't retry
                db.rollback()
                db.close()
                logger.error(
                    f"❌ Error logging AI decision to DB (non-recoverable): {str(e)}. "
                    f"Decision: {json.dumps(log_entry)}"
                )
                break
            
            finally:
                try:
                    db.close()
                except:
                    pass  # Session already closed
    
    def set_mode(self, mode: str):
        """
        Set operating mode
        
        Args:
            mode: 'observation', 'paper', or 'live'
        """
        valid_modes = ["observation", "paper", "live"]
        if mode not in valid_modes:
            raise ValueError(f"Invalid mode. Must be one of: {valid_modes}")
        
        old_mode = self.mode
        self.mode = mode
        logger.info(f"🔄 AI Bot Controller mode changed: {old_mode} -> {mode}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of AI Bot Controller"""
        return {
            "enabled": self.enabled,
            "running": self._running,
            "mode": self.mode,
            "ai_bots_count": len(self.ai_bots),
            "active_ai_bots": sum(1 for b in self.ai_bots.values() if b.get("status") == "RUNNING"),
            "daily_trades": self.daily_trades,
            "max_daily_trades": self.config["max_daily_trades"],
            "in_cooldown": self.cooldown_until and datetime.utcnow() < self.cooldown_until,
            "cooldown_until": self.cooldown_until.isoformat() if self.cooldown_until else None,
            "config": self.config
        }
    
    def get_ai_bots(self) -> List[Dict[str, Any]]:
        """Get list of AI-managed bots"""
        return list(self.ai_bots.values())
    
    async def chat(self, message: str) -> Dict[str, Any]:
        """
        Chat with AI Agent about trading decisions
        
        Args:
            message: User message/question
            
        Returns:
            AI response with context
        """
        if not ai_agent:
            return {
                "response": "AI Agent not available",
                "error": True
            }
        
        # Build context for AI
        context = {
            "mode": self.mode,
            "active_bots": self.get_ai_bots(),
            "recent_decisions": ai_agent.decision_history[-5:] if ai_agent.decision_history else []
        }
        
        # Get AI response
        response = await ai_agent.chat(message, context)
        
        return {
            "response": response,
            "timestamp": datetime.utcnow().isoformat(),
            "mode": self.mode
        }


# Global instance
ai_bot_controller: Optional[AIBotController] = None


def initialize_ai_bot_controller(db_session_factory, bot_engine=None) -> AIBotController:
    """
    Initialize the global AI Bot Controller
    
    Args:
        db_session_factory: Database session factory
        bot_engine: Optional BotEngine reference
        
    Returns:
        Initialized AIBotController instance
    """
    global ai_bot_controller
    
    ai_bot_controller = AIBotController(db_session_factory, bot_engine)
    logger.info("✅ AI Bot Controller initialized")
    
    return ai_bot_controller

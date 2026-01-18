"""
Bot Execution Engine
Manages active trading bots and executes their strategies
Integrates with AI Agent for enhanced decision making
Integrates with SLTPManager for intelligent SL/TP management
"""
import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.database_models import Bot, Trade, Portfolio
from app.services.strategies import StrategyRegistry
from app.services.market_data import MarketDataCollector
from app.services.technical_analysis import TechnicalAnalysis
from app.services.risk_manager import RiskManager
from app.services.sl_tp_manager import SLTPManager, TradeState, TradePhase, ExitReason
import uuid
import logging

logger = logging.getLogger(__name__)


class BotEngine:
    """
    Central engine for executing trading bots.
    Manages active bots, executes strategies, and handles paper trading.
    Integrates with AI Agent for intelligent trade validation.
    Integrates with SLTPManager for intelligent SL/TP management.
    """
    
    def __init__(self, db_session_factory):
        """
        Initialize BotEngine with a session factory for database operations.
        
        Args:
            db_session_factory: A callable that returns a new database session
        """
        self.db_session_factory = db_session_factory
        self.active_bots: Dict[str, Dict[str, Any]] = {}
        self.market_data = MarketDataCollector()
        self.technical_analysis = TechnicalAnalysis()
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
        # Risk Manager (centralized validation)
        self.risk_manager = RiskManager(db_session_factory)
        
        # SL/TP Manager (intelligent stop loss and take profit)
        self.sltp_manager = SLTPManager(
            market_data_service=self.market_data,
            technical_analysis=self.technical_analysis,
            db_session_factory=db_session_factory
        )
        
        # AI Agent integration
        self.ai_agent = None  # Will be set via set_ai_agent()
        self.ai_enabled = False  # Enable/disable AI validation
        self.ai_mode = "advisory"  # advisory (suggest) or autonomous (auto-trade)
        self.ai_min_confidence = 60  # Minimum AI confidence to proceed
    
    def set_ai_agent(self, ai_agent):
        """
        Set the AI Agent for trade validation
        
        Args:
            ai_agent: AITradingAgent instance
        """
        self.ai_agent = ai_agent
        self.ai_enabled = ai_agent is not None
        logger.info(f"🤖 AI Agent {'connected' if self.ai_enabled else 'disconnected'} to BotEngine")
    
    def configure_ai(self, enabled: bool = True, mode: str = "advisory", min_confidence: int = 60):
        """
        Configure AI integration settings
        
        Args:
            enabled: Enable/disable AI validation
            mode: 'advisory' (suggest only) or 'autonomous' (can block trades)
            min_confidence: Minimum confidence level (0-100)
        """
        # ✅ Allow enabling AI even if agent not set yet (will be set per-user later)
        self.ai_enabled = enabled
        self.ai_mode = mode if mode in ["advisory", "autonomous"] else "advisory"
        self.ai_min_confidence = max(0, min(100, min_confidence))
        
        logger.info(f"🤖 AI Config: enabled={self.ai_enabled}, mode={self.ai_mode}, min_confidence={self.ai_min_confidence}%")
    
    async def start(self):
        """Start the bot engine"""
        if self._running:
            logger.warning("⚠️ Bot engine already running")
            return
        
        self._running = True
        logger.info("✅ Bot Engine started")
        
        # Load all active bots from database
        await self.load_active_bots()
        
        # Start monitoring loop as background task
        self._task = asyncio.create_task(self._monitor_loop())
    
    async def stop(self):
        """Stop the bot engine"""
        self._running = False
        logger.info("🛑 Stopping Bot Engine...")
        
        # Cancel task
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("✅ Bot Engine stopped")
    
    async def load_active_bots(self):
        """Load all active bots from database"""
        db = self.db_session_factory()
        try:
            bots = db.query(Bot).filter(Bot.status == "RUNNING").all()
            
            for bot in bots:
                await self.activate_bot(str(bot.id))
            
            logger.info(f"📊 Loaded {len(bots)} active bots")
        finally:
            db.close()
    
    async def activate_bot(self, bot_id: str):
        """Activate a bot and start its execution"""
        db = self.db_session_factory()
        try:
            bot = db.query(Bot).filter(Bot.id == bot_id).first()
            
            if not bot:
                raise ValueError(f"Bot {bot_id} not found")
            
            # Parse configuration - handle both string and dict (PostgreSQL JSONB)
            if isinstance(bot.config, str):
                config = json.loads(bot.config) if bot.config else {}
            else:
                config = bot.config or {}
                
            if isinstance(bot.symbols, str):
                symbols = json.loads(bot.symbols) if bot.symbols else ["BTCUSDT"]
            else:
                symbols = bot.symbols or ["BTCUSDT"]
            
            # Load strategy
            strategy = StrategyRegistry.get_strategy(bot.strategy, config)
            
            # Store bot state
            self.active_bots[str(bot.id)] = {
                "bot_id": str(bot.id),
                "user_id": str(bot.user_id),
                "name": bot.name,
                "strategy": strategy,
                "symbols": symbols,
                "config": config,
                "paper_trading": bot.paper_trading,
                "risk_percent": float(bot.risk_percent or 2.0),
                "last_check": None
            }
            
            # Update bot status
            bot.status = "RUNNING"
            db.commit()
            
            logger.info(f"✅ Activated bot: {bot.name} ({bot.strategy})")
        finally:
            db.close()
    
    async def deactivate_bot(self, bot_id: str):
        """Deactivate a bot and stop its execution"""
        if bot_id not in self.active_bots:
            return
        
        bot_state = self.active_bots[bot_id]
        
        # Remove from active bots
        del self.active_bots[bot_id]
        
        # Update database
        db = self.db_session_factory()
        try:
            bot = db.query(Bot).filter(Bot.id == bot_id).first()
            if bot:
                bot.status = "IDLE"
                db.commit()
            logger.info(f"🛑 Deactivated bot: {bot_state['name']}")
        finally:
            db.close()
    
    async def _monitor_loop(self):
        """Main monitoring loop - checks all active bots every 60 seconds"""
        logger.info("🔄 Bot monitoring loop started")
        while self._running:
            try:
                # Process each active bot
                for bot_id in list(self.active_bots.keys()):
                    try:
                        await self._process_bot(bot_id)
                    except Exception as e:
                        logger.error(f"❌ Error processing bot {bot_id}: {str(e)}")
                        await self._handle_bot_error(bot_id, str(e))
                
                # Wait before next iteration (60 seconds for paper trading)
                await asyncio.sleep(60)
            
            except Exception as e:
                logger.error(f"❌ Error in monitor loop: {str(e)}")
                await asyncio.sleep(5)
    
    async def _process_bot(self, bot_id: str):
        """Process a single bot - check signals and execute trades"""
        bot_state = self.active_bots.get(bot_id)
        if not bot_state:
            return
        
        strategy = bot_state["strategy"]
        symbols = bot_state["symbols"]
        
        # Check each symbol
        for symbol in symbols:
            try:
                # Get market data
                market_data = await self._get_market_data(symbol)
                
                if not market_data:
                    continue
                
                # Check for open positions (for strategies that need to know this)
                db = self.db_session_factory()
                try:
                    open_buy_position = db.query(Trade).filter(
                        Trade.bot_id == bot_id,
                        Trade.symbol == symbol,
                        Trade.status == "OPEN",
                        Trade.side == "BUY"
                    ).first()
                    
                    if open_buy_position:
                        market_data['open_position'] = {
                            'side': 'BUY',
                            'entry_price': float(open_buy_position.entry_price),
                            'quantity': float(open_buy_position.quantity),
                            'id': str(open_buy_position.id)
                        }
                finally:
                    db.close()
                
                # Check for new signals from strategy
                signal = strategy.get_signal_direction(market_data)
                
                logger.info(f"📊 [SIGNAL] {bot_state['name']} | {symbol} | Signal: {signal}")
                
                # === AI AGENT VALIDATION ===
                ai_validation = None
                if signal in ["BUY", "SELL"] and self.ai_enabled and self.ai_agent:
                    ai_validation = await self._get_ai_validation(symbol, signal, market_data)
                    
                    if ai_validation:
                        logger.info(f"🤖 AI Analysis for {symbol}: {ai_validation.get('action')} "
                                   f"(confidence: {ai_validation.get('confidence', 0)}%)")
                        
                        # In autonomous mode, AI can block trades
                        if self.ai_mode == "autonomous":
                            ai_confidence = ai_validation.get("confidence", 0)
                            ai_action = ai_validation.get("action", "HOLD")
                            
                            # Block if AI disagrees or low confidence
                            if ai_action != signal or ai_confidence < self.ai_min_confidence:
                                logger.warning(f"🤖 AI BLOCKED {signal} on {symbol}: "
                                             f"AI says {ai_action} with {ai_confidence}% confidence")
                                continue  # Skip this trade
                
                if signal == "BUY":
                    await self._execute_buy(bot_state, strategy, symbol, market_data, ai_validation)
                elif signal == "SELL":
                    await self._execute_sell(bot_state, strategy, symbol, market_data, ai_validation)
                
                # Check open positions for exit signals
                await self._check_open_positions(bot_state, strategy, symbol, market_data)
            
            except Exception as e:
                logger.error(f"❌ Error processing {symbol} for bot {bot_state['name']}: {str(e)}")
        
        bot_state["last_check"] = datetime.utcnow()
    
    async def _get_ai_validation(
        self,
        symbol: str,
        proposed_action: str,
        market_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Get AI Agent validation for a proposed trade
        
        Args:
            symbol: Trading pair
            proposed_action: BUY or SELL
            market_data: Current market data with indicators
            
        Returns:
            AI analysis dict or None if AI unavailable
        """
        if not self.ai_agent or not self.ai_enabled:
            return None
        
        try:
            # Prepare data for AI
            price_data = {
                "close": market_data.get("close", 0),
                "high": market_data.get("high", 0),
                "low": market_data.get("low", 0),
                "volume": market_data.get("volume", 0),
                "change_24h": 0  # TODO: Calculate from history
            }
            
            indicators = market_data.get("indicators", {})
            
            # Get AI analysis - simplified API
            analysis = await self.ai_agent.analyze_market(symbol=symbol)
            
            # Add context about what strategy proposed
            analysis["strategy_proposed"] = proposed_action
            analysis["ai_agrees"] = analysis.get("action") == proposed_action
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ AI validation error for {symbol}: {str(e)}")
            return None
    
    async def _get_market_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch and prepare market data with indicators"""
        try:
            # Get historical data from Binance
            candles = await self.market_data.get_candles(symbol, timeframe="1h", limit=100)
            
            if not candles or len(candles) < 20:
                logger.warning(f"Insufficient market data for {symbol}")
                return None
            
            # Calculate technical indicators
            closes = [c['close'] for c in candles]
            highs = [c['high'] for c in candles]
            lows = [c['low'] for c in candles]
            volumes = [c['volume'] for c in candles]
            
            # Calculate indicators
            sma_20 = self.technical_analysis.calculate_sma(closes, 20)
            sma_50 = self.technical_analysis.calculate_sma(closes, 50)
            rsi = self.technical_analysis.calculate_rsi(closes, 14)
            bb_upper, bb_middle, bb_lower = self.technical_analysis.calculate_bollinger_bands(closes, 20, 2)
            atr = self.technical_analysis.calculate_atr(candles, 14)
            
            # Find support/resistance (simplified)
            resistance = max(highs[-20:])
            support = min(lows[-20:])
            avg_volume = sum(volumes[-20:]) / 20
            
            current = candles[-1]
            
            return {
                "symbol": symbol,
                "close": current['close'],
                "high": current['high'],
                "low": current['low'],
                "volume": current['volume'],
                "timestamp": current['timestamp'],
                "indicators": {
                    "sma_20": sma_20[-1] if sma_20 else None,
                    "sma_50": sma_50[-1] if sma_50 else None,
                    "rsi": rsi[-1] if rsi else None,
                    "bb_upper": bb_upper[-1] if bb_upper else None,
                    "bb_middle": bb_middle[-1] if bb_middle else None,
                    "bb_lower": bb_lower[-1] if bb_lower else None,
                    "atr": atr[-1] if atr and atr[-1] is not None else None,
                    "resistance": resistance,
                    "support": support,
                    "avg_volume": avg_volume
                },
                "open_position": None  # Will be populated by strategy if needed
            }
        except Exception as e:
            logger.error(f"Error getting market data for {symbol}: {e}")
            return None
    
    async def _execute_buy(
        self,
        bot_state: Dict[str, Any],
        strategy: Any,
        symbol: str,
        market_data: Dict[str, Any],
        ai_validation: Optional[Dict[str, Any]] = None
    ):
        """Execute a BUY trade (paper trading) with centralized risk validation and intelligent SL/TP"""
        ABSOLUTE_MAX_POSITION_PCT = 0.25  # 25% max
        
        bot_id = bot_state["bot_id"]
        user_id = bot_state["user_id"]
        current_price = market_data['close']
        
        # ================================================================
        # 1. Validate trade with RiskManager
        # ================================================================
        validation = await self.risk_manager.validate_trade(
            user_id=user_id,
            symbol=symbol,
            side="BUY",
            entry_price=current_price,
            source="BOT",
            bot_id=bot_id,
            market_data=market_data
        )
        
        if not validation.allowed:
            logger.info(f"⚠️ [BLOCKED] {symbol} BUY: {validation.reason}")
            return
        
        # Log warnings if any
        for warning in validation.warnings:
            logger.warning(f"⚠️ {symbol}: {warning}")
        
        # ================================================================
        # 2. Calculate Intelligent SL/TP with SLTPManager
        # ================================================================
        try:
            from uuid import UUID
            user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
            
            sltp_config = await self.sltp_manager.calculate_sl_tp(
                user_id=user_uuid,
                symbol=symbol,
                entry_price=current_price,
                side="BUY",
                market_data=market_data
            )
            
            final_stop_loss = sltp_config.stop_loss
            take_profit = sltp_config.take_profit_1
            
            # Validate SL/TP (fallback in case SLTPManager failed)
            if not final_stop_loss or final_stop_loss <= 0 or final_stop_loss == current_price:
                logger.warning(f"⚠️ Invalid SL from SLTPManager: {final_stop_loss}, using fallback")
                final_stop_loss = current_price * 0.97  # 3% below
            
            if not take_profit or take_profit <= 0 or take_profit == current_price:
                logger.warning(f"⚠️ Invalid TP from SLTPManager: {take_profit}, using fallback")
                take_profit = current_price * 1.03  # 3% above
            
            logger.info(f"🎯 [SLTP] Using intelligent SL/TP: SL=${final_stop_loss:.4f}, TP=${take_profit:.4f}")
            
        except Exception as e:
            logger.warning(f"⚠️ SLTPManager error, falling back to strategy: {e}")
            # Fallback to strategy-based SL/TP
            final_stop_loss = strategy.get_stop_loss(current_price, "BUY", market_data)
            take_profit = strategy.get_take_profit(current_price, "BUY", market_data)
        
        # Override with RiskManager values if provided (for backward compatibility)
        if validation.stop_loss:
            final_stop_loss = validation.stop_loss
        if validation.take_profit:
            take_profit = validation.take_profit
        
        # ================================================================
        # 3. Execute the trade
        # ================================================================
        db = self.db_session_factory()
        try:
            # Get portfolio
            portfolio = db.query(Portfolio).filter(Portfolio.user_id == user_id).first()
            if not portfolio:
                logger.warning(f"❌ Portfolio not found for user {user_id}")
                return
            
            # Calculate position size using SLTPManager (risk-first approach)
            portfolio_value = float(portfolio.total_value) if portfolio.total_value else float(portfolio.cash_balance)
            
            if validation.adjusted_amount:
                # Use RiskManager's calculated amount
                cost = validation.adjusted_amount
                quantity = cost / current_price
            else:
                # Use SLTPManager's position sizing (risk-first)
                quantity, cost = self.sltp_manager.calculate_position_size_from_sl(
                    portfolio_value=portfolio_value,
                    entry_price=current_price,
                    stop_loss=final_stop_loss,
                    risk_percent=bot_state["risk_percent"],
                    max_position_pct=ABSOLUTE_MAX_POSITION_PCT * 100
                )
            
            # ================================================================
            # CRITICAL: Position Size Enforcement (FIX #3 & #4)
            # ================================================================
            max_position_cost = portfolio_value * ABSOLUTE_MAX_POSITION_PCT
            
            # ALSO CHECK: We have enough cash to buy
            available_cash = float(portfolio.cash_balance)
            if cost > available_cash:
                logger.warning(f"⚠️ [CASH-LIMIT] Cost ${cost:.2f} exceeds available cash ${available_cash:.2f}, reducing")
                cost = available_cash * 0.95  # Use 95% to leave buffer
                quantity = cost / current_price
                if cost <= 0:
                    logger.error(f"❌ [INSUFFICIENT-CASH] Cannot trade {symbol}, need ${cost:.2f} but only have ${available_cash:.2f}")
                    return
            
            if cost > max_position_cost:
                logger.warning(f"⚠️ [POS-LIMIT] Cost ${cost:.2f} exceeds max ${max_position_cost:.2f}, clamping")
                cost = max_position_cost
                quantity = cost / current_price
            
            old_balance = float(portfolio.cash_balance)
            
            # Deduct from balance (paper trading)
            if bot_state["paper_trading"]:
                portfolio.cash_balance = float(portfolio.cash_balance) - cost
            
            new_balance = float(portfolio.cash_balance)
            
            # Create trade
            trade = Trade(
                id=uuid.uuid4(),
                user_id=user_id,
                bot_id=bot_id,
                symbol=symbol,
                side="BUY",
                entry_price=current_price,
                exit_price=None,
                quantity=quantity,
                pnl=None,
                pnl_percent=None,
                status="OPEN",
                entry_time=datetime.utcnow(),
                exit_time=None,
                strategy=bot_state["strategy"].__class__.__name__,
                stop_loss_price=final_stop_loss,
                take_profit_price=take_profit
            )
            
            db.add(trade)
            db.add(portfolio)
            
            # Update bot stats
            bot = db.query(Bot).filter(Bot.id == bot_id).first()
            if bot:
                bot.total_trades = (bot.total_trades or 0) + 1
            
            db.commit()
            trade_id = str(trade.id)
            
            # ================================================================
            # Comprehensive Logging (FIX #5)
            # ================================================================
            sl_pct = ((float(final_stop_loss) - current_price) / current_price) * 100 if final_stop_loss else 0
            tp_pct = ((take_profit - current_price) / current_price) * 100 if take_profit else 0
            
            ai_result = "N/A"
            if ai_validation:
                ai_confidence = ai_validation.get("confidence", 0)
                ai_agrees = ai_validation.get("ai_agrees", False)
                ai_result = f"{'✓' if ai_agrees else '✗'} ({ai_confidence}%)"
            
            logger.info(f"✅ [BUY-EXEC] {bot_state['name']} | {symbol}")
            logger.info(f"├─ Trade ID: {trade_id}")
            logger.info(f"├─ Price: ${current_price:.2f}")
            logger.info(f"├─ Quantity: {quantity:.6f}")
            logger.info(f"├─ Cost: ${cost:.2f}")
            logger.info(f"├─ Portfolio: ${old_balance:.2f} → ${new_balance:.2f}")
            logger.info(f"├─ SL: ${final_stop_loss:.2f} ({sl_pct:.2f}%)")
            logger.info(f"├─ TP: ${take_profit:.2f} ({tp_pct:.2f}%)" if take_profit else f"├─ TP: N/A")
            logger.info(f"└─ 🤖 AI: {ai_result}")
        finally:
            db.close()
    
    async def _execute_sell(
        self,
        bot_state: Dict[str, Any],
        strategy: Any,
        symbol: str,
        market_data: Dict[str, Any],
        ai_validation: Optional[Dict[str, Any]] = None
    ):
        """Execute a SELL trade (close position)"""
        db = self.db_session_factory()
        try:
            bot_id = bot_state["bot_id"]
            exit_price = market_data['close']
            
            # Find open BUY position
            open_position = db.query(Trade).filter(
                Trade.bot_id == bot_id,
                Trade.symbol == symbol,
                Trade.status == "OPEN",
                Trade.side == "BUY"
            ).first()
            
            if not open_position:
                logger.info(f"⚠️ [SKIP] No open BUY position to SELL for {symbol}")
                return
            
            # Prepare AI info
            ai_result = "N/A"
            if ai_validation:
                ai_confidence = ai_validation.get("confidence", 0)
                ai_agrees = ai_validation.get("ai_agrees", False)
                ai_result = f"{'✓' if ai_agrees else '✗'} ({ai_confidence}%)"
            
            # Close position and capture the reason
            await self._close_position(db, bot_state, open_position, exit_price, "Signal", ai_result=ai_result)
        finally:
            db.close()
    
    async def _check_open_positions(self, bot_state: Dict[str, Any], strategy: Any, symbol: str, market_data: Dict[str, Any]):
        """Check if any open positions should be closed"""
        db = self.db_session_factory()
        try:
            bot_id = bot_state["bot_id"]
            
            open_trades = db.query(Trade).filter(
                Trade.bot_id == bot_id,
                Trade.symbol == symbol,
                Trade.status == "OPEN"
            ).all()
            
            if not open_trades:
                logger.debug(f"📊 [POS-CHECK] {symbol} | No open trades")
                return
            
            current_price = market_data['close']
            logger.info(f"📊 [POS-CHECK] {symbol} | {len(open_trades)} open trade(s) @ ${current_price:.2f}")
            
            for trade in open_trades:
                trade_id = str(trade.id)
                
                # Check stop loss
                if trade.stop_loss_price:
                    sl_price = float(trade.stop_loss_price)
                    if trade.side == "BUY" and current_price <= sl_price:
                        logger.info(f"🛑 [SL-TRIGGER] {symbol} | Trade {trade_id[:8]} | Price ${current_price:.2f} ≤ SL ${sl_price:.2f}")
                        await self._close_position(db, bot_state, trade, current_price, "Stop Loss")
                        continue
                
                # Check take profit
                if trade.take_profit_price:
                    tp_price = float(trade.take_profit_price)
                    if trade.side == "BUY" and current_price >= tp_price:
                        logger.info(f"💰 [TP-TRIGGER] {symbol} | Trade {trade_id[:8]} | Price ${current_price:.2f} ≥ TP ${tp_price:.2f}")
                        await self._close_position(db, bot_state, trade, current_price, "Take Profit")
                        continue
                    elif current_price < tp_price:
                        # Still monitoring TP
                        tp_distance = tp_price - current_price
                        tp_pct = (tp_distance / current_price) * 100
                        logger.debug(f"📊 [TP-WATCH] {symbol} | Trade {trade_id[:8]} | ${current_price:.2f} → TP ${tp_price:.2f} (+{tp_pct:.2f}%)")
                else:
                    logger.debug(f"⚠️ [NO-TP] Trade {trade_id[:8]} has no take_profit_price set")
                
                # Check strategy exit conditions
                trade_dict = {
                    "entry_price": float(trade.entry_price),
                    "side": trade.side,
                    "quantity": float(trade.quantity)
                }
                
                exit_result = strategy.should_exit(trade_dict, current_price, market_data)
                # Handle both (bool, str) tuple and plain bool returns
                if isinstance(exit_result, tuple):
                    should_exit, exit_reason = exit_result
                else:
                    should_exit, exit_reason = exit_result, ""
                
                if should_exit:
                    reason = exit_reason if exit_reason else "Strategy Exit"
                    await self._close_position(db, bot_state, trade, current_price, reason)
        finally:
            db.close()
    
    async def _close_position(self, db: Session, bot_state: Dict[str, Any], trade: Trade, exit_price: float, reason: str, ai_result: str = "N/A"):
        """Close an open position"""
        entry_price = float(trade.entry_price)
        trade_id = str(trade.id)
        
        trade.exit_price = exit_price
        trade.exit_time = datetime.utcnow()
        trade.status = "CLOSED"
        
        # Calculate PnL
        if trade.side == "BUY":
            trade.pnl = (exit_price - entry_price) * float(trade.quantity)
            trade.pnl_percent = ((exit_price - entry_price) / entry_price) * 100
        
        # Update portfolio (paper trading)
        if bot_state["paper_trading"]:
            portfolio = db.query(Portfolio).filter(Portfolio.user_id == bot_state["user_id"]).first()
            if portfolio:
                # BUG FIX: Add only the PnL (gain/loss), not the full proceeds
                # When selling at exit_price:
                #   - Proceeds = exit_price * quantity (total cash received)
                #   - But we spent = entry_price * quantity (initial cost)
                #   - Gain/Loss = PnL = (exit_price - entry_price) * quantity
                pnl = trade.pnl or 0
                new_balance = float(portfolio.cash_balance) + pnl
                
                # === CRITICAL: Protect against negative balance ===
                if new_balance < 0:
                    logger.error(f"🚨 CRITICAL: Portfolio balance would go negative! ({new_balance:.2f})")
                    logger.error(f"   Current: ${float(portfolio.cash_balance):.2f}, PnL: ${pnl:.2f}")
                    logger.error(f"   Trade: {trade.symbol} {trade.side} {float(trade.quantity):.6f} @ Entry: ${entry_price:.2f}, Exit: ${exit_price:.2f}")
                    # Still allow the transaction but alert the user
                    # This shouldn't happen if protections work, but catches bugs
                
                portfolio.cash_balance = new_balance
                portfolio.total_pnl = float(portfolio.total_pnl or 0) + pnl
                db.add(portfolio)  # Ensure portfolio changes are persisted
        
        # Update bot stats
        bot = db.query(Bot).filter(Bot.id == bot_state["bot_id"]).first()
        if bot:
            bot.total_pnl = float(bot.total_pnl or 0) + (trade.pnl or 0)
            
            # Recalculate win rate
            closed_trades = db.query(Trade).filter(
                Trade.bot_id == bot.id,
                Trade.status == "CLOSED"
            ).all()
            
            if closed_trades:
                winning = len([t for t in closed_trades if (t.pnl or 0) > 0])
                bot.win_rate = (winning / len(closed_trades)) * 100
        
        db.commit()
        
        # ================================================================
        # Comprehensive Close Logging (FIX #5)
        # ================================================================
        pnl_str = f"+${trade.pnl:.2f}" if trade.pnl and trade.pnl > 0 else f"${trade.pnl:.2f}" if trade.pnl else "$0.00"
        pnl_pct_str = f"+{trade.pnl_percent:.2f}%" if trade.pnl_percent and trade.pnl_percent > 0 else f"{trade.pnl_percent:.2f}%" if trade.pnl_percent else "0.00%"
        
        logger.info(f"✅ [CLOSE-EXEC] {trade.symbol}")
        logger.info(f"├─ Trade ID: {trade_id}")
        logger.info(f"├─ Entry: ${entry_price:.2f} → Exit: ${exit_price:.2f}")
        logger.info(f"├─ PnL: {pnl_str} ({pnl_pct_str})")
        logger.info(f"└─ Reason: {reason}")
    
    async def _handle_bot_error(self, bot_id: str, error: str):
        """Handle bot execution error"""
        if bot_id not in self.active_bots:
            return
        
        bot_state = self.active_bots[bot_id]
        
        db = self.db_session_factory()
        try:
            bot = db.query(Bot).filter(Bot.id == bot_id).first()
            if bot:
                bot.status = "ERROR"
                db.commit()
            
            logger.error(f"❌ Bot {bot_state['name']} encountered error: {error}")
        finally:
            db.close()


# Global bot engine instance (will be set in main.py)
bot_engine: Optional[BotEngine] = None
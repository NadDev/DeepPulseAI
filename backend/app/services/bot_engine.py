"""
Bot Execution Engine
Manages active trading bots and executes their strategies
"""
import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.database_models import Bot, Trade, Portfolio
from app.services.strategies import StrategyRegistry
from app.services.market_data import MarketDataService
from app.services.technical_analysis import TechnicalAnalysis
import uuid


class BotEngine:
    """
    Central engine for executing trading bots.
    Manages active bots, executes strategies, and handles paper trading.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.active_bots: Dict[str, Dict[str, Any]] = {}
        self.market_data_service = MarketDataService()
        self.technical_analysis = TechnicalAnalysis()
        self._running = False
        self._tasks: List[asyncio.Task] = []
    
    async def start(self):
        """Start the bot engine"""
        if self._running:
            print("⚠️ Bot engine already running")
            return
        
        self._running = True
        print("✅ Bot Engine started")
        
        # Load all active bots from database
        await self.load_active_bots()
        
        # Start monitoring loop
        self._tasks.append(asyncio.create_task(self._monitor_loop()))
    
    async def stop(self):
        """Stop the bot engine"""
        self._running = False
        print("🛑 Stopping Bot Engine...")
        
        # Cancel all tasks
        for task in self._tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        
        print("✅ Bot Engine stopped")
    
    async def load_active_bots(self):
        """Load all active bots from database"""
        bots = self.db.query(Bot).filter(Bot.status == "ACTIVE").all()
        
        for bot in bots:
            await self.activate_bot(bot.id)
        
        print(f"📊 Loaded {len(bots)} active bots")
    
    async def activate_bot(self, bot_id: str):
        """Activate a bot and start its execution"""
        bot = self.db.query(Bot).filter(Bot.id == bot_id).first()
        
        if not bot:
            raise ValueError(f"Bot {bot_id} not found")
        
        # Parse configuration
        config = json.loads(bot.config) if bot.config else {}
        symbols = json.loads(bot.symbols) if bot.symbols else ["BTCUSDT"]
        
        # Load strategy
        strategy = StrategyRegistry.get_strategy(bot.strategy, config)
        
        # Store bot state
        self.active_bots[bot_id] = {
            "bot": bot,
            "strategy": strategy,
            "symbols": symbols,
            "config": config,
            "last_check": None
        }
        
        # Update bot status
        bot.status = "ACTIVE"
        self.db.commit()
        
        print(f"✅ Activated bot: {bot.name} ({bot.strategy})")
    
    async def deactivate_bot(self, bot_id: str):
        """Deactivate a bot and stop its execution"""
        if bot_id not in self.active_bots:
            return
        
        bot = self.active_bots[bot_id]["bot"]
        
        # Remove from active bots
        del self.active_bots[bot_id]
        
        # Update database
        bot.status = "INACTIVE"
        self.db.commit()
        
        print(f"🛑 Deactivated bot: {bot.name}")
    
    async def _monitor_loop(self):
        """Main monitoring loop - checks all active bots"""
        while self._running:
            try:
                # Process each active bot
                for bot_id in list(self.active_bots.keys()):
                    try:
                        await self._process_bot(bot_id)
                    except Exception as e:
                        print(f"❌ Error processing bot {bot_id}: {str(e)}")
                        await self._handle_bot_error(bot_id, str(e))
                
                # Wait before next iteration (e.g., 1 minute)
                await asyncio.sleep(60)
            
            except Exception as e:
                print(f"❌ Error in monitor loop: {str(e)}")
                await asyncio.sleep(5)
    
    async def _process_bot(self, bot_id: str):
        """Process a single bot - check signals and execute trades"""
        bot_state = self.active_bots.get(bot_id)
        if not bot_state:
            return
        
        bot = bot_state["bot"]
        strategy = bot_state["strategy"]
        symbols = bot_state["symbols"]
        
        # Check each symbol
        for symbol in symbols:
            try:
                # Get market data
                market_data = await self._get_market_data(symbol)
                
                # Check for new signals
                signal = strategy.get_signal_direction(market_data)
                
                if signal == "BUY":
                    await self._execute_buy(bot, strategy, symbol, market_data)
                elif signal == "SELL":
                    await self._execute_sell(bot, strategy, symbol, market_data)
                
                # Check open positions for exit signals
                await self._check_open_positions(bot, strategy, symbol, market_data)
            
            except Exception as e:
                print(f"❌ Error processing {symbol} for bot {bot.name}: {str(e)}")
        
        bot_state["last_check"] = datetime.utcnow()
    
    async def _get_market_data(self, symbol: str) -> Dict[str, Any]:
        """Fetch and prepare market data with indicators"""
        # Get historical data
        candles = self.market_data_service.get_historical_data(symbol, interval="1h", limit=100)
        
        if not candles:
            raise ValueError(f"No market data available for {symbol}")
        
        # Calculate technical indicators
        closes = [c['close'] for c in candles]
        highs = [c['high'] for c in candles]
        lows = [c['low'] for c in candles]
        volumes = [c['volume'] for c in candles]
        
        # Calculate indicators
        sma_20 = self.technical_analysis.calculate_sma(closes, 20)
        sma_50 = self.technical_analysis.calculate_sma(closes, 50)
        rsi = self.technical_analysis.calculate_rsi(closes, 14)
        bb = self.technical_analysis.calculate_bollinger_bands(closes, 20, 2)
        
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
                "bb_upper": bb['upper'][-1] if bb else None,
                "bb_middle": bb['middle'][-1] if bb else None,
                "bb_lower": bb['lower'][-1] if bb else None,
                "resistance": resistance,
                "support": support,
                "avg_volume": avg_volume
            }
        }
    
    async def _execute_buy(self, bot: Bot, strategy: Any, symbol: str, market_data: Dict[str, Any]):
        """Execute a BUY trade"""
        # Check if already have open position
        open_position = self.db.query(Trade).filter(
            Trade.bot_id == bot.id,
            Trade.symbol == symbol,
            Trade.status == "OPEN",
            Trade.side == "BUY"
        ).first()
        
        if open_position:
            print(f"⚠️ Already have open BUY position for {symbol}")
            return
        
        # Get portfolio
        portfolio = self.db.query(Portfolio).filter(Portfolio.user_id == "default").first()
        if not portfolio:
            print("❌ Portfolio not found")
            return
        
        # Calculate position size
        current_price = market_data['close']
        stop_loss = strategy.get_stop_loss(current_price, "BUY", market_data)
        risk_amount = portfolio.cash_balance * (bot.risk_percent / 100)
        quantity = strategy.calculate_position_size(risk_amount, current_price, stop_loss)
        
        cost = quantity * current_price
        
        # Check if enough balance (paper trading)
        if bot.paper_trading:
            if cost > portfolio.cash_balance:
                print(f"⚠️ Insufficient balance for {symbol} BUY")
                return
            
            # Deduct from balance
            portfolio.cash_balance -= cost
        
        # Calculate targets
        take_profit = strategy.get_take_profit(current_price, "BUY", market_data)
        
        # Create trade
        trade = Trade(
            id=None,  # Auto-increment
            bot_id=bot.id,
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
            strategy=bot.strategy,
            stop_loss_price=stop_loss,
            take_profit_price=take_profit
        )
        
        self.db.add(trade)
        bot.total_trades += 1
        self.db.commit()
        
        print(f"✅ BUY {symbol} @ {current_price:.2f} | Qty: {quantity:.6f} | SL: {stop_loss:.2f} | TP: {take_profit:.2f if take_profit else 'N/A'}")
    
    async def _execute_sell(self, bot: Bot, strategy: Any, symbol: str, market_data: Dict[str, Any]):
        """Execute a SELL trade (close position)"""
        # Find open BUY position
        open_position = self.db.query(Trade).filter(
            Trade.bot_id == bot.id,
            Trade.symbol == symbol,
            Trade.status == "OPEN",
            Trade.side == "BUY"
        ).first()
        
        if not open_position:
            print(f"⚠️ No open BUY position to SELL for {symbol}")
            return
        
        # Close position
        await self._close_position(open_position, market_data['close'], "Signal")
    
    async def _check_open_positions(self, bot: Bot, strategy: Any, symbol: str, market_data: Dict[str, Any]):
        """Check if any open positions should be closed"""
        open_trades = self.db.query(Trade).filter(
            Trade.bot_id == bot.id,
            Trade.symbol == symbol,
            Trade.status == "OPEN"
        ).all()
        
        current_price = market_data['close']
        
        for trade in open_trades:
            # Check stop loss
            if trade.stop_loss_price:
                if trade.side == "BUY" and current_price <= trade.stop_loss_price:
                    await self._close_position(trade, current_price, "Stop Loss")
                    continue
            
            # Check take profit
            if trade.take_profit_price:
                if trade.side == "BUY" and current_price >= trade.take_profit_price:
                    await self._close_position(trade, current_price, "Take Profit")
                    continue
            
            # Check strategy exit conditions
            trade_dict = {
                "entry_price": trade.entry_price,
                "side": trade.side,
                "quantity": trade.quantity
            }
            
            if strategy.should_exit(trade_dict, current_price, market_data):
                await self._close_position(trade, current_price, "Strategy Exit")
    
    async def _close_position(self, trade: Trade, exit_price: float, reason: str):
        """Close an open position"""
        trade.exit_price = exit_price
        trade.exit_time = datetime.utcnow()
        trade.status = "CLOSED"
        
        # Calculate PnL
        if trade.side == "BUY":
            trade.pnl = (exit_price - trade.entry_price) * trade.quantity
            trade.pnl_percent = ((exit_price - trade.entry_price) / trade.entry_price) * 100
        
        # Update portfolio (paper trading)
        bot = self.db.query(Bot).filter(Bot.id == trade.bot_id).first()
        if bot and bot.paper_trading:
            portfolio = self.db.query(Portfolio).filter(Portfolio.user_id == "default").first()
            if portfolio:
                proceeds = exit_price * trade.quantity
                portfolio.cash_balance += proceeds
                portfolio.total_pnl += trade.pnl or 0
        
        # Update bot stats
        if bot:
            bot.total_pnl += trade.pnl or 0
            
            # Recalculate win rate
            closed_trades = self.db.query(Trade).filter(
                Trade.bot_id == bot.id,
                Trade.status == "CLOSED"
            ).all()
            
            if closed_trades:
                winning = len([t for t in closed_trades if (t.pnl or 0) > 0])
                bot.win_rate = (winning / len(closed_trades)) * 100
        
        self.db.commit()
        
        pnl_str = f"+{trade.pnl:.2f}" if trade.pnl and trade.pnl > 0 else f"{trade.pnl:.2f}"
        print(f"✅ CLOSED {trade.symbol} @ {exit_price:.2f} | PnL: ${pnl_str} ({trade.pnl_percent:.2f}%) | Reason: {reason}")
    
    async def _handle_bot_error(self, bot_id: str, error: str):
        """Handle bot execution error"""
        if bot_id not in self.active_bots:
            return
        
        bot = self.active_bots[bot_id]["bot"]
        bot.status = "ERROR"
        self.db.commit()
        
        print(f"❌ Bot {bot.name} encountered error: {error}")
        
        # Could also create a RiskEvent here for logging

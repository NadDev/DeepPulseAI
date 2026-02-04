from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from app.db.database import get_db
from app.models.database_models import Bot, Trade, StrategyPerformance, Portfolio
from app.services.strategies import StrategyRegistry
from app.services import bot_engine as bot_engine_module
from app.auth.local_auth import get_current_user, get_optional_user, UserResponse
from sqlalchemy import desc
from datetime import datetime
import json
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bots", tags=["bots"])

# Helper function to get bot engine at runtime
def get_bot_engine():
    return bot_engine_module.bot_engine


# Pydantic models for request validation
class BotCreate(BaseModel):
    name: str
    strategy: str
    symbols: Optional[List[str]] = ["BTCUSDT"]
    config: Optional[Dict[str, Any]] = {}
    paper_trading: Optional[bool] = True
    risk_percent: Optional[float] = 2.0
    max_drawdown: Optional[float] = 20.0


class BotUpdate(BaseModel):
    name: Optional[str] = None
    strategy: Optional[str] = None
    symbols: Optional[List[str]] = None
    config: Optional[Dict[str, Any]] = None
    paper_trading: Optional[bool] = None
    risk_percent: Optional[float] = None
    max_drawdown: Optional[float] = None

@router.get("/strategies")
async def get_available_strategies():
    """Get all available trading strategies"""
    strategies = StrategyRegistry.list_strategies()
    return {"strategies": strategies, "total": len(strategies)}


@router.get("/list")
async def get_bots(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """Get all bots for current authenticated user"""
    bots = db.query(Bot).filter(Bot.user_id == current_user.id).all()
    
    result = []
    for bot in bots:
        # Get open trades count
        open_trades = db.query(Trade).filter(
            Trade.bot_id == bot.id,
            Trade.status == "OPEN"
        ).count()
        
        # Parse JSON fields - handle both string and parsed JSON (PostgreSQL JSONB)
        if isinstance(bot.config, str):
            config = json.loads(bot.config) if bot.config else {}
        else:
            config = bot.config or {}
            
        if isinstance(bot.symbols, str):
            symbols = json.loads(bot.symbols) if bot.symbols else []
        else:
            symbols = bot.symbols or []
        
        result.append({
            "id": bot.id,
            "name": bot.name,
            "strategy": bot.strategy,
            "status": bot.status,
            "is_live": bot.is_live,
            "paper_trading": bot.paper_trading,
            "total_trades": bot.total_trades,
            "win_rate": bot.win_rate,
            "total_pnl": bot.total_pnl,
            "max_drawdown": bot.max_drawdown,
            "open_trades": open_trades,
            "risk_percent": bot.risk_percent,
            "symbols": symbols,
            "config": config,
            "created_at": bot.created_at.isoformat() if bot.created_at else None,
            "updated_at": bot.updated_at.isoformat() if bot.updated_at else None,
        })
    
    return {"bots": result, "total": len(result)}

@router.get("/{bot_id}")
async def get_bot(
    bot_id: str, 
    db: Session = Depends(get_db),
    current_user: Optional[UserResponse] = Depends(get_optional_user)
):
    """Get specific bot details"""
    query = db.query(Bot).filter(Bot.id == bot_id)
    
    # Filter by user_id if authenticated
    if current_user:
        query = query.filter(Bot.user_id == current_user.id)
    
    bot = query.first()
    
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    # Get performance stats
    trades = db.query(Trade).filter(Trade.bot_id == bot.id).all()
    open_trades = [t for t in trades if t.status == "OPEN"]
    closed_trades = [t for t in trades if t.status == "CLOSED"]
    
    total_pnl = sum([t.pnl or 0 for t in closed_trades])
    
    # Parse JSON fields - handle both string and parsed JSON (PostgreSQL JSONB)
    if isinstance(bot.config, str):
        config = json.loads(bot.config) if bot.config else {}
    else:
        config = bot.config or {}
        
    if isinstance(bot.symbols, str):
        symbols = json.loads(bot.symbols) if bot.symbols else []
    else:
        symbols = bot.symbols or []
    
    return {
        "id": bot.id,
        "name": bot.name,
        "strategy": bot.strategy,
        "status": bot.status,
        "is_live": bot.is_live,
        "paper_trading": bot.paper_trading,
        "total_trades": len(trades),
        "open_trades": len(open_trades),
        "closed_trades": len(closed_trades),
        "win_rate": bot.win_rate,
        "total_pnl": total_pnl,
        "max_drawdown": bot.max_drawdown,
        "risk_percent": bot.risk_percent,
        "symbols": symbols,
        "config": config,
        "created_at": bot.created_at.isoformat() if bot.created_at else None,
        "updated_at": bot.updated_at.isoformat() if bot.updated_at else None,
    }


@router.post("/create")
async def create_bot(
    bot_data: BotCreate, 
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """Create a new trading bot"""
    # Validate strategy exists
    if not StrategyRegistry.is_registered(bot_data.strategy):
        available = ', '.join([s['name'] for s in StrategyRegistry.list_strategies()])
        raise HTTPException(
            status_code=400, 
            detail=f"Strategy '{bot_data.strategy}' not found. Available: {available}"
        )
    
    # Validate strategy config
    strategy_instance = StrategyRegistry.get_strategy(bot_data.strategy, bot_data.config)
    if not strategy_instance.validate_config():
        raise HTTPException(
            status_code=400,
            detail="Invalid strategy configuration"
        )
    
    # Check if bot name already exists for this user
    existing_bot = db.query(Bot).filter(
        Bot.name == bot_data.name,
        Bot.user_id == current_user.id
    ).first()
    
    if existing_bot:
        raise HTTPException(status_code=400, detail="Bot name already exists")
    
    # Check for duplicate bot (same strategy + same symbol) to prevent overtrading
    if bot_data.symbols:
        first_symbol = bot_data.symbols[0]
        # Use cast to text for JSONB array search (PostgreSQL compatible)
        from sqlalchemy import cast, String
        duplicate_bot = db.query(Bot).filter(
            Bot.user_id == current_user.id,
            Bot.strategy == bot_data.strategy,
            Bot.status == "RUNNING",  # Only block if actively RUNNING (not IDLE, PAUSED, ERROR)
            cast(Bot.symbols, String).contains(first_symbol)  # Search in JSONB array
        ).first()
        
        if duplicate_bot:
            raise HTTPException(
                status_code=400,
                detail=f"Bot with strategy '{bot_data.strategy}' already trading {first_symbol}. Use different strategy or symbol."
            )
    
    # Create new bot with user_id (REQUIRED)
    new_bot = Bot(
        id=uuid.uuid4(),
        user_id=current_user.id,
        name=bot_data.name,
        strategy=bot_data.strategy,
        status="IDLE",
        config=json.dumps(bot_data.config),
        symbols=json.dumps(bot_data.symbols),
        paper_trading=bot_data.paper_trading,
        risk_percent=bot_data.risk_percent,
        max_drawdown=bot_data.max_drawdown,
        is_live=False,
        total_trades=0,
        win_rate=0.0,
        total_pnl=0.0
    )
    
    db.add(new_bot)
    db.commit()
    db.refresh(new_bot)
    
    return {
        "message": f"Bot '{bot_data.name}' created successfully",
        "bot_id": new_bot.id,
        "bot": {
            "id": new_bot.id,
            "name": new_bot.name,
            "strategy": new_bot.strategy,
            "status": new_bot.status,
            "paper_trading": new_bot.paper_trading
        }
    }


@router.put("/{bot_id}")
async def update_bot(
    bot_id: str, 
    bot_data: BotUpdate, 
    db: Session = Depends(get_db),
    current_user: Optional[UserResponse] = Depends(get_optional_user)
):
    """Update bot configuration"""
    query = db.query(Bot).filter(Bot.id == bot_id)
    
    # Filter by user_id if authenticated
    if current_user:
        query = query.filter(Bot.user_id == current_user.id)
    
    bot = query.first()
    
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    # Don't allow updates while bot is active
    if bot.status == "ACTIVE":
        raise HTTPException(
            status_code=400,
            detail="Cannot update bot while it's active. Stop the bot first."
        )
    
    # Update fields
    if bot_data.name is not None:
        # Check if new name already exists for this user
        existing_query = db.query(Bot).filter(Bot.name == bot_data.name, Bot.id != bot_id)
        if current_user:
            existing_query = existing_query.filter(Bot.user_id == current_user.id)
        existing = existing_query.first()
        if existing:
            raise HTTPException(status_code=400, detail="Bot name already exists")
        bot.name = bot_data.name
    
    if bot_data.strategy is not None:
        if not StrategyRegistry.is_registered(bot_data.strategy):
            raise HTTPException(status_code=400, detail=f"Strategy '{bot_data.strategy}' not found")
        bot.strategy = bot_data.strategy
    
    if bot_data.config is not None:
        # Validate config with strategy
        strategy_name = bot_data.strategy if bot_data.strategy else bot.strategy
        strategy_instance = StrategyRegistry.get_strategy(strategy_name, bot_data.config)
        if not strategy_instance.validate_config():
            raise HTTPException(status_code=400, detail="Invalid strategy configuration")
        bot.config = json.dumps(bot_data.config)
    
    if bot_data.symbols is not None:
        bot.symbols = json.dumps(bot_data.symbols)
    
    if bot_data.paper_trading is not None:
        bot.paper_trading = bot_data.paper_trading
    
    if bot_data.risk_percent is not None:
        bot.risk_percent = bot_data.risk_percent
    
    if bot_data.max_drawdown is not None:
        bot.max_drawdown = bot_data.max_drawdown
    
    bot.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(bot)
    
    return {
        "message": f"Bot '{bot.name}' updated successfully",
        "bot_id": bot.id
    }


@router.delete("/{bot_id}")
async def delete_bot(
    bot_id: str, 
    db: Session = Depends(get_db),
    current_user: Optional[UserResponse] = Depends(get_optional_user)
):
    """Delete a bot and close its open trades at current market price"""
    query = db.query(Bot).filter(Bot.id == bot_id)
    
    # Filter by user_id if authenticated
    if current_user:
        query = query.filter(Bot.user_id == current_user.id)
    
    bot = query.first()
    
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    # Don't allow deletion while bot is active
    if bot.status == "ACTIVE":
        raise HTTPException(
            status_code=400,
            detail="Cannot delete bot while it's active. Stop the bot first."
        )
    
    bot_name = bot.name
    
    # === FIX Bug #7: Close open trades at current market price before deleting bot ===
    open_trades = db.query(Trade).filter(
        Trade.bot_id == bot_id,
        Trade.status == "OPEN"
    ).all()
    
    closed_count = 0
    closed_details = []
    
    if open_trades:
        # Get market data collector to fetch current prices
        from app.services.market_data import MarketDataCollector
        market_collector = MarketDataCollector()
        
        for trade in open_trades:
            try:
                # Fetch current market price for the symbol
                candles = await market_collector.get_candles(trade.symbol, timeframe="1h", limit=1)
                if candles and len(candles) > 0:
                    exit_price = float(candles[-1]['close'])
                else:
                    # Fallback: use entry price if price fetch fails
                    exit_price = float(trade.entry_price)
                
                # Close trade at current market price with real PnL calculation
                trade.status = "CLOSED"
                trade.exit_price = exit_price
                trade.exit_time = datetime.utcnow()
                
                # Calculate real PnL based on market price
                pnl = (exit_price - float(trade.entry_price)) * float(trade.quantity)
                pnl_percent = ((exit_price - float(trade.entry_price)) / float(trade.entry_price)) * 100 if float(trade.entry_price) > 0 else 0
                
                trade.pnl = pnl
                trade.pnl_percent = pnl_percent
                
                # Update portfolio with PnL (not proceeds!)
                # BUG FIX: Add only the PnL (gain/loss), not the full proceeds
                # When closing at exit_price:
                #   - Cash recovered = exit_price * quantity
                #   - Cash spent = entry_price * quantity  
                #   - Gain/Loss = PnL = (exit_price - entry_price) * quantity
                portfolio = db.query(Portfolio).filter(
                    Portfolio.user_id == bot.user_id
                ).first()
                
                if portfolio:
                    portfolio.cash_balance = float(portfolio.cash_balance) + float(pnl)
                    portfolio.total_pnl = float(portfolio.total_pnl or 0) + float(pnl)
                    db.add(portfolio)
                
                closed_count += 1
                closed_details.append({
                    "symbol": trade.symbol,
                    "quantity": float(trade.quantity),
                    "entry_price": float(trade.entry_price),
                    "exit_price": exit_price,
                    "pnl": float(pnl),
                    "pnl_percent": float(pnl_percent)
                })
                
                logger.info(f"🔄 Closed trade {trade.symbol}: Entry={float(trade.entry_price):.2f}, Exit={exit_price:.2f}, PnL={float(pnl):.2f} ({float(pnl_percent):.2f}%)")
                
            except Exception as e:
                logger.error(f"❌ Error closing trade {trade.symbol} for bot {bot_name}: {str(e)}")
                # Still close the trade in DB even if price fetch fails (use entry price)
                trade.status = "CLOSED"
                trade.exit_price = float(trade.entry_price)
                trade.exit_time = datetime.utcnow()
                trade.pnl = 0
                trade.pnl_percent = 0
                closed_count += 1
        
        # Persist all changes
        db.add_all(open_trades)
        db.commit()
        
        logger.info(f"✅ Closed {closed_count} orphan trades for bot {bot_name}")
    
    # Now delete the bot
    db.delete(bot)
    db.commit()
    
    return {
        "message": f"Bot '{bot_name}' deleted successfully",
        "closed_trades": closed_count,
        "trade_details": closed_details
    }
    open_trades = [t for t in trades if t.status == "OPEN"]
    closed_trades = [t for t in trades if t.status == "CLOSED"]
    
    total_pnl = sum([t.pnl or 0 for t in closed_trades])
    
    return {
        "id": bot.id,
        "name": bot.name,
        "strategy": bot.strategy,
        "status": bot.status,
        "is_live": bot.is_live,
        "total_trades": len(trades),
        "open_trades": len(open_trades),
        "closed_trades": len(closed_trades),
        "win_rate": bot.win_rate,
        "total_pnl": total_pnl,
        "max_drawdown": bot.max_drawdown,
        "risk_percent": bot.risk_percent,
        "created_at": bot.created_at.isoformat() if bot.created_at else None,
        "updated_at": bot.updated_at.isoformat() if bot.updated_at else None,
    }

@router.post("/{bot_id}/start")
async def start_bot(
    bot_id: str, 
    db: Session = Depends(get_db),
    current_user: Optional[UserResponse] = Depends(get_optional_user)
):
    """Start a bot - activates trading"""
    engine = get_bot_engine()
    
    query = db.query(Bot).filter(Bot.id == bot_id)
    if current_user:
        query = query.filter(Bot.user_id == current_user.id)
    
    bot = query.first()
    
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    bot.status = "RUNNING"
    bot.updated_at = datetime.utcnow()
    db.commit()
    
    # Activate bot in the engine
    if engine:
        try:
            await engine.activate_bot(str(bot.id))
        except Exception as e:
            logger.error(f"Failed to activate bot in engine: {e}")
    
    return {"message": f"Bot {bot.name} started", "status": "RUNNING"}

@router.post("/{bot_id}/pause")
async def pause_bot(
    bot_id: str, 
    db: Session = Depends(get_db),
    current_user: Optional[UserResponse] = Depends(get_optional_user)
):
    """Pause a bot"""
    query = db.query(Bot).filter(Bot.id == bot_id)
    if current_user:
        query = query.filter(Bot.user_id == current_user.id)
    
    bot = query.first()
    
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    bot.status = "PAUSED"
    bot.updated_at = datetime.utcnow()
    db.commit()
    
    # Deactivate bot in the engine
    engine = get_bot_engine()
    if engine:
        try:
            await engine.deactivate_bot(str(bot.id))
        except Exception as e:
            logger.error(f"Failed to deactivate bot in engine: {e}")
    
    return {"message": f"Bot {bot.name} paused", "status": "PAUSED"}

@router.post("/{bot_id}/stop")
async def stop_bot(
    bot_id: str, 
    db: Session = Depends(get_db),
    current_user: Optional[UserResponse] = Depends(get_optional_user)
):
    """Stop a bot - deactivates trading"""
    engine = get_bot_engine()
    
    query = db.query(Bot).filter(Bot.id == bot_id)
    if current_user:
        query = query.filter(Bot.user_id == current_user.id)
    
    bot = query.first()
    
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    bot.status = "IDLE"
    bot.updated_at = datetime.utcnow()
    db.commit()
    
    # Deactivate bot in the engine
    if engine:
        try:
            await engine.deactivate_bot(str(bot.id))
        except Exception as e:
            logger.error(f"Failed to deactivate bot in engine: {e}")
    
    return {"message": f"Bot {bot.name} stopped", "status": "IDLE"}

@router.get("/{bot_id}/performance")
async def get_bot_performance(bot_id: str, db: Session = Depends(get_db)):
    """Get bot performance metrics"""
    performance = db.query(StrategyPerformance).filter(
        StrategyPerformance.strategy_name == bot_id
    ).all()
    
    if not performance:
        raise HTTPException(status_code=404, detail="Performance data not found")
    
    latest = performance[-1] if performance else None
    
    return {
        "total_trades": latest.total_trades if latest else 0,
        "winning_trades": latest.winning_trades if latest else 0,
        "losing_trades": latest.losing_trades if latest else 0,
        "win_rate": latest.win_rate if latest else 0,
        "avg_win": latest.avg_win if latest else 0,
        "avg_loss": latest.avg_loss if latest else 0,
        "profit_factor": latest.profit_factor if latest else 0,
        "sharpe_ratio": latest.sharpe_ratio if latest else 0,
        "max_drawdown": latest.max_drawdown if latest else 0,
    }

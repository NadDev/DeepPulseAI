"""
Watchlist API Routes
Endpoints for managing user's crypto watchlist
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from app.db.database import get_db
from app.auth.supabase_auth import get_current_user, UserResponse
from app.models.database_models import WatchlistItem
from app.services import ai_bot_controller as ai_bot_controller_module
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/watchlist", tags=["Watchlist"])


# ============================================
# Helper Functions
# ============================================

def get_user_uuid(user_id) -> UUID:
    """
    Safely convert user_id to UUID
    Handles both string and UUID inputs
    """
    if isinstance(user_id, UUID):
        return user_id
    if isinstance(user_id, str):
        try:
            return UUID(user_id)
        except (ValueError, TypeError) as e:
            logger.error(f"❌ Invalid user_id format: {user_id} - {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid user ID format")
    raise HTTPException(status_code=400, detail="Invalid user ID format")


# ============================================
# Popular Crypto Symbols
# ============================================

POPULAR_SYMBOLS = [
    {"symbol": "BTC/USDT", "name": "Bitcoin", "logo": "₿"},
    {"symbol": "ETH/USDT", "name": "Ethereum", "logo": "Ξ"},
    {"symbol": "BNB/USDT", "name": "Binance Coin", "logo": "🔶"},
    {"symbol": "XRP/USDT", "name": "Ripple", "logo": "✕"},
    {"symbol": "SOL/USDT", "name": "Solana", "logo": "◎"},
    {"symbol": "ADA/USDT", "name": "Cardano", "logo": "₳"},
    {"symbol": "DOGE/USDT", "name": "Dogecoin", "logo": "🐕"},
    {"symbol": "DOT/USDT", "name": "Polkadot", "logo": "●"},
    {"symbol": "MATIC/USDT", "name": "Polygon", "logo": "⬡"},
    {"symbol": "LTC/USDT", "name": "Litecoin", "logo": "Ł"},
    {"symbol": "AVAX/USDT", "name": "Avalanche", "logo": "🔺"},
    {"symbol": "LINK/USDT", "name": "Chainlink", "logo": "⬡"},
    {"symbol": "UNI/USDT", "name": "Uniswap", "logo": "🦄"},
    {"symbol": "ATOM/USDT", "name": "Cosmos", "logo": "⚛"},
    {"symbol": "XLM/USDT", "name": "Stellar", "logo": "✦"},
    {"symbol": "ALGO/USDT", "name": "Algorand", "logo": "Ⱥ"},
    {"symbol": "NEAR/USDT", "name": "NEAR Protocol", "logo": "Ⓝ"},
    {"symbol": "FTM/USDT", "name": "Fantom", "logo": "👻"},
    {"symbol": "AAVE/USDT", "name": "Aave", "logo": "👻"},
    {"symbol": "CRO/USDT", "name": "Cronos", "logo": "🔷"},
]


# ============================================
# Pydantic Models
# ============================================

class WatchlistItemCreate(BaseModel):
    """Request to add a symbol to watchlist"""
    symbol: str
    notes: Optional[str] = None
    priority: int = 0
    watchlist_id: Optional[str] = None  # Ignored - for frontend compatibility
    
    @validator('symbol')
    def validate_symbol(cls, v):
        v = v.upper().strip()
        # Normalize to Binance format (BTCUSDT, not BTC/USDT)
        # Remove any slashes first
        v = v.replace('/', '')
        # Add USDT if missing
        if not v.endswith('USDT'):
            v = f"{v}USDT"
        return v
    
    @validator('priority', pre=True)
    def validate_priority(cls, v):
        """Convert string priority to integer"""
        if isinstance(v, str):
            priority_map = {
                'low': 0,
                'medium': 5,
                'high': 10,
                'critical': 15
            }
            return priority_map.get(v.lower(), 5)  # Default to medium (5)
        return v


class WatchlistItemUpdate(BaseModel):
    """Request to update a watchlist item"""
    is_active: Optional[bool] = None
    notes: Optional[str] = None
    priority: Optional[int] = None


class WatchlistItemResponse(BaseModel):
    """Response with watchlist item details"""
    id: str
    symbol: str
    base_currency: Optional[str]
    quote_currency: Optional[str]
    is_active: bool
    priority: int
    notes: Optional[str]
    created_at: str


class BulkAddRequest(BaseModel):
    """Request to add multiple symbols at once"""
    symbols: List[str]
    
    @validator('symbols')
    def validate_symbols(cls, v):
        # Normalize all symbols to Binance format (BTCUSDT, not BTC/USDT)
        normalized = []
        for s in v:
            s = s.upper().strip()
            # Remove any slashes
            s = s.replace('/', '')
            # Add USDT if missing
            if not s.endswith('USDT'):
                s = f"{s}USDT"
            normalized.append(s)
        return normalized


# ============================================
# Routes
# ============================================

@router.get("/popular")
async def get_popular_symbols(
    current_user: UserResponse = Depends(get_current_user)
):
    """Get list of popular crypto symbols"""
    return {
        "symbols": POPULAR_SYMBOLS,
        "count": len(POPULAR_SYMBOLS)
    }


@router.get("/", name="get_watchlist_with_slash")
@router.get("", name="get_watchlist_without_slash")
async def get_watchlist(
    active_only: bool = Query(False, description="Only return active items"),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """Get user's watchlist - returns as array for frontend compatibility"""
    logger.info(f"📋 [WATCHLIST] Fetching watchlist for user {current_user.id}")
    try:
        user_uuid = get_user_uuid(current_user.id)
        logger.info(f"📋 [WATCHLIST] User UUID: {user_uuid}")
        
        query = db.query(WatchlistItem).filter(
            WatchlistItem.user_id == user_uuid
        )
        
        if active_only:
            query = query.filter(WatchlistItem.is_active == True)
        
        items = query.order_by(WatchlistItem.priority.desc(), WatchlistItem.created_at).all()
        logger.info(f"📋 [WATCHLIST] Found {len(items)} items")
        
        # Format items for response
        formatted_items = []
        for item in items:
            logger.info(f"📋 [WATCHLIST] Item: {item.symbol} (active={item.is_active})")
            
            # Extract base_currency from symbol if empty
            base_currency = item.base_currency
            if not base_currency and item.symbol:
                # Remove 'USDT' suffix to get base currency (e.g., BTCUSDT -> BTC)
                base_currency = item.symbol.replace('USDT', '').replace('/USDT', '').strip()
            
            quote_currency = item.quote_currency or 'USDT'
            
            formatted_items.append({
                "id": str(item.id),
                "symbol": item.symbol,
                "base_currency": base_currency,
                "quote_currency": quote_currency,
                "is_active": item.is_active,
                "priority": item.priority,
                "notes": item.notes,
                "created_at": item.created_at.isoformat() if item.created_at else None
            })
        
        # Return as single watchlist in array format (frontend expects array)
        response = [{
            "id": "default",
            "name": "Ma Watchlist",
            "is_default": True,
            "items": formatted_items,
            "item_count": len(formatted_items),
            "active_count": sum(1 for i in formatted_items if i["is_active"])
        }]
        
        logger.info(f"✅ [WATCHLIST] Returning {len(formatted_items)} symbols")
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching watchlist for user {current_user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch watchlist: {str(e)}")


@router.post("/", name="add_to_watchlist_with_slash")
@router.post("", name="add_to_watchlist_without_slash")
@router.post("/add")  # Alias for frontend compatibility
async def add_to_watchlist(
    request: WatchlistItemCreate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """Add a symbol to watchlist"""
    try:
        user_uuid = get_user_uuid(current_user.id)
        
        # Check if already exists
        existing = db.query(WatchlistItem).filter(
            WatchlistItem.user_id == user_uuid,
            WatchlistItem.symbol == request.symbol
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Symbol {request.symbol} is already in your watchlist"
            )
        
        # Parse symbol
        parts = request.symbol.split('/')
        base_currency = parts[0] if len(parts) > 0 else None
        quote_currency = parts[1] if len(parts) > 1 else None
        
        # Create item
        item = WatchlistItem(
            user_id=user_uuid,
            symbol=request.symbol,
            base_currency=base_currency,
            quote_currency=quote_currency,
            notes=request.notes,
            priority=request.priority,
            is_active=True
        )
        
        db.add(item)
        db.commit()
        db.refresh(item)
        
        # Sync with AI config
        await _sync_watchlist_to_ai(db, str(current_user.id))
        
        logger.info(f"✅ Added {request.symbol} to watchlist for user {current_user.id}")
        
        return {
            "status": "success",
            "message": f"{request.symbol} added to watchlist",
            "id": str(item.id),
            "symbol": item.symbol
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error adding symbol to watchlist: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to add symbol: {str(e)}")


@router.post("/bulk")
async def bulk_add_to_watchlist(
    request: BulkAddRequest,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """Add multiple symbols to watchlist at once"""
    try:
        user_uuid = get_user_uuid(current_user.id)
        logger.info(f"📥 Bulk add request: {request.symbols} for user {current_user.id}")
        added = []
        skipped = []
        
        for symbol in request.symbols:
            # Check if already exists for THIS user
            existing = db.query(WatchlistItem).filter(
                WatchlistItem.user_id == user_uuid,
                WatchlistItem.symbol == symbol
            ).first()
            
            if existing:
                skipped.append(symbol)
                logger.debug(f"⏭️ Skipped {symbol} - already exists for user")
                continue
            
            # Parse symbol
            parts = symbol.split('/')
            base_currency = parts[0] if len(parts) > 0 else None
            quote_currency = parts[1] if len(parts) > 1 else None
            
            # Create item with correct user_id
            item = WatchlistItem(
                user_id=user_uuid,
                symbol=symbol,
                base_currency=base_currency,
                quote_currency=quote_currency,
                is_active=True
            )
            db.add(item)
            added.append(symbol)
            logger.info(f"➕ Added {symbol} for user {current_user.id}")
        
        db.commit()
        
        # Sync with AI config
        await _sync_watchlist_to_ai(db, str(current_user.id))
        
        logger.info(f"✅ Bulk result: added={len(added)}, skipped={len(skipped)}")
        
        return {
            "status": "success",
            "added": added,
            "skipped": skipped,
            "added_count": len(added),
            "skipped_count": len(skipped)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in bulk add: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to bulk add symbols: {str(e)}")


@router.put("/{item_id}")
async def update_watchlist_item(
    item_id: str,
    request: WatchlistItemUpdate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """Update a watchlist item"""
    item = db.query(WatchlistItem).filter(
        WatchlistItem.id == item_id,
        WatchlistItem.user_id == UUID(current_user.id)
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Watchlist item not found")
    
    # Update fields
    if request.is_active is not None:
        item.is_active = request.is_active
    if request.notes is not None:
        item.notes = request.notes
    if request.priority is not None:
        item.priority = request.priority
    
    db.commit()
    
    # Sync with AI config if active status changed
    if request.is_active is not None:
        await _sync_watchlist_to_ai(db, current_user.id)
    
    return {
        "status": "success",
        "message": f"{item.symbol} updated"
    }


@router.delete("/{item_id}")
async def remove_from_watchlist(
    item_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """Remove a symbol from watchlist"""
    item = db.query(WatchlistItem).filter(
        WatchlistItem.id == item_id,
        WatchlistItem.user_id == UUID(current_user.id)
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Watchlist item not found")
    
    symbol = item.symbol
    db.delete(item)
    db.commit()
    
    # Sync with AI config
    await _sync_watchlist_to_ai(db, current_user.id)
    
    logger.info(f"🗑️ Removed {symbol} from watchlist")
    
    return {
        "status": "success",
        "message": f"{symbol} removed from watchlist"
    }


@router.post("/{item_id}/toggle")
async def toggle_watchlist_item(
    item_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """Toggle a watchlist item's active status"""
    item = db.query(WatchlistItem).filter(
        WatchlistItem.id == item_id,
        WatchlistItem.user_id == UUID(current_user.id)
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Watchlist item not found")
    
    item.is_active = not item.is_active
    db.commit()
    
    # Sync with AI config
    await _sync_watchlist_to_ai(db, current_user.id)
    
    return {
        "status": "success",
        "symbol": item.symbol,
        "is_active": item.is_active,
        "message": f"{item.symbol} {'activated' if item.is_active else 'deactivated'}"
    }


@router.get("/symbols")
async def get_watchlist_symbols(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """Get just the active symbol list (for AI config sync)"""
    items = db.query(WatchlistItem).filter(
        WatchlistItem.user_id == UUID(current_user.id),
        WatchlistItem.is_active == True
    ).order_by(WatchlistItem.priority.desc()).all()
    
    symbols = [item.symbol for item in items]
    
    return {
        "symbols": symbols,
        "count": len(symbols)
    }


# ============================================
# Helper Functions
# ============================================

async def _sync_watchlist_to_ai(db: Session, user_id: str):
    """Sync active watchlist symbols to AI Bot Controller config"""
    try:
        # Get active symbols
        items = db.query(WatchlistItem).filter(
            WatchlistItem.user_id == UUID(user_id),
            WatchlistItem.is_active == True
        ).order_by(WatchlistItem.priority.desc()).all()
        
        symbols = [item.symbol for item in items]
        
        # Update AI Bot Controller config
        controller = ai_bot_controller_module.ai_bot_controller
        if controller:
            controller.config["watchlist_symbols"] = symbols
            logger.info(f"🔄 Synced {len(symbols)} symbols to AI config")
        else:
            logger.warning("⚠️ AI Bot Controller not available for sync")
            
    except Exception as e:
        logger.error(f"Failed to sync watchlist to AI: {e}")

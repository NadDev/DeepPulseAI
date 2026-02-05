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
from app.auth.local_auth import get_current_user, UserResponse
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
    include_recommendations: bool = Query(False, description="Include pending recommendations"),
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
            logger.info(f"📋 [WATCHLIST] base_currency from DB: '{item.base_currency}' (type: {type(item.base_currency)})")
            
            # Extract base_currency from symbol if empty
            base_currency = item.base_currency
            if not base_currency and item.symbol:
                # Remove 'USDT' suffix to get base currency (e.g., BTCUSDT -> BTC)
                base_currency = item.symbol.replace('USDT', '').replace('/USDT', '').strip()
                logger.info(f"📋 [WATCHLIST] Extracted base_currency from symbol: '{base_currency}'")
            
            quote_currency = item.quote_currency or 'USDT'
            logger.info(f"📋 [WATCHLIST] Final: symbol={item.symbol}, base={base_currency}, quote={quote_currency}")
            
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
        
        # Build base response
        response = [{
            "id": "default",
            "name": "Ma Watchlist",
            "is_default": True,
            "items": formatted_items,
            "item_count": len(formatted_items),
            "active_count": sum(1 for i in formatted_items if i["is_active"])
        }]
        
        # Add pending recommendations if requested
        if include_recommendations:
            from app.services.watchlist_recommendation_engine import get_recommendation_engine
            engine = get_recommendation_engine()
            
            recommendations = engine.get_user_pending_recommendations(db, str(user_uuid), limit=10)
            
            response[0]["pending_recommendations"] = recommendations
            response[0]["recommendation_count"] = len(recommendations)
            
            logger.info(f"📋 [WATCHLIST] Added {len(recommendations)} pending recommendations")
        
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


# ============================================
# Crypto Recommendations Routes (Feature: RecommendationCrypto)
# ============================================

class RecommendationResponse(BaseModel):
    """Response model for recommendation"""
    id: str
    symbol: str
    score: float
    action: str
    reasoning: Optional[str]
    created_at: str


class RecommendationAcceptRequest(BaseModel):
    """Request to accept a recommendation"""
    add_to_watchlist: bool = True


@router.get("/recommendations/pending")
async def get_pending_recommendations(
    limit: int = Query(50, le=100),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Get global pending recommendations, filtered by what the user already has.
    """
    try:
        user_uuid = get_user_uuid(current_user.id)
        SYSTEM_USER_ID = "00000000-0000-0000-0000-000000000000"
        
        # 1. Get user's existing watchlist symbols (BOTH active and inactive)
        # We need inactive ones too to show REMOVE recommendations for items they've disabled
        existing_items = db.query(WatchlistItem.symbol).filter(
            WatchlistItem.user_id == user_uuid
        ).all()
        user_symbols = {item.symbol for item in existing_items}
        
        # 2. Get GLOBAL recommendations (from System User)
        from app.services.watchlist_recommendation_engine import get_recommendation_engine
        from app.db.database import SessionLocal
        engine = get_recommendation_engine(SessionLocal)
        
        # We fetch MORE than the limit to allow for filtering
        raw_recommendations = engine.get_user_pending_recommendations(
            db, SYSTEM_USER_ID, limit=limit * 2
        )
        
        # 3. Filter out what user already has
        # Also filter out REMOVE actions if the user doesn't have the symbol (doesn't make sense to recommend removing something they don't have)
        filtered_recommendations = []
        for rec in raw_recommendations:
            symbol = rec['symbol']
            action = rec['action']
            
            # If user has the symbol, we skip ADD recommendations (already added)
            # If user does NOT have the symbol, we skip REMOVE recommendations (nothing to remove)
            
            if symbol in user_symbols:
                if action == 'REMOVE':
                    filtered_recommendations.append(rec)
            else:
                if action == 'ADD':
                    filtered_recommendations.append(rec)
        
        # Apply limit after filtering
        final_recommendations = filtered_recommendations[:limit]
        
        logger.info(f"[RECOMMENDATION] User {user_uuid}: {len(final_recommendations)} global recs (filtered from {len(raw_recommendations)})")
        
        return {
            "recommendations": final_recommendations,
            "count": len(final_recommendations),
            "date": datetime.now().date().isoformat()
        }
        
    except Exception as e:
        logger.error(f"[RECOMMENDATION] Error fetching pending: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommendations/{recommendation_id}/accept")
async def accept_recommendation(
    recommendation_id: str,
    request: RecommendationAcceptRequest,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Accept a recommendation.
    Optionally adds the symbol to the user's watchlist.
    """
    try:
        user_uuid = get_user_uuid(current_user.id)
        SYSTEM_USER_ID = "00000000-0000-0000-0000-000000000000"
        
        # Get recommendation (allowing Global OR User-specific)
        from sqlalchemy import text
        result = db.execute(text("""
            SELECT symbol, action, user_id FROM watchlist_recommendations
            WHERE id = :id AND (user_id = :user_id OR user_id = :system_user_id)
        """), {
            "id": recommendation_id, 
            "user_id": str(user_uuid),
            "system_user_id": SYSTEM_USER_ID
        })
        
        rec = result.fetchone()
        
        if not rec:
            raise HTTPException(status_code=404, detail="Recommendation not found")
        
        symbol = rec[0]
        action = rec[1]
        rec_owner_id = str(rec[2])
        
        # Mark as accepted ONLY if owned by user
        # (Global recs stay available for others)
        if rec_owner_id == str(user_uuid):
            db.execute(text("""
                UPDATE watchlist_recommendations
                SET accepted = true, accepted_at = NOW()
                WHERE id = :id
            """), {"id": recommendation_id})
        
        # Handle action: ADD (add to watchlist) or REMOVE (deactivate from watchlist)
        if request.add_to_watchlist:
            if action == "ADD":
                # Add to watchlist if requested and action is ADD
                existing = db.query(WatchlistItem).filter(
                    WatchlistItem.user_id == user_uuid,
                    WatchlistItem.symbol == symbol
                ).first()
                
                if not existing:
                    # Normalize to Binance format (BTCUSDT, not BTC/USDT)
                    normalized_symbol = symbol.upper().strip()
                    normalized_symbol = normalized_symbol.replace('/', '')
                    if not normalized_symbol.endswith('USDT'):
                        normalized_symbol = f"{normalized_symbol}USDT"
                    
                    # Extract base currency from normalized symbol
                    base_currency = normalized_symbol.replace('USDT', '').replace('/USDT', '').strip()
                    
                    try:
                        new_item = WatchlistItem(
                            user_id=user_uuid,
                            symbol=normalized_symbol,
                            base_currency=base_currency,
                            quote_currency='USDT',
                            is_active=True,
                            priority=5,
                            notes=f"Added from recommendation"
                        )
                        db.add(new_item)
                        logger.info(f"[RECOMMENDATION] ✅ Added {normalized_symbol} to watchlist for user {user_uuid}")
                    except Exception as e:
                        logger.error(f"[RECOMMENDATION] ❌ Failed to add {symbol} to watchlist: {e}")
                        db.rollback()
                        raise
                else:
                    # Item exists but might be inactive, reactivate it
                    if not existing.is_active:
                        existing.is_active = True
                        logger.info(f"[RECOMMENDATION] ✅ Reactivated {symbol} in watchlist for user {user_uuid}")
            
            elif action == "REMOVE":
                # Remove/deactivate from watchlist if action is REMOVE
                existing = db.query(WatchlistItem).filter(
                    WatchlistItem.user_id == user_uuid,
                    WatchlistItem.symbol == symbol
                ).first()
                
                if existing:
                    existing.is_active = False  # Deactivate instead of delete
                    logger.info(f"[RECOMMENDATION] ✅ Deactivated {symbol} from watchlist for user {user_uuid}")
        
        
        db.commit()
        
        logger.info(f"[RECOMMENDATION] User {user_uuid} accepted {symbol} ({action})")
        
        return {
            "success": True,
            "message": f"Recommendation accepted",
            "symbol": symbol,
            "action": action,
            "applied": request.add_to_watchlist
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[RECOMMENDATION] Error accepting: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommendations/{recommendation_id}/reject")
async def reject_recommendation(
    recommendation_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Reject a recommendation.
    Marks it as not accepted without adding to watchlist.
    """
    try:
        user_uuid = get_user_uuid(current_user.id)
        
        # Check if exists
        from sqlalchemy import text
        result = db.execute(text("""
            SELECT symbol FROM watchlist_recommendations
            WHERE id = :id AND user_id = :user_id
        """), {"id": recommendation_id, "user_id": str(user_uuid)})
        
        rec = result.fetchone()
        
        if not rec:
            raise HTTPException(status_code=404, detail="Recommendation not found")
        
        symbol = rec[0]
        
        # Mark as rejected
        db.execute(text("""
            UPDATE watchlist_recommendations
            SET accepted = false, accepted_at = NOW()
            WHERE id = :id
        """), {"id": recommendation_id})
        
        db.commit()
        
        logger.info(f"[RECOMMENDATION] User {user_uuid} rejected {symbol}")
        
        return {
            "success": True,
            "message": f"Recommendation rejected",
            "symbol": symbol
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[RECOMMENDATION] Error rejecting: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommendations/history")
async def get_recommendation_history(
    status: Optional[str] = Query(None, regex="^(accepted|rejected|all)$"),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Get recommendation history with pagination.
    
    Args:
        status: Filter by status (accepted, rejected, or all)
        limit: Number of results per page
        offset: Pagination offset
    """
    try:
        user_uuid = get_user_uuid(current_user.id)
        
        from sqlalchemy import text
        
        # Build query based on status filter
        where_clause = "WHERE user_id = :user_id AND accepted IS NOT NULL"
        if status == "accepted":
            where_clause += " AND accepted = true"
        elif status == "rejected":
            where_clause += " AND accepted = false"
        
        # Get total count
        count_result = db.execute(text(f"""
            SELECT COUNT(*) FROM watchlist_recommendations
            {where_clause}
        """), {"user_id": str(user_uuid)})
        
        total_count = count_result.fetchone()[0]
        
        # Get paginated results
        result = db.execute(text(f"""
            SELECT id, symbol, score, action, reasoning, accepted, accepted_at, created_at
            FROM watchlist_recommendations
            {where_clause}
            ORDER BY accepted_at DESC
            LIMIT :limit OFFSET :offset
        """), {"user_id": str(user_uuid), "limit": limit, "offset": offset})
        
        history = [
            {
                "id": str(row[0]),
                "symbol": row[1],
                "score": row[2],
                "action": row[3],
                "reasoning": row[4],
                "accepted": row[5],
                "accepted_at": row[6].isoformat() if row[6] else None,
                "created_at": row[7].isoformat() if row[7] else None
            }
            for row in result.fetchall()
        ]
        
        logger.info(f"[RECOMMENDATION] History for user {user_uuid}: {len(history)} items")
        
        return {
            "history": history,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total_count
        }
        
    except Exception as e:
        logger.error(f"[RECOMMENDATION] Error fetching history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Manual Trigger Endpoint (For Testing)
# ============================================

@router.post("/recommendations/generate-now")
async def generate_recommendations_now(
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manually trigger recommendation generation for the current user
    Useful for testing without waiting for scheduled time
    
    Returns the number of recommendations generated
    """
    try:
        user_uuid = get_user_uuid(current_user.id)
        logger.info(f"📊 [TRIGGER] Manual recommendation generation requested by {user_uuid}")
        
        # Import here to avoid circular imports
        from app.services.watchlist_recommendation_engine import get_recommendation_engine
        from app.db.database import SessionLocal
        
        # Get the engine with proper session factory
        engine = get_recommendation_engine(SessionLocal)
        
        # Generate recommendations for this user
        recommendations = engine.generate_recommendations(user_id=str(user_uuid))
        
        # Save to database
        saved_count = engine.save_recommendations(db, str(user_uuid), recommendations)
        
        logger.info(f"✅ [TRIGGER] Generated {len(recommendations)} recommendations for user {user_uuid}")
        logger.info(f"💾 [TRIGGER] Saved {saved_count} recommendations to database")
        
        return {
            "status": "success",
            "user_id": str(user_uuid),
            "count": len(recommendations),
            "saved": saved_count,
            "recommendations": [
                {
                    "symbol": r.symbol,
                    "score": r.score,
                    "action": r.action,
                    "current_price": r.current_price,
                    "price_change_7d": r.price_change_7d,
                    "reasoning": r.reasoning[:200] if r.reasoning else None
                }
                for r in recommendations
            ],
            "message": f"Generated {len(recommendations)} recommendations ({saved_count} saved to DB)"
        }
        
    except Exception as e:
        logger.error(f"❌ [TRIGGER] Error generating recommendations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating recommendations: {str(e)}")

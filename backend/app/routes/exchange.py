"""
Exchange Configuration API Routes
Endpoints for managing exchange/broker configurations
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.db.database import get_db
from app.auth.local_auth import get_current_user, UserResponse
from app.models.database_models import ExchangeConfig
from app.services.crypto_service import get_crypto_service
import logging
import json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/exchange", tags=["Exchange"])


# ============================================
# Supported Exchanges Configuration
# ============================================

SUPPORTED_EXCHANGES = {
    "binance": {
        "name": "Binance",
        "logo": "binance.png",
        "has_testnet": True,
        "requires_passphrase": False,
        "testnet_url": "https://testnet.binance.vision",
        "api_docs": "https://binance-docs.github.io/apidocs/spot/en/",
        "supported_features": ["spot", "futures", "margin"],
        "default_quote": "USDT"
    },
    "kraken": {
        "name": "Kraken",
        "logo": "kraken.png",
        "has_testnet": False,
        "requires_passphrase": False,
        "api_docs": "https://docs.kraken.com/rest/",
        "supported_features": ["spot", "margin"],
        "default_quote": "USD"
    },
    "coinbase": {
        "name": "Coinbase Pro",
        "logo": "coinbase.png",
        "has_testnet": True,
        "requires_passphrase": True,
        "testnet_url": "https://api-public.sandbox.exchange.coinbase.com",
        "api_docs": "https://docs.cdp.coinbase.com/",
        "supported_features": ["spot"],
        "default_quote": "USD"
    },
    "kucoin": {
        "name": "KuCoin",
        "logo": "kucoin.png",
        "has_testnet": True,
        "requires_passphrase": True,
        "testnet_url": "https://openapi-sandbox.kucoin.com",
        "api_docs": "https://docs.kucoin.com/",
        "supported_features": ["spot", "futures", "margin"],
        "default_quote": "USDT"
    },
    "bybit": {
        "name": "Bybit",
        "logo": "bybit.png",
        "has_testnet": True,
        "requires_passphrase": False,
        "testnet_url": "https://api-testnet.bybit.com",
        "api_docs": "https://bybit-exchange.github.io/docs/",
        "supported_features": ["spot", "futures"],
        "default_quote": "USDT"
    },
    "okx": {
        "name": "OKX",
        "logo": "okx.png",
        "has_testnet": True,
        "requires_passphrase": True,
        "testnet_url": "https://www.okx.com/api/v5/",
        "api_docs": "https://www.okx.com/docs-v5/en/",
        "supported_features": ["spot", "futures", "margin"],
        "default_quote": "USDT"
    }
}


# ============================================
# Pydantic Models
# ============================================

class ExchangeConfigCreate(BaseModel):
    """Request to create/update exchange configuration"""
    exchange: str
    name: Optional[str] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    passphrase: Optional[str] = None
    paper_trading: bool = True
    use_testnet: bool = True
    max_trade_size: float = 1000.0
    max_daily_trades: int = 50
    allowed_symbols: Optional[List[str]] = None
    is_default: bool = False
    
    @validator('exchange')
    def validate_exchange(cls, v):
        if v.lower() not in SUPPORTED_EXCHANGES:
            raise ValueError(f"Unsupported exchange: {v}. Supported: {list(SUPPORTED_EXCHANGES.keys())}")
        return v.lower()
    
    @validator('api_key', 'api_secret', pre=True, always=True)
    def validate_credentials(cls, v):
        # None or empty string = keep existing (for updates)
        if v is None or v == '':
            return None
        if len(v.strip()) < 10:
            raise ValueError("API key/secret must be at least 10 characters")
        return v.strip()


class ExchangeConfigResponse(BaseModel):
    """Response with exchange configuration (masked keys)"""
    id: str
    exchange: str
    name: Optional[str]
    api_key_masked: str
    has_passphrase: bool
    is_active: bool
    is_default: bool
    paper_trading: bool
    use_testnet: bool
    max_trade_size: float
    max_daily_trades: int
    allowed_symbols: Optional[List[str]]
    connection_status: str
    last_connection_test: Optional[str]
    connection_error: Optional[str]
    created_at: str
    updated_at: str


class TestConnectionRequest(BaseModel):
    """Request to test exchange connection"""
    exchange_id: Optional[str] = None  # Test existing config
    # Or provide credentials directly (for testing before saving)
    exchange: Optional[str] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    passphrase: Optional[str] = None
    use_testnet: bool = True


# ============================================
# Routes
# ============================================

@router.get("/supported")
async def get_supported_exchanges(
    current_user: UserResponse = Depends(get_current_user)
):
    """Get list of supported exchanges with their features"""
    return {
        "exchanges": SUPPORTED_EXCHANGES,
        "count": len(SUPPORTED_EXCHANGES)
    }


@router.get("/configs")
async def get_exchange_configs(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """Get all exchange configurations for current user"""
    crypto = get_crypto_service()
    
    configs = db.query(ExchangeConfig).filter(
        ExchangeConfig.user_id == current_user.id
    ).all()
    
    result = []
    for config in configs:
        # Decrypt API key just to mask it
        try:
            api_key = crypto.decrypt(config.api_key_encrypted)
            api_key_masked = crypto.mask_key(api_key)
        except Exception:
            api_key_masked = "***ERROR***"
        
        # Parse allowed symbols
        allowed_symbols = None
        if config.allowed_symbols:
            try:
                allowed_symbols = json.loads(config.allowed_symbols)
            except:
                allowed_symbols = None
        
        result.append({
            "id": str(config.id),
            "exchange": config.exchange,
            "name": config.name,
            "api_key_masked": api_key_masked,
            "has_passphrase": config.passphrase_encrypted is not None,
            "is_active": config.is_active,
            "is_default": config.is_default,
            "paper_trading": config.paper_trading,
            "use_testnet": config.use_testnet,
            "max_trade_size": config.max_trade_size,
            "max_daily_trades": config.max_daily_trades,
            "allowed_symbols": allowed_symbols,
            "connection_status": config.connection_status,
            "last_connection_test": config.last_connection_test.isoformat() if config.last_connection_test else None,
            "connection_error": config.connection_error,
            "created_at": config.created_at.isoformat() if config.created_at else None,
            "updated_at": config.updated_at.isoformat() if config.updated_at else None
        })
    
    return {
        "configs": result,
        "count": len(result)
    }


@router.post("/configs")
async def create_exchange_config(
    request: ExchangeConfigCreate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """Create a new exchange configuration"""
    crypto = get_crypto_service()
    
    if not crypto.is_initialized():
        raise HTTPException(status_code=500, detail="Encryption service not available")
    
    # Check if exchange already configured for user
    existing = db.query(ExchangeConfig).filter(
        ExchangeConfig.user_id == current_user.id,
        ExchangeConfig.exchange == request.exchange
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Exchange {request.exchange} already configured. Use PUT to update."
        )
    
    # API key and secret are REQUIRED for creation
    if not request.api_key or not request.api_secret:
        raise HTTPException(
            status_code=400,
            detail="API key and secret are required when creating a new exchange config"
        )
    
    # Check if passphrase required
    exchange_info = SUPPORTED_EXCHANGES.get(request.exchange)
    if exchange_info and exchange_info.get("requires_passphrase") and not request.passphrase:
        raise HTTPException(
            status_code=400,
            detail=f"{request.exchange} requires a passphrase"
        )
    
    try:
        # Encrypt credentials
        api_key_encrypted = crypto.encrypt(request.api_key)
        api_secret_encrypted = crypto.encrypt(request.api_secret)
        passphrase_encrypted = crypto.encrypt(request.passphrase) if request.passphrase else None
        
        # If setting as default, unset other defaults
        if request.is_default:
            db.query(ExchangeConfig).filter(
                ExchangeConfig.user_id == current_user.id,
                ExchangeConfig.is_default == True
            ).update({"is_default": False})
        
        # Create config
        config = ExchangeConfig(
            user_id=current_user.id,
            exchange=request.exchange,
            name=request.name or SUPPORTED_EXCHANGES[request.exchange]["name"],
            api_key_encrypted=api_key_encrypted,
            api_secret_encrypted=api_secret_encrypted,
            passphrase_encrypted=passphrase_encrypted,
            paper_trading=request.paper_trading,
            use_testnet=request.use_testnet,
            max_trade_size=request.max_trade_size,
            max_daily_trades=request.max_daily_trades,
            allowed_symbols=json.dumps(request.allowed_symbols) if request.allowed_symbols else None,
            is_default=request.is_default,
            is_active=True,
            connection_status="untested"
        )
        
        db.add(config)
        db.commit()
        db.refresh(config)
        
        logger.info(f"✅ Exchange config created: {request.exchange} for user {current_user.id}")
        
        # === AUTO-SYNC PORTFOLIO WITH BROKER ===
        sync_result = None
        try:
            from app.services.portfolio_sync_service import PortfolioSyncService
            sync_service = PortfolioSyncService()
            sync_success = await sync_service.sync_user_portfolio(str(current_user.id), db)
            if sync_success:
                logger.info(f"✅ Portfolio auto-synced after broker creation")
                sync_result = "synced"
            else:
                logger.warning(f"⚠️ Portfolio auto-sync failed after broker creation")
                sync_result = "sync_failed"
        except Exception as sync_err:
            logger.error(f"❌ Portfolio auto-sync error: {sync_err}")
            sync_result = "sync_error"
        
        return {
            "status": "success",
            "message": f"Exchange {request.exchange} configured successfully",
            "id": str(config.id),
            "exchange": config.exchange,
            "portfolio_sync": sync_result
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create exchange config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/configs/{config_id}")
async def update_exchange_config(
    config_id: str,
    request: ExchangeConfigCreate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """Update an existing exchange configuration"""
    crypto = get_crypto_service()
    
    config = db.query(ExchangeConfig).filter(
        ExchangeConfig.id == config_id,
        ExchangeConfig.user_id == current_user.id
    ).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="Exchange config not found")
    
    try:
        # Update encrypted credentials (ONLY if provided - editing preserves existing secrets)
        if request.api_key:  # Only update if a new key is provided
            config.api_key_encrypted = crypto.encrypt(request.api_key)
        if request.api_secret:  # Only update if a new secret is provided
            config.api_secret_encrypted = crypto.encrypt(request.api_secret)
        if request.passphrase:  # Only update if a new passphrase is provided
            config.passphrase_encrypted = crypto.encrypt(request.passphrase)
        
        # Update other fields
        config.name = request.name or config.name
        config.paper_trading = request.paper_trading
        config.use_testnet = request.use_testnet
        config.max_trade_size = request.max_trade_size
        config.max_daily_trades = request.max_daily_trades
        config.allowed_symbols = json.dumps(request.allowed_symbols) if request.allowed_symbols else None
        config.connection_status = "untested"  # Reset status after update
        
        # Handle default
        if request.is_default and not config.is_default:
            db.query(ExchangeConfig).filter(
                ExchangeConfig.user_id == current_user.id,
                ExchangeConfig.is_default == True
            ).update({"is_default": False})
            config.is_default = True
        
        db.commit()
        
        logger.info(f"✅ Exchange config updated: {config.exchange}")
        
        # === AUTO-SYNC PORTFOLIO WITH BROKER ===
        sync_result = None
        try:
            from app.services.portfolio_sync_service import PortfolioSyncService
            sync_service = PortfolioSyncService()
            sync_success = await sync_service.sync_user_portfolio(str(current_user.id), db)
            if sync_success:
                logger.info(f"✅ Portfolio auto-synced after broker update")
                sync_result = "synced"
            else:
                logger.warning(f"⚠️ Portfolio auto-sync failed after broker update")
                sync_result = "sync_failed"
        except Exception as sync_err:
            logger.error(f"❌ Portfolio auto-sync error: {sync_err}")
            sync_result = "sync_error"
        
        return {
            "status": "success",
            "message": f"Exchange {config.exchange} updated successfully",
            "portfolio_sync": sync_result
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update exchange config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/configs/{config_id}")
async def delete_exchange_config(
    config_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """Delete an exchange configuration"""
    config = db.query(ExchangeConfig).filter(
        ExchangeConfig.id == config_id,
        ExchangeConfig.user_id == current_user.id
    ).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="Exchange config not found")
    
    exchange_name = config.exchange
    db.delete(config)
    db.commit()
    
    logger.info(f"🗑️ Exchange config deleted: {exchange_name}")
    
    return {
        "status": "success",
        "message": f"Exchange {exchange_name} configuration deleted"
    }


@router.post("/test-connection")
async def test_exchange_connection(
    request: TestConnectionRequest,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Test connection to an exchange by calling get_account_balance() via broker.
    
    This is a REAL connection test that validates:
    1. API credentials are valid
    2. Exchange API is accessible  
    3. Account balance can be retrieved
    """
    from app.brokers import BrokerFactory
    
    crypto = get_crypto_service()
    config = None
    
    logger.info(f"🔍 TEST-CONNECTION request: exchange_id={request.exchange_id}, paper_trading={getattr(request, 'paper_trading', 'NOT SET')}")
    
    # === 1. LOAD CREDENTIALS ===
    
    # Either use existing config or provided credentials
    if request.exchange_id:
        logger.info(f"📋 Loading config from exchange_id: {request.exchange_id}")
        config = db.query(ExchangeConfig).filter(
            ExchangeConfig.id == request.exchange_id,
            ExchangeConfig.user_id == current_user.id
        ).first()
        
        if not config:
            logger.error(f"❌ Config NOT FOUND for ID {request.exchange_id}")
            raise HTTPException(status_code=404, detail="Exchange config not found")
        
        logger.info(f"✅ Config found: exchange={config.exchange}, paper_trading={config.paper_trading}, testnet={config.use_testnet}")
        
        # Create broker from config
        try:
            logger.info(f"🔄 Creating BrokerFactory for {config.exchange}...")
            broker = BrokerFactory.create(config, db)
            logger.info(f"✅ BrokerFactory.create() succeeded: {broker.__class__.__name__}")
            exchange = config.exchange
            use_testnet = config.use_testnet
        except Exception as e:
            logger.error(f"❌ BrokerFactory.create() FAILED: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to create broker: {str(e)}")
    
    elif request.exchange and request.api_key and request.api_secret:
        # Create temporary config for testing
        from app.models.database_models import ExchangeConfig as ExchangeConfigModel
        from uuid import uuid4
        
        temp_config = ExchangeConfigModel(
            id=uuid4(),
            user_id=current_user.id,
            exchange=request.exchange.lower(),
            api_key_encrypted=crypto.encrypt(request.api_key),
            api_secret_encrypted=crypto.encrypt(request.api_secret),
            passphrase_encrypted=crypto.encrypt(request.passphrase) if request.passphrase else None,
            use_testnet=request.use_testnet,
            paper_trading=False  # Test real connection
        )
        
        try:
            broker = BrokerFactory.create(temp_config, db)
            exchange = temp_config.exchange
            use_testnet = temp_config.use_testnet
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to create broker: {e}")
    
    else:
        raise HTTPException(status_code=400, detail="Provide exchange_id or full credentials")
    
    # === 2. TEST CONNECTION VIA BROKER ===
    
    try:
        logger.info(f"� Testing {exchange} connection for user {current_user.id} (testnet={use_testnet})...")
        
        # REAL API CALL - get account balance
        logger.info(f"🔗 Calling broker.get_account_balance()...")
        account_balance = await broker.get_account_balance()
        logger.info(f"✅ get_account_balance() succeeded: {account_balance}")
        
        if not account_balance:
            raise Exception("get_account_balance() returned None")
        
        # Connection successful!
        connection_success = True
        connection_message = f"Connection successful to {exchange}"
        
        account_info = {
            "exchange": exchange,
            "broker": broker.name,
            "testnet": use_testnet,
            "status": "connected",
            "free_balance": account_balance.free_usdt,
            "locked_balance": account_balance.locked_usdt,
            "total_value": account_balance.total_value_usdt,
            "assets_count": len(account_balance.assets)
        }
        
        logger.info(f"✅ Connection test SUCCESS: {exchange} - Balance=${account_balance.total_value_usdt:.2f}")
        
        # Update config status if testing existing config
        if config:
            config.connection_status = "connected"
            config.last_connection_test = datetime.utcnow()
            config.connection_error = None
            db.commit()
        
        return {
            "status": "success",
            "message": connection_message,
            "account": account_info
        }
        
    except Exception as e:
        logger.error(f"❌ Connection test FAILED at get_account_balance(): {str(e)}", exc_info=True)
        
        # Update config status if testing existing config
        if config:
            config.connection_status = "failed"
            config.last_connection_test = datetime.utcnow()
            config.connection_error = str(e)
            db.commit()
        
        return {
            "status": "error",
            "message": f"Connection failed: {str(e)}"
        }


@router.post("/configs/{config_id}/toggle")
async def toggle_exchange_active(
    config_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """Toggle exchange active status"""
    config = db.query(ExchangeConfig).filter(
        ExchangeConfig.id == config_id,
        ExchangeConfig.user_id == current_user.id
    ).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="Exchange config not found")
    
    config.is_active = not config.is_active
    db.commit()
    
    return {
        "status": "success",
        "is_active": config.is_active,
        "message": f"Exchange {config.exchange} {'activated' if config.is_active else 'deactivated'}"
    }

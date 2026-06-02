"""
BrokerFactory - Creates the appropriate broker based on user configuration.

Reads ExchangeConfig from database and instantiates:
- PaperBroker (with LiveDataSource) if paper_trading=True
- BinanceBroker (live/testnet) if paper_trading=False
- Future: KrakenBroker, BybitBroker, etc.
"""

from typing import Optional
from sqlalchemy.orm import Session

from .base import BaseBroker
from .binance_broker import BinanceBroker
from .bybit_broker import BybitBroker
from .paper_broker import PaperBroker
from .data_sources import LiveDataSource
from .data_sources.mock import MockDataSource


class BrokerFactory:
    """
    Factory for creating broker instances based on user configuration.
    
    This is the main entry point for services (BotEngine, AIAgent, etc.) 
    to obtain a broker instance without knowing implementation details.
    
    Usage:
        >>> # From user_id (most common)
        >>> broker = BrokerFactory.from_user(user_id, db)
        >>> 
        >>> # From ExchangeConfig object
        >>> config = db.query(ExchangeConfig).filter(...).first()
        >>> broker = BrokerFactory.create(config)
        >>> 
        >>> # Create paper broker directly (for testing)
        >>> paper = BrokerFactory.create_paper()
    """
    
    @staticmethod
    def create(config, db_session: Optional[Session] = None) -> BaseBroker:
        """
        Create a broker from an ExchangeConfig.
        
        Logic:
        1. If paper_trading=True → PaperBroker with configurable initial_balance
        2. If paper_trading=False → BinanceBroker (live or testnet)
        
        Args:
            config: ExchangeConfig model instance
            db_session: Optional database session (unused for now)
            
        Returns:
            BaseBroker implementation
            
        Raises:
            ValueError: If exchange not supported
        """
        if config.paper_trading:
            # === PAPER TRADING MODE ===
            # Create PaperBroker with user-configured initial_balance
            # Uses Binance testnet OR Bybit testnet for market data prices
            from app.services.crypto_service import get_crypto_service

            crypto_service = get_crypto_service()
            api_key = crypto_service.decrypt(config.api_key_encrypted) if config.api_key_encrypted else ""
            api_secret = crypto_service.decrypt(config.api_secret_encrypted) if config.api_secret_encrypted else ""

            # Pick upstream data source based on configured exchange
            if config.exchange == "bybit":
                upstream_broker = BybitBroker(api_key=api_key, api_secret=api_secret, testnet=True)
            else:
                upstream_broker = BinanceBroker(api_key=api_key, api_secret=api_secret, testnet=True)

            data_source = LiveDataSource(upstream_broker)

            return PaperBroker(
                data_source=data_source,
                initial_balance=config.initial_balance,
                slippage_pct=0.05,
                commission_pct=0.1
            )
        else:
            # === LIVE TRADING MODE ===
            # Real exchange connection (live or testnet based on config)
            return BrokerFactory._create_live_broker(config)
    
    @staticmethod
    def _create_live_broker(config, force_testnet: bool = False) -> BaseBroker:
        """
        Create a live broker based on exchange type.
        
        Decrypts API credentials and instantiates the appropriate broker.
        
        Args:
            config: ExchangeConfig model instance
            force_testnet: If True, force testnet mode (used for paper trading)
            
        Returns:
            Live broker (Binance, Kraken, etc.)
            
        Raises:
            ValueError: If exchange not supported
        """
        from app.services.crypto_service import get_crypto_service
        
        # Decrypt credentials
        crypto_service = get_crypto_service()
        api_key = crypto_service.decrypt(config.api_key_encrypted) if config.api_key_encrypted else ""
        api_secret = crypto_service.decrypt(config.api_secret_encrypted) if config.api_secret_encrypted else ""
        
        use_testnet = force_testnet or config.use_testnet
        
        # Create appropriate broker
        if config.exchange == "binance":
            return BinanceBroker(
                api_key=api_key,
                api_secret=api_secret,
                testnet=use_testnet
            )
        elif config.exchange == "bybit":
            return BybitBroker(
                api_key=api_key,
                api_secret=api_secret,
                testnet=use_testnet
            )
        elif config.exchange == "kraken":
            # Future implementation
            raise NotImplementedError("Kraken broker not yet implemented")
        elif config.exchange == "coinbase":
            # Future implementation
            raise NotImplementedError("Coinbase broker not yet implemented")
        else:
            raise ValueError(f"Unsupported exchange: {config.exchange}")
    
    @staticmethod
    def from_user(user_id: str, db: Session) -> BaseBroker:
        """
        Create a broker for a user based on their active default ExchangeConfig.
        
        This is the primary method used by services.
        
        Workflow:
        1. Query ExchangeConfig for user (is_active=True, is_default=True)
        2. If found → create broker from config
        3. If not found → create default PaperBroker with Binance data
        
        Args:
            user_id: User UUID
            db: SQLAlchemy database session
            
        Returns:
            BaseBroker instance (Paper or Live)
            
        Example:
            >>> from app.brokers import BrokerFactory
            >>> 
            >>> def execute_trade(user_id: str, db: Session):
            >>>     broker = BrokerFactory.from_user(user_id, db)
            >>>     result = await broker.place_order("BTCUSDT", OrderSide.BUY, 0.01)
            >>>     print(f"Order executed: {result.order_id}")
        """
        from app.models.database_models import ExchangeConfig
        
        # 1) Try active default config first
        config = db.query(ExchangeConfig).filter(
            ExchangeConfig.user_id == user_id,
            ExchangeConfig.is_active == True,
            ExchangeConfig.is_default == True
        ).order_by(ExchangeConfig.updated_at.desc()).first()

        # 2) Fallback to any active config (deterministic by latest update)
        if not config:
            config = db.query(ExchangeConfig).filter(
                ExchangeConfig.user_id == user_id,
                ExchangeConfig.is_active == True
            ).order_by(ExchangeConfig.updated_at.desc()).first()

        # 3) If user has no active broker config, use local fake-paper fallback
        #    This keeps broker architecture consistent and avoids external API dependency.
        if not config:
            return PaperBroker(
                data_source=MockDataSource(),
                initial_balance=10000.0,
            )
        
        # Create broker from config
        return BrokerFactory.create(config, db)
    
    @staticmethod
    def create_paper(
        source_type: str = "live",
        config: Optional[dict] = None
    ) -> PaperBroker:
        """
        Create a PaperBroker directly (for testing/backtesting).
        
        Args:
            source_type: "live", "mock", "file", or "db"
            config: Optional configuration dict
            
        Returns:
            PaperBroker instance
            
        Example:
            >>> # Paper trading with live Binance data
            >>> paper = BrokerFactory.create_paper("live")
            >>> 
            >>> # Backtesting with file data
            >>> paper = BrokerFactory.create_paper("file", {
            >>>     "data_dir": "tests/fixtures/market_data"
            >>> })
        """
        config = config or {}
        
        if source_type == "live":
            # Live data from Binance
            upstream = BinanceBroker()
            data_source = LiveDataSource(upstream)
        elif source_type == "mock":
            # Fully local fake market data (no external API calls)
            data_source = MockDataSource()
        elif source_type == "file":
            # Historical data from files
            from .data_sources import FileDataSource
            data_source = FileDataSource(config)
        elif source_type == "db":
            # Test scenarios from database
            from .data_sources import DBDataSource
            data_source = DBDataSource(config.get("db_session"))
        else:
            raise ValueError(f"Unknown source type: {source_type}")
        
        return PaperBroker(
            data_source=data_source,
            initial_balance=config.get("initial_balance", 10000.0),
            slippage_pct=config.get("slippage_pct", 0.05),
            commission_pct=config.get("commission_pct", 0.1)
        )

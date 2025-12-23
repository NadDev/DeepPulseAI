"""
Timescale Cloud Client for Market Data
=======================================
Handles connection to TimescaleDB for time-series market data storage.
"""

import os
from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv

load_dotenv()


class TimescaleClient:
    """Client for connecting to TimescaleDB Cloud."""
    
    def __init__(self):
        self.host = os.getenv("TIMESCALE_HOST")
        self.port = os.getenv("TIMESCALE_PORT", "5432")
        self.database = os.getenv("TIMESCALE_DATABASE", "tsdb")
        self.user = os.getenv("TIMESCALE_USER")
        self.password = os.getenv("TIMESCALE_PASSWORD")
        
        # Sync engine (for migrations and admin tasks)
        self._sync_engine = None
        self._sync_session_factory = None
        
        # Async engine (for application use)
        self._async_engine = None
        self._async_session_factory = None
    
    @property
    def sync_url(self) -> str:
        """PostgreSQL connection URL for sync operations."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}?sslmode=require"
    
    @property
    def async_url(self) -> str:
        """PostgreSQL connection URL for async operations."""
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}?ssl=require"
    
    def get_sync_engine(self):
        """Get or create synchronous SQLAlchemy engine."""
        if self._sync_engine is None:
            self._sync_engine = create_engine(
                self.sync_url,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                echo=os.getenv("ENV") == "development"
            )
        return self._sync_engine
    
    def get_sync_session(self) -> Session:
        """Get a synchronous database session."""
        if self._sync_session_factory is None:
            self._sync_session_factory = sessionmaker(
                bind=self.get_sync_engine(),
                autocommit=False,
                autoflush=False
            )
        return self._sync_session_factory()
    
    async def get_async_engine(self):
        """Get or create asynchronous SQLAlchemy engine."""
        if self._async_engine is None:
            self._async_engine = create_async_engine(
                self.async_url,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                echo=os.getenv("ENV") == "development"
            )
        return self._async_engine
    
    async def get_async_session(self) -> AsyncSession:
        """Get an asynchronous database session."""
        if self._async_session_factory is None:
            engine = await self.get_async_engine()
            self._async_session_factory = async_sessionmaker(
                bind=engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
        return self._async_session_factory()
    
    def test_connection(self) -> bool:
        """Test the database connection."""
        try:
            engine = self.get_sync_engine()
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                return result.fetchone()[0] == 1
        except Exception as e:
            print(f"❌ Timescale connection failed: {e}")
            return False
    
    def init_hypertables(self):
        """Initialize TimescaleDB hypertables for market data."""
        engine = self.get_sync_engine()
        
        with engine.connect() as conn:
            # Enable TimescaleDB extension
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"))
            
            # Create OHLCV market data table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS market_data (
                    time TIMESTAMPTZ NOT NULL,
                    symbol VARCHAR(20) NOT NULL,
                    exchange VARCHAR(20) NOT NULL,
                    open DOUBLE PRECISION,
                    high DOUBLE PRECISION,
                    low DOUBLE PRECISION,
                    close DOUBLE PRECISION,
                    volume DOUBLE PRECISION,
                    quote_volume DOUBLE PRECISION,
                    trades_count INTEGER,
                    timeframe VARCHAR(10) DEFAULT '1m'
                );
            """))
            
            # Convert to hypertable (if not already)
            conn.execute(text("""
                SELECT create_hypertable('market_data', 'time', 
                    if_not_exists => TRUE,
                    chunk_time_interval => INTERVAL '1 day'
                );
            """))
            
            # Create index for fast symbol lookups
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_market_data_symbol_time 
                ON market_data (symbol, time DESC);
            """))
            
            # Create trades table for order history
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS trade_history (
                    time TIMESTAMPTZ NOT NULL,
                    user_id UUID NOT NULL,
                    bot_id UUID,
                    symbol VARCHAR(20) NOT NULL,
                    side VARCHAR(10) NOT NULL,
                    order_type VARCHAR(20),
                    quantity DOUBLE PRECISION,
                    price DOUBLE PRECISION,
                    total DOUBLE PRECISION,
                    fee DOUBLE PRECISION,
                    fee_asset VARCHAR(10),
                    exchange VARCHAR(20),
                    order_id VARCHAR(100),
                    status VARCHAR(20)
                );
            """))
            
            # Convert trades to hypertable
            conn.execute(text("""
                SELECT create_hypertable('trade_history', 'time',
                    if_not_exists => TRUE,
                    chunk_time_interval => INTERVAL '7 days'
                );
            """))
            
            # Create index for user trade lookups
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_trade_history_user_time 
                ON trade_history (user_id, time DESC);
            """))
            
            conn.commit()
            print("✅ TimescaleDB hypertables initialized successfully!")
    
    def close(self):
        """Close all database connections."""
        if self._sync_engine:
            self._sync_engine.dispose()
        if self._async_engine:
            import asyncio
            asyncio.get_event_loop().run_until_complete(self._async_engine.dispose())


# Global client instance
_timescale_client: Optional[TimescaleClient] = None


def get_timescale_client() -> TimescaleClient:
    """Get or create the global Timescale client."""
    global _timescale_client
    if _timescale_client is None:
        _timescale_client = TimescaleClient()
    return _timescale_client


# Dependency for FastAPI
def get_timescale_session():
    """FastAPI dependency for getting a Timescale session."""
    client = get_timescale_client()
    session = client.get_sync_session()
    try:
        yield session
    finally:
        session.close()


@asynccontextmanager
async def get_timescale_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager for Timescale sessions."""
    client = get_timescale_client()
    session = await client.get_async_session()
    try:
        yield session
    finally:
        await session.close()

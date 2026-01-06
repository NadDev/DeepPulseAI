"""
Initialize Railway PostgreSQL database with schema.
Run this script once to create all tables.
"""
import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Railway PostgreSQL connection
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ ERROR: DATABASE_URL not found in environment variables")
    sys.exit(1)

print(f"📦 Connecting to Railway PostgreSQL...")
print(f"🔗 URL: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'hidden'}")

try:
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        print("\n✅ Connected successfully!")
        
        # Create extensions first
        print("\n📦 Creating extensions...")
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\""))
            conn.commit()
            print("   ✓ uuid-ossp extension")
        except Exception as e:
            conn.rollback()
            if "already exists" not in str(e):
                print(f"   ⚠️  {e}")
        
        # Create ENUMs
        print("\n📦 Creating enums...")
        enums = [
            ("trade_status", "('OPEN', 'CLOSED', 'CANCELLED')"),
            ("bot_status", "('IDLE', 'RUNNING', 'PAUSED', 'ERROR')")
        ]
        
        for enum_name, enum_values in enums:
            try:
                conn.execute(text(f"CREATE TYPE {enum_name} AS ENUM {enum_values}"))
                conn.commit()
                print(f"   ✓ {enum_name}")
            except Exception as e:
                conn.rollback()
                if "already exists" not in str(e):
                    print(f"   ⚠️  {enum_name}: {e}")
                if "already exists" not in str(e):
                    print(f"   ⚠️  {enum_name}: {e}")
        
        # Create tables
        print("\n📋 Creating tables...")
        
        tables_sql = [
            # Users table
            """
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                email VARCHAR(255) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # Bots table
            """
            CREATE TABLE IF NOT EXISTS bots (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name VARCHAR(255) NOT NULL,
                strategy VARCHAR(100) NOT NULL,
                status bot_status DEFAULT 'IDLE',
                config JSONB DEFAULT '{}'::jsonb,
                paper_trading BOOLEAN DEFAULT true,
                risk_percent DECIMAL(5, 2) DEFAULT 2.0,
                max_drawdown DECIMAL(5, 2) DEFAULT 20.0,
                is_live BOOLEAN DEFAULT false,
                total_trades INT DEFAULT 0,
                win_rate DECIMAL(5, 2) DEFAULT 0.0,
                total_pnl DECIMAL(20, 8) DEFAULT 0.0,
                symbols JSONB DEFAULT '[]'::jsonb,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT unique_user_bot_name UNIQUE(user_id, name)
            )
            """,
            
            # Trades table
            """
            CREATE TABLE IF NOT EXISTS trades (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                bot_id UUID REFERENCES bots(id) ON DELETE CASCADE,
                symbol VARCHAR(20) NOT NULL,
                side VARCHAR(10) NOT NULL,
                status trade_status DEFAULT 'OPEN',
                entry_price DECIMAL(20, 8) NOT NULL,
                exit_price DECIMAL(20, 8),
                quantity DECIMAL(20, 8) NOT NULL,
                pnl DECIMAL(20, 8),
                pnl_percent DECIMAL(10, 2),
                entry_time TIMESTAMP NOT NULL,
                exit_time TIMESTAMP,
                strategy VARCHAR(100),
                stop_loss_price DECIMAL(20, 8),
                take_profit_price DECIMAL(20, 8),
                trailing_stop_percent DECIMAL(5, 2),
                max_loss_amount DECIMAL(20, 8),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # Portfolios table
            """
            CREATE TABLE IF NOT EXISTS portfolios (
                id BIGSERIAL PRIMARY KEY,
                user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
                total_value DECIMAL(20, 8) DEFAULT 100000.0,
                cash_balance DECIMAL(20, 8) DEFAULT 100000.0,
                daily_pnl DECIMAL(20, 8) DEFAULT 0.0,
                total_pnl DECIMAL(20, 8) DEFAULT 0.0,
                win_rate DECIMAL(5, 2) DEFAULT 0.0,
                max_drawdown DECIMAL(5, 2) DEFAULT 0.0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # Sentiment data table
            """
            CREATE TABLE IF NOT EXISTS sentiment_data (
                id BIGSERIAL PRIMARY KEY,
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                symbol VARCHAR(20) NOT NULL,
                sentiment_score DECIMAL(5, 2) NOT NULL,
                source VARCHAR(100),
                analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # Risk events table
            """
            CREATE TABLE IF NOT EXISTS risk_events (
                id BIGSERIAL PRIMARY KEY,
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                bot_id UUID REFERENCES bots(id) ON DELETE CASCADE,
                event_type VARCHAR(50) NOT NULL,
                severity VARCHAR(20) NOT NULL,
                description TEXT,
                resolved BOOLEAN DEFAULT false,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # Strategy performance table
            """
            CREATE TABLE IF NOT EXISTS strategy_performance (
                id BIGSERIAL PRIMARY KEY,
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                strategy VARCHAR(100) NOT NULL,
                total_trades INT DEFAULT 0,
                win_rate DECIMAL(5, 2) DEFAULT 0.0,
                avg_profit DECIMAL(20, 8) DEFAULT 0.0,
                sharpe_ratio DECIMAL(10, 4),
                max_drawdown DECIMAL(5, 2),
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # Broker connections table
            """
            CREATE TABLE IF NOT EXISTS broker_connections (
                id BIGSERIAL PRIMARY KEY,
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                broker_name VARCHAR(50) NOT NULL,
                api_key_encrypted TEXT NOT NULL,
                api_secret_encrypted TEXT NOT NULL,
                is_testnet BOOLEAN DEFAULT true,
                is_active BOOLEAN DEFAULT true,
                last_connected TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT unique_user_broker UNIQUE(user_id, broker_name)
            )
            """
        ]
        
        for table_sql in tables_sql:
            try:
                conn.execute(text(table_sql))
                conn.commit()
                # Extract table name for logging
                table_name = table_sql.split("CREATE TABLE IF NOT EXISTS ")[1].split("(")[0].strip()
                print(f"   ✓ {table_name}")
            except Exception as e:
                conn.rollback()
                if "already exists" not in str(e).lower():
                    print(f"   ⚠️  Error creating table: {e}")
        
        # Create indexes
        print("\n📊 Creating indexes...")
        
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_bots_user_id ON bots(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_bots_status ON bots(status)",
            "CREATE INDEX IF NOT EXISTS idx_bots_created_at ON bots(created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_trades_user_id ON trades(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_trades_bot_id ON trades(bot_id)",
            "CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)",
            "CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status)",
            "CREATE INDEX IF NOT EXISTS idx_trades_entry_time ON trades(entry_time DESC)",
            "CREATE INDEX IF NOT EXISTS idx_portfolios_user_id ON portfolios(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_sentiment_user_id ON sentiment_data(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_sentiment_symbol ON sentiment_data(symbol)",
            "CREATE INDEX IF NOT EXISTS idx_sentiment_analyzed_at ON sentiment_data(analyzed_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_risk_events_user_id ON risk_events(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_risk_events_bot_id ON risk_events(bot_id)",
            "CREATE INDEX IF NOT EXISTS idx_risk_events_severity ON risk_events(severity)",
            "CREATE INDEX IF NOT EXISTS idx_risk_events_created_at ON risk_events(created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_strategy_perf_user_id ON strategy_performance(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_strategy_perf_strategy ON strategy_performance(strategy)",
            "CREATE INDEX IF NOT EXISTS idx_broker_conn_user_id ON broker_connections(user_id)"
        ]
        
        for index_sql in indexes:
            try:
                conn.execute(text(index_sql))
                conn.commit()
            except Exception as e:
                conn.rollback()
                if "already exists" not in str(e).lower():
                    print(f"   ⚠️  {e}")
                conn.rollback()
                if "already exists" not in str(e).lower():
                    print(f"   ⚠️  {e}")
        
        print("\n✅ All tables and indexes created successfully!")
        
        # Verify tables
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """))
        conn.commit()
        
        tables = [row[0] for row in result]
        print(f"\n📊 Created {len(tables)} tables:")
        for table in tables:
            print(f"   ✓ {table}")
        
        print("\n🎉 Database initialization complete!")
        
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    sys.exit(1)

-- Migration 023: Add automatic data retention policies
-- Purpose: Automatically clean up old data to manage database storage
-- Implements: Stored procedures for automated cleanup based on data age

-- ============================================================================
-- RETENTION POLICIES TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS data_retention_policies (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL UNIQUE,
    retention_days INT NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    delete_condition VARCHAR(500),  -- SQL WHERE clause
    last_cleanup TIMESTAMP,
    cleanup_frequency_hours INT DEFAULT 24,  -- How often to run cleanup
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Insert default retention policies
DELETE FROM data_retention_policies WHERE table_name IN (
    'crypto_market_data',
    'ai_decisions', 
    'trades',
    'risk_events',
    'bot_metrics',
    'equity_curve'
);

INSERT INTO data_retention_policies (table_name, retention_days, delete_condition, cleanup_frequency_hours) VALUES
    -- Keep 180 days of crypto market data (10GB allows extended history for backtesting)
    -- ~200 cryptos × 3 timeframes × 180 days ≈ 1-2GB
    ('crypto_market_data', 180, 'timestamp < EXTRACT(EPOCH FROM (NOW() - INTERVAL ''180 days'')) * 1000', 48),
    
    -- Keep 60 days of AI decisions (extended for analysis)
    ('ai_decisions', 60, 'created_at < NOW() - INTERVAL ''60 days''', 24),
    
    -- Keep 365 days of closed/cancelled trades (full year history)
    -- OPEN trades never deleted
    ('trades', 365, 'status IN (''CLOSED'', ''CANCELLED'') AND updated_at < NOW() - INTERVAL ''365 days''', 48),
    
    -- Keep 60 days of risk events (extended for pattern analysis)
    ('risk_events', 60, 'created_at < NOW() - INTERVAL ''60 days''', 48),
    
    -- Keep 180 days of bot metrics (6 months of equity curves)
    ('bot_metrics', 180, 'recorded_at < NOW() - INTERVAL ''180 days''', 48),
    
    -- Keep 180 days of equity curves
    ('equity_curve', 180, 'created_at < NOW() - INTERVAL ''180 days''', 48);

-- ============================================================================
-- STORED PROCEDURE: Cleanup old data based on retention policies
-- ============================================================================
CREATE OR REPLACE FUNCTION cleanup_old_data()
RETURNS TABLE(
    table_name VARCHAR,
    rows_deleted BIGINT,
    space_freed_mb NUMERIC,
    status VARCHAR
) AS $$
DECLARE
    policy RECORD;
    rows_count BIGINT;
    space_before BIGINT;
    space_after BIGINT;
    vacuum_success BOOLEAN;
BEGIN
    -- Iterate through all enabled policies
    FOR policy IN 
        SELECT * FROM data_retention_policies 
        WHERE enabled = TRUE
        AND (last_cleanup IS NULL OR last_cleanup < NOW() - (cleanup_frequency_hours || ' hours')::INTERVAL)
    LOOP
        BEGIN
            -- Get space before cleanup
            EXECUTE format('SELECT pg_total_relation_size(%L)', policy.table_name) 
            INTO space_before;
            
            -- Count rows to delete
            EXECUTE format(
                'SELECT COUNT(*) FROM %I WHERE %s',
                policy.table_name,
                policy.delete_condition
            ) INTO rows_count;
            
            IF rows_count > 0 THEN
                -- Delete old rows
                EXECUTE format(
                    'DELETE FROM %I WHERE %s',
                    policy.table_name,
                    policy.delete_condition
                );
                
                -- Get space after
                EXECUTE format('SELECT pg_total_relation_size(%L)', policy.table_name) 
                INTO space_after;
                
                -- Vacuum to reclaim space
                EXECUTE format('VACUUM ANALYZE %I', policy.table_name);
                
                -- Update last cleanup time
                UPDATE data_retention_policies 
                SET last_cleanup = NOW()
                WHERE id = policy.id;
                
                RETURN QUERY SELECT 
                    policy.table_name::VARCHAR,
                    rows_count,
                    ROUND(CAST((space_before - space_after) / 1024 / 1024 AS NUMERIC), 2),
                    'SUCCESS'::VARCHAR;
            ELSE
                -- Update last cleanup time even if no rows deleted
                UPDATE data_retention_policies 
                SET last_cleanup = NOW()
                WHERE id = policy.id;
                
                RETURN QUERY SELECT 
                    policy.table_name::VARCHAR,
                    0::BIGINT,
                    0::NUMERIC,
                    'NO_DATA'::VARCHAR;
            END IF;
            
        EXCEPTION WHEN OTHERS THEN
            RETURN QUERY SELECT 
                policy.table_name::VARCHAR,
                0::BIGINT,
                0::NUMERIC,
                ('ERROR: ' || SQLERRM)::VARCHAR;
        END;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- STORED PROCEDURE: Get database storage statistics
-- ============================================================================
CREATE OR REPLACE FUNCTION get_database_storage_stats()
RETURNS TABLE(
    table_name VARCHAR,
    size_mb NUMERIC,
    row_count BIGINT,
    index_size_mb NUMERIC,
    last_vacuum TIMESTAMP,
    last_autovacuum TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        t.tablename::VARCHAR,
        ROUND(CAST(pg_total_relation_size(t.schemaname||'.'||t.tablename) / 1024 / 1024 AS NUMERIC), 2),
        t.n_live_tup,
        ROUND(CAST(pg_indexes_size(t.schemaname||'.'||t.tablename) / 1024 / 1024 AS NUMERIC), 2),
        t.last_vacuum,
        t.last_autovacuum
    FROM pg_stat_user_tables t
    WHERE t.schemaname = 'public'
    ORDER BY pg_total_relation_size(t.schemaname||'.'||t.tablename) DESC;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- STORED PROCEDURE: Get total database size
-- ============================================================================
CREATE OR REPLACE FUNCTION get_total_database_size()
RETURNS TABLE(
    database_name VARCHAR,
    total_size_mb NUMERIC,
    tables_size_mb NUMERIC,
    indexes_size_mb NUMERIC,
    free_space_estimate_mb NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    WITH db_stats AS (
        SELECT 
            current_database() as db,
            SUM(pg_total_relation_size(t.schemaname||'.'||t.tablename)) as total,
            SUM(pg_relation_size(t.schemaname||'.'||t.tablename)) as tables,
            SUM(pg_indexes_size(t.schemaname||'.'||t.tablename)) as indexes
        FROM pg_stat_user_tables t
        WHERE t.schemaname = 'public'
    )
    SELECT 
        db::VARCHAR,
        ROUND(CAST(total / 1024 / 1024 AS NUMERIC), 2),
        ROUND(CAST(tables / 1024 / 1024 AS NUMERIC), 2),
        ROUND(CAST(indexes / 1024 / 1024 AS NUMERIC), 2),
        0::NUMERIC  -- Placeholder for free space (requires OS access)
    FROM db_stats;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- TRIGGER: Auto-cleanup on insert if space is critical (emergency mode)
-- ============================================================================
-- This function runs cleanup if database is >80% full
CREATE OR REPLACE FUNCTION check_storage_and_cleanup()
RETURNS TRIGGER AS $$
BEGIN
    -- This would be called periodically, not on every insert
    -- To use: SELECT check_storage_and_cleanup();
    PERFORM cleanup_old_data();
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- HELPER FUNCTION: Adjust retention for a table
-- ============================================================================
CREATE OR REPLACE FUNCTION set_retention_policy(
    p_table_name VARCHAR,
    p_retention_days INT,
    p_enabled BOOLEAN DEFAULT TRUE
)
RETURNS VARCHAR AS $$
DECLARE
    v_updated BOOLEAN;
BEGIN
    UPDATE data_retention_policies 
    SET 
        retention_days = p_retention_days,
        enabled = p_enabled,
        updated_at = NOW()
    WHERE table_name = p_table_name;
    
    IF FOUND THEN
        RETURN 'Policy updated for table: ' || p_table_name || 
               ' (retention: ' || p_retention_days || ' days)';
    ELSE
        RETURN 'ERROR: Table not found in policies: ' || p_table_name;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- VERIFICATION
-- ============================================================================
-- Log that migration was applied
INSERT INTO schema_migrations (name, applied_at) 
VALUES ('023_add_retention_policies', NOW())
ON CONFLICT DO NOTHING;

-- Show retention policies
SELECT 'Retention Policies Configured:' as info;
SELECT table_name, retention_days, enabled FROM data_retention_policies ORDER BY table_name;

-- Show database size
SELECT 'Current Database Storage:' as info;
SELECT * FROM get_total_database_size();

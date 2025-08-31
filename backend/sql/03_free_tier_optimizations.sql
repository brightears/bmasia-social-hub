-- BMA Social - Free Tier PostgreSQL Optimizations
-- Maximizing performance within Render's free tier constraints
-- Database: bma_social_esoq (expires Sept 24, 2025)
-- Limitations: 1GB storage, 1 CPU, 512MB RAM, 1000 connections/month

-- ============================================================================
-- CONNECTION MANAGEMENT FOR FREE TIER
-- ============================================================================

-- Optimize connection settings for low-resource environment
ALTER SYSTEM SET max_connections = 10;  -- Conservative for free tier
ALTER SYSTEM SET shared_buffers = '128MB';  -- 25% of 512MB RAM
ALTER SYSTEM SET effective_cache_size = '384MB';  -- 75% of 512MB RAM
ALTER SYSTEM SET work_mem = '4MB';  -- Small per-operation memory
ALTER SYSTEM SET maintenance_work_mem = '64MB';  -- For VACUUM, indexes

-- Aggressive connection cleanup
ALTER SYSTEM SET idle_in_transaction_session_timeout = '30s';
ALTER SYSTEM SET statement_timeout = '10s';  -- Kill long queries quickly
ALTER SYSTEM SET lock_timeout = '5s';  -- Prevent lock waits

-- Optimize checkpoint frequency for small database
ALTER SYSTEM SET checkpoint_completion_target = 0.8;
ALTER SYSTEM SET wal_buffers = '4MB';

-- Apply configuration
SELECT pg_reload_conf();

-- ============================================================================
-- STORAGE OPTIMIZATION STRATEGY
-- ============================================================================

-- Use aggressive compression for text fields
-- Enable toast compression for large text fields
ALTER TABLE conversations ALTER COLUMN metadata SET STORAGE EXTENDED;
ALTER TABLE messages ALTER COLUMN content SET STORAGE EXTENDED;
ALTER TABLE messages ALTER COLUMN entities SET STORAGE EXTENDED;

-- Set fillfactor for tables to minimize bloat
ALTER TABLE conversations SET (fillfactor = 90);
ALTER TABLE messages SET (fillfactor = 95);  -- Append-mostly
ALTER TABLE venues SET (fillfactor = 85);
ALTER TABLE zones SET (fillfactor = 80);

-- ============================================================================
-- DATA RETENTION STRATEGY (CRITICAL FOR 1GB LIMIT)
-- ============================================================================

-- Create data retention policies to stay under 1GB
CREATE OR REPLACE FUNCTION cleanup_old_data()
RETURNS TEXT AS $$
DECLARE
    deleted_conversations INTEGER := 0;
    deleted_messages INTEGER := 0;
    db_size TEXT;
    result_text TEXT;
BEGIN
    -- Get current database size
    SELECT pg_size_pretty(pg_database_size(current_database())) INTO db_size;
    
    -- Only keep last 90 days of resolved conversations
    DELETE FROM conversations 
    WHERE status IN ('resolved', 'closed')
    AND closed_at < CURRENT_TIMESTAMP - INTERVAL '90 days';
    
    GET DIAGNOSTICS deleted_conversations = ROW_COUNT;
    
    -- Clean up orphaned messages (should be handled by CASCADE but safety first)
    DELETE FROM messages m
    WHERE NOT EXISTS (SELECT 1 FROM conversations c WHERE c.id = m.conversation_id);
    
    GET DIAGNOSTICS deleted_messages = ROW_COUNT;
    
    -- Archive old monitoring logs (keep only 30 days)
    DELETE FROM monitoring_logs 
    WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '30 days';
    
    -- Clean up resolved alerts older than 30 days
    DELETE FROM alerts 
    WHERE status IN ('resolved', 'dismissed')
    AND resolved_at < CURRENT_TIMESTAMP - INTERVAL '30 days';
    
    -- Vacuum to reclaim space
    VACUUM ANALYZE;
    
    result_text := format(
        'Cleanup completed. DB size: %s. Deleted: %s conversations, %s messages',
        db_size, deleted_conversations, deleted_messages
    );
    
    RETURN result_text;
END;
$$ LANGUAGE plpgsql;

-- Create function to monitor database size
CREATE OR REPLACE FUNCTION check_database_size()
RETURNS TABLE(
    table_name TEXT,
    size TEXT,
    size_bytes BIGINT,
    percentage NUMERIC
) AS $$
DECLARE
    total_size BIGINT;
BEGIN
    -- Get total database size
    SELECT pg_database_size(current_database()) INTO total_size;
    
    RETURN QUERY
    SELECT 
        t.tablename::TEXT,
        pg_size_pretty(pg_total_relation_size(t.schemaname||'.'||t.tablename))::TEXT,
        pg_total_relation_size(t.schemaname||'.'||t.tablename),
        ROUND(
            (pg_total_relation_size(t.schemaname||'.'||t.tablename)::NUMERIC / total_size::NUMERIC) * 100, 
            2
        )
    FROM pg_tables t
    WHERE t.schemaname = 'public'
    ORDER BY pg_total_relation_size(t.schemaname||'.'||t.tablename) DESC;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- LIGHTWEIGHT MONITORING FOR FREE TIER
-- ============================================================================

-- Create lightweight monitoring view (no expensive operations)
CREATE OR REPLACE VIEW v_database_health AS
SELECT 
    current_database() as database_name,
    pg_size_pretty(pg_database_size(current_database())) as db_size,
    (
        SELECT COUNT(*) 
        FROM pg_stat_activity 
        WHERE datname = current_database() AND state = 'active'
    ) as active_connections,
    (
        SELECT COUNT(*) 
        FROM conversations 
        WHERE status IN ('open', 'in_progress')
    ) as active_conversations,
    (
        SELECT COUNT(*) 
        FROM messages 
        WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '1 hour'
    ) as recent_messages,
    CURRENT_TIMESTAMP as checked_at;

-- Simplified performance metrics
CREATE OR REPLACE VIEW v_simple_performance AS
SELECT 
    'conversations' as table_name,
    COUNT(*) as total_rows,
    COUNT(*) FILTER (WHERE created_at >= CURRENT_DATE) as today_rows,
    MAX(created_at) as latest_activity
FROM conversations
UNION ALL
SELECT 
    'messages' as table_name,
    COUNT(*) as total_rows,
    COUNT(*) FILTER (WHERE created_at >= CURRENT_DATE) as today_rows,
    MAX(created_at) as latest_activity
FROM messages
UNION ALL
SELECT 
    'venues' as table_name,
    COUNT(*) as total_rows,
    COUNT(*) FILTER (WHERE updated_at >= CURRENT_DATE) as today_rows,
    MAX(updated_at) as latest_activity
FROM venues;

-- ============================================================================
-- OPTIMIZED QUERIES FOR FREE TIER
-- ============================================================================

-- Function: Get conversation thread (optimized for low memory)
CREATE OR REPLACE FUNCTION get_conversation_thread_lite(
    p_conversation_id UUID,
    p_limit INTEGER DEFAULT 20  -- Smaller default for free tier
)
RETURNS TABLE(
    message_id UUID,
    sender_type TEXT,
    sender_name VARCHAR,
    content TEXT,
    created_at TIMESTAMPTZ,
    is_read BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        m.id,
        m.sender_type::TEXT,
        m.sender_name,
        -- Truncate very long messages to save memory
        CASE 
            WHEN LENGTH(m.content) > 500 
            THEN LEFT(m.content, 500) || '...'
            ELSE m.content 
        END,
        m.created_at,
        m.is_read
    FROM messages m
    WHERE m.conversation_id = p_conversation_id
    ORDER BY m.created_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Function: Get venue conversations (with limits)
CREATE OR REPLACE FUNCTION get_venue_conversations_lite(
    p_venue_id UUID,
    p_status TEXT[] DEFAULT ARRAY['open', 'in_progress'],
    p_limit INTEGER DEFAULT 50
)
RETURNS TABLE(
    conversation_id UUID,
    customer_name VARCHAR,
    channel TEXT,
    status TEXT,
    priority TEXT,
    message_count INTEGER,
    last_activity_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.id,
        c.customer_name,
        c.channel::TEXT,
        c.status::TEXT,
        c.priority::TEXT,
        c.message_count,
        c.last_activity_at,
        c.created_at
    FROM conversations c
    WHERE c.venue_id = p_venue_id
    AND (p_status IS NULL OR c.status::TEXT = ANY(p_status))
    ORDER BY c.priority DESC, c.last_activity_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- AUTOMATED MAINTENANCE FOR FREE TIER
-- ============================================================================

-- Lightweight autovacuum settings
ALTER TABLE conversations SET (
    autovacuum_vacuum_scale_factor = 0.1,
    autovacuum_analyze_scale_factor = 0.05,
    autovacuum_vacuum_cost_delay = 5  -- Faster vacuum
);

ALTER TABLE messages SET (
    autovacuum_vacuum_scale_factor = 0.2,  -- Less frequent for append-only
    autovacuum_analyze_scale_factor = 0.1,
    autovacuum_vacuum_cost_delay = 5
);

-- Create maintenance procedure for free tier
CREATE OR REPLACE FUNCTION daily_maintenance()
RETURNS TEXT AS $$
DECLARE
    result_text TEXT;
    db_size BIGINT;
BEGIN
    -- Check if we're approaching 1GB limit
    SELECT pg_database_size(current_database()) INTO db_size;
    
    IF db_size > 800 * 1024 * 1024 THEN  -- 800MB threshold
        -- Aggressive cleanup if approaching limit
        PERFORM cleanup_old_data();
        result_text := 'Performed aggressive cleanup - approaching 1GB limit';
    ELSE
        -- Normal maintenance
        VACUUM ANALYZE conversations;
        VACUUM ANALYZE messages;
        
        -- Update table statistics
        ANALYZE venues;
        ANALYZE zones;
        
        result_text := format('Normal maintenance completed. DB size: %s', 
                             pg_size_pretty(db_size));
    END IF;
    
    RETURN result_text;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- MIGRATION TO PAID TIER PREPARATION
-- ============================================================================

-- Function to estimate resource needs for paid tier migration
CREATE OR REPLACE FUNCTION estimate_paid_tier_needs()
RETURNS TABLE(
    metric TEXT,
    current_value TEXT,
    recommended_paid_plan TEXT,
    reasoning TEXT
) AS $$
DECLARE
    conversation_count BIGINT;
    message_count BIGINT;
    daily_growth NUMERIC;
    db_size_mb NUMERIC;
BEGIN
    SELECT COUNT(*) FROM conversations INTO conversation_count;
    SELECT COUNT(*) FROM messages INTO message_count;
    SELECT pg_database_size(current_database()) / 1024.0 / 1024.0 INTO db_size_mb;
    
    -- Estimate daily growth
    SELECT COUNT(*) * 7 -- Extrapolate weekly to daily
    FROM conversations 
    WHERE created_at >= CURRENT_DATE - INTERVAL '1 day'
    INTO daily_growth;
    
    RETURN QUERY
    VALUES 
        ('Database Size', pg_size_pretty(db_size_mb * 1024 * 1024)::TEXT, 
         CASE 
            WHEN db_size_mb > 500 THEN 'basic_1gb or higher'
            ELSE 'basic_256mb sufficient for now'
         END,
         'Based on current size and growth projection'),
        
        ('Conversations', conversation_count::TEXT,
         CASE 
            WHEN conversation_count > 10000 THEN 'basic_4gb recommended'
            WHEN conversation_count > 1000 THEN 'basic_1gb adequate'
            ELSE 'basic_256mb adequate'
         END,
         'Based on query complexity and indexing needs'),
        
        ('Messages', message_count::TEXT,
         CASE 
            WHEN message_count > 100000 THEN 'basic_4gb+ for performance'
            WHEN message_count > 10000 THEN 'basic_1gb adequate'
            ELSE 'basic_256mb adequate'
         END,
         'Message storage and retrieval performance'),
        
        ('Daily Growth', COALESCE(daily_growth, 0)::TEXT,
         CASE 
            WHEN daily_growth > 100 THEN 'basic_4gb for sustained growth'
            WHEN daily_growth > 20 THEN 'basic_1gb for moderate growth'
            ELSE 'basic_256mb for current growth'
         END,
         'Based on daily conversation creation rate');
END;
$$ LANGUAGE plpgsql;

-- Export/backup functions for migration
CREATE OR REPLACE FUNCTION create_migration_backup()
RETURNS TEXT AS $$
DECLARE
    backup_info TEXT;
BEGIN
    -- Create logical backup commands (to be run externally)
    backup_info := format('
Migration backup commands:
1. pg_dump -h %s -U %s -d %s --no-owner --no-privileges > bma_social_backup.sql
2. pg_dump -h %s -U %s -d %s --schema-only > bma_social_schema.sql
3. pg_dump -h %s -U %s -d %s --data-only > bma_social_data.sql

Post-migration verification:
SELECT check_database_size();
SELECT * FROM v_database_health;
SELECT estimate_paid_tier_needs();
    ', 
    current_setting('listen_addresses'), 
    current_user, 
    current_database(),
    current_setting('listen_addresses'), 
    current_user, 
    current_database(),
    current_setting('listen_addresses'), 
    current_user, 
    current_database()
    );
    
    RETURN backup_info;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- FREE TIER MONITORING QUERIES
-- ============================================================================

-- Quick health check query
CREATE OR REPLACE FUNCTION quick_health_check()
RETURNS TABLE(
    status TEXT,
    detail TEXT
) AS $$
DECLARE
    db_size_mb NUMERIC;
    connection_count INTEGER;
BEGIN
    SELECT pg_database_size(current_database()) / 1024.0 / 1024.0 INTO db_size_mb;
    SELECT COUNT(*) FROM pg_stat_activity WHERE datname = current_database() INTO connection_count;
    
    RETURN QUERY
    VALUES 
        ('Database Size', format('%s MB (%.1f%% of 1GB limit)', 
                                ROUND(db_size_mb, 1), 
                                ROUND((db_size_mb / 1024.0) * 100, 1))),
        ('Active Connections', format('%s connections', connection_count)),
        ('Active Conversations', (SELECT COUNT(*)::TEXT FROM conversations WHERE status IN ('open', 'in_progress'))),
        ('Recent Messages (1hr)', (SELECT COUNT(*)::TEXT FROM messages WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '1 hour')),
        ('Cleanup Recommended', 
         CASE 
            WHEN db_size_mb > 800 THEN 'YES - Approaching limit'
            WHEN db_size_mb > 600 THEN 'CONSIDER - 60% full'
            ELSE 'NO - Size OK'
         END);
END;
$$ LANGUAGE plpgsql;
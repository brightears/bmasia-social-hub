-- BMA Social - Quick Start Implementation
-- Run these commands in order to immediately optimize your database

-- Step 1: Enable extensions and configure for free tier
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
ALTER SYSTEM SET max_connections = 10;
ALTER SYSTEM SET shared_buffers = '128MB';
ALTER SYSTEM SET effective_cache_size = '384MB';
ALTER SYSTEM SET work_mem = '4MB';
SELECT pg_reload_conf();

-- Step 2: Check current database size
SELECT 
    pg_size_pretty(pg_database_size(current_database())) as current_size,
    ROUND((pg_database_size(current_database())::NUMERIC / (1024*1024*1024)) * 100, 1) || '%' as percentage_of_1gb;

-- Step 3: If size > 600MB, run immediate cleanup
-- Uncomment the next line if needed:
-- SELECT cleanup_old_data();

-- Step 4: Create essential indexes for immediate performance boost
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_conversations_venue_status 
    ON conversations (venue_id, status, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_messages_conversation_created 
    ON messages (conversation_id, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_conversations_active_sla 
    ON conversations (sla_deadline, status)
    WHERE sla_deadline IS NOT NULL AND status NOT IN ('resolved', 'closed');

-- Step 5: Set up basic monitoring
CREATE OR REPLACE FUNCTION quick_status_check()
RETURNS TABLE(metric TEXT, value TEXT, status TEXT) AS $$
BEGIN
    RETURN QUERY
    SELECT 'DB Size', pg_size_pretty(pg_database_size(current_database())), 
           CASE WHEN pg_database_size(current_database()) > 800*1024*1024 THEN 'WARNING' ELSE 'OK' END
    UNION ALL
    SELECT 'Active Conversations', COUNT(*)::TEXT, 'INFO'
    FROM conversations WHERE status IN ('open', 'in_progress')
    UNION ALL
    SELECT 'Messages Today', COUNT(*)::TEXT, 'INFO'
    FROM messages WHERE created_at >= CURRENT_DATE;
END;
$$ LANGUAGE plpgsql;

-- Step 6: Run status check
SELECT * FROM quick_status_check();

-- Step 7: Analyze tables for better query plans
ANALYZE conversations;
ANALYZE messages;
ANALYZE venues;

-- NEXT: Run the full optimization files in order (01-06)
-- Monitor with: SELECT * FROM quick_status_check();
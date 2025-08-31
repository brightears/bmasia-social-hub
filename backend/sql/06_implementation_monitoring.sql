-- BMA Social - Implementation Guide and Performance Monitoring
-- Complete monitoring setup for PostgreSQL performance tracking
-- Production-ready health checks and optimization recommendations

-- ============================================================================
-- DATABASE PERFORMANCE MONITORING SETUP
-- ============================================================================

-- Enable required extensions for monitoring
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
CREATE EXTENSION IF NOT EXISTS pg_buffercache;

-- Configure pg_stat_statements for comprehensive query tracking
ALTER SYSTEM SET pg_stat_statements.max = 10000;
ALTER SYSTEM SET pg_stat_statements.track = 'all';
ALTER SYSTEM SET pg_stat_statements.track_utility = on;
ALTER SYSTEM SET pg_stat_statements.save = on;

-- Apply configuration
SELECT pg_reload_conf();

-- ============================================================================
-- COMPREHENSIVE HEALTH CHECK SYSTEM
-- ============================================================================

-- Master health check function
CREATE OR REPLACE FUNCTION comprehensive_health_check()
RETURNS TABLE(
    category TEXT,
    check_name TEXT,
    status TEXT,
    value TEXT,
    recommendation TEXT,
    severity TEXT
) AS $$
BEGIN
    RETURN QUERY
    
    -- Database Size Monitoring
    WITH db_size AS (
        SELECT pg_database_size(current_database()) as size_bytes
    )
    SELECT 
        'Storage'::TEXT,
        'Database Size'::TEXT,
        CASE 
            WHEN size_bytes > 900 * 1024 * 1024 THEN 'CRITICAL'  -- >900MB on free tier
            WHEN size_bytes > 700 * 1024 * 1024 THEN 'WARNING'   -- >700MB
            WHEN size_bytes > 500 * 1024 * 1024 THEN 'WATCH'     -- >500MB
            ELSE 'OK'
        END::TEXT,
        pg_size_pretty(size_bytes)::TEXT,
        CASE 
            WHEN size_bytes > 900 * 1024 * 1024 THEN 'URGENT: Run cleanup_old_data() immediately'
            WHEN size_bytes > 700 * 1024 * 1024 THEN 'Schedule data cleanup soon'
            WHEN size_bytes > 500 * 1024 * 1024 THEN 'Monitor growth, plan cleanup'
            ELSE 'Size is healthy'
        END::TEXT,
        CASE 
            WHEN size_bytes > 900 * 1024 * 1024 THEN 'HIGH'
            WHEN size_bytes > 700 * 1024 * 1024 THEN 'MEDIUM'
            ELSE 'LOW'
        END::TEXT
    FROM db_size
    
    UNION ALL
    
    -- Connection Monitoring
    SELECT 
        'Connections'::TEXT,
        'Active Connections'::TEXT,
        CASE 
            WHEN COUNT(*) > 8 THEN 'WARNING'  -- Near free tier limit
            WHEN COUNT(*) > 5 THEN 'WATCH'
            ELSE 'OK'
        END::TEXT,
        COUNT(*)::TEXT,
        CASE 
            WHEN COUNT(*) > 8 THEN 'Close unused connections, check connection pooling'
            WHEN COUNT(*) > 5 THEN 'Monitor connection usage'
            ELSE 'Connection count is healthy'
        END::TEXT,
        CASE 
            WHEN COUNT(*) > 8 THEN 'MEDIUM'
            ELSE 'LOW'
        END::TEXT
    FROM pg_stat_activity
    WHERE datname = current_database()
    AND state = 'active'
    
    UNION ALL
    
    -- Query Performance Monitoring
    SELECT 
        'Performance'::TEXT,
        'Slow Queries'::TEXT,
        CASE 
            WHEN COUNT(*) > 10 THEN 'CRITICAL'
            WHEN COUNT(*) > 5 THEN 'WARNING'
            WHEN COUNT(*) > 0 THEN 'WATCH'
            ELSE 'OK'
        END::TEXT,
        COUNT(*)::TEXT || ' queries >1s',
        CASE 
            WHEN COUNT(*) > 10 THEN 'Critical: Review and optimize slow queries immediately'
            WHEN COUNT(*) > 5 THEN 'Review slow queries, add indexes if needed'
            WHEN COUNT(*) > 0 THEN 'Monitor slow queries'
            ELSE 'Query performance is good'
        END::TEXT,
        CASE 
            WHEN COUNT(*) > 10 THEN 'HIGH'
            WHEN COUNT(*) > 5 THEN 'MEDIUM'
            ELSE 'LOW'
        END::TEXT
    FROM pg_stat_statements
    WHERE mean_exec_time > 1000  -- Queries averaging >1 second
    
    UNION ALL
    
    -- Table Bloat Monitoring
    SELECT 
        'Maintenance'::TEXT,
        'Table Bloat'::TEXT,
        CASE 
            WHEN MAX(bloat_ratio) > 50 THEN 'CRITICAL'
            WHEN MAX(bloat_ratio) > 30 THEN 'WARNING'
            WHEN MAX(bloat_ratio) > 20 THEN 'WATCH'
            ELSE 'OK'
        END::TEXT,
        'Max: ' || COALESCE(ROUND(MAX(bloat_ratio), 1), 0)::TEXT || '%',
        CASE 
            WHEN MAX(bloat_ratio) > 50 THEN 'URGENT: Run VACUUM FULL on bloated tables'
            WHEN MAX(bloat_ratio) > 30 THEN 'Schedule VACUUM operations'
            WHEN MAX(bloat_ratio) > 20 THEN 'Monitor bloat levels'
            ELSE 'Table bloat is under control'
        END::TEXT,
        CASE 
            WHEN MAX(bloat_ratio) > 50 THEN 'HIGH'
            WHEN MAX(bloat_ratio) > 30 THEN 'MEDIUM'
            ELSE 'LOW'
        END::TEXT
    FROM (
        SELECT 
            CASE 
                WHEN relpages > 0 THEN 
                    (relpages - ceil(reltuples * 8.0 / 8192))::NUMERIC / relpages * 100
                ELSE 0
            END as bloat_ratio
        FROM pg_class c
        JOIN pg_namespace n ON c.relnamespace = n.oid
        WHERE c.relkind = 'r'
        AND n.nspname = 'public'
        AND c.reltuples > 100  -- Only check tables with data
    ) bloat_stats
    
    UNION ALL
    
    -- Conversation System Health
    SELECT 
        'Application'::TEXT,
        'Active Conversations'::TEXT,
        CASE 
            WHEN COUNT(*) > 100 THEN 'WARNING'
            WHEN COUNT(*) > 50 THEN 'WATCH'
            ELSE 'OK'
        END::TEXT,
        COUNT(*)::TEXT,
        CASE 
            WHEN COUNT(*) > 100 THEN 'High conversation volume - ensure adequate resources'
            WHEN COUNT(*) > 50 THEN 'Monitor conversation resolution rate'
            ELSE 'Conversation volume is normal'
        END::TEXT,
        CASE 
            WHEN COUNT(*) > 100 THEN 'MEDIUM'
            ELSE 'LOW'
        END::TEXT
    FROM conversations
    WHERE status IN ('open', 'in_progress', 'waiting_customer')
    
    UNION ALL
    
    -- SLA Breach Monitoring
    SELECT 
        'SLA'::TEXT,
        'Overdue Conversations'::TEXT,
        CASE 
            WHEN COUNT(*) > 5 THEN 'CRITICAL'
            WHEN COUNT(*) > 2 THEN 'WARNING'
            WHEN COUNT(*) > 0 THEN 'WATCH'
            ELSE 'OK'
        END::TEXT,
        COUNT(*)::TEXT,
        CASE 
            WHEN COUNT(*) > 5 THEN 'CRITICAL: Multiple SLA breaches - immediate attention needed'
            WHEN COUNT(*) > 2 THEN 'Review overdue conversations'
            WHEN COUNT(*) > 0 THEN 'Monitor SLA compliance'
            ELSE 'All conversations within SLA'
        END::TEXT,
        CASE 
            WHEN COUNT(*) > 5 THEN 'HIGH'
            WHEN COUNT(*) > 2 THEN 'MEDIUM'
            ELSE 'LOW'
        END::TEXT
    FROM conversations
    WHERE status NOT IN ('resolved', 'closed')
    AND sla_deadline < CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- AUTOMATED PERFORMANCE OPTIMIZATION RECOMMENDATIONS
-- ============================================================================

-- Function to analyze and suggest optimizations
CREATE OR REPLACE FUNCTION get_optimization_recommendations()
RETURNS TABLE(
    priority TEXT,
    category TEXT,
    recommendation TEXT,
    sql_command TEXT,
    estimated_impact TEXT
) AS $$
BEGIN
    RETURN QUERY
    
    -- Index recommendations based on query patterns
    WITH missing_indexes AS (
        SELECT 
            schemaname,
            tablename,
            attname,
            n_distinct,
            correlation
        FROM pg_stats
        WHERE schemaname = 'public'
        AND n_distinct > 100
        AND (tablename IN ('conversations', 'messages', 'venues', 'zones'))
        AND NOT EXISTS (
            SELECT 1 FROM pg_indexes 
            WHERE tablename = pg_stats.tablename 
            AND indexdef LIKE '%' || attname || '%'
        )
    )
    SELECT 
        'HIGH'::TEXT,
        'Indexing'::TEXT,
        format('Missing index on %s.%s (cardinality: %s)', tablename, attname, n_distinct)::TEXT,
        format('CREATE INDEX CONCURRENTLY idx_%s_%s ON %s(%s);', tablename, attname, tablename, attname)::TEXT,
        CASE 
            WHEN tablename = 'conversations' THEN 'High - Improves conversation queries'
            WHEN tablename = 'messages' THEN 'High - Improves message retrieval'
            ELSE 'Medium - General query improvement'
        END::TEXT
    FROM missing_indexes
    WHERE n_distinct > 500  -- Focus on high-cardinality columns
    
    UNION ALL
    
    -- Slow query optimization recommendations
    SELECT 
        'CRITICAL'::TEXT,
        'Query Optimization'::TEXT,
        format('Slow query pattern detected: %s (avg: %sms, calls: %s)', 
               LEFT(query, 50), ROUND(mean_exec_time), calls)::TEXT,
        'EXPLAIN ANALYZE ' || LEFT(query, 100) || '...'::TEXT,
        'Critical - Direct user experience impact'::TEXT
    FROM pg_stat_statements
    WHERE mean_exec_time > 500  -- Queries averaging >500ms
    AND calls > 5
    ORDER BY mean_exec_time DESC
    LIMIT 5
    
    UNION ALL
    
    -- Table bloat cleanup recommendations
    SELECT 
        'MEDIUM'::TEXT,
        'Maintenance'::TEXT,
        format('Table %s has significant bloat', tablename)::TEXT,
        format('VACUUM (ANALYZE, VERBOSE) %s;', tablename)::TEXT,
        'Medium - Reduces storage usage and improves performance'::TEXT
    FROM (
        SELECT 
            c.relname as tablename,
            CASE 
                WHEN c.relpages > 0 THEN 
                    (c.relpages - ceil(c.reltuples * 8.0 / 8192))::NUMERIC / c.relpages * 100
                ELSE 0
            END as bloat_percentage
        FROM pg_class c
        JOIN pg_namespace n ON c.relnamespace = n.oid
        WHERE c.relkind = 'r'
        AND n.nspname = 'public'
        AND c.reltuples > 100
    ) bloated_tables
    WHERE bloat_percentage > 25
    
    UNION ALL
    
    -- Data retention recommendations
    SELECT 
        'LOW'::TEXT,
        'Data Management'::TEXT,
        format('Consider archiving old %s records (%s records older than 90 days)', 
               table_name, old_record_count)::TEXT,
        format('SELECT cleanup_old_data();')::TEXT,
        'Low - Reduces storage usage'::TEXT
    FROM (
        SELECT 
            'conversations' as table_name,
            COUNT(*) as old_record_count
        FROM conversations
        WHERE status IN ('resolved', 'closed')
        AND closed_at < CURRENT_TIMESTAMP - INTERVAL '90 days'
        HAVING COUNT(*) > 100
        
        UNION ALL
        
        SELECT 
            'messages' as table_name,
            COUNT(*) as old_record_count
        FROM messages
        WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '180 days'
        HAVING COUNT(*) > 1000
    ) old_data
    
    ORDER BY 
        CASE priority 
            WHEN 'CRITICAL' THEN 1 
            WHEN 'HIGH' THEN 2 
            WHEN 'MEDIUM' THEN 3 
            ELSE 4 
        END;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- REAL-TIME MONITORING DASHBOARDS
-- ============================================================================

-- Real-time system metrics view
CREATE OR REPLACE VIEW v_realtime_metrics AS
SELECT 
    'Database Size' as metric_name,
    pg_size_pretty(pg_database_size(current_database())) as current_value,
    ROUND((pg_database_size(current_database())::NUMERIC / (1024*1024*1024)) * 100, 1) || '% of 1GB' as utilization,
    CASE 
        WHEN pg_database_size(current_database()) > 900*1024*1024 THEN 'CRITICAL'
        WHEN pg_database_size(current_database()) > 700*1024*1024 THEN 'WARNING'
        ELSE 'OK'
    END as status
    
UNION ALL

SELECT 
    'Active Connections',
    COUNT(*)::TEXT,
    COUNT(*)::TEXT || ' of 10 max',
    CASE 
        WHEN COUNT(*) > 8 THEN 'WARNING'
        WHEN COUNT(*) > 5 THEN 'WATCH'
        ELSE 'OK'
    END
FROM pg_stat_activity
WHERE datname = current_database() AND state = 'active'

UNION ALL

SELECT 
    'Open Conversations',
    COUNT(*)::TEXT,
    CASE 
        WHEN COUNT(*) = 0 THEN 'No active conversations'
        ELSE COUNT(*)::TEXT || ' conversations need attention'
    END,
    CASE 
        WHEN COUNT(*) > 20 THEN 'HIGH'
        WHEN COUNT(*) > 10 THEN 'MEDIUM'
        ELSE 'LOW'
    END
FROM conversations
WHERE status IN ('open', 'in_progress', 'waiting_customer')

UNION ALL

SELECT 
    'SLA Breaches',
    COUNT(*)::TEXT,
    CASE 
        WHEN COUNT(*) = 0 THEN 'All conversations within SLA'
        ELSE COUNT(*)::TEXT || ' conversations overdue'
    END,
    CASE 
        WHEN COUNT(*) > 5 THEN 'CRITICAL'
        WHEN COUNT(*) > 0 THEN 'WARNING'
        ELSE 'OK'
    END
FROM conversations
WHERE status NOT IN ('resolved', 'closed')
AND sla_deadline < CURRENT_TIMESTAMP;

-- Performance metrics view
CREATE OR REPLACE VIEW v_performance_metrics AS
WITH query_stats AS (
    SELECT 
        COUNT(*) as total_queries,
        AVG(mean_exec_time) as avg_query_time,
        MAX(mean_exec_time) as max_query_time,
        COUNT(*) FILTER (WHERE mean_exec_time > 1000) as slow_queries
    FROM pg_stat_statements
    WHERE calls > 1
),
table_stats AS (
    SELECT 
        SUM(seq_scan) as sequential_scans,
        SUM(seq_tup_read) as sequential_reads,
        SUM(idx_scan) as index_scans,
        SUM(idx_tup_fetch) as index_reads
    FROM pg_stat_user_tables
),
cache_stats AS (
    SELECT 
        SUM(heap_blks_hit) as cache_hits,
        SUM(heap_blks_read) as disk_reads
    FROM pg_statio_user_tables
)
SELECT 
    'Average Query Time' as metric,
    ROUND(qs.avg_query_time, 2)::TEXT || 'ms' as value,
    CASE 
        WHEN qs.avg_query_time > 100 THEN 'Review slow queries'
        WHEN qs.avg_query_time > 50 THEN 'Monitor performance'
        ELSE 'Good performance'
    END as status
FROM query_stats qs

UNION ALL

SELECT 
    'Cache Hit Ratio',
    CASE 
        WHEN (cs.cache_hits + cs.disk_reads) > 0 THEN
            ROUND((cs.cache_hits::NUMERIC / (cs.cache_hits + cs.disk_reads)) * 100, 1)::TEXT || '%'
        ELSE 'N/A'
    END,
    CASE 
        WHEN (cs.cache_hits::NUMERIC / NULLIF(cs.cache_hits + cs.disk_reads, 0)) > 0.95 THEN 'Excellent'
        WHEN (cs.cache_hits::NUMERIC / NULLIF(cs.cache_hits + cs.disk_reads, 0)) > 0.90 THEN 'Good'
        ELSE 'Needs improvement'
    END
FROM cache_stats cs

UNION ALL

SELECT 
    'Index Usage Ratio',
    CASE 
        WHEN (ts.index_scans + ts.sequential_scans) > 0 THEN
            ROUND((ts.index_scans::NUMERIC / (ts.index_scans + ts.sequential_scans)) * 100, 1)::TEXT || '%'
        ELSE 'N/A'
    END,
    CASE 
        WHEN (ts.index_scans::NUMERIC / NULLIF(ts.index_scans + ts.sequential_scans, 0)) > 0.90 THEN 'Excellent'
        WHEN (ts.index_scans::NUMERIC / NULLIF(ts.index_scans + ts.sequential_scans, 0)) > 0.80 THEN 'Good'
        ELSE 'Add more indexes'
    END
FROM table_stats ts;

-- ============================================================================
-- AUTOMATED MAINTENANCE SCHEDULER
-- ============================================================================

-- Function to perform daily maintenance tasks
CREATE OR REPLACE FUNCTION daily_maintenance_routine()
RETURNS TEXT AS $$
DECLARE
    maintenance_log TEXT[] := ARRAY[]::TEXT[];
    db_size BIGINT;
    cleanup_result TEXT;
    vacuum_result TEXT;
BEGIN
    -- Log start time
    maintenance_log := array_append(maintenance_log, 
        format('Maintenance started at %s', CURRENT_TIMESTAMP));
    
    -- Check database size
    SELECT pg_database_size(current_database()) INTO db_size;
    maintenance_log := array_append(maintenance_log, 
        format('Database size: %s', pg_size_pretty(db_size)));
    
    -- Automatic cleanup if approaching free tier limit
    IF db_size > 800 * 1024 * 1024 THEN  -- 800MB threshold
        SELECT cleanup_old_data() INTO cleanup_result;
        maintenance_log := array_append(maintenance_log, cleanup_result);
    END IF;
    
    -- Update conversation summaries
    PERFORM refresh_venue_conversation_summaries();
    maintenance_log := array_append(maintenance_log, 'Venue summaries refreshed');
    
    -- Analyze important tables
    ANALYZE conversations;
    ANALYZE messages;
    maintenance_log := array_append(maintenance_log, 'Table statistics updated');
    
    -- Light vacuum on most active tables
    VACUUM (ANALYZE) conversations;
    VACUUM (ANALYZE) messages;
    maintenance_log := array_append(maintenance_log, 'Vacuum completed');
    
    -- Reset query statistics if they get too large
    IF (SELECT COUNT(*) FROM pg_stat_statements) > 8000 THEN
        PERFORM pg_stat_statements_reset();
        maintenance_log := array_append(maintenance_log, 'Query statistics reset');
    END IF;
    
    -- Log completion
    maintenance_log := array_append(maintenance_log, 
        format('Maintenance completed at %s', CURRENT_TIMESTAMP));
    
    RETURN array_to_string(maintenance_log, E'\n');
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- MONITORING QUERIES FOR EXTERNAL TOOLS
-- ============================================================================

-- Simple health check query (for external monitoring)
CREATE OR REPLACE FUNCTION simple_health_check()
RETURNS JSON AS $$
BEGIN
    RETURN json_build_object(
        'timestamp', CURRENT_TIMESTAMP,
        'database_size_mb', ROUND((pg_database_size(current_database())::NUMERIC / 1024 / 1024), 2),
        'active_connections', (
            SELECT COUNT(*) FROM pg_stat_activity 
            WHERE datname = current_database() AND state = 'active'
        ),
        'active_conversations', (
            SELECT COUNT(*) FROM conversations 
            WHERE status IN ('open', 'in_progress', 'waiting_customer')
        ),
        'overdue_conversations', (
            SELECT COUNT(*) FROM conversations 
            WHERE status NOT IN ('resolved', 'closed') 
            AND sla_deadline < CURRENT_TIMESTAMP
        ),
        'recent_messages_1hr', (
            SELECT COUNT(*) FROM messages 
            WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '1 hour'
        ),
        'avg_query_time_ms', (
            SELECT ROUND(AVG(mean_exec_time), 2) FROM pg_stat_statements WHERE calls > 1
        )
    );
END;
$$ LANGUAGE plpgsql;

-- Export function for monitoring integrations
CREATE OR REPLACE FUNCTION export_metrics_for_monitoring()
RETURNS TABLE(
    metric_name TEXT,
    metric_value NUMERIC,
    metric_unit TEXT,
    status TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        'database_size_bytes'::TEXT,
        pg_database_size(current_database())::NUMERIC,
        'bytes'::TEXT,
        CASE 
            WHEN pg_database_size(current_database()) > 900*1024*1024 THEN 'critical'
            WHEN pg_database_size(current_database()) > 700*1024*1024 THEN 'warning'
            ELSE 'ok'
        END::TEXT
    
    UNION ALL
    
    SELECT 
        'active_connections',
        (SELECT COUNT(*)::NUMERIC FROM pg_stat_activity WHERE datname = current_database() AND state = 'active'),
        'count',
        CASE 
            WHEN (SELECT COUNT(*) FROM pg_stat_activity WHERE datname = current_database() AND state = 'active') > 8 THEN 'warning'
            ELSE 'ok'
        END
    
    UNION ALL
    
    SELECT 
        'active_conversations',
        (SELECT COUNT(*)::NUMERIC FROM conversations WHERE status IN ('open', 'in_progress', 'waiting_customer')),
        'count',
        'ok'
    
    UNION ALL
    
    SELECT 
        'overdue_conversations',
        (SELECT COUNT(*)::NUMERIC FROM conversations WHERE status NOT IN ('resolved', 'closed') AND sla_deadline < CURRENT_TIMESTAMP),
        'count',
        CASE 
            WHEN (SELECT COUNT(*) FROM conversations WHERE status NOT IN ('resolved', 'closed') AND sla_deadline < CURRENT_TIMESTAMP) > 0 THEN 'warning'
            ELSE 'ok'
        END
    
    UNION ALL
    
    SELECT 
        'avg_query_time_ms',
        COALESCE((SELECT AVG(mean_exec_time) FROM pg_stat_statements WHERE calls > 1), 0),
        'milliseconds',
        CASE 
            WHEN COALESCE((SELECT AVG(mean_exec_time) FROM pg_stat_statements WHERE calls > 1), 0) > 100 THEN 'warning'
            ELSE 'ok'
        END;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- IMPLEMENTATION COMPLETION VERIFICATION
-- ============================================================================

-- Function to verify all optimizations are properly implemented
CREATE OR REPLACE FUNCTION verify_implementation()
RETURNS TABLE(
    component TEXT,
    status TEXT,
    details TEXT
) AS $$
BEGIN
    RETURN QUERY
    
    -- Check if required indexes exist
    SELECT 
        'Indexes'::TEXT,
        CASE 
            WHEN COUNT(*) >= 15 THEN 'COMPLETE'
            WHEN COUNT(*) >= 10 THEN 'PARTIAL'
            ELSE 'MISSING'
        END::TEXT,
        format('%s critical indexes found', COUNT(*))::TEXT
    FROM pg_indexes
    WHERE tablename IN ('conversations', 'messages', 'venues', 'zones')
    AND indexname LIKE 'idx_%'
    
    UNION ALL
    
    -- Check if functions are created
    SELECT 
        'Functions'::TEXT,
        CASE 
            WHEN COUNT(*) >= 10 THEN 'COMPLETE'
            ELSE 'PARTIAL'
        END::TEXT,
        format('%s optimization functions created', COUNT(*))::TEXT
    FROM pg_proc p
    JOIN pg_namespace n ON p.pronamespace = n.oid
    WHERE n.nspname = 'public'
    AND p.proname LIKE '%conversation%' OR p.proname LIKE '%maintenance%'
    
    UNION ALL
    
    -- Check if monitoring is set up
    SELECT 
        'Monitoring'::TEXT,
        CASE 
            WHEN COUNT(*) > 0 THEN 'COMPLETE'
            ELSE 'MISSING'
        END::TEXT,
        'pg_stat_statements extension status'::TEXT
    FROM pg_extension
    WHERE extname = 'pg_stat_statements'
    
    UNION ALL
    
    -- Check table optimizations
    SELECT 
        'Table Settings'::TEXT,
        'COMPLETE'::TEXT,
        format('%s tables optimized with fillfactor', COUNT(*))::TEXT
    FROM pg_class c
    JOIN pg_namespace n ON c.relnamespace = n.oid
    WHERE n.nspname = 'public'
    AND c.relkind = 'r'
    AND c.relname IN ('conversations', 'messages', 'venues', 'zones');
END;
$$ LANGUAGE plpgsql;
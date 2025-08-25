-- BMA Social Database Optimizations
-- Production-ready PostgreSQL optimizations for high-volume operations
-- Target: 2000+ venues, 120K+ API calls/hour, 10M+ logs/month

-- ============================================================================
-- CONFIGURATION PARAMETERS (for postgresql.conf or ALTER SYSTEM)
-- ============================================================================

-- Memory Configuration (for 16GB RAM server on Render)
ALTER SYSTEM SET shared_buffers = '4GB';                -- 25% of RAM
ALTER SYSTEM SET effective_cache_size = '12GB';         -- 75% of RAM
ALTER SYSTEM SET maintenance_work_mem = '1GB';          -- For VACUUM, CREATE INDEX
ALTER SYSTEM SET work_mem = '32MB';                     -- Per operation memory
ALTER SYSTEM SET wal_buffers = '16MB';                  -- Write-ahead log buffer

-- Connection Pool Settings (matching our app configuration)
ALTER SYSTEM SET max_connections = 200;                 -- Total connections
ALTER SYSTEM SET superuser_reserved_connections = 3;    -- Reserved for admin

-- Checkpoint and WAL Settings
ALTER SYSTEM SET checkpoint_completion_target = 0.9;    -- Spread checkpoint I/O
ALTER SYSTEM SET wal_compression = on;                  -- Compress WAL
ALTER SYSTEM SET max_wal_size = '4GB';                 -- Maximum WAL size
ALTER SYSTEM SET min_wal_size = '1GB';                 -- Minimum WAL size

-- Query Planner Optimizations
ALTER SYSTEM SET random_page_cost = 1.1;               -- SSD optimization
ALTER SYSTEM SET effective_io_concurrency = 200;       -- SSD parallel I/O
ALTER SYSTEM SET default_statistics_target = 100;      -- Better query plans

-- Parallel Query Execution
ALTER SYSTEM SET max_worker_processes = 8;             -- Total worker processes
ALTER SYSTEM SET max_parallel_workers_per_gather = 4;  -- Per-query parallelism
ALTER SYSTEM SET max_parallel_workers = 8;             -- Total parallel workers
ALTER SYSTEM SET max_parallel_maintenance_workers = 4; -- For CREATE INDEX, VACUUM

-- Statement Timeout Protection
ALTER SYSTEM SET statement_timeout = '30s';            -- Kill long queries
ALTER SYSTEM SET lock_timeout = '10s';                 -- Prevent lock waits
ALTER SYSTEM SET idle_in_transaction_session_timeout = '60s'; -- Kill idle transactions

-- Autovacuum Tuning (critical for high-write workload)
ALTER SYSTEM SET autovacuum_max_workers = 4;
ALTER SYSTEM SET autovacuum_naptime = '30s';          -- Check every 30 seconds
ALTER SYSTEM SET autovacuum_vacuum_threshold = 50;
ALTER SYSTEM SET autovacuum_vacuum_scale_factor = 0.1; -- Vacuum at 10% dead tuples
ALTER SYSTEM SET autovacuum_analyze_threshold = 50;
ALTER SYSTEM SET autovacuum_analyze_scale_factor = 0.05; -- Analyze at 5% changes

-- Logging for Performance Analysis
ALTER SYSTEM SET log_min_duration_statement = 100;     -- Log queries > 100ms
ALTER SYSTEM SET log_checkpoints = on;
ALTER SYSTEM SET log_connections = on;
ALTER SYSTEM SET log_disconnections = on;
ALTER SYSTEM SET log_lock_waits = on;
ALTER SYSTEM SET log_temp_files = 0;
ALTER SYSTEM SET log_autovacuum_min_duration = 0;

-- Apply configuration changes
SELECT pg_reload_conf();

-- ============================================================================
-- TABLE OPTIMIZATIONS
-- ============================================================================

-- VENUES table (2000+ records, frequent reads)
CREATE TABLE IF NOT EXISTS venues (
    id SERIAL PRIMARY KEY,
    external_id VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    brand_id INTEGER,
    region VARCHAR(100),
    timezone VARCHAR(50),
    configuration JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    last_sync_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
) WITH (
    fillfactor = 90,  -- Leave 10% space for updates
    autovacuum_vacuum_scale_factor = 0.05,
    autovacuum_analyze_scale_factor = 0.02
);

-- Optimized indexes for venues
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_venues_status 
    ON venues(status) 
    WHERE status IN ('active', 'inactive', 'pending');

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_venues_brand_region 
    ON venues(brand_id, region) 
    INCLUDE (name, status);  -- Covering index

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_venues_last_sync 
    ON venues(last_sync_at DESC NULLS LAST)
    WHERE status = 'active';

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_venues_config_gin 
    ON venues USING GIN (configuration);

-- ZONES table (10,000+ records, constant updates)
CREATE TABLE IF NOT EXISTS zones (
    id SERIAL PRIMARY KEY,
    venue_id INTEGER NOT NULL REFERENCES venues(id),
    external_id VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    zone_type VARCHAR(50),
    configuration JSONB DEFAULT '{}',
    current_status VARCHAR(50),
    last_status_change TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
) WITH (
    fillfactor = 80,  -- More update space
    autovacuum_vacuum_scale_factor = 0.05,
    autovacuum_analyze_scale_factor = 0.02
);

-- Optimized indexes for zones
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_zones_venue_id 
    ON zones(venue_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_zones_status_change 
    ON zones(venue_id, last_status_change DESC)
    WHERE current_status != 'offline';

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_zones_type_status 
    ON zones(zone_type, current_status)
    INCLUDE (name, venue_id);

-- CONVERSATIONS table (1M+ records/year, partitioned by month)
CREATE TABLE IF NOT EXISTS conversations (
    id BIGSERIAL,
    venue_id INTEGER NOT NULL,
    zone_id INTEGER,
    contact_id BIGINT NOT NULL,
    channel VARCHAR(50) NOT NULL,
    thread_id VARCHAR(255),
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    last_message_at TIMESTAMP WITH TIME ZONE,
    message_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- Create partitions for conversations (automated via pg_partman in production)
CREATE TABLE IF NOT EXISTS conversations_2024_01 
    PARTITION OF conversations 
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE IF NOT EXISTS conversations_2024_02 
    PARTITION OF conversations 
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');

-- Indexes for conversations (created on parent, inherited by partitions)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_conversations_venue_created 
    ON conversations(venue_id, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_conversations_contact_channel 
    ON conversations(contact_id, channel, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_conversations_status_active 
    ON conversations(status, last_message_at DESC)
    WHERE status = 'active';

-- MONITORING_LOGS table (10M+ records/month, time-series data)
CREATE TABLE IF NOT EXISTS monitoring_logs (
    id BIGSERIAL,
    venue_id INTEGER NOT NULL,
    zone_id INTEGER,
    event_type VARCHAR(50) NOT NULL,
    event_level VARCHAR(20) DEFAULT 'info',
    event_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- Create partitions for monitoring_logs
CREATE TABLE IF NOT EXISTS monitoring_logs_2024_01 
    PARTITION OF monitoring_logs 
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01')
    WITH (
        fillfactor = 100,  -- No updates expected
        autovacuum_enabled = false  -- Disable for append-only
    );

-- BRIN index for time-series data (very space-efficient)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_monitoring_logs_created_brin 
    ON monitoring_logs USING BRIN (created_at)
    WITH (pages_per_range = 128);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_monitoring_logs_venue_time 
    ON monitoring_logs(venue_id, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_monitoring_logs_event_type 
    ON monitoring_logs(event_type, created_at DESC)
    WHERE event_level IN ('error', 'warning');

-- ALERTS table (real-time operations)
CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    venue_id INTEGER NOT NULL REFERENCES venues(id),
    zone_id INTEGER,
    alert_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    message TEXT,
    metadata JSONB DEFAULT '{}',
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
) WITH (
    fillfactor = 85,
    autovacuum_vacuum_scale_factor = 0.02,  -- Aggressive vacuum
    autovacuum_analyze_scale_factor = 0.01
);

-- Indexes for real-time alert queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_alerts_pending 
    ON alerts(venue_id, created_at DESC)
    WHERE status = 'pending';

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_alerts_severity_type 
    ON alerts(severity, alert_type, created_at DESC)
    WHERE status NOT IN ('resolved', 'dismissed');

-- CAMPAIGNS table (bulk operations)
CREATE TABLE IF NOT EXISTS campaigns (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    campaign_type VARCHAR(50) NOT NULL,
    target_venues INTEGER[] DEFAULT '{}',
    target_zones INTEGER[] DEFAULT '{}',
    configuration JSONB DEFAULT '{}',
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    scheduled_at TIMESTAMP WITH TIME ZONE,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    statistics JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
) WITH (
    fillfactor = 90
);

-- GIN index for array operations
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_campaigns_venues_gin 
    ON campaigns USING GIN (target_venues);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_campaigns_zones_gin 
    ON campaigns USING GIN (target_zones);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_campaigns_scheduled 
    ON campaigns(scheduled_at, status)
    WHERE status IN ('scheduled', 'pending');

-- ============================================================================
-- MATERIALIZED VIEWS FOR ANALYTICS
-- ============================================================================

-- Hourly venue statistics (refreshed every hour)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_venue_hourly_stats AS
SELECT 
    v.id as venue_id,
    v.name as venue_name,
    DATE_TRUNC('hour', ml.created_at) as hour,
    COUNT(DISTINCT ml.zone_id) as active_zones,
    COUNT(*) as event_count,
    COUNT(*) FILTER (WHERE ml.event_level = 'error') as error_count,
    COUNT(*) FILTER (WHERE ml.event_level = 'warning') as warning_count,
    AVG((ml.event_data->>'response_time')::float) as avg_response_time
FROM venues v
LEFT JOIN monitoring_logs ml ON v.id = ml.venue_id
WHERE ml.created_at >= NOW() - INTERVAL '7 days'
GROUP BY v.id, v.name, DATE_TRUNC('hour', ml.created_at)
WITH DATA;

CREATE UNIQUE INDEX ON mv_venue_hourly_stats (venue_id, hour);
CREATE INDEX ON mv_venue_hourly_stats (hour DESC);

-- Daily conversation summary
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_daily_conversation_stats AS
SELECT 
    DATE_TRUNC('day', created_at) as day,
    venue_id,
    channel,
    COUNT(*) as conversation_count,
    COUNT(DISTINCT contact_id) as unique_contacts,
    AVG(message_count) as avg_messages_per_conversation,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY message_count) as median_messages
FROM conversations
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE_TRUNC('day', created_at), venue_id, channel
WITH DATA;

CREATE UNIQUE INDEX ON mv_daily_conversation_stats (day, venue_id, channel);

-- ============================================================================
-- PERFORMANCE MONITORING QUERIES
-- ============================================================================

-- Create extension for advanced monitoring
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Function to analyze table bloat
CREATE OR REPLACE FUNCTION check_table_bloat()
RETURNS TABLE(
    schemaname TEXT,
    tablename TEXT,
    bloat_ratio NUMERIC,
    wasted_bytes BIGINT,
    table_size TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        schemaname::TEXT,
        tablename::TEXT,
        ROUND(bloat_ratio::numeric, 2) as bloat_ratio,
        wasted_bytes::BIGINT,
        pg_size_pretty(table_bytes) as table_size
    FROM (
        SELECT 
            schemaname,
            tablename,
            CASE WHEN table_bytes > 0
                THEN (table_bytes - (ceil(reltuples * 
                    (24 + avg_width))::BIGINT))::NUMERIC / table_bytes::NUMERIC
                ELSE 0 
            END as bloat_ratio,
            CASE WHEN table_bytes > 0
                THEN table_bytes - (ceil(reltuples * (24 + avg_width))::BIGINT)
                ELSE 0 
            END as wasted_bytes,
            table_bytes
        FROM (
            SELECT
                schemaname,
                tablename,
                cc.reltuples,
                pg_relation_size(cc.oid) AS table_bytes,
                ceil((cc.reltuples * (
                    (SELECT avg(attlen) FROM pg_attribute WHERE attrelid = cc.oid)
                ))::NUMERIC) as avg_width
            FROM pg_class cc
            JOIN pg_namespace nn ON cc.relnamespace = nn.oid
            WHERE cc.relkind = 'r'
            AND nn.nspname NOT IN ('pg_catalog', 'information_schema')
        ) AS ss
    ) AS tt
    WHERE bloat_ratio > 0.2  -- Show tables with >20% bloat
    ORDER BY wasted_bytes DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to find missing indexes
CREATE OR REPLACE FUNCTION suggest_missing_indexes()
RETURNS TABLE(
    table_name TEXT,
    column_name TEXT,
    index_suggestion TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        t.tablename::TEXT,
        a.attname::TEXT,
        format('CREATE INDEX CONCURRENTLY idx_%s_%s ON %s(%s);', 
               t.tablename, a.attname, t.tablename, a.attname)::TEXT
    FROM pg_stats s
    JOIN pg_attribute a ON a.attname = s.attname
    JOIN pg_class c ON c.oid = a.attrelid
    JOIN pg_tables t ON t.tablename = c.relname
    WHERE s.null_frac < 0.5  -- Column is mostly not null
    AND s.n_distinct > 100    -- Has good cardinality
    AND t.schemaname = 'public'
    AND NOT EXISTS (  -- No index exists
        SELECT 1 FROM pg_indexes i 
        WHERE i.tablename = t.tablename 
        AND i.indexdef LIKE '%' || a.attname || '%'
    )
    ORDER BY s.n_distinct DESC
    LIMIT 10;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- MAINTENANCE PROCEDURES
-- ============================================================================

-- Automated partition creation for time-series tables
CREATE OR REPLACE FUNCTION create_monthly_partitions()
RETURNS void AS $$
DECLARE
    start_date DATE;
    end_date DATE;
    partition_name TEXT;
BEGIN
    -- Create partitions for next 3 months
    FOR i IN 0..2 LOOP
        start_date := DATE_TRUNC('month', CURRENT_DATE + (i || ' months')::INTERVAL);
        end_date := start_date + INTERVAL '1 month';
        
        -- For conversations table
        partition_name := 'conversations_' || TO_CHAR(start_date, 'YYYY_MM');
        IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = partition_name) THEN
            EXECUTE format('CREATE TABLE %I PARTITION OF conversations FOR VALUES FROM (%L) TO (%L)',
                          partition_name, start_date, end_date);
            RAISE NOTICE 'Created partition: %', partition_name;
        END IF;
        
        -- For monitoring_logs table
        partition_name := 'monitoring_logs_' || TO_CHAR(start_date, 'YYYY_MM');
        IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = partition_name) THEN
            EXECUTE format('CREATE TABLE %I PARTITION OF monitoring_logs FOR VALUES FROM (%L) TO (%L)',
                          partition_name, start_date, end_date);
            RAISE NOTICE 'Created partition: %', partition_name;
        END IF;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Schedule partition creation (run monthly)
-- In production, use pg_cron or external scheduler
-- SELECT cron.schedule('create-partitions', '0 0 1 * *', 'SELECT create_monthly_partitions();');

-- ============================================================================
-- GRANT PERMISSIONS (adjust for your users)
-- ============================================================================

-- Create read-only user for analytics
-- CREATE USER analytics_reader WITH PASSWORD 'secure_password';
-- GRANT CONNECT ON DATABASE bma_social TO analytics_reader;
-- GRANT USAGE ON SCHEMA public TO analytics_reader;
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO analytics_reader;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO analytics_reader;

-- Create application user with appropriate permissions
-- CREATE USER app_user WITH PASSWORD 'secure_password';
-- GRANT CONNECT ON DATABASE bma_social TO app_user;
-- GRANT USAGE ON SCHEMA public TO app_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;

-- ============================================================================
-- MONITORING QUERIES
-- ============================================================================

-- Check current connections and activity
CREATE OR REPLACE VIEW v_connection_stats AS
SELECT 
    datname,
    usename,
    application_name,
    state,
    COUNT(*) as connection_count,
    MAX(EXTRACT(EPOCH FROM (NOW() - query_start))) as max_query_duration_seconds
FROM pg_stat_activity
WHERE datname = current_database()
GROUP BY datname, usename, application_name, state
ORDER BY connection_count DESC;

-- Check slow queries
CREATE OR REPLACE VIEW v_slow_queries AS
SELECT 
    query,
    mean_exec_time,
    calls,
    total_exec_time,
    min_exec_time,
    max_exec_time,
    stddev_exec_time
FROM pg_stat_statements
WHERE mean_exec_time > 100  -- Queries averaging > 100ms
ORDER BY mean_exec_time DESC
LIMIT 20;

-- Check index usage
CREATE OR REPLACE VIEW v_index_usage AS
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes
ORDER BY idx_scan ASC
LIMIT 20;

-- ============================================================================
-- INITIAL DATA ANALYSIS
-- ============================================================================

-- Analyze all tables for query planner
ANALYZE;

-- Update table statistics for critical tables
ANALYZE venues;
ANALYZE zones;
ANALYZE conversations;
ANALYZE monitoring_logs;
ANALYZE alerts;
ANALYZE campaigns;
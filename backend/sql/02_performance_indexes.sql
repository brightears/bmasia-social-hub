-- BMA Social - Advanced Indexing Strategy
-- Optimized for <100ms response times on conversation queries
-- Covers WhatsApp bot integration and real-time status updates

-- ============================================================================
-- COMPOSITE INDEXES FOR MULTI-COLUMN QUERIES
-- ============================================================================

-- Venue-based conversation filtering (most common query pattern)
CREATE INDEX CONCURRENTLY idx_conversations_venue_status_priority 
    ON conversations (venue_id, status, priority, created_at DESC)
    INCLUDE (customer_name, message_count, last_activity_at);

-- Channel-specific active conversations
CREATE INDEX CONCURRENTLY idx_conversations_channel_active 
    ON conversations (channel, status, created_at DESC)
    WHERE status IN ('open', 'in_progress', 'waiting_customer')
    INCLUDE (venue_id, customer_name, priority);

-- SLA management - critical for real-time alerts
CREATE INDEX CONCURRENTLY idx_conversations_sla_urgent 
    ON conversations (sla_deadline, priority, status)
    WHERE sla_deadline IS NOT NULL 
    AND status NOT IN ('resolved', 'closed')
    INCLUDE (venue_id, customer_name, assigned_to);

-- Bot escalation patterns
CREATE INDEX CONCURRENTLY idx_conversations_bot_needs_attention 
    ON conversations (bot_escalated, bot_confidence_score, status, created_at DESC)
    WHERE (bot_escalated = TRUE OR bot_confidence_score < 0.7)
    AND status NOT IN ('resolved', 'closed');

-- Team member workload distribution
CREATE INDEX CONCURRENTLY idx_conversations_assigned_workload 
    ON conversations (assigned_to, status, priority, created_at DESC)
    WHERE assigned_to IS NOT NULL
    INCLUDE (venue_id, message_count, last_activity_at);

-- Customer interaction history (for WhatsApp threading)
CREATE INDEX CONCURRENTLY idx_conversations_customer_history 
    ON conversations (customer_phone, channel, created_at DESC)
    WHERE customer_phone IS NOT NULL
    INCLUDE (venue_id, status, message_count);

CREATE INDEX CONCURRENTLY idx_conversations_customer_id_history 
    ON conversations (customer_id, channel, created_at DESC)
    WHERE customer_id IS NOT NULL
    INCLUDE (venue_id, status, message_count);

-- ============================================================================
-- MESSAGE RETRIEVAL OPTIMIZATIONS
-- ============================================================================

-- Conversation thread retrieval (primary query pattern)
CREATE INDEX CONCURRENTLY idx_messages_conversation_thread 
    ON messages (conversation_id, created_at DESC)
    INCLUDE (sender_type, sender_name, content, content_type, attachment_url, is_read);

-- Unread message tracking per conversation
CREATE INDEX CONCURRENTLY idx_messages_unread_by_conversation 
    ON messages (conversation_id, is_read, created_at DESC)
    WHERE is_read = FALSE
    INCLUDE (sender_type, content);

-- WhatsApp message ID lookup (for status updates)
CREATE INDEX CONCURRENTLY idx_messages_whatsapp_external_id 
    ON messages (external_id, channel)
    WHERE external_id IS NOT NULL;

-- Message threading support
CREATE INDEX CONCURRENTLY idx_messages_reply_chain 
    ON messages (reply_to_id, created_at)
    WHERE reply_to_id IS NOT NULL
    INCLUDE (conversation_id, sender_type, content);

-- AI intent analysis queries
CREATE INDEX CONCURRENTLY idx_messages_intent_analysis 
    ON messages (intent, confidence_score, created_at DESC)
    WHERE intent IS NOT NULL
    INCLUDE (conversation_id, sender_type, content);

-- Recent activity tracking (for dashboard)
CREATE INDEX CONCURRENTLY idx_messages_recent_activity 
    ON messages (created_at DESC, sender_type)
    WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '24 hours'
    INCLUDE (conversation_id, content, attachment_url);

-- ============================================================================
-- VENUE AND ZONE PERFORMANCE INDEXES
-- ============================================================================

-- Active venue monitoring (core BMA Social functionality)
CREATE INDEX CONCURRENTLY idx_venues_active_monitoring 
    ON venues (is_active, monitoring_enabled, country)
    INCLUDE (name, brand, timezone, primary_contact_phone, whatsapp_number);

-- Zone status updates (high-frequency operations)
CREATE INDEX CONCURRENTLY idx_zones_status_updates 
    ON zones (venue_id, current_status, last_status_change DESC)
    INCLUDE (name, zone_type);

-- Venue health score calculations
CREATE INDEX CONCURRENTLY idx_venues_health_metrics 
    ON venues (is_active, total_zones, active_zones, last_month_uptime)
    INCLUDE (name, brand, country);

-- ============================================================================
-- SEARCH AND ANALYTICS INDEXES
-- ============================================================================

-- Full-text search across conversations
CREATE INDEX CONCURRENTLY idx_conversations_fulltext_search 
    ON conversations USING GIN (
        to_tsvector('english', 
            COALESCE(subject, '') || ' ' || 
            COALESCE(category, '') || ' ' ||
            COALESCE(subcategory, '') || ' ' ||
            COALESCE(customer_name, '') || ' ' ||
            COALESCE(bot_escalation_reason, '')
        )
    );

-- Message content search
CREATE INDEX CONCURRENTLY idx_messages_content_fulltext 
    ON messages USING GIN (
        to_tsvector('english', content)
    );

-- Analytics: conversation patterns by time
CREATE INDEX CONCURRENTLY idx_conversations_time_analytics 
    ON conversations (
        DATE_TRUNC('hour', created_at),
        channel,
        status,
        venue_id
    ) INCLUDE (priority, message_count, resolution_time_seconds);

-- Satisfaction score analytics
CREATE INDEX CONCURRENTLY idx_conversations_satisfaction_analytics 
    ON conversations (satisfaction_score, channel, created_at)
    WHERE satisfaction_score IS NOT NULL
    INCLUDE (venue_id, resolution_time_seconds, bot_handled);

-- ============================================================================
-- JSONB OPTIMIZATIONS FOR METADATA
-- ============================================================================

-- Conversation metadata queries (flexible filtering)
CREATE INDEX CONCURRENTLY idx_conversations_metadata_gin 
    ON conversations USING GIN (metadata);

-- Common metadata path queries
CREATE INDEX CONCURRENTLY idx_conversations_metadata_customer_type 
    ON conversations ((metadata->>'customer_type'))
    WHERE metadata->>'customer_type' IS NOT NULL;

CREATE INDEX CONCURRENTLY idx_conversations_metadata_source 
    ON conversations ((metadata->>'source'))
    WHERE metadata->>'source' IS NOT NULL;

-- Message entities for AI analysis
CREATE INDEX CONCURRENTLY idx_messages_entities_gin 
    ON messages USING GIN (entities)
    WHERE entities IS NOT NULL;

-- Actions taken by bot
CREATE INDEX CONCURRENTLY idx_messages_actions_gin 
    ON messages USING GIN (actions)
    WHERE actions IS NOT NULL;

-- ============================================================================
-- PARTIAL INDEXES FOR SPECIFIC USE CASES
-- ============================================================================

-- Only index active conversations for most queries
CREATE INDEX CONCURRENTLY idx_conversations_active_only 
    ON conversations (venue_id, created_at DESC, priority)
    WHERE is_active = TRUE
    INCLUDE (status, customer_name, message_count, last_activity_at);

-- High-priority conversations needing attention
CREATE INDEX CONCURRENTLY idx_conversations_urgent_attention 
    ON conversations (created_at DESC, sla_deadline)
    WHERE priority IN ('high', 'urgent') 
    AND status NOT IN ('resolved', 'closed')
    INCLUDE (venue_id, customer_name, assigned_to);

-- Failed message deliveries for retry processing
CREATE INDEX CONCURRENTLY idx_messages_failed_delivery 
    ON messages (created_at, failure_reason)
    WHERE failed_delivery = TRUE
    INCLUDE (conversation_id, external_id, content);

-- Bot-handled conversations for training analysis
CREATE INDEX CONCURRENTLY idx_conversations_bot_training 
    ON conversations (bot_confidence_score, created_at DESC)
    WHERE bot_handled = TRUE
    INCLUDE (channel, message_count, satisfaction_score);

-- ============================================================================
-- INDEX MAINTENANCE AND MONITORING
-- ============================================================================

-- Function to analyze index usage and suggest improvements
CREATE OR REPLACE FUNCTION analyze_index_performance()
RETURNS TABLE(
    table_name TEXT,
    index_name TEXT,
    index_size TEXT,
    index_scans BIGINT,
    tuples_read BIGINT,
    tuples_fetched BIGINT,
    usage_ratio NUMERIC,
    recommendation TEXT
) AS $$
BEGIN
    RETURN QUERY
    WITH index_stats AS (
        SELECT 
            schemaname,
            tablename,
            indexrelname,
            pg_size_pretty(pg_relation_size(indexrelid)) as size,
            idx_scan,
            idx_tup_read,
            idx_tup_fetch,
            CASE 
                WHEN idx_scan = 0 THEN 0
                WHEN idx_tup_read = 0 THEN 0
                ELSE ROUND((idx_tup_fetch::NUMERIC / idx_tup_read::NUMERIC) * 100, 2)
            END as efficiency_ratio
        FROM pg_stat_user_indexes
        WHERE schemaname = 'public'
    )
    SELECT 
        s.tablename::TEXT,
        s.indexrelname::TEXT,
        s.size::TEXT,
        s.idx_scan,
        s.idx_tup_read,
        s.idx_tup_fetch,
        s.efficiency_ratio,
        CASE 
            WHEN s.idx_scan = 0 THEN 'UNUSED - Consider dropping'
            WHEN s.efficiency_ratio < 10 THEN 'LOW EFFICIENCY - Review query patterns'
            WHEN s.idx_scan > 10000 AND s.efficiency_ratio > 80 THEN 'HIGH VALUE - Keep optimized'
            ELSE 'MODERATE USE - Monitor performance'
        END::TEXT
    FROM index_stats s
    ORDER BY s.idx_scan DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to identify missing indexes based on query patterns
CREATE OR REPLACE FUNCTION suggest_missing_conversation_indexes()
RETURNS TABLE(
    suggestion TEXT,
    reason TEXT,
    estimated_benefit TEXT
) AS $$
BEGIN
    RETURN QUERY
    VALUES 
        ('CREATE INDEX ON conversations (last_activity_at DESC) WHERE is_active = TRUE;',
         'Recent activity queries are common for dashboard',
         'HIGH - Dashboard performance'),
        
        ('CREATE INDEX ON messages (conversation_id, sender_type, created_at DESC);',
         'Conversation history with sender filtering',
         'MEDIUM - Thread display optimization'),
         
        ('CREATE INDEX ON conversations (category, subcategory, status);',
         'Category-based filtering for support analytics',
         'MEDIUM - Analytics queries'),
         
        ('CREATE INDEX ON conversations USING GIN (tags) WHERE array_length(tags, 1) > 0;',
         'Tag-based conversation filtering',
         'LOW - Depends on tag usage patterns');
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- QUERY OPTIMIZATION HELPERS
-- ============================================================================

-- Function to get index usage statistics
CREATE OR REPLACE FUNCTION get_conversation_index_stats()
RETURNS TABLE(
    index_name TEXT,
    table_name TEXT,
    scans BIGINT,
    size TEXT,
    last_used TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        i.indexrelname::TEXT,
        i.tablename::TEXT,
        i.idx_scan,
        pg_size_pretty(pg_relation_size(i.indexrelid))::TEXT,
        s.last_idx_scan
    FROM pg_stat_user_indexes i
    LEFT JOIN pg_stat_user_tables s ON i.relid = s.relid
    WHERE i.tablename IN ('conversations', 'messages', 'venues', 'zones')
    ORDER BY i.idx_scan DESC;
END;
$$ LANGUAGE plpgsql;

-- Update table statistics for optimal query planning
ANALYZE conversations;
ANALYZE messages;
ANALYZE venues;
ANALYZE zones;
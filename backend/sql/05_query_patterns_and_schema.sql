-- BMA Social - Optimized Query Patterns and Schema Integration
-- High-performance queries for conversation history, venue linking, and analytics
-- Designed for sub-500ms response times on conversation retrieval

-- ============================================================================
-- OPTIMIZED SCHEMA RELATIONSHIPS
-- ============================================================================

-- Ensure proper foreign key constraints for data integrity and query optimization
ALTER TABLE conversations 
ADD CONSTRAINT fk_conversations_venue 
FOREIGN KEY (venue_id) REFERENCES venues(id) ON DELETE CASCADE;

-- Add venue-conversation materialized relationship for faster queries
CREATE TABLE IF NOT EXISTS venue_conversation_summary (
    venue_id UUID PRIMARY KEY,
    total_conversations INTEGER DEFAULT 0,
    active_conversations INTEGER DEFAULT 0,
    avg_response_time_seconds NUMERIC(10,2),
    last_conversation_at TIMESTAMPTZ,
    satisfaction_score NUMERIC(3,2),
    bot_handled_percentage NUMERIC(5,2),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_venue_summary_active 
    ON venue_conversation_summary (active_conversations DESC, last_conversation_at DESC);

-- ============================================================================
-- HIGH-PERFORMANCE CONVERSATION QUERIES
-- ============================================================================

-- Query Pattern 1: Get recent conversations for venue dashboard (< 100ms target)
CREATE OR REPLACE FUNCTION get_venue_conversations_fast(
    p_venue_id UUID,
    p_limit INTEGER DEFAULT 20,
    p_status TEXT[] DEFAULT ARRAY['open', 'in_progress', 'waiting_customer']
)
RETURNS TABLE(
    conversation_id UUID,
    customer_name VARCHAR,
    customer_phone VARCHAR,
    channel TEXT,
    status TEXT,
    priority TEXT,
    message_count INTEGER,
    last_message_preview TEXT,
    last_activity_at TIMESTAMPTZ,
    is_overdue BOOLEAN,
    bot_confidence NUMERIC,
    created_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    WITH recent_messages AS (
        SELECT DISTINCT ON (m.conversation_id)
            m.conversation_id,
            LEFT(m.content, 100) as preview
        FROM messages m
        WHERE m.conversation_id IN (
            SELECT id FROM conversations 
            WHERE venue_id = p_venue_id 
            AND (p_status IS NULL OR status::TEXT = ANY(p_status))
        )
        ORDER BY m.conversation_id, m.created_at DESC
    )
    SELECT 
        c.id,
        c.customer_name,
        c.customer_phone,
        c.channel::TEXT,
        c.status::TEXT,
        c.priority::TEXT,
        c.message_count,
        rm.preview,
        c.last_activity_at,
        (c.sla_deadline IS NOT NULL AND c.sla_deadline < CURRENT_TIMESTAMP) as is_overdue,
        c.bot_confidence_score,
        c.created_at
    FROM conversations c
    LEFT JOIN recent_messages rm ON c.id = rm.conversation_id
    WHERE c.venue_id = p_venue_id
    AND (p_status IS NULL OR c.status::TEXT = ANY(p_status))
    ORDER BY 
        c.priority DESC,
        c.last_activity_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Query Pattern 2: Conversation history with efficient pagination
CREATE OR REPLACE FUNCTION get_conversation_history(
    p_conversation_id UUID,
    p_page_size INTEGER DEFAULT 25,
    p_cursor TIMESTAMPTZ DEFAULT NULL,
    p_direction TEXT DEFAULT 'DESC' -- 'DESC' for newest first, 'ASC' for oldest first
)
RETURNS TABLE(
    message_id UUID,
    sender_type TEXT,
    sender_name VARCHAR,
    content TEXT,
    content_type VARCHAR,
    attachment_url VARCHAR,
    reply_to_id UUID,
    intent VARCHAR,
    sentiment VARCHAR,
    actions_taken JSONB,
    created_at TIMESTAMPTZ,
    is_read BOOLEAN,
    has_more BOOLEAN
) AS $$
DECLARE
    v_cursor TIMESTAMPTZ;
    v_has_more BOOLEAN := FALSE;
BEGIN
    -- Set cursor to current time if not provided
    v_cursor := COALESCE(p_cursor, 
        CASE WHEN p_direction = 'DESC' THEN CURRENT_TIMESTAMP ELSE '1900-01-01'::TIMESTAMPTZ END
    );
    
    -- Check if there are more messages beyond this page
    IF p_direction = 'DESC' THEN
        SELECT EXISTS(
            SELECT 1 FROM messages 
            WHERE conversation_id = p_conversation_id 
            AND created_at < (
                SELECT created_at FROM messages 
                WHERE conversation_id = p_conversation_id 
                AND created_at < v_cursor
                ORDER BY created_at DESC 
                LIMIT 1 OFFSET p_page_size - 1
            )
        ) INTO v_has_more;
    ELSE
        SELECT EXISTS(
            SELECT 1 FROM messages 
            WHERE conversation_id = p_conversation_id 
            AND created_at > (
                SELECT created_at FROM messages 
                WHERE conversation_id = p_conversation_id 
                AND created_at > v_cursor
                ORDER BY created_at ASC 
                LIMIT 1 OFFSET p_page_size - 1
            )
        ) INTO v_has_more;
    END IF;
    
    -- Return paginated results
    RETURN QUERY
    SELECT 
        m.id,
        m.sender_type::TEXT,
        m.sender_name,
        m.content,
        m.content_type,
        m.attachment_url,
        m.reply_to_id,
        m.intent,
        m.sentiment,
        m.actions,
        m.created_at,
        m.is_read,
        v_has_more
    FROM messages m
    WHERE m.conversation_id = p_conversation_id
    AND (
        CASE 
            WHEN p_direction = 'DESC' THEN m.created_at < v_cursor
            ELSE m.created_at > v_cursor
        END
    )
    ORDER BY 
        CASE WHEN p_direction = 'DESC' THEN m.created_at END DESC,
        CASE WHEN p_direction = 'ASC' THEN m.created_at END ASC
    LIMIT p_page_size;
END;
$$ LANGUAGE plpgsql;

-- Query Pattern 3: Multi-venue conversation search with filters
CREATE OR REPLACE FUNCTION search_conversations(
    p_venue_ids UUID[] DEFAULT NULL,
    p_channels TEXT[] DEFAULT NULL,
    p_status TEXT[] DEFAULT NULL,
    p_priority TEXT[] DEFAULT NULL,
    p_customer_search TEXT DEFAULT NULL,
    p_content_search TEXT DEFAULT NULL,
    p_date_from TIMESTAMPTZ DEFAULT NULL,
    p_date_to TIMESTAMPTZ DEFAULT NULL,
    p_assigned_to UUID DEFAULT NULL,
    p_bot_escalated BOOLEAN DEFAULT NULL,
    p_limit INTEGER DEFAULT 50,
    p_offset INTEGER DEFAULT 0
)
RETURNS TABLE(
    conversation_id UUID,
    venue_id UUID,
    venue_name VARCHAR,
    customer_name VARCHAR,
    customer_phone VARCHAR,
    channel TEXT,
    status TEXT,
    priority TEXT,
    assigned_to UUID,
    message_count INTEGER,
    last_activity_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ,
    satisfaction_score INTEGER,
    bot_handled BOOLEAN,
    is_overdue BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.id,
        c.venue_id,
        v.name,
        c.customer_name,
        c.customer_phone,
        c.channel::TEXT,
        c.status::TEXT,
        c.priority::TEXT,
        c.assigned_to,
        c.message_count,
        c.last_activity_at,
        c.created_at,
        c.satisfaction_score,
        c.bot_handled,
        (c.sla_deadline IS NOT NULL AND c.sla_deadline < CURRENT_TIMESTAMP) as is_overdue
    FROM conversations c
    JOIN venues v ON c.venue_id = v.id
    WHERE 
        (p_venue_ids IS NULL OR c.venue_id = ANY(p_venue_ids))
        AND (p_channels IS NULL OR c.channel::TEXT = ANY(p_channels))
        AND (p_status IS NULL OR c.status::TEXT = ANY(p_status))
        AND (p_priority IS NULL OR c.priority::TEXT = ANY(p_priority))
        AND (p_assigned_to IS NULL OR c.assigned_to = p_assigned_to)
        AND (p_bot_escalated IS NULL OR c.bot_escalated = p_bot_escalated)
        AND (p_date_from IS NULL OR c.created_at >= p_date_from)
        AND (p_date_to IS NULL OR c.created_at <= p_date_to)
        AND (
            p_customer_search IS NULL OR
            (c.customer_name ILIKE '%' || p_customer_search || '%' OR
             c.customer_phone ILIKE '%' || p_customer_search || '%')
        )
        AND (
            p_content_search IS NULL OR
            EXISTS (
                SELECT 1 FROM messages m 
                WHERE m.conversation_id = c.id 
                AND to_tsvector('english', m.content) @@ plainto_tsquery('english', p_content_search)
            )
        )
    ORDER BY c.priority DESC, c.last_activity_at DESC
    LIMIT p_limit
    OFFSET p_offset;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- VENUE-CONVERSATION ANALYTICS QUERIES
-- ============================================================================

-- Query Pattern 4: Venue performance dashboard
CREATE OR REPLACE FUNCTION get_venue_performance_metrics(
    p_venue_id UUID,
    p_date_from TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP - INTERVAL '30 days',
    p_date_to TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
)
RETURNS TABLE(
    metric_name TEXT,
    current_value NUMERIC,
    previous_value NUMERIC,
    percentage_change NUMERIC,
    trend TEXT
) AS $$
BEGIN
    RETURN QUERY
    WITH current_period AS (
        SELECT 
            COUNT(*) as total_conversations,
            COUNT(*) FILTER (WHERE status = 'resolved') as resolved_conversations,
            AVG(first_response_time_seconds) as avg_first_response,
            AVG(resolution_time_seconds) as avg_resolution_time,
            COUNT(*) FILTER (WHERE bot_handled = true) as bot_handled_count,
            AVG(satisfaction_score) as avg_satisfaction,
            COUNT(*) FILTER (WHERE sla_deadline < resolved_at) as sla_breaches
        FROM conversations
        WHERE venue_id = p_venue_id
        AND created_at >= p_date_from
        AND created_at <= p_date_to
    ),
    previous_period AS (
        SELECT 
            COUNT(*) as total_conversations,
            COUNT(*) FILTER (WHERE status = 'resolved') as resolved_conversations,
            AVG(first_response_time_seconds) as avg_first_response,
            AVG(resolution_time_seconds) as avg_resolution_time,
            COUNT(*) FILTER (WHERE bot_handled = true) as bot_handled_count,
            AVG(satisfaction_score) as avg_satisfaction,
            COUNT(*) FILTER (WHERE sla_deadline < resolved_at) as sla_breaches
        FROM conversations
        WHERE venue_id = p_venue_id
        AND created_at >= p_date_from - (p_date_to - p_date_from)
        AND created_at < p_date_from
    )
    SELECT 
        'Total Conversations'::TEXT,
        c.total_conversations::NUMERIC,
        p.total_conversations::NUMERIC,
        CASE 
            WHEN p.total_conversations > 0 THEN
                ROUND(((c.total_conversations::NUMERIC - p.total_conversations::NUMERIC) / p.total_conversations::NUMERIC) * 100, 1)
            ELSE 0
        END,
        CASE 
            WHEN c.total_conversations > p.total_conversations THEN '↑'
            WHEN c.total_conversations < p.total_conversations THEN '↓'
            ELSE '→'
        END::TEXT
    FROM current_period c, previous_period p
    
    UNION ALL
    
    SELECT 
        'Resolution Rate (%)'::TEXT,
        CASE 
            WHEN c.total_conversations > 0 THEN 
                ROUND((c.resolved_conversations::NUMERIC / c.total_conversations::NUMERIC) * 100, 1)
            ELSE 0
        END,
        CASE 
            WHEN p.total_conversations > 0 THEN 
                ROUND((p.resolved_conversations::NUMERIC / p.total_conversations::NUMERIC) * 100, 1)
            ELSE 0
        END,
        CASE 
            WHEN p.total_conversations > 0 AND c.total_conversations > 0 THEN
                ROUND((
                    (c.resolved_conversations::NUMERIC / c.total_conversations::NUMERIC) - 
                    (p.resolved_conversations::NUMERIC / p.total_conversations::NUMERIC)
                ) * 100, 1)
            ELSE 0
        END,
        CASE 
            WHEN c.total_conversations > 0 AND p.total_conversations > 0 THEN
                CASE 
                    WHEN (c.resolved_conversations::NUMERIC / c.total_conversations::NUMERIC) > 
                         (p.resolved_conversations::NUMERIC / p.total_conversations::NUMERIC) THEN '↑'
                    WHEN (c.resolved_conversations::NUMERIC / c.total_conversations::NUMERIC) < 
                         (p.resolved_conversations::NUMERIC / p.total_conversations::NUMERIC) THEN '↓'
                    ELSE '→'
                END
            ELSE '→'
        END::TEXT
    FROM current_period c, previous_period p
    
    UNION ALL
    
    SELECT 
        'Avg First Response (min)'::TEXT,
        ROUND(COALESCE(c.avg_first_response, 0) / 60, 1),
        ROUND(COALESCE(p.avg_first_response, 0) / 60, 1),
        CASE 
            WHEN p.avg_first_response > 0 THEN
                ROUND(((COALESCE(c.avg_first_response, 0) - COALESCE(p.avg_first_response, 0)) / p.avg_first_response) * 100, 1)
            ELSE 0
        END,
        CASE 
            WHEN COALESCE(c.avg_first_response, 0) < COALESCE(p.avg_first_response, 0) THEN '↑'  -- Lower is better
            WHEN COALESCE(c.avg_first_response, 0) > COALESCE(p.avg_first_response, 0) THEN '↓'
            ELSE '→'
        END::TEXT
    FROM current_period c, previous_period p;
END;
$$ LANGUAGE plpgsql;

-- Query Pattern 5: Real-time conversation monitoring
CREATE OR REPLACE FUNCTION get_real_time_conversation_stats()
RETURNS TABLE(
    stat_name TEXT,
    stat_value TEXT,
    alert_level TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        'Active Conversations'::TEXT,
        COUNT(*)::TEXT,
        CASE 
            WHEN COUNT(*) > 100 THEN 'HIGH'
            WHEN COUNT(*) > 50 THEN 'MEDIUM'
            ELSE 'LOW'
        END::TEXT
    FROM conversations
    WHERE status IN ('open', 'in_progress', 'waiting_customer')
    
    UNION ALL
    
    SELECT 
        'Overdue SLA'::TEXT,
        COUNT(*)::TEXT,
        CASE 
            WHEN COUNT(*) > 10 THEN 'CRITICAL'
            WHEN COUNT(*) > 5 THEN 'HIGH'
            WHEN COUNT(*) > 0 THEN 'MEDIUM'
            ELSE 'LOW'
        END::TEXT
    FROM conversations
    WHERE status NOT IN ('resolved', 'closed')
    AND sla_deadline < CURRENT_TIMESTAMP
    
    UNION ALL
    
    SELECT 
        'Bot Escalations (1hr)'::TEXT,
        COUNT(*)::TEXT,
        CASE 
            WHEN COUNT(*) > 5 THEN 'HIGH'
            WHEN COUNT(*) > 2 THEN 'MEDIUM'
            ELSE 'LOW'
        END::TEXT
    FROM conversations
    WHERE bot_escalated = true
    AND created_at >= CURRENT_TIMESTAMP - INTERVAL '1 hour'
    
    UNION ALL
    
    SELECT 
        'Unassigned Urgent'::TEXT,
        COUNT(*)::TEXT,
        CASE 
            WHEN COUNT(*) > 0 THEN 'CRITICAL'
            ELSE 'LOW'
        END::TEXT
    FROM conversations
    WHERE priority = 'urgent'
    AND assigned_to IS NULL
    AND status NOT IN ('resolved', 'closed');
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- OPTIMIZED AGGREGATION QUERIES
-- ============================================================================

-- Query Pattern 6: Conversation volume analytics with time grouping
CREATE OR REPLACE FUNCTION get_conversation_volume_analytics(
    p_venue_ids UUID[] DEFAULT NULL,
    p_date_from TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP - INTERVAL '7 days',
    p_date_to TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    p_grouping TEXT DEFAULT 'hour' -- 'hour', 'day', 'week'
)
RETURNS TABLE(
    time_bucket TIMESTAMPTZ,
    total_conversations INTEGER,
    whatsapp_conversations INTEGER,
    line_conversations INTEGER,
    bot_handled INTEGER,
    human_handled INTEGER,
    avg_resolution_minutes NUMERIC
) AS $$
DECLARE
    v_trunc_format TEXT;
BEGIN
    -- Set time truncation based on grouping
    v_trunc_format := CASE 
        WHEN p_grouping = 'hour' THEN 'hour'
        WHEN p_grouping = 'day' THEN 'day'
        WHEN p_grouping = 'week' THEN 'week'
        ELSE 'hour'
    END;
    
    RETURN QUERY
    EXECUTE format('
        SELECT 
            DATE_TRUNC(%L, c.created_at) as time_bucket,
            COUNT(*)::INTEGER as total_conversations,
            COUNT(*) FILTER (WHERE c.channel = ''whatsapp'')::INTEGER as whatsapp_conversations,
            COUNT(*) FILTER (WHERE c.channel = ''line'')::INTEGER as line_conversations,
            COUNT(*) FILTER (WHERE c.bot_handled = true)::INTEGER as bot_handled,
            COUNT(*) FILTER (WHERE c.bot_handled = false OR c.bot_handled IS NULL)::INTEGER as human_handled,
            ROUND(AVG(c.resolution_time_seconds) / 60.0, 1) as avg_resolution_minutes
        FROM conversations c
        WHERE c.created_at >= $1
        AND c.created_at <= $2
        AND ($3 IS NULL OR c.venue_id = ANY($3))
        GROUP BY DATE_TRUNC(%L, c.created_at)
        ORDER BY time_bucket DESC',
        v_trunc_format, v_trunc_format
    )
    USING p_date_from, p_date_to, p_venue_ids;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- MATERIALIZED VIEW REFRESH PROCEDURES
-- ============================================================================

-- Function to refresh venue conversation summaries
CREATE OR REPLACE FUNCTION refresh_venue_conversation_summaries()
RETURNS TEXT AS $$
DECLARE
    refresh_count INTEGER;
BEGIN
    -- Refresh venue conversation summary table
    INSERT INTO venue_conversation_summary (
        venue_id,
        total_conversations,
        active_conversations,
        avg_response_time_seconds,
        last_conversation_at,
        satisfaction_score,
        bot_handled_percentage,
        updated_at
    )
    SELECT 
        c.venue_id,
        COUNT(*) as total_conversations,
        COUNT(*) FILTER (WHERE c.status NOT IN ('resolved', 'closed')) as active_conversations,
        AVG(c.first_response_time_seconds) as avg_response_time_seconds,
        MAX(c.last_activity_at) as last_conversation_at,
        AVG(c.satisfaction_score) as satisfaction_score,
        ROUND(
            (COUNT(*) FILTER (WHERE c.bot_handled = true))::NUMERIC / 
            NULLIF(COUNT(*), 0) * 100, 2
        ) as bot_handled_percentage,
        CURRENT_TIMESTAMP
    FROM conversations c
    WHERE c.created_at >= CURRENT_TIMESTAMP - INTERVAL '30 days'
    GROUP BY c.venue_id
    ON CONFLICT (venue_id) DO UPDATE SET
        total_conversations = EXCLUDED.total_conversations,
        active_conversations = EXCLUDED.active_conversations,
        avg_response_time_seconds = EXCLUDED.avg_response_time_seconds,
        last_conversation_at = EXCLUDED.last_conversation_at,
        satisfaction_score = EXCLUDED.satisfaction_score,
        bot_handled_percentage = EXCLUDED.bot_handled_percentage,
        updated_at = CURRENT_TIMESTAMP;
    
    GET DIAGNOSTICS refresh_count = ROW_COUNT;
    
    RETURN format('Refreshed %s venue conversation summaries', refresh_count);
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- QUERY PERFORMANCE MONITORING
-- ============================================================================

-- Function to analyze query performance for conversation operations
CREATE OR REPLACE FUNCTION analyze_conversation_query_performance()
RETURNS TABLE(
    query_pattern TEXT,
    avg_duration_ms NUMERIC,
    call_count BIGINT,
    total_duration_ms NUMERIC,
    performance_rating TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        CASE 
            WHEN query LIKE '%get_venue_conversations_fast%' THEN 'Venue Dashboard Queries'
            WHEN query LIKE '%get_conversation_history%' THEN 'Message History Queries'
            WHEN query LIKE '%search_conversations%' THEN 'Search Queries'
            WHEN query LIKE '%FROM conversations%' THEN 'General Conversation Queries'
            WHEN query LIKE '%FROM messages%' THEN 'Message Queries'
            ELSE 'Other'
        END as query_pattern,
        ROUND(mean_exec_time, 2) as avg_duration_ms,
        calls as call_count,
        ROUND(total_exec_time, 2) as total_duration_ms,
        CASE 
            WHEN mean_exec_time < 50 THEN 'EXCELLENT'
            WHEN mean_exec_time < 100 THEN 'GOOD'
            WHEN mean_exec_time < 500 THEN 'ACCEPTABLE'
            WHEN mean_exec_time < 1000 THEN 'SLOW'
            ELSE 'CRITICAL'
        END as performance_rating
    FROM pg_stat_statements
    WHERE query LIKE '%conversations%' OR query LIKE '%messages%'
    AND calls > 10  -- Only show frequently used queries
    ORDER BY mean_exec_time DESC;
END;
$$ LANGUAGE plpgsql;
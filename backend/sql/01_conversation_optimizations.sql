-- BMA Social - Conversation Storage Optimizations
-- Optimized for WhatsApp messaging with thousands of messages daily
-- Target: Sub-100ms query performance, efficient conversation threading

-- ============================================================================
-- CONVERSATION PARTITIONING STRATEGY
-- ============================================================================

-- Enable pg_partman extension for automated partition management
CREATE EXTENSION IF NOT EXISTS pg_partman;

-- Create partitioned conversations table (monthly partitions)
-- This will handle 1M+ conversations efficiently
DROP TABLE IF EXISTS conversations CASCADE;

CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    venue_id UUID NOT NULL,
    
    -- Channel and External Integration
    channel conversation_channel NOT NULL,
    external_id VARCHAR(255), -- WhatsApp conversation ID
    customer_phone VARCHAR(50),
    customer_email VARCHAR(255),
    customer_name VARCHAR(255),
    customer_id VARCHAR(100),
    
    -- Status and Priority Management
    status conversation_status DEFAULT 'open' NOT NULL,
    priority conversation_priority DEFAULT 'normal' NOT NULL,
    assigned_to UUID, -- Team member ID
    assigned_at TIMESTAMPTZ,
    
    -- Conversation Context
    subject VARCHAR(500),
    category VARCHAR(100),
    subcategory VARCHAR(100),
    language VARCHAR(10) DEFAULT 'en',
    
    -- SLA Tracking (optimized for real-time queries)
    sla_deadline TIMESTAMPTZ,
    first_response_at TIMESTAMPTZ,
    first_response_time_seconds INTEGER,
    resolution_time_seconds INTEGER,
    resolved_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    
    -- Bot Processing Metrics
    bot_handled BOOLEAN DEFAULT FALSE,
    bot_confidence_score NUMERIC(3,2), -- 0.00-1.00
    bot_escalated BOOLEAN DEFAULT FALSE,
    bot_escalation_reason VARCHAR(500),
    
    -- Message Counters (denormalized for performance)
    message_count INTEGER DEFAULT 0,
    customer_message_count INTEGER DEFAULT 0,
    team_message_count INTEGER DEFAULT 0,
    bot_message_count INTEGER DEFAULT 0,
    
    -- Satisfaction Tracking
    satisfaction_requested BOOLEAN DEFAULT FALSE,
    satisfaction_requested_at TIMESTAMPTZ,
    satisfaction_score INTEGER, -- 1-5 scale
    satisfaction_comment TEXT,
    
    -- Session Management
    session_id VARCHAR(100),
    last_activity_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Flexible Metadata
    metadata JSONB DEFAULT '{}',
    tags TEXT[] DEFAULT '{}', -- Use array for better performance than JSONB
    
    -- Audit Fields
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
) PARTITION BY RANGE (created_at);

-- Set table storage parameters for optimal performance
ALTER TABLE conversations SET (
    fillfactor = 85,  -- Leave 15% space for updates
    autovacuum_vacuum_scale_factor = 0.05,
    autovacuum_analyze_scale_factor = 0.02,
    autovacuum_vacuum_cost_delay = 10
);

-- ============================================================================
-- MESSAGE STORAGE OPTIMIZATION
-- ============================================================================

-- Create optimized messages table with partitioning
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL,
    
    -- Message Sender Details
    sender_type message_sender_type NOT NULL,
    sender_id VARCHAR(255),
    sender_name VARCHAR(255),
    
    -- Message Content (optimized for WhatsApp)
    content TEXT NOT NULL,
    content_type VARCHAR(50) DEFAULT 'text',
    
    -- Media Attachments
    attachment_url VARCHAR(500),
    attachment_name VARCHAR(255),
    attachment_size INTEGER,
    attachment_type VARCHAR(100),
    
    -- WhatsApp Integration
    external_id VARCHAR(255), -- WhatsApp message ID
    reply_to_id UUID, -- For message threading
    
    -- AI Processing Results
    intent VARCHAR(100),
    entities JSONB,
    sentiment VARCHAR(20), -- positive, negative, neutral
    confidence_score NUMERIC(3,2),
    
    -- Action Results
    actions JSONB,
    action_results JSONB,
    
    -- Delivery Status
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    failed_delivery BOOLEAN DEFAULT FALSE,
    failure_reason VARCHAR(500),
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    -- Audit
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
) PARTITION BY RANGE (created_at);

-- Optimize messages table for high-volume inserts
ALTER TABLE messages SET (
    fillfactor = 95,  -- Messages rarely updated after creation
    autovacuum_vacuum_scale_factor = 0.02,
    autovacuum_analyze_scale_factor = 0.01
);

-- ============================================================================
-- INDEXING STRATEGY FOR FAST QUERIES
-- ============================================================================

-- Core conversation indexes
CREATE INDEX CONCURRENTLY idx_conversations_venue_created 
    ON conversations (venue_id, created_at DESC);

CREATE INDEX CONCURRENTLY idx_conversations_status_priority 
    ON conversations (status, priority, created_at DESC)
    WHERE status IN ('open', 'in_progress', 'waiting_customer');

CREATE INDEX CONCURRENTLY idx_conversations_sla_overdue 
    ON conversations (sla_deadline, status)
    WHERE sla_deadline IS NOT NULL AND status NOT IN ('resolved', 'closed');

CREATE INDEX CONCURRENTLY idx_conversations_assigned 
    ON conversations (assigned_to, status, created_at DESC)
    WHERE assigned_to IS NOT NULL;

CREATE INDEX CONCURRENTLY idx_conversations_channel_external 
    ON conversations (channel, external_id)
    WHERE external_id IS NOT NULL;

CREATE INDEX CONCURRENTLY idx_conversations_active_session 
    ON conversations (session_id, is_active, last_activity_at DESC)
    WHERE is_active = TRUE;

-- Bot escalation tracking
CREATE INDEX CONCURRENTLY idx_conversations_bot_escalated 
    ON conversations (bot_escalated, bot_confidence_score, created_at DESC)
    WHERE bot_escalated = TRUE OR bot_confidence_score < 0.7;

-- Text search on conversation content
CREATE INDEX CONCURRENTLY idx_conversations_search_gin 
    ON conversations USING GIN (
        to_tsvector('english', 
            COALESCE(subject, '') || ' ' || 
            COALESCE(category, '') || ' ' ||
            COALESCE(customer_name, '')
        )
    );

-- Tags array index for filtering
CREATE INDEX CONCURRENTLY idx_conversations_tags_gin 
    ON conversations USING GIN (tags);

-- Message indexes optimized for conversation retrieval
CREATE INDEX CONCURRENTLY idx_messages_conversation_created 
    ON messages (conversation_id, created_at DESC);

CREATE INDEX CONCURRENTLY idx_messages_sender_type_created 
    ON messages (sender_type, created_at DESC);

CREATE INDEX CONCURRENTLY idx_messages_external_id 
    ON messages (external_id)
    WHERE external_id IS NOT NULL;

CREATE INDEX CONCURRENTLY idx_messages_reply_threading 
    ON messages (reply_to_id, created_at)
    WHERE reply_to_id IS NOT NULL;

-- Content search index
CREATE INDEX CONCURRENTLY idx_messages_content_search 
    ON messages USING GIN (to_tsvector('english', content));

-- Unread messages tracking
CREATE INDEX CONCURRENTLY idx_messages_unread 
    ON messages (conversation_id, is_read, created_at DESC)
    WHERE is_read = FALSE;

-- ============================================================================
-- AUTOMATED PARTITION CREATION
-- ============================================================================

-- Function to create monthly partitions
CREATE OR REPLACE FUNCTION create_conversation_partitions()
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
        
        -- Conversations partition
        partition_name := 'conversations_' || TO_CHAR(start_date, 'YYYY_MM');
        IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = partition_name) THEN
            EXECUTE format(
                'CREATE TABLE %I PARTITION OF conversations 
                 FOR VALUES FROM (%L) TO (%L)',
                partition_name, start_date, end_date
            );
            
            -- Add partition-specific optimizations
            EXECUTE format(
                'ALTER TABLE %I SET (
                    fillfactor = 85,
                    autovacuum_vacuum_scale_factor = 0.05
                )', 
                partition_name
            );
            
            RAISE NOTICE 'Created conversations partition: %', partition_name;
        END IF;
        
        -- Messages partition
        partition_name := 'messages_' || TO_CHAR(start_date, 'YYYY_MM');
        IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = partition_name) THEN
            EXECUTE format(
                'CREATE TABLE %I PARTITION OF messages 
                 FOR VALUES FROM (%L) TO (%L)',
                partition_name, start_date, end_date
            );
            
            -- Messages are append-mostly
            EXECUTE format(
                'ALTER TABLE %I SET (
                    fillfactor = 95,
                    autovacuum_vacuum_scale_factor = 0.02
                )', 
                partition_name
            );
            
            RAISE NOTICE 'Created messages partition: %', partition_name;
        END IF;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Create initial partitions
SELECT create_conversation_partitions();

-- ============================================================================
-- CONVERSATION THREADING FUNCTIONS
-- ============================================================================

-- Function to get conversation thread with pagination
CREATE OR REPLACE FUNCTION get_conversation_thread(
    p_conversation_id UUID,
    p_limit INTEGER DEFAULT 50,
    p_offset INTEGER DEFAULT 0
)
RETURNS TABLE(
    message_id UUID,
    sender_type message_sender_type,
    sender_name VARCHAR,
    content TEXT,
    content_type VARCHAR,
    attachment_url VARCHAR,
    reply_to_id UUID,
    created_at TIMESTAMPTZ,
    is_read BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        m.id,
        m.sender_type,
        m.sender_name,
        m.content,
        m.content_type,
        m.attachment_url,
        m.reply_to_id,
        m.created_at,
        m.is_read
    FROM messages m
    WHERE m.conversation_id = p_conversation_id
    ORDER BY m.created_at DESC
    LIMIT p_limit
    OFFSET p_offset;
END;
$$ LANGUAGE plpgsql;

-- Function to update conversation metrics
CREATE OR REPLACE FUNCTION update_conversation_metrics(p_conversation_id UUID)
RETURNS void AS $$
DECLARE
    v_message_count INTEGER;
    v_customer_count INTEGER;
    v_team_count INTEGER;
    v_bot_count INTEGER;
    v_last_activity TIMESTAMPTZ;
BEGIN
    -- Get message counts
    SELECT 
        COUNT(*),
        COUNT(*) FILTER (WHERE sender_type = 'customer'),
        COUNT(*) FILTER (WHERE sender_type = 'team'),
        COUNT(*) FILTER (WHERE sender_type = 'bot'),
        MAX(created_at)
    INTO v_message_count, v_customer_count, v_team_count, v_bot_count, v_last_activity
    FROM messages
    WHERE conversation_id = p_conversation_id;
    
    -- Update conversation
    UPDATE conversations
    SET 
        message_count = COALESCE(v_message_count, 0),
        customer_message_count = COALESCE(v_customer_count, 0),
        team_message_count = COALESCE(v_team_count, 0),
        bot_message_count = COALESCE(v_bot_count, 0),
        last_activity_at = COALESCE(v_last_activity, last_activity_at),
        updated_at = CURRENT_TIMESTAMP
    WHERE id = p_conversation_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- PERFORMANCE MONITORING VIEWS
-- ============================================================================

-- Active conversations dashboard view
CREATE OR REPLACE VIEW v_active_conversations AS
SELECT 
    c.id,
    c.venue_id,
    v.name as venue_name,
    c.channel,
    c.status,
    c.priority,
    c.customer_name,
    c.customer_phone,
    c.message_count,
    c.last_activity_at,
    c.created_at,
    CASE 
        WHEN c.sla_deadline IS NOT NULL AND c.sla_deadline < CURRENT_TIMESTAMP 
        THEN TRUE 
        ELSE FALSE 
    END as is_overdue,
    EXTRACT(EPOCH FROM (c.sla_deadline - CURRENT_TIMESTAMP))/3600 as hours_to_sla
FROM conversations c
JOIN venues v ON c.venue_id = v.id
WHERE c.status IN ('open', 'in_progress', 'waiting_customer', 'waiting_team')
ORDER BY c.priority DESC, c.created_at ASC;

-- Conversation performance metrics
CREATE OR REPLACE VIEW v_conversation_metrics AS
SELECT 
    DATE_TRUNC('hour', created_at) as hour,
    channel,
    COUNT(*) as conversation_count,
    COUNT(*) FILTER (WHERE status = 'resolved') as resolved_count,
    AVG(message_count) as avg_messages,
    AVG(first_response_time_seconds)/60 as avg_first_response_minutes,
    AVG(resolution_time_seconds)/3600 as avg_resolution_hours,
    COUNT(*) FILTER (WHERE bot_handled = TRUE) as bot_handled_count,
    AVG(bot_confidence_score) as avg_bot_confidence
FROM conversations
WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '7 days'
GROUP BY DATE_TRUNC('hour', created_at), channel
ORDER BY hour DESC;
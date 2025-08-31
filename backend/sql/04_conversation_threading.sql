-- BMA Social - Advanced Conversation Threading
-- Optimized WhatsApp conversation management with proper threading
-- Handles message replies, context preservation, and session management

-- ============================================================================
-- CONVERSATION THREADING SCHEMA ENHANCEMENTS
-- ============================================================================

-- Enhanced message threading with WhatsApp integration
ALTER TABLE messages 
ADD COLUMN IF NOT EXISTS thread_position INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS is_thread_root BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS thread_root_id UUID,
ADD COLUMN IF NOT EXISTS context_window JSONB DEFAULT '{}';

-- Enhanced conversation context tracking
ALTER TABLE conversations 
ADD COLUMN IF NOT EXISTS thread_context JSONB DEFAULT '{}',
ADD COLUMN IF NOT EXISTS active_thread_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS last_thread_activity TIMESTAMPTZ;

-- Create thread-specific indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_messages_thread_root 
    ON messages (thread_root_id, thread_position)
    WHERE thread_root_id IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_messages_thread_context 
    ON messages (conversation_id, is_thread_root, created_at DESC)
    WHERE is_thread_root = TRUE;

-- ============================================================================
-- CONVERSATION SESSION MANAGEMENT
-- ============================================================================

-- Enhanced session tracking for continuous conversations
CREATE OR REPLACE FUNCTION manage_conversation_session(
    p_venue_id UUID,
    p_customer_phone VARCHAR(50),
    p_channel conversation_channel,
    p_external_id VARCHAR(255) DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    v_existing_conversation_id UUID;
    v_new_conversation_id UUID;
    v_session_timeout INTERVAL := INTERVAL '2 hours'; -- WhatsApp session timeout
BEGIN
    -- Look for existing active session within timeout window
    SELECT id INTO v_existing_conversation_id
    FROM conversations
    WHERE venue_id = p_venue_id
    AND customer_phone = p_customer_phone
    AND channel = p_channel
    AND status NOT IN ('resolved', 'closed')
    AND last_activity_at >= CURRENT_TIMESTAMP - v_session_timeout
    ORDER BY last_activity_at DESC
    LIMIT 1;
    
    IF v_existing_conversation_id IS NOT NULL THEN
        -- Update existing session
        UPDATE conversations
        SET 
            last_activity_at = CURRENT_TIMESTAMP,
            external_id = COALESCE(p_external_id, external_id),
            updated_at = CURRENT_TIMESTAMP
        WHERE id = v_existing_conversation_id;
        
        RETURN v_existing_conversation_id;
    ELSE
        -- Create new conversation session
        INSERT INTO conversations (
            venue_id,
            customer_phone,
            channel,
            external_id,
            status,
            session_id,
            last_activity_at,
            is_active,
            created_at
        )
        VALUES (
            p_venue_id,
            p_customer_phone,
            p_channel,
            p_external_id,
            'open',
            gen_random_uuid()::TEXT,
            CURRENT_TIMESTAMP,
            TRUE,
            CURRENT_TIMESTAMP
        )
        RETURNING id INTO v_new_conversation_id;
        
        RETURN v_new_conversation_id;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- MESSAGE THREADING FUNCTIONS
-- ============================================================================

-- Function to handle threaded message insertion
CREATE OR REPLACE FUNCTION insert_threaded_message(
    p_conversation_id UUID,
    p_sender_type message_sender_type,
    p_sender_id VARCHAR(255),
    p_sender_name VARCHAR(255),
    p_content TEXT,
    p_content_type VARCHAR(50) DEFAULT 'text',
    p_external_id VARCHAR(255) DEFAULT NULL,
    p_reply_to_id UUID DEFAULT NULL,
    p_entities JSONB DEFAULT NULL,
    p_metadata JSONB DEFAULT '{}'
)
RETURNS UUID AS $$
DECLARE
    v_message_id UUID;
    v_thread_root_id UUID;
    v_thread_position INTEGER := 0;
    v_is_thread_root BOOLEAN := FALSE;
    v_context_window JSONB := '{}';
BEGIN
    -- Generate message ID
    v_message_id := gen_random_uuid();
    
    -- Handle threading logic
    IF p_reply_to_id IS NOT NULL THEN
        -- This is a reply - find the thread root
        SELECT 
            COALESCE(thread_root_id, id),
            thread_position + 1
        INTO v_thread_root_id, v_thread_position
        FROM messages
        WHERE id = p_reply_to_id;
        
        -- Build context window from recent thread messages
        SELECT json_agg(
            json_build_object(
                'message_id', id,
                'content', LEFT(content, 200),
                'sender_type', sender_type,
                'created_at', created_at
            ) ORDER BY created_at DESC
        ) INTO v_context_window
        FROM messages
        WHERE (thread_root_id = v_thread_root_id OR id = v_thread_root_id)
        AND created_at >= CURRENT_TIMESTAMP - INTERVAL '1 hour'
        LIMIT 5;
        
    ELSE
        -- This could be a new thread root
        v_thread_root_id := NULL;
        v_is_thread_root := TRUE;
        v_thread_position := 0;
    END IF;
    
    -- Insert the message
    INSERT INTO messages (
        id,
        conversation_id,
        sender_type,
        sender_id,
        sender_name,
        content,
        content_type,
        external_id,
        reply_to_id,
        thread_root_id,
        thread_position,
        is_thread_root,
        context_window,
        entities,
        metadata,
        created_at
    )
    VALUES (
        v_message_id,
        p_conversation_id,
        p_sender_type,
        p_sender_id,
        p_sender_name,
        p_content,
        p_content_type,
        p_external_id,
        p_reply_to_id,
        v_thread_root_id,
        v_thread_position,
        v_is_thread_root,
        v_context_window,
        p_entities,
        p_metadata,
        CURRENT_TIMESTAMP
    );
    
    -- Update conversation counters and activity
    UPDATE conversations
    SET 
        message_count = message_count + 1,
        customer_message_count = CASE 
            WHEN p_sender_type = 'customer' THEN customer_message_count + 1 
            ELSE customer_message_count 
        END,
        team_message_count = CASE 
            WHEN p_sender_type = 'team' THEN team_message_count + 1 
            ELSE team_message_count 
        END,
        bot_message_count = CASE 
            WHEN p_sender_type = 'bot' THEN bot_message_count + 1 
            ELSE bot_message_count 
        END,
        active_thread_count = CASE 
            WHEN v_is_thread_root THEN active_thread_count + 1 
            ELSE active_thread_count 
        END,
        last_activity_at = CURRENT_TIMESTAMP,
        last_thread_activity = CASE 
            WHEN p_reply_to_id IS NOT NULL THEN CURRENT_TIMESTAMP 
            ELSE last_thread_activity 
        END,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = p_conversation_id;
    
    RETURN v_message_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- THREAD RETRIEVAL FUNCTIONS
-- ============================================================================

-- Function to get conversation with threaded messages
CREATE OR REPLACE FUNCTION get_threaded_conversation(
    p_conversation_id UUID,
    p_include_threads BOOLEAN DEFAULT TRUE,
    p_limit INTEGER DEFAULT 50,
    p_offset INTEGER DEFAULT 0
)
RETURNS TABLE(
    message_id UUID,
    sender_type TEXT,
    sender_name VARCHAR,
    content TEXT,
    content_type VARCHAR,
    attachment_url VARCHAR,
    reply_to_id UUID,
    thread_root_id UUID,
    thread_position INTEGER,
    is_thread_root BOOLEAN,
    thread_message_count INTEGER,
    created_at TIMESTAMPTZ,
    is_read BOOLEAN
) AS $$
BEGIN
    IF p_include_threads THEN
        -- Return full threaded view
        RETURN QUERY
        WITH thread_counts AS (
            SELECT 
                COALESCE(thread_root_id, id) as root_id,
                COUNT(*) as thread_count
            FROM messages
            WHERE conversation_id = p_conversation_id
            GROUP BY COALESCE(thread_root_id, id)
        )
        SELECT 
            m.id,
            m.sender_type::TEXT,
            m.sender_name,
            m.content,
            m.content_type,
            m.attachment_url,
            m.reply_to_id,
            m.thread_root_id,
            m.thread_position,
            m.is_thread_root,
            COALESCE(tc.thread_count, 1)::INTEGER as thread_msg_count,
            m.created_at,
            m.is_read
        FROM messages m
        LEFT JOIN thread_counts tc ON COALESCE(m.thread_root_id, m.id) = tc.root_id
        WHERE m.conversation_id = p_conversation_id
        ORDER BY m.created_at DESC, m.thread_position ASC
        LIMIT p_limit
        OFFSET p_offset;
    ELSE
        -- Return only root messages (no thread replies)
        RETURN QUERY
        SELECT 
            m.id,
            m.sender_type::TEXT,
            m.sender_name,
            m.content,
            m.content_type,
            m.attachment_url,
            m.reply_to_id,
            m.thread_root_id,
            m.thread_position,
            m.is_thread_root,
            0::INTEGER as thread_msg_count,
            m.created_at,
            m.is_read
        FROM messages m
        WHERE m.conversation_id = p_conversation_id
        AND (m.is_thread_root = TRUE OR m.thread_root_id IS NULL)
        ORDER BY m.created_at DESC
        LIMIT p_limit
        OFFSET p_offset;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Function to get a specific message thread
CREATE OR REPLACE FUNCTION get_message_thread(
    p_thread_root_id UUID,
    p_include_context BOOLEAN DEFAULT TRUE
)
RETURNS TABLE(
    message_id UUID,
    sender_type TEXT,
    sender_name VARCHAR,
    content TEXT,
    thread_position INTEGER,
    context_data JSONB,
    created_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        m.id,
        m.sender_type::TEXT,
        m.sender_name,
        m.content,
        m.thread_position,
        CASE 
            WHEN p_include_context THEN m.context_window 
            ELSE '{}'::JSONB 
        END as context_data,
        m.created_at
    FROM messages m
    WHERE (m.id = p_thread_root_id OR m.thread_root_id = p_thread_root_id)
    ORDER BY m.thread_position ASC, m.created_at ASC;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- CONTEXT MANAGEMENT
-- ============================================================================

-- Function to update conversation context based on message patterns
CREATE OR REPLACE FUNCTION update_conversation_context(
    p_conversation_id UUID
)
RETURNS void AS $$
DECLARE
    v_recent_intents JSONB;
    v_topic_keywords JSONB;
    v_customer_sentiment TEXT;
    v_escalation_indicators JSONB;
BEGIN
    -- Analyze recent messages for context
    WITH recent_analysis AS (
        SELECT 
            array_agg(DISTINCT intent) FILTER (WHERE intent IS NOT NULL) as intents,
            array_agg(DISTINCT sentiment) FILTER (WHERE sentiment IS NOT NULL) as sentiments,
            COUNT(*) FILTER (WHERE sender_type = 'customer' AND sentiment = 'negative') as negative_count,
            COUNT(*) FILTER (WHERE confidence_score < 0.7) as low_confidence_count,
            string_agg(content, ' ') as content_combined
        FROM messages
        WHERE conversation_id = p_conversation_id
        AND created_at >= CURRENT_TIMESTAMP - INTERVAL '1 hour'
    )
    SELECT 
        to_jsonb(intents),
        (SELECT jsonb_agg(word) 
         FROM unnest(string_to_array(lower(content_combined), ' ')) as word
         WHERE length(word) > 3
         GROUP BY word
         ORDER BY COUNT(*) DESC
         LIMIT 10),
        CASE 
            WHEN 'negative' = ANY(sentiments) THEN 'negative'
            WHEN 'positive' = ANY(sentiments) THEN 'positive'
            ELSE 'neutral'
        END,
        jsonb_build_object(
            'negative_messages', negative_count,
            'low_confidence_messages', low_confidence_count,
            'requires_escalation', (negative_count > 2 OR low_confidence_count > 3)
        )
    INTO v_recent_intents, v_topic_keywords, v_customer_sentiment, v_escalation_indicators
    FROM recent_analysis;
    
    -- Update conversation context
    UPDATE conversations
    SET 
        thread_context = jsonb_build_object(
            'recent_intents', COALESCE(v_recent_intents, '[]'),
            'topic_keywords', COALESCE(v_topic_keywords, '[]'),
            'customer_sentiment', COALESCE(v_customer_sentiment, 'neutral'),
            'escalation_indicators', COALESCE(v_escalation_indicators, '{}'),
            'last_context_update', CURRENT_TIMESTAMP
        ),
        -- Auto-escalate if needed
        bot_escalated = CASE 
            WHEN (v_escalation_indicators->>'requires_escalation')::BOOLEAN THEN TRUE
            ELSE bot_escalated
        END,
        bot_escalation_reason = CASE 
            WHEN (v_escalation_indicators->>'requires_escalation')::BOOLEAN 
            THEN 'Auto-escalated: negative sentiment or low confidence detected'
            ELSE bot_escalation_reason
        END,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = p_conversation_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- WHATSAPP INTEGRATION HELPERS
-- ============================================================================

-- Function to handle WhatsApp message status updates
CREATE OR REPLACE FUNCTION update_whatsapp_message_status(
    p_external_id VARCHAR(255),
    p_status VARCHAR(50), -- 'sent', 'delivered', 'read', 'failed'
    p_timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
)
RETURNS BOOLEAN AS $$
DECLARE
    v_updated BOOLEAN := FALSE;
BEGIN
    UPDATE messages
    SET 
        delivered_at = CASE WHEN p_status IN ('delivered', 'read') THEN p_timestamp ELSE delivered_at END,
        read_at = CASE WHEN p_status = 'read' THEN p_timestamp ELSE read_at END,
        is_read = CASE WHEN p_status = 'read' THEN TRUE ELSE is_read END,
        failed_delivery = CASE WHEN p_status = 'failed' THEN TRUE ELSE failed_delivery END,
        failure_reason = CASE WHEN p_status = 'failed' THEN 'WhatsApp delivery failed' ELSE failure_reason END,
        updated_at = CURRENT_TIMESTAMP
    WHERE external_id = p_external_id;
    
    GET DIAGNOSTICS v_updated = FOUND;
    RETURN v_updated;
END;
$$ LANGUAGE plpgsql;

-- Function to find conversation by WhatsApp identifiers
CREATE OR REPLACE FUNCTION find_conversation_by_whatsapp(
    p_venue_id UUID,
    p_customer_phone VARCHAR(50),
    p_external_conversation_id VARCHAR(255) DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    v_conversation_id UUID;
BEGIN
    -- First try to find by external conversation ID if provided
    IF p_external_conversation_id IS NOT NULL THEN
        SELECT id INTO v_conversation_id
        FROM conversations
        WHERE venue_id = p_venue_id
        AND external_id = p_external_conversation_id
        AND is_active = TRUE
        LIMIT 1;
        
        IF v_conversation_id IS NOT NULL THEN
            RETURN v_conversation_id;
        END IF;
    END IF;
    
    -- Fall back to finding by phone number and recent activity
    SELECT id INTO v_conversation_id
    FROM conversations
    WHERE venue_id = p_venue_id
    AND customer_phone = p_customer_phone
    AND channel = 'whatsapp'
    AND status NOT IN ('resolved', 'closed')
    AND last_activity_at >= CURRENT_TIMESTAMP - INTERVAL '24 hours'
    ORDER BY last_activity_at DESC
    LIMIT 1;
    
    RETURN v_conversation_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- CONVERSATION THREADING ANALYTICS
-- ============================================================================

-- View for thread analytics
CREATE OR REPLACE VIEW v_threading_analytics AS
SELECT 
    c.venue_id,
    v.name as venue_name,
    c.channel,
    DATE_TRUNC('day', c.created_at) as day,
    COUNT(*) as conversation_count,
    AVG(c.active_thread_count) as avg_threads_per_conversation,
    AVG(c.message_count) as avg_messages_per_conversation,
    COUNT(*) FILTER (WHERE c.active_thread_count > 0) as conversations_with_threads,
    AVG(
        EXTRACT(EPOCH FROM (c.last_thread_activity - c.created_at)) / 3600
    ) as avg_thread_duration_hours
FROM conversations c
JOIN venues v ON c.venue_id = v.id
WHERE c.created_at >= CURRENT_TIMESTAMP - INTERVAL '30 days'
GROUP BY c.venue_id, v.name, c.channel, DATE_TRUNC('day', c.created_at)
ORDER BY day DESC, conversation_count DESC;

-- Function to get conversation threading stats
CREATE OR REPLACE FUNCTION get_threading_performance()
RETURNS TABLE(
    metric TEXT,
    value TEXT,
    trend TEXT
) AS $$
BEGIN
    RETURN QUERY
    WITH current_stats AS (
        SELECT 
            COUNT(*) as total_conversations,
            COUNT(*) FILTER (WHERE active_thread_count > 0) as threaded_conversations,
            AVG(active_thread_count) as avg_threads,
            AVG(message_count) as avg_messages
        FROM conversations
        WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '7 days'
    ),
    previous_stats AS (
        SELECT 
            COUNT(*) as total_conversations,
            COUNT(*) FILTER (WHERE active_thread_count > 0) as threaded_conversations,
            AVG(active_thread_count) as avg_threads,
            AVG(message_count) as avg_messages
        FROM conversations
        WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '14 days'
        AND created_at < CURRENT_TIMESTAMP - INTERVAL '7 days'
    )
    SELECT 
        'Total Conversations (7d)'::TEXT, 
        c.total_conversations::TEXT,
        CASE 
            WHEN c.total_conversations > p.total_conversations THEN '↑'
            WHEN c.total_conversations < p.total_conversations THEN '↓'
            ELSE '→'
        END::TEXT
    FROM current_stats c, previous_stats p
    
    UNION ALL
    
    SELECT 
        'Threaded Conversations (%)'::TEXT,
        ROUND((c.threaded_conversations::NUMERIC / c.total_conversations * 100), 1)::TEXT || '%',
        CASE 
            WHEN (c.threaded_conversations::NUMERIC / c.total_conversations) > 
                 (p.threaded_conversations::NUMERIC / p.total_conversations) THEN '↑'
            WHEN (c.threaded_conversations::NUMERIC / c.total_conversations) < 
                 (p.threaded_conversations::NUMERIC / p.total_conversations) THEN '↓'
            ELSE '→'
        END::TEXT
    FROM current_stats c, previous_stats p
    WHERE c.total_conversations > 0 AND p.total_conversations > 0
    
    UNION ALL
    
    SELECT 
        'Avg Messages per Conversation'::TEXT,
        ROUND(c.avg_messages, 1)::TEXT,
        CASE 
            WHEN c.avg_messages > p.avg_messages THEN '↑'
            WHEN c.avg_messages < p.avg_messages THEN '↓'
            ELSE '→'
        END::TEXT
    FROM current_stats c, previous_stats p;
END;
$$ LANGUAGE plpgsql;
-- Campaign Management Database Schema
-- Extends the existing BMA Social database with campaign capabilities

-- Campaigns table (main campaign records)
CREATE TABLE IF NOT EXISTS campaigns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL, -- renewal, seasonal, announcement, survey, follow_up
    status VARCHAR(20) DEFAULT 'draft', -- draft, scheduled, sending, sent, completed
    goal TEXT,
    target_audience TEXT,
    key_message TEXT,
    tone VARCHAR(50), -- formal, casual, friendly

    -- Filtering criteria (stored as JSONB for flexibility)
    filters JSONB,

    -- AI-generated content
    ai_prompt TEXT,
    ai_response JSONB,

    -- Scheduling
    scheduled_at TIMESTAMP,
    sent_at TIMESTAMP,
    completed_at TIMESTAMP,

    -- Metrics
    total_recipients INTEGER DEFAULT 0,
    sent_count INTEGER DEFAULT 0,
    delivered_count INTEGER DEFAULT 0,
    opened_count INTEGER DEFAULT 0,
    clicked_count INTEGER DEFAULT 0,
    responded_count INTEGER DEFAULT 0,

    -- Metadata
    created_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Campaign Recipients table (who gets the campaign)
CREATE TABLE IF NOT EXISTS campaign_recipients (
    id SERIAL PRIMARY KEY,
    campaign_id UUID REFERENCES campaigns(id) ON DELETE CASCADE,
    venue_id INTEGER REFERENCES venues(id),
    contact_id INTEGER REFERENCES contacts(id),

    -- Personalization
    personalized_message TEXT,
    message_variables JSONB, -- Variables used in template

    -- Delivery status per channel
    whatsapp_status VARCHAR(20), -- pending, sent, delivered, read, failed
    whatsapp_sent_at TIMESTAMP,
    whatsapp_message_id VARCHAR(255),

    email_status VARCHAR(20), -- pending, sent, delivered, opened, clicked, bounced
    email_sent_at TIMESTAMP,
    email_message_id VARCHAR(255),

    line_status VARCHAR(20), -- pending, sent, delivered, read, failed
    line_sent_at TIMESTAMP,
    line_message_id VARCHAR(255),

    -- Response tracking
    responded BOOLEAN DEFAULT FALSE,
    response_text TEXT,
    response_channel VARCHAR(20),
    responded_at TIMESTAMP,
    response_sentiment VARCHAR(20), -- positive, neutral, negative
    response_intent VARCHAR(50), -- interested, question, complaint, unsubscribe

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Campaign Templates table (reusable message templates)
CREATE TABLE IF NOT EXISTS campaign_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,
    channel VARCHAR(20) NOT NULL, -- whatsapp, email, line

    -- Template content
    subject VARCHAR(255), -- For email
    body_template TEXT NOT NULL, -- With {{variables}}
    variables JSONB, -- List of required variables

    -- WhatsApp specific
    whatsapp_template_name VARCHAR(255),
    whatsapp_language VARCHAR(10),

    -- Approval status
    approved BOOLEAN DEFAULT FALSE,
    approved_at TIMESTAMP,

    -- Usage metrics
    times_used INTEGER DEFAULT 0,
    last_used_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Campaign Analytics table (aggregated metrics)
CREATE TABLE IF NOT EXISTS campaign_analytics (
    id SERIAL PRIMARY KEY,
    campaign_id UUID REFERENCES campaigns(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    hour INTEGER, -- 0-23, NULL for daily aggregates

    -- Delivery metrics
    sends INTEGER DEFAULT 0,
    deliveries INTEGER DEFAULT 0,
    opens INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    responses INTEGER DEFAULT 0,
    unsubscribes INTEGER DEFAULT 0,

    -- Channel breakdown
    whatsapp_sends INTEGER DEFAULT 0,
    whatsapp_deliveries INTEGER DEFAULT 0,
    email_sends INTEGER DEFAULT 0,
    email_opens INTEGER DEFAULT 0,
    line_sends INTEGER DEFAULT 0,
    line_reads INTEGER DEFAULT 0,

    -- Response analysis
    positive_responses INTEGER DEFAULT 0,
    negative_responses INTEGER DEFAULT 0,
    questions INTEGER DEFAULT 0,

    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(campaign_id, date, hour)
);

-- Contact Preferences table (opt-in/opt-out management)
CREATE TABLE IF NOT EXISTS contact_preferences (
    id SERIAL PRIMARY KEY,
    contact_id INTEGER REFERENCES contacts(id),
    venue_id INTEGER REFERENCES venues(id),

    -- Channel preferences
    whatsapp_opted_in BOOLEAN DEFAULT TRUE,
    email_opted_in BOOLEAN DEFAULT TRUE,
    line_opted_in BOOLEAN DEFAULT TRUE,

    -- Campaign type preferences
    renewal_reminders BOOLEAN DEFAULT TRUE,
    seasonal_offers BOOLEAN DEFAULT TRUE,
    announcements BOOLEAN DEFAULT TRUE,
    surveys BOOLEAN DEFAULT TRUE,

    -- Frequency preferences
    max_emails_per_week INTEGER DEFAULT 3,
    max_messages_per_week INTEGER DEFAULT 5,
    quiet_hours_start TIME, -- Don't contact before
    quiet_hours_end TIME, -- Don't contact after
    timezone VARCHAR(50) DEFAULT 'Asia/Bangkok',

    -- Unsubscribe tracking
    unsubscribed BOOLEAN DEFAULT FALSE,
    unsubscribe_reason TEXT,
    unsubscribed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(contact_id, venue_id)
);

-- Campaign Queue table (for scheduled sends)
CREATE TABLE IF NOT EXISTS campaign_queue (
    id SERIAL PRIMARY KEY,
    campaign_id UUID REFERENCES campaigns(id) ON DELETE CASCADE,
    recipient_id INTEGER REFERENCES campaign_recipients(id) ON DELETE CASCADE,
    channel VARCHAR(20) NOT NULL,
    scheduled_for TIMESTAMP NOT NULL,

    -- Processing
    status VARCHAR(20) DEFAULT 'pending', -- pending, processing, sent, failed
    attempts INTEGER DEFAULT 0,
    last_attempt_at TIMESTAMP,
    error_message TEXT,

    created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_campaigns_status ON campaigns(status) WHERE status != 'completed';
CREATE INDEX idx_campaigns_scheduled ON campaigns(scheduled_at) WHERE scheduled_at IS NOT NULL;
CREATE INDEX idx_campaign_recipients_campaign ON campaign_recipients(campaign_id);
CREATE INDEX idx_campaign_recipients_venue ON campaign_recipients(venue_id);
CREATE INDEX idx_campaign_recipients_responded ON campaign_recipients(responded) WHERE responded = TRUE;
CREATE INDEX idx_campaign_analytics_campaign_date ON campaign_analytics(campaign_id, date DESC);
CREATE INDEX idx_campaign_queue_scheduled ON campaign_queue(scheduled_for, status) WHERE status = 'pending';
CREATE INDEX idx_contact_preferences_contact ON contact_preferences(contact_id);
CREATE INDEX idx_contact_preferences_unsubscribed ON contact_preferences(unsubscribed) WHERE unsubscribed = TRUE;

-- Create functions for campaign metrics
CREATE OR REPLACE FUNCTION update_campaign_metrics()
RETURNS TRIGGER AS $$
BEGIN
    -- Update campaign metrics when recipient status changes
    UPDATE campaigns
    SET
        sent_count = (
            SELECT COUNT(*) FROM campaign_recipients
            WHERE campaign_id = NEW.campaign_id
            AND (whatsapp_status = 'sent' OR email_status = 'sent' OR line_status = 'sent')
        ),
        delivered_count = (
            SELECT COUNT(*) FROM campaign_recipients
            WHERE campaign_id = NEW.campaign_id
            AND (whatsapp_status = 'delivered' OR email_status = 'delivered' OR line_status = 'delivered')
        ),
        responded_count = (
            SELECT COUNT(*) FROM campaign_recipients
            WHERE campaign_id = NEW.campaign_id AND responded = TRUE
        ),
        updated_at = NOW()
    WHERE id = NEW.campaign_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to update metrics
CREATE TRIGGER update_campaign_metrics_trigger
AFTER INSERT OR UPDATE ON campaign_recipients
FOR EACH ROW
EXECUTE FUNCTION update_campaign_metrics();

-- Create function to get venue campaign history
CREATE OR REPLACE FUNCTION get_venue_campaign_history(
    venue_id_param INTEGER,
    limit_param INTEGER DEFAULT 10
)
RETURNS TABLE (
    campaign_name VARCHAR(255),
    campaign_type VARCHAR(50),
    sent_at TIMESTAMP,
    channel VARCHAR(20),
    status VARCHAR(20),
    responded BOOLEAN,
    response_text TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.name,
        c.type,
        COALESCE(cr.whatsapp_sent_at, cr.email_sent_at, cr.line_sent_at) as sent_at,
        CASE
            WHEN cr.whatsapp_sent_at IS NOT NULL THEN 'whatsapp'
            WHEN cr.email_sent_at IS NOT NULL THEN 'email'
            WHEN cr.line_sent_at IS NOT NULL THEN 'line'
        END as channel,
        COALESCE(cr.whatsapp_status, cr.email_status, cr.line_status) as status,
        cr.responded,
        cr.response_text
    FROM campaign_recipients cr
    JOIN campaigns c ON cr.campaign_id = c.id
    WHERE cr.venue_id = venue_id_param
    ORDER BY sent_at DESC
    LIMIT limit_param;
END;
$$ LANGUAGE plpgsql;

-- Add comments for documentation
COMMENT ON TABLE campaigns IS 'Main campaign records with AI-generated content';
COMMENT ON TABLE campaign_recipients IS 'Individual recipient tracking with multi-channel delivery';
COMMENT ON TABLE campaign_templates IS 'Reusable message templates for different channels';
COMMENT ON TABLE campaign_analytics IS 'Aggregated metrics for campaign performance';
COMMENT ON TABLE contact_preferences IS 'Contact opt-in/opt-out and communication preferences';
COMMENT ON TABLE campaign_queue IS 'Queue for scheduled campaign sends';

-- Grant permissions (adjust user as needed)
-- GRANT ALL ON ALL TABLES IN SCHEMA public TO bma_user;
-- GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO bma_user;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO bma_user;
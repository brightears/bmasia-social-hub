-- BMA Social Hub Database Schema
-- PostgreSQL schema for high-performance venue and product data management

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For fuzzy text matching

-- Drop existing tables if they exist (for clean migration)
DROP TABLE IF EXISTS messages CASCADE;
DROP TABLE IF EXISTS issues CASCADE;
DROP TABLE IF EXISTS conversations CASCADE;
DROP TABLE IF EXISTS product_info CASCADE;
DROP TABLE IF EXISTS contacts CASCADE;
DROP TABLE IF EXISTS zones CASCADE;
DROP TABLE IF EXISTS venues CASCADE;

-- Venues table (core entity)
CREATE TABLE venues (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    name_normalized VARCHAR(255), -- Lowercase, no special chars for matching
    business_type VARCHAR(100),
    zone_count INTEGER DEFAULT 0,
    platform VARCHAR(50), -- SYB, Beat Breeze, BMS
    annual_price_per_zone DECIMAL(10,2),
    currency VARCHAR(3),
    contract_start DATE,
    contract_end DATE,
    soundtrack_account_id VARCHAR(255),
    hardware_type TEXT,
    special_notes TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Zones table (music zones within venues)
CREATE TABLE zones (
    id SERIAL PRIMARY KEY,
    venue_id INTEGER REFERENCES venues(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    zone_id VARCHAR(255), -- Soundtrack zone ID if available
    zone_order INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'active', -- active, inactive, maintenance
    last_status_check TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Contacts table (venue contacts)
CREATE TABLE contacts (
    id SERIAL PRIMARY KEY,
    venue_id INTEGER REFERENCES venues(id) ON DELETE CASCADE,
    role VARCHAR(100), -- General Manager, Purchasing Manager, F&B Director, etc.
    name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    preferred_contact VARCHAR(20) DEFAULT 'email', -- email, phone, whatsapp
    notes TEXT,
    is_primary BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Product Information table (versioned product data)
CREATE TABLE product_info (
    id SERIAL PRIMARY KEY,
    product_name VARCHAR(100) NOT NULL, -- SYB, Beat Breeze
    category VARCHAR(50) NOT NULL, -- pricing, features, availability, licensing
    key VARCHAR(100) NOT NULL,
    value JSONB NOT NULL,
    version INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Conversations table (track all customer interactions)
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_phone VARCHAR(50) NOT NULL,
    customer_name VARCHAR(255),
    venue_id INTEGER REFERENCES venues(id),
    platform VARCHAR(20) NOT NULL, -- whatsapp, line, google_chat
    thread_key VARCHAR(255) UNIQUE,
    status VARCHAR(20) DEFAULT 'active', -- active, closed, escalated
    mode VARCHAR(20) DEFAULT 'bot', -- bot, human
    department VARCHAR(50), -- TECHNICAL, DESIGN, SALES, FINANCE
    priority VARCHAR(20) DEFAULT 'normal', -- critical, high, normal
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    last_message_at TIMESTAMP DEFAULT NOW(),
    closed_at TIMESTAMP
);

-- Messages table (conversation history)
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    sender_type VARCHAR(20) NOT NULL, -- customer, bot, human
    sender_id VARCHAR(255),
    content TEXT NOT NULL,
    message_type VARCHAR(50) DEFAULT 'text', -- text, image, command, escalation
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Issues table (track problems and resolutions)
CREATE TABLE issues (
    id SERIAL PRIMARY KEY,
    venue_id INTEGER REFERENCES venues(id),
    conversation_id UUID REFERENCES conversations(id),
    category VARCHAR(50), -- technical, billing, playlist, hardware
    status VARCHAR(20) DEFAULT 'open', -- open, in_progress, resolved, closed
    priority VARCHAR(20) DEFAULT 'normal', -- critical, high, normal, low
    description TEXT,
    resolution TEXT,
    assigned_to VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP
);

-- Create indexes for performance

-- Venue name matching (critical for bot performance)
CREATE INDEX idx_venues_name_trgm ON venues USING GIN(name gin_trgm_ops);
CREATE INDEX idx_venues_name_normalized ON venues(name_normalized);
CREATE INDEX idx_venues_platform ON venues(platform) WHERE is_active = TRUE;
CREATE INDEX idx_venues_contract_end ON venues(contract_end) WHERE contract_end IS NOT NULL;
CREATE INDEX idx_venues_active ON venues(is_active);

-- Zone lookups
CREATE INDEX idx_zones_venue_id ON zones(venue_id);
CREATE INDEX idx_zones_name ON zones(name);
CREATE INDEX idx_zones_status ON zones(status) WHERE status = 'active';

-- Contact searches
CREATE INDEX idx_contacts_venue_id ON contacts(venue_id);
CREATE INDEX idx_contacts_email ON contacts(email) WHERE email IS NOT NULL;
CREATE INDEX idx_contacts_role ON contacts(role);
CREATE INDEX idx_contacts_primary ON contacts(venue_id, is_primary) WHERE is_primary = TRUE;

-- Conversation tracking
CREATE INDEX idx_conversations_phone ON conversations(customer_phone);
CREATE INDEX idx_conversations_thread_key ON conversations(thread_key);
CREATE INDEX idx_conversations_venue_id ON conversations(venue_id) WHERE venue_id IS NOT NULL;
CREATE INDEX idx_conversations_status_mode ON conversations(status, mode);
CREATE INDEX idx_conversations_last_message ON conversations(last_message_at DESC);
CREATE INDEX idx_conversations_active ON conversations(status) WHERE status = 'active';

-- Message history (time-series optimized)
CREATE INDEX idx_messages_conversation_created ON messages(conversation_id, created_at DESC);
CREATE INDEX idx_messages_created_at ON messages(created_at DESC);

-- Product info lookups
CREATE INDEX idx_product_info_lookup ON product_info(product_name, category, key) WHERE is_active = TRUE;
CREATE INDEX idx_product_info_active ON product_info(is_active);

-- Issues tracking
CREATE INDEX idx_issues_venue_id ON issues(venue_id) WHERE status != 'closed';
CREATE INDEX idx_issues_conversation_id ON issues(conversation_id);
CREATE INDEX idx_issues_status ON issues(status) WHERE status IN ('open', 'in_progress');
CREATE INDEX idx_issues_priority ON issues(priority, created_at) WHERE status != 'closed';

-- Create function to normalize venue names for better matching
CREATE OR REPLACE FUNCTION normalize_name(input_text TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN LOWER(
        REGEXP_REPLACE(
            REGEXP_REPLACE(
                REGEXP_REPLACE(input_text, '[^a-zA-Z0-9\s]', '', 'g'),
                '\s+', ' ', 'g'
            ),
            '^\s+|\s+$', '', 'g'
        )
    );
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Create trigger to update normalized name
CREATE OR REPLACE FUNCTION update_venue_normalized_name()
RETURNS TRIGGER AS $$
BEGIN
    NEW.name_normalized = normalize_name(NEW.name);
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER venue_normalize_name
    BEFORE INSERT OR UPDATE OF name ON venues
    FOR EACH ROW
    EXECUTE FUNCTION update_venue_normalized_name();

-- Create function for venue similarity search
CREATE OR REPLACE FUNCTION search_venues(
    search_text TEXT,
    threshold FLOAT DEFAULT 0.3,
    limit_results INTEGER DEFAULT 10
)
RETURNS TABLE (
    venue_id INTEGER,
    venue_name VARCHAR(255),
    platform VARCHAR(50),
    zone_count INTEGER,
    match_score FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        v.id,
        v.name,
        v.platform,
        v.zone_count,
        similarity(v.name, search_text) as match_score
    FROM venues v
    WHERE v.is_active = TRUE
        AND similarity(v.name, search_text) > threshold
    ORDER BY match_score DESC, v.zone_count DESC
    LIMIT limit_results;
END;
$$ LANGUAGE plpgsql;

-- Create updated_at trigger for all tables
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at trigger to relevant tables
CREATE TRIGGER update_venues_updated_at BEFORE UPDATE ON venues
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_zones_updated_at BEFORE UPDATE ON zones
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_contacts_updated_at BEFORE UPDATE ON contacts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_product_info_updated_at BEFORE UPDATE ON product_info
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_issues_updated_at BEFORE UPDATE ON issues
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Add comments for documentation
COMMENT ON TABLE venues IS 'Music venues using BMA services';
COMMENT ON TABLE zones IS 'Music zones within venues (e.g., Lobby, Bar, Restaurant)';
COMMENT ON TABLE contacts IS 'Venue contact persons with roles';
COMMENT ON TABLE product_info IS 'Product information for SYB and Beat Breeze';
COMMENT ON TABLE conversations IS 'Customer support conversations across all channels';
COMMENT ON TABLE messages IS 'Individual messages within conversations';
COMMENT ON TABLE issues IS 'Problem tracking and resolution history';

-- Grant permissions (adjust user as needed for Render)
-- GRANT ALL ON ALL TABLES IN SCHEMA public TO bma_user;
-- GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO bma_user;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO bma_user;
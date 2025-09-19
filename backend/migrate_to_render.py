#!/usr/bin/env python3
"""
Complete migration script for Render PostgreSQL
This will create the proper schema and migrate all data
"""

import os
import sys
import re
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Schema definition (simplified for direct execution)
SCHEMA_SQL = """
-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Drop existing tables to start fresh
DROP TABLE IF EXISTS alerts CASCADE;
DROP TABLE IF EXISTS messages CASCADE;
DROP TABLE IF EXISTS conversations CASCADE;
DROP TABLE IF EXISTS zones CASCADE;
DROP TABLE IF EXISTS venues CASCADE;
DROP TABLE IF EXISTS contacts CASCADE;
DROP TABLE IF EXISTS product_info CASCADE;
DROP TABLE IF EXISTS issues CASCADE;

-- Venues table (core entity)
CREATE TABLE venues (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    name_normalized VARCHAR(255),
    business_type VARCHAR(100),
    zone_count INTEGER DEFAULT 0,
    platform VARCHAR(50),
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

-- Zones table
CREATE TABLE zones (
    id SERIAL PRIMARY KEY,
    venue_id INTEGER REFERENCES venues(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    zone_id VARCHAR(255),
    zone_order INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'active',
    last_status_check TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Contacts table
CREATE TABLE contacts (
    id SERIAL PRIMARY KEY,
    venue_id INTEGER REFERENCES venues(id) ON DELETE CASCADE,
    role VARCHAR(100),
    name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    preferred_contact VARCHAR(20) DEFAULT 'email',
    notes TEXT,
    is_primary BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Product Information table
CREATE TABLE product_info (
    id SERIAL PRIMARY KEY,
    product_name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    key VARCHAR(100) NOT NULL,
    value JSONB NOT NULL,
    version INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_venues_name_trgm ON venues USING GIN(name gin_trgm_ops);
CREATE INDEX idx_venues_name_normalized ON venues(name_normalized);
CREATE INDEX idx_venues_platform ON venues(platform) WHERE is_active = TRUE;
CREATE INDEX idx_zones_venue_id ON zones(venue_id);
CREATE INDEX idx_contacts_venue_id ON contacts(venue_id);
CREATE INDEX idx_product_info_lookup ON product_info(product_name, category, key) WHERE is_active = TRUE;

-- Create function to normalize venue names
CREATE OR REPLACE FUNCTION normalize_name(input_text TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN LOWER(
        REGEXP_REPLACE(
            REGEXP_REPLACE(
                REGEXP_REPLACE(input_text, '[^a-zA-Z0-9\\s]', '', 'g'),
                '\\s+', ' ', 'g'
            ),
            '^\\s+|\\s+$', '', 'g'
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
"""

def parse_venue_data(file_path):
    """Parse venue_data.md file and extract venue information"""
    venues = []

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split by venue sections (### marks each venue)
    venue_sections = re.split(r'\n### ', content)

    for section in venue_sections[1:]:  # Skip the header
        lines = section.strip().split('\n')
        if not lines:
            continue

        # Parse venue name
        venue_name = lines[0].strip()

        # Skip if it's metadata sections
        if venue_name in ['Statistics', 'Notes', 'Contract Status', 'Summary']:
            continue

        venue = {
            'name': venue_name,
            'zones': [],
            'contacts': [],
            'platform': None,
            'business_type': None,
            'contract_end': None,
            'annual_price': None,
            'currency': 'USD'
        }

        current_section = None

        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue

            # Detect sections
            if line.startswith('**Zones'):
                current_section = 'zones'
                continue
            elif line.startswith('**Contact'):
                current_section = 'contacts'
                continue
            elif line.startswith('**Platform'):
                venue['platform'] = line.split(':', 1)[1].strip() if ':' in line else None
                continue
            elif line.startswith('**Business Type'):
                venue['business_type'] = line.split(':', 1)[1].strip() if ':' in line else None
                continue
            elif line.startswith('**Contract End'):
                date_str = line.split(':', 1)[1].strip() if ':' in line else None
                if date_str and date_str != 'N/A':
                    try:
                        # Handle various date formats
                        venue['contract_end'] = date_str
                    except:
                        pass
                continue
            elif line.startswith('**Annual Price'):
                price_str = line.split(':', 1)[1].strip() if ':' in line else None
                if price_str:
                    # Extract number from price string
                    numbers = re.findall(r'[\d,]+\.?\d*', price_str)
                    if numbers:
                        venue['annual_price'] = float(numbers[0].replace(',', ''))
                continue

            # Parse section content
            if current_section == 'zones' and line.startswith('-'):
                zone_name = line[1:].strip()
                if zone_name and zone_name != 'N/A':
                    venue['zones'].append(zone_name)
            elif current_section == 'contacts' and line.startswith('-'):
                contact_info = line[1:].strip()
                if ':' in contact_info:
                    role, details = contact_info.split(':', 1)
                    contact = {'role': role.strip()}

                    # Extract name, email, phone
                    details = details.strip()
                    # Simple parsing - can be improved
                    if '(' in details:
                        name_part = details.split('(')[0].strip()
                        contact['name'] = name_part

                    # Extract email
                    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', details)
                    if email_match:
                        contact['email'] = email_match.group()

                    venue['contacts'].append(contact)

        if venue['name']:
            venues.append(venue)

    return venues

def migrate_to_database():
    """Main migration function"""
    print("🚀 BMA Social Database Migration to Render")
    print("="*60)

    # Get database URL from environment or construct it
    database_url = os.getenv('DATABASE_URL')

    if not database_url:
        # Try to construct from components
        host = os.getenv('DATABASE_HOST', 'dpg-d2m6jrre5dus739fr8p0-a.singapore-postgres.render.com')
        name = os.getenv('DATABASE_NAME', 'bma_social_esoq')
        user = os.getenv('DATABASE_USER', 'bma_user')
        password = os.getenv('DATABASE_PASSWORD', 'wVLGYkim3mf3qYocucd6IhXjogfLbZAb')

        database_url = f"postgresql://{user}:{password}@{host}/{name}?sslmode=require"

    # Connect to database
    print("\n1️⃣ Connecting to Render PostgreSQL...")
    try:
        # Use explicit parameters for better SSL handling
        conn = psycopg2.connect(
            host='dpg-d2m6jrre5dus739fr8p0-a.singapore-postgres.render.com',
            database='bma_social_esoq',
            user='bma_user',
            password='wVLGYkim3mf3qYocucd6IhXjogfLbZAb',
            sslmode='require'
        )
        cursor = conn.cursor()
        print("✅ Connected to database")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        print("\nPlease set DATABASE_URL or DATABASE_PASSWORD environment variable")
        return False

    # Create schema
    print("\n2️⃣ Creating database schema...")
    try:
        cursor.execute(SCHEMA_SQL)
        conn.commit()
        print("✅ Schema created successfully")
    except Exception as e:
        conn.rollback()
        print(f"❌ Failed to create schema: {e}")
        print("Attempting to continue with existing schema...")

    # Parse venue data
    print("\n3️⃣ Parsing venue data...")
    venue_file = 'venue_data.md'
    if not os.path.exists(venue_file):
        venue_file = '../venue_data.md'

    if not os.path.exists(venue_file):
        print(f"❌ Cannot find {venue_file}")
        return False

    venues = parse_venue_data(venue_file)
    print(f"✅ Parsed {len(venues)} venues")

    # Migrate venues
    print("\n4️⃣ Migrating venues to database...")
    venue_count = 0
    zone_count = 0
    contact_count = 0

    for venue in venues:
        try:
            # Insert venue
            cursor.execute("""
                INSERT INTO venues (
                    name, business_type, platform,
                    annual_price_per_zone, currency, zone_count
                ) VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                venue['name'],
                venue.get('business_type'),
                venue.get('platform'),
                venue.get('annual_price'),
                venue.get('currency', 'USD'),
                len(venue.get('zones', []))
            ))

            venue_id = cursor.fetchone()[0]
            venue_count += 1

            # Insert zones
            for i, zone_name in enumerate(venue.get('zones', [])):
                cursor.execute("""
                    INSERT INTO zones (venue_id, name, zone_order)
                    VALUES (%s, %s, %s)
                """, (venue_id, zone_name, i))
                zone_count += 1

            # Insert contacts
            for contact in venue.get('contacts', []):
                cursor.execute("""
                    INSERT INTO contacts (
                        venue_id, role, name, email
                    ) VALUES (%s, %s, %s, %s)
                """, (
                    venue_id,
                    contact.get('role'),
                    contact.get('name'),
                    contact.get('email')
                ))
                contact_count += 1

        except Exception as e:
            print(f"   ⚠️ Error migrating {venue['name']}: {e}")

    conn.commit()
    print(f"✅ Migrated {venue_count} venues, {zone_count} zones, {contact_count} contacts")

    # Add product info
    print("\n5️⃣ Adding product information...")
    product_records = [
        ('SYB', 'pricing', 'essential', {'price': 29, 'currency': 'USD', 'period': 'month', 'unit': 'zone'}),
        ('SYB', 'pricing', 'unlimited', {'price': 39, 'currency': 'USD', 'period': 'month', 'unit': 'zone'}),
        ('SYB', 'features', 'track_library', {'count': '100+ million', 'type': 'licensed tracks'}),
        ('SYB', 'licensing', 'pro_required', {'required': True, 'countries': ['Thailand', 'Singapore', 'USA']}),
        ('Beat Breeze', 'pricing', 'basic', {'price': 15, 'currency': 'USD', 'period': 'month', 'unit': 'location'}),
        ('Beat Breeze', 'pricing', 'pro', {'price': 25, 'currency': 'USD', 'period': 'month', 'unit': 'location'}),
        ('Beat Breeze', 'features', 'track_library', {'count': '30,000', 'type': 'royalty-free tracks'}),
        ('Beat Breeze', 'licensing', 'pro_required', {'required': False}),
    ]

    for product_name, category, key, value in product_records:
        try:
            cursor.execute("""
                INSERT INTO product_info (product_name, category, key, value)
                VALUES (%s, %s, %s, %s)
            """, (product_name, category, key, json.dumps(value)))
        except Exception as e:
            print(f"   ⚠️ Error adding product info: {e}")

    conn.commit()
    print("✅ Product information added")

    # Verify migration
    print("\n6️⃣ Verifying migration...")
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    tables = ['venues', 'zones', 'contacts', 'product_info']
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
        count = cursor.fetchone()['count']
        print(f"   {table}: {count} records")

    conn.close()

    print("\n" + "="*60)
    print("🎉 MIGRATION COMPLETE!")
    print("="*60)
    print("\nNext steps:")
    print("1. Update DATABASE_URL in Render environment variables")
    print("2. Set USE_DATABASE=false initially (for safety)")
    print("3. Deploy: git push origin main")
    print("4. Test the deployment")
    print("5. When ready, set USE_DATABASE=true in Render")

    return True

if __name__ == "__main__":
    # Check if we're in the right directory
    if not os.path.exists('venue_data.md') and not os.path.exists('../venue_data.md'):
        print("❌ Please run this script from the backend directory")
        sys.exit(1)

    success = migrate_to_database()
    sys.exit(0 if success else 1)
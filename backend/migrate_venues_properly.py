#!/usr/bin/env python3
"""
Proper venue migration script with correct parsing
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

def parse_venue_data_correctly(file_path):
    """Parse venue_data.md with the actual format"""
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
        if venue_name in ['Statistics', 'Notes', 'Contract Status', 'Summary', 'Total']:
            continue

        venue = {
            'name': venue_name,
            'zones': [],
            'contacts': [],
            'platform': None,
            'business_type': None,
            'zone_count': 0,
            'contract_end': None,
            'contract_start': None,
            'annual_price': None,
            'currency': 'THB',
            'soundtrack_account_id': None,
            'hardware_type': None
        }

        # Parse all the fields
        for line in lines[1:]:
            line = line.strip()
            if not line or not line.startswith('- **'):
                continue

            # Remove the leading "- **" and trailing "**"
            line = line[4:]  # Remove "- **"

            if '**:' in line:
                key, value = line.split('**:', 1)
                key = key.strip()
                value = value.strip()

                if value in ['—', 'N/A', '-', '']:
                    value = None

                if key == 'Business Type' and value:
                    venue['business_type'] = value
                elif key == 'Zone Count' and value:
                    try:
                        venue['zone_count'] = int(value)
                    except:
                        pass
                elif key == 'Zone Names' and value:
                    # Split zones by comma
                    zones = [z.strip() for z in value.split(',')]
                    venue['zones'] = [z for z in zones if z and z != 'N/A']
                elif key == 'Music Platform' and value:
                    venue['platform'] = value
                elif key == 'Annual Price per Zone' and value:
                    # Extract number
                    numbers = re.findall(r'[\d,]+\.?\d*', value)
                    if numbers:
                        try:
                            venue['annual_price'] = float(numbers[0].replace(',', ''))
                        except:
                            pass
                elif key == 'Currency' and value:
                    venue['currency'] = value[:3]  # Take first 3 chars
                elif key == 'Contract Start' and value:
                    venue['contract_start'] = value
                elif key == 'Contract End' and value:
                    venue['contract_end'] = value
                elif key == 'Soundtrack Account ID' and value:
                    venue['soundtrack_account_id'] = value
                elif key == 'Hardware Type' and value:
                    venue['hardware_type'] = value
                elif key.startswith('Contact') and value:
                    # Parse contact information
                    # Format: Role - Name (email/phone)
                    parts = value.split(' - ', 1)
                    if len(parts) == 2:
                        role = parts[0].strip()
                        details = parts[1].strip()

                        contact = {'role': role}

                        # Extract name (before parentheses)
                        if '(' in details:
                            contact['name'] = details.split('(')[0].strip()
                            # Extract email from parentheses
                            email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', details)
                            if email_match:
                                contact['email'] = email_match.group()
                        else:
                            contact['name'] = details

                        venue['contacts'].append(contact)

        if venue['name']:
            venues.append(venue)

    return venues

def migrate_venues_with_zones():
    """Migrate venues with proper zone and contact data"""
    print("🚀 Proper Venue Migration to Render PostgreSQL")
    print("="*60)

    # Connect to database
    print("\n1️⃣ Connecting to database...")
    conn = psycopg2.connect(
        host='dpg-d2m6jrre5dus739fr8p0-a.singapore-postgres.render.com',
        database='bma_social_esoq',
        user='bma_user',
        password='wVLGYkim3mf3qYocucd6IhXjogfLbZAb',
        sslmode='require'
    )
    cursor = conn.cursor()
    print("✅ Connected")

    # Clear existing data for clean migration
    print("\n2️⃣ Clearing existing data...")
    cursor.execute("DELETE FROM contacts")
    cursor.execute("DELETE FROM zones")
    cursor.execute("DELETE FROM venues")
    conn.commit()
    print("✅ Cleared")

    # Parse venue data with correct format
    print("\n3️⃣ Parsing venue data...")
    venues = parse_venue_data_correctly('venue_data.md')
    print(f"✅ Parsed {len(venues)} venues")

    # Show sample
    if venues:
        sample = venues[0]
        print(f"\nSample venue: {sample['name']}")
        print(f"  Business Type: {sample.get('business_type')}")
        print(f"  Zones: {sample.get('zones')}")
        print(f"  Zone Count: {sample.get('zone_count')}")
        print(f"  Platform: {sample.get('platform')}")

    # Migrate venues
    print("\n4️⃣ Migrating venues...")
    venue_count = 0
    zone_count = 0
    contact_count = 0

    for venue in venues:
        try:
            # Prepare dates
            contract_start = None
            contract_end = None

            if venue.get('contract_start'):
                try:
                    contract_start = datetime.strptime(venue['contract_start'], '%Y-%m-%d').date()
                except:
                    pass

            if venue.get('contract_end'):
                try:
                    contract_end = datetime.strptime(venue['contract_end'], '%Y-%m-%d').date()
                except:
                    pass

            # Insert venue
            cursor.execute("""
                INSERT INTO venues (
                    name, business_type, platform, zone_count,
                    annual_price_per_zone, currency,
                    contract_start, contract_end,
                    soundtrack_account_id, hardware_type
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                venue['name'],
                venue.get('business_type'),
                venue.get('platform'),
                venue.get('zone_count', 0),
                venue.get('annual_price'),
                venue.get('currency'),
                contract_start,
                contract_end,
                venue.get('soundtrack_account_id'),
                venue.get('hardware_type')
            ))

            venue_id = cursor.fetchone()[0]
            venue_count += 1

            # Insert zones
            for i, zone_name in enumerate(venue.get('zones', [])):
                if zone_name and zone_name != 'N/A':
                    cursor.execute("""
                        INSERT INTO zones (venue_id, name, zone_order)
                        VALUES (%s, %s, %s)
                    """, (venue_id, zone_name, i))
                    zone_count += 1

            # Insert contacts
            for contact in venue.get('contacts', []):
                if contact.get('name') or contact.get('email'):
                    cursor.execute("""
                        INSERT INTO contacts (
                            venue_id, role, name, email, is_primary
                        ) VALUES (%s, %s, %s, %s, %s)
                    """, (
                        venue_id,
                        contact.get('role', 'Contact'),
                        contact.get('name'),
                        contact.get('email'),
                        len(venue.get('contacts', [])) == 1  # Primary if only contact
                    ))
                    contact_count += 1

        except Exception as e:
            print(f"  ⚠️ Error with {venue['name']}: {e}")
            conn.rollback()
            continue

        # Commit every 100 venues
        if venue_count % 100 == 0:
            conn.commit()
            print(f"  Progress: {venue_count} venues...")

    conn.commit()
    print(f"✅ Migrated {venue_count} venues, {zone_count} zones, {contact_count} contacts")

    # Verify
    print("\n5️⃣ Verifying migration...")
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # Count records
    tables = ['venues', 'zones', 'contacts']
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
        count = cursor.fetchone()['count']
        print(f"  {table}: {count} records")

    # Sample venues with zones
    cursor.execute("""
        SELECT v.name, v.platform, v.zone_count,
               array_agg(z.name ORDER BY z.zone_order) as zone_names
        FROM venues v
        LEFT JOIN zones z ON v.id = z.venue_id
        WHERE v.zone_count > 0
        GROUP BY v.id, v.name, v.platform, v.zone_count
        LIMIT 5
    """)
    samples = cursor.fetchall()

    print("\nSample venues with zones:")
    for venue in samples:
        zones = venue['zone_names'] if venue['zone_names'][0] else []
        print(f"  - {venue['name']} ({venue['platform']}): {len(zones)} zones")
        if zones:
            print(f"    Zones: {', '.join(zones[:3])}")

    conn.close()

    print("\n" + "="*60)
    print("🎉 MIGRATION COMPLETE WITH ZONES AND CONTACTS!")
    print("="*60)

if __name__ == "__main__":
    migrate_venues_with_zones()
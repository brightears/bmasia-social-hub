#!/usr/bin/env python3
"""
Add campaign tables to the existing Render PostgreSQL database
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Read the campaign schema
with open('database/campaign_schema.sql', 'r') as f:
    CAMPAIGN_SCHEMA = f.read()

def add_campaign_tables():
    """Add campaign tables to existing database"""
    print("🚀 Adding Campaign Tables to Database")
    print("="*60)

    # Connect to database
    conn = psycopg2.connect(
        host='dpg-d2m6jrre5dus739fr8p0-a.singapore-postgres.render.com',
        database='bma_social_esoq',
        user='bma_user',
        password='wVLGYkim3mf3qYocucd6IhXjogfLbZAb',
        sslmode='require'
    )
    cursor = conn.cursor()

    try:
        # Execute the schema
        print("Creating campaign tables...")
        cursor.execute(CAMPAIGN_SCHEMA)
        conn.commit()
        print("✅ Campaign tables created successfully")

        # Verify tables
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name LIKE 'campaign%'
            ORDER BY table_name
        """)
        tables = cursor.fetchall()

        print(f"\n📊 Created {len(tables)} campaign tables:")
        for table in tables:
            print(f"   - {table[0]}")

        conn.close()
        print("\n✅ Campaign database setup complete!")
        return True

    except Exception as e:
        conn.rollback()
        print(f"❌ Error: {e}")
        conn.close()
        return False

if __name__ == "__main__":
    add_campaign_tables()
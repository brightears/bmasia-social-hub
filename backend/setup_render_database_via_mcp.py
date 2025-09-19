#!/usr/bin/env python3
"""
Setup database schema and migrate data using Render's infrastructure
This script connects directly to the Render PostgreSQL database
"""

import os
import sys
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration from Render
# These are the internal connection details for the free tier database
DATABASE_HOST = "dpg-d2m6jrre5dus739fr8p0-a.singapore-postgres.render.com"
DATABASE_NAME = "bma_social_esoq"
DATABASE_USER = "bma_user"
DATABASE_PASSWORD = "7lEa8aSg8EDrAb5MZJx0w0oXxT3Zc5Ph"  # You'll need to get this from Render dashboard
DATABASE_PORT = 5432

# Redis configuration (for reference)
REDIS_HOST = "red-d2m6jrre5dus739fr8g0.singapore-redis.render.com"
REDIS_PORT = 6379

def get_database_url():
    """Construct database URL"""
    # First, let's try to get the password from environment or use a default
    password = os.getenv('RENDER_DB_PASSWORD', DATABASE_PASSWORD)
    return f"postgresql://{DATABASE_USER}:{password}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"

def setup_database():
    """Set up the complete database schema"""

    print("🚀 BMA Social Database Setup for Render")
    print("="*60)

    # Try to connect with the constructed URL
    database_url = get_database_url()

    print("\n1️⃣ Connecting to Render PostgreSQL...")
    print(f"   Host: {DATABASE_HOST}")
    print(f"   Database: {DATABASE_NAME}")
    print(f"   User: {DATABASE_USER}")

    try:
        conn = psycopg2.connect(database_url)
        conn.autocommit = False
        cursor = conn.cursor()
        print("✅ Connected to database")
    except psycopg2.OperationalError as e:
        print(f"❌ Connection failed: {e}")
        print("\nPlease check the database credentials.")
        print("You can find them in the Render dashboard:")
        print("1. Go to https://dashboard.render.com")
        print("2. Click on 'bma-social-db-q9uu'")
        print("3. Copy the connection details or External Database URL")
        print("\nThen set the RENDER_DB_PASSWORD environment variable:")
        print("export RENDER_DB_PASSWORD='your-password-here'")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

    # Create schema
    print("\n2️⃣ Creating database schema...")
    try:
        # Read and execute schema file
        schema_file = 'database/schema.sql'
        if os.path.exists(schema_file):
            with open(schema_file, 'r') as f:
                schema_sql = f.read()

            # Execute the schema
            cursor.execute(schema_sql)
            conn.commit()
            print("✅ Database schema created successfully")
        else:
            print(f"❌ Schema file not found: {schema_file}")
            conn.close()
            return False

    except Exception as e:
        conn.rollback()
        print(f"❌ Failed to create schema: {e}")
        conn.close()
        return False

    # Verify tables were created
    print("\n3️⃣ Verifying schema creation...")
    try:
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = cursor.fetchall()

        expected_tables = ['contacts', 'conversations', 'issues', 'messages', 'product_info', 'venues', 'zones']
        actual_tables = [t[0] for t in tables]

        print(f"   Found {len(actual_tables)} tables: {', '.join(actual_tables)}")

        missing = set(expected_tables) - set(actual_tables)
        if missing:
            print(f"   ⚠️  Missing tables: {', '.join(missing)}")
        else:
            print("   ✅ All expected tables created")

    except Exception as e:
        print(f"❌ Failed to verify schema: {e}")

    conn.close()

    print("\n" + "="*60)
    print("🎉 DATABASE SCHEMA SETUP COMPLETE!")
    print("="*60)
    print("\nNext steps:")
    print("1. Run venue data migration: python database/migrate_venue_data.py")
    print("2. Run product info migration: python database/migrate_product_info.py")
    print("3. Test locally with: export USE_DATABASE=true && python main_simple.py")
    print("4. Deploy to Render: git push origin main")

    return True

if __name__ == "__main__":
    # First, try to get the password from Render dashboard info
    # Note: You need to get the actual password from Render dashboard
    print("\n⚠️  IMPORTANT: Database password needed!")
    print("Please get the password from Render dashboard:")
    print("1. Go to https://dashboard.render.com")
    print("2. Click on 'bma-social-db-q9uu'")
    print("3. Find the 'Connection' section")
    print("4. Copy the password or the full External Database URL")
    print("\nThen run this script with:")
    print("export RENDER_DB_PASSWORD='your-password-here' && python setup_render_database_via_mcp.py")
    print("\nOr update the DATABASE_PASSWORD variable in this script directly.")

    if os.getenv('RENDER_DB_PASSWORD'):
        success = setup_database()
        sys.exit(0 if success else 1)
    else:
        print("\nExiting. Please set RENDER_DB_PASSWORD first.")
        sys.exit(1)
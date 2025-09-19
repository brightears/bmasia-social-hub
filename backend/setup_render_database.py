#!/usr/bin/env python3
"""
Complete database setup for Render PostgreSQL
This script will create schema and migrate all data
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Render database credentials (from MCP query)
RENDER_DATABASE_URL = "postgresql://bma_user:7lEa8aSg8EDrAb5MZJx0w0oXxT3Zc5Ph@dpg-d2m6jrre5dus739fr8p0-a.singapore-postgres.render.com/bma_social_esoq"
RENDER_REDIS_URL = "rediss://red-d2m6jrre5dus739fr8g0:fRE2KOLMNnQ0q2pK9fVBzUqBP19PVNOs@singapore-redis.render.com:6380"

def setup_database():
    """Set up the complete database schema and migrate data"""

    print("🚀 BMA Social Database Setup for Render")
    print("="*60)

    # Save credentials to .env file
    print("\n1️⃣ Saving database credentials to .env...")

    env_file = ".env"
    env_content = []

    # Read existing .env if it exists
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            env_content = f.readlines()

    # Update or add database URLs
    database_url_found = False
    redis_url_found = False
    use_database_found = False

    new_env = []
    for line in env_content:
        if line.startswith('DATABASE_URL='):
            database_url_found = True
            new_env.append(f'DATABASE_URL={RENDER_DATABASE_URL}\n')
        elif line.startswith('REDIS_URL='):
            redis_url_found = True
            new_env.append(f'REDIS_URL={RENDER_REDIS_URL}\n')
        elif line.startswith('USE_DATABASE='):
            use_database_found = True
            new_env.append('USE_DATABASE=false  # Start with false for testing\n')
        else:
            new_env.append(line)

    # Add missing variables
    if not database_url_found:
        new_env.append(f'\n# Database Configuration (Added by setup script)\n')
        new_env.append(f'DATABASE_URL={RENDER_DATABASE_URL}\n')
    if not redis_url_found:
        new_env.append(f'REDIS_URL={RENDER_REDIS_URL}\n')
    if not use_database_found:
        new_env.append(f'USE_DATABASE=false  # Start with false for testing\n')

    # Write updated .env
    with open(env_file, 'w') as f:
        f.writelines(new_env)

    print("✅ Database credentials saved to .env file")

    # Connect to database
    print("\n2️⃣ Connecting to Render PostgreSQL...")
    try:
        conn = psycopg2.connect(RENDER_DATABASE_URL)
        conn.autocommit = False
        cursor = conn.cursor()
        print("✅ Connected to database")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return False

    # Drop existing tables and recreate schema
    print("\n3️⃣ Creating database schema...")
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
            return False

    except Exception as e:
        conn.rollback()
        print(f"❌ Failed to create schema: {e}")
        return False

    # Migrate venue data
    print("\n4️⃣ Migrating venue data...")
    try:
        # Import and run the migration
        sys.path.insert(0, 'database')
        from migrate_venue_data import VenueDataMigrator

        migrator = VenueDataMigrator(RENDER_DATABASE_URL)
        migrator.connect()

        # Parse venue data
        venues = migrator.parse_venue_data('venue_data.md')
        print(f"   Parsed {len(venues)} venues")

        # Migrate to database
        migrator.migrate_to_database(venues)

        # Verify
        migrator.verify_migration()
        migrator.disconnect()

        print("✅ Venue data migration completed")

    except Exception as e:
        print(f"❌ Failed to migrate venue data: {e}")
        return False

    # Migrate product info
    print("\n5️⃣ Migrating product information...")
    try:
        from migrate_product_info import ProductInfoMigrator

        product_migrator = ProductInfoMigrator(RENDER_DATABASE_URL)
        product_migrator.connect()

        # Create and migrate product records
        records = product_migrator.create_product_records()
        print(f"   Created {len(records)} product records")

        product_migrator.migrate_to_database(records)

        # Verify
        product_migrator.verify_migration()
        product_migrator.disconnect()

        print("✅ Product information migration completed")

    except Exception as e:
        print(f"❌ Failed to migrate product info: {e}")
        return False

    # Final verification
    print("\n6️⃣ Final verification...")
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Check record counts
        tables = ['venues', 'zones', 'contacts', 'product_info']
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
            count = cursor.fetchone()['count']
            print(f"   {table}: {count} records")

        # Test venue search
        cursor.execute("""
            SELECT name, platform, zone_count
            FROM venues
            WHERE name ILIKE '%hilton%'
            LIMIT 3
        """)
        hiltons = cursor.fetchall()

        print(f"\n   Sample Hilton venues found: {len(hiltons)}")
        for venue in hiltons:
            print(f"     - {venue['name']} ({venue['platform']}): {venue['zone_count']} zones")

        conn.close()

    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

    # Success!
    print("\n" + "="*60)
    print("🎉 DATABASE SETUP COMPLETE!")
    print("="*60)
    print("\nNext steps:")
    print("1. Test locally with: export USE_DATABASE=true && python main_simple.py")
    print("2. Update Render environment variables")
    print("3. Deploy with: git push origin main")
    print("4. Monitor logs and switch USE_DATABASE=true when ready")

    return True

if __name__ == "__main__":
    success = setup_database()
    sys.exit(0 if success else 1)
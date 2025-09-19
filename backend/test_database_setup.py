#!/usr/bin/env python3
"""
Test script to verify database setup and migration
Run this before deploying to production
"""

import os
import sys
import asyncio
import json
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# Load environment variables
load_dotenv()

def test_database_connection():
    """Test PostgreSQL connection"""
    print("\n🔍 Testing PostgreSQL connection...")

    # Try to get DATABASE_URL from environment
    database_url = os.getenv('DATABASE_URL')

    if not database_url:
        print("❌ DATABASE_URL not found in .env file")
        print("\nPlease add to your .env file:")
        print("DATABASE_URL=postgresql://bma_user:password@host:port/bma_social_esoq")
        print("\nYou can find the connection string in Render dashboard:")
        print("1. Go to https://dashboard.render.com")
        print("2. Click on 'bma-social-db-q9uu'")
        print("3. Copy the 'External Database URL'")
        return False

    try:
        # Test connection
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()
        print(f"✅ Connected to PostgreSQL: {version[0][:30]}...")

        # Check if tables exist
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        tables = cursor.fetchall()

        if not tables:
            print("⚠️  No tables found. Database schema needs to be created.")
            print("\nRun: psql $DATABASE_URL < database/schema.sql")
            return False
        else:
            print(f"\n📊 Found {len(tables)} tables:")
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
                count = cursor.fetchone()[0]
                print(f"   - {table[0]}: {count} records")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_redis_connection():
    """Test Redis connection"""
    print("\n🔍 Testing Redis connection...")

    redis_url = os.getenv('REDIS_URL')

    if not redis_url:
        print("⚠️  REDIS_URL not found in .env file (optional but recommended)")
        print("\nTo enable caching, add to your .env file:")
        print("REDIS_URL=redis://red-abc123:password@host:port")
        return False

    try:
        import redis
        r = redis.from_url(redis_url)
        r.ping()
        print("✅ Connected to Redis/Valkey")

        # Test basic operations
        r.set('test_key', 'test_value', ex=10)
        value = r.get('test_key')
        if value:
            print("✅ Redis read/write test successful")
        r.delete('test_key')

        return True

    except ImportError:
        print("⚠️  redis package not installed. Run: pip install redis")
        return False
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False

async def test_database_manager():
    """Test the database manager"""
    print("\n🔍 Testing Database Manager...")

    try:
        from database_manager import DatabaseManager

        database_url = os.getenv('DATABASE_URL')
        redis_url = os.getenv('REDIS_URL')

        if not database_url:
            print("❌ Cannot test database manager without DATABASE_URL")
            return False

        # Create manager
        db_manager = DatabaseManager(database_url, redis_url)
        await db_manager.initialize()
        print("✅ Database manager initialized")

        # Test venue search
        print("\n📍 Testing venue search...")
        venues = await db_manager.find_venues_by_name("Hilton", threshold=0.3)

        if venues:
            print(f"✅ Found {len(venues)} venues matching 'Hilton':")
            for venue in venues[:3]:
                print(f"   - {venue['name']} (score: {venue.get('match_score', 0):.2f})")
        else:
            print("⚠️  No venues found. Database might be empty.")
            print("   Run: python database/migrate_venue_data.py")

        # Test product info
        print("\n📦 Testing product info...")
        products = await db_manager.get_product_info(['SYB', 'Beat Breeze'])

        if products:
            print(f"✅ Found {len(products)} product records")
            categories = set(p['category'] for p in products)
            print(f"   Categories: {', '.join(categories)}")
        else:
            print("⚠️  No product info found. Database might be empty.")
            print("   Run: python database/migrate_product_info.py")

        # Test health check
        health = await db_manager.health_check()
        print(f"\n💚 Health check: {health}")

        await db_manager.close()
        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure you're in the backend directory")
        return False
    except Exception as e:
        print(f"❌ Database manager test failed: {e}")
        return False

async def test_hybrid_venue_manager():
    """Test the hybrid venue manager"""
    print("\n🔍 Testing Hybrid Venue Manager...")

    try:
        from venue_manager_hybrid import HybridVenueManager

        # Test file mode
        print("\n📁 Testing FILE mode...")
        os.environ['USE_DATABASE'] = 'false'
        manager = HybridVenueManager()
        await manager.initialize()

        venue, confidence = manager.find_venue_with_confidence("Hilton Pattaya")
        if venue:
            print(f"✅ File mode: Found {venue['name']} (confidence: {confidence:.2f})")
        else:
            print("⚠️  File mode: No venue found")

        # Test database mode
        if os.getenv('DATABASE_URL'):
            print("\n💾 Testing DATABASE mode...")
            os.environ['USE_DATABASE'] = 'true'
            manager = HybridVenueManager()
            await manager.initialize()

            venue, confidence = await manager.find_venue_with_confidence_async("Hilton Pattaya")
            if venue:
                print(f"✅ Database mode: Found {venue['name']} (confidence: {confidence:.2f})")
            else:
                print("⚠️  Database mode: No venue found")

        return True

    except Exception as e:
        print(f"❌ Hybrid venue manager test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("="*60)
    print("BMA SOCIAL DATABASE SETUP TEST")
    print("="*60)

    # Check Python packages
    print("\n📦 Checking required packages...")
    required = ['psycopg2', 'asyncpg', 'redis', 'python-dotenv']
    missing = []

    for package in required:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package}")
            missing.append(package)

    if missing:
        print(f"\n⚠️  Missing packages. Run: pip install {' '.join(missing)}")
        return

    # Test connections
    db_ok = test_database_connection()
    redis_ok = test_redis_connection()

    # Test async components
    if db_ok:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(test_database_manager())
            loop.run_until_complete(test_hybrid_venue_manager())
        finally:
            loop.close()

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    if db_ok:
        print("✅ PostgreSQL is configured and accessible")
        print("\nNext steps:")
        print("1. Run database migration if needed:")
        print("   cd database")
        print("   python migrate_venue_data.py")
        print("   python migrate_product_info.py")
        print("\n2. Test the bot locally:")
        print("   export USE_DATABASE=true")
        print("   python main_simple.py")
        print("\n3. Deploy to Render:")
        print("   git add .")
        print("   git commit -m 'Add database support'")
        print("   git push origin main")
    else:
        print("❌ Database setup incomplete")
        print("\nPlease configure DATABASE_URL in your .env file")
        print("Get the connection string from Render dashboard")

    print("="*60)

if __name__ == "__main__":
    main()
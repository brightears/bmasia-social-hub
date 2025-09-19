#!/usr/bin/env python3
"""
Test the database-enabled bot
"""

import os
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set database mode
os.environ['USE_DATABASE'] = 'true'
os.environ['DATABASE_URL'] = 'postgresql://bma_user:wVLGYkim3mf3qYocucd6IhXjogfLbZAb@dpg-d2m6jrre5dus739fr8p0-a.singapore-postgres.render.com/bma_social_esoq?sslmode=require'

async def test_bot():
    """Test the bot with database"""
    print("🔍 Testing Database-Enabled Bot")
    print("="*60)

    # Test hybrid venue manager
    print("\n1️⃣ Testing Hybrid Venue Manager...")
    from venue_manager_hybrid import HybridVenueManager

    manager = HybridVenueManager()
    await manager.initialize()

    # Test venue lookups
    test_cases = [
        "Hi from Hilton Pattaya",
        "Hello from One Bangkok",
        "Help from Ad Lib Bangkok",
        "Random message without venue",
        "ok"  # This should NOT match any venue now
    ]

    for message in test_cases:
        print(f"\n  Testing: '{message}'")
        venue, confidence = await manager.find_venue_with_confidence_async(
            message, phone="+66123456789"
        )

        if venue:
            print(f"    ✅ Found: {venue['name']} (confidence: {confidence:.2%})")
            print(f"       Platform: {venue.get('platform')}")
            print(f"       Zones: {venue.get('zone_count')} zones")
        else:
            print(f"    ❌ No venue found (confidence < 90%)")

    # Test database manager directly
    print("\n2️⃣ Testing Database Manager...")
    from database_manager import DatabaseManager

    db_manager = DatabaseManager(os.environ['DATABASE_URL'])
    await db_manager.initialize()

    # Test venue search
    import time
    start = time.time()
    venues = await db_manager.find_venues_by_name("Hilton", threshold=0.3)
    elapsed = (time.time() - start) * 1000

    print(f"\n  Database search for 'Hilton': {len(venues)} results in {elapsed:.1f}ms")
    for venue in venues[:3]:
        print(f"    - {venue['name']} (score: {venue['match_score']:.2f})")

    # Test product info
    products = await db_manager.get_product_info(['SYB', 'Beat Breeze'])
    print(f"\n  Product info records: {len(products)}")

    # Health check
    health = await db_manager.health_check()
    print(f"\n  Health check: {'✅ Healthy' if health['database'] else '❌ Unhealthy'}")
    print(f"    - Pool size: {health.get('pool_size', 0)}")
    print(f"    - Redis: {'Connected' if health.get('redis') else 'Not connected'}")

    await db_manager.close()
    await manager.close() if hasattr(manager, 'close') else None

    print("\n" + "="*60)
    print("✅ DATABASE BOT TEST COMPLETE!")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(test_bot())
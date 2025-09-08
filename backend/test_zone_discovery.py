#!/usr/bin/env python3
"""
Test the zone discovery service
This will help us understand what zones we can access
"""

import logging
import json
from zone_discovery import zone_discovery, get_zone_id

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_specific_zone():
    """Test getting a specific zone"""
    print("\n=== Testing Hilton Pattaya Edge zone ===")
    zone_id = get_zone_id("Hilton Pattaya", "Edge")
    if zone_id:
        print(f"✅ Found Edge zone: {zone_id[:50]}...")
    else:
        print("❌ Edge zone not found")
    
    print("\n=== Testing Hilton Pattaya Drift Bar zone ===")
    zone_id = get_zone_id("Hilton Pattaya", "Drift Bar")
    if zone_id:
        print(f"✅ Found Drift Bar zone: {zone_id[:50]}...")
    else:
        print("❌ Drift Bar zone not found")

def discover_all_available_zones():
    """Discover all zones we have access to"""
    print("\n=== Discovering all accessible zones ===")
    discovered = zone_discovery.discover_and_cache_all_zones()
    
    if discovered:
        print(f"\n✅ Discovered {len(discovered)} venues with zones:")
        for venue_name, zones in discovered.items():
            print(f"\n  {venue_name}:")
            for zone_name, zone_id in zones.items():
                print(f"    - {zone_name}: {zone_id[:30]}...")
    else:
        print("❌ No zones discovered via API")
    
    return discovered

def test_api_access():
    """Test what we can access via the API"""
    print("\n=== Testing API Access ===")
    
    from soundtrack_api import SoundtrackAPI
    api = SoundtrackAPI()
    
    # Test getting accounts
    accounts = api.get_accounts(limit=10)
    
    if accounts:
        print(f"\n✅ Can access {len(accounts)} accounts:")
        for acc in accounts:
            print(f"  - {acc.get('businessName', 'Unknown')}: {acc.get('id', 'No ID')[:30]}...")
    else:
        print("❌ No accounts accessible via API")

if __name__ == "__main__":
    print("Zone Discovery Service Test")
    print("=" * 50)
    
    # Test API access first
    test_api_access()
    
    # Test specific zones (using hardcoded fallback)
    test_specific_zone()
    
    # Try to discover all zones
    discovered = discover_all_available_zones()
    
    # Save results
    if discovered:
        with open('discovered_zones_test.json', 'w') as f:
            json.dump(discovered, f, indent=2)
        print(f"\n💾 Results saved to discovered_zones_test.json")
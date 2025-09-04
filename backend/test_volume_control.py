#!/usr/bin/env python3
"""
Test volume control capabilities on different SYB zones
Find out which zones allow control and which don't
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from soundtrack_api import soundtrack_api

def test_volume_control():
    """Test volume control on various zones"""
    
    print("\n" + "="*60)
    print("TESTING SYB VOLUME CONTROL CAPABILITIES")
    print("="*60 + "\n")
    
    # Find Hilton Pattaya zones
    print("Searching for Hilton Pattaya zones...")
    zones = soundtrack_api.find_venue_zones("Hilton Pattaya")
    
    if not zones:
        print("No zones found for Hilton Pattaya")
        # Try broader search
        print("\nSearching all available zones...")
        all_zones = []
        accounts = soundtrack_api.get_accounts()
        
        for account in accounts[:5]:  # Test first 5 accounts
            print(f"  Checking account: {account.get('name', 'Unknown')}")
            # Get zones from account structure
            for loc_edge in account.get('locations', {}).get('edges', []):
                location = loc_edge['node']
                for zone_edge in location.get('soundZones', {}).get('edges', []):
                    zone = zone_edge['node']
                    zone['location_name'] = location.get('name')
                    zone['account_name'] = account.get('name')
                    all_zones.append(zone)
        
        zones = all_zones[:10]  # Test up to 10 zones
    
    print(f"\nFound {len(zones)} zones to test\n")
    
    # Test results
    controllable_zones = []
    non_controllable_zones = []
    
    for i, zone in enumerate(zones, 1):
        zone_id = zone.get('id')
        zone_name = zone.get('name', 'Unknown')
        streaming_type = zone.get('streamingType', 'Unknown')
        
        print(f"{i}. Testing zone: {zone_name}")
        print(f"   Zone ID: {zone_id}")
        print(f"   Type: {streaming_type}")
        
        # Get zone status first
        status = soundtrack_api.get_zone_status(zone_id)
        if status.get('error'):
            print(f"   Status check: ❌ {status['error']}")
        else:
            print(f"   Status check: ✅ Zone accessible")
        
        # Test volume control
        print(f"   Testing volume control...")
        
        # Try to set volume to 8 (middle of 0-16 range)
        result = soundtrack_api.set_volume(zone_id, 8)
        
        if result.get('success'):
            print(f"   Volume control: ✅ SUCCESS! Can control this zone")
            controllable_zones.append({
                'name': zone_name,
                'id': zone_id,
                'type': streaming_type
            })
            
            # Try different volume levels
            print("   Testing volume range...")
            for vol in [4, 12, 8]:  # Test low, high, medium
                vol_result = soundtrack_api.set_volume(zone_id, vol)
                if vol_result.get('success'):
                    print(f"     Level {vol}/16: ✅")
                else:
                    print(f"     Level {vol}/16: ❌")
            
        else:
            print(f"   Volume control: ❌ {result.get('error', 'Unknown error')}")
            non_controllable_zones.append({
                'name': zone_name,
                'id': zone_id,
                'type': streaming_type,
                'error': result.get('error')
            })
        
        print()
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60 + "\n")
    
    if controllable_zones:
        print(f"✅ CONTROLLABLE ZONES ({len(controllable_zones)}):")
        for zone in controllable_zones:
            print(f"   • {zone['name']} (Type: {zone['type']})")
            print(f"     ID: {zone['id']}")
    else:
        print("❌ No controllable zones found with current credentials")
    
    if non_controllable_zones:
        print(f"\n❌ NON-CONTROLLABLE ZONES ({len(non_controllable_zones)}):")
        for zone in non_controllable_zones:
            print(f"   • {zone['name']} (Type: {zone['type']})")
            print(f"     Reason: {zone['error']}")
    
    # Analysis
    print("\n" + "="*60)
    print("ANALYSIS")
    print("="*60 + "\n")
    
    # Check patterns
    trial_zones = [z for z in non_controllable_zones if 'trial' in z.get('type', '').lower() or 'tier_3' in z.get('type', '').lower()]
    if trial_zones:
        print(f"• {len(trial_zones)} zones are TRIAL/TIER_3 type (likely restricted)")
    
    if controllable_zones:
        types = set(z['type'] for z in controllable_zones)
        print(f"• Controllable zones have types: {', '.join(types)}")
    
    print("\nCONCLUSION:")
    if controllable_zones:
        print("✅ Volume control IS POSSIBLE for some zones!")
        print("   The bot CAN control volume for properly configured zones.")
        print("   Need to check zone type/permissions before attempting control.")
    else:
        print("⚠️ Current credentials may have limited permissions")
        print("   Consider using production credentials for full control")
        print("   Your web app likely used different credentials/zones")
    
    return controllable_zones, non_controllable_zones


def test_specific_zone(zone_id: str):
    """Test a specific zone's capabilities"""
    print(f"\nTesting specific zone: {zone_id}")
    print("-" * 40)
    
    # Get zone info
    status = soundtrack_api.get_zone_status(zone_id)
    print(f"Zone name: {status.get('name', 'Unknown')}")
    print(f"Type: {status.get('streamingType', 'Unknown')}")
    
    # Test capabilities
    capabilities = soundtrack_api.get_zone_capabilities(zone_id)
    
    print("\nCapabilities:")
    for key, value in capabilities.items():
        symbol = "✅" if value else "❌"
        print(f"  {symbol} {key}: {value}")
    
    return capabilities


if __name__ == "__main__":
    # Test general zones
    controllable, non_controllable = test_volume_control()
    
    # If you have a specific zone ID from your web app, test it here:
    # test_specific_zone("YOUR_ZONE_ID_HERE")
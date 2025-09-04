#!/usr/bin/env python3
"""
Detailed analysis of zone capabilities to understand what makes zones controllable
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

def analyze_zones_in_detail():
    """Get detailed information about all zones to understand controllability patterns"""
    
    print("\n" + "="*70)
    print("DETAILED ZONE ANALYSIS")
    print("="*70 + "\n")
    
    # Get Hilton Pattaya zones
    zones = soundtrack_api.find_venue_zones("Hilton Pattaya")
    
    if not zones:
        print("No zones found")
        return
    
    print(f"Analyzing {len(zones)} zones in detail...\n")
    
    for i, zone in enumerate(zones, 1):
        zone_id = zone.get('id')
        zone_name = zone.get('name', 'Unknown')
        
        print(f"{i}. Zone: {zone_name}")
        print(f"   Zone ID: {zone_id}")
        print("   " + "-" * 50)
        
        # Get detailed zone status
        status = soundtrack_api.get_zone_status(zone_id)
        
        if status.get('error'):
            print(f"   ❌ Cannot get status: {status['error']}")
            continue
        
        print(f"   Name: {status.get('name')}")
        print(f"   Streaming Type: {status.get('streamingType')}")
        
        device = status.get('device', {})
        print(f"   Device: {device.get('name', 'Unknown')} (ID: {device.get('id', 'N/A')})")
        
        schedule = status.get('schedule', {})
        if schedule:
            print(f"   Schedule: {schedule.get('name', 'N/A')} (ID: {schedule.get('id', 'N/A')})")
        else:
            print("   Schedule: None (Manual mode)")
        
        now_playing = status.get('nowPlaying')
        if now_playing:
            print(f"   Now Playing: {now_playing.get('__typename', 'Unknown type')}")
        else:
            print("   Now Playing: None")
        
        # Test control capabilities
        print("   Testing capabilities:")
        
        # Test volume control
        volume_result = soundtrack_api.set_volume(zone_id, 8)
        if volume_result.get('success'):
            print("     ✅ Volume control: WORKING")
        else:
            print(f"     ❌ Volume control: FAILED - {volume_result.get('error')}")
        
        # Test playback control
        play_result = soundtrack_api.control_playback(zone_id, 'play')
        if play_result.get('success'):
            print("     ✅ Playback control: WORKING")
        else:
            print(f"     ❌ Playback control: FAILED - {play_result.get('error')}")
        
        print()
    
    print("\n" + "="*70)
    print("PATTERN ANALYSIS")
    print("="*70 + "\n")
    
    # Let's specifically test the GraphQL introspection to see available mutations
    print("Testing GraphQL schema introspection...")
    
    introspection_query = """
    query IntrospectionQuery {
        __schema {
            mutationType {
                fields {
                    name
                    description
                    args {
                        name
                        type {
                            name
                            kind
                        }
                    }
                }
            }
        }
    }
    """
    
    result = soundtrack_api._execute_query(introspection_query)
    
    if result.get('error'):
        print(f"❌ Introspection failed: {result['error']}")
    else:
        print("✅ Available mutations:")
        schema = result.get('__schema', {})
        mutation_type = schema.get('mutationType', {})
        fields = mutation_type.get('fields', [])
        
        volume_mutations = [f for f in fields if 'volume' in f.get('name', '').lower()]
        control_mutations = [f for f in fields if any(word in f.get('name', '').lower() 
                           for word in ['play', 'pause', 'skip', 'control', 'set'])]
        
        print("\n   Volume-related mutations:")
        for mutation in volume_mutations:
            print(f"     • {mutation['name']}")
            for arg in mutation.get('args', []):
                arg_type = arg.get('type', {})
                print(f"       - {arg['name']}: {arg_type.get('name', 'Unknown')}")
        
        print("\n   Control-related mutations:")
        for mutation in control_mutations[:10]:  # Show first 10
            print(f"     • {mutation['name']}")


def test_alternative_volume_methods(zone_id: str):
    """Test different ways to set volume"""
    
    print(f"\n" + "="*70)
    print(f"TESTING ALTERNATIVE VOLUME METHODS FOR ZONE")
    print("="*70 + "\n")
    
    print(f"Zone ID: {zone_id}")
    
    # Method 1: Current method (SetVolumeInput)
    print("\n1. Testing current SetVolumeInput mutation...")
    result1 = soundtrack_api.set_volume(zone_id, 8)
    print(f"   Result: {'✅ SUCCESS' if result1.get('success') else '❌ FAILED'}")
    if not result1.get('success'):
        print(f"   Error: {result1.get('error')}")
    
    # Method 2: Try different input structure
    print("\n2. Testing alternative input structure...")
    query2 = """
    mutation SetVolume($zoneId: ID!, $volume: Int!) {
        setVolume(input: {soundZoneId: $zoneId, volume: $volume}) {
            __typename
        }
    }
    """
    
    result2 = soundtrack_api._execute_query(query2, {
        'zoneId': zone_id,
        'volume': 8
    })
    
    if result2.get('error'):
        print(f"   Result: ❌ FAILED - {result2['error']}")
    else:
        print("   Result: ✅ SUCCESS")
    
    # Method 3: Try updateZone mutation if it exists
    print("\n3. Testing updateZone mutation...")
    query3 = """
    mutation UpdateZone($input: UpdateSoundZoneInput!) {
        updateSoundZone(input: $input) {
            soundZone {
                id
                name
            }
        }
    }
    """
    
    result3 = soundtrack_api._execute_query(query3, {
        'input': {
            'id': zone_id,
            'volume': 8
        }
    })
    
    if result3.get('error'):
        print(f"   Result: ❌ FAILED - {result3['error']}")
    else:
        print("   Result: ✅ SUCCESS")


if __name__ == "__main__":
    # Run detailed analysis
    analyze_zones_in_detail()
    
    # Test alternative methods on a known working zone
    working_zone_id = "U291bmRab25lLCwxaDAyZ2k3bHY1cy9Mb2NhdGlvbiwsMW9wM3prbHBjZTgvQWNjb3VudCwsMXN4N242NTZyeTgv"  # Drift Bar
    test_alternative_volume_methods(working_zone_id)
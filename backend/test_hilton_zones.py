#!/usr/bin/env python3
"""
Test Hilton Pattaya zone retrieval
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Import API
from soundtrack_api import soundtrack_api

def test_hilton_pattaya():
    """Test fetching Hilton Pattaya zones"""
    
    print("=== Testing Hilton Pattaya Zone Retrieval ===\n")
    
    # Test different variations
    test_names = [
        "Hilton Pattaya",
        "hilton pattaya",
        "Pattaya Hilton",
        "Hilton"
    ]
    
    for venue_name in test_names:
        print(f"\nSearching for: '{venue_name}'")
        zones = soundtrack_api.find_venue_zones(venue_name)
        
        if zones:
            print(f"✅ Found {len(zones)} zones:")
            for zone in zones:
                status = "🟢 Online" if zone.get('isOnline', zone.get('online')) else "🔴 Offline"
                paired = "✅ Paired" if zone.get('isPaired') else "❌ Not Paired"
                print(f"  • {zone['name']} - {status}, {paired}")
                print(f"    Location: {zone.get('location_name')}")
                print(f"    Account: {zone.get('account_name')}")
                print(f"    Zone ID: {zone['id']}")
        else:
            print(f"❌ No zones found")
    
    # Test getting now playing for Edge zone
    print("\n\n=== Testing Now Playing for Edge Zone ===\n")
    edge_zone_id = "U291bmRab25lLCwxOGZ5M2R2a2NuNC9Mb2NhdGlvbiwsMW9wM3prbHBjZTgvQWNjb3VudCwsMXN4N242NTZyeTgv"
    
    now_playing = soundtrack_api.get_now_playing(edge_zone_id)
    
    if 'error' not in now_playing:
        if now_playing and now_playing.get('track'):
            track = now_playing['track']
            artists = [a['name'] for a in track.get('artists', [])] if isinstance(track.get('artists', []), list) else []
            artist_str = ', '.join(artists) if artists else 'Unknown'
            print(f"🎵 Now Playing: {track.get('name', 'Unknown')} by {artist_str}")
            print(f"   Started at: {now_playing.get('startedAt')}")
        else:
            print("⏸️ No music currently playing")
    else:
        print(f"❌ Error: {now_playing['error']}")

if __name__ == "__main__":
    test_hilton_pattaya()
#!/usr/bin/env python3
"""
Test the bot fix to ensure track details are now working
"""

import os
import sys
import logging
from soundtrack_api import soundtrack_api
from venue_accounts import VENUE_ACCOUNTS

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_env():
    """Load environment variables from .env file"""
    try:
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value.strip('"').strip("'")
    except FileNotFoundError:
        print("No .env file found")

def test_edge_zone_status():
    """Test getting status for Edge zone"""
    print("=== Testing Edge Zone Status ===")
    
    hilton_data = VENUE_ACCOUNTS['hilton_pattaya']
    edge_zone_id = hilton_data['zones']['edge']
    
    print(f"Testing zone ID: {edge_zone_id}")
    
    # Use the updated get_zone_status method
    status = soundtrack_api.get_zone_status(edge_zone_id)
    
    print(f"Status result: {status}")
    
    if 'error' in status:
        print(f"❌ Error: {status['error']}")
        return False
    
    # Verify we have track details
    zone_name = status.get('name')
    playing = status.get('playing')
    current_track = status.get('current_track')
    playlist = status.get('current_playlist')
    
    print(f"\n🎵 Zone Status:")
    print(f"   Name: {zone_name}")
    print(f"   Playing: {playing}")
    print(f"   Device Online: {status.get('device_online')}")
    
    if current_track:
        print(f"   Current Track: {current_track.get('name')}")
        print(f"   Artist: {current_track.get('artist')}")
        print(f"   Album: {current_track.get('album')}")
    else:
        print(f"   No current track data")
    
    if playlist:
        print(f"   Playlist/Schedule: {playlist}")
    
    # Test the bot response format
    if playing and current_track:
        track_name = current_track.get('name', 'Unknown track')
        artist = current_track.get('artist', 'Unknown artist')
        
        bot_response = f'At {zone_name} in Hilton Pattaya, "{track_name}" by {artist} is currently playing'
        if playlist:
            bot_response += f' from the {playlist} playlist'
        bot_response += '.'
        
        print(f"\n🤖 Bot Response:")
        print(f"   {bot_response}")
        
        return True
    else:
        print(f"\n⚠️ No track playing or no track details")
        return False

def test_all_hilton_zones():
    """Test all Hilton zones"""
    print("\n=== Testing All Hilton Zones ===")
    
    hilton_data = VENUE_ACCOUNTS['hilton_pattaya']
    zones = hilton_data['zones']
    
    results = {}
    
    for zone_name, zone_id in zones.items():
        print(f"\n--- Testing {zone_name.title()} Zone ---")
        
        status = soundtrack_api.get_zone_status(zone_id)
        
        if 'error' in status:
            print(f"❌ {zone_name}: {status['error']}")
            results[zone_name] = 'error'
        else:
            playing = status.get('playing')
            current_track = status.get('current_track')
            
            if playing and current_track:
                track_name = current_track.get('name', 'Unknown')
                artist = current_track.get('artist', 'Unknown')
                print(f"✅ {zone_name}: Playing '{track_name}' by {artist}")
                results[zone_name] = 'playing_with_details'
            elif playing:
                print(f"⚠️ {zone_name}: Playing but no track details")
                results[zone_name] = 'playing_no_details'
            else:
                print(f"🔇 {zone_name}: Not playing")
                results[zone_name] = 'not_playing'
    
    print(f"\n📊 Summary:")
    for zone, result in results.items():
        emoji = {'playing_with_details': '✅', 'playing_no_details': '⚠️', 'not_playing': '🔇', 'error': '❌'}
        print(f"   {emoji.get(result, '?')} {zone.title()}: {result.replace('_', ' ')}")
    
    return results

def main():
    """Run bot fix test"""
    load_env()
    
    print("🔧 Testing Bot Fix")
    print("=" * 40)
    
    # Test Edge zone specifically
    edge_works = test_edge_zone_status()
    
    # Test all zones
    all_results = test_all_hilton_zones()
    
    print(f"\n" + "=" * 40)
    print("🏁 Test Results")
    
    if edge_works:
        print("✅ CRITICAL ISSUE FIXED!")
        print("   The bot can now retrieve track details from Edge zone")
    else:
        print("❌ Edge zone still not working properly")
    
    working_zones = sum(1 for result in all_results.values() if result == 'playing_with_details')
    total_zones = len(all_results)
    
    print(f"📊 Zone Status: {working_zones}/{total_zones} zones providing track details")
    
    if working_zones > 0:
        print(f"\n🎉 SUCCESS! The WhatsApp bot should now show real track names!")
        print(f"   Next: Test with actual WhatsApp message: 'What's playing at Edge?'")
    else:
        print(f"\n⚠️ No zones currently providing track details - may be normal if nothing is playing")

if __name__ == "__main__":
    main()
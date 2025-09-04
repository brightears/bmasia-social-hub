#!/usr/bin/env python3
"""
Debug script to test Soundtrack Your Brand API connection
and identify why track details are not being returned
"""

import os
import sys
import json
import logging
from soundtrack_api import soundtrack_api
from venue_accounts import VENUE_ACCOUNTS

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_basic_connection():
    """Test basic API authentication"""
    print("=== Testing Basic API Connection ===")
    
    # Check if credentials are configured
    if not soundtrack_api.session.headers.get('Authorization'):
        print("❌ No authorization header found!")
        print("Please check your environment variables:")
        print("- SOUNDTRACK_API_CREDENTIALS (preferred)")
        print("- Or SOUNDTRACK_CLIENT_ID and SOUNDTRACK_CLIENT_SECRET")
        return False
    
    print("✅ Authorization header present")
    
    # Test a simple GraphQL query
    test_query = """
    query TestConnection {
        me {
            ... on PublicAPIClient {
                id
            }
        }
    }
    """
    
    result = soundtrack_api._execute_query(test_query)
    
    if 'error' in result:
        print(f"❌ API Connection failed: {result['error']}")
        return False
    elif result.get('me'):
        print("✅ API connection successful")
        return True
    else:
        print(f"⚠️ Unexpected response: {result}")
        return False

def test_hilton_zones():
    """Test access to Hilton Pattaya zones"""
    print("\n=== Testing Hilton Pattaya Zone Access ===")
    
    hilton_data = VENUE_ACCOUNTS['hilton_pattaya']
    account_id = hilton_data['account_id']
    
    print(f"Account ID: {account_id}")
    
    # Test account access
    account_data = soundtrack_api.get_account_by_id(account_id)
    
    if not account_data:
        print("❌ Cannot access Hilton account")
        return False
    
    print(f"✅ Account found: {account_data.get('businessName')}")
    
    # List all zones
    print("\nZones found:")
    for loc_edge in account_data.get('locations', {}).get('edges', []):
        location = loc_edge['node']
        print(f"  Location: {location.get('name')}")
        for zone_edge in location.get('soundZones', {}).get('edges', []):
            zone = zone_edge['node']
            print(f"    Zone: {zone.get('name')} (ID: {zone.get('id')})")
            print(f"      Online: {zone.get('online')}")
            print(f"      Paired: {zone.get('isPaired')}")
    
    return True

def test_zone_status(zone_name='Edge'):
    """Test getting detailed zone status"""
    print(f"\n=== Testing {zone_name} Zone Status ===")
    
    # Get zone ID
    hilton_data = VENUE_ACCOUNTS['hilton_pattaya']
    zone_id = hilton_data['zones'].get(zone_name.lower())
    
    if not zone_id:
        print(f"❌ Zone ID not found for {zone_name}")
        return False
    
    print(f"Zone ID: {zone_id}")
    
    # Test the comprehensive GraphQL query
    comprehensive_query = """
    query GetZoneStatus($zoneId: ID!) {
        soundZone(id: $zoneId) {
            id
            name
            streamingType
            isPlaying
            volume
            device {
                id
                name
                online
            }
            schedule {
                id
                name
            }
            nowPlaying {
                __typename
                ... on Track {
                    id
                    name
                    artistName
                    albumName
                    duration
                }
                ... on Announcement {
                    id
                    name
                }
            }
            currentPlaylist {
                id
                name
            }
        }
    }
    """
    
    print("Testing comprehensive query...")
    result = soundtrack_api._execute_query(comprehensive_query, {'zoneId': zone_id})
    
    if 'error' in result:
        print(f"❌ Comprehensive query failed: {result['error']}")
        
        # Try basic query
        print("Trying basic query...")
        basic_query = """
        query GetZoneStatus($zoneId: ID!) {
            soundZone(id: $zoneId) {
                id
                name
                device {
                    name
                }
                nowPlaying {
                    __typename
                }
            }
        }
        """
        
        result = soundtrack_api._execute_query(basic_query, {'zoneId': zone_id})
        
        if 'error' in result:
            print(f"❌ Basic query also failed: {result['error']}")
            return False
    
    # Analyze the response
    zone_data = result.get('soundZone', {})
    
    if zone_data:
        print("✅ Zone data received:")
        print(f"  Name: {zone_data.get('name')}")
        print(f"  Streaming Type: {zone_data.get('streamingType')}")
        print(f"  Is Playing: {zone_data.get('isPlaying')}")
        print(f"  Volume: {zone_data.get('volume')}")
        
        device = zone_data.get('device', {})
        if device:
            print(f"  Device: {device.get('name')} (Online: {device.get('online')})")
        
        now_playing = zone_data.get('nowPlaying', {})
        if now_playing:
            print(f"  Now Playing Type: {now_playing.get('__typename')}")
            if now_playing.get('__typename') == 'Track':
                print(f"    Track: {now_playing.get('name', 'No name')}")
                print(f"    Artist: {now_playing.get('artistName', 'No artist')}")
                print(f"    Album: {now_playing.get('albumName', 'No album')}")
            elif now_playing.get('__typename') == 'Announcement':
                print(f"    Announcement: {now_playing.get('name', 'No name')}")
            else:
                print(f"    Unknown type: {now_playing}")
        else:
            print("  No nowPlaying data")
        
        current_playlist = zone_data.get('currentPlaylist', {})
        if current_playlist:
            print(f"  Current Playlist: {current_playlist.get('name')}")
        else:
            print("  No current playlist data")
        
        return zone_data
    else:
        print("❌ No zone data returned")
        return False

def main():
    """Run diagnostic tests"""
    print("🔍 Soundtrack API Diagnostic Tool")
    print("=" * 50)
    
    # Test 1: Basic connection
    if not test_basic_connection():
        print("\n❌ Cannot proceed - fix authentication first")
        return
    
    # Test 2: Hilton zones
    if not test_hilton_zones():
        print("\n❌ Cannot access Hilton account")
        return
    
    # Test 3: Zone status for Edge
    zone_data = test_zone_status('Edge')
    
    print("\n" + "=" * 50)
    print("🏁 Diagnostic Complete")
    
    # Summary
    print("\n📋 SUMMARY:")
    if zone_data:
        if zone_data.get('nowPlaying'):
            if zone_data['nowPlaying'].get('name'):
                print("✅ Track details ARE being returned")
            else:
                print("⚠️ nowPlaying exists but no track name")
                print(f"   Type: {zone_data['nowPlaying'].get('__typename')}")
        else:
            print("❌ No nowPlaying data returned")
            print(f"   Zone is playing: {zone_data.get('isPlaying')}")
    
    print("\nRecommendations:")
    print("1. Check if music is actually playing in the zone")
    print("2. Verify the zone has content scheduled")
    print("3. Test with a different zone")
    print("4. Check Soundtrack dashboard for comparison")

if __name__ == "__main__":
    main()
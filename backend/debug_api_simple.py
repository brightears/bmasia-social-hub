#!/usr/bin/env python3
"""
Simplified debug script focusing just on the Soundtrack API issue
"""

import os
import sys
import json
import requests
import logging
from venue_accounts import VENUE_ACCOUNTS

# Setup logging
logging.basicConfig(level=logging.DEBUG)
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

def test_api_connection():
    """Test direct API connection"""
    load_env()
    
    print("=== Testing Direct API Connection ===")
    
    # Check credentials
    api_credentials = os.getenv('SOUNDTRACK_API_CREDENTIALS')
    client_id = os.getenv('SOUNDTRACK_CLIENT_ID')
    client_secret = os.getenv('SOUNDTRACK_CLIENT_SECRET')
    
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'BMA-Social/2.0'
    }
    
    if api_credentials:
        headers['Authorization'] = f'Basic {api_credentials}'
        print("✅ Using SOUNDTRACK_API_CREDENTIALS")
    elif client_id and client_secret:
        import base64
        credentials_string = f"{client_id}:{client_secret}"
        encoded_credentials = base64.b64encode(credentials_string.encode()).decode()
        headers['Authorization'] = f'Basic {encoded_credentials}'
        print("✅ Using client_id and client_secret")
    else:
        print("❌ No credentials found")
        return False
    
    # Test connection
    base_url = 'https://api.soundtrackyourbrand.com/v2'
    
    test_query = """
    query TestConnection {
        me {
            ... on PublicAPIClient {
                id
            }
        }
    }
    """
    
    payload = {'query': test_query}
    
    try:
        response = requests.post(base_url, json=payload, headers=headers, timeout=10)
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if 'errors' in data:
                print(f"❌ GraphQL errors: {data['errors']}")
                return False
            elif data.get('data', {}).get('me'):
                print("✅ API connection successful")
                return True
            else:
                print(f"⚠️ Unexpected response: {data}")
                return False
        else:
            print(f"❌ HTTP error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

def test_zone_status():
    """Test getting zone status for Edge"""
    load_env()
    
    print("\n=== Testing Edge Zone Status ===")
    
    # Get credentials
    api_credentials = os.getenv('SOUNDTRACK_API_CREDENTIALS')
    client_id = os.getenv('SOUNDTRACK_CLIENT_ID')
    client_secret = os.getenv('SOUNDTRACK_CLIENT_SECRET')
    
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'BMA-Social/2.0'
    }
    
    if api_credentials:
        headers['Authorization'] = f'Basic {api_credentials}'
    elif client_id and client_secret:
        import base64
        credentials_string = f"{client_id}:{client_secret}"
        encoded_credentials = base64.b64encode(credentials_string.encode()).decode()
        headers['Authorization'] = f'Basic {encoded_credentials}'
    else:
        print("❌ No credentials")
        return
    
    # Get Edge zone ID
    hilton_data = VENUE_ACCOUNTS['hilton_pattaya']
    edge_zone_id = hilton_data['zones']['edge']
    
    print(f"Edge zone ID: {edge_zone_id}")
    
    # Test comprehensive query
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
    
    payload = {
        'query': comprehensive_query,
        'variables': {'zoneId': edge_zone_id}
    }
    
    base_url = 'https://api.soundtrackyourbrand.com/v2'
    
    try:
        response = requests.post(base_url, json=payload, headers=headers, timeout=10)
        print(f"Response status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ HTTP error: {response.text}")
            return
        
        data = response.json()
        print(f"Raw response: {json.dumps(data, indent=2)}")
        
        if 'errors' in data:
            print(f"❌ GraphQL errors: {data['errors']}")
            return
        
        zone_data = data.get('data', {}).get('soundZone', {})
        
        if zone_data:
            print("\n=== Zone Data Analysis ===")
            print(f"Name: {zone_data.get('name')}")
            print(f"Is Playing: {zone_data.get('isPlaying')}")
            print(f"Volume: {zone_data.get('volume')}")
            print(f"Streaming Type: {zone_data.get('streamingType')}")
            
            device = zone_data.get('device', {})
            if device:
                print(f"Device: {device.get('name')} (Online: {device.get('online')})")
            
            now_playing = zone_data.get('nowPlaying')
            if now_playing:
                print(f"Now Playing Type: {now_playing.get('__typename')}")
                if now_playing.get('__typename') == 'Track':
                    print(f"  Track Name: {now_playing.get('name')}")
                    print(f"  Artist: {now_playing.get('artistName')}")
                    print(f"  Album: {now_playing.get('albumName')}")
                    print(f"  Duration: {now_playing.get('duration')}")
                elif now_playing.get('__typename') == 'Announcement':
                    print(f"  Announcement: {now_playing.get('name')}")
            else:
                print("No nowPlaying data")
            
            playlist = zone_data.get('currentPlaylist')
            if playlist:
                print(f"Current Playlist: {playlist.get('name')}")
            else:
                print("No current playlist data")
                
        else:
            print("❌ No zone data returned")
            
    except Exception as e:
        print(f"❌ Request error: {e}")

def main():
    """Run the diagnostic"""
    print("🔍 Simple Soundtrack API Diagnostic")
    print("=" * 40)
    
    # Test 1: Connection
    if not test_api_connection():
        print("❌ Fix authentication first")
        return
    
    # Test 2: Zone status
    test_zone_status()
    
    print("\n" + "=" * 40)
    print("🏁 Diagnostic Complete")

if __name__ == "__main__":
    main()
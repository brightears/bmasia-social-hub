#!/usr/bin/env python3
"""
Test the working query with actual track details
"""

import os
import json
import requests

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

def test_full_working_query():
    """Test the complete working query with track details"""
    load_env()
    
    print("=== Testing Full Working Query ===")
    
    # Get credentials
    api_credentials = os.getenv('SOUNDTRACK_API_CREDENTIALS')
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'BMA-Social/2.0',
        'Authorization': f'Basic {api_credentials}'
    }
    
    # Edge zone ID
    edge_zone_id = 'U291bmRab25lLCwxOGZ5M2R2a2NuNC9Mb2NhdGlvbiwsMW9wM3prbHBjZTgvQWNjb3VudCwsMXN4N242NTZyeTgv'
    
    # The working query with all track details
    working_query = '''
    query GetZoneStatus($zoneId: ID!) {
        soundZone(id: $zoneId) {
            id
            name
            online
            device {
                id
                name
            }
            nowPlaying {
                __typename
                startedAt
                track {
                    id
                    name
                    title
                    durationMs
                    artists {
                        id
                        name
                    }
                    album {
                        id
                        name
                    }
                }
                playFrom {
                    __typename
                    ... on Playlist {
                        id
                        name
                    }
                    ... on Schedule {
                        id
                        name
                    }
                }
            }
            playback {
                __typename
                state
                volume {
                    level
                }
            }
        }
    }
    '''
    
    payload = {
        'query': working_query,
        'variables': {'zoneId': edge_zone_id}
    }
    
    base_url = 'https://api.soundtrackyourbrand.com/v2'
    
    try:
        response = requests.post(base_url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if 'errors' in data:
                print(f"❌ Error: {data['errors'][0].get('message')}")
                return None
            else:
                zone_data = data.get('data', {}).get('soundZone', {})
                print(f"✅ SUCCESS! Full track details retrieved!")
                
                # Extract and display the information
                print(f"\n🎵 Zone Information:")
                print(f"   Name: {zone_data.get('name')}")
                print(f"   Online: {zone_data.get('online')}")
                
                device = zone_data.get('device', {})
                if device:
                    print(f"   Device: {device.get('name')}")
                
                now_playing = zone_data.get('nowPlaying', {})
                if now_playing:
                    print(f"\n🎶 Now Playing:")
                    print(f"   Started At: {now_playing.get('startedAt')}")
                    
                    track = now_playing.get('track', {})
                    if track:
                        print(f"   Track: {track.get('name')}")
                        
                        artists = track.get('artists', [])
                        if artists:
                            artist_names = [artist.get('name', 'Unknown') for artist in artists]
                            print(f"   Artist(s): {', '.join(artist_names)}")
                        
                        album = track.get('album', {})
                        if album:
                            print(f"   Album: {album.get('name')}")
                        
                        duration = track.get('durationMs')
                        if duration:
                            minutes = duration // 60000
                            seconds = (duration % 60000) // 1000
                            print(f"   Duration: {minutes}:{seconds:02d}")
                    
                    play_from = now_playing.get('playFrom', {})
                    if play_from:
                        print(f"   Playing From: {play_from.get('name')} ({play_from.get('__typename')})")
                
                playback = zone_data.get('playback', {})
                if playback:
                    print(f"\n🎛 Playback:")
                    print(f"   State: {playback.get('state')}")
                    
                    volume = playback.get('volume', {})
                    if volume:
                        print(f"   Volume: {volume.get('level')}")
                
                print(f"\n📋 Raw Response:")
                print(json.dumps(zone_data, indent=2))
                
                return zone_data
                
        else:
            print(f"❌ HTTP error: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def main():
    print("🔍 Testing Working Query")
    print("=" * 40)
    
    result = test_full_working_query()
    
    if result:
        print("\n✅ SUCCESS! The bot can now retrieve track details!")
        print("\nNext steps:")
        print("1. Update soundtrack_api.py with the correct GraphQL query")
        print("2. Test the bot with the fixed queries")
        print("3. Verify all zones work correctly")
    else:
        print("\n❌ Still need to debug the query")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Test a simplified working query focusing on track details
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

def test_simple_working_query():
    """Test simplified working query with just track details"""
    load_env()
    
    print("=== Testing Simplified Working Query ===")
    
    # Get credentials
    api_credentials = os.getenv('SOUNDTRACK_API_CREDENTIALS')
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'BMA-Social/2.0',
        'Authorization': f'Basic {api_credentials}'
    }
    
    # Edge zone ID
    edge_zone_id = 'U291bmRab25lLCwxOGZ5M2R2a2NuNC9Mb2NhdGlvbiwsMW9wM3prbHBjZTgvQWNjb3VudCwsMXN4N242NTZyeTgv'
    
    # Simplified working query - just the essentials
    working_query = '''
    query GetZoneStatus($zoneId: ID!) {
        soundZone(id: $zoneId) {
            id
            name
            online
            device {
                name
            }
            nowPlaying {
                startedAt
                track {
                    name
                    artists {
                        name
                    }
                    album {
                        name
                    }
                }
                playFrom {
                    __typename
                    ... on Playlist {
                        name
                    }
                    ... on Schedule {
                        name
                    }
                }
            }
            playback {
                state
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
                print(f"✅ SUCCESS! Track details retrieved!")
                
                # Format like the bot would
                print(f"\n🎵 Bot Response Format:")
                zone_name = zone_data.get('name')
                online = zone_data.get('online')
                
                now_playing = zone_data.get('nowPlaying', {})
                if now_playing:
                    track = now_playing.get('track', {})
                    if track:
                        track_name = track.get('name', 'Unknown track')
                        
                        artists = track.get('artists', [])
                        artist_name = artists[0].get('name', 'Unknown artist') if artists else 'Unknown artist'
                        
                        album = track.get('album', {})
                        album_name = album.get('name', '') if album else ''
                        
                        play_from = now_playing.get('playFrom', {})
                        playlist = play_from.get('name', '') if play_from else ''
                        
                        # Bot response format
                        response = f'At {zone_name} in Hilton Pattaya, "{track_name}" by {artist_name} is currently playing'
                        if playlist:
                            response += f' from the {playlist} playlist'
                        response += '.'
                        
                        print(f"   {response}")
                        
                        if album_name:
                            print(f"   Album: {album_name}")
                        
                        playback = zone_data.get('playback', {})
                        if playback:
                            state = playback.get('state')
                            print(f"   Playback State: {state}")
                    else:
                        print(f"   Music is playing at {zone_name} but no track details available")
                else:
                    print(f"   No music playing at {zone_name}")
                
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
    print("🔍 Testing Simplified Working Query")
    print("=" * 40)
    
    result = test_simple_working_query()
    
    if result:
        print("\n🎉 CRITICAL ISSUE SOLVED!")
        print("\nThe problem was:")
        print("- The GraphQL schema changed")
        print("- Field 'isPlaying' was removed from SoundZone")
        print("- Track details are accessed via nowPlaying.track")
        print("- Artists is an array, not a single field")
        print("- Need to use 'artists[0].name' not 'artistName'")
        
        print("\nReady to fix the bot!")
    else:
        print("\n❌ Still need to debug")

if __name__ == "__main__":
    main()
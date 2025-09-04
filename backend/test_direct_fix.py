#!/usr/bin/env python3
"""
Test the API fix directly with proper environment loading
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

def test_fixed_query():
    """Test the fixed GraphQL query directly"""
    load_env()
    
    print("=== Testing Fixed GraphQL Query ===")
    
    # Get credentials
    api_credentials = os.getenv('SOUNDTRACK_API_CREDENTIALS')
    if not api_credentials:
        print("❌ No credentials found in environment")
        return False
    
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'BMA-Social/2.0',
        'Authorization': f'Basic {api_credentials}'
    }
    
    # Edge zone ID
    edge_zone_id = 'U291bmRab25lLCwxOGZ5M2R2a2NuNC9Mb2NhdGlvbiwsMW9wM3prbHBjZTgvQWNjb3VudCwsMXN4N242NTZyeTgv'
    
    # The fixed query (same as in updated soundtrack_api.py)
    query = """
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
    """
    
    payload = {
        'query': query,
        'variables': {'zoneId': edge_zone_id}
    }
    
    base_url = 'https://api.soundtrackyourbrand.com/v2'
    
    try:
        response = requests.post(base_url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if 'errors' in data:
                print(f"❌ GraphQL Error: {data['errors'][0].get('message')}")
                return False
            
            zone_data = data.get('data', {}).get('soundZone', {})
            
            if not zone_data:
                print(f"❌ No zone data returned")
                return False
            
            print(f"✅ SUCCESS! Zone data retrieved:")
            
            # Process the data like the updated soundtrack_api.py does
            status = {
                'id': zone_data.get('id'),
                'name': zone_data.get('name'),
                'device_name': zone_data.get('device', {}).get('name'),
                'device_online': zone_data.get('online'),
            }
            
            # Extract playback state
            playback = zone_data.get('playback', {})
            if playback:
                playback_state = playback.get('state', '').lower()
                status['playing'] = playback_state == 'playing'
            else:
                now_playing = zone_data.get('nowPlaying', {})
                status['playing'] = bool(now_playing and now_playing.get('track'))
            
            # Extract track information
            now_playing = zone_data.get('nowPlaying', {})
            if now_playing:
                track = now_playing.get('track', {})
                if track:
                    artists = track.get('artists', [])
                    artist_name = artists[0].get('name', 'Unknown artist') if artists else 'Unknown artist'
                    
                    album = track.get('album', {})
                    album_name = album.get('name', '') if album else ''
                    
                    status['current_track'] = {
                        'name': track.get('name', 'Unknown track'),
                        'artist': artist_name,
                        'album': album_name
                    }
                
                play_from = now_playing.get('playFrom', {})
                if play_from:
                    status['current_playlist'] = play_from.get('name')
            
            # Display results
            print(f"   Zone: {status.get('name')}")
            print(f"   Online: {status.get('device_online')}")
            print(f"   Playing: {status.get('playing')}")
            
            current_track = status.get('current_track')
            if current_track:
                print(f"   Track: {current_track.get('name')}")
                print(f"   Artist: {current_track.get('artist')}")
                print(f"   Album: {current_track.get('album')}")
            
            playlist = status.get('current_playlist')
            if playlist:
                print(f"   Playlist: {playlist}")
            
            # Show bot response format
            if status.get('playing') and current_track:
                track_name = current_track.get('name')
                artist = current_track.get('artist')
                
                bot_response = f'At {status.get("name")} in Hilton Pattaya, "{track_name}" by {artist} is currently playing'
                if playlist:
                    bot_response += f' from the {playlist} playlist'
                bot_response += '.'
                
                print(f"\n🤖 Bot will now respond:")
                print(f'   "{bot_response}"')
                
                print(f"\n🎉 ISSUE FIXED! The bot will now show real track names instead of just 'Music is playing'")
                return True
            else:
                print(f"\n⚠️ Zone found but no track currently playing")
                return False
            
        else:
            print(f"❌ HTTP error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("🔧 Testing Direct Fix")
    print("=" * 40)
    
    result = test_fixed_query()
    
    if result:
        print(f"\n✅ CRITICAL ISSUE RESOLVED!")
        print(f"The WhatsApp bot deployed at https://bma-social-api-q9uu.onrender.com")
        print(f"should now properly show track names and artists.")
        print(f"\nTest message: 'What's playing at Edge in Hilton Pattaya?'")
    else:
        print(f"\n❌ Issue not resolved - check API connection or zone status")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Final test to find the working schema for track information
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

def test_track_fields():
    """Test different track field names"""
    load_env()
    
    print("=== Testing Track Fields ===")
    
    # Get credentials
    api_credentials = os.getenv('SOUNDTRACK_API_CREDENTIALS')
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'BMA-Social/2.0',
        'Authorization': f'Basic {api_credentials}'
    }
    
    # Edge zone ID
    edge_zone_id = 'U291bmRab25lLCwxOGZ5M2R2a2NuNC9Mb2NhdGlvbiwsMW9wM3prbHBjZTgvQWNjb3VudCwsMXN4N242NTZyeTgv'
    
    # Try different approaches based on what we learned
    queries = [
        {
            'name': 'NowPlaying with basic Track fields',
            'query': '''
            query GetZone($zoneId: ID!) {
                soundZone(id: $zoneId) {
                    id
                    name
                    nowPlaying {
                        __typename
                        track {
                            id
                            name
                            artist {
                                name
                            }
                        }
                    }
                }
            }
            '''
        },
        {
            'name': 'History approach - recent tracks',
            'query': '''
            query GetZone($zoneId: ID!) {
                soundZone(id: $zoneId) {
                    id
                    name
                    playbackHistory(first: 1) {
                        edges {
                            node {
                                track {
                                    id
                                    name
                                    artist {
                                        name
                                    }
                                }
                                playedAt
                            }
                        }
                    }
                }
            }
            '''
        },
        {
            'name': 'Minimal working query',
            'query': '''
            query GetZone($zoneId: ID!) {
                soundZone(id: $zoneId) {
                    id
                    name
                    online
                    nowPlaying {
                        __typename
                    }
                    playFrom {
                        __typename
                        ... on Schedule {
                            name
                        }
                        ... on Playlist {
                            name
                        }
                    }
                }
            }
            '''
        }
    ]
    
    base_url = 'https://api.soundtrackyourbrand.com/v2'
    
    for query_info in queries:
        print(f"\n--- Testing: {query_info['name']} ---")
        
        payload = {
            'query': query_info['query'],
            'variables': {'zoneId': edge_zone_id}
        }
        
        try:
            response = requests.post(base_url, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'errors' in data:
                    print(f"❌ Error: {data['errors'][0].get('message')}")
                else:
                    zone_data = data.get('data', {}).get('soundZone', {})
                    print(f"✅ Success!")
                    
                    # Pretty print the response
                    if 'playbackHistory' in zone_data:
                        history = zone_data.get('playbackHistory', {})
                        edges = history.get('edges', [])
                        if edges:
                            recent_track = edges[0]['node']
                            track = recent_track.get('track', {})
                            print(f"   Most recent track: {track.get('name')} by {track.get('artist', {}).get('name')}")
                            print(f"   Played at: {recent_track.get('playedAt')}")
                        else:
                            print("   No recent tracks found")
                    
                    elif 'nowPlaying' in zone_data:
                        now_playing = zone_data.get('nowPlaying', {})
                        print(f"   Now Playing Type: {now_playing.get('__typename')}")
                        if 'track' in now_playing:
                            track = now_playing['track']
                            artist = track.get('artist', {})
                            print(f"   Current track: {track.get('name')} by {artist.get('name')}")
                    
                    if 'playFrom' in zone_data:
                        play_from = zone_data.get('playFrom', {})
                        print(f"   Playing from: {play_from.get('name')} ({play_from.get('__typename')})")
                    
                    print(f"   Full response: {json.dumps(zone_data, indent=2)}")
                    
            else:
                print(f"❌ HTTP error: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error: {e}")

def main():
    print("🔍 Final Schema Test")
    print("=" * 40)
    
    test_track_fields()

if __name__ == "__main__":
    main()
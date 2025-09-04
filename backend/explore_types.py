#!/usr/bin/env python3
"""
Explore the NowPlaying and Playback types to understand structure
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

def explore_fields():
    """Try different field combinations to discover the structure"""
    load_env()
    
    print("=== Exploring Field Structure ===")
    
    # Get credentials
    api_credentials = os.getenv('SOUNDTRACK_API_CREDENTIALS')
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'BMA-Social/2.0',
        'Authorization': f'Basic {api_credentials}'
    }
    
    # Edge zone ID
    edge_zone_id = 'U291bmRab25lLCwxOGZ5M2R2a2NuNC9Mb2NhdGlvbiwsMW9wM3prbHBjZTgvQWNjb3VudCwsMXN4N242NTZyeTgv'
    
    # Try different field combinations
    queries = [
        {
            'name': 'NowPlaying with common fields',
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
                            artistName
                        }
                    }
                }
            }
            '''
        },
        {
            'name': 'Playback with common fields', 
            'query': '''
            query GetZone($zoneId: ID!) {
                soundZone(id: $zoneId) {
                    id
                    name
                    playback {
                        __typename
                        isPlaying
                        track {
                            id
                            name
                            artistName
                        }
                    }
                }
            }
            '''
        },
        {
            'name': 'Status with fields',
            'query': '''
            query GetZone($zoneId: ID!) {
                soundZone(id: $zoneId) {
                    id
                    name
                    status {
                        playing
                        paused
                    }
                }
            }
            '''
        },
        {
            'name': 'Try playFrom field',
            'query': '''
            query GetZone($zoneId: ID!) {
                soundZone(id: $zoneId) {
                    id
                    name
                    playFrom {
                        __typename
                        ... on Playlist {
                            id
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
                    print(f"   Response: {json.dumps(zone_data, indent=2)}")
            else:
                print(f"❌ HTTP error: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error: {e}")

def try_working_query():
    """Test a query that should work based on what we learned"""
    load_env()
    
    print("\n=== Testing Working Query ===")
    
    # Get credentials
    api_credentials = os.getenv('SOUNDTRACK_API_CREDENTIALS')
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'BMA-Social/2.0',
        'Authorization': f'Basic {api_credentials}'
    }
    
    # Edge zone ID
    edge_zone_id = 'U291bmRab25lLCwxOGZ5M2R2a2NuNC9Mb2NhdGlvbiwsMW9wM3prbHBjZTgvQWNjb3VudCwsMXN4N242NTZyeTgv'
    
    # Based on discovery, this should be our working query
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
            playback {
                track {
                    id
                    name
                    artistName
                    albumName
                }
                isPlaying
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
            else:
                zone_data = data.get('data', {}).get('soundZone', {})
                print(f"✅ Final Working Query Success!")
                print(f"Zone: {zone_data.get('name')}")
                print(f"Online: {zone_data.get('online')}")
                
                playback = zone_data.get('playback', {})
                if playback:
                    track = playback.get('track', {})
                    if track:
                        print(f"Currently Playing: {track.get('name')} by {track.get('artistName')}")
                        print(f"Is Playing: {playback.get('isPlaying')}")
                    else:
                        print(f"No track data in playback")
                        print(f"Playback data: {playback}")
                else:
                    print("No playback data")
                
                play_from = zone_data.get('playFrom')
                if play_from:
                    print(f"Playing from: {play_from.get('name')} ({play_from.get('__typename')})")
                
        else:
            print(f"❌ HTTP error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    print("🔍 Exploring GraphQL Types")
    print("=" * 40)
    
    explore_fields()
    try_working_query()

if __name__ == "__main__":
    main()
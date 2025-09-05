#!/usr/bin/env python3
"""
Test script to discover the correct Soundtrack Your Brand GraphQL schema
"""

import os
import requests
import json
import base64

def test_syb_api():
    """Test the Soundtrack API to discover correct schema"""
    
    # Get credentials from environment
    api_credentials = os.getenv('SOUNDTRACK_API_CREDENTIALS')
    if not api_credentials:
        print("ERROR: SOUNDTRACK_API_CREDENTIALS not found in environment")
        return
    
    base_url = 'https://api.soundtrackyourbrand.com/v2'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Basic {api_credentials}',
        'User-Agent': 'BMA-Social/2.0'
    }
    
    print(f"Testing Soundtrack API at {base_url}")
    print(f"Using credentials: {api_credentials[:10]}...")
    
    # Test 1: Introspection query to get schema
    print("\n=== TEST 1: Schema Introspection ===")
    introspection_query = """
    query IntrospectionQuery {
      __schema {
        types {
          name
          kind
          fields {
            name
            type {
              name
              kind
            }
          }
        }
      }
    }
    """
    
    try:
        response = requests.post(base_url, 
                               json={'query': introspection_query}, 
                               headers=headers, 
                               timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if 'errors' in data:
                print(f"Errors: {data['errors']}")
            else:
                # Find SoundZone type
                types = data.get('data', {}).get('__schema', {}).get('types', [])
                for type_def in types:
                    if type_def.get('name') == 'SoundZone':
                        print("Found SoundZone type:")
                        fields = type_def.get('fields', [])
                        for field in fields:
                            field_name = field.get('name')
                            field_type = field.get('type', {}).get('name', 'Unknown')
                            print(f"  - {field_name}: {field_type}")
                        break
        else:
            print(f"HTTP Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 2: Get accounts to find our known Hilton Pattaya account
    print("\n=== TEST 2: Get Account ===")
    account_query = """
    query GetAccount($id: ID!) {
      account(id: $id) {
        id
        businessName
        locations(first: 10) {
          edges {
            node {
              id
              name
              soundZones(first: 10) {
                edges {
                  node {
                    id
                    name
                    isPaired
                    volume
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    
    hilton_account_id = "QWNjb3VudCwsMXN4N242NTZyeTgv"
    
    try:
        response = requests.post(base_url, 
                               json={'query': account_query, 'variables': {'id': hilton_account_id}}, 
                               headers=headers, 
                               timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if 'errors' in data:
                print(f"Errors: {data['errors']}")
            else:
                account = data.get('data', {}).get('account')
                if account:
                    print(f"Account: {account.get('businessName')}")
                    for loc_edge in account.get('locations', {}).get('edges', []):
                        location = loc_edge['node']
                        print(f"  Location: {location.get('name')}")
                        for zone_edge in location.get('soundZones', {}).get('edges', []):
                            zone = zone_edge['node']
                            print(f"    Zone: {zone.get('name')} (ID: {zone.get('id')}) - Paired: {zone.get('isPaired')}, Volume: {zone.get('volume')}")
                else:
                    print("No account data found")
        else:
            print(f"HTTP Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 3: Test specific zone status with known Edge zone ID
    print("\n=== TEST 3: Zone Status ===")
    edge_zone_id = "U291bmRab25lLCwxOGZ5M2R2a2NuNC9Mb2NhdGlvbiwsMW9wM3prbHBjZTgvQWNjb3VudCwsMXN4N242NTZyeTgv"
    
    zone_query = """
    query GetZoneStatus($zoneId: ID!) {
      soundZone(id: $zoneId) {
        id
        name
        isPaired
        volume
        nowPlaying {
          track {
            name
            artists {
              name
            }
            album {
              name
            }
          }
        }
      }
    }
    """
    
    try:
        response = requests.post(base_url, 
                               json={'query': zone_query, 'variables': {'zoneId': edge_zone_id}}, 
                               headers=headers, 
                               timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if 'errors' in data:
                print(f"Errors: {data['errors']}")
            else:
                zone = data.get('data', {}).get('soundZone')
                if zone:
                    print(f"Zone: {zone.get('name')}")
                    print(f"  ID: {zone.get('id')}")
                    print(f"  Paired: {zone.get('isPaired')}")
                    print(f"  Volume: {zone.get('volume')}")
                    
                    now_playing = zone.get('nowPlaying')
                    if now_playing:
                        track = now_playing.get('track')
                        if track:
                            artists = track.get('artists', [])
                            artist_names = [a.get('name') for a in artists]
                            print(f"  Now Playing: {track.get('name')} by {', '.join(artist_names)}")
                            if track.get('album'):
                                print(f"    Album: {track.get('album', {}).get('name')}")
                        else:
                            print("  Now Playing: No track info")
                    else:
                        print("  Now Playing: None")
                else:
                    print("No zone data found")
        else:
            print(f"HTTP Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 4: Test volume control
    print("\n=== TEST 4: Volume Control ===")
    volume_mutation = """
    mutation SetVolume($input: SetVolumeInput!) {
      setVolume(input: $input) {
        soundZone {
          id
          name
          volume
        }
      }
    }
    """
    
    try:
        response = requests.post(base_url, 
                               json={
                                   'query': volume_mutation, 
                                   'variables': {
                                       'input': {
                                           'soundZone': edge_zone_id,
                                           'volume': 8
                                       }
                                   }
                               }, 
                               headers=headers, 
                               timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if 'errors' in data:
                print(f"Errors: {data['errors']}")
            else:
                result = data.get('data', {}).get('setVolume')
                if result:
                    zone = result.get('soundZone', {})
                    print(f"Volume set successfully: {zone.get('name')} -> {zone.get('volume')}")
                else:
                    print("Volume mutation returned no data")
        else:
            print(f"HTTP Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_syb_api()
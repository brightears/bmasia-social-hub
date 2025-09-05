#!/usr/bin/env python3
"""
Test script with corrected schema based on introspection results
"""

import os
import requests
import json

def test_corrected_schema():
    """Test with the correct GraphQL schema"""
    
    api_credentials = os.getenv('SOUNDTRACK_API_CREDENTIALS')
    base_url = 'https://api.soundtrackyourbrand.com/v2'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Basic {api_credentials}',
        'User-Agent': 'BMA-Social/2.0'
    }
    
    print("=== Testing CORRECTED Soundtrack API Schema ===")
    
    # Test 1: Get account WITHOUT volume field
    print("\n=== TEST 1: Get Account (Corrected) ===")
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
                    online
                    streamingType
                    nowPlaying {
                      track {
                        name
                        artists {
                          name
                        }
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
                    playback {
                      state
                    }
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
                            print(f"    Zone: {zone.get('name')}")
                            print(f"      ID: {zone.get('id')}")
                            print(f"      Paired: {zone.get('isPaired')}")
                            print(f"      Online: {zone.get('online')}")
                            print(f"      StreamingType: {zone.get('streamingType')}")
                            
                            # Check playback
                            playback = zone.get('playback')
                            if playback:
                                print(f"      Playback State: {playback.get('state')}")
                            
                            # Check now playing
                            now_playing = zone.get('nowPlaying')
                            if now_playing and now_playing.get('track'):
                                track = now_playing['track']
                                artists = track.get('artists', [])
                                artist_names = [a.get('name') for a in artists]
                                print(f"      Now Playing: {track.get('name')} by {', '.join(artist_names)}")
                            
                            # Check play source
                            play_from = zone.get('playFrom')
                            if play_from:
                                print(f"      Playing From: {play_from.get('__typename')} - {play_from.get('name')}")
                else:
                    print("No account data found")
        else:
            print(f"HTTP Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 2: Check if volume is available in device or settings
    print("\n=== TEST 2: Check Device/Settings for Volume ===")
    edge_zone_id = "U291bmRab25lLCwxOGZ5M2R2a2NuNC9Mb2NhdGlvbiwsMW9wM3prbHBjZTgvQWNjb3VudCwsMXN4N242NTZyeTgv"
    
    detailed_query = """
    query GetDetailedZone($zoneId: ID!) {
      soundZone(id: $zoneId) {
        id
        name
        device {
          id
          name
          volume
        }
        settings {
          volume
        }
      }
    }
    """
    
    try:
        response = requests.post(base_url, 
                               json={'query': detailed_query, 'variables': {'zoneId': edge_zone_id}}, 
                               headers=headers, 
                               timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if 'errors' in data:
                print(f"Errors: {data['errors']}")
                # Try alternative
                alt_query = """
                query GetAltZone($zoneId: ID!) {
                  soundZone(id: $zoneId) {
                    id
                    name
                    device {
                      id
                      name
                    }
                  }
                }
                """
                print("Trying alternative query...")
                response2 = requests.post(base_url, 
                                        json={'query': alt_query, 'variables': {'zoneId': edge_zone_id}}, 
                                        headers=headers, 
                                        timeout=10)
                if response2.status_code == 200:
                    data2 = response2.json()
                    print(f"Alt query result: {data2}")
            else:
                zone = data.get('data', {}).get('soundZone')
                if zone:
                    print(f"Zone: {zone}")
        else:
            print(f"HTTP Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 3: Corrected Volume Control Mutation
    print("\n=== TEST 3: Corrected Volume Control ===")
    volume_mutation = """
    mutation SetVolume($input: SetVolumeInput!) {
      setVolume(input: $input) {
        __typename
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
        print(f"Response: {response.text}")
        if response.status_code == 200:
            data = response.json()
            if 'errors' in data:
                print(f"Errors: {data['errors']}")
            else:
                result = data.get('data', {}).get('setVolume')
                print(f"Volume mutation result: {result}")
        else:
            print(f"HTTP Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_corrected_schema()
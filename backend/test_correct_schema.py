#!/usr/bin/env python3
"""
Test the correct GraphQL schema based on discovery
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

def test_correct_query():
    """Test with the correct schema"""
    load_env()
    
    print("=== Testing Correct Schema ===")
    
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
            'name': 'NowPlaying only',
            'query': '''
            query GetZone($zoneId: ID!) {
                soundZone(id: $zoneId) {
                    id
                    name
                    nowPlaying {
                        __typename
                        ... on Track {
                            id
                            name
                            artistName
                            albumName
                        }
                    }
                }
            }
            '''
        },
        {
            'name': 'Playback field',
            'query': '''
            query GetZone($zoneId: ID!) {
                soundZone(id: $zoneId) {
                    id
                    name
                    playback {
                        __typename
                    }
                }
            }
            '''
        },
        {
            'name': 'Status field',
            'query': '''
            query GetZone($zoneId: ID!) {
                soundZone(id: $zoneId) {
                    id
                    name
                    status
                }
            }
            '''
        },
        {
            'name': 'Online field',
            'query': '''
            query GetZone($zoneId: ID!) {
                soundZone(id: $zoneId) {
                    id
                    name
                    online
                }
            }
            '''
        },
        {
            'name': 'Combined approach',
            'query': '''
            query GetZone($zoneId: ID!) {
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
                    }
                    playback {
                        __typename
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
                    print(f"   Raw data: {json.dumps(zone_data, indent=2)}")
            else:
                print(f"❌ HTTP error: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error: {e}")

def inspect_nowplaying_type():
    """Try to understand the NowPlaying type structure"""
    load_env()
    
    print("\n=== Inspecting NowPlaying Type ===")
    
    # Get credentials
    api_credentials = os.getenv('SOUNDTRACK_API_CREDENTIALS')
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'BMA-Social/2.0',
        'Authorization': f'Basic {api_credentials}'
    }
    
    # Try to introspect NowPlaying type
    introspection_query = """
    query IntrospectNowPlaying {
        __schema {
            types {
                name
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
    
    payload = {'query': introspection_query}
    base_url = 'https://api.soundtrackyourbrand.com/v2'
    
    try:
        response = requests.post(base_url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if 'data' in data:
                schema = data.get('data', {}).get('__schema', {})
                types = schema.get('types', [])
                
                for type_info in types:
                    type_name = type_info.get('name', '')
                    if 'nowplaying' in type_name.lower() or 'playing' in type_name.lower() or 'playback' in type_name.lower() or 'track' in type_name.lower():
                        print(f"\n🔍 {type_name} fields:")
                        for field in type_info.get('fields', []):
                            field_name = field.get('name')
                            field_type = field.get('type', {}).get('name', 'Unknown')
                            print(f"  - {field_name}: {field_type}")
                            
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    print("🔍 Testing Correct GraphQL Schema")
    print("=" * 40)
    
    test_correct_query()
    inspect_nowplaying_type()

if __name__ == "__main__":
    main()
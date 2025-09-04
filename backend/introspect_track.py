#!/usr/bin/env python3
"""
Introspect Track type to find actual field names
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

def find_track_fields():
    """Search for all Track-related types and their fields"""
    load_env()
    
    print("=== Finding Track Fields ===")
    
    # Get credentials
    api_credentials = os.getenv('SOUNDTRACK_API_CREDENTIALS')
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'BMA-Social/2.0',
        'Authorization': f'Basic {api_credentials}'
    }
    
    # Full schema introspection
    introspection_query = """
    query IntrospectSchema {
        __schema {
            types {
                name
                kind
                fields {
                    name
                    type {
                        name
                        kind
                        ofType {
                            name
                            kind
                        }
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
                
                # Find all types related to track/music
                track_related_types = []
                for type_info in types:
                    type_name = type_info.get('name', '').lower()
                    if any(keyword in type_name for keyword in ['track', 'song', 'music', 'nowplaying', 'playback']):
                        track_related_types.append(type_info)
                
                print(f"Found {len(track_related_types)} track-related types:")
                
                for type_info in track_related_types:
                    type_name = type_info.get('name', '')
                    print(f"\n🎵 {type_name} ({type_info.get('kind', 'unknown')})")
                    
                    fields = type_info.get('fields', [])
                    if fields:
                        for field in fields:
                            field_name = field.get('name')
                            field_type = field.get('type', {})
                            
                            # Get readable type name
                            type_name_str = field_type.get('name', '')
                            if not type_name_str:
                                of_type = field_type.get('ofType', {})
                                type_name_str = of_type.get('name', 'Unknown')
                            
                            print(f"  • {field_name}: {type_name_str}")
                    else:
                        print(f"  (No fields - likely interface/union)")
                        
                # Also look for Artist type specifically
                print(f"\n🎤 Looking for Artist type...")
                for type_info in types:
                    if type_info.get('name') == 'Artist':
                        print(f"Artist fields:")
                        for field in type_info.get('fields', []):
                            print(f"  • {field.get('name')}: {field.get('type', {}).get('name', 'Unknown')}")
                        
            else:
                print(f"❌ No schema data")
                
    except Exception as e:
        print(f"❌ Error: {e}")

def test_direct_track_access():
    """Try to access track data more directly"""
    load_env()
    
    print("\n=== Testing Direct Track Access ===")
    
    # Get credentials
    api_credentials = os.getenv('SOUNDTRACK_API_CREDENTIALS')
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'BMA-Social/2.0',
        'Authorization': f'Basic {api_credentials}'
    }
    
    # Edge zone ID
    edge_zone_id = 'U291bmRab25lLCwxOGZ5M2R2a2NuNC9Mb2NhdGlvbiwsMW9wM3prbHBjZTgvQWNjb3VudCwsMXN4N242NTZyeTgv'
    
    # Try with minimal fields that might work
    test_queries = [
        {
            'name': 'Just track name',
            'query': '''
            query GetZone($zoneId: ID!) {
                soundZone(id: $zoneId) {
                    nowPlaying {
                        track {
                            name
                        }
                    }
                }
            }
            '''
        },
        {
            'name': 'Track with title field',
            'query': '''
            query GetZone($zoneId: ID!) {
                soundZone(id: $zoneId) {
                    nowPlaying {
                        track {
                            title
                        }
                    }
                }
            }
            '''
        },
        {
            'name': 'Track without nested fields',
            'query': '''
            query GetZone($zoneId: ID!) {
                soundZone(id: $zoneId) {
                    nowPlaying {
                        __typename
                        id
                    }
                }
            }
            '''
        }
    ]
    
    base_url = 'https://api.soundtrackyourbrand.com/v2'
    
    for query_info in test_queries:
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
                    print(f"✅ Success!")
                    print(f"   Response: {json.dumps(data, indent=2)}")
                    
            else:
                print(f"❌ HTTP error: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error: {e}")

def main():
    print("🔍 Track Introspection")
    print("=" * 40)
    
    find_track_fields()
    test_direct_track_access()

if __name__ == "__main__":
    main()
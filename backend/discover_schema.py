#!/usr/bin/env python3
"""
Discover the current GraphQL schema for SoundZone
"""

import os
import sys
import json
import requests
import logging

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

def discover_soundzone_schema():
    """Try to introspect the SoundZone schema"""
    load_env()
    
    print("=== Discovering SoundZone Schema ===")
    
    # Get credentials
    api_credentials = os.getenv('SOUNDTRACK_API_CREDENTIALS')
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'BMA-Social/2.0'
    }
    
    if api_credentials:
        headers['Authorization'] = f'Basic {api_credentials}'
    else:
        print("❌ No credentials")
        return
    
    # Introspection query
    introspection_query = """
    query IntrospectSoundZone {
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
            
            if 'errors' in data:
                print(f"❌ Introspection not allowed: {data['errors']}")
                return
            
            # Find SoundZone type
            schema = data.get('data', {}).get('__schema', {})
            types = schema.get('types', [])
            
            soundzone_type = None
            for type_info in types:
                if type_info.get('name') == 'SoundZone':
                    soundzone_type = type_info
                    break
            
            if soundzone_type:
                print("✅ SoundZone fields found:")
                for field in soundzone_type.get('fields', []):
                    field_name = field.get('name')
                    field_type = field.get('type', {}).get('name', 'Unknown')
                    print(f"  - {field_name}: {field_type}")
            else:
                print("❌ SoundZone type not found")
                
        else:
            print(f"❌ HTTP error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def test_minimal_query():
    """Test with minimal fields to see what works"""
    load_env()
    
    print("\n=== Testing Minimal Query ===")
    
    # Get credentials
    api_credentials = os.getenv('SOUNDTRACK_API_CREDENTIALS')
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'BMA-Social/2.0',
        'Authorization': f'Basic {api_credentials}'
    }
    
    # Edge zone ID
    edge_zone_id = 'U291bmRab25lLCwxOGZ5M2R2a2NuNC9Mb2NhdGlvbiwsMW9wM3prbHBjZTgvQWNjb3VudCwsMXN4N242NTZyeTgv'
    
    # Try progressively more fields
    queries = [
        {
            'name': 'Just ID and name',
            'query': '''
            query GetZone($zoneId: ID!) {
                soundZone(id: $zoneId) {
                    id
                    name
                }
            }
            '''
        },
        {
            'name': 'Add device info',
            'query': '''
            query GetZone($zoneId: ID!) {
                soundZone(id: $zoneId) {
                    id
                    name
                    device {
                        id
                        name
                    }
                }
            }
            '''
        },
        {
            'name': 'Add nowPlaying',
            'query': '''
            query GetZone($zoneId: ID!) {
                soundZone(id: $zoneId) {
                    id
                    name
                    device {
                        id
                        name
                    }
                    nowPlaying {
                        __typename
                    }
                }
            }
            '''
        },
        {
            'name': 'Full nowPlaying with Track details',
            'query': '''
            query GetZone($zoneId: ID!) {
                soundZone(id: $zoneId) {
                    id
                    name
                    device {
                        id
                        name
                    }
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
                    print(f"   Zone: {zone_data.get('name')}")
                    
                    device = zone_data.get('device')
                    if device:
                        print(f"   Device: {device.get('name')}")
                    
                    now_playing = zone_data.get('nowPlaying')
                    if now_playing:
                        print(f"   Now Playing: {now_playing.get('__typename')}")
                        if now_playing.get('name'):
                            print(f"   Track: {now_playing.get('name')}")
                            print(f"   Artist: {now_playing.get('artistName')}")
            else:
                print(f"❌ HTTP error: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error: {e}")

def main():
    print("🔍 GraphQL Schema Discovery")
    print("=" * 40)
    
    # Try introspection first
    discover_soundzone_schema()
    
    # Test queries
    test_minimal_query()

if __name__ == "__main__":
    main()
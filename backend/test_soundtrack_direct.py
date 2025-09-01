#!/usr/bin/env python3
"""
Direct test of Soundtrack API with Hilton Pattaya account ID
"""

import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get credentials
api_credentials = os.getenv('SOUNDTRACK_API_CREDENTIALS')
client_id = os.getenv('SOUNDTRACK_CLIENT_ID')
client_secret = os.getenv('SOUNDTRACK_CLIENT_SECRET')

print(f"API Credentials present: {bool(api_credentials)}")
print(f"Client ID: {client_id}")
print(f"Client Secret: {client_secret[:10]}..." if client_secret else "None")

# Soundtrack API endpoint
url = "https://api.soundtrackyourbrand.com/v2"

# Test 1: Get account info for Hilton Pattaya
account_id = "QWNjb3VudCwsMXN4N242NTZyeTgv"

query = """
query GetAccount($id: ID!) {
    account(id: $id) {
        id
        businessName
        locations(first: 50) {
            edges {
                node {
                    id
                    name
                    soundZones(first: 50) {
                        edges {
                            node {
                                id
                                name
                                isPaired
                                online
                            }
                        }
                    }
                }
            }
        }
    }
}
"""

headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}

# Try with Basic auth
auth = None
if api_credentials:
    headers['Authorization'] = f'Basic {api_credentials}'
elif client_id and client_secret:
    from requests.auth import HTTPBasicAuth
    auth = HTTPBasicAuth(client_id, client_secret)
else:
    print("No authentication credentials available!")

payload = {
    'query': query,
    'variables': {'id': account_id}
}

print(f"\n🚀 Testing Soundtrack API...")
print(f"URL: {url}")
print(f"Account ID: {account_id}")

try:
    if auth:
        response = requests.post(url, json=payload, headers=headers, auth=auth)
    else:
        response = requests.post(url, json=payload, headers=headers)
    
    print(f"\n📡 Response Status: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Response Data:")
        print(json.dumps(data, indent=2))
        
        # Parse zones if available
        if 'data' in data and data['data'] and 'account' in data['data']:
            account = data['data']['account']
            print(f"\n🏨 Account: {account.get('businessName', 'Unknown')}")
            
            locations = account.get('locations', {}).get('edges', [])
            total_zones = 0
            
            for loc_edge in locations:
                location = loc_edge['node']
                print(f"\n📍 Location: {location.get('name')}")
                
                zones = location.get('soundZones', {}).get('edges', [])
                total_zones += len(zones)
                
                for zone_edge in zones:
                    zone = zone_edge['node']
                    status = "🟢 Online" if zone.get('online') else "🔴 Offline"
                    paired = "✅ Paired" if zone.get('isPaired') else "❌ Not Paired"
                    
                    print(f"    • {zone['name']}")
                    print(f"      Status: {status}, {paired}")
                    print(f"      ID: {zone['id']}")
            
            print(f"\n🎵 Total zones across all locations: {total_zones}")
    else:
        print(f"\n❌ Error Response:")
        print(response.text)
        
except Exception as e:
    print(f"\n❌ Exception: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Try alternative query structure
print("\n\n=== Testing Alternative Query Structure ===")

alt_query = """
query {
    me {
        ... on PublicAPIClient {
            accounts(first: 10) {
                edges {
                    node {
                        id
                        businessName
                    }
                }
            }
        }
    }
}
"""

payload2 = {'query': alt_query}

try:
    if auth:
        response2 = requests.post(url, json=payload2, headers=headers, auth=auth)
    else:
        response2 = requests.post(url, json=payload2, headers=headers)
    
    print(f"\n📡 Response Status: {response2.status_code}")
    
    if response2.status_code == 200:
        data2 = response2.json()
        print(f"\n✅ Accounts Found:")
        print(json.dumps(data2, indent=2))
    else:
        print(f"\n❌ Error: {response2.text}")
        
except Exception as e:
    print(f"\n❌ Exception: {e}")
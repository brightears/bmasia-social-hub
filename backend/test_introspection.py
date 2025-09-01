#!/usr/bin/env python3
"""
Test GraphQL introspection to understand the API schema
"""

import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get credentials
api_credentials = os.getenv('SOUNDTRACK_API_CREDENTIALS')

print(f"API Credentials present: {bool(api_credentials)}")

# Soundtrack API endpoint
url = "https://api.soundtrackyourbrand.com/v2"

headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'Authorization': f'Basic {api_credentials}'
}

# Test 1: Basic account query
account_id = "QWNjb3VudCwsMXN4N242NTZyeTgv"

basic_query = """
query GetAccount($id: ID!) {
    account(id: $id) {
        id
        businessName
    }
}
"""

payload = {
    'query': basic_query,
    'variables': {'id': account_id}
}

print(f"\n🚀 Testing basic account query...")
print(f"Account ID: {account_id}")

try:
    response = requests.post(url, json=payload, headers=headers)
    
    print(f"\n📡 Response Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Response Data:")
        print(json.dumps(data, indent=2))
    else:
        print(f"\n❌ Error Response:")
        print(response.text)
        
except Exception as e:
    print(f"\n❌ Exception: {e}")

# Test 2: Introspection query for SoundZone type
introspection_query = """
query {
    __type(name: "SoundZone") {
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
"""

print("\n\n=== Testing Introspection for SoundZone Type ===")

payload2 = {'query': introspection_query}

try:
    response2 = requests.post(url, json=payload2, headers=headers)
    
    print(f"\n📡 Response Status: {response2.status_code}")
    
    if response2.status_code == 200:
        data2 = response2.json()
        print(f"\n✅ SoundZone Fields:")
        if data2.get('data') and data2['data'].get('__type'):
            fields = data2['data']['__type']['fields']
            for field in fields:
                print(f"  • {field['name']}: {field['type']['name'] or field['type']['kind']}")
        else:
            print(json.dumps(data2, indent=2))
    else:
        print(f"\n❌ Error: {response2.text}")
        
except Exception as e:
    print(f"\n❌ Exception: {e}")

# Test 3: Check NowPlaying type
nowplaying_query = """
query {
    __type(name: "NowPlaying") {
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
"""

print("\n\n=== Testing Introspection for NowPlaying Type ===")

payload3 = {'query': nowplaying_query}

try:
    response3 = requests.post(url, json=payload3, headers=headers)
    
    print(f"\n📡 Response Status: {response3.status_code}")
    
    if response3.status_code == 200:
        data3 = response3.json()
        print(f"\n✅ NowPlaying Fields:")
        if data3.get('data') and data3['data'].get('__type'):
            fields = data3['data']['__type']['fields']
            for field in fields:
                print(f"  • {field['name']}: {field['type']['name'] or field['type']['kind']}")
        else:
            print(json.dumps(data3, indent=2))
    else:
        print(f"\n❌ Error: {response3.text}")
        
except Exception as e:
    print(f"\n❌ Exception: {e}")
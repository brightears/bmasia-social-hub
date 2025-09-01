#!/usr/bin/env python3
"""
Test Playback type introspection
"""

import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get credentials
api_credentials = os.getenv('SOUNDTRACK_API_CREDENTIALS')

url = "https://api.soundtrackyourbrand.com/v2"

headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'Authorization': f'Basic {api_credentials}'
}

# Check Playback type
playback_query = """
query {
    __type(name: "Playback") {
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

print("=== Testing Introspection for Playback Type ===")

payload = {'query': playback_query}

try:
    response = requests.post(url, json=payload, headers=headers)
    
    print(f"\n📡 Response Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Playback Fields:")
        if data.get('data') and data['data'].get('__type'):
            fields = data['data']['__type']['fields']
            for field in fields:
                print(f"  • {field['name']}: {field['type']['name'] or field['type']['kind']}")
        else:
            print(json.dumps(data, indent=2))
    else:
        print(f"\n❌ Error: {response.text}")
        
except Exception as e:
    print(f"\n❌ Exception: {e}")
#!/usr/bin/env python3
"""
Test Soundtrack API authentication
"""

import requests
import json

# The credentials from .env
SOUNDTRACK_API_CREDENTIALS = "YVhId2UyTWJVWEhMRWlycUFPaUl3Y2NtOXNGeUoxR0Q6SVRHazZSWDVYV2FTenhiS1ZwNE1sSmhHUUJEVVRDdDZGU0FwVjZqMXNEQU1EMjRBT2pub2hmZ3NQODRRNndQWg=="

url = "https://api.soundtrackyourbrand.com/v2"

# Test query to get accounts
query = """
query GetAccounts {
    me {
        ... on PublicAPIClient {
            id
            accounts(first: 5) {
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

headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Basic {SOUNDTRACK_API_CREDENTIALS}'
}

payload = {
    'query': query,
    'variables': {}
}

print("Testing Soundtrack API authentication...")
print(f"URL: {url}")
print(f"Auth header present: {'Authorization' in headers}")

response = requests.post(url, json=payload, headers=headers)

print(f"Response status: {response.status_code}")
print(f"Response: {response.text[:500]}")

if response.status_code == 200:
    data = response.json()
    if 'errors' in data:
        print("GraphQL errors:", data['errors'])
    else:
        print("Success! Data:", json.dumps(data, indent=2))
else:
    print(f"HTTP Error: {response.status_code}")
    print(f"Response: {response.text}")
#!/usr/bin/env python3
"""
Test different Soundtrack API credentials
"""

import os
import sys
import json
import base64
import requests

def test_credentials(credentials_b64, description):
    """Test a specific set of base64-encoded credentials"""
    
    print(f"=== Testing {description} ===")
    
    url = 'https://api.soundtrackyourbrand.com/v2'
    
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'BMA-Social/2.0',
        'Authorization': f'Basic {credentials_b64}'
    }
    
    # Simple test query
    test_query = """
    query TestConnection {
        viewer {
            id
            name
            email
        }
    }
    """
    
    try:
        print(f"Making request to: {url}")
        response = requests.post(
            url,
            json={'query': test_query},
            headers=headers,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
            
            if 'errors' in data:
                print(f"❌ GraphQL Errors: {data['errors']}")
                return False
            else:
                print("✅ Authentication successful!")
                return True
        else:
            print(f"❌ HTTP Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False

def main():
    # Test credentials from .env
    api_credentials = 'YVhId2UyTWJVWEhMRWlycUFPaUl3Y2NtOXNGeUoxR0Q6SVRHazZSWDVYV2FTenhiS1ZwNE1sSmhHUUJEVVRDdDZGU0FwVjZqMXNEQU1EMjRBT2pub2hmZ3NQODRRNndQWg=='
    client_id = 'VCZz6nGt0pkQ1fBsHuO8cqgR6Ctefv7f'
    client_secret = 'Ht4g6isxxrNXeYgxNkDyfM0TJe508kqJHPdFVihi9KYbOnmfO8v2PipFUCf69zmc'
    
    # Test 1: Pre-encoded credentials from SOUNDTRACK_API_CREDENTIALS
    success1 = test_credentials(api_credentials, "SOUNDTRACK_API_CREDENTIALS")
    
    # Test 2: Manual encoding of CLIENT_ID:CLIENT_SECRET  
    manual_credentials = base64.b64encode(f'{client_id}:{client_secret}'.encode()).decode()
    success2 = test_credentials(manual_credentials, "SOUNDTRACK_CLIENT_ID:SOUNDTRACK_CLIENT_SECRET")
    
    print(f"\n=== SUMMARY ===")
    print(f"SOUNDTRACK_API_CREDENTIALS: {'✅ WORKING' if success1 else '❌ FAILED'}")
    print(f"CLIENT_ID:CLIENT_SECRET: {'✅ WORKING' if success2 else '❌ FAILED'}")
    
    if success1:
        print(f"\n✅ Use SOUNDTRACK_API_CREDENTIALS for production")
        print(f"Decoded value: {base64.b64decode(api_credentials).decode()}")
    elif success2:
        print(f"\n✅ Use CLIENT_ID:CLIENT_SECRET encoding for production") 
        print(f"Encoded value: {manual_credentials}")
    else:
        print(f"\n❌ Neither credential set works - need to check with Soundtrack API provider")
        
    return success1 or success2

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
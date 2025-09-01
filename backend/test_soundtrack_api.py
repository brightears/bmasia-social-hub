#!/usr/bin/env python3
"""
Test Soundtrack Your Brand API integration
Tests authentication and basic queries
"""

import os
import sys
import json
import logging
import requests
from soundtrack_api import soundtrack_api

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_api_connection():
    """Test basic API connection and credentials"""
    
    print("=== Soundtrack API Connection Test ===\n")
    
    # Check environment variables
    print("1. Checking environment variables:")
    base_url = os.getenv('SOUNDTRACK_BASE_URL')
    api_credentials = os.getenv('SOUNDTRACK_API_CREDENTIALS')
    client_id = os.getenv('SOUNDTRACK_CLIENT_ID')
    client_secret = os.getenv('SOUNDTRACK_CLIENT_SECRET')
    
    print(f"   SOUNDTRACK_BASE_URL: {base_url or 'Not set'}")
    print(f"   SOUNDTRACK_API_CREDENTIALS: {'Set' if api_credentials else 'Not set'}")
    print(f"   SOUNDTRACK_CLIENT_ID: {'Set' if client_id else 'Not set'}")
    print(f"   SOUNDTRACK_CLIENT_SECRET: {'Set' if client_secret else 'Not set'}")
    print()
    
    if not (api_credentials or (client_id and client_secret)):
        print("❌ ERROR: No API credentials found!")
        return False
    
    # Test direct API call
    print("2. Testing direct API connection:")
    
    url = base_url or 'https://api.soundtrackyourbrand.com/v2'
    
    # Prepare headers
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'BMA-Social/2.0'
    }
    
    if api_credentials:
        headers['Authorization'] = f'Basic {api_credentials}'
    elif client_id and client_secret:
        import base64
        credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        headers['Authorization'] = f'Basic {credentials}'
    
    # Test query - get accounts
    test_query = """
    query TestConnection {
        me {
            ... on PublicAPIClient {
                id
                accounts(first: 1) {
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
    
    try:
        print(f"   Making request to: {url}")
        response = requests.post(
            url,
            json={'query': test_query},
            headers=headers,
            timeout=10
        )
        
        print(f"   Status Code: {response.status_code}")
        print(f"   Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Response: {json.dumps(data, indent=2)}")
            
            if 'errors' in data:
                print(f"   ❌ GraphQL Errors: {data['errors']}")
                return False
            else:
                print("   ✅ API connection successful!")
                return True
        else:
            print(f"   ❌ HTTP Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        return False

def test_accounts_query():
    """Test the accounts query used by the bot"""
    
    print("\n3. Testing accounts query:")
    
    try:
        accounts = soundtrack_api.get_accounts()
        print(f"   Found {len(accounts)} accounts:")
        
        for i, account in enumerate(accounts[:3]):  # Show first 3
            print(f"   {i+1}. {account.get('name')} (ID: {account.get('id')})")
            
            # Count locations and zones
            locations = account.get('locations', {}).get('edges', [])
            total_zones = 0
            online_zones = 0
            
            for loc_edge in locations:
                location = loc_edge['node']
                zones = location.get('soundZones', {}).get('edges', [])
                total_zones += len(zones)
                
                for zone_edge in zones:
                    zone = zone_edge['node']
                    if zone.get('isOnline'):
                        online_zones += 1
                
                print(f"      Location: {location.get('name')} ({len(zones)} zones)")
            
            print(f"      Total zones: {total_zones} ({online_zones} online)")
        
        return len(accounts) > 0
        
    except Exception as e:
        print(f"   ❌ Accounts query failed: {e}")
        return False

def test_venue_search():
    """Test searching for specific venues"""
    
    print("\n4. Testing venue search:")
    
    test_venues = [
        "Millennium Hilton Bangkok",
        "Hilton Bangkok", 
        "Millennium",
        "Hilton"
    ]
    
    for venue in test_venues:
        try:
            print(f"\n   Searching for: '{venue}'")
            matches = soundtrack_api.find_matching_accounts(venue)
            
            if matches:
                print(f"   ✅ Found {len(matches)} matches:")
                for match in matches[:2]:  # Show top 2
                    print(f"      • {match['account_name']} (score: {match['match_score']})")
                    print(f"        {match['total_zones']} zones, {match['online_zones']} online")
            else:
                print(f"   ❌ No matches found")
                
        except Exception as e:
            print(f"   ❌ Search failed: {e}")

def main():
    """Run all tests"""
    
    print("Starting Soundtrack API integration tests...\n")
    
    # Test 1: Basic connection
    if not test_api_connection():
        print("\n❌ Basic API connection failed - stopping tests")
        return False
    
    # Test 2: Accounts query
    if not test_accounts_query():
        print("\n❌ Accounts query failed - stopping tests")
        return False
    
    # Test 3: Venue search
    test_venue_search()
    
    print("\n✅ All tests completed!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
#!/usr/bin/env python3
"""
Simple test to check the current Soundtrack API setup and discover issues
"""

import sys
import os

# Add current directory to path
sys.path.append('/Users/benorbe/Documents/BMAsia Social Hub/backend')

try:
    from soundtrack_api import soundtrack_api
    from venue_accounts import get_zone_id
    
    print("=== Testing Current Soundtrack API Setup ===")
    print(f"API Base URL: {soundtrack_api.base_url}")
    print(f"Authentication configured: {'Yes' if 'Authorization' in soundtrack_api.session.headers else 'No'}")
    
    # Test 1: Get zone status for Edge at Hilton Pattaya
    print("\n=== TEST 1: Zone Status for Edge ===")
    edge_zone_id = get_zone_id("Hilton Pattaya", "edge")
    print(f"Edge Zone ID: {edge_zone_id}")
    
    if edge_zone_id:
        status = soundtrack_api.get_zone_status(edge_zone_id)
        print(f"Zone Status: {status}")
    
    # Test 2: Simple volume query to see what fields are actually available
    print("\n=== TEST 2: Direct Volume Query ===")
    
    # Try a simple query to see what works
    simple_query = """
    query GetSimpleZone($zoneId: ID!) {
      soundZone(id: $zoneId) {
        id
        name
        volume
        isPaired
      }
    }
    """
    
    if edge_zone_id:
        result = soundtrack_api._execute_query(simple_query, {'zoneId': edge_zone_id})
        print(f"Simple Query Result: {result}")
    
    # Test 3: Check account access
    print("\n=== TEST 3: Account Access ===")
    hilton_account_id = "QWNjb3VudCwsMXN4N242NTZyeTgv"
    account = soundtrack_api.get_account_by_id(hilton_account_id)
    if account:
        print(f"Account found: {account.get('businessName')}")
        locations = account.get('locations', {}).get('edges', [])
        print(f"Number of locations: {len(locations)}")
        for loc_edge in locations:
            location = loc_edge['node']
            zones = location.get('soundZones', {}).get('edges', [])
            print(f"  Location: {location.get('name')} - {len(zones)} zones")
            for zone_edge in zones:
                zone = zone_edge['node']
                print(f"    Zone: {zone.get('name')} - ID: {zone.get('id')} - Paired: {zone.get('isPaired')}")
    else:
        print("No account data retrieved")
    
except ImportError as e:
    print(f"Import error: {e}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
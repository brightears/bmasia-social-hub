#!/usr/bin/env python3
"""
Test Soundtrack bot integration
Tests the bot's ability to handle Soundtrack-related queries
"""

import os
import sys
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_bot_integration():
    """Test the bot integration with Soundtrack API"""
    
    print("=== Bot Soundtrack Integration Test ===\n")
    
    # Test importing the bot
    print("1. Testing bot import:")
    try:
        from bot_soundtrack import soundtrack_bot
        print("   ✅ Soundtrack bot imported successfully")
    except ImportError as e:
        print(f"   ❌ Failed to import soundtrack bot: {e}")
        return False
    
    # Test basic functionality
    print("\n2. Testing basic bot functionality:")
    try:
        test_message = "Hello, I need help with music"
        test_phone = "+6012345678"
        test_name = "Test User"
        
        response = soundtrack_bot.process_message(test_message, test_phone, test_name)
        print(f"   ✅ Bot response generated: {response[:100]}...")
    except Exception as e:
        print(f"   ❌ Bot processing failed: {e}")
        return False
    
    # Test Soundtrack-specific queries
    print("\n3. Testing Soundtrack-specific queries:")
    
    test_queries = [
        ("I am from Millennium Hilton Bangkok, can you check our zones?", "Venue introduction with zone query"),
        ("What zones are active?", "Zone status query"),
        ("Music stopped playing in lobby", "Music issue report"),
        ("Can you check our zone status?", "Direct zone check")
    ]
    
    for query, description in test_queries:
        try:
            print(f"\n   Testing: {description}")
            print(f"   Query: '{query}'")
            
            response = soundtrack_bot.process_message(query, test_phone, test_name)
            print(f"   Response (first 150 chars): {response[:150]}...")
            
            # Check if response indicates API connection issues
            if "trouble connecting" in response.lower():
                print("   ⚠️ API connection issue detected")
            elif "couldn't find" in response.lower():
                print("   ⚠️ No venue found (expected if credentials not configured)")
            elif "zones" in response.lower():
                print("   ✅ Zone-related response generated")
            else:
                print("   ✅ Response generated")
                
        except Exception as e:
            print(f"   ❌ Query failed: {e}")
    
    return True

def test_soundtrack_api_direct():
    """Test the Soundtrack API directly"""
    
    print("\n4. Testing Soundtrack API directly:")
    
    try:
        from soundtrack_api import soundtrack_api
        
        # Test basic connection
        print("   Testing account retrieval...")
        accounts = soundtrack_api.get_accounts()
        
        if isinstance(accounts, list):
            print(f"   ✅ Retrieved {len(accounts)} accounts")
            
            # Show first few account names (without sensitive data)
            for i, account in enumerate(accounts[:3]):
                name = account.get('name', 'Unknown')
                account_id = account.get('id', 'Unknown')[:8] + "..."  # First 8 chars only
                print(f"      {i+1}. {name} (ID: {account_id})")
        else:
            print(f"   ❌ API call returned: {accounts}")
            
    except Exception as e:
        print(f"   ❌ Direct API test failed: {e}")

def main():
    """Run all tests"""
    
    print("Starting Soundtrack bot integration tests...\n")
    
    # Check environment
    print("Environment check:")
    print(f"   SOUNDTRACK_BASE_URL: {os.getenv('SOUNDTRACK_BASE_URL', 'Not set')}")
    print(f"   API credentials configured: {'Yes' if os.getenv('SOUNDTRACK_API_CREDENTIALS') or os.getenv('SOUNDTRACK_CLIENT_ID') else 'No'}")
    print()
    
    # Run bot integration test
    if not test_bot_integration():
        print("\n❌ Bot integration test failed")
        return False
    
    # Test direct API if possible
    test_soundtrack_api_direct()
    
    print("\n✅ All tests completed!")
    print("\nNote: If API credentials are not configured, you may see 'connection issues' messages.")
    print("This is expected and the bot will handle it gracefully.")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
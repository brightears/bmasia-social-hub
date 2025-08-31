#!/usr/bin/env python3
"""
Debug script to test Soundtrack bot module loading and API connectivity
Run this to identify exactly what's failing
"""

import os
import sys
import logging
from typing import Dict, Any

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_imports():
    """Test all imports step by step"""
    print("=== TESTING IMPORTS ===")
    
    # Test 1: Basic imports
    try:
        import bot_simple
        print("✅ bot_simple imported successfully")
    except Exception as e:
        print(f"❌ bot_simple import failed: {e}")
        return False
    
    # Test 2: Soundtrack API
    try:
        import soundtrack_api
        print("✅ soundtrack_api imported successfully")
    except Exception as e:
        print(f"❌ soundtrack_api import failed: {e}")
        return False
    
    # Test 3: Bot integrated (parent class)
    try:
        import bot_integrated
        print("✅ bot_integrated imported successfully")
    except Exception as e:
        print(f"❌ bot_integrated import failed: {e}")
        return False
    
    # Test 4: Bot soundtrack
    try:
        import bot_soundtrack
        print("✅ bot_soundtrack imported successfully")
        
        # Test instance creation
        from bot_soundtrack import soundtrack_bot
        print(f"✅ soundtrack_bot instance created: {type(soundtrack_bot)}")
        
    except Exception as e:
        print(f"❌ bot_soundtrack import/creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def test_soundtrack_credentials():
    """Test Soundtrack API credentials"""
    print("\n=== TESTING SOUNDTRACK CREDENTIALS ===")
    
    required_vars = [
        'SOUNDTRACK_API_CREDENTIALS',
        'SOUNDTRACK_CLIENT_ID', 
        'SOUNDTRACK_CLIENT_SECRET'
    ]
    
    found_credentials = False
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {'*' * min(len(value), 10)}...")
            found_credentials = True
        else:
            print(f"❌ {var}: Not set")
    
    if not found_credentials:
        print("⚠️ No Soundtrack credentials found. API will not work.")
        return False
    
    return True

def test_soundtrack_api():
    """Test Soundtrack API connectivity"""
    print("\n=== TESTING SOUNDTRACK API ===")
    
    try:
        from soundtrack_api import soundtrack_api
        
        # Test API initialization
        print(f"✅ SoundtrackAPI initialized: {type(soundtrack_api)}")
        
        # Test a simple API call
        print("Testing API call...")
        accounts = soundtrack_api.get_accounts()
        
        if isinstance(accounts, list):
            print(f"✅ API call successful. Found {len(accounts)} accounts")
            return True
        else:
            print(f"❌ API call returned unexpected type: {type(accounts)}")
            return False
            
    except Exception as e:
        print(f"❌ Soundtrack API test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_trust_manager():
    """Test trust manager calls"""
    print("\n=== TESTING TRUST MANAGER ===")
    
    try:
        from smart_authentication import trust_manager
        print("✅ trust_manager imported successfully")
        
        # Test the method signature that's failing
        test_phone = "+1234567890"
        test_venue_id = "test_venue"
        
        # This is the call that should work
        result = trust_manager.is_trusted(test_phone, test_venue_id)
        print(f"✅ trust_manager.is_trusted(phone, venue_id) works: {result}")
        
        return True
        
    except Exception as e:
        print(f"❌ Trust manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_webhooks_import():
    """Test webhooks import chain"""
    print("\n=== TESTING WEBHOOKS IMPORT CHAIN ===")
    
    try:
        from webhooks_simple import BOT_ENABLED, bot, sender
        print(f"✅ Webhooks imported. BOT_ENABLED: {BOT_ENABLED}")
        
        if bot:
            print(f"✅ Bot loaded: {type(bot)}")
        else:
            print("❌ Bot is None")
            
        if sender:
            print(f"✅ Sender loaded: {type(sender)}")
        else:
            print("❌ Sender is None")
        
        return BOT_ENABLED
        
    except Exception as e:
        print(f"❌ Webhooks import test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("🔍 BMA Soundtrack Bot Diagnostic Tool")
    print("=" * 50)
    
    # Test each component
    import_ok = test_imports()
    creds_ok = test_soundtrack_credentials()
    api_ok = test_soundtrack_api() if creds_ok else False
    trust_ok = test_trust_manager()
    webhook_ok = test_webhooks_import()
    
    print("\n" + "=" * 50)
    print("📊 DIAGNOSTIC SUMMARY:")
    print(f"Imports: {'✅' if import_ok else '❌'}")
    print(f"Credentials: {'✅' if creds_ok else '❌'}")
    print(f"API Connectivity: {'✅' if api_ok else '❌'}")
    print(f"Trust Manager: {'✅' if trust_ok else '❌'}")
    print(f"Webhook Integration: {'✅' if webhook_ok else '❌'}")
    
    if all([import_ok, creds_ok, api_ok, trust_ok, webhook_ok]):
        print("\n🎉 All tests passed! Soundtrack bot should be working.")
        return 0
    else:
        print("\n⚠️ Some tests failed. Check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
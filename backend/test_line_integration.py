#!/usr/bin/env python3
"""
Test script for Line integration
Verifies that both WhatsApp and Line webhooks work properly
"""

import requests
import json
import os
from datetime import datetime

# Base URL for testing
BASE_URL = "http://localhost:8000"  # Change this to your deployed URL when testing

def test_webhook_diagnostics():
    """Test webhook diagnostics endpoint"""
    print("🔍 Testing webhook diagnostics...")

    try:
        response = requests.get(f"{BASE_URL}/webhook-test")
        if response.status_code == 200:
            data = response.json()
            print("✅ Webhook diagnostics endpoint working")
            print(f"   WhatsApp configured: {data.get('configuration', {}).get('whatsapp_configured')}")
            print(f"   Line configured: {data.get('configuration', {}).get('line_configured')}")
            print(f"   Bot initialized: {data.get('configuration', {}).get('bot_initialized')}")
            return True
        else:
            print(f"❌ Webhook diagnostics failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error testing diagnostics: {e}")
        return False

def test_whatsapp_webhook_structure():
    """Test that WhatsApp webhook endpoint still exists and handles GET requests"""
    print("\n🔍 Testing WhatsApp webhook structure...")

    try:
        # Test GET request (webhook verification)
        params = {
            "hub.mode": "subscribe",
            "hub.verify_token": "bma_whatsapp_verify_2024",
            "hub.challenge": "test_challenge_123"
        }
        response = requests.get(f"{BASE_URL}/webhooks/whatsapp", params=params)

        if response.status_code == 200 and response.text == "test_challenge_123":
            print("✅ WhatsApp webhook verification working")
            return True
        else:
            print(f"❌ WhatsApp webhook verification failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error testing WhatsApp webhook: {e}")
        return False

def test_line_webhook_structure():
    """Test that Line webhook endpoint exists and handles POST requests"""
    print("\n🔍 Testing Line webhook structure...")

    try:
        # Test POST request with empty events (should fail due to missing signature)
        test_payload = {
            "destination": "test",
            "events": []
        }

        response = requests.post(
            f"{BASE_URL}/webhooks/line",
            json=test_payload,
            headers={"Content-Type": "application/json"}
        )

        # Should return 400 due to missing signature (which is correct behavior)
        if response.status_code == 400:
            print("✅ Line webhook endpoint exists and validates signatures")
            return True
        else:
            print(f"❌ Line webhook unexpected response: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error testing Line webhook: {e}")
        return False

def test_bot_message_api():
    """Test that the bot message API still works"""
    print("\n🔍 Testing bot message API...")

    try:
        test_message = {
            "message": "Hello, this is a test message",
            "user_phone": "+1234567890",
            "user_name": "Test User"
        }

        response = requests.post(
            f"{BASE_URL}/api/v1/bot/message",
            json=test_message,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                print("✅ Bot message API working")
                print(f"   Response: {data.get('response', '')[:100]}...")
                return True
            else:
                print(f"❌ Bot message API returned error: {data.get('error')}")
                return False
        else:
            print(f"❌ Bot message API failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error testing bot message API: {e}")
        return False

def run_integration_tests():
    """Run all integration tests"""
    print("🚀 Running Line Integration Tests")
    print("=" * 50)

    tests = [
        test_webhook_diagnostics,
        test_whatsapp_webhook_structure,
        test_line_webhook_structure,
        test_bot_message_api
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            failed += 1

    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All tests passed! Line integration is working correctly.")
        print("\nNext steps:")
        print("1. Configure Line webhook URL in Line Developer Console")
        print("2. Test with real Line messages")
        print("3. Verify Google Chat integration works with both platforms")
    else:
        print("⚠️  Some tests failed. Check the errors above.")

    return failed == 0

if __name__ == "__main__":
    success = run_integration_tests()
    exit(0 if success else 1)
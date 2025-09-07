#!/usr/bin/env python3
"""
Simple test to check if Google Chat webhook is configured
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_webhook():
    # Check for webhook URL
    webhook_url = os.getenv('GOOGLE_CHAT_WEBHOOK_URL', '')
    
    if not webhook_url:
        print("❌ GOOGLE_CHAT_WEBHOOK_URL not found in .env")
        print("\nTo fix this:")
        print("1. Go to Google Chat > BMAsia Working Group")
        print("2. Click space name > Manage webhooks")
        print("3. Find 'BMA Social Support Bot' and copy its URL")
        print("4. Add to .env: GOOGLE_CHAT_WEBHOOK_URL='<the-url>'")
        return False
    
    print(f"✅ Found webhook URL: {webhook_url[:50]}...")
    
    # Try to send a test message
    try:
        response = requests.post(
            webhook_url,
            json={"text": "🧪 Test message from BMA Social Bot - Google Chat is connected!"},
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            print("✅ Test message sent successfully!")
            print("Check your Google Chat space for the message.")
            return True
        else:
            print(f"❌ Failed to send: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("Testing Google Chat Webhook Connection")
    print("=" * 40)
    test_webhook()
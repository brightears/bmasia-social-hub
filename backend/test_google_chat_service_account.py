#!/usr/bin/env python3
"""
Test Google Chat connection using Service Account credentials
"""

import os
import json
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_google_chat():
    print("🔍 Testing Google Chat Service Account Connection")
    print("=" * 50)
    
    # Check for credentials
    creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON', '')
    
    if not creds_json:
        print("❌ GOOGLE_CREDENTIALS_JSON not found in .env")
        return False
    
    try:
        creds = json.loads(creds_json)
        print(f"✅ Found service account: {creds.get('client_email', 'unknown')}")
        print(f"   Project: {creds.get('project_id', 'unknown')}")
    except Exception as e:
        print(f"❌ Failed to parse credentials: {e}")
        return False
    
    # Check for space ID
    space_id = os.getenv('GCHAT_BMASIA_ALL_SPACE', '')
    if not space_id:
        print("❌ GCHAT_BMASIA_ALL_SPACE not found in .env")
        return False
    
    print(f"✅ Found space ID: {space_id}")
    
    # Try to initialize the Google Chat client
    try:
        from google_chat_client import GoogleChatClient
        
        client = GoogleChatClient()
        print("✅ Google Chat client initialized successfully")
        
        # Try to send a test notification
        print("\n📤 Sending test notification to Google Chat...")
        
        from google_chat_client import Department, Priority
        
        success = client.send_notification(
            message="🎉 Google Chat connection test successful! Service account credentials are working properly.",
            venue_name="Test Venue",
            department=Department.OPERATIONS,
            priority=Priority.INFO,
            context="Testing Google Chat integration after setting up new service account credentials"
        )
        
        if success:
            print("✅ Test notification sent successfully!")
            print("   Check the 'BMAsia Working Group' space for the message")
            return True
        else:
            print("❌ Failed to send test notification")
            return False
            
    except ImportError as e:
        print(f"❌ Failed to import Google Chat client: {e}")
        print("   Make sure google_chat_client.py is in the same directory")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_google_chat())
#!/usr/bin/env python3
"""
Test Google Chat notifications for BMA Social bot
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Test bot's notification system
def test_bot_notifications():
    """Test the bot's ability to send notifications"""
    from bot_fresh_start import bot
    
    print("🧪 Testing Bot Notification System...")
    print("-" * 50)
    
    # Test scenarios
    test_cases = [
        {
            'name': 'Playlist Change Request',
            'venue': 'Hilton Pattaya',
            'issue': 'Customer wants to play smooth jazz at Edge bar',
            'phone': '+66891234567'
        },
        {
            'name': 'Technical Issue',
            'venue': 'Hilton Pattaya',
            'issue': 'Zone offline - Edge bar has no music playing',
            'phone': '+66897654321'
        },
        {
            'name': 'Complex Design Request',
            'venue': 'Hilton Pattaya',
            'issue': 'Customer wants custom playlist for wedding event',
            'phone': '+66895555555'
        }
    ]
    
    success_count = 0
    
    for test in test_cases:
        print(f"\n📧 Test: {test['name']}")
        print(f"   Venue: {test['venue']}")
        print(f"   Issue: {test['issue']}")
        
        try:
            result = bot.send_support_notification(
                venue_name=test['venue'],
                issue=test['issue'],
                phone=test['phone']
            )
            
            if result:
                print(f"   ✅ SUCCESS - Notification sent!")
                success_count += 1
            else:
                print(f"   ❌ FAILED - Notification not sent")
                print(f"      Check that GOOGLE_CREDENTIALS_JSON is set in .env")
                print(f"      Check that GCHAT_BMASIA_ALL_SPACE is set in .env")
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Results: {success_count}/{len(test_cases)} notifications sent successfully")
    
    if success_count == 0:
        print("\n⚠️  No notifications were sent. Please check:")
        print("1. GOOGLE_CREDENTIALS_JSON is properly set in .env")
        print("2. GCHAT_BMASIA_ALL_SPACE contains the correct space ID")
        print("3. The service account has permission to post to the space")
        print("\nTo find your space ID:")
        print("1. Open Google Chat")
        print("2. Click on the space (BMAsia All)")
        print("3. Click the space name at the top")
        print("4. Look for 'Space ID' in the details")
    elif success_count < len(test_cases):
        print("\n⚠️  Some notifications failed. Check the error messages above.")
    else:
        print("\n🎉 All notifications sent successfully!")
        print("Check the Google Chat 'BMAsia All' space for the test messages.")

def test_direct_message():
    """Test sending a direct WhatsApp-style message to the bot"""
    from bot_fresh_start import handle_whatsapp_message
    
    print("\n\n🤖 Testing Bot Message Processing...")
    print("-" * 50)
    
    test_messages = [
        "I want to play chillhop at Edge",
        "Can you change the music to jazz at Drift Bar?",
        "The music is too loud at Horizon",
        "What's playing at Shore right now?"
    ]
    
    for msg in test_messages:
        print(f"\n📱 User: {msg}")
        response = handle_whatsapp_message(msg, "+66891234567")
        print(f"🤖 Bot: {response[:200]}..." if len(response) > 200 else f"🤖 Bot: {response}")

if __name__ == "__main__":
    print("🎯 BMA Social Bot Notification Test")
    print("=" * 50)
    
    # Check if Google credentials exist
    if not os.getenv('GOOGLE_CREDENTIALS_JSON'):
        print("⚠️  WARNING: GOOGLE_CREDENTIALS_JSON not found in .env")
        print("Notifications will not work without proper credentials.")
        print("\nTo set up Google Chat:")
        print("1. Create a service account in Google Cloud Console")
        print("2. Enable Google Chat API")
        print("3. Add the service account to your Google Chat space")
        print("4. Copy the JSON credentials to GOOGLE_CREDENTIALS_JSON in .env")
    
    if not os.getenv('GCHAT_BMASIA_ALL_SPACE'):
        print("⚠️  WARNING: GCHAT_BMASIA_ALL_SPACE not found in .env")
        print("Please set the Google Chat space ID in your .env file")
    
    print("\nStarting tests...\n")
    
    # Run notification tests
    test_bot_notifications()
    
    # Run message processing tests
    test_direct_message()
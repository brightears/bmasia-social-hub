#!/usr/bin/env python3
"""
Test Google Chat integration
First enable the Google Chat API and configure the bot
"""

import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv()

print("=" * 60)
print("Google Chat Integration Test")
print("=" * 60)
print()

# Check if Chat API is available
try:
    from google_chat_client import chat_client, Department, Priority, escalate_to_chat, should_escalate
    
    print("✅ Google Chat client imported successfully")
    print()
    
    # Check if space is configured
    if not chat_client.BMASIA_ALL_SPACE:
        print("❌ No Google Chat space configured")
        print()
        print("To set up Google Chat:")
        print()
        print("1. Enable Google Chat API in Google Cloud Console:")
        print("   https://console.cloud.google.com/apis/library/chat.googleapis.com")
        print()
        print("2. Create a Chat bot in Google Cloud Console:")
        print("   - Go to Google Chat API settings")
        print("   - Click 'Configuration'")
        print("   - Set bot name: 'BMA Social Support Bot'")
        print("   - Set description: 'Automated support notifications'")
        print("   - Add bot to your BMAsia All space")
        print()
        print("3. Get the space ID:")
        print("   - In Google Chat, go to your BMAsia All space")
        print("   - Click on the space name -> 'View space details'")
        print("   - Copy the space ID (looks like: spaces/AAAAxxxxxxx)")
        print()
        print("4. Add to your .env file:")
        print("   GCHAT_BMASIA_ALL_SPACE=spaces/YOUR_SPACE_ID")
        print()
        sys.exit(1)
    
    print(f"📍 Space configured: {chat_client.BMASIA_ALL_SPACE}")
    
    if chat_client.service:
        print("✅ Google Chat API connected")
        
        if chat_client.space_verified:
            print("✅ Space access verified")
            print()
            
            # Test message analysis
            print("Testing message categorization...")
            print("-" * 40)
            
            test_messages = [
                ("All zones are offline at Hilton Pattaya!", "Hilton Pattaya"),
                ("We want to discuss contract renewal", "Marriott Bangkok"),
                ("The playlist needs updating", "Centara Grand"),
                ("Payment is overdue for last month", "Novotel"),
                ("This is urgent - customer very unhappy!", "Holiday Inn"),
            ]
            
            for msg, venue in test_messages:
                dept, priority = chat_client.analyze_message(msg, venue)
                print(f"Message: '{msg[:40]}...'")
                print(f"  → {dept.value} | {priority.value} Priority")
                print()
            
            # Ask if user wants to send a test message
            print("-" * 40)
            print("Would you like to send a test notification?")
            print("This will post to your BMAsia All Google Chat space.")
            print()
            response = input("Send test? (yes/no): ").lower().strip()
            
            if response == 'yes':
                print()
                print("Sending test notification...")
                
                success = chat_client.send_notification(
                    message="This is a test notification from the BMA Social Support Bot. All systems operational!",
                    venue_name="Test Venue",
                    venue_data={
                        'contract_end': '2025-12-31',
                        'zones': 5,
                        'contact': 'test@example.com'
                    },
                    user_info={
                        'name': 'Test User',
                        'phone': '+66 812345678',
                        'platform': 'WhatsApp'
                    },
                    department=Department.OPERATIONS,
                    priority=Priority.INFO,
                    context="This is a test notification to verify Google Chat integration is working correctly."
                )
                
                if success:
                    print("✅ Test notification sent successfully!")
                    print("Check your BMAsia All Google Chat space")
                else:
                    print("❌ Failed to send test notification")
                    print("Check the error messages above")
            
            # Test escalation detection
            print()
            print("Testing automatic escalation detection...")
            print("-" * 40)
            
            escalation_tests = [
                "The music is too loud",
                "All zones offline emergency!",
                "Can you update our playlist?",
                "System completely down urgent help needed",
            ]
            
            for msg in escalation_tests:
                should_esc = should_escalate(msg)
                print(f"'{msg[:40]}...' → Escalate: {'Yes 🚨' if should_esc else 'No'}")
            
        else:
            print("❌ Cannot access the configured space")
            print()
            print("Possible issues:")
            print("1. Bot not added to the space")
            print("2. Space ID is incorrect")
            print("3. Bot doesn't have permission")
            print()
            print("To add the bot to your space:")
            print("1. Open Google Chat")
            print("2. Go to your BMAsia All space")
            print("3. Type: @BMA Social Support Bot")
            print("4. Click 'Add to space' when prompted")
    else:
        print("❌ Could not connect to Google Chat API")
        print()
        print("Make sure you have:")
        print("1. Enabled Google Chat API")
        print("2. Service account has Chat Bot scope")
        
except ImportError as e:
    print(f"❌ Could not import Google Chat client: {e}")
    print()
    print("Install required packages:")
    print("pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")

print()
print("=" * 60)
print("Next Steps:")
print()
print("Once Google Chat is working:")
print("1. The bot will automatically detect critical issues")
print("2. Messages will be tagged by department (Sales/Ops/Design/Finance)")
print("3. Priority levels help team focus on urgent matters")
print("4. All notifications go to BMAsia All group for visibility")
print()
print("Integration with bot:")
print("- Critical issues auto-escalate")
print("- Venue context included automatically")
print("- Smart categorization based on keywords")
print("- Full conversation context provided")
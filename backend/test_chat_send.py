#!/usr/bin/env python3
"""Send a test notification to Google Chat"""

import os
from dotenv import load_dotenv
load_dotenv()

from google_chat_client import chat_client, Department, Priority

# Send test notification
success = chat_client.send_notification(
    message="Test notification from BMA Social Bot - Integration successful! 🎉",
    venue_name="Test Venue (Hilton Pattaya)", 
    venue_data={
        'contract_end': '2025-10-31',
        'zones': 5,
        'contact': 'test@hilton.com'
    },
    user_info={
        'name': 'System Test',
        'phone': '+66 812345678',
        'platform': 'WhatsApp'
    },
    department=Department.OPERATIONS,
    priority=Priority.INFO,
    context="This is a test to verify Google Chat integration is working correctly."
)

if success:
    print("✅ Test notification sent successfully!")
    print("Check your BMAsia Working Group space in Google Chat")
else:
    print("❌ Failed to send test notification")
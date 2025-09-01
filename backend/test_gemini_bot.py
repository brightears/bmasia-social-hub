#!/usr/bin/env python3
"""
Test the Gemini-powered bot
"""

import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Test the bot
try:
    from bot_gemini import gemini_bot
    print("✅ Gemini bot loaded successfully")
except Exception as e:
    print(f"❌ Failed to load Gemini bot: {e}")
    sys.exit(1)

# Test messages
test_messages = [
    ("Hi, I am from Hilton Pattaya", "+66812345678"),
    ("Can you tell me what is playing at my venue called 'Edge'?", "+66812345678"),
    ("The zone is called Edge", "+66812345678"),
    ("What's playing at Edge?", "+66812345678"),
    ("Edge", "+66812345678"),
]

print("\n" + "="*60)
print("Testing Gemini Bot with Natural Language Understanding")
print("="*60)

for message, phone in test_messages:
    print(f"\n📱 User ({phone}): {message}")
    print("-" * 40)
    
    try:
        response = gemini_bot.process_message(message, phone, "Test User")
        print(f"🤖 Bot: {response}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("-" * 40)

print("\n✅ Test completed!")
#!/usr/bin/env python3
"""Test bot with new Google Sheets structure"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import bot components
from bot_gemini import GeminiBot

print('=' * 60)
print('Testing Bot with New Google Sheets Structure')
print('=' * 60)
print()

# Initialize bot
try:
    bot = GeminiBot()
    print("✅ Bot initialized successfully")
except Exception as e:
    print(f"❌ Bot initialization failed: {e}")
    exit(1)

# Test scenarios
test_cases = [
    ("Hi, I'm from Hilton Pattaya", "+66812345678"),
    ("What's our current rate?", "+66812345678"),
    ("When does our contract expire?", "+66812345678"),
    ("Who's my contact person?", "+66812345678"),
    ("What zones do we have?", "+66812345678"),
]

print("\n🧪 Testing conversations:")
print("-" * 40)

for message, phone in test_cases:
    print(f'\n📱 User: {message}')
    try:
        response = bot.process_message(message, phone, 'Test User', 'WhatsApp')
        print(f'🤖 Bot: {response[:200]}...' if len(response) > 200 else f'🤖 Bot: {response}')
    except Exception as e:
        print(f'❌ Error: {e}')
    print("-" * 40)

print("\n✅ Test complete!")
print("\n💡 Key things to verify:")
print("1. Property identification works (Hilton Pattaya recognized)")
print("2. Rate shows: THB 10,500 per zone (THB 42,000 total)")
print("3. Contract expiry shows: 31st October 2025")
print("4. Contacts show with titles")
print("5. Zones list properly: Drift Bar, Edge, Horizon, Shore")
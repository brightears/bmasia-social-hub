#!/usr/bin/env python3
"""
Test the customer confirmation flow for music fixes
"""

import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

# Set test environment
os.environ['GEMINI_API_KEY'] = os.getenv('GEMINI_API_KEY', 'test_key')

from bot_simplified import simplified_bot

def test_confirmation_flow():
    """Test the bot's confirmation flow for fixing music issues"""
    
    print("\n" + "="*60)
    print("TESTING CUSTOMER CONFIRMATION FLOW")
    print("="*60 + "\n")
    
    test_phone = "+66812345678"
    test_user = "John (Hilton GM)"
    
    # Test 1: Customer reports wrong music
    print("1. Customer reports wrong music:")
    print("-" * 40)
    message1 = "The music at Drift Bar seems wrong, it should be playing chill lunch music but it's playing party music"
    response1 = simplified_bot.process_message(message1, test_phone, test_user)
    print(f"Customer: {message1}")
    print(f"Bot: {response1}\n")
    
    # Test 2: Customer confirms they want to change it
    print("2. Customer confirms fix:")
    print("-" * 40)
    message2 = "Yes please fix it"
    response2 = simplified_bot.process_message(message2, test_phone, test_user)
    print(f"Customer: {message2}")
    print(f"Bot: {response2}\n")
    
    # Test 3: New customer reports volume issue
    print("3. Different customer reports volume issue:")
    print("-" * 40)
    test_phone2 = "+66887654321"
    message3 = "The music is too loud in the Lobby"
    response3 = simplified_bot.process_message(message3, test_phone2, "Sarah (Front Desk)")
    print(f"Customer: {message3}")
    print(f"Bot: {response3}\n")
    
    # Test 4: Customer declines fix
    print("4. Customer declines fix:")
    print("-" * 40)
    message4 = "No, leave it as is"
    response4 = simplified_bot.process_message(message4, test_phone2)
    print(f"Customer: {message4}")
    print(f"Bot: {response4}\n")
    
    # Test 5: Check zone status directly
    print("5. Direct zone status check:")
    print("-" * 40)
    message5 = "What's playing at Hilton Pattaya Drift Bar?"
    response5 = simplified_bot.process_message(message5, test_phone, test_user)
    print(f"Customer: {message5}")
    print(f"Bot: {response5}\n")

if __name__ == "__main__":
    test_confirmation_flow()
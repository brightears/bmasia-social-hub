#!/usr/bin/env python3
"""
Test the new conversational bot with GPT-5-Mini
"""

from bot_final import music_bot
import asyncio

def test_conversational_bot():
    """Test various conversational interactions"""
    
    print("\n" + "="*60)
    print("🎵 BMA Social Music Bot - GPT-5-Mini Conversational Test 🎵")
    print("="*60 + "\n")
    
    test_messages = [
        # Natural volume requests
        ("music is too loud at Edge in Hilton Pattaya", "+66123456789"),
        ("can you turn it down a bit in the lobby?", "+66123456789"),
        ("crank up the tunes in Drift Bar!", "+66123456789"),
        
        # Natural playlist requests  
        ("play something chill in Edge", "+66123456789"),
        ("I want 80s music at Hilton Pattaya", "+66123456789"),
        ("can we get some jazz vibes going?", "+66123456789"),
        ("party mode in Drift Bar please!", "+66123456789"),
        
        # Status checks
        ("what's playing in Edge right now?", "+66123456789"),
        ("what song is this?", "+66123456789"),
        
        # Troubleshooting
        ("the music stopped working in Edge", "+66123456789"),
        ("no sound in the lobby help!", "+66123456789"),
        
        # Venue questions
        ("when does our contract expire?", "+66123456789"),
        ("how much are we paying per year?", "+66123456789"),
        ("how many zones do we have?", "+66123456789"),
        
        # General help
        ("hi", "+66123456789"),
        ("help", "+66123456789"),
        ("what can you do?", "+66123456789"),
    ]
    
    print("Testing conversational responses...\n")
    
    for i, (message, phone) in enumerate(test_messages, 1):
        print(f"Test {i}:")
        print(f"User: {message}")
        
        try:
            response = music_bot.process_message(message, phone, "Test User")
            print(f"Bot: {response}")
        except Exception as e:
            print(f"Error: {e}")
        
        print("-" * 50)
        
        # Small delay between tests
        import time
        time.sleep(0.5)
    
    print("\n" + "="*60)
    print("✅ Conversational Test Complete!")
    print("="*60 + "\n")
    
    # Test context retention
    print("Testing context retention (same user, multiple messages):")
    print("-" * 50)
    
    context_messages = [
        "I'm at Hilton Pattaya",
        "turn up the music in Edge",  # Should remember Hilton Pattaya
        "what's playing?",  # Should remember Edge and Hilton Pattaya
        "make it quieter",  # Should remember everything
    ]
    
    phone = "+66999888777"
    for message in context_messages:
        print(f"User: {message}")
        response = music_bot.process_message(message, phone, "Context Test User")
        print(f"Bot: {response}")
        print("-" * 50)
        time.sleep(0.5)
    
    print("\n🎉 All tests complete! The bot should now be much more conversational!")
    print("Notice how it:")
    print("  • Uses casual, friendly language")
    print("  • Sometimes suggests design services")
    print("  • Remembers context between messages")
    print("  • Understands natural language better")

if __name__ == "__main__":
    test_conversational_bot()
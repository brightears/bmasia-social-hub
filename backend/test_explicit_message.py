#!/usr/bin/env python3
"""
Test the bot with explicit venue name
"""

import os
import sys

def load_env():
    """Load environment variables from .env file"""
    try:
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value.strip('"').strip("'")
    except FileNotFoundError:
        print("No .env file found")

def test_explicit_venue():
    """Test with explicit venue name"""
    
    load_env()
    
    # Add the current directory to path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    try:
        from bot_final import music_bot
        
        print("=== Testing Explicit Venue Messages ===")
        
        # Test messages with very explicit venue names
        test_messages = [
            "What's playing at Edge in Hilton Pattaya?",
            "Check music at Edge zone in Hilton Pattaya hotel",
            "Status of music at Hilton Pattaya Edge zone"
        ]
        
        for message in test_messages:
            print(f"\n🤖 Testing: '{message}'")
            
            try:
                response = music_bot.process_message(message, "+66123456789", "Test User")
                print(f"📱 Response: {response}")
                
                # Check for success indicators
                if "At Edge" in response and '"' in response and "by" in response:
                    print("✅ SUCCESS! Real track details returned!")
                elif "couldn't find" in response.lower():
                    print("⚠️ Venue not found in system")
                elif "which venue" in response.lower():
                    print("⚠️ Bot didn't recognize venue name")
                elif "music is playing" in response.lower() and '"' not in response:
                    print("❌ Still getting generic response")
                else:
                    print("ℹ️ Other response type")
                    
            except Exception as e:
                print(f"❌ Error: {e}")
        
    except Exception as e:
        print(f"❌ Error importing bot: {e}")

def main():
    print("🎵 Testing Explicit Venue Messages")
    print("=" * 40)
    
    test_explicit_venue()

if __name__ == "__main__":
    main()
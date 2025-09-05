#!/usr/bin/env python3
"""
Test script to verify the bot fixes work correctly
"""

import sys
import os

# Add backend directory to path
sys.path.append('/Users/benorbe/Documents/BMAsia Social Hub/backend')

# Set environment variables
os.environ['SOUNDTRACK_API_CREDENTIALS'] = 'YVhId2UyTWJVWEhMRWlycUFPaUl3Y2NtOXNHeUoxR0Q6SVRHazZSWDVYV2FTenhiS1ZwNE1sSmhHUUJEVVRDdDZGU0FwVjZqMXNEQU1EMjRBT2pub2hmZ3NQODRRNndQWg=='
os.environ['GEMINI_API_KEY'] = 'AIzaSyDm2Km4ydXBhUp1bBamVZ1XaTwXZIoCoHs'

def test_bot_fixes():
    """Test the corrected bot functionality"""
    
    print("=== Testing Bot Fixes ===")
    
    try:
        # Import after setting environment variables
        from soundtrack_api import soundtrack_api
        from bot_final import music_bot
        
        print("✅ Bot imported successfully")
        
        # Test 1: Get zone status for Edge
        print("\n=== TEST 1: Zone Status ===")
        edge_zone_id = "U291bmRab25lLCwxOGZ5M2R2a2NuNC9Mb2NhdGlvbiwsMW9wM3prbHBjZTgvQWNjb3VudCwsMXN4N242NTZyeTgv"
        status = soundtrack_api.get_zone_status(edge_zone_id)
        print(f"Zone Status: {status}")
        
        if status and 'error' not in status:
            print("✅ Zone status retrieval working")
            print(f"  - Name: {status.get('name')}")
            print(f"  - Playing: {status.get('playing')}")
            print(f"  - Playback State: {status.get('playback_state')}")
            print(f"  - Current Track: {status.get('current_track')}")
            print(f"  - Current Playlist: {status.get('current_playlist')}")
            print(f"  - Volume: {status.get('volume')} (should be None)")
        else:
            print(f"❌ Zone status failed: {status}")
        
        # Test 2: Volume Control
        print("\n=== TEST 2: Volume Control ===")
        volume_result = soundtrack_api.set_volume(edge_zone_id, 10)
        print(f"Volume Result: {volume_result}")
        
        if volume_result.get('success'):
            print("✅ Volume control working")
        else:
            print(f"❌ Volume control failed: {volume_result}")
        
        # Test 3: Bot Message Processing
        print("\n=== TEST 3: Bot Message Processing ===")
        
        # Test volume query
        bot_response = music_bot.process_message(
            "What's the volume level at Edge in Hilton Pattaya?", 
            "+66123456789"
        )
        print(f"Volume Query Response: {bot_response}")
        
        # Test status query  
        bot_response = music_bot.process_message(
            "What's playing at Edge in Hilton Pattaya?", 
            "+66123456789"
        )
        print(f"Status Query Response: {bot_response}")
        
        # Test volume adjustment
        bot_response = music_bot.process_message(
            "Set volume to 8 at Edge in Hilton Pattaya", 
            "+66123456789"
        )
        print(f"Volume Adjustment Response: {bot_response}")
        
        print("\n=== Test Complete ===")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_bot_fixes()
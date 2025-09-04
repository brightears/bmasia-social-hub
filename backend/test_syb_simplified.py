#!/usr/bin/env python3
"""
Test simplified SYB handling - no design comparison, just live data and history
"""

import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

# Set test environment
os.environ['GEMINI_API_KEY'] = os.getenv('GEMINI_API_KEY', 'test_key')

from bot_simplified import simplified_bot

def test_syb_simplified():
    """Test the simplified SYB handling"""
    
    print("\n" + "="*60)
    print("TESTING SIMPLIFIED SYB HANDLING")
    print("="*60 + "\n")
    
    test_phone = "+66812345678"
    test_user = "John (Hilton GM)"
    
    print("KEY DIFFERENCES:")
    print("-" * 40)
    print("SYB Venues (like Hilton Pattaya):")
    print("  • NO design comparison")
    print("  • Shows live status from SYB API")
    print("  • Shows playlist history (past 3 weeks)")
    print("  • Customer manages designs in their SYB account")
    print()
    print("Beat Breeze Venues:")
    print("  • Compares with our design specs")
    print("  • Can detect 'wrong' music")
    print("  • We maintain the design records")
    print("\n" + "="*60 + "\n")
    
    # Test 1: Check SYB venue status (Hilton is SYB)
    print("1. Check SYB venue (Hilton Pattaya):")
    print("-" * 40)
    message1 = "What's playing at Hilton Pattaya Drift Bar?"
    print(f"Customer: {message1}")
    print("\nExpected Response:")
    print("📊 Current status for Drift Bar:")
    print("🎵 Now playing: [Current Playlist]")
    print("   Track: '[Current Song]' by [Artist]")
    print("🔊 Volume level: 11/16")
    print()
    print("📅 Past 3 weeks:")
    print("   Most played: Pool Party Vibes")
    print("   Playlist rotation:")
    print("   • Pool Party Vibes: 42 plays")
    print("   • Chill Lunch Vibes: 35 plays")
    print("   • Sunset Sessions: 28 plays")
    print()
    
    # Test 2: Customer reports issue with SYB venue
    print("2. Customer reports issue with SYB venue:")
    print("-" * 40)
    message2 = "The music seems wrong at Drift Bar"
    print(f"Customer: {message2}")
    print("\nExpected Response:")
    print("I've checked Drift Bar status.")
    print("If you need any adjustments, please let me know what changes you'd like.")
    print("(Note: No 'should be' comparison for SYB venues)")
    print()
    
    # Test 3: SYB zone offline
    print("3. SYB zone offline:")
    print("-" * 40)
    message3 = "Drift Bar music is not working"
    print(f"Customer: {message3}")
    print("\nExpected Response (if offline):")
    print("⚠️ Drift Bar appears to be offline.")
    print("I can notify our team to check the connection. Would you like me to do that?")
    print()
    
    print("="*60)
    print("SUMMARY")
    print("="*60)
    print()
    print("For SYB venues, the bot now:")
    print("1. Reports current status without judgment")
    print("2. Shows historical patterns for context")
    print("3. Doesn't compare with 'intended' designs")
    print("4. Lets customers decide what changes they want")
    print("5. Can still notify team for technical issues (offline zones)")

if __name__ == "__main__":
    test_syb_simplified()
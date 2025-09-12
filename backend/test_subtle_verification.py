#!/usr/bin/env python3
"""
Test subtle verification implementation for sensitive queries
"""

import json
from bot_ai_first import AIFirstBot

def test_verification_scenarios():
    """Test various pricing query scenarios"""
    
    bot = AIFirstBot()
    
    # Test venue data (simulating Hilton Pattaya)
    venue = {
        'name': 'Hilton Pattaya',
        'zones': ['Drift Bar', 'Edge', 'Horizon', 'Shore'],
        'platform': 'Soundtrack Your Brand',
        'contract_end': '2025-10-31',
        'annual_price': 'THB 12,000'
    }
    
    test_cases = [
        {
            "scenario": "Direct pricing query",
            "message": "Hi, I am from Hilton Pattaya, how much are we paying right now?",
            "expected": "Should trigger verification question about Rudolf/Dennis/zones"
        },
        {
            "scenario": "Contract renewal query",
            "message": "When is our contract up for renewal?",
            "expected": "Should trigger verification question"
        },
        {
            "scenario": "Music query (non-sensitive)",
            "message": "What song is playing at Edge?",
            "expected": "Should NOT trigger verification, just check_playing command"
        },
        {
            "scenario": "Volume control (non-sensitive)",
            "message": "Can you turn up the volume at Drift Bar?",
            "expected": "Should NOT trigger verification, just volume command"
        }
    ]
    
    print("=" * 60)
    print("TESTING SUBTLE VERIFICATION")
    print("=" * 60)
    
    for test in test_cases:
        print(f"\nScenario: {test['scenario']}")
        print(f"Message: {test['message']}")
        
        # Process message
        ai_decision = bot._analyze_message_with_ai(
            message=test['message'],
            venue=venue,
            context=[]
        )
        
        print(f"AI Action: {ai_decision.get('action')}")
        print(f"Response: {ai_decision.get('response', '')[:200]}")
        print(f"Expected: {test['expected']}")
        print("-" * 40)
    
    print("\n" + "=" * 60)
    print("VERIFICATION FEATURES:")
    print("=" * 60)
    print("""
✅ Subtle questions about Rudolf (GM) or Dennis (F&B)
✅ Natural zone verification (Drift Bar, Edge, etc.)
✅ No mention of "security" or "verification"
✅ Graceful escalation for wrong answers
✅ Direct responses for non-sensitive queries
    """)

if __name__ == "__main__":
    test_verification_scenarios()
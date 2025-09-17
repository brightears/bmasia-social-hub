#!/usr/bin/env python3
"""
Test script for venue detection confidence
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from venue_manager import VenueManager

def test_venue_detection():
    """Test various venue detection scenarios"""
    vm = VenueManager()

    test_messages = [
        # High confidence tests (should find venue)
        "I am from Hilton Pattaya and need help",
        "This is John from DoubleTree by Hilton Bangkok Ploenchit",

        # Low confidence tests (should NOT find venue)
        "I am from Hilton",  # Too ambiguous - multiple Hiltons
        "We're at the hotel and need assistance",  # Too generic
        "I'm from Bangkok",  # City name, not venue

        # No match tests
        "I am from Apple Store",  # Not in database
        "Help with our restaurant",  # Generic

        # Edge cases
        "hilton pattaya",  # Exact match lowercase
        "HILTON PATTAYA needs help",  # Exact match uppercase
    ]

    print("=" * 70)
    print("VENUE DETECTION CONFIDENCE TESTING")
    print("=" * 70)

    for message in test_messages:
        print(f"\nMessage: '{message}'")
        print("-" * 50)

        # Test old method (for comparison)
        venue = vm.find_venue(message)
        if venue:
            print(f"✓ find_venue(): {venue['name']}")
        else:
            print("✗ find_venue(): No venue found")

        # Test new confidence method
        venue_conf, confidence = vm.find_venue_with_confidence(message)
        if venue_conf:
            status = "✓" if confidence >= 0.7 else "⚠️"
            print(f"{status} Confidence: {confidence:.0%} - {venue_conf['name']}")
        else:
            print("✗ No venue match")

        # Test possible venues
        possible = vm.find_possible_venues(message, threshold=0.3)
        if possible:
            print(f"Possible venues ({len(possible)}):")
            for v, conf in possible[:3]:
                print(f"  - {v['name']} ({conf:.0%})")

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    test_venue_detection()
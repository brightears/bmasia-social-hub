#!/usr/bin/env python3
"""
Test contact extraction for specific venues we know have correspondence
"""

import os
import sys
from pathlib import Path

# Load environment variables from .env file
env_file = Path(__file__).parent / '.env'
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                value = value.strip().strip('"').strip("'")
                os.environ[key] = value

# Now run the extractor for specific hotels
from extract_venue_contacts import VenueContactExtractor

print("\n🔍 Testing contact extraction for popular hotel chains...\n")

extractor = VenueContactExtractor(dry_run=True)

# Test with specific popular venues
test_venues = [
    "Marriott",
    "Hyatt",
    "Intercontinental",
    "Sheraton",
    "Westin",
    "Centara",
    "Anantara"
]

for venue in test_venues:
    print(f"\n🏨 Testing: {venue}")
    extractor.run(specific_venue=venue, limit=3)
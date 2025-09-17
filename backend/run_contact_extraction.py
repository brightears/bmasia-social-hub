#!/usr/bin/env python3
"""
Run contact extraction with proper environment setup
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
                # Remove quotes if present
                value = value.strip().strip('"').strip("'")
                os.environ[key] = value
                if key == 'GOOGLE_CREDENTIALS_JSON':
                    print(f"✅ Loaded Google credentials")

# Now run the extractor
from extract_venue_contacts import VenueContactExtractor

# Test with dry run first
print("\n🔍 Starting contact extraction in DRY RUN mode...")
print("This will search for venue contacts but not update the database.\n")

extractor = VenueContactExtractor(dry_run=True)
extractor.run(limit=5)

print("\n" + "="*60)
print("Dry run complete. To run the actual extraction:")
print("1. For specific venue: python run_contact_extraction.py --venue 'Hilton'")
print("2. For all venues: python run_contact_extraction.py --all")
print("="*60)
#!/usr/bin/env python3
"""
Test Gmail search directly to see what emails are available
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

# Test Gmail client directly
from gmail_client import gmail_client

print("Testing Gmail search for venue emails...\n")

# Test search for common hotel names
test_searches = ["Hilton", "Marriott", "hotel", "venue", "music"]

for search_term in test_searches:
    print(f"\n🔍 Searching for: '{search_term}'")
    results = gmail_client.search_venue_emails(search_term, days_back=30)

    if results:
        print(f"✅ Found {len(results)} emails")
        for email in results[:3]:  # Show first 3
            print(f"   - From: {email.get('from', 'Unknown')[:50]}")
            print(f"     Subject: {email.get('subject', 'No subject')[:50]}")
            print(f"     Date: {email.get('date', 'Unknown date')[:20]}")
    else:
        print("❌ No emails found")
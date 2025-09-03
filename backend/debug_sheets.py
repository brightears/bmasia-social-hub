#!/usr/bin/env python3
"""Debug Google Sheets data structure"""

import os
import json
from dotenv import load_dotenv
from google_sheets_client import GoogleSheetsClient

load_dotenv()

print('=' * 60)
print('Google Sheets Data Debug')
print('=' * 60)
print()

# Initialize sheets client
sheets = GoogleSheetsClient()

# Get all venues
venues = sheets.get_all_venues()

print(f"Total venues found: {len(venues)}")
print()

# Show first venue's data structure
if venues:
    print("First venue data structure:")
    print("-" * 40)
    first_venue = venues[0]
    for key, value in first_venue.items():
        print(f"  {key}: {value}")
    print()
    
    # Check for Hilton Pattaya specifically
    print("Looking for Hilton Pattaya:")
    print("-" * 40)
    hilton = sheets.find_venue_by_name("Hilton Pattaya")
    if hilton:
        print("Found! Data structure:")
        for key, value in hilton.items():
            print(f"  {key}: {value}")
    else:
        print("Not found. Available property names:")
        for venue in venues:
            prop_name = venue.get('property_name', venue.get('outlet_name', 'Unknown'))
            print(f"  - {prop_name}")
else:
    print("No venues found in sheet!")

print()
print("Expected fields for contract rate:")
print("-" * 40)
print("Looking for fields like:")
print("  - contract_rate")
print("  - monthly_rate")
print("  - rate")
print("  - pricing")
print("  - contract_value")
print()

# Check what fields contain 'rate' or 'contract'
if venues:
    all_keys = set()
    for venue in venues:
        all_keys.update(venue.keys())
    
    print("All available fields in sheet:")
    print("-" * 40)
    for key in sorted(all_keys):
        if 'rate' in key.lower() or 'contract' in key.lower() or 'price' in key.lower():
            print(f"  ★ {key} (potential rate/contract field)")
        else:
            print(f"    {key}")
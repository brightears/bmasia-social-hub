#!/usr/bin/env python3
"""Force refresh Google Sheets data and show what's being read"""

import os
from dotenv import load_dotenv
from google_sheets_client import GoogleSheetsClient

load_dotenv()

print('=' * 60)
print('Force Refreshing Google Sheets Data')
print('=' * 60)
print()

# Initialize sheets client
sheets = GoogleSheetsClient()

# Force refresh by getting all venues
venues = sheets.get_all_venues()

print(f"✅ Found {len(venues)} venues in sheet\n")

# Show Hilton Pattaya data
for venue in venues:
    if 'hilton' in venue.get('property_name', '').lower():
        print("📊 Hilton Pattaya Current Data:")
        print("-" * 40)
        
        # Show all fields
        important_fields = [
            'property_name',
            'business_type',
            'amount_of_zones_venues',
            'name_of_zones_venues',
            'music_platform',
            'current_price_per_zone_venue_per_year',
            'contract_expiry',
            'contact_name_1',
            'contact_title_1',
            'contact_email_1',
            'soundtrack_account_id',
            'special_notes'
        ]
        
        for field in important_fields:
            value = venue.get(field, 'NOT FOUND')
            if value:
                print(f"  {field}: {value}")
        
        print("\n📝 Special Notes Content:")
        print(f"  {venue.get('special_notes', 'No notes')}")
        
        print("\n💰 Rate Calculation:")
        rate = venue.get('current_price_per_zone_venue_per_year', '')
        zones = venue.get('amount_of_zones_venues', '')
        print(f"  Per zone: {rate}")
        print(f"  Zones: {zones}")
        
        if rate and zones:
            try:
                import re
                # Extract number from rate
                numbers = re.findall(r'[\d,]+', str(rate))
                if numbers:
                    per_zone = int(numbers[0].replace(',', ''))
                    total_zones = int(zones)
                    total = per_zone * total_zones
                    print(f"  💵 Total annual: THB {total:,}")
            except:
                print("  ⚠️ Could not calculate total")
        
        break
else:
    print("❌ No Hilton Pattaya found in sheet!")
    print("\nAll property names found:")
    for venue in venues:
        print(f"  - {venue.get('property_name', 'Unknown')}")
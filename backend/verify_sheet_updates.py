#!/usr/bin/env python3
"""Verify Google Sheets structure updates"""

import os
import re
from datetime import datetime
from dotenv import load_dotenv
from google_sheets_client import GoogleSheetsClient

load_dotenv()

print('=' * 60)
print('🔍 Verifying Google Sheets Structure Updates')
print('=' * 60)
print()

# Initialize sheets client
sheets = GoogleSheetsClient()

# Get all venues
venues = sheets.get_all_venues()

if not venues:
    print("❌ No venues found. Checking authentication...")
    print("   Make sure Google credentials are properly set")
    exit(1)

print(f"✅ Found {len(venues)} venue(s) in sheet\n")

# Check the first venue (Hilton Pattaya)
venue = venues[0]

print("📊 Data Structure Check:")
print("-" * 40)

# Expected optimized fields based on best practices
checks = {
    'property_name': '✅ Property identification',
    'business_type': '✅ Business categorization',
    'zone_count': '✅ Zone counting (simplified name)',
    'zone_names': '✅ Zone listing',
    'music_platform': '✅ Platform specification',
    'annual_price_per_zone': '✅ Pricing (simplified name)',
    'currency': '✅ Currency separation',
    'contract_start': '✅ Start date (ISO format)',
    'contract_end': '✅ End date (ISO format)', 
    'primary_contact_name': '✅ Primary contact',
    'primary_contact_title': '✅ Contact title',
    'primary_contact_email': '✅ Contact email'
}

# Check which fields exist
found_fields = []
missing_fields = []
old_format_fields = []

for field, description in checks.items():
    if field in venue:
        found_fields.append(f"{description}: '{venue[field]}'")
    else:
        missing_fields.append(f"❌ Missing: {field}")

# Check for old field names that might still exist
old_field_checks = {
    'amount_of_zones_venues': 'Should be zone_count',
    'name_of_zones_venues': 'Should be zone_names',
    'current_price_per_zone_venue_per_year': 'Should be annual_price_per_zone',
    'contract_expiry': 'Should be contract_end'
}

for old_field, suggestion in old_field_checks.items():
    if old_field in venue:
        old_format_fields.append(f"⚠️  Found old field '{old_field}' ({suggestion})")

print("✅ Found Fields:")
for field in found_fields[:5]:  # Show first 5
    print(f"   {field}")
if len(found_fields) > 5:
    print(f"   ... and {len(found_fields) - 5} more")

if missing_fields:
    print("\n⚠️  Missing/Different Fields:")
    for field in missing_fields[:5]:
        print(f"   {field}")

if old_format_fields:
    print("\n📝 Old Format Fields Still Present:")
    for field in old_format_fields:
        print(f"   {field}")

# Check data format compliance
print("\n📏 Format Compliance Check:")
print("-" * 40)

# Check date formats
date_fields = ['contract_start', 'contract_end', 'activation_date', 'contract_expiry']
for field in date_fields:
    if field in venue and venue[field]:
        value = venue[field]
        # Check if ISO format (YYYY-MM-DD)
        if re.match(r'^\d{4}-\d{2}-\d{2}', str(value)):
            print(f"✅ {field}: {value} (ISO format)")
        else:
            print(f"⚠️  {field}: {value} (not ISO format YYYY-MM-DD)")

# Check zone names separator
if 'zone_names' in venue:
    zones = venue['zone_names']
    if '|' in zones:
        print(f"✅ zone_names: Using pipe separator (|)")
    elif ',' in zones:
        print(f"⚠️  zone_names: Still using comma separator, consider pipe (|)")
elif 'name_of_zones_venues' in venue:
    zones = venue['name_of_zones_venues']
    print(f"⚠️  Using old field name 'name_of_zones_venues': {zones}")

# Check price format
price_fields = ['annual_price_per_zone', 'current_price_per_zone_venue_per_year']
for field in price_fields:
    if field in venue and venue[field]:
        value = str(venue[field])
        if value.replace(',', '').replace('.', '').isdigit():
            print(f"✅ {field}: {value} (numeric)")
        else:
            print(f"⚠️  {field}: {value} (contains non-numeric characters)")

# Check currency field
if 'currency' in venue:
    print(f"✅ currency: {venue['currency']} (separate field)")
else:
    print("⚠️  currency: Not found as separate field")

print("\n📈 Summary:")
print("-" * 40)
print(f"Fields found: {len(found_fields)}/{len(checks)}")
print(f"Old format fields: {len(old_format_fields)}")

if len(found_fields) >= 10 and len(old_format_fields) == 0:
    print("\n🎉 Excellent! Sheet follows AI best practices!")
elif len(found_fields) >= 8:
    print("\n✅ Good! Sheet is well-structured with minor improvements possible.")
else:
    print("\n⚠️  Sheet may need updates to follow best practices.")

# Show all available fields
print("\n📋 All Available Fields:")
print("-" * 40)
for key in sorted(venue.keys()):
    print(f"   {key}: {venue[key][:50] if len(str(venue[key])) > 50 else venue[key]}")
#!/usr/bin/env python3
"""
Test Gemini Bot with Google Sheets Integration
"""

import os
import sys
from dotenv import load_dotenv

# Load environment first
load_dotenv()

# Now import the bot
from bot_gemini import gemini_bot

print('=' * 60)
print('Testing Gemini Bot with Google Sheets Integration')
print('=' * 60)
print()

# Test venue identification and sheets lookup
test_cases = [
    ('Hi, I am from Hilton Pattaya', '+66812345678'),
    ('What are our venue details?', '+66812345678'),
    ('Who is our IT contact?', '+66812345678'),
    ('What zones do we have?', '+66812345678'),
]

for message, phone in test_cases:
    print(f'📱 User: {message}')
    try:
        response = gemini_bot.process_message(message, phone, 'Test User')
        print(f'🤖 Bot: {response}')
    except Exception as e:
        print(f'❌ Error: {e}')
    print('-' * 60)
    print()

# Also test direct sheets access
print('Direct Google Sheets Test:')
print('-' * 40)
try:
    if gemini_bot.sheets:
        venues = gemini_bot.sheets.get_all_venues()
        print(f'✅ Can access {len(venues)} venues from master sheet')
        
        # Show first few venues
        if venues:
            print('\nFirst 3 venues in sheet:')
            for i, venue in enumerate(venues[:3], 1):
                name = venue.get('name') or venue.get('Name') or venue.get('') or 'Unknown'
                location = venue.get('location') or venue.get('Location') or 'N/A'
                print(f'  {i}. {name} - {location}')
        
        # Try to find Hilton Pattaya
        print('\nSearching for Hilton Pattaya...')
        hilton = gemini_bot.sheets.find_venue_by_name('Hilton Pattaya')
        if hilton:
            print('✅ Found Hilton Pattaya in sheets!')
            print('Venue data:')
            for key, value in hilton.items():
                if value and key not in ['', 'sheet_id'] and str(value).strip():
                    print(f'   {key}: {value}')
        else:
            print('⚠️  Hilton Pattaya not found in sheets')
            print('   (You may need to add it to your master sheet)')
    else:
        print('❌ Sheets client not available')
except Exception as e:
    print(f'❌ Error accessing sheets: {e}')
    import traceback
    traceback.print_exc()

print()
print('=' * 60)
print('✅ Test completed!')
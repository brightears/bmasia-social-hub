#!/usr/bin/env python3
"""
Test Google Sheets Access
Tests if the sheet is properly shared with the service account
"""

import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

print("=" * 60)
print("Google Sheets Access Test")
print("=" * 60)
print()

# Check if credentials are loaded
import json
creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
if creds_json:
    try:
        creds = json.loads(creds_json)
        service_email = creds.get('client_email')
        print("✅ Credentials loaded")
        print(f"📧 Service Account Email: {service_email}")
        print()
        print("IMPORTANT: Make sure you've shared your Google Sheet with this email!")
        print()
        print("Steps to share:")
        print("1. Open your Google Sheet:")
        print("   https://docs.google.com/spreadsheets/d/1awtlzSY7eBwkvA9cbbjrb5wx--okEtWuj53b0AVSv44/")
        print()
        print("2. Click the 'Share' button (top right)")
        print()
        print(f"3. Add this email: {service_email}")
        print()
        print("4. Give it 'Editor' permission")
        print()
        print("5. Click 'Send'")
        print()
        print("-" * 60)
        
        # Try to connect
        try:
            from google_sheets_client import sheets_client
            
            if sheets_client.service:
                print("✅ API client initialized")
                print()
                print("Testing sheet access...")
                
                try:
                    # Try to read the sheet
                    venues = sheets_client.get_all_venues()
                    print(f"✅ SUCCESS! Found {len(venues)} venues in the sheet")
                    
                    if venues:
                        print("\nFirst venue:")
                        venue = venues[0]
                        for key, value in venue.items():
                            if value:
                                print(f"  {key}: {value}")
                                
                except Exception as e:
                    error_msg = str(e)
                    if "403" in error_msg or "permission" in error_msg.lower():
                        print("❌ Permission Denied!")
                        print()
                        print("The sheet is not shared with the service account.")
                        print(f"Please share the sheet with: {service_email}")
                    elif "404" in error_msg:
                        print("❌ Sheet Not Found!")
                        print()
                        print("Check that the MASTER_SHEET_ID is correct:")
                        print(f"Current ID: {os.getenv('MASTER_SHEET_ID')}")
                    elif "invalid_grant" in error_msg.lower() or "jwt" in error_msg.lower():
                        print("❌ Authentication Failed!")
                        print()
                        print("Possible issues:")
                        print("1. The credentials might be incorrect")
                        print("2. The service account might have been deleted")
                        print("3. The project might not have Google Sheets API enabled")
                        print()
                        print("Try creating a new service account and downloading fresh credentials")
                    else:
                        print(f"❌ Error: {e}")
            else:
                print("❌ Could not initialize Google Sheets client")
                
        except ImportError as e:
            print(f"❌ Import error: {e}")
            print("Make sure Google API libraries are installed:")
            print("pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
            
    except json.JSONDecodeError:
        print("❌ Invalid JSON in GOOGLE_CREDENTIALS_JSON")
else:
    print("❌ GOOGLE_CREDENTIALS_JSON not found in environment")
    print()
    print("Add to your .env file:")
    print("GOOGLE_CREDENTIALS_JSON={paste your JSON here}")

print()
print("=" * 60)
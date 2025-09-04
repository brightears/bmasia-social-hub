#!/usr/bin/env python3
"""
Check what's wrong with Google Sheets on Render deployment
"""

import os
import json
from dotenv import load_dotenv

load_dotenv()

print("=" * 60)
print("🔍 RENDER DEPLOYMENT DIAGNOSTICS")
print("=" * 60)
print()

# Check critical environment variables
critical_vars = [
    'GOOGLE_CREDENTIALS_JSON',
    'GOOGLE_CREDENTIALS_PATH',
    'MASTER_SHEET_ID',
    'GEMINI_API_KEY'
]

print("1️⃣ ENVIRONMENT VARIABLES CHECK:")
print("-" * 40)
for var in critical_vars:
    value = os.getenv(var)
    if value:
        if var == 'GOOGLE_CREDENTIALS_JSON':
            try:
                creds = json.loads(value)
                print(f"✅ {var}: Valid JSON with service account: {creds.get('client_email', 'Unknown')}")
            except:
                print(f"❌ {var}: INVALID JSON!")
        elif 'KEY' in var or 'TOKEN' in var:
            print(f"✅ {var}: Set (hidden)")
        else:
            print(f"✅ {var}: {value[:50]}...")
    else:
        print(f"❌ {var}: NOT SET")

print()
print("2️⃣ GOOGLE SHEETS TEST:")
print("-" * 40)

try:
    from google_sheets_client import GoogleSheetsClient
    sheets = GoogleSheetsClient()
    
    if sheets.service:
        print("✅ Sheets API connected")
        venues = sheets.get_all_venues()
        print(f"✅ Found {len(venues)} venues")
        if venues:
            print(f"   First venue: {venues[0].get('property_name', 'Unknown')}")
    else:
        print("❌ Sheets API NOT connected")
except Exception as e:
    print(f"❌ Sheets connection failed: {e}")

print()
print("3️⃣ REQUIRED RENDER ENVIRONMENT VARIABLES:")
print("-" * 40)
print("""
To fix on Render.com:
1. Go to https://dashboard.render.com/web/srv-d2m6l0re5dus739fso30/env
2. Add/Update these variables:

GOOGLE_CREDENTIALS_JSON = (paste entire JSON from .env file)
MASTER_SHEET_ID = 1xiXrJCmI-FgqtXcPCn4sKbcicDj2Q8kQe0yXjztpovM

3. Restart the service
""")
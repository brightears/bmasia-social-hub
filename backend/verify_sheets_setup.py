#!/usr/bin/env python3
"""
Verify Google Sheets Setup
Helps diagnose and fix Google Sheets integration issues
"""

import os
import json
from dotenv import load_dotenv

# Load environment
load_dotenv()

print("=" * 70)
print("🔍 Google Sheets Setup Verification")
print("=" * 70)
print()

# Step 1: Check credentials
print("Step 1: Checking Credentials")
print("-" * 40)

creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
if not creds_json:
    print("❌ GOOGLE_CREDENTIALS_JSON not found in .env file")
    print()
    print("Action Required:")
    print("1. Copy the entire JSON from your service account key file")
    print("2. Add to .env file as: GOOGLE_CREDENTIALS_JSON={paste JSON here}")
    exit(1)

try:
    creds = json.loads(creds_json)
    service_email = creds.get('client_email')
    project_id = creds.get('project_id')
    
    print(f"✅ Credentials loaded")
    print(f"   Project ID: {project_id}")
    print(f"   Service Account: {service_email}")
    print()
    
except json.JSONDecodeError as e:
    print(f"❌ Invalid JSON format: {e}")
    print()
    print("Action Required:")
    print("1. Make sure you copied the ENTIRE JSON content")
    print("2. Check for any missing brackets or quotes")
    exit(1)

# Step 2: Check Sheet ID
print("Step 2: Checking Sheet Configuration")
print("-" * 40)

sheet_id = os.getenv('MASTER_SHEET_ID')
if sheet_id:
    print(f"✅ Master Sheet ID: {sheet_id}")
    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/"
    print(f"   URL: {sheet_url}")
    print()
else:
    print("❌ MASTER_SHEET_ID not found in .env file")
    print("Action Required: Add MASTER_SHEET_ID to your .env file")
    exit(1)

# Step 3: Test API Connection
print("Step 3: Testing Google Sheets API")
print("-" * 40)

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    
    print("✅ Google API libraries installed")
    
    # Create credentials
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    
    try:
        credentials = service_account.Credentials.from_service_account_info(
            creds, scopes=SCOPES)
        print("✅ Service account credentials created")
        
        # Build service
        service = build('sheets', 'v4', credentials=credentials)
        print("✅ Google Sheets service initialized")
        
        # Try to access the sheet
        print()
        print("Step 4: Attempting to Access Sheet")
        print("-" * 40)
        
        try:
            result = service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range='A1:A1'
            ).execute()
            
            print("✅ SUCCESS! Sheet access working!")
            print()
            
            # Try to get more data
            result = service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range='Sheet1!A1:Z100'
            ).execute()
            
            values = result.get('values', [])
            if values:
                print(f"📊 Found {len(values)-1} rows of data (excluding header)")
                print()
                
                # Show headers
                if len(values) > 0:
                    headers = values[0]
                    print("Column headers found:")
                    for i, header in enumerate(headers[:10], 1):  # Show first 10
                        print(f"  {i}. {header}")
                    if len(headers) > 10:
                        print(f"  ... and {len(headers)-10} more columns")
                        
                print()
                print("✅ Everything is working! Your Google Sheets integration is ready.")
                
        except HttpError as e:
            error_details = e.error_details if hasattr(e, 'error_details') else str(e)
            
            if e.resp.status == 403:
                print("❌ Permission Denied (403)")
                print()
                print("📋 ACTION REQUIRED:")
                print()
                print("1. Open your Google Sheet:")
                print(f"   {sheet_url}")
                print()
                print("2. Click the 'Share' button (top right)")
                print()
                print("3. In the 'Add people and groups' field, paste this email:")
                print(f"   {service_email}")
                print()
                print("4. Set permission to 'Editor'")
                print()
                print("5. IMPORTANT: Uncheck 'Notify people' (optional)")
                print()
                print("6. Click 'Share'")
                print()
                print("7. Run this script again to verify")
                
            elif e.resp.status == 404:
                print("❌ Sheet Not Found (404)")
                print()
                print("The sheet ID might be incorrect or the sheet was deleted.")
                print(f"Current Sheet ID: {sheet_id}")
                print()
                print("Please verify the sheet exists at:")
                print(f"{sheet_url}")
                
            else:
                print(f"❌ API Error ({e.resp.status}): {error_details}")
                print()
                print("This might be a temporary issue. Try again in a few moments.")
                
    except Exception as e:
        if "invalid_grant" in str(e).lower():
            print("❌ Authentication Failed - Invalid Grant")
            print()
            print("This usually means one of the following:")
            print()
            print("1. The Google Sheets API is not enabled in your project")
            print("   → Go to: https://console.cloud.google.com/apis/library")
            print("   → Search for 'Google Sheets API'")
            print("   → Click on it and press 'Enable'")
            print()
            print("2. The service account key is invalid or corrupted")
            print("   → Try creating a new service account key")
            print()
            print("3. System time is incorrect (rare)")
            print("   → Check your system clock is accurate")
        else:
            print(f"❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            
except ImportError as e:
    print(f"❌ Missing required libraries: {e}")
    print()
    print("Install with:")
    print("pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")

print()
print("=" * 70)
print()

# Additional help
print("📚 Troubleshooting Resources:")
print("-" * 40)
print("1. Enable APIs: https://console.cloud.google.com/apis/library")
print("2. Service Accounts: https://console.cloud.google.com/iam-admin/serviceaccounts")
print("3. Google Sheets API Docs: https://developers.google.com/sheets/api")
print()
print("Need more help? Check the GOOGLE_SHEETS_SETUP.md file for detailed instructions.")
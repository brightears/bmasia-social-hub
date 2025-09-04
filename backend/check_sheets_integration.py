#!/usr/bin/env python3
"""
Google Sheets Integration Health Check
Tests if sheets integration is working and provides setup guidance
"""

import os
import sys
import json
from google_sheets_client import GoogleSheetsClient

def check_credentials():
    """Check if Google credentials are available"""
    
    print("🔍 Checking Google Sheets credentials...")
    
    # Check for credentials file
    creds_file = os.getenv('GOOGLE_CREDENTIALS_PATH', 'google-credentials.json')
    if os.path.exists(creds_file):
        print(f"✅ Credentials file found: {creds_file}")
        return True
    
    # Check for environment variable
    creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
    if creds_json:
        try:
            json.loads(creds_json)
            print("✅ Credentials found in GOOGLE_CREDENTIALS_JSON environment variable")
            return True
        except json.JSONDecodeError:
            print("❌ GOOGLE_CREDENTIALS_JSON environment variable contains invalid JSON")
            return False
    
    print("❌ No Google credentials found!")
    print("   Please set either:")
    print("   1. GOOGLE_CREDENTIALS_PATH env variable pointing to service account JSON file")
    print("   2. GOOGLE_CREDENTIALS_JSON env variable with service account JSON content")
    return False

def test_sheets_access():
    """Test if sheets can be accessed"""
    
    print("\n🔗 Testing Google Sheets connection...")
    
    try:
        sheets = GoogleSheetsClient()
        if not sheets.service:
            print("❌ Failed to create Sheets service")
            return False
        
        print("✅ Google Sheets service created successfully")
        
        # Test reading venues
        venues = sheets.get_all_venues()
        if venues:
            print(f"✅ Successfully loaded {len(venues)} venues from Google Sheets")
            
            # Show sample venue data
            sample = venues[0]
            print("\n📊 Sample venue data:")
            for key, value in sample.items():
                if value and 'price' in key.lower():
                    print(f"   💰 {key}: {value}")
                elif value and key in ['property_name', 'contract_expiry', 'expiry_date']:
                    print(f"   📋 {key}: {value}")
            
            return True
        else:
            print("⚠️  Sheets connection successful but no venues found")
            print("   Check MASTER_SHEET_ID environment variable")
            return False
            
    except Exception as e:
        print(f"❌ Error accessing Google Sheets: {e}")
        return False

def check_environment():
    """Check environment configuration"""
    
    print("\n🔧 Checking environment configuration...")
    
    master_sheet_id = os.getenv('MASTER_SHEET_ID')
    if master_sheet_id:
        print(f"✅ MASTER_SHEET_ID: {master_sheet_id}")
    else:
        print("⚠️  MASTER_SHEET_ID not set, using default")
    
    gemini_key = os.getenv('GEMINI_API_KEY')
    if gemini_key:
        print("✅ GEMINI_API_KEY is set")
    else:
        print("❌ GEMINI_API_KEY not found - bot won't work!")

def provide_setup_instructions():
    """Provide setup instructions if integration fails"""
    
    print("\n📝 SETUP INSTRUCTIONS:")
    print("To fix Google Sheets integration:")
    print("\n1. Create a Google Service Account:")
    print("   - Go to: https://console.cloud.google.com/")
    print("   - Create new project or use existing")
    print("   - Enable Google Sheets API")
    print("   - Create Service Account credentials")
    print("   - Download JSON key file")
    
    print("\n2. Set up credentials:")
    print("   Option A: File-based")
    print("   - Place JSON file as 'google-credentials.json' in backend folder")
    print("   - Or set GOOGLE_CREDENTIALS_PATH=/path/to/your/credentials.json")
    
    print("\n   Option B: Environment variable")
    print("   - Set GOOGLE_CREDENTIALS_JSON='{"your": "service_account_json"}'")
    
    print("\n3. Share your Google Sheet with the service account email")
    print("   - Open your master sheet")
    print("   - Click Share")
    print("   - Add service account email (from JSON file)")
    print("   - Give Editor permissions")
    
    print("\n4. Set MASTER_SHEET_ID environment variable")
    print("   - Copy sheet ID from URL: https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")

def main():
    """Run comprehensive health check"""
    
    print("🏥 BMA Social - Google Sheets Integration Health Check")
    print("=" * 60)
    
    # Check credentials
    has_creds = check_credentials()
    
    # Check environment
    check_environment()
    
    # Test sheets access if credentials available
    if has_creds:
        sheets_working = test_sheets_access()
        
        if sheets_working:
            print("\n🎉 Google Sheets integration is working correctly!")
            print("   Your bot should now have access to venue data.")
        else:
            print("\n❌ Google Sheets integration has issues")
            provide_setup_instructions()
    else:
        provide_setup_instructions()
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
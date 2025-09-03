#!/usr/bin/env python3
"""
Test Google Drive integration
Help set up folder IDs and test document search
"""

import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv()

print("=" * 60)
print("Google Drive Integration Test")
print("=" * 60)
print()

try:
    from google_drive_client import drive_client, find_venue_contract, find_troubleshooting_guide
    
    if not drive_client.service:
        print("❌ Google Drive not connected")
        print()
        print("Make sure you have:")
        print("1. Enabled Google Drive API in Google Cloud Console")
        print("2. Service account has Drive API access")
        sys.exit(1)
    
    print("✅ Google Drive client initialized")
    print()
    
    # First, let's list some accessible folders to help find the right IDs
    print("Searching for accessible folders...")
    print("-" * 40)
    
    try:
        # Search for folders the service account can access
        results = drive_client.service.files().list(
            q="mimeType='application/vnd.google-apps.folder' and trashed=false",
            pageSize=20,
            fields="files(id, name)",
            orderBy="name"
        ).execute()
        
        folders = results.get('files', [])
        
        if folders:
            print("Folders accessible to the service account:")
            print()
            for folder in folders:
                print(f"📁 {folder['name']}")
                print(f"   ID: {folder['id']}")
                print()
            
            print("-" * 40)
            print("To use these folders, add to your .env file:")
            print()
            print("GDRIVE_CONTRACTS_FOLDER=<folder_id_for_contracts>")
            print("GDRIVE_TECH_DOCS_FOLDER=<folder_id_for_tech_docs>")
            print()
            print("Then share the folders with the service account:")
            print(f"Share with: {os.getenv('GOOGLE_SERVICE_ACCOUNT_EMAIL', 'your-service-account@project.iam.gserviceaccount.com')}")
            
        else:
            print("❌ No folders found accessible to the service account")
            print()
            print("To set up Google Drive folders:")
            print()
            print("1. Create folders in Google Drive:")
            print("   - 'BMA Contracts' (for venue contracts)")
            print("   - 'BMA Technical Docs' (for manuals and guides)")
            print()
            print("2. Share each folder with your service account:")
            service_account_email = "bma-social-service@bamboo-theorem-399923.iam.gserviceaccount.com"
            print(f"   Share with: {service_account_email}")
            print("   Give 'Viewer' permission")
            print()
            print("3. Get the folder IDs:")
            print("   - Open the folder in Google Drive")
            print("   - Look at the URL: drive.google.com/drive/folders/FOLDER_ID_HERE")
            print("   - Copy the folder ID")
            print()
            print("4. Add to your .env file:")
            print("   GDRIVE_CONTRACTS_FOLDER=your_contracts_folder_id")
            print("   GDRIVE_TECH_DOCS_FOLDER=your_tech_docs_folder_id")
        
        # Test search if folders are configured
        contracts_folder = os.getenv('GDRIVE_CONTRACTS_FOLDER')
        tech_folder = os.getenv('GDRIVE_TECH_DOCS_FOLDER')
        
        if contracts_folder or tech_folder:
            print()
            print("=" * 60)
            print("Testing Document Search")
            print("-" * 40)
            
            # Test contract search
            print("Testing contract search for 'Hilton'...")
            contract_result = find_venue_contract("Hilton")
            if contract_result:
                print(contract_result)
            else:
                print("No contracts found for Hilton")
            
            print()
            
            # Test tech doc search
            print("Testing technical doc search for 'troubleshooting'...")
            tech_result = find_troubleshooting_guide("troubleshooting offline")
            if tech_result:
                print(tech_result)
            else:
                print("No technical docs found")
        
    except Exception as e:
        print(f"Error during testing: {e}")
        print()
        print("This might mean:")
        print("1. Service account doesn't have Drive API access")
        print("2. Folders aren't shared with the service account")
    
except ImportError as e:
    print(f"❌ Could not import Google Drive client: {e}")
    print()
    print("Make sure Drive API is enabled in Google Cloud Console")

print()
print("=" * 60)
print("Next Steps:")
print()
print("1. Create and share folders with service account")
print("2. Add folder IDs to .env file")
print("3. Upload some test contracts and documents")
print("4. Run this test again to verify")
print()
print("Once working, the bot can:")
print("- Find contracts when venues ask about terms")
print("- Provide troubleshooting guides for issues")
print("- Share direct links to relevant documents")
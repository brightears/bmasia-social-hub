#!/usr/bin/env python3
"""
Setup script to configure Google Chat connection for BMA Social Bot
This will help you add the existing BMA Social Support Bot credentials
"""

import os
import json
import sys

def setup_google_chat():
    print("=" * 60)
    print("BMA Social Bot - Google Chat Setup")
    print("=" * 60)
    print("\nYou mentioned the 'BMA Social Support Bot' is already working")
    print("and sending messages to 'BMAsia Working Group' Google Chat.")
    print("\nLet's connect it to the new bot!\n")
    
    # We know the space ID from .env
    space_id = "spaces/AAQA3gAn8GY"
    print(f"✅ Found Space ID: {space_id}")
    
    print("\nTo complete the connection, we need the service account credentials.")
    print("\nYou have 3 options:\n")
    
    print("OPTION 1: Add to .env file (Recommended)")
    print("-" * 40)
    print("Add this line to your .env file:")
    print("GOOGLE_CREDENTIALS_JSON='{paste-your-json-here}'")
    print("\nThe JSON should be from the 'BMA Social Support Bot' service account")
    print("that you already tested successfully.\n")
    
    print("OPTION 2: Copy existing credentials file")
    print("-" * 40)
    print("If you have the credentials file from when you set up")
    print("the 'BMA Social Support Bot', copy it to:")
    print(f"{os.path.dirname(__file__)}/")
    print("And name it one of these:")
    print("  - bamboo-theorem-399923-credentials.json")
    print("  - bma-social-support-bot.json")
    print("  - google-credentials.json\n")
    
    print("OPTION 3: Extract from existing working bot")
    print("-" * 40)
    print("If another bot is already sending notifications successfully,")
    print("check its configuration and copy the credentials.\n")
    
    # Check current status
    print("Current Status:")
    print("-" * 40)
    
    env_has_creds = os.getenv('GOOGLE_CREDENTIALS_JSON') is not None
    print(f"GOOGLE_CREDENTIALS_JSON in .env: {'✅ Yes' if env_has_creds else '❌ No'}")
    
    # Check for credential files
    possible_files = [
        'bamboo-theorem-399923-credentials.json',
        'bma-social-support-bot.json',
        'google-credentials.json',
        'credentials.json'
    ]
    
    found_file = None
    for filename in possible_files:
        if os.path.exists(filename):
            found_file = filename
            break
    
    print(f"Credentials file found: {'✅ ' + found_file if found_file else '❌ No'}")
    print(f"Space ID configured: ✅ {space_id}")
    
    if env_has_creds or found_file:
        print("\n🎉 Google Chat should be working!")
        print("Run test_notifications.py to verify.")
    else:
        print("\n⚠️  Please add credentials using one of the options above.")
        print("\nSince you already have 'BMA Social Support Bot' working,")
        print("you just need to copy those same credentials here.")
    
    print("\n" + "=" * 60)
    
    # Offer to create a template
    create_template = input("\nWould you like me to create a template credentials file? (y/n): ")
    if create_template.lower() == 'y':
        template = {
            "type": "service_account",
            "project_id": "bamboo-theorem-399923",
            "private_key_id": "YOUR_PRIVATE_KEY_ID",
            "private_key": "-----BEGIN PRIVATE KEY-----\nYOUR_PRIVATE_KEY\n-----END PRIVATE KEY-----\n",
            "client_email": "bma-social-service@bamboo-theorem-399923.iam.gserviceaccount.com",
            "client_id": "YOUR_CLIENT_ID",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": "YOUR_CERT_URL"
        }
        
        template_file = "bma-social-support-bot-template.json"
        with open(template_file, 'w') as f:
            json.dump(template, f, indent=2)
        
        print(f"\n✅ Created template: {template_file}")
        print("Replace the YOUR_* values with the actual values from your")
        print("working 'BMA Social Support Bot' credentials.")
        print(f"Then rename it to: bma-social-support-bot.json")

if __name__ == "__main__":
    setup_google_chat()
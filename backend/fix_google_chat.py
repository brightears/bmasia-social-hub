#!/usr/bin/env python3
"""
Diagnose why Google Chat stopped working
"""

import os
import json
from dotenv import load_dotenv

load_dotenv()

print("🔍 Diagnosing Google Chat Connection Issue")
print("=" * 50)

# Check what's configured locally
print("\n1. LOCAL ENVIRONMENT CHECK:")
print("-" * 30)

# Check for credentials JSON
creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON', '')
if creds_json:
    try:
        creds = json.loads(creds_json)
        print(f"✅ GOOGLE_CREDENTIALS_JSON found")
        print(f"   Project: {creds.get('project_id', 'unknown')}")
        print(f"   Service Account: {creds.get('client_email', 'unknown')}")
    except:
        print("❌ GOOGLE_CREDENTIALS_JSON exists but is invalid JSON")
else:
    print("❌ GOOGLE_CREDENTIALS_JSON not found")

# Check for webhook URL
webhook_url = os.getenv('GOOGLE_CHAT_WEBHOOK_URL', '')
if webhook_url:
    print(f"✅ GOOGLE_CHAT_WEBHOOK_URL found: {webhook_url[:50]}...")
else:
    print("❌ GOOGLE_CHAT_WEBHOOK_URL not found")

# Check for space ID
space_id = os.getenv('GCHAT_BMASIA_ALL_SPACE', '')
if space_id:
    print(f"✅ GCHAT_BMASIA_ALL_SPACE found: {space_id}")
else:
    print("❌ GCHAT_BMASIA_ALL_SPACE not found")

print("\n2. WHAT YOU NEED TO FIX THIS:")
print("-" * 30)

if not creds_json and not webhook_url:
    print("\nYou have TWO options to fix this:\n")
    
    print("OPTION A: Use Service Account (how it worked before)")
    print("  The 'BMA Social Support Bot' app uses service account credentials.")
    print("  You need to:")
    print("  1. Get the service account JSON from whoever set it up originally")
    print("  2. Add to Render's environment variables as GOOGLE_CREDENTIALS_JSON")
    print("  3. The JSON should be for: bma-social-service@bamboo-theorem-399923.iam.gserviceaccount.com")
    
    print("\nOPTION B: Use Webhook (simpler, no credentials needed)")
    print("  1. Create a webhook in Google Chat (as shown in the screenshots)")
    print("  2. Add the webhook URL to Render as GOOGLE_CHAT_WEBHOOK_URL")
    print("  3. This is simpler but less feature-rich than service account")

print("\n3. WHY IT STOPPED WORKING:")
print("-" * 30)
print("The service account credentials were likely:")
print("• Not included in the git repository (for security)")
print("• Set as environment variable on Render")
print("• Lost during a redeploy or environment update")
print("• Or the service account lost permissions")

print("\n4. TO FIX ON RENDER:")
print("-" * 30)
print("Go to: https://dashboard.render.com/web/srv-d2m6l0re5dus739fso30/env")
print("Add one of these environment variables:")
print("• GOOGLE_CREDENTIALS_JSON = (the full JSON as a string)")
print("• OR")
print("• GOOGLE_CHAT_WEBHOOK_URL = (the webhook URL from Google Chat)")

print("\n" + "=" * 50)
print("The bot is working fine, it just can't send notifications")
print("to Google Chat without one of these authentication methods.")
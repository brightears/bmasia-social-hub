#!/usr/bin/env python3
"""
Check Google Cloud API Requirements
"""

print("=" * 70)
print("📋 Google Cloud API Requirements Checklist")
print("=" * 70)
print()

print("Please ensure these APIs are ENABLED in your Google Cloud project:")
print()

print("1. Google Sheets API")
print("   → Go to: https://console.cloud.google.com/apis/library")
print("   → Search for: Google Sheets API")
print("   → Click on it and press 'ENABLE'")
print()

print("2. Google Drive API (optional but recommended)")
print("   → Go to: https://console.cloud.google.com/apis/library")
print("   → Search for: Google Drive API")
print("   → Click on it and press 'ENABLE'")
print()

print("-" * 70)
print()
print("Quick Links for your project (bmasia-social-hub):")
print()
print("🔗 Enable Google Sheets API:")
print("   https://console.cloud.google.com/apis/library/sheets.googleapis.com?project=bmasia-social-hub")
print()
print("🔗 Enable Google Drive API:")
print("   https://console.cloud.google.com/apis/library/drive.googleapis.com?project=bmasia-social-hub")
print()
print("🔗 View Enabled APIs:")
print("   https://console.cloud.google.com/apis/dashboard?project=bmasia-social-hub")
print()

print("-" * 70)
print()
print("After enabling the APIs:")
print("1. Wait about 30 seconds for changes to propagate")
print("2. Run: python verify_sheets_setup.py")
print("3. If it still fails, try creating a new service account key")
print()

print("Current Service Account:")
print("bma-social-sheets@bmasia-social-hub.iam.gserviceaccount.com")
print()
print("=" * 70)
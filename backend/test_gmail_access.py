#!/usr/bin/env python3
"""
Test Gmail API access after domain-wide delegation setup
"""

import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv()

print("=" * 60)
print("Testing Gmail API Access")
print("=" * 60)
print()

# Test the Gmail client
try:
    from gmail_client import gmail_client
    
    if not gmail_client.services:
        print("❌ No Gmail services initialized")
        print()
        print("This usually means:")
        print("1. Domain-wide delegation not set up yet")
        print("2. Or the service account needs permission")
        print()
        print("Please complete the setup in Google Admin Console:")
        print("https://admin.google.com/ac/owl/domainwidedelegation")
        print()
        print("Add Client ID: 109302315012481422492")
        print("With scope: https://www.googleapis.com/auth/gmail.readonly")
    else:
        print(f"✅ Gmail client initialized for {len(gmail_client.services)} accounts")
        print()
        
        # Test search for each account
        for email in gmail_client.services.keys():
            print(f"Testing {email}...")
            try:
                # Search for recent emails
                results = gmail_client.search_venue_emails(
                    venue_name="test",
                    days_back=7
                )
                print(f"  ✅ Can access {email}")
                print(f"     Found {len(results)} emails in last 7 days")
            except Exception as e:
                error_msg = str(e)
                if "delegation denied" in error_msg.lower():
                    print(f"  ❌ Delegation not set up for {email}")
                    print("     Please add domain-wide delegation in Google Admin")
                else:
                    print(f"  ❌ Error: {e}")
        
        print()
        print("Testing smart search with Hilton Pattaya...")
        try:
            from smart_email_search import init_smart_search
            smart_searcher = init_smart_search()
            
            # Test with a contract query
            result = smart_searcher.smart_search(
                message="Did we discuss the contract renewal?",
                venue_name="Hilton Pattaya",
                domain="hilton.com"
            )
            
            if result and result.get('found'):
                print(f"✅ Smart search working!")
                print(f"   Found {result.get('count', 0)} relevant emails")
                if result.get('summary'):
                    print(f"   Summary: {result['summary']}")
            else:
                print("📭 No emails found for Hilton Pattaya (this is normal if no recent emails)")
                
        except Exception as e:
            print(f"❌ Smart search error: {e}")
            
except ImportError as e:
    print(f"❌ Could not import Gmail client: {e}")
    print()
    print("Make sure you have installed the required packages:")
    print("pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")

print()
print("=" * 60)
print("Next Steps:")
print()
print("If delegation is working:")
print("  ✅ The bot can now search emails automatically")
print("  ✅ Smart search will activate on relevant keywords")
print()
print("If not working:")
print("  1. Complete domain-wide delegation setup")
print("  2. Wait 5-10 minutes for changes to propagate")
print("  3. Run this test again")
print()
print("Alternative: Use IMAP with existing credentials if no admin access")
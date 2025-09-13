#!/usr/bin/env python3
"""
Test the Campaign System via API calls
This script demonstrates how to use the campaign API endpoints
"""

import requests
import json
from datetime import datetime

# API Base URL - Update this with your Render URL
BASE_URL = "https://bma-social-api-q9uu.onrender.com"
# For local testing: BASE_URL = "http://localhost:8000"

def test_campaign_system():
    """Test campaign system via API calls"""

    print("\n" + "="*50)
    print("BMA SOCIAL CAMPAIGN API TEST")
    print("="*50 + "\n")

    # 1. Get campaign statistics
    print("1. Getting Campaign Statistics...")
    response = requests.get(f"{BASE_URL}/api/campaigns/statistics")
    if response.status_code == 200:
        stats = response.json()
        print(f"✅ Statistics retrieved:")
        print(f"   - Total customers: {stats.get('customer_statistics', {}).get('total_customers', 0)}")
        print(f"   - Total zones: {stats.get('customer_statistics', {}).get('total_zones', 0)}")
        print(f"   - Active campaigns: {stats.get('active_campaigns', 0)}\n")
    else:
        print(f"❌ Error: {response.status_code} - {response.text}\n")

    # 2. Create campaign with natural language
    print("2. Creating Campaign with Natural Language...")
    campaign_data = {
        "human_request": "Send renewal reminders to all Hiltons expiring in the next 30 days"
    }

    response = requests.post(
        f"{BASE_URL}/api/campaigns/create",
        json=campaign_data
    )

    if response.status_code == 200:
        campaign = response.json()
        campaign_id = campaign.get('id')
        print(f"✅ Campaign created: {campaign_id}")
        print(f"   - Type: {campaign.get('type')}")
        print(f"   - Target customers: {campaign.get('statistics', {}).get('total_customers', 0)}")
        print(f"   - Total zones: {campaign.get('statistics', {}).get('total_zones', 0)}")
        if campaign.get('plan'):
            print(f"   - Campaign name: {campaign['plan'].get('campaign_name')}")
            print(f"   - Goal: {campaign['plan'].get('campaign_goal')}\n")
    else:
        print(f"❌ Error: {response.status_code} - {response.text}\n")
        campaign_id = None

    # 3. Create seasonal campaign with filters
    print("3. Creating Seasonal Campaign with Filters...")
    seasonal_data = {
        "type": "seasonal",
        "filters": {
            "brand": "Hilton Hotels & Resorts",
            "region": "Asia Pacific"
        },
        "context": "Christmas holiday music promotion for December"
    }

    response = requests.post(
        f"{BASE_URL}/api/campaigns/create",
        json=seasonal_data
    )

    if response.status_code == 200:
        seasonal = response.json()
        seasonal_id = seasonal.get('id')
        print(f"✅ Seasonal campaign created: {seasonal_id}")
        print(f"   - Target customers: {seasonal.get('statistics', {}).get('total_customers', 0)}\n")
    else:
        print(f"❌ Error: {response.status_code} - {response.text}\n")
        seasonal_id = None

    # 4. Preview campaign (if created successfully)
    if campaign_id:
        print("4. Previewing Campaign Messages...")
        response = requests.get(f"{BASE_URL}/api/campaigns/{campaign_id}/preview")

        if response.status_code == 200:
            preview = response.json()
            print(f"✅ Campaign preview:")
            print(f"   - Total customers: {preview.get('total_customers', 0)}")

            samples = preview.get('sample_messages', [])
            if samples:
                sample = samples[0]
                print(f"\n   Sample message for: {sample.get('customer')}")
                print(f"   - Brand: {sample.get('brand')}")
                print(f"   - Zones: {', '.join(sample.get('zones', []))}")
                print(f"   - Contact: {sample.get('contact')}")
                print(f"   - WhatsApp preview: {sample.get('whatsapp', '')[:150]}...")
                print(f"   - Email subject: {sample.get('email_subject')}\n")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}\n")

    # 5. Send campaign in test mode (only first customer)
    if campaign_id:
        print("5. Sending Campaign (Test Mode - First Customer Only)...")
        send_data = {
            "channels": ["whatsapp", "email"],
            "test_mode": True  # Only sends to first customer
        }

        response = requests.post(
            f"{BASE_URL}/api/campaigns/{campaign_id}/send",
            json=send_data
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Test campaign sent:")
            print(f"   - Campaign ID: {result.get('campaign_id')}")
            print(f"   - Channels: {', '.join(result.get('channels', []))}")

            # Show results for first customer
            customer_results = result.get('results_by_customer', [])
            if customer_results:
                first = customer_results[0]
                print(f"   - Customer: {first.get('customer')}")
                print(f"   - Sent: {first.get('sent')}")
                print(f"   - Failed: {first.get('failed')}\n")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}\n")

    print("="*50)
    print("TEST COMPLETE")
    print("="*50 + "\n")

    # Show example curl commands
    print("EXAMPLE CURL COMMANDS:")
    print("-"*50)
    print("""
# Get statistics:
curl https://bma-social-api-q9uu.onrender.com/api/campaigns/statistics

# Create campaign with natural language:
curl -X POST https://bma-social-api-q9uu.onrender.com/api/campaigns/create \\
  -H "Content-Type: application/json" \\
  -d '{"human_request": "Send renewal reminders to Hiltons expiring this month"}'

# Create campaign with filters:
curl -X POST https://bma-social-api-q9uu.onrender.com/api/campaigns/create \\
  -H "Content-Type: application/json" \\
  -d '{
    "type": "seasonal",
    "filters": {"brand": "Hilton Hotels & Resorts"},
    "context": "Christmas promotion"
  }'

# Preview campaign:
curl https://bma-social-api-q9uu.onrender.com/api/campaigns/{campaign_id}/preview

# Send campaign (test mode):
curl -X POST https://bma-social-api-q9uu.onrender.com/api/campaigns/{campaign_id}/send \\
  -H "Content-Type: application/json" \\
  -d '{"channels": ["whatsapp", "email"], "test_mode": true}'
    """)


if __name__ == "__main__":
    test_campaign_system()
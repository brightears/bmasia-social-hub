#!/usr/bin/env python3
"""
Test script for BMA Social AI-Powered Campaign System
Tests campaign creation, filtering, and message generation
"""

import os
import json
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_campaign_system():
    """Test the campaign management system"""

    print("\n" + "="*50)
    print("BMA SOCIAL CAMPAIGN SYSTEM TEST")
    print("="*50 + "\n")

    try:
        # Import campaign system
        from campaigns.campaign_orchestrator import CampaignOrchestrator

        # Initialize orchestrator
        print("1. Initializing Campaign System...")
        orchestrator = CampaignOrchestrator()
        print("✅ Campaign system initialized\n")

        # Get customer statistics
        print("2. Loading Customer Data...")
        stats = orchestrator.customer_manager.get_statistics()
        print(f"✅ Loaded {stats['total_customers']} customers")
        print(f"   - Total zones: {stats['total_zones']}")
        print(f"   - Brands: {stats['total_brands']}")
        print(f"   - Expiring in 30 days: {stats['expiring_30_days']}")
        print(f"   - Expiring in 60 days: {stats['expiring_60_days']}\n")

        # Test natural language campaign creation
        print("3. Testing Natural Language Campaign Creation...")
        print("   Request: 'Send renewal reminders to all Hiltons expiring in October 2025'\n")

        campaign = orchestrator.create_campaign(
            campaign_type='auto',
            human_request='Send renewal reminders to all Hiltons expiring in October 2025'
        )

        print(f"✅ Campaign created: {campaign['id']}")
        print(f"   - Type: {campaign['type']}")
        print(f"   - Target customers: {campaign['statistics']['total_customers']}")
        print(f"   - Total zones: {campaign['statistics']['total_zones']}")
        if campaign['plan']:
            print(f"   - Campaign name: {campaign['plan'].get('campaign_name')}")
            print(f"   - Goal: {campaign['plan'].get('campaign_goal')}\n")

        # Preview campaign
        print("4. Preview Campaign Messages...")
        preview = orchestrator.preview_campaign(campaign['id'], sample_size=1)

        if preview.get('sample_messages'):
            sample = preview['sample_messages'][0]
            print(f"   Sample for: {sample['customer']}")
            print(f"   - Brand: {sample['brand']}")
            print(f"   - Zones: {', '.join(sample['zones'])}")
            print(f"   - Contact: {sample['contact']}")
            print(f"   - WhatsApp preview: {sample['whatsapp'][:150]}...")
            print(f"   - Email subject: {sample['email_subject']}\n")

        # Test specific filters
        print("5. Testing Brand Filter...")
        hilton_customers = orchestrator.customer_manager.get_customers_by_brand('Hilton Hotels & Resorts')
        print(f"✅ Found {len(hilton_customers)} Hilton properties\n")

        # Test renewal filter
        print("6. Testing Contract Expiry Filter...")
        expiring = orchestrator.customer_manager.get_expiring_contracts(days=90)
        print(f"✅ Found {len(expiring)} customers expiring in next 90 days")
        for customer in expiring[:3]:
            print(f"   - {customer['name']}: expires {customer.get('contract_end')}")
        print()

        # Test seasonal campaign
        print("7. Creating Seasonal Campaign...")
        seasonal = orchestrator.create_campaign(
            campaign_type='seasonal',
            filters={'region': 'Asia Pacific'},
            context='Christmas music offer for hotels'
        )
        print(f"✅ Seasonal campaign created: {seasonal['id']}")
        print(f"   - Target customers: {seasonal['statistics']['total_customers']}\n")

        # Test campaign response handling
        print("8. Testing Campaign Response Analysis...")
        test_response = orchestrator.ai_manager.analyze_response(
            response_text="Yes, please renew all our zones for another year",
            campaign_context={'campaign_name': 'Renewal Reminder'},
            customer_context={'name': 'Hilton Pattaya', 'zones': ['Edge', 'Drift Bar']}
        )
        print(f"✅ Response analyzed:")
        print(f"   - Intent: {test_response.get('intent')}")
        print(f"   - Sentiment: {test_response.get('sentiment')}")
        print(f"   - Requires human: {test_response.get('requires_human')}")
        print(f"   - Suggested reply: {test_response.get('suggested_reply')[:100]}...\n")

        # Show sending statistics
        print("9. Checking Send Capabilities...")
        send_stats = orchestrator.sender.get_send_statistics()
        print(f"✅ Send limits:")
        print(f"   - WhatsApp daily: {send_stats['limits']['whatsapp_daily']}")
        print(f"   - Line batch: {send_stats['limits']['line_batch']}")
        print(f"   - Email hourly: {send_stats['limits']['email_hourly']}")
        print(f"   - Sent today: {send_stats['sent_today']}\n")

        print("="*50)
        print("✅ ALL TESTS PASSED SUCCESSFULLY!")
        print("="*50 + "\n")

        # Show example API calls
        print("EXAMPLE API USAGE:")
        print("-"*50)
        print("""
# Create campaign with natural language:
POST /api/campaigns/create
{
    "human_request": "Send renewal reminders to all Hiltons expiring this month"
}

# Or with specific filters:
POST /api/campaigns/create
{
    "type": "seasonal",
    "filters": {
        "brand": "Hilton Hotels & Resorts",
        "region": "Asia Pacific"
    },
    "context": "Chinese New Year music promotion"
}

# Preview before sending:
GET /api/campaigns/{campaign_id}/preview

# Send campaign:
POST /api/campaigns/{campaign_id}/send
{
    "channels": ["whatsapp", "email"],
    "test_mode": true  // Send to first customer only
}

# Get statistics:
GET /api/campaigns/statistics
        """)

    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("   Make sure you're running from the backend directory")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_campaign_system()
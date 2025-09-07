#!/usr/bin/env python3
"""
Test if Google Chat notifications work on the live Render deployment
"""

import requests
import json

# Your Render API endpoint
API_URL = "https://bma-social-api-q9uu.onrender.com"

def test_whatsapp_webhook():
    """Simulate a WhatsApp message that should trigger Google Chat notification"""
    
    # Simulate a WhatsApp message asking to change playlist
    webhook_data = {
        "entry": [{
            "id": "ENTRY_ID",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "display_phone_number": "1234567890",
                        "phone_number_id": "742462142273418"
                    },
                    "contacts": [{
                        "profile": {"name": "Test User"},
                        "wa_id": "60123456789"
                    }],
                    "messages": [{
                        "from": "60123456789",
                        "id": "test_message_id",
                        "timestamp": "1234567890",
                        "text": {"body": "Can you change the playlist to Jazz at my venue?"},
                        "type": "text"
                    }]
                },
                "field": "messages"
            }]
        }]
    }
    
    print("📤 Sending test WhatsApp message to trigger Google Chat...")
    print(f"   URL: {API_URL}/webhooks/whatsapp")
    print(f"   Message: 'Can you change the playlist to Jazz at my venue?'")
    
    try:
        response = requests.post(
            f"{API_URL}/webhooks/whatsapp",
            json=webhook_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"\n📥 Response Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ Webhook processed successfully!")
            print("\n🔔 Check your Google Chat 'BMAsia Working Group' space")
            print("   You should see a notification about the playlist change request")
        else:
            print(f"❌ Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Failed to connect: {e}")

def test_health():
    """First check if the API is running"""
    print("🏥 Checking API health...")
    try:
        response = requests.get(f"{API_URL}/health")
        if response.status_code == 200:
            print("✅ API is healthy and running")
            return True
        else:
            print(f"❌ API health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        return False

if __name__ == "__main__":
    print("Testing Live Google Chat Integration")
    print("=" * 40)
    
    if test_health():
        print()
        test_whatsapp_webhook()
    else:
        print("\n⚠️  Fix the API connection first")
#!/usr/bin/env python3
"""
Test the two-way communication between WhatsApp and Google Chat
"""

import requests
import json
import time

# Your Render API endpoint
API_URL = "https://bma-social-api-q9uu.onrender.com"

def test_whatsapp_to_gchat():
    """Simulate a WhatsApp customer message"""
    
    print("🧪 Testing Two-Way Communication System")
    print("=" * 50)
    
    # Simulate a WhatsApp message from a customer
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
                        "profile": {"name": "John from Café Milano"},
                        "wa_id": "60123456789"
                    }],
                    "messages": [{
                        "from": "60123456789",
                        "id": f"test_{int(time.time())}",
                        "timestamp": str(int(time.time())),
                        "text": {"body": "Hi! The music stopped playing at our venue. Can someone help?"},
                        "type": "text"
                    }]
                },
                "field": "messages"
            }]
        }]
    }
    
    print("📤 Sending test customer message:")
    print("   Customer: John from Café Milano (+60123456789)")
    print("   Message: 'Hi! The music stopped playing at our venue. Can someone help?'")
    print()
    
    try:
        response = requests.post(
            f"{API_URL}/webhooks/whatsapp",
            json=webhook_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            print("✅ Message processed successfully!")
            print()
            print("📱 Check 'BMA Customer Support' space in Google Chat")
            print("   You should see:")
            print("   - A new thread for John from Café Milano")
            print("   - The customer's message")
            print("   - Instructions to reply in the thread")
            print()
            print("💬 To test two-way communication:")
            print("   1. Reply in the Google Chat thread")
            print("   2. The reply will be sent back to WhatsApp")
            print("   3. Check the logs to see if it was sent successfully")
            
        else:
            print(f"❌ Error: HTTP {response.status_code}")
            print(f"   Response: {response.text}")
            
    except requests.exceptions.Timeout:
        print("⏱️  Request timed out (bot might be processing)")
        print("   Check Google Chat anyway - message might have been sent")
    except Exception as e:
        print(f"❌ Failed: {e}")

def check_health():
    """Check if the API is running"""
    print("🏥 Checking API health...")
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ API is healthy")
            return True
        else:
            print(f"❌ API health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        return False

if __name__ == "__main__":
    if check_health():
        print()
        test_whatsapp_to_gchat()
        print()
        print("🔍 Next Steps:")
        print("1. Check 'BMA Customer Support' space for the message")
        print("2. Reply in the thread to test two-way communication")
        print("3. Monitor logs at: https://dashboard.render.com/web/srv-d2m6l0re5dus739fso30/logs")
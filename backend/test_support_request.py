#!/usr/bin/env python3
"""
Test with a support request that should definitely trigger Google Chat notification
"""

import requests
import json
import time

# Your Render API endpoint
API_URL = "https://bma-social-api-q9uu.onrender.com"

def test_support_request():
    """Simulate a WhatsApp message that needs human support"""
    
    print("🧪 Testing Google Chat Notification - Support Request")
    print("=" * 50)
    
    # Simulate a message that the bot can't handle
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
                        "profile": {"name": "Mike from Bar Central"},
                        "wa_id": "60177778888"
                    }],
                    "messages": [{
                        "from": "60177778888",
                        "id": f"test_{int(time.time())}",
                        "timestamp": str(int(time.time())),
                        "text": {"body": "Our music system is completely broken and we need urgent help! Nothing is playing at all!"},
                        "type": "text"
                    }]
                },
                "field": "messages"
            }]
        }]
    }
    
    print("📤 Sending urgent support request:")
    print("   Customer: Mike from Bar Central")
    print("   Phone: +60177778888")
    print("   Message: 'Our music system is completely broken...'")
    print()
    print("This should DEFINITELY trigger a Google Chat notification because:")
    print("- It's an urgent technical issue")
    print("- Bot can't fix broken systems")
    print("- Requires human intervention")
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
            print("🚨 CHECK 'BMA Customer Support' space NOW!")
            print("   You should see an URGENT notification about:")
            print("   - Broken music system at Bar Central")
            print("   - Mike needs immediate assistance")
            print()
            print("If you see it: The integration is working! 🎉")
            print("If not: There's still a permission/configuration issue")
            
        else:
            print(f"❌ Error: HTTP {response.status_code}")
            print(f"   Response: {response.text}")
            
    except requests.exceptions.Timeout:
        print("⏱️  Request timed out")
    except Exception as e:
        print(f"❌ Failed: {e}")

if __name__ == "__main__":
    test_support_request()
    print()
    print("📊 Monitor logs at:")
    print("https://dashboard.render.com/web/srv-d2m6l0re5dus739fso30/logs")
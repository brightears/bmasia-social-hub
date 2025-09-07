#!/usr/bin/env python3
"""
Test with a playlist change request that should trigger Google Chat notification
"""

import requests
import json
import time

# Your Render API endpoint
API_URL = "https://bma-social-api-q9uu.onrender.com"

def test_playlist_change():
    """Simulate a WhatsApp message requesting playlist change"""
    
    print("🧪 Testing Google Chat Notification")
    print("=" * 50)
    
    # Simulate a WhatsApp message requesting a playlist change
    # This should trigger a Google Chat notification
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
                        "profile": {"name": "Sarah from The Coffee House"},
                        "wa_id": "60198765432"
                    }],
                    "messages": [{
                        "from": "60198765432",
                        "id": f"test_{int(time.time())}",
                        "timestamp": str(int(time.time())),
                        "text": {"body": "Hi, can you please change our playlist to Jazz? We're The Coffee House venue."},
                        "type": "text"
                    }]
                },
                "field": "messages"
            }]
        }]
    }
    
    print("📤 Sending playlist change request:")
    print("   Customer: Sarah from The Coffee House")
    print("   Phone: +60198765432")
    print("   Message: 'Hi, can you please change our playlist to Jazz?'")
    print()
    print("This should trigger a Google Chat notification because:")
    print("- It's requesting a playlist change (which requires licensing)")
    print("- Bot can't do this automatically")
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
            print("📱 NOW CHECK 'BMA Customer Support' space in Google Chat")
            print("   You should see:")
            print("   - A notification about playlist change request")
            print("   - Customer details (Sarah from The Coffee House)")
            print("   - The request that needs manual handling")
            print()
            print("💬 If you see the message in Google Chat:")
            print("   Try replying to test two-way communication!")
            
        else:
            print(f"❌ Error: HTTP {response.status_code}")
            print(f"   Response: {response.text}")
            
    except requests.exceptions.Timeout:
        print("⏱️  Request timed out (bot might be processing)")
        print("   Check Google Chat anyway - notification might have been sent")
    except Exception as e:
        print(f"❌ Failed: {e}")

if __name__ == "__main__":
    print("Testing Playlist Change Request (Should trigger Google Chat)")
    print()
    test_playlist_change()
    print()
    print("📊 Monitor logs at:")
    print("https://dashboard.render.com/web/srv-d2m6l0re5dus739fso30/logs")
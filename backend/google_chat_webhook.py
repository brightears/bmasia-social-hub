"""
Google Chat Webhook Integration for BMA Social
Uses webhook URLs instead of service account credentials
"""

import os
import json
import logging
import requests
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class GoogleChatWebhook:
    """Send notifications to Google Chat via webhook URL"""
    
    def __init__(self):
        # Get webhook URL from environment
        # This is the webhook URL from your "BMA Social Support Bot" in Google Chat
        self.webhook_url = os.getenv('GOOGLE_CHAT_WEBHOOK_URL', '')
        
        if not self.webhook_url:
            logger.warning("GOOGLE_CHAT_WEBHOOK_URL not configured")
            logger.warning("To get webhook URL:")
            logger.warning("1. Go to Google Chat > BMAsia Working Group")
            logger.warning("2. Click space name > Manage webhooks")
            logger.warning("3. Find 'BMA Social Support Bot' and copy its URL")
            logger.warning("4. Add to .env: GOOGLE_CHAT_WEBHOOK_URL='https://chat.googleapis.com/v1/spaces/...'")
        else:
            logger.info("✅ Google Chat webhook configured")
    
    def send_notification(
        self,
        message: str,
        venue_name: str = None,
        venue_data: Dict = None,
        user_info: Dict = None,
        priority: str = "Normal"
    ) -> bool:
        """
        Send a notification to Google Chat via webhook
        
        Args:
            message: The message or issue description
            venue_name: Name of the venue
            venue_data: Additional venue information
            user_info: User information (phone, platform)
            priority: Priority level (Critical, High, Normal)
        
        Returns:
            True if notification sent successfully
        """
        
        if not self.webhook_url:
            logger.error("Google Chat webhook URL not configured")
            return False
        
        try:
            # Build the message card
            card_message = self._build_card_message(
                message, venue_name, venue_data, user_info, priority
            )
            
            # Send to Google Chat webhook
            response = requests.post(
                self.webhook_url,
                json=card_message,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Google Chat notification sent for {venue_name}")
                return True
            else:
                logger.error(f"Failed to send notification: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending Google Chat notification: {e}")
            return False
    
    def _build_card_message(
        self,
        message: str,
        venue_name: str,
        venue_data: Dict,
        user_info: Dict,
        priority: str
    ) -> Dict:
        """Build a formatted message card for Google Chat"""
        
        # Priority emojis
        priority_emojis = {
            "Critical": "🔴",
            "High": "🟡", 
            "Normal": "🟢",
            "Info": "ℹ️"
        }
        
        # Determine department based on message content
        department = self._determine_department(message)
        
        # Current timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Build the card
        card = {
            "cards": [
                {
                    "header": {
                        "title": f"{priority_emojis.get(priority, '🟢')} {department} Request",
                        "subtitle": f"{venue_name or 'Unknown Venue'} - {timestamp}"
                    },
                    "sections": [
                        {
                            "widgets": [
                                {
                                    "textParagraph": {
                                        "text": f"<b>Request:</b> {message}"
                                    }
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        
        # Add venue details if available
        # Only show venue details if we're confident about the venue
        if venue_data and not venue_name.startswith('Uncertain:'):
            venue_widgets = []

            if venue_data.get('zones'):
                zones_text = ', '.join(venue_data['zones']) if isinstance(venue_data['zones'], list) else str(venue_data['zones'])
                venue_widgets.append({
                    "keyValue": {
                        "topLabel": "Zones",
                        "content": zones_text
                    }
                })

            if venue_data.get('contract_end'):
                venue_widgets.append({
                    "keyValue": {
                        "topLabel": "Contract Ends",
                        "content": venue_data['contract_end']
                    }
                })

            if venue_widgets:
                card["cards"][0]["sections"].append({
                    "widgets": venue_widgets
                })
        
        # Add user info if available
        if user_info:
            user_widgets = []
            
            if user_info.get('phone'):
                user_widgets.append({
                    "keyValue": {
                        "topLabel": "Contact",
                        "content": user_info['phone']
                    }
                })
            
            if user_info.get('platform'):
                user_widgets.append({
                    "keyValue": {
                        "topLabel": "Platform",
                        "content": user_info['platform']
                    }
                })
            
            if user_widgets:
                card["cards"][0]["sections"].append({
                    "widgets": user_widgets
                })
        
        return card
    
    def _determine_department(self, message: str) -> str:
        """Determine department based on message content"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['playlist', 'music', 'genre', 'song', 'volume']):
            return "🎨 Music Design"
        elif any(word in message_lower for word in ['offline', 'broken', 'not working', 'technical', 'error']):
            return "⚙️ Operations"
        elif any(word in message_lower for word in ['contract', 'renewal', 'pricing', 'cancel']):
            return "💰 Sales"
        elif any(word in message_lower for word in ['payment', 'invoice', 'billing']):
            return "💳 Finance"
        else:
            return "📢 General"

# Create a global instance
google_chat_webhook = GoogleChatWebhook()
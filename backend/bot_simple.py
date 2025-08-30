"""
Simple bot module for processing messages with Gemini AI
No database dependencies - just AI responses
"""

import os
import logging
import json
import requests
from typing import Dict, Any, Optional
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Try to import Gemini, but make it optional
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    genai = None
    GEMINI_AVAILABLE = False
    logger.warning("google-generativeai not installed - using fallback responses")

# Configure Gemini if available
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_AVAILABLE and GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_GEMINI_API_KEY_HERE":
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    AI_ENABLED = True
    logger.info("✅ Gemini AI configured successfully")
else:
    model = None
    AI_ENABLED = False
    if not GEMINI_AVAILABLE:
        logger.warning("⚠️ google-generativeai package not installed")
    else:
        logger.warning("⚠️ Gemini API key not configured - using fallback responses")

# WhatsApp configuration
WHATSAPP_API_URL = "https://graph.facebook.com/v17.0"
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")

# LINE configuration
LINE_API_URL = "https://api.line.me/v2/bot"
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")


class SimpleBot:
    """Simple bot for handling messages"""
    
    def __init__(self):
        self.system_prompt = """You are BMA Social AI Assistant, helping venue staff with their music systems.
        You support venues using Soundtrack Your Brand music players.
        
        Key capabilities:
        - Troubleshoot music playback issues
        - Guide through volume and playlist changes
        - Help with zone management
        - Provide quick solutions for common problems
        
        Keep responses concise and helpful. If you need more information to help, ask specific questions.
        Always be professional and friendly."""
    
    def generate_response(self, user_message: str, user_name: str = "User") -> str:
        """Generate AI response to user message"""
        
        if not AI_ENABLED:
            # Fallback responses when Gemini is not configured
            return self._get_fallback_response(user_message)
        
        try:
            # Create conversation context
            prompt = f"""System: {self.system_prompt}
            
User ({user_name}): {user_message}
            
Assistant: """
            
            # Generate response with Gemini
            response = model.generate_content(prompt)
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            return self._get_fallback_response(user_message)
    
    def _get_fallback_response(self, message: str) -> str:
        """Get fallback response when AI is not available"""
        message_lower = message.lower()
        
        # Common troubleshooting responses
        if "no music" in message_lower or "not playing" in message_lower or "stopped" in message_lower:
            return "I can help you troubleshoot the music playback issue. Please check:\n1. Is the player device powered on?\n2. Is the internet connection working?\n3. Try restarting the player by unplugging it for 10 seconds.\n\nIf the issue persists, I'll escalate this to our technical team."
        
        elif "volume" in message_lower:
            return "To adjust the volume:\n1. Open the Soundtrack app\n2. Go to your zone\n3. Use the volume slider to adjust\n\nNeed help finding the app or accessing your zone?"
        
        elif "playlist" in message_lower or "music" in message_lower:
            return "For playlist changes:\n1. Open the Soundtrack app\n2. Browse or search for playlists\n3. Select and apply to your zone\n\nWould you like help finding a specific type of music?"
        
        elif "hello" in message_lower or "hi" in message_lower:
            return "Hello! I'm the BMA Social AI Assistant. I can help you with:\n• Music playback issues\n• Volume control\n• Playlist changes\n• Zone management\n\nWhat can I help you with today?"
        
        elif "help" in message_lower:
            return "I can assist with:\n• Troubleshooting music playback\n• Volume adjustments\n• Changing playlists\n• Zone configuration\n• Technical support\n\nWhat specific issue are you experiencing?"
        
        else:
            return "I understand you need assistance. Could you please describe:\n1. What issue are you experiencing?\n2. Which zone or player is affected?\n3. When did this start?\n\nThis will help me provide the best solution."


class MessageSender:
    """Send messages via WhatsApp and LINE"""
    
    @staticmethod
    def send_whatsapp_message(to_number: str, message: str) -> bool:
        """Send WhatsApp message"""
        if not WHATSAPP_ACCESS_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
            logger.error("WhatsApp credentials not configured")
            return False
        
        try:
            url = f"{WHATSAPP_API_URL}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
            headers = {
                "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
                "Content-Type": "application/json"
            }
            
            # WhatsApp message payload
            payload = {
                "messaging_product": "whatsapp",
                "to": to_number,
                "type": "text",
                "text": {
                    "body": message
                }
            }
            
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                message_id = result.get("messages", [{}])[0].get("id")
                logger.info(f"WhatsApp message sent successfully: {message_id}")
                return True
            else:
                logger.error(f"Failed to send WhatsApp message: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {e}")
            return False
    
    @staticmethod
    def send_line_message(reply_token: str, message: str) -> bool:
        """Send LINE reply message"""
        if not LINE_CHANNEL_ACCESS_TOKEN:
            logger.error("LINE credentials not configured")
            return False
        
        try:
            url = f"{LINE_API_URL}/message/reply"
            headers = {
                "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
                "Content-Type": "application/json"
            }
            
            # LINE message payload
            payload = {
                "replyToken": reply_token,
                "messages": [
                    {
                        "type": "text",
                        "text": message
                    }
                ]
            }
            
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                logger.info("LINE message sent successfully")
                return True
            else:
                logger.error(f"Failed to send LINE message: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending LINE message: {e}")
            return False
    
    @staticmethod
    def send_line_push_message(user_id: str, message: str) -> bool:
        """Send LINE push message (not a reply)"""
        if not LINE_CHANNEL_ACCESS_TOKEN:
            logger.error("LINE credentials not configured")
            return False
        
        try:
            url = f"{LINE_API_URL}/message/push"
            headers = {
                "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
                "Content-Type": "application/json"
            }
            
            # LINE push message payload
            payload = {
                "to": user_id,
                "messages": [
                    {
                        "type": "text",
                        "text": message
                    }
                ]
            }
            
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                logger.info("LINE push message sent successfully")
                return True
            else:
                logger.error(f"Failed to send LINE push message: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending LINE push message: {e}")
            return False


# Create global instances
bot = SimpleBot()
sender = MessageSender()
"""
WhatsApp Business API Integration

Handles sending and receiving messages via WhatsApp Business API.
Supports both Cloud API and On-Premise deployment.
"""

import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import aiohttp
import hashlib
import hmac

from app.config import settings
from app.core.redis import redis_manager

logger = logging.getLogger(__name__)


class WhatsAppClient:
    """
    WhatsApp Business API client for message handling.
    Designed for high-volume messaging with rate limiting.
    """
    
    def __init__(self):
        self.api_url = settings.whatsapp_api_url
        self.access_token = settings.whatsapp_access_token
        self.phone_number_id = settings.whatsapp_phone_number_id
        self.webhook_verify_token = settings.whatsapp_webhook_verify_token
        self.app_secret = settings.whatsapp_app_secret
        
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Rate limiting: 1000 messages per second (WhatsApp limit)
        self.rate_limit = 1000
        self.rate_window = 1  # seconds
    
    async def initialize(self):
        """Initialize HTTP session"""
        self.session = aiohttp.ClientSession(
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            }
        )
        logger.info("WhatsApp client initialized")
    
    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
    
    async def send_message(
        self,
        to: str,
        message: str,
        conversation_id: Optional[str] = None,
        reply_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send text message via WhatsApp.
        
        Args:
            to: Recipient phone number (with country code)
            message: Message text
            conversation_id: Internal conversation ID for tracking
            reply_to: Message ID to reply to
            
        Returns:
            API response with message ID
        """
        # Check rate limit
        if not await self._check_rate_limit(to):
            raise Exception("Rate limit exceeded for WhatsApp messages")
        
        # Prepare message payload
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": message
            }
        }
        
        # Add context if replying
        if reply_to:
            payload["context"] = {
                "message_id": reply_to
            }
        
        # Send message
        url = f"{self.api_url}/{self.phone_number_id}/messages"
        
        try:
            async with self.session.post(url, json=payload) as response:
                response.raise_for_status()
                result = await response.json()
                
                # Log successful send
                await self._log_message_sent(
                    to=to,
                    message_id=result.get("messages", [{}])[0].get("id"),
                    conversation_id=conversation_id
                )
                
                return result
                
        except Exception as e:
            logger.error(f"Failed to send WhatsApp message to {to}: {e}")
            raise
    
    async def send_template(
        self,
        to: str,
        template_name: str,
        language_code: str = "en",
        components: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Send template message (for initial contact or notifications).
        
        Args:
            to: Recipient phone number
            template_name: Pre-approved template name
            language_code: Language code for template
            components: Template parameters
            
        Returns:
            API response
        """
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {
                    "code": language_code
                }
            }
        }
        
        if components:
            payload["template"]["components"] = components
        
        url = f"{self.api_url}/{self.phone_number_id}/messages"
        
        async with self.session.post(url, json=payload) as response:
            response.raise_for_status()
            return await response.json()
    
    async def send_interactive(
        self,
        to: str,
        body: str,
        buttons: List[Dict[str, str]],
        header: Optional[str] = None,
        footer: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send interactive message with buttons.
        
        Args:
            to: Recipient phone number
            body: Message body
            buttons: List of button options
            header: Optional header text
            footer: Optional footer text
            
        Returns:
            API response
        """
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {
                    "text": body
                },
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {
                                "id": btn.get("id", str(i)),
                                "title": btn.get("title", "Option")[:20]  # Max 20 chars
                            }
                        }
                        for i, btn in enumerate(buttons[:3])  # Max 3 buttons
                    ]
                }
            }
        }
        
        if header:
            payload["interactive"]["header"] = {
                "type": "text",
                "text": header
            }
        
        if footer:
            payload["interactive"]["footer"] = {
                "text": footer
            }
        
        url = f"{self.api_url}/{self.phone_number_id}/messages"
        
        async with self.session.post(url, json=payload) as response:
            response.raise_for_status()
            return await response.json()
    
    async def mark_as_read(self, message_id: str) -> bool:
        """
        Mark message as read.
        
        Args:
            message_id: WhatsApp message ID
            
        Returns:
            Success status
        """
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id
        }
        
        url = f"{self.api_url}/{self.phone_number_id}/messages"
        
        try:
            async with self.session.post(url, json=payload) as response:
                response.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"Failed to mark message as read: {e}")
            return False
    
    def verify_webhook(self, signature: str, payload: bytes) -> bool:
        """
        Verify webhook signature from WhatsApp.
        
        Args:
            signature: X-Hub-Signature-256 header value
            payload: Raw request body
            
        Returns:
            True if signature is valid
        """
        if not signature or not signature.startswith("sha256="):
            return False
        
        expected_signature = hmac.new(
            self.app_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        provided_signature = signature.replace("sha256=", "")
        
        return hmac.compare_digest(expected_signature, provided_signature)
    
    async def process_webhook(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process incoming webhook from WhatsApp.
        
        Args:
            data: Webhook payload
            
        Returns:
            Processed message data for queue
        """
        entry = data.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        
        # Handle different webhook types
        if "messages" in value:
            # Incoming message
            message = value["messages"][0]
            contact = value["contacts"][0]
            
            return {
                "type": "message",
                "platform": "whatsapp",
                "message_id": message.get("id"),
                "from": message.get("from"),
                "contact_name": contact.get("profile", {}).get("name"),
                "content": self._extract_message_content(message),
                "content_type": message.get("type"),
                "timestamp": message.get("timestamp"),
                "context": message.get("context"),
            }
        
        elif "statuses" in value:
            # Message status update
            status = value["statuses"][0]
            
            return {
                "type": "status",
                "platform": "whatsapp",
                "message_id": status.get("id"),
                "recipient": status.get("recipient_id"),
                "status": status.get("status"),
                "timestamp": status.get("timestamp"),
            }
        
        return {"type": "unknown", "data": data}
    
    def _extract_message_content(self, message: Dict) -> str:
        """Extract text content from message"""
        msg_type = message.get("type")
        
        if msg_type == "text":
            return message.get("text", {}).get("body", "")
        elif msg_type == "interactive":
            return message.get("interactive", {}).get("button_reply", {}).get("title", "")
        elif msg_type == "button":
            return message.get("button", {}).get("text", "")
        else:
            return f"[{msg_type} message]"
    
    async def _check_rate_limit(self, recipient: str) -> bool:
        """Check if we can send message within rate limits"""
        key = f"whatsapp:rate:{recipient}"
        
        # Use Redis to track rate limit
        allowed, remaining = await redis_manager.check_rate_limit(
            identifier=key,
            limit=self.rate_limit,
            window=self.rate_window
        )
        
        if not allowed:
            logger.warning(f"Rate limit reached for WhatsApp recipient {recipient}")
        
        return allowed
    
    async def _log_message_sent(
        self,
        to: str,
        message_id: str,
        conversation_id: Optional[str]
    ):
        """Log sent message for tracking"""
        log_data = {
            "platform": "whatsapp",
            "to": to,
            "message_id": message_id,
            "conversation_id": conversation_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        # Store in Redis for recent activity
        key = f"whatsapp:sent:{datetime.utcnow().strftime('%Y%m%d')}"
        await redis_manager.redis.zadd(
            key,
            {json.dumps(log_data): datetime.utcnow().timestamp()}
        )
        await redis_manager.redis.expire(key, 86400 * 7)  # 7 days retention
    
    async def get_profile(self, phone_number: str) -> Dict[str, Any]:
        """
        Get WhatsApp profile information.
        
        Args:
            phone_number: Phone number to query
            
        Returns:
            Profile data
        """
        url = f"{self.api_url}/{phone_number}"
        
        async with self.session.get(url) as response:
            response.raise_for_status()
            return await response.json()
    
    async def upload_media(self, file_path: str, mime_type: str) -> str:
        """
        Upload media file for sending.
        
        Args:
            file_path: Path to media file
            mime_type: MIME type of file
            
        Returns:
            Media ID for sending
        """
        url = f"{self.api_url}/{self.phone_number_id}/media"
        
        data = aiohttp.FormData()
        data.add_field("messaging_product", "whatsapp")
        data.add_field("type", mime_type)
        
        with open(file_path, "rb") as f:
            data.add_field("file", f, filename=file_path.split("/")[-1])
        
        async with self.session.post(url, data=data) as response:
            response.raise_for_status()
            result = await response.json()
            return result.get("id")
    
    async def send_media(
        self,
        to: str,
        media_id: str,
        media_type: str,
        caption: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send media message.
        
        Args:
            to: Recipient phone number
            media_id: Media ID from upload
            media_type: Type of media (image, video, audio, document)
            caption: Optional caption
            
        Returns:
            API response
        """
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": media_type,
            media_type: {
                "id": media_id
            }
        }
        
        if caption and media_type in ["image", "video", "document"]:
            payload[media_type]["caption"] = caption
        
        url = f"{self.api_url}/{self.phone_number_id}/messages"
        
        async with self.session.post(url, json=payload) as response:
            response.raise_for_status()
            return await response.json()


# Global WhatsApp client instance
whatsapp_client = WhatsAppClient()
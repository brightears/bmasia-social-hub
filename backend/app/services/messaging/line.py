"""
LINE Messaging API Integration

Handles sending and receiving messages via LINE Messaging API.
Supports rich messages, flex messages, and quick replies.
"""

import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import aiohttp
import hashlib
import hmac
import base64

from app.config import settings
from app.core.redis import redis_manager

logger = logging.getLogger(__name__)


class LineClient:
    """
    LINE Messaging API client for message handling.
    Supports both push and reply messages.
    """
    
    def __init__(self):
        self.api_url = "https://api.line.me/v2/bot"
        self.channel_access_token = settings.line_channel_access_token
        self.channel_secret = settings.line_channel_secret
        
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Rate limiting: 500 requests per second (LINE limit)
        self.rate_limit = 500
        self.rate_window = 1  # seconds
    
    async def initialize(self):
        """Initialize HTTP session"""
        self.session = aiohttp.ClientSession(
            headers={
                "Authorization": f"Bearer {self.channel_access_token}",
                "Content-Type": "application/json",
            }
        )
        logger.info("LINE client initialized")
    
    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
    
    async def send_message(
        self,
        to: str,
        message: str,
        conversation_id: Optional[str] = None,
        reply_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send text message via LINE.
        
        Args:
            to: User ID or Group ID
            message: Message text
            conversation_id: Internal conversation ID for tracking
            reply_token: Reply token for reply messages
            
        Returns:
            API response
        """
        # Check rate limit
        if not await self._check_rate_limit(to):
            raise Exception("Rate limit exceeded for LINE messages")
        
        # Prepare message object
        message_obj = {
            "type": "text",
            "text": message
        }
        
        # Use reply or push based on token availability
        if reply_token:
            return await self._reply_message(reply_token, [message_obj])
        else:
            return await self._push_message(to, [message_obj])
    
    async def _reply_message(
        self,
        reply_token: str,
        messages: List[Dict]
    ) -> Dict[str, Any]:
        """
        Send reply message (within 30 seconds of receiving).
        
        Args:
            reply_token: Reply token from webhook
            messages: List of message objects (max 5)
            
        Returns:
            API response
        """
        url = f"{self.api_url}/message/reply"
        
        payload = {
            "replyToken": reply_token,
            "messages": messages[:5]  # LINE allows max 5 messages
        }
        
        try:
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    return {"success": True}
                else:
                    error = await response.text()
                    logger.error(f"LINE reply failed: {error}")
                    raise Exception(f"LINE API error: {error}")
                    
        except Exception as e:
            logger.error(f"Failed to send LINE reply: {e}")
            raise
    
    async def _push_message(
        self,
        to: str,
        messages: List[Dict]
    ) -> Dict[str, Any]:
        """
        Send push message (proactive message).
        
        Args:
            to: User ID or Group ID
            messages: List of message objects (max 5)
            
        Returns:
            API response
        """
        url = f"{self.api_url}/message/push"
        
        payload = {
            "to": to,
            "messages": messages[:5]
        }
        
        try:
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    return {"success": True}
                else:
                    error = await response.text()
                    logger.error(f"LINE push failed: {error}")
                    raise Exception(f"LINE API error: {error}")
                    
        except Exception as e:
            logger.error(f"Failed to send LINE push message: {e}")
            raise
    
    async def send_flex_message(
        self,
        to: str,
        alt_text: str,
        contents: Dict,
        reply_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send flex message (custom layout).
        
        Args:
            to: User ID
            alt_text: Alternative text for notifications
            contents: Flex message contents (bubble or carousel)
            reply_token: Optional reply token
            
        Returns:
            API response
        """
        message = {
            "type": "flex",
            "altText": alt_text,
            "contents": contents
        }
        
        if reply_token:
            return await self._reply_message(reply_token, [message])
        else:
            return await self._push_message(to, [message])
    
    async def send_quick_reply(
        self,
        to: str,
        message: str,
        items: List[Dict[str, str]],
        reply_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send message with quick reply buttons.
        
        Args:
            to: User ID
            message: Message text
            items: List of quick reply items
            reply_token: Optional reply token
            
        Returns:
            API response
        """
        message_obj = {
            "type": "text",
            "text": message,
            "quickReply": {
                "items": [
                    {
                        "type": "action",
                        "action": {
                            "type": "message",
                            "label": item.get("label", "Option")[:20],
                            "text": item.get("text", item.get("label", ""))
                        }
                    }
                    for item in items[:13]  # Max 13 items
                ]
            }
        }
        
        if reply_token:
            return await self._reply_message(reply_token, [message_obj])
        else:
            return await self._push_message(to, [message_obj])
    
    async def send_template(
        self,
        to: str,
        alt_text: str,
        template: Dict,
        reply_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send template message (buttons, confirm, carousel).
        
        Args:
            to: User ID
            alt_text: Alternative text
            template: Template object
            reply_token: Optional reply token
            
        Returns:
            API response
        """
        message = {
            "type": "template",
            "altText": alt_text,
            "template": template
        }
        
        if reply_token:
            return await self._reply_message(reply_token, [message])
        else:
            return await self._push_message(to, [message])
    
    async def send_image(
        self,
        to: str,
        original_url: str,
        preview_url: str,
        reply_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send image message.
        
        Args:
            to: User ID
            original_url: Full-size image URL (HTTPS)
            preview_url: Preview image URL (HTTPS)
            reply_token: Optional reply token
            
        Returns:
            API response
        """
        message = {
            "type": "image",
            "originalContentUrl": original_url,
            "previewImageUrl": preview_url
        }
        
        if reply_token:
            return await self._reply_message(reply_token, [message])
        else:
            return await self._push_message(to, [message])
    
    def verify_webhook(self, signature: str, body: bytes) -> bool:
        """
        Verify webhook signature from LINE.
        
        Args:
            signature: X-Line-Signature header value
            body: Raw request body
            
        Returns:
            True if signature is valid
        """
        hash_value = hmac.new(
            self.channel_secret.encode("utf-8"),
            body,
            hashlib.sha256
        ).digest()
        
        expected_signature = base64.b64encode(hash_value).decode("utf-8")
        
        return hmac.compare_digest(signature, expected_signature)
    
    async def process_webhook(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process incoming webhook from LINE.
        
        Args:
            data: Webhook payload
            
        Returns:
            List of processed events for queue
        """
        events = []
        
        for event in data.get("events", []):
            event_type = event.get("type")
            
            if event_type == "message":
                # Incoming message
                message = event.get("message", {})
                source = event.get("source", {})
                
                events.append({
                    "type": "message",
                    "platform": "line",
                    "message_id": message.get("id"),
                    "reply_token": event.get("replyToken"),
                    "from": source.get("userId"),
                    "group_id": source.get("groupId"),
                    "room_id": source.get("roomId"),
                    "content": self._extract_message_content(message),
                    "content_type": message.get("type"),
                    "timestamp": event.get("timestamp"),
                })
            
            elif event_type == "postback":
                # Postback event (from template actions)
                postback = event.get("postback", {})
                source = event.get("source", {})
                
                events.append({
                    "type": "postback",
                    "platform": "line",
                    "reply_token": event.get("replyToken"),
                    "from": source.get("userId"),
                    "data": postback.get("data"),
                    "params": postback.get("params"),
                    "timestamp": event.get("timestamp"),
                })
            
            elif event_type == "follow":
                # User added bot as friend
                source = event.get("source", {})
                
                events.append({
                    "type": "follow",
                    "platform": "line",
                    "reply_token": event.get("replyToken"),
                    "from": source.get("userId"),
                    "timestamp": event.get("timestamp"),
                })
            
            elif event_type == "unfollow":
                # User blocked bot
                source = event.get("source", {})
                
                events.append({
                    "type": "unfollow",
                    "platform": "line",
                    "from": source.get("userId"),
                    "timestamp": event.get("timestamp"),
                })
        
        return events
    
    def _extract_message_content(self, message: Dict) -> str:
        """Extract text content from message"""
        msg_type = message.get("type")
        
        if msg_type == "text":
            return message.get("text", "")
        elif msg_type == "sticker":
            return f"[Sticker: {message.get('packageId')}_{message.get('stickerId')}]"
        elif msg_type == "image":
            return "[Image]"
        elif msg_type == "video":
            return "[Video]"
        elif msg_type == "audio":
            return "[Audio]"
        elif msg_type == "file":
            return f"[File: {message.get('fileName')}]"
        elif msg_type == "location":
            return f"[Location: {message.get('title')}]"
        else:
            return f"[{msg_type} message]"
    
    async def _check_rate_limit(self, recipient: str) -> bool:
        """Check if we can send message within rate limits"""
        key = f"line:rate:{recipient}"
        
        # Use Redis to track rate limit
        allowed, remaining = await redis_manager.check_rate_limit(
            identifier=key,
            limit=self.rate_limit,
            window=self.rate_window
        )
        
        if not allowed:
            logger.warning(f"Rate limit reached for LINE recipient {recipient}")
        
        return allowed
    
    async def get_profile(self, user_id: str) -> Dict[str, Any]:
        """
        Get user profile information.
        
        Args:
            user_id: LINE user ID
            
        Returns:
            Profile data with displayName, pictureUrl, statusMessage
        """
        url = f"{self.api_url}/profile/{user_id}"
        
        async with self.session.get(url) as response:
            if response.status == 200:
                return await response.json()
            else:
                error = await response.text()
                logger.error(f"Failed to get LINE profile: {error}")
                raise Exception(f"LINE API error: {error}")
    
    async def get_group_member_profile(
        self,
        group_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get member profile in a group.
        
        Args:
            group_id: Group ID
            user_id: User ID
            
        Returns:
            Profile data
        """
        url = f"{self.api_url}/group/{group_id}/member/{user_id}"
        
        async with self.session.get(url) as response:
            if response.status == 200:
                return await response.json()
            else:
                error = await response.text()
                logger.error(f"Failed to get group member profile: {error}")
                raise Exception(f"LINE API error: {error}")
    
    async def leave_group(self, group_id: str) -> bool:
        """
        Leave a group.
        
        Args:
            group_id: Group ID to leave
            
        Returns:
            Success status
        """
        url = f"{self.api_url}/group/{group_id}/leave"
        
        async with self.session.post(url) as response:
            return response.status == 200
    
    async def get_message_content(self, message_id: str) -> bytes:
        """
        Get binary message content (images, videos, audio files).
        
        Args:
            message_id: Message ID
            
        Returns:
            Binary content
        """
        url = f"https://api-data.line.me/v2/bot/message/{message_id}/content"
        
        async with self.session.get(url) as response:
            if response.status == 200:
                return await response.read()
            else:
                error = await response.text()
                logger.error(f"Failed to get message content: {error}")
                raise Exception(f"LINE API error: {error}")
    
    async def broadcast(self, messages: List[Dict]) -> Dict[str, Any]:
        """
        Send broadcast message to all users.
        
        Args:
            messages: List of message objects
            
        Returns:
            API response
        """
        url = f"{self.api_url}/message/broadcast"
        
        payload = {
            "messages": messages[:5]
        }
        
        async with self.session.post(url, json=payload) as response:
            if response.status == 200:
                return {"success": True}
            else:
                error = await response.text()
                logger.error(f"Broadcast failed: {error}")
                raise Exception(f"LINE API error: {error}")
    
    def create_rich_menu(self) -> Dict:
        """
        Create rich menu structure for better UX.
        
        Returns:
            Rich menu object
        """
        return {
            "size": {
                "width": 2500,
                "height": 1686
            },
            "selected": True,
            "name": "BMA Music Control",
            "chatBarText": "Menu",
            "areas": [
                {
                    "bounds": {
                        "x": 0,
                        "y": 0,
                        "width": 833,
                        "height": 843
                    },
                    "action": {
                        "type": "message",
                        "text": "Check music status"
                    }
                },
                {
                    "bounds": {
                        "x": 834,
                        "y": 0,
                        "width": 833,
                        "height": 843
                    },
                    "action": {
                        "type": "message",
                        "text": "Change playlist"
                    }
                },
                {
                    "bounds": {
                        "x": 1667,
                        "y": 0,
                        "width": 833,
                        "height": 843
                    },
                    "action": {
                        "type": "message",
                        "text": "Adjust volume"
                    }
                },
                {
                    "bounds": {
                        "x": 0,
                        "y": 843,
                        "width": 833,
                        "height": 843
                    },
                    "action": {
                        "type": "message",
                        "text": "Play music"
                    }
                },
                {
                    "bounds": {
                        "x": 834,
                        "y": 843,
                        "width": 833,
                        "height": 843
                    },
                    "action": {
                        "type": "message",
                        "text": "Stop music"
                    }
                },
                {
                    "bounds": {
                        "x": 1667,
                        "y": 843,
                        "width": 833,
                        "height": 843
                    },
                    "action": {
                        "type": "message",
                        "text": "Get help"
                    }
                }
            ]
        }


# Global LINE client instance
line_client = LineClient()
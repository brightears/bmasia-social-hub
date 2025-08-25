"""
Webhook endpoints for WhatsApp and Line message processing.
Handles incoming messages with async processing for scale.
"""

import hashlib
import hmac
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from fastapi import APIRouter, Request, Response, HTTPException, BackgroundTasks, Depends, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.database import get_db
from app.core.redis import redis_manager

logger = logging.getLogger(__name__)

router = APIRouter()


class WebhookProcessor:
    """Process webhook messages asynchronously"""
    
    @staticmethod
    async def process_whatsapp_message(data: Dict[str, Any], db: AsyncSession):
        """Process WhatsApp message in background"""
        try:
            # Extract message details
            entry = data.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            value = changes.get("value", {})
            
            if "messages" in value:
                for message in value["messages"]:
                    await WebhookProcessor._handle_whatsapp_message(message, value, db)
            
            if "statuses" in value:
                for status in value["statuses"]:
                    await WebhookProcessor._handle_whatsapp_status(status, db)
                    
        except Exception as e:
            logger.error(f"Error processing WhatsApp webhook: {e}", exc_info=True)
    
    @staticmethod
    async def _handle_whatsapp_message(message: Dict, value: Dict, db: AsyncSession):
        """Handle individual WhatsApp message"""
        message_id = message.get("id")
        from_number = message.get("from")
        message_type = message.get("type")
        timestamp = message.get("timestamp")
        
        # Get contact info
        contacts = value.get("contacts", [{}])
        contact = contacts[0] if contacts else {}
        contact_name = contact.get("profile", {}).get("name", "Unknown")
        
        # Extract message content based on type
        content = ""
        if message_type == "text":
            content = message.get("text", {}).get("body", "")
        elif message_type == "audio":
            content = "[Audio message]"
        elif message_type == "image":
            content = message.get("image", {}).get("caption", "[Image]")
        elif message_type == "document":
            content = "[Document]"
        elif message_type == "location":
            location = message.get("location", {})
            content = f"[Location: {location.get('latitude')}, {location.get('longitude')}]"
        
        # Store message for processing
        message_data = {
            "channel": "whatsapp",
            "external_id": message_id,
            "from_number": from_number,
            "contact_name": contact_name,
            "message_type": message_type,
            "content": content,
            "timestamp": timestamp,
            "raw_data": message,
        }
        
        # Queue for bot processing
        await redis_manager.publish("messages:whatsapp:incoming", message_data)
        
        logger.info(f"WhatsApp message queued: {message_id} from {from_number}")
    
    @staticmethod
    async def _handle_whatsapp_status(status: Dict, db: AsyncSession):
        """Handle WhatsApp message status updates"""
        message_id = status.get("id")
        status_type = status.get("status")
        recipient_id = status.get("recipient_id")
        timestamp = status.get("timestamp")
        
        # Update message delivery status
        status_data = {
            "message_id": message_id,
            "status": status_type,
            "recipient_id": recipient_id,
            "timestamp": timestamp,
        }
        
        await redis_manager.publish("messages:whatsapp:status", status_data)
        
        logger.debug(f"WhatsApp status update: {message_id} - {status_type}")
    
    @staticmethod
    async def process_line_message(data: Dict[str, Any], db: AsyncSession):
        """Process Line message in background"""
        try:
            events = data.get("events", [])
            
            for event in events:
                event_type = event.get("type")
                
                if event_type == "message":
                    await WebhookProcessor._handle_line_message(event, db)
                elif event_type == "follow":
                    await WebhookProcessor._handle_line_follow(event, db)
                elif event_type == "unfollow":
                    await WebhookProcessor._handle_line_unfollow(event, db)
                elif event_type == "postback":
                    await WebhookProcessor._handle_line_postback(event, db)
                    
        except Exception as e:
            logger.error(f"Error processing Line webhook: {e}", exc_info=True)
    
    @staticmethod
    async def _handle_line_message(event: Dict, db: AsyncSession):
        """Handle individual Line message"""
        message = event.get("message", {})
        message_id = message.get("id")
        message_type = message.get("type")
        
        source = event.get("source", {})
        user_id = source.get("userId")
        source_type = source.get("type")
        
        reply_token = event.get("replyToken")
        timestamp = event.get("timestamp")
        
        # Extract message content based on type
        content = ""
        if message_type == "text":
            content = message.get("text", "")
        elif message_type == "image":
            content = "[Image]"
        elif message_type == "video":
            content = "[Video]"
        elif message_type == "audio":
            content = "[Audio]"
        elif message_type == "file":
            content = f"[File: {message.get('fileName', 'Unknown')}]"
        elif message_type == "location":
            content = f"[Location: {message.get('title', 'Unknown')}]"
        elif message_type == "sticker":
            content = "[Sticker]"
        
        # Store message for processing
        message_data = {
            "channel": "line",
            "external_id": message_id,
            "user_id": user_id,
            "message_type": message_type,
            "content": content,
            "reply_token": reply_token,
            "timestamp": timestamp,
            "raw_data": event,
        }
        
        # Queue for bot processing
        await redis_manager.publish("messages:line:incoming", message_data)
        
        logger.info(f"Line message queued: {message_id} from {user_id}")
    
    @staticmethod
    async def _handle_line_follow(event: Dict, db: AsyncSession):
        """Handle Line follow event (user added bot)"""
        source = event.get("source", {})
        user_id = source.get("userId")
        
        logger.info(f"New Line follower: {user_id}")
        
        # Queue welcome message
        await redis_manager.publish("events:line:follow", {"user_id": user_id})
    
    @staticmethod
    async def _handle_line_unfollow(event: Dict, db: AsyncSession):
        """Handle Line unfollow event (user blocked bot)"""
        source = event.get("source", {})
        user_id = source.get("userId")
        
        logger.info(f"Line unfollower: {user_id}")
        
        # Queue cleanup
        await redis_manager.publish("events:line:unfollow", {"user_id": user_id})
    
    @staticmethod
    async def _handle_line_postback(event: Dict, db: AsyncSession):
        """Handle Line postback event (button clicks)"""
        postback = event.get("postback", {})
        data = postback.get("data")
        
        source = event.get("source", {})
        user_id = source.get("userId")
        
        # Queue postback processing
        await redis_manager.publish("events:line:postback", {
            "user_id": user_id,
            "data": data,
            "raw_event": event,
        })


# WhatsApp Webhooks

@router.get("/whatsapp")
async def whatsapp_webhook_verify(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    """
    WhatsApp webhook verification endpoint.
    Called by Meta to verify webhook URL.
    """
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        logger.info("WhatsApp webhook verified successfully")
        return PlainTextResponse(content=hub_challenge)
    else:
        logger.warning(f"WhatsApp webhook verification failed: {hub_verify_token}")
        raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/whatsapp")
async def whatsapp_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    WhatsApp webhook endpoint for receiving messages.
    Processes messages asynchronously for scalability.
    """
    # Get request body
    body = await request.body()
    data = await request.json()
    
    # Verify webhook signature
    signature = request.headers.get("X-Hub-Signature-256", "")
    if signature:
        expected_signature = hmac.new(
            settings.whatsapp_webhook_secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(f"sha256={expected_signature}", signature):
            logger.warning("Invalid WhatsApp webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Process in background
    background_tasks.add_task(
        WebhookProcessor.process_whatsapp_message,
        data,
        db
    )
    
    # Return immediate response
    return {"status": "received"}


# Line Webhooks

@router.post("/line")
async def line_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Line webhook endpoint for receiving messages.
    Processes messages asynchronously for scalability.
    """
    # Get request body
    body = await request.body()
    data = await request.json()
    
    # Verify webhook signature
    signature = request.headers.get("X-Line-Signature", "")
    if signature:
        expected_signature = hmac.new(
            settings.line_channel_secret.encode(),
            body,
            hashlib.sha256
        ).digest()
        
        import base64
        expected_signature_b64 = base64.b64encode(expected_signature).decode()
        
        if not hmac.compare_digest(expected_signature_b64, signature):
            logger.warning("Invalid Line webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Process in background
    background_tasks.add_task(
        WebhookProcessor.process_line_message,
        data,
        db
    )
    
    # Return immediate response
    return {"status": "received"}


# Test endpoints (development only)

if settings.is_development:
    @router.post("/test/whatsapp")
    async def test_whatsapp_message(
        message: Dict[str, Any],
        background_tasks: BackgroundTasks,
        db: AsyncSession = Depends(get_db),
    ):
        """Test endpoint for WhatsApp message processing"""
        # Create test webhook data
        test_data = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [message],
                        "contacts": [{
                            "profile": {"name": "Test User"}
                        }]
                    }
                }]
            }]
        }
        
        background_tasks.add_task(
            WebhookProcessor.process_whatsapp_message,
            test_data,
            db
        )
        
        return {"status": "test message queued"}
    
    @router.post("/test/line")
    async def test_line_message(
        message: Dict[str, Any],
        background_tasks: BackgroundTasks,
        db: AsyncSession = Depends(get_db),
    ):
        """Test endpoint for Line message processing"""
        # Create test webhook data
        test_data = {
            "events": [{
                "type": "message",
                "message": message,
                "source": {
                    "type": "user",
                    "userId": "test_user_123"
                },
                "replyToken": "test_reply_token",
                "timestamp": int(datetime.utcnow().timestamp() * 1000)
            }]
        }
        
        background_tasks.add_task(
            WebhookProcessor.process_line_message,
            test_data,
            db
        )
        
        return {"status": "test message queued"}
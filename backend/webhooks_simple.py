"""
Simple webhook endpoints for WhatsApp and Line message processing.
No database dependencies - just webhook verification and logging.
"""

import hashlib
import hmac
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, Request, Response, HTTPException, BackgroundTasks, Query
from fastapi.responses import PlainTextResponse

# Simple config using environment variables
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

router = APIRouter()

# Get config from environment
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "bma_whatsapp_verify_2024")
WHATSAPP_WEBHOOK_SECRET = os.getenv("WHATSAPP_WEBHOOK_SECRET", "bma_webhook_secret_2024")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")

# Import bot for responses
try:
    from bot_simple import bot, sender
    BOT_ENABLED = True
    logger.info("✅ Bot module loaded successfully")
except ImportError as e:
    logger.warning(f"⚠️ Bot module not available: {e}")
    BOT_ENABLED = False
    bot = None
    sender = None


# WhatsApp Webhooks

@router.get("/whatsapp")
def whatsapp_webhook_verify(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    """
    WhatsApp webhook verification endpoint.
    Called by Meta to verify webhook URL.
    """
    logger.info(f"WhatsApp webhook verification: mode={hub_mode}, token={hub_verify_token}")
    
    if hub_mode == "subscribe" and hub_verify_token == WHATSAPP_VERIFY_TOKEN:
        logger.info("WhatsApp webhook verified successfully")
        return PlainTextResponse(content=hub_challenge)
    else:
        logger.warning(f"WhatsApp webhook verification failed: {hub_verify_token} != {WHATSAPP_VERIFY_TOKEN}")
        raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/whatsapp")
async def whatsapp_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    WhatsApp webhook endpoint for receiving messages.
    Logs messages for now - processing to be added later.
    """
    # Get request body
    body = await request.body()
    data = await request.json()
    
    # Temporarily skip signature verification for testing
    # TODO: Get App Secret from Meta App Dashboard for production
    signature = request.headers.get("X-Hub-Signature-256", "")
    if signature:
        logger.info(f"Received signature: {signature[:20]}...")
        # For now, just log and continue
        pass
    
    # Log the message
    logger.info(f"WhatsApp webhook received: {json.dumps(data)}")
    
    # Process message data
    try:
        entry = data.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        
        if "messages" in value:
            for message in value["messages"]:
                message_id = message.get("id")
                from_number = message.get("from")
                message_type = message.get("type")
                
                # Get contact name if available
                contacts = value.get("contacts", [{}])
                contact = contacts[0] if contacts else {}
                contact_name = contact.get("profile", {}).get("name", "User")
                
                if message_type == "text":
                    content = message.get("text", {}).get("body", "")
                    logger.info(f"WhatsApp message: {message_id} from {from_number} ({contact_name}): {content}")
                    
                    # Generate and send response if bot is enabled
                    if BOT_ENABLED and bot and sender:
                        try:
                            # Generate AI response
                            response_text = bot.generate_response(content, contact_name)
                            logger.info(f"Generated response: {response_text[:100]}...")
                            
                            # Send response back via WhatsApp
                            success = sender.send_whatsapp_message(from_number, response_text)
                            if success:
                                logger.info(f"Response sent to {from_number}")
                            else:
                                logger.error(f"Failed to send response to {from_number}")
                                
                        except Exception as e:
                            logger.error(f"Error generating/sending response: {e}")
                    else:
                        logger.info("Bot not enabled - no response sent")
                
    except Exception as e:
        logger.error(f"Error processing WhatsApp webhook: {e}")
    
    # Return immediate response
    return {"status": "received"}


# Line Webhooks

@router.post("/line")
async def line_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    Line webhook endpoint for receiving messages.
    Logs messages for now - processing to be added later.
    """
    # Get request body
    body = await request.body()
    data = await request.json()
    
    # Verify webhook signature
    if LINE_CHANNEL_SECRET:
        signature = request.headers.get("X-Line-Signature", "")
        if signature:
            expected_signature = hmac.new(
                LINE_CHANNEL_SECRET.encode(),
                body,
                hashlib.sha256
            ).digest()
            
            import base64
            expected_signature_b64 = base64.b64encode(expected_signature).decode()
            
            if not hmac.compare_digest(expected_signature_b64, signature):
                logger.warning("Invalid Line webhook signature")
                raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Log the message
    logger.info(f"Line webhook received: {json.dumps(data)}")
    
    # Process events
    try:
        events = data.get("events", [])
        
        for event in events:
            event_type = event.get("type")
            
            if event_type == "message":
                message = event.get("message", {})
                message_id = message.get("id")
                message_type = message.get("type")
                
                source = event.get("source", {})
                user_id = source.get("userId")
                reply_token = event.get("replyToken")
                
                if message_type == "text":
                    content = message.get("text", "")
                    logger.info(f"Line message: {message_id} from {user_id}: {content}")
                    
                    # Generate and send response if bot is enabled
                    if BOT_ENABLED and bot and sender and reply_token:
                        try:
                            # Generate AI response
                            response_text = bot.generate_response(content, user_id)
                            logger.info(f"Generated LINE response: {response_text[:100]}...")
                            
                            # Send response back via LINE
                            success = sender.send_line_message(reply_token, response_text)
                            if success:
                                logger.info(f"LINE response sent to {user_id}")
                            else:
                                logger.error(f"Failed to send LINE response to {user_id}")
                                
                        except Exception as e:
                            logger.error(f"Error generating/sending LINE response: {e}")
                    else:
                        logger.info("Bot not enabled or no reply token - no response sent")
                    
    except Exception as e:
        logger.error(f"Error processing Line webhook: {e}")
    
    # Return immediate response
    return {"status": "received"}
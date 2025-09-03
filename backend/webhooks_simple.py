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
import time
from collections import defaultdict

# Simple config using environment variables
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

router = APIRouter()

# Simple deduplication - track recent message IDs
processed_messages = defaultdict(float)
MESSAGE_DEDUPE_WINDOW = 10  # seconds

# Get config from environment
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "bma_whatsapp_verify_2024")
WHATSAPP_WEBHOOK_SECRET = os.getenv("WHATSAPP_WEBHOOK_SECRET", "bma_webhook_secret_2024")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")

# Import bot for responses - try Gemini AI-powered version first
try:
    from bot_gemini import gemini_bot as bot
    from bot_simple import sender
    BOT_ENABLED = True
    logger.info("✅ Gemini AI-powered bot loaded with natural language understanding")
except ImportError as e:
    logger.warning(f"⚠️ Gemini bot not available: {e}")
    try:
        from bot_soundtrack import soundtrack_bot as bot
        from bot_simple import sender
        BOT_ENABLED = True
        logger.info("✅ Soundtrack-enabled bot loaded (fallback)")
    except ImportError:
        try:
            from bot_integrated import integrated_bot as bot
            from bot_simple import sender
            BOT_ENABLED = True
            logger.info("✅ Integrated bot loaded (fallback)")
        except ImportError:
            try:
                from bot_simple import bot, sender
                BOT_ENABLED = True
                logger.info("✅ Simple bot loaded (final fallback)")
            except ImportError as e:
                logger.warning(f"⚠️ Bot module not available: {e}")
            BOT_ENABLED = False
            bot = None
            sender = None

# Import database manager
try:
    from database import db_manager
    DB_ENABLED = True
    logger.info("✅ Database module loaded successfully")
except ImportError as e:
    logger.warning(f"⚠️ Database module not available: {e}")
    DB_ENABLED = False
    db_manager = None


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
    # Enhanced logging for debugging
    logger.info(f"🔍 WhatsApp webhook verification received:")
    logger.info(f"  - mode: {hub_mode}")
    logger.info(f"  - token: {hub_verify_token}")
    logger.info(f"  - challenge: {hub_challenge}")
    logger.info(f"  - expected_token: {WHATSAPP_VERIFY_TOKEN}")
    
    if hub_mode == "subscribe" and hub_verify_token == WHATSAPP_VERIFY_TOKEN:
        logger.info("✅ WhatsApp webhook verified successfully")
        return PlainTextResponse(content=hub_challenge)
    else:
        logger.error(f"❌ WhatsApp webhook verification failed: received='{hub_verify_token}' expected='{WHATSAPP_VERIFY_TOKEN}'")
        raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/whatsapp")
async def whatsapp_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    WhatsApp webhook endpoint for receiving messages.
    Enhanced logging and processing.
    """
    # Enhanced logging
    logger.info("📨 WhatsApp webhook POST received!")
    logger.info(f"  - Source IP: {request.client.host if request.client else 'unknown'}")
    logger.info(f"  - Headers: {dict(request.headers)}")
    
    # Get request body
    try:
        body = await request.body()
        data = await request.json()
        logger.info(f"  - Body length: {len(body)} bytes")
        logger.info(f"📱 WhatsApp webhook data: {json.dumps(data, indent=2)}")
    except Exception as e:
        logger.error(f"❌ Failed to parse webhook body: {e}")
        return {"status": "error", "message": "Invalid JSON"}
    
    # Check signature
    signature = request.headers.get("X-Hub-Signature-256", "")
    if signature:
        logger.info(f"🔐 Received signature: {signature[:20]}...")
        # TODO: Implement proper signature verification for production
    else:
        logger.warning("⚠️ No signature received from WhatsApp")
    
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
                
                # Check for duplicate messages
                current_time = time.time()
                if message_id in processed_messages:
                    if current_time - processed_messages[message_id] < MESSAGE_DEDUPE_WINDOW:
                        logger.info(f"Duplicate message {message_id} ignored (processed {current_time - processed_messages[message_id]:.1f}s ago)")
                        continue
                processed_messages[message_id] = current_time
                
                # Clean old entries from deduplication dict
                for msg_id in list(processed_messages.keys()):
                    if current_time - processed_messages[msg_id] > MESSAGE_DEDUPE_WINDOW * 2:
                        del processed_messages[msg_id]
                
                # Get contact name if available
                contacts = value.get("contacts", [{}])
                contact = contacts[0] if contacts else {}
                contact_name = contact.get("profile", {}).get("name", "User")
                
                if message_type == "text":
                    content = message.get("text", {}).get("body", "")
                    logger.info(f"WhatsApp message: {message_id} from {from_number} ({contact_name}): {content}")
                    
                    # Store message in database if enabled
                    conversation_id = None
                    if DB_ENABLED and db_manager:
                        try:
                            conversation_id = db_manager.store_message(
                                channel="whatsapp",
                                user_phone=from_number,
                                user_name=contact_name,
                                message_id=message_id,
                                content=content,
                                direction="inbound",
                                message_type=message_type
                            )
                            logger.info(f"Message stored in conversation {conversation_id}")
                        except Exception as e:
                            logger.error(f"Failed to store message: {e}")
                    
                    # Generate and send response if bot is enabled
                    if BOT_ENABLED and bot and sender:
                        try:
                            # Use integrated bot's process_message if available
                            if hasattr(bot, 'process_message'):
                                response_text = bot.process_message(content, from_number, contact_name, platform="WhatsApp")
                            else:
                                # Fallback to simple generate_response
                                response_text = bot.generate_response(content, contact_name)
                            logger.info(f"Generated response: {response_text[:100]}...")
                            
                            # Send response back via WhatsApp
                            success = sender.send_whatsapp_message(from_number, response_text)
                            if success:
                                logger.info(f"Response sent to {from_number}")
                                
                                # Store outbound message in database
                                if DB_ENABLED and db_manager and conversation_id:
                                    try:
                                        db_manager.store_message(
                                            channel="whatsapp",
                                            user_phone=from_number,
                                            user_name=contact_name,
                                            message_id=f"out_{message_id}_{datetime.now().timestamp()}",
                                            content=response_text,
                                            direction="outbound",
                                            message_type="text",
                                            ai_response=True
                                        )
                                        logger.info("Response stored in database")
                                    except Exception as e:
                                        logger.error(f"Failed to store response: {e}")
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


@router.post("/whatsapp/test")
async def test_whatsapp_webhook():
    """Test endpoint to simulate a WhatsApp message"""
    logger.info("🧪 Test WhatsApp webhook triggered")
    
    # Simulate a WhatsApp message payload
    test_data = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "test_entry",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "display_phone_number": "6563237765",
                        "phone_number_id": "test_phone_id"
                    },
                    "contacts": [{
                        "profile": {"name": "Test User"},
                        "wa_id": "601234567890"
                    }],
                    "messages": [{
                        "from": "601234567890",
                        "id": f"test_msg_{datetime.now().timestamp()}",
                        "timestamp": str(int(datetime.now().timestamp())),
                        "text": {"body": "Test message - is the bot working?"},
                        "type": "text"
                    }]
                },
                "field": "messages"
            }]
        }]
    }
    
    logger.info(f"🧪 Simulating WhatsApp message: {json.dumps(test_data, indent=2)}")
    
    # Process the test message through the same logic
    try:
        entry = test_data.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        
        if "messages" in value:
            for message in value["messages"]:
                message_id = message.get("id")
                from_number = message.get("from")
                content = message.get("text", {}).get("body", "")
                contact_name = "Test User"
                
                logger.info(f"🧪 Processing test message: {content}")
                
                # Generate response if bot is enabled
                if BOT_ENABLED and bot and sender:
                    try:
                        if hasattr(bot, 'process_message'):
                            response_text = bot.process_message(content, from_number, contact_name, platform="LINE")
                        else:
                            response_text = bot.generate_response(content, contact_name)
                        
                        logger.info(f"🤖 Generated test response: {response_text[:100]}...")
                        
                        return {
                            "status": "test_success",
                            "test_message": content,
                            "bot_response": response_text,
                            "message": "Test webhook processed successfully"
                        }
                    except Exception as e:
                        logger.error(f"❌ Error in test bot response: {e}")
                        return {
                            "status": "test_error",
                            "error": str(e),
                            "message": "Bot response failed"
                        }
                else:
                    return {
                        "status": "test_partial",
                        "message": "Webhook received but bot not enabled"
                    }
    except Exception as e:
        logger.error(f"❌ Test webhook processing error: {e}")
        return {
            "status": "test_error",
            "error": str(e)
        }


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
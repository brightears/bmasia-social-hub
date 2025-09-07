#!/usr/bin/env python3
"""
FastAPI application with BMA Social Music Bot
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import FastAPI, Response, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

# Try to import psycopg2, but make it optional
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAS_DATABASE = True
except ImportError:
    HAS_DATABASE = False
    psycopg2 = None
    RealDictCursor = None

# Try to import redis, but make it optional
try:
    import redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False
    redis = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="BMA Social API",
    description="AI-powered music operations platform with intelligent bot",
    version="0.3.0"
)

# Request models
class BotMessage(BaseModel):
    message: str
    user_phone: str
    user_name: Optional[str] = None
    
class WebhookMessage(BaseModel):
    from_number: str
    body: str
    message_sid: Optional[str] = None

# Global state
startup_time = datetime.utcnow()
request_count = 0
db_connection = None
redis_client = None

# Initialize the music bot
music_bot = None
try:
    # Use bot_final which actually reads venue_data.md properly
    from bot_fresh_start import bot as bot_instance
    music_bot = bot_instance
    logger.info("✅ Music bot (final) initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize music bot: {e}")
    music_bot = None

def get_db_connection():
    """Get database connection"""
    global db_connection
    
    if not HAS_DATABASE:
        logger.warning("psycopg2 not installed - database features disabled")
        return None
    
    DATABASE_URL = os.environ.get('DATABASE_URL', 
        'postgresql://bma_user:wVLGYkim3mf3qYocucd6IhXjogfLbZAb@dpg-d2m6jrre5dus739fr8p0-a/bma_social_esoq')
    
    try:
        if db_connection is None or db_connection.closed:
            db_connection = psycopg2.connect(DATABASE_URL)
            logger.info("Database connected successfully")
        return db_connection
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return None

def get_redis_client():
    """Get Redis client"""
    global redis_client
    
    if not HAS_REDIS:
        logger.warning("redis not installed - cache features disabled")
        return None
    
    REDIS_URL = os.environ.get('REDIS_URL', 
        'redis://red-d2m6jrre5dus739fr8g0:6379')
    
    try:
        if redis_client is None:
            redis_client = redis.from_url(REDIS_URL, decode_responses=True)
            # Test connection
            redis_client.ping()
            logger.info("Redis connected successfully")
        return redis_client
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        redis_client = None
        return None

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    logger.info("Starting BMA Social API with Database and Cache")
    
    # Initialize database with new manager
    try:
        from database import db_manager
        if db_manager.ensure_connection():
            logger.info("✅ Database connection established")
            # Initialize tables
            if db_manager.initialize_tables():
                logger.info("✅ Database tables initialized")
            else:
                logger.warning("⚠️ Failed to initialize tables")
        else:
            logger.warning("⚠️ Running without database")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        logger.warning("⚠️ Running without database")
    
    # Initialize Redis
    redis = get_redis_client()
    if redis:
        logger.info("✅ Redis connection established")
    else:
        logger.warning("⚠️ Running without cache")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global db_connection
    if db_connection and not db_connection.closed:
        db_connection.close()
        logger.info("Database connection closed")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "BMA Social API",
        "status": "running",
        "mode": "with_database",
        "uptime": str(datetime.utcnow() - startup_time)
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    global request_count
    request_count += 1
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime": str(datetime.utcnow() - startup_time),
        "requests_served": request_count,
        "service_awake": True
    }

@app.get("/wake")
@app.post("/wake")
async def wake_service():
    """Wake up endpoint to prevent service from sleeping"""
    logger.info("🚀 Service wake-up requested")
    return {
        "status": "awake",
        "timestamp": datetime.utcnow().isoformat(),
        "message": "Service is now awake and ready to receive webhooks"
    }

@app.get("/webhook-test")
async def webhook_diagnostics():
    """Test endpoint to verify webhook configuration"""
    return {
        "webhook_urls": {
            "whatsapp_verify": "https://bma-social-api-q9uu.onrender.com/webhooks/whatsapp",
            "whatsapp_webhook": "https://bma-social-api-q9uu.onrender.com/webhooks/whatsapp",
            "line_webhook": "https://bma-social-api-q9uu.onrender.com/webhooks/line"
        },
        "verify_token": "bma_whatsapp_verify_2024",
        "service_status": "active",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/api/v1/bot/message")
async def bot_message(message: BotMessage):
    """Process a message through the music bot"""
    if not music_bot:
        raise HTTPException(status_code=503, detail="Bot service unavailable")
    
    try:
        response = music_bot.process_message(
            message.message,
            message.user_phone,
            message.user_name
        )
        return {
            "success": True,
            "response": response,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Bot error: {e}")
        return {
            "success": False,
            "error": str(e),
            "response": "I apologize, but I encountered an error. Please try again or contact support.",
            "timestamp": datetime.utcnow().isoformat()
        }

@app.post("/webhooks/whatsapp")
async def whatsapp_webhook(request: Request):
    """Handle WhatsApp webhook"""
    try:
        data = await request.json()
        logger.info(f"WhatsApp webhook received: {data}")
        
        # Extract message from WhatsApp format
        if "entry" in data:
            for entry in data["entry"]:
                for change in entry.get("changes", []):
                    if change.get("field") == "messages":
                        messages = change.get("value", {}).get("messages", [])
                        for msg in messages:
                            if msg.get("type") == "text":
                                text = msg.get("text", {}).get("body", "")
                                from_number = msg.get("from", "")
                                
                                if music_bot and text:
                                    response = music_bot.process_message(
                                        text,
                                        from_number,
                                        None
                                    )
                                    logger.info(f"Bot response: {response}")
                                    
                                    # Send response back via WhatsApp API
                                    import requests
                                    whatsapp_token = os.environ.get('WHATSAPP_ACCESS_TOKEN')
                                    phone_number_id = change.get("value", {}).get("metadata", {}).get("phone_number_id")
                                    
                                    if whatsapp_token and phone_number_id:
                                        url = f"https://graph.facebook.com/v17.0/{phone_number_id}/messages"
                                        headers = {
                                            "Authorization": f"Bearer {whatsapp_token}",
                                            "Content-Type": "application/json"
                                        }
                                        payload = {
                                            "messaging_product": "whatsapp",
                                            "to": from_number,
                                            "text": {"body": response}
                                        }
                                        
                                        try:
                                            send_response = requests.post(url, headers=headers, json=payload)
                                            if send_response.status_code == 200:
                                                logger.info(f"WhatsApp response sent to {from_number}")
                                            else:
                                                logger.error(f"Failed to send WhatsApp response: {send_response.text}")
                                        except Exception as e:
                                            logger.error(f"Error sending WhatsApp response: {e}")
                                    else:
                                        logger.warning("WhatsApp token or phone_number_id not configured")
        
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"WhatsApp webhook error: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/webhooks/whatsapp")
async def whatsapp_verify(request: Request):
    """WhatsApp webhook verification"""
    verify_token = "bma_whatsapp_verify_2024"
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    
    if mode == "subscribe" and token == verify_token:
        logger.info("WhatsApp webhook verified")
        return Response(content=challenge, media_type="text/plain")
    
    return {"status": "failed"}

@app.post("/webhooks/google-chat")
async def google_chat_webhook(request: Request):
    """Handle incoming messages from Google Chat for two-way communication"""
    try:
        data = await request.json()
        logger.info(f"Google Chat webhook received: {data.get('type', 'unknown')}")
        
        # Handle different event types
        event_type = data.get("type")
        
        if event_type == "MESSAGE":
            # Import here to avoid circular dependency
            from conversation_tracker import conversation_tracker
            import requests
            
            message = data.get("message", {})
            text = message.get("text", "").strip()
            space = data.get("space", {})
            user = data.get("user", {})
            thread = message.get("thread", {})
            
            # Get thread name to find the conversation
            thread_name = thread.get("name", "")
            
            # Extract thread key from the thread name
            # Thread name format: spaces/SPACE_ID/threads/THREAD_KEY
            thread_key = thread_name.split("/")[-1] if "/" in thread_name else thread_name
            
            # Look up the conversation
            conversation = conversation_tracker.get_conversation_by_thread(thread_key)
            
            if conversation:
                customer_phone = conversation["customer_phone"]
                customer_name = conversation["customer_name"]
                
                # Send the reply to WhatsApp
                whatsapp_token = os.getenv('WHATSAPP_ACCESS_TOKEN')
                phone_number_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
                
                if whatsapp_token and phone_number_id:
                    url = f"https://graph.facebook.com/v17.0/{phone_number_id}/messages"
                    headers = {
                        "Authorization": f"Bearer {whatsapp_token}",
                        "Content-Type": "application/json"
                    }
                    payload = {
                        "messaging_product": "whatsapp",
                        "to": customer_phone,
                        "type": "text",
                        "text": {"body": text}
                    }
                    
                    try:
                        response = requests.post(url, headers=headers, json=payload)
                        if response.status_code == 200:
                            logger.info(f"Reply sent to WhatsApp customer {customer_phone}")
                            
                            # Track the message
                            conversation_tracker.add_message(
                                thread_key=thread_key,
                                message=text,
                                sender=user.get("displayName", "Support Agent"),
                                direction="outbound"
                            )
                            
                            # Send confirmation back to Google Chat
                            return {"text": f"✅ Reply sent to {customer_name}"}
                        else:
                            logger.error(f"Failed to send WhatsApp message: {response.text}")
                            return {"text": f"❌ Failed to send reply: {response.status_code}"}
                    except Exception as e:
                        logger.error(f"Error sending WhatsApp message: {e}")
                        return {"text": f"❌ Error: {str(e)}"}
                else:
                    return {"text": "❌ WhatsApp not configured"}
            else:
                logger.warning(f"No conversation found for thread {thread_key}")
                return {"text": "⚠️ No active conversation found for this thread"}
                
        elif event_type == "ADDED_TO_SPACE":
            # Bot was added to a space
            space_name = data.get("space", {}).get("displayName", "Unknown")
            return {"text": f"👋 BMA Customer Support Bot is ready to relay messages in {space_name}!"}
            
        elif event_type == "REMOVED_FROM_SPACE":
            # Bot was removed from a space
            logger.info("Bot removed from space")
            return {"status": "ok"}
            
        else:
            # Other event types
            logger.info(f"Unhandled event type: {event_type}")
            return {"status": "ok"}
            
    except Exception as e:
        logger.error(f"Google Chat webhook error: {e}", exc_info=True)
        return {"text": f"❌ Error processing message: {str(e)}"}

@app.get("/api/v1/status")
async def api_status():
    """API status with database and cache check"""
    db_status = "connected"
    redis_status = "connected"
    soundtrack_status = "not_configured"
    table_count = 0
    
    # Check database
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            table_count = cursor.fetchone()[0]
            cursor.close()
        except Exception as e:
            db_status = f"error: {str(e)}"
    else:
        db_status = "not_connected"
    
    # Check Redis
    redis = get_redis_client()
    if redis:
        try:
            redis.ping()
            redis_status = "connected"
        except Exception as e:
            redis_status = f"error: {str(e)}"
    else:
        redis_status = "not_connected"
    
    # Check Soundtrack API
    try:
        soundtrack_credentials = os.environ.get('SOUNDTRACK_API_CREDENTIALS')
        soundtrack_client_id = os.environ.get('SOUNDTRACK_CLIENT_ID')
        if soundtrack_credentials or soundtrack_client_id:
            soundtrack_status = "configured"
        else:
            soundtrack_status = "not_configured"
    except Exception:
        soundtrack_status = "error"
    
    return {
        "api_version": "2.0.0",
        "environment": os.environ.get("ENVIRONMENT", "development"),
        "services": {
            "database": db_status,
            "database_tables": table_count,
            "redis": redis_status,
            "soundtrack_api": soundtrack_status
        },
        "features": {
            "venues": table_count > 0,
            "zones": table_count > 0,
            "conversations": False,
            "webhooks": True
        }
    }

@app.get("/api/v1/database/test")
async def test_database():
    """Test database connection"""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor) if RealDictCursor else conn.cursor()
        
        # Get PostgreSQL version
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        
        # Get database size
        cursor.execute("""
            SELECT pg_database_size(current_database()) as size_bytes,
                   pg_size_pretty(pg_database_size(current_database())) as size_pretty
        """)
        db_size = cursor.fetchone()
        
        # Get table list
        cursor.execute("""
            SELECT table_name, 
                   pg_size_pretty(pg_total_relation_size(quote_ident(table_name))) as size
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = cursor.fetchall()
        
        cursor.close()
        
        return {
            "status": "connected",
            "postgresql_version": version['version'],
            "database_size": db_size['size_pretty'],
            "tables": tables
        }
        
    except Exception as e:
        logger.error(f"Database test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/database/init")
async def init_database():
    """Initialize database with basic tables"""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        cursor = conn.cursor()
        
        # Create venues table with all required columns
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS venues (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                phone_number VARCHAR(50) UNIQUE,
                location VARCHAR(500),
                soundtrack_account_id VARCHAR(255),
                contact_name VARCHAR(255),
                contact_email VARCHAR(255),
                active BOOLEAN DEFAULT true,
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Add missing columns if they don't exist
        cursor.execute("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                             WHERE table_name='venues' AND column_name='phone_number') THEN
                    ALTER TABLE venues ADD COLUMN phone_number VARCHAR(50) UNIQUE;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                             WHERE table_name='venues' AND column_name='contact_name') THEN
                    ALTER TABLE venues ADD COLUMN contact_name VARCHAR(255);
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                             WHERE table_name='venues' AND column_name='contact_email') THEN
                    ALTER TABLE venues ADD COLUMN contact_email VARCHAR(255);
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                             WHERE table_name='venues' AND column_name='metadata') THEN
                    ALTER TABLE venues ADD COLUMN metadata JSONB DEFAULT '{}';
                END IF;
            END $$;
        """)
        
        # Create zones table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS zones (
                id SERIAL PRIMARY KEY,
                venue_id INTEGER REFERENCES venues(id) ON DELETE CASCADE,
                name VARCHAR(255) NOT NULL,
                soundtrack_zone_id VARCHAR(255),
                status VARCHAR(50) DEFAULT 'unknown',
                last_check TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create alerts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id SERIAL PRIMARY KEY,
                zone_id INTEGER REFERENCES zones(id) ON DELETE CASCADE,
                alert_type VARCHAR(50),
                message TEXT,
                resolved BOOLEAN DEFAULT false,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP
            )
        """)
        
        conn.commit()
        cursor.close()
        
        return {
            "status": "success",
            "message": "Database initialized/updated with all required columns",
            "tables_created": ["venues", "zones", "alerts"]
        }
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Database init failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/cache/test")
async def test_cache():
    """Test Redis cache connection"""
    redis = get_redis_client()
    if not redis:
        raise HTTPException(status_code=503, detail="Cache not available")
    
    try:
        # Set a test key
        test_key = f"test_{datetime.utcnow().timestamp()}"
        redis.set(test_key, "Hello Redis!", ex=60)  # Expire after 60 seconds
        
        # Get the test key
        value = redis.get(test_key)
        
        # Get Redis info
        info = redis.info()
        
        return {
            "status": "connected",
            "test_key": test_key,
            "test_value": value,
            "redis_version": info.get("redis_version", "unknown"),
            "used_memory_human": info.get("used_memory_human", "unknown"),
            "connected_clients": info.get("connected_clients", 0),
            "total_commands_processed": info.get("total_commands_processed", 0)
        }
        
    except Exception as e:
        logger.error(f"Cache test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/soundtrack/test")
async def test_soundtrack_api():
    """Test Soundtrack API integration"""
    try:
        from test_live_soundtrack import test_soundtrack_api_live
        results = test_soundtrack_api_live()
        
        return {
            "status": "completed",
            "results": results,
            "success_rate": results["summary"]["passed"] / max(results["summary"]["total"], 1) * 100
        }
    except Exception as e:
        logger.error(f"Soundtrack API test failed: {e}")
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")

@app.post("/api/v1/soundtrack/test-message")
async def test_soundtrack_message(message: Dict[str, Any]):
    """Test bot response to Soundtrack-related messages"""
    try:
        test_message = message.get("message", "I am from Millennium Hilton Bangkok, can you check our zones?")
        test_phone = message.get("phone", "+6012345678")
        test_name = message.get("name", "Test User")
        
        # Import and test the bot
        from bot_soundtrack import soundtrack_bot
        response = soundtrack_bot.process_message(test_message, test_phone, test_name)
        
        return {
            "status": "success",
            "input": {
                "message": test_message,
                "phone": test_phone,
                "name": test_name
            },
            "output": {
                "response": response,
                "response_length": len(response)
            }
        }
    except Exception as e:
        logger.error(f"Message test failed: {e}")
        raise HTTPException(status_code=500, detail=f"Message test failed: {str(e)}")

@app.get("/api/v1/venues")
async def get_venues():
    """Get all venues"""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor) if RealDictCursor else conn.cursor()
        cursor.execute("SELECT * FROM venues ORDER BY id")
        venues = cursor.fetchall()
        cursor.close()
        
        return {
            "count": len(venues),
            "venues": venues
        }
    except Exception as e:
        if "venues" not in str(e):
            logger.error(f"Failed to get venues: {e}")
        return {
            "count": 0,
            "venues": [],
            "error": "Table not initialized. Call /api/v1/database/init first"
        }

@app.post("/api/v1/venues/import-sample")
async def import_sample_venues():
    """Import sample venue data"""
    try:
        # First ensure database tables are properly initialized
        from database import db_manager
        if db_manager.ensure_connection():
            db_manager.initialize_tables()
            logger.info("Database tables verified/updated")
        
        from import_venues import create_sample_venues, import_venues
        
        # Create and import sample venues
        sample_venues = create_sample_venues()
        count = import_venues(sample_venues)
        
        return {
            "status": "success",
            "message": f"Imported {count} sample venues",
            "venues_imported": count
        }
    except Exception as e:
        logger.error(f"Failed to import sample venues: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Add webhook routes
try:
    # Try simple webhooks first (no database dependencies)
    import webhooks_simple
    app.include_router(webhooks_simple.router, prefix="/webhooks", tags=["webhooks"])
    logger.info("Webhook routes loaded successfully (simple mode)")
except ImportError:
    try:
        # Fallback to full webhooks if available
        from app.api.v1.endpoints import webhooks
        app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
        logger.info("Webhook routes loaded successfully (full mode)")
    except ImportError as e:
        logger.warning(f"Could not load webhook routes: {e}")

# Error handlers
@app.exception_handler(404)
async def not_found(request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Not found", "path": str(request.url.path)}
    )

@app.exception_handler(500)
async def server_error(request, exc):
    logger.error(f"Internal error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    
    logger.info("=" * 50)
    logger.info("Starting BMA Social API - Database Mode")
    logger.info(f"Port: {port}")
    logger.info(f"Environment: {os.environ.get('ENVIRONMENT', 'development')}")
    logger.info("=" * 50)
    
    # Run with uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
        access_log=True
    )
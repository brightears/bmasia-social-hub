"""
Database connection and session management for BMA Social
Uses PostgreSQL with psycopg2 for conversation storage
"""

import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Database connection URL from environment
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    # Render uses postgres:// but psycopg2 needs postgresql://
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

class DatabaseManager:
    """Manage database connections and operations"""
    
    def __init__(self):
        self.connection = None
        self.connect()
    
    def connect(self):
        """Establish database connection"""
        if not DATABASE_URL:
            logger.warning("No DATABASE_URL found - database features disabled")
            return False
        
        try:
            self.connection = psycopg2.connect(DATABASE_URL)
            self.connection.autocommit = False  # Use transactions
            logger.info("✅ Database connected successfully")
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            self.connection = None
            return False
    
    def ensure_connection(self):
        """Ensure database connection is active"""
        if self.connection is None or self.connection.closed:
            return self.connect()
        return True
    
    @contextmanager
    def get_cursor(self, dict_cursor=True):
        """Get a database cursor with automatic cleanup"""
        if not self.ensure_connection():
            yield None
            return
        
        cursor = None
        try:
            if dict_cursor:
                cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            else:
                cursor = self.connection.cursor()
            yield cursor
            self.connection.commit()
        except Exception as e:
            logger.error(f"Database operation failed: {e}")
            if self.connection:
                self.connection.rollback()
            raise
        finally:
            if cursor:
                cursor.close()
    
    def initialize_tables(self):
        """Create necessary tables if they don't exist"""
        with self.get_cursor(dict_cursor=False) as cursor:
            if not cursor:
                return False
            
            try:
                # Create venues table
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
                
                # Create conversations table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS conversations (
                        id SERIAL PRIMARY KEY,
                        external_id VARCHAR(255) UNIQUE,
                        venue_id INTEGER REFERENCES venues(id) ON DELETE SET NULL,
                        channel VARCHAR(50) NOT NULL, -- whatsapp, line, email
                        user_phone VARCHAR(50),
                        user_name VARCHAR(255),
                        status VARCHAR(50) DEFAULT 'active', -- active, resolved, escalated
                        metadata JSONB DEFAULT '{}',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        resolved_at TIMESTAMP
                    )
                """)
                
                # Create messages table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        id SERIAL PRIMARY KEY,
                        conversation_id INTEGER REFERENCES conversations(id) ON DELETE CASCADE,
                        external_id VARCHAR(255) UNIQUE,
                        direction VARCHAR(10) NOT NULL, -- inbound, outbound
                        message_type VARCHAR(50), -- text, image, audio, etc
                        content TEXT,
                        ai_response BOOLEAN DEFAULT false,
                        metadata JSONB DEFAULT '{}',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create indexes for performance
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_conversations_venue_id 
                    ON conversations(venue_id);
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_conversations_user_phone 
                    ON conversations(user_phone);
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_conversations_status 
                    ON conversations(status);
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_messages_conversation_id 
                    ON messages(conversation_id);
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_messages_created_at 
                    ON messages(created_at DESC);
                """)
                
                logger.info("✅ Database tables initialized successfully")
                return True
                
            except Exception as e:
                logger.error(f"Failed to initialize tables: {e}")
                return False
    
    def store_message(self, 
                     channel: str,
                     user_phone: str,
                     user_name: str,
                     message_id: str,
                     content: str,
                     direction: str = "inbound",
                     message_type: str = "text",
                     ai_response: bool = False,
                     metadata: Dict = None) -> Optional[int]:
        """Store a message and create/update conversation"""
        
        with self.get_cursor() as cursor:
            if not cursor:
                return None
            
            try:
                # Find or create conversation
                cursor.execute("""
                    SELECT id FROM conversations 
                    WHERE user_phone = %s AND channel = %s 
                    AND status = 'active'
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (user_phone, channel))
                
                result = cursor.fetchone()
                
                if result:
                    conversation_id = result['id']
                    # Update conversation timestamp
                    cursor.execute("""
                        UPDATE conversations 
                        SET updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (conversation_id,))
                else:
                    # Create new conversation
                    cursor.execute("""
                        INSERT INTO conversations 
                        (channel, user_phone, user_name, metadata)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id
                    """, (channel, user_phone, user_name, 
                          psycopg2.extras.Json(metadata or {})))
                    conversation_id = cursor.fetchone()['id']
                
                # Store the message
                cursor.execute("""
                    INSERT INTO messages 
                    (conversation_id, external_id, direction, message_type, 
                     content, ai_response, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (external_id) DO NOTHING
                    RETURNING id
                """, (conversation_id, message_id, direction, message_type,
                      content, ai_response, psycopg2.extras.Json(metadata or {})))
                
                result = cursor.fetchone()
                if result:
                    logger.info(f"Message stored: {message_id} in conversation {conversation_id}")
                    return conversation_id
                else:
                    logger.debug(f"Message already exists: {message_id}")
                    return conversation_id
                    
            except Exception as e:
                logger.error(f"Failed to store message: {e}")
                return None
    
    def get_conversation_history(self, 
                                 conversation_id: int = None,
                                 user_phone: str = None,
                                 limit: int = 10) -> List[Dict]:
        """Get conversation history"""
        
        with self.get_cursor() as cursor:
            if not cursor:
                return []
            
            try:
                if conversation_id:
                    cursor.execute("""
                        SELECT m.*, c.user_name, c.channel
                        FROM messages m
                        JOIN conversations c ON m.conversation_id = c.id
                        WHERE m.conversation_id = %s
                        ORDER BY m.created_at DESC
                        LIMIT %s
                    """, (conversation_id, limit))
                elif user_phone:
                    cursor.execute("""
                        SELECT m.*, c.user_name, c.channel
                        FROM messages m
                        JOIN conversations c ON m.conversation_id = c.id
                        WHERE c.user_phone = %s
                        ORDER BY m.created_at DESC
                        LIMIT %s
                    """, (user_phone, limit))
                else:
                    return []
                
                messages = cursor.fetchall()
                return list(reversed(messages))  # Return in chronological order
                
            except Exception as e:
                logger.error(f"Failed to get conversation history: {e}")
                return []
    
    def get_venue_by_phone(self, phone_number: str) -> Optional[Dict]:
        """Get venue details by phone number"""
        
        with self.get_cursor() as cursor:
            if not cursor:
                return None
            
            try:
                cursor.execute("""
                    SELECT * FROM venues 
                    WHERE phone_number = %s AND active = true
                    LIMIT 1
                """, (phone_number,))
                
                return cursor.fetchone()
                
            except Exception as e:
                logger.error(f"Failed to get venue: {e}")
                return None
    
    def close(self):
        """Close database connection"""
        if self.connection and not self.connection.closed:
            self.connection.close()
            logger.info("Database connection closed")


# Create global database manager instance
db_manager = DatabaseManager()
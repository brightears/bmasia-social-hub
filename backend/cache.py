"""
Redis cache management for BMA Social
Handles caching of venue data, bot responses, and session management
"""

import os
import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import redis

logger = logging.getLogger(__name__)

# Redis connection URL from environment
REDIS_URL = os.environ.get('REDIS_URL')
if REDIS_URL and REDIS_URL.startswith('redis://'):
    # Ensure proper format
    pass
else:
    logger.warning("No valid REDIS_URL found")

class CacheManager:
    """Manage Redis cache operations"""
    
    def __init__(self):
        self.client = None
        self.connect()
    
    def connect(self):
        """Establish Redis connection"""
        if not REDIS_URL:
            logger.warning("No REDIS_URL found - cache features disabled")
            return False
        
        try:
            self.client = redis.from_url(REDIS_URL, decode_responses=True)
            # Test connection
            self.client.ping()
            logger.info("✅ Redis cache connected successfully")
            return True
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            self.client = None
            return False
    
    def ensure_connection(self):
        """Ensure Redis connection is active"""
        if self.client is None:
            return self.connect()
        try:
            self.client.ping()
            return True
        except:
            return self.connect()
    
    # Venue caching methods
    
    def cache_venue(self, phone_number: str, venue_data: Dict, ttl: int = 3600):
        """Cache venue data by phone number (1 hour default)"""
        if not self.ensure_connection():
            return False
        
        try:
            key = f"venue:phone:{phone_number}"
            self.client.setex(
                key,
                ttl,
                json.dumps(venue_data)
            )
            logger.debug(f"Cached venue data for {phone_number}")
            return True
        except Exception as e:
            logger.error(f"Failed to cache venue: {e}")
            return False
    
    def get_venue(self, phone_number: str) -> Optional[Dict]:
        """Get cached venue data by phone number"""
        if not self.ensure_connection():
            return None
        
        try:
            key = f"venue:phone:{phone_number}"
            data = self.client.get(key)
            if data:
                logger.debug(f"Cache hit for venue {phone_number}")
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Failed to get cached venue: {e}")
            return None
    
    # Conversation session caching
    
    def cache_conversation_context(self, 
                                  user_phone: str, 
                                  context: Dict, 
                                  ttl: int = 900):
        """Cache conversation context (15 minutes default)"""
        if not self.ensure_connection():
            return False
        
        try:
            key = f"conversation:context:{user_phone}"
            self.client.setex(
                key,
                ttl,
                json.dumps(context)
            )
            logger.debug(f"Cached conversation context for {user_phone}")
            return True
        except Exception as e:
            logger.error(f"Failed to cache conversation context: {e}")
            return False
    
    def get_conversation_context(self, user_phone: str) -> Optional[Dict]:
        """Get cached conversation context"""
        if not self.ensure_connection():
            return None
        
        try:
            key = f"conversation:context:{user_phone}"
            data = self.client.get(key)
            if data:
                logger.debug(f"Cache hit for conversation context {user_phone}")
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Failed to get conversation context: {e}")
            return None
    
    # Response caching for common questions
    
    def cache_response(self, question_hash: str, response: str, ttl: int = 3600):
        """Cache bot response for common questions (1 hour default)"""
        if not self.ensure_connection():
            return False
        
        try:
            key = f"response:hash:{question_hash}"
            self.client.setex(
                key,
                ttl,
                response
            )
            logger.debug(f"Cached response for question hash {question_hash}")
            return True
        except Exception as e:
            logger.error(f"Failed to cache response: {e}")
            return False
    
    def get_cached_response(self, question_hash: str) -> Optional[str]:
        """Get cached bot response"""
        if not self.ensure_connection():
            return None
        
        try:
            key = f"response:hash:{question_hash}"
            response = self.client.get(key)
            if response:
                logger.debug(f"Cache hit for response {question_hash}")
                return response
            return None
        except Exception as e:
            logger.error(f"Failed to get cached response: {e}")
            return None
    
    # Rate limiting
    
    def check_rate_limit(self, user_phone: str, max_requests: int = 10, window: int = 60) -> bool:
        """Check if user has exceeded rate limit (10 requests per minute default)"""
        if not self.ensure_connection():
            return True  # Allow if Redis is down
        
        try:
            key = f"rate_limit:{user_phone}"
            current = self.client.incr(key)
            
            if current == 1:
                # First request, set expiry
                self.client.expire(key, window)
            
            if current > max_requests:
                logger.warning(f"Rate limit exceeded for {user_phone}: {current} requests")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            return True  # Allow on error
    
    # Statistics and monitoring
    
    def increment_counter(self, counter_name: str, amount: int = 1):
        """Increment a counter (for statistics)"""
        if not self.ensure_connection():
            return
        
        try:
            key = f"stats:counter:{counter_name}"
            self.client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Failed to increment counter: {e}")
    
    def get_counter(self, counter_name: str) -> int:
        """Get counter value"""
        if not self.ensure_connection():
            return 0
        
        try:
            key = f"stats:counter:{counter_name}"
            value = self.client.get(key)
            return int(value) if value else 0
        except Exception as e:
            logger.error(f"Failed to get counter: {e}")
            return 0
    
    # Health check
    
    def health_check(self) -> Dict:
        """Check Redis health and stats"""
        if not self.ensure_connection():
            return {"status": "disconnected"}
        
        try:
            info = self.client.info()
            return {
                "status": "connected",
                "version": info.get("redis_version", "unknown"),
                "memory_used": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands": info.get("total_commands_processed", 0)
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "error", "error": str(e)}
    
    def close(self):
        """Close Redis connection"""
        if self.client:
            try:
                self.client.close()
                logger.info("Redis connection closed")
            except:
                pass


# Create global cache manager instance
cache_manager = CacheManager()
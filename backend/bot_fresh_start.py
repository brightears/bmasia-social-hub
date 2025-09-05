"""
BMA Social WhatsApp Bot - Fresh Start
Clean implementation that actually reads venue data and responds intelligently
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from openai import OpenAI
from dotenv import load_dotenv

# Try to import redis but make it optional
try:
    import redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False
    redis = None

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VenueDataManager:
    """Manages venue data from markdown files"""
    
    def __init__(self):
        self.venues = {}
        self.load_venue_data()
    
    def load_venue_data(self):
        """Load venue data from venue_data.md"""
        try:
            with open('venue_data.md', 'r') as f:
                content = f.read()
                
            # Parse venues from markdown - split only on venue headers (### followed by venue name)
            import re
            venue_sections = re.split(r'\n### (?=\w)', content)
            
            for venue_section in venue_sections[1:]:  # Skip header
                lines = venue_section.strip().split('\n')
                if not lines:
                    continue
                    
                venue_name = lines[0].strip()
                venue_info = {
                    'name': venue_name,
                    'zones': [],
                    'contract_end': None,
                    'annual_price': None,
                    'platform': None,
                    'contacts': []
                }
                
                for line in lines[1:]:
                    if '**Zone Names**:' in line:
                        zones_text = line.split(':', 1)[1].strip()
                        venue_info['zones'] = [z.strip() for z in zones_text.split(',')]
                    elif '**Contract End**:' in line:
                        venue_info['contract_end'] = line.split(':', 1)[1].strip()
                    elif '**Annual Price per Zone**:' in line:
                        venue_info['annual_price'] = line.split(':', 1)[1].strip()
                    elif '**Music Platform**:' in line:
                        venue_info['platform'] = line.split(':', 1)[1].strip()
                
                # Store with lowercase key for easy lookup
                self.venues[venue_name.lower()] = venue_info
                
            logger.info(f"Loaded {len(self.venues)} venues: {list(self.venues.keys())}")
            
        except Exception as e:
            logger.error(f"Error loading venue data: {e}")
            # Fallback data so bot doesn't crash
            self.venues = {
                'hilton pattaya': {
                    'name': 'Hilton Pattaya',
                    'zones': ['Drift Bar', 'Edge', 'Horizon', 'Shore'],
                    'contract_end': '2025-10-31',
                    'annual_price': 'THB 12,000',
                    'platform': 'Soundtrack Your Brand'
                }
            }

    def find_venue(self, text: str) -> Optional[Dict]:
        """Find venue from user message"""
        text_lower = text.lower()
        
        # Direct venue name mentions
        for venue_key, venue_data in self.venues.items():
            if venue_key in text_lower or venue_key.replace(' ', '') in text_lower.replace(' ', ''):
                return venue_data
        
        # Common misspellings
        if 'hilton' in text_lower and 'pattay' in text_lower:
            return self.venues.get('hilton pattaya')
            
        return None
    
    def get_venue_info(self, venue_name: str) -> Optional[Dict]:
        """Get venue information by name"""
        return self.venues.get(venue_name.lower())


class ConversationBot:
    """Clean bot implementation that actually works"""
    
    def __init__(self):
        self.openai = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        # Use the correct GPT-5-Mini model with full name including date
        self.model = 'gpt-5-mini-2025-08-07'  # Correct GPT-5-Mini model name
        logger.info(f"Using OpenAI model: {self.model}")
        self.venue_manager = VenueDataManager()
        
        # Redis for conversation memory
        self.redis_enabled = False
        self.memory = {}
        
        if HAS_REDIS:
            try:
                self.redis_client = redis.Redis(
                    host=os.getenv('REDIS_HOST', 'localhost'),
                    port=int(os.getenv('REDIS_PORT', 6379)),
                    db=0,
                    decode_responses=True
                )
                self.redis_client.ping()
                self.redis_enabled = True
                logger.info("Redis connected for conversation memory")
            except:
                logger.info("Redis not available, using in-memory storage")
        else:
            logger.info("Redis module not installed, using in-memory storage")
    
    def get_conversation_context(self, phone: str) -> List[Dict]:
        """Get recent conversation history"""
        if self.redis_enabled:
            try:
                context = self.redis_client.get(f"conv:{phone}")
                if context:
                    return json.loads(context)
            except:
                pass
        else:
            return self.memory.get(phone, [])
        return []
    
    def save_conversation_context(self, phone: str, context: List[Dict]):
        """Save conversation history"""
        # Keep only last 10 messages
        context = context[-10:]
        
        if self.redis_enabled:
            try:
                self.redis_client.setex(
                    f"conv:{phone}",
                    600,  # 10 minute expiry
                    json.dumps(context)
                )
            except:
                pass
        else:
            self.memory[phone] = context
    
    def process_message(self, message: str, phone: str, user_name: Optional[str] = None) -> str:
        """Process incoming message and generate response"""
        
        # Get conversation history
        context = self.get_conversation_context(phone)
        
        # Check if venue is mentioned or already in context
        venue = self.venue_manager.find_venue(message)
        if not venue and context:
            # Check if venue was mentioned previously
            for msg in context:
                if 'venue' in msg:
                    venue = self.venue_manager.get_venue_info(msg['venue'])
                    break
        
        # Build system prompt with actual venue data
        system_prompt = self._build_system_prompt(venue)
        
        # Build messages for OpenAI
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history
        for msg in context[-4:]:  # Last 4 messages for context
            messages.append({"role": msg['role'], "content": msg['content']})
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        try:
            # Call OpenAI with proper parameters
            response = self.openai.chat.completions.create(
                model=self.model,
                messages=messages,
                # Note: GPT-5-Mini may have restrictions on temperature
                max_completion_tokens=300  # Correct parameter name
            )
            
            bot_response = response.choices[0].message.content
            
            # Check if response is None or empty
            if not bot_response:
                logger.warning(f"OpenAI returned empty response for message: {message}")
                # Return a fallback response
                if venue:
                    return f"Hello from {venue['name']}! How can I help you with your music system today?"
                else:
                    return "Hello! I'm here to help with your music system. Which venue are you calling from?"
            
            bot_response = bot_response.strip()
            logger.info(f"OpenAI response: {bot_response[:100]}...")  # Log first 100 chars
            
            # Update context
            context.append({"role": "user", "content": message})
            if venue:
                context.append({"role": "assistant", "content": bot_response, "venue": venue['name']})
            else:
                context.append({"role": "assistant", "content": bot_response})
            
            self.save_conversation_context(phone, context)
            
            return bot_response
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            
            # Fallback response with actual data if we have venue
            if venue:
                if 'contract' in message.lower() or 'renewal' in message.lower():
                    return f"Your contract at {venue['name']} expires on {venue['contract_end']}. Would you like me to have someone contact you about renewal options?"
                elif 'zone' in message.lower():
                    zones = ', '.join(venue['zones'])
                    return f"You have {len(venue['zones'])} zones at {venue['name']}: {zones}. Which zone would you like help with?"
                elif 'price' in message.lower() or 'cost' in message.lower():
                    return f"Your current rate is {venue['annual_price']} per zone annually. You have {len(venue['zones'])} zones."
            
            return "I'm here to help with your music system! Could you tell me your venue name and what you need help with?"
    
    def _build_system_prompt(self, venue: Optional[Dict]) -> str:
        """Build system prompt with actual venue data"""
        
        base_prompt = """You are a friendly music system support bot for BMA Social. 
You help venues with their background music systems.
Be conversational and natural, not robotic.

IMPORTANT: 
- Always use actual data, never make up information
- If you don't have specific information, ask for it
- Be helpful and proactive about offering assistance
"""
        
        if venue:
            venue_details = f"""
Current venue information:
- Venue: {venue['name']}
- Music Zones: {', '.join(venue['zones'])}
- Contract expires: {venue['contract_end']}
- Annual price per zone: {venue['annual_price']}
- Platform: {venue['platform']}

When the user asks about their contract, zones, or pricing, use this ACTUAL data.
Never make up dates or information.
"""
            return base_prompt + venue_details
        
        else:
            return base_prompt + """
The user hasn't mentioned their venue yet. 
Politely ask them which venue they're calling from so you can help them better.
Common venues include: Hilton Pattaya, Mana Beach Club, and others.
"""


# Create bot instance
bot = ConversationBot()

def handle_whatsapp_message(message: str, from_number: str) -> str:
    """Main entry point for WhatsApp messages"""
    logger.info(f"Processing message from {from_number}: {message}")
    
    response = bot.process_message(message, from_number)
    
    logger.info(f"Responding with: {response}")
    return response

# Also make the bot instance available as music_bot for compatibility
music_bot = bot
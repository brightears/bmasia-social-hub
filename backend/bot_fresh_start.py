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

# Import Soundtrack API
try:
    from soundtrack_api import SoundtrackAPI
    HAS_SOUNDTRACK = True
except ImportError:
    HAS_SOUNDTRACK = False
    SoundtrackAPI = None

# Import Google Chat for notifications
try:
    from google_chat_client import GoogleChatClient, Department, Priority
    HAS_GOOGLE_CHAT = True
except ImportError:
    HAS_GOOGLE_CHAT = False
    GoogleChatClient = None

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
                    'account_id': None,
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
                    elif '**Soundtrack Account ID**:' in line:
                        venue_info['account_id'] = line.split(':', 1)[1].strip()
                
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
        # Use gpt-4o-mini which definitely works and is accessible
        self.model = 'gpt-4o-mini'  # Using verified working model
        logger.info(f"Using OpenAI model: {self.model}")
        self.venue_manager = VenueDataManager()
        
        # Initialize Soundtrack API if available
        self.soundtrack = None
        if HAS_SOUNDTRACK:
            try:
                self.soundtrack = SoundtrackAPI()
                logger.info("Soundtrack API initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Soundtrack API: {e}")
        else:
            logger.info("Soundtrack API not available")
        
        # Initialize Google Chat for notifications
        self.google_chat = None
        if HAS_GOOGLE_CHAT:
            try:
                self.google_chat = GoogleChatClient()
                logger.info("Google Chat client initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Google Chat: {e}")
        else:
            logger.info("Google Chat not available")
        
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
    
    def check_zone_music(self, venue_name: str, zone_name: str, venue_data: Dict) -> str:
        """Check what's playing at a specific zone"""
        if not self.soundtrack:
            return "I cannot access the Soundtrack API right now to check what's playing."
        
        try:
            # Get account ID from venue data
            account_id = venue_data.get('account_id')
            
            if account_id and venue_data.get('platform') == 'Soundtrack Your Brand':
                logger.info(f"Using account ID from venue data: {account_id}")
                
                # Get all zones for this account
                account_data = self.soundtrack.get_account_by_id(account_id)
                
                if not account_data:
                    logger.error(f"Could not fetch account data for ID: {account_id}")
                    return f"I couldn't access the Soundtrack account for {venue_name}."
                
                # Find the specific zone in the account
                target_zone = None
                all_zones = []
                
                for loc_edge in account_data.get('locations', {}).get('edges', []):
                    location = loc_edge.get('node', {})
                    for zone_edge in location.get('soundZones', {}).get('edges', []):
                        zone = zone_edge.get('node', {})
                        zone_name_api = zone.get('name', '')
                        all_zones.append(zone_name_api)
                        
                        # Match zone name (case insensitive)
                        if zone_name.lower() in zone_name_api.lower() or zone_name_api.lower() in zone_name.lower():
                            target_zone = zone
                            logger.info(f"Found matching zone: {zone_name_api} with ID: {zone.get('id')}")
                            break
                    if target_zone:
                        break
                
                if not target_zone:
                    return f"I couldn't find the zone '{zone_name}' at {venue_name}. Available zones are: {', '.join(all_zones)}"
                
                # Get zone status
                zone_status = self.soundtrack.get_zone_status(target_zone['id'])
                logger.info(f"Zone status for {zone_name}: {zone_status}")
            else:
                # Venue doesn't use Soundtrack or no account ID
                if venue_data.get('platform') != 'Soundtrack Your Brand':
                    return f"{venue_name} uses {venue_data.get('platform', 'a different platform')}, not Soundtrack Your Brand, so I can't check what's playing."
                else:
                    return f"I don't have the Soundtrack account ID for {venue_name} to check what's playing."
            
            if 'error' in zone_status:
                return f"I couldn't check the status of {zone_name}: {zone_status['error']}"
            
            # Build response based on actual API response
            # The API returns 'playing' not 'is_playing'
            if zone_status.get('playing') or zone_status.get('playback_state') == 'playing':
                playlist = zone_status.get('current_playlist', 'Unknown playlist')
                current_track = zone_status.get('current_track', {})
                track_info = ""
                if current_track:
                    track_name = current_track.get('name', '')
                    artist = current_track.get('artist', '')
                    if track_name and artist:
                        track_info = f"\n🎵 Now playing: {track_name} by {artist}"
                    elif track_name:
                        track_info = f"\n🎵 Now playing: {track_name}"
                
                volume = zone_status.get('volume')
                volume_info = f" Volume is set to {volume}%." if volume else ""
                
                return f"{zone_name} is currently playing from the playlist: {playlist}.{volume_info}{track_info}"
            else:
                # Provide more detail about why it's not playing
                if not zone_status.get('device_online'):
                    return f"{zone_name} appears to be offline. The Soundtrack player may be disconnected or powered off."
                elif zone_status.get('playback_state') == 'paused':
                    return f"{zone_name} is currently paused. The music can be resumed from the Soundtrack app."
                else:
                    return f"{zone_name} is currently not playing any music. Device is {zone_status.get('playback_state', 'unknown')}"
            
        except Exception as e:
            logger.error(f"Error checking zone music: {e}")
            return "I encountered an error while checking the music status. Please try again later."
    
    def change_playlist(self, venue_name: str, zone_name: str, playlist_suggestion: str) -> str:
        """Change playlist for a zone or provide suggestions"""
        if not self.soundtrack:
            return "I cannot change playlists right now as the Soundtrack API is not available."
        
        # Common playlist suggestions based on time and mood
        playlist_suggestions = {
            'chill': ['Chill Lounge', 'Smooth Jazz', 'Acoustic Chill', 'Bossa Nova'],
            'upbeat': ['Pop Hits', 'Feel Good Vibes', 'Dance Mix', 'Happy Hour'],
            'dinner': ['Jazz Standards', 'Classical Dinner', 'Soft Rock', 'Evening Jazz'],
            'party': ['Party Mix', 'Dance Hits', 'Friday Night', 'Weekend Vibes'],
            'morning': ['Morning Coffee', 'Breakfast Jazz', 'Easy Morning', 'Sunrise Sessions'],
            'afternoon': ['Afternoon Delight', 'Lunch Vibes', 'Daytime Mix', 'Casual Dining']
        }
        
        # Provide suggestions based on request
        response = f"For {zone_name}, I'd recommend these playlists:\n\n"
        
        for mood, playlists in playlist_suggestions.items():
            if mood in playlist_suggestion.lower():
                response += f"🎵 {mood.title()} Options:\n"
                for playlist in playlists:
                    response += f"  • {playlist}\n"
                response += "\n"
        
        response += "To change the playlist, you can:\n"
        response += "1. Open your Soundtrack app\n"
        response += "2. Select the zone and choose from available playlists\n\n"
        response += "Would you like our music design team to create a custom playlist for your venue? They can craft something unique for your brand! 🎨"
        
        return response
    
    def send_support_notification(self, venue_name: str, issue: str, phone: str) -> bool:
        """Send notification to support team via Google Chat"""
        if not self.google_chat:
            return False
        
        try:
            # Get venue data if available
            venue_data = self.venue_manager.get_venue_info(venue_name) if venue_name else None
            
            # Send notification via Google Chat
            success = self.google_chat.send_notification(
                message=issue,
                venue_name=venue_name,
                venue_data=venue_data,
                user_info={'phone': phone, 'platform': 'WhatsApp'}
            )
            
            if success:
                logger.info(f"Support notification sent for {venue_name}: {issue[:50]}...")
            
            return success
        except Exception as e:
            logger.error(f"Failed to send support notification: {e}")
            return False
    
    def provide_music_advice(self, venue_name: str, zone_name: str, request: str) -> str:
        """Provide music design advice and playlist suggestions"""
        request_lower = request.lower()
        current_hour = datetime.now().hour
        
        # Enhanced playlist database with moods and times
        playlist_database = {
            'breakfast': {
                'playlists': ['Morning Coffee Jazz', 'Easy Breakfast', 'Sunrise Acoustic', 'Morning Classics'],
                'advice': 'For breakfast, create an energizing yet relaxed atmosphere. Keep volume moderate (50-60%) to allow conversation.',
                'best_time': '6:00-10:00'
            },
            'lunch': {
                'playlists': ['Lunch Lounge', 'Midday Jazz', 'Acoustic Lunch', 'Business Casual'],
                'advice': 'Lunch music should be upbeat but not distracting. Aim for 60-70% volume with lighter genres.',
                'best_time': '11:30-14:00'
            },
            'dinner': {
                'playlists': ['Dinner Jazz Elegance', 'Evening Standards', 'Wine & Dine', 'Sophisticated Dining'],
                'advice': 'Dinner requires sophisticated ambiance. Start mellow and gradually increase energy. Volume 55-65%.',
                'best_time': '18:00-22:00'
            },
            'happy_hour': {
                'playlists': ['Happy Hour Hits', 'After Work Party', 'Friday Feeling', 'Cocktail Lounge'],
                'advice': 'Happy hour needs energy! Go for upbeat, familiar songs at 70-80% volume to create buzz.',
                'best_time': '17:00-19:00'
            },
            'late_night': {
                'playlists': ['Late Night Lounge', 'Deep House Nights', 'Midnight Jazz', 'After Hours'],
                'advice': 'Late night should be smooth and sophisticated. Keep it cool with 65-75% volume.',
                'best_time': '22:00-02:00'
            },
            'chill': {
                'playlists': ['Chill Out Lounge', 'Downtempo Dreams', 'Ambient Atmosphere', 'Relaxed Vibes'],
                'advice': 'For a chill atmosphere, use downtempo tracks with minimal vocals. Volume around 50-60%.',
                'best_time': 'Any time'
            },
            'party': {
                'playlists': ['Party Anthems', 'Dance Floor Fillers', 'Weekend Party Mix', 'Celebration Hits'],
                'advice': 'Party mode needs high energy! Use recognizable hits at 75-85% volume. Build energy gradually.',
                'best_time': 'Fri-Sat nights'
            },
            'romantic': {
                'playlists': ['Romantic Evening', 'Love Songs Collection', 'Candlelight Jazz', 'Intimate Moments'],
                'advice': 'For romance, use soft jazz or acoustic at 45-55% volume. Avoid songs with heavy beats.',
                'best_time': 'Evenings'
            }
        }
        
        # Detect what kind of advice they need
        detected_mood = None
        for mood in playlist_database.keys():
            if mood in request_lower or (mood == 'breakfast' and 'morning' in request_lower):
                detected_mood = mood
                break
        
        # Check time-based suggestion if no specific mood detected
        if not detected_mood:
            if 'suggest' in request_lower or 'recommend' in request_lower or 'what should' in request_lower:
                if 6 <= current_hour < 11:
                    detected_mood = 'breakfast'
                elif 11 <= current_hour < 15:
                    detected_mood = 'lunch'
                elif 17 <= current_hour < 19:
                    detected_mood = 'happy_hour'
                elif 18 <= current_hour < 22:
                    detected_mood = 'dinner'
                else:
                    detected_mood = 'late_night'
        
        # Build response with design advice
        if detected_mood:
            mood_data = playlist_database[detected_mood]
            response = f"🎵 **Music Design Advice for {zone_name} at {venue_name}**\n\n"
            response += f"**Recommended Playlists:**\n"
            for playlist in mood_data['playlists']:
                response += f"• {playlist}\n"
            response += f"\n**Design Tips:** {mood_data['advice']}\n"
            response += f"**Best Time:** {mood_data['best_time']}\n"
            
            # Add current status if available
            if self.soundtrack:
                response += f"\n📊 I can check what's currently playing or help you switch playlists. "
            
            response += "\nWould you like me to notify our music design team to implement these changes?"
            
        else:
            # Provide general design consultation
            response = f"🎨 **Music Design Consultation for {zone_name} at {venue_name}**\n\n"
            response += "I can help you create the perfect atmosphere! Consider:\n\n"
            response += "**🌅 Morning (6-11am):** Start gentle with jazz or acoustic\n"
            response += "**☀️ Lunch (11-3pm):** Upbeat but professional\n"
            response += "**🍸 Happy Hour (5-7pm):** Build energy with pop hits\n"
            response += "**🍽️ Dinner (6-10pm):** Sophisticated and elegant\n"
            response += "**🌙 Late Night (10pm+):** Smooth and atmospheric\n\n"
            
            response += "**Pro Tips:**\n"
            response += "• Match music energy to crowd energy\n"
            response += "• Consider your target demographic\n"
            response += "• Volume should allow conversation\n"
            response += "• Change playlists every 2-3 hours\n\n"
            
            response += "What kind of atmosphere are you trying to create? I can provide specific recommendations!"
        
        return response
    
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
        
        # Check if asking about music playing in a specific zone
        message_lower = message.lower()
        if venue:
            # Check for music status requests
            if 'playing' in message_lower or 'current' in message_lower:
                for zone_name in venue.get('zones', []):
                    if zone_name.lower() in message_lower:
                        music_status = self.check_zone_music(venue['name'], zone_name, venue)
                        
                        # Add to context and return
                        context.append({"role": "user", "content": message})
                        context.append({"role": "assistant", "content": music_status, "venue": venue['name']})
                        self.save_conversation_context(phone, context)
                        
                        return music_status
            
            # Check for playlist change or design advice requests
            if any(word in message_lower for word in ['change', 'switch', 'playlist', 'music', 'suggest', 'recommendation', 'chill', 'upbeat', 'party', 'dinner', 'morning', 'afternoon', 'design', 'atmosphere', 'mood', 'vibe']):
                # Find which zone they're asking about
                zone_name = None
                for zone in venue.get('zones', []):
                    if zone.lower() in message_lower:
                        zone_name = zone
                        break
                
                # If no specific zone mentioned, provide general advice
                if not zone_name and venue.get('zones'):
                    zone_name = venue['zones'][0]  # Default to first zone
                
                if zone_name:
                    playlist_response = self.provide_music_advice(venue['name'], zone_name, message)
                    
                    # Add to context and return
                    context.append({"role": "user", "content": message})
                    context.append({"role": "assistant", "content": playlist_response, "venue": venue['name']})
                    self.save_conversation_context(phone, context)
                    
                    return playlist_response
        
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
            logger.info(f"Calling OpenAI with model: {self.model}, message count: {len(messages)}")
            
            # Call OpenAI with proper parameters
            response = self.openai.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,  # Natural conversation temperature
                max_completion_tokens=300  # Correct parameter name
            )
            
            logger.info(f"OpenAI API response received: {response}")
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
            
            # Check if bot can't help and needs human assistance
            cant_help_phrases = [
                "i'm not sure", "i don't know", "i cannot help", "i can't help",
                "contact support", "reach out to", "call our team", "email us",
                "i apologize but", "unable to assist", "beyond my capabilities"
            ]
            
            needs_human = any(phrase in bot_response.lower() for phrase in cant_help_phrases)
            
            # Check if this is a complex issue that needs human help
            complex_keywords = [
                'technical problem', 'completely broken', 'not working at all',
                'urgent', 'emergency', 'legal', 'contract dispute', 'refund',
                'compensation', 'complaint', 'unhappy', 'frustrated'
            ]
            
            is_complex = any(keyword in message.lower() for keyword in complex_keywords)
            
            # Send Google Chat notification if needed
            if (needs_human or is_complex) and self.google_chat:
                issue_summary = f"Customer needs assistance: {message[:200]}"
                if needs_human:
                    issue_summary = f"Bot unable to help - {message[:200]}"
                elif is_complex:
                    issue_summary = f"Complex issue detected - {message[:200]}"
                
                notification_sent = self.send_support_notification(
                    venue_name=venue['name'] if venue else 'Unknown Venue',
                    issue=issue_summary,
                    phone=phone
                )
                
                if notification_sent:
                    # Append notification to response
                    bot_response += "\n\n📞 I've notified our support team about your request. They'll be in touch with you shortly to help resolve this issue."
                    logger.info(f"Google Chat notification sent for complex/unhandled issue")
            
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
        
        soundtrack_info = ""
        if self.soundtrack:
            soundtrack_info = """
I can check what's playing at specific zones using the Soundtrack Your Brand API.
Just ask me about a specific zone like "What's playing at Edge?" and I'll check for you.
"""
        
        base_prompt = f"""You are a friendly music system support bot for BMA Social. 
You help venues with their background music systems.
Be conversational and natural, not robotic.

KEY CAPABILITIES:
- Check what's currently playing at any zone
- Provide music design advice and playlist recommendations
- Suggest playlists for different times (breakfast, lunch, dinner, happy hour)
- Recommend music for different moods (chill, upbeat, romantic, party)
- Give professional tips on volume levels (50-85% depending on time/mood)
- Help with atmosphere creation and brand alignment
{soundtrack_info}
MUSIC EXPERTISE:
- Morning (6-11am): Gentle jazz/acoustic at 50-60% volume
- Lunch (11-3pm): Upbeat but professional at 60-70%
- Happy Hour (5-7pm): Energy builders at 70-80%
- Dinner (6-10pm): Sophisticated elegance at 55-65%
- Late Night (10pm+): Smooth atmospheric at 65-75%

IMPORTANT: 
- Always use actual data, never make up information
- If you don't have specific information, ask for it
- Be helpful and proactive about offering assistance
- Offer to connect them with our design team for custom playlists
- If you can't help with something, say you'll get our team to assist
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
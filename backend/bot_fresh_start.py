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

# Also try webhook-based Google Chat (simpler, no credentials needed)
try:
    from google_chat_webhook import google_chat_webhook
    HAS_WEBHOOK = True
except ImportError:
    HAS_WEBHOOK = False
    google_chat_webhook = None

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
        self.use_webhook = False
        
        # Try webhook first (simpler, no credentials needed)
        if HAS_WEBHOOK and google_chat_webhook and google_chat_webhook.webhook_url:
            self.google_chat = google_chat_webhook
            self.use_webhook = True
            logger.info("✅ Using Google Chat webhook for notifications")
        # Fall back to service account method
        elif HAS_GOOGLE_CHAT:
            try:
                self.google_chat = GoogleChatClient()
                logger.info("Google Chat client initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Google Chat: {e}")
        else:
            logger.info("Google Chat not available - notifications disabled")
        
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
            logger.warning("Google Chat not available - notification cannot be sent")
            logger.warning("To enable notifications:")
            logger.warning("Option 1: Add GOOGLE_CHAT_WEBHOOK_URL to .env (easier)")
            logger.warning("Option 2: Add GOOGLE_CREDENTIALS_JSON to .env")
            return False
        
        try:
            # Get venue data if available
            venue_data = self.venue_manager.get_venue_info(venue_name) if venue_name else None
            
            # Determine priority based on issue
            priority = "Normal"
            if any(word in issue.lower() for word in ['urgent', 'emergency', 'critical', 'broken', 'offline']):
                priority = "High"
            if any(word in issue.lower() for word in ['completely broken', 'all zones', 'legal', 'lawsuit']):
                priority = "Critical"
            
            # Send notification via Google Chat (webhook or service account)
            if self.use_webhook:
                # Using webhook method (simpler)
                success = self.google_chat.send_notification(
                    message=issue,
                    venue_name=venue_name,
                    venue_data=venue_data,
                    user_info={'phone': phone, 'platform': 'WhatsApp'},
                    priority=priority
                )
            else:
                # Using service account method
                success = self.google_chat.send_notification(
                    message=issue,
                    venue_name=venue_name,
                    venue_data=venue_data,
                    user_info={'phone': phone, 'platform': 'WhatsApp'}
                )
            
            if success:
                logger.info(f"✅ Support notification sent for {venue_name}: {issue[:50]}...")
            else:
                logger.error(f"❌ Support notification failed for {venue_name}: {issue[:50]}...")
            
            return success
        except Exception as e:
            logger.error(f"❌ Failed to send support notification: {e}")
            return False
    
    def execute_music_change(self, venue_name: str, zone_name: str, request: str, venue_data: Dict, phone: str = "WhatsApp") -> str:
        """Execute actual music changes via Soundtrack API"""
        logger.info(f"=== EXECUTE_MUSIC_CHANGE CALLED ===")
        logger.info(f"Venue: {venue_name}, Zone: {zone_name}, Request: {request}")
        
        if not self.soundtrack or not venue_data:
            logger.warning("No Soundtrack API or venue data available")
            return self.provide_music_advice(venue_name, zone_name, request)
        
        request_lower = request.lower()
        account_id = venue_data.get('account_id')
        
        if not account_id:
            logger.warning(f"No account_id for venue: {venue_name}")
            return "I can provide advice but need your account ID to make changes. Let me help with recommendations instead:\n\n" + self.provide_music_advice(venue_name, zone_name, request)
        
        # Get zone ID for the specific zone
        try:
            account_data = self.soundtrack.get_account_by_id(account_id)
            if not account_data:
                return self.provide_music_advice(venue_name, zone_name, request)
            
            # Find the specific zone using the correct API structure
            zone_id = None
            all_zones = []
            
            for loc_edge in account_data.get('locations', {}).get('edges', []):
                location = loc_edge.get('node', {})
                for zone_edge in location.get('soundZones', {}).get('edges', []):
                    zone = zone_edge.get('node', {})
                    zone_name_api = zone.get('name', '')
                    all_zones.append(zone_name_api)
                    
                    # Match zone name (case insensitive)
                    if zone_name.lower() in zone_name_api.lower() or zone_name_api.lower() in zone_name.lower():
                        zone_id = zone.get('id')
                        logger.info(f"Found matching zone: {zone_name_api} with ID: {zone.get('id')}")
                        break
                if zone_id:
                    break
            
            if not zone_id:
                return f"I couldn't find zone '{zone_name}'. Available zones: {', '.join(all_zones)}"
            
            # PLAYLIST CHANGE - Check this FIRST before play/pause
            # "Play jazz" or "play chillhop" = playlist request (but we can't do it)
            music_genres = ['jazz', 'chillhop', 'chill', 'rock', 'pop', 'classical', 'hip hop', 'hiphop', 
                          'dance', 'acoustic', 'ambient', 'lounge', '80s', '90s', 'dinner', 'party', 
                          'relaxing', 'smooth', 'easy listening', 'background']
            
            # Check if "play" is followed by ANY music-related words
            if 'play' in request_lower:
                words_after_play = request_lower.split('play')[1].strip() if 'play' in request_lower else ""
                if words_after_play and words_after_play not in ['music', 'the music', 'it']:
                    logger.info(f"Detected playlist change request: 'play' + '{words_after_play}'")
                    return self.handle_playlist_request(zone_id, zone_name, request, venue_name=venue['name'], phone=phone)
            
            # Other playlist change keywords
            elif any(word in request_lower for word in ['playlist', 'change music', 'switch to', 'put on', 'change to', 'some music', 'try', 'let\'s try']):
                logger.info(f"Detected playlist change request: explicit keywords")
                return self.handle_playlist_request(zone_id, zone_name, request, venue_name=venue['name'], phone=phone)
            
            # VOLUME CONTROL
            elif any(word in request_lower for word in ['volume', 'louder', 'quieter', 'loud', 'soft']):
                return self.control_volume(zone_id, zone_name, request)
            
            # SKIP TRACK
            elif any(word in request_lower for word in ['skip', 'next song', 'next track', 'change song']):
                result = self.soundtrack.skip_track(zone_id)
                if result:
                    return f"✅ Done! Skipped to the next track in {zone_name}. 🎵"
                else:
                    response = f"I couldn't skip the track. Let me notify our support team to help."
                    notification_sent = self.send_support_notification(
                        venue_name=zone_name,
                        issue=f"Skip track failed for zone {zone_name}",
                        phone="WhatsApp"
                    )
                    if notification_sent:
                        response += "\n\n📞 Our team has been notified and will help you shortly!"
                    else:
                        response += "\n\n📞 Please contact our support team directly for assistance with this issue."
                    return response
            
            # PAUSE
            elif 'pause' in request_lower or 'stop' in request_lower:
                result = self.soundtrack.control_playback(zone_id, 'pause')
                if result.get('success'):
                    return f"✅ Done! Music paused in {zone_name}. ⏸️\n\nJust say 'play' or 'resume' when you're ready to continue."
                else:
                    response = "I couldn't pause the playback. Let me notify our support team."
                    notification_sent = self.send_support_notification(
                        venue_name=zone_name,
                        issue=f"Pause command failed for zone {zone_name}",
                        phone="WhatsApp"
                    )
                    if notification_sent:
                        response += "\n\n📞 Our team has been notified and will help you shortly!"
                    else:
                        response += "\n\n📞 Please contact our support team directly for assistance with this issue."
                    return response
            
            # RESUME/PLAY (only if NOT followed by a genre)
            elif ('play' in request_lower or 'resume' in request_lower or 'start' in request_lower) and not any(genre in request_lower for genre in music_genres):
                result = self.soundtrack.control_playback(zone_id, 'play')
                if result.get('success'):
                    return f"✅ Music resumed in {zone_name}! 🎵"
                else:
                    response = "I couldn't resume playback. Let me notify our support team."
                    notification_sent = self.send_support_notification(
                        venue_name=zone_name,
                        issue=f"Play/resume command failed for zone {zone_name}",
                        phone="WhatsApp"
                    )
                    if notification_sent:
                        response += "\n\n📞 Our team has been notified and will help you shortly!"
                    else:
                        response += "\n\n📞 Please contact our support team directly for assistance with this issue."
                    return response
            
            # If no specific action detected, provide advice
            else:
                return self.provide_music_advice(venue_name, zone_name, request)
                
        except Exception as e:
            logger.error(f"Error executing music change: {e}")
            return self.provide_music_advice(venue_name, zone_name, request)
    
    def control_volume(self, zone_id: str, zone_name: str, request: str) -> str:
        """Control volume for a zone"""
        request_lower = request.lower()
        
        # Parse volume request
        if 'louder' in request_lower or 'up' in request_lower or 'increase' in request_lower:
            # Increase by 2 points (on 0-16 scale)
            current_zone = self.soundtrack.get_zone_status(zone_id)
            if current_zone and 'volume' in current_zone:
                current_vol = current_zone['volume']
                new_vol = min(16, current_vol + 2)
            else:
                new_vol = 10  # Default medium-high
        
        elif 'quieter' in request_lower or 'down' in request_lower or 'decrease' in request_lower:
            # Decrease by 2 points
            current_zone = self.soundtrack.get_zone_status(zone_id)
            if current_zone and 'volume' in current_zone:
                current_vol = current_zone['volume']
                new_vol = max(0, current_vol - 2)
            else:
                new_vol = 8  # Default medium
        
        elif 'mute' in request_lower or 'silent' in request_lower:
            new_vol = 0
        
        elif 'max' in request_lower or 'maximum' in request_lower:
            new_vol = 16
        
        else:
            # Try to extract specific percentage
            import re
            percent_match = re.search(r'(\d+)\s*%', request_lower)
            if percent_match:
                percent = int(percent_match.group(1))
                new_vol = int((percent / 100) * 16)
            else:
                # Default moderate volume
                new_vol = 10
        
        # Set the volume IMMEDIATELY
        result = self.soundtrack.set_volume(zone_id, new_vol)
        
        if result.get('success'):
            percent = int((new_vol / 16) * 100)
            return f"✅ Done! Volume is now {percent}% in {zone_name}. 🔊"
        else:
            error = result.get('error', 'Unknown error')
            response = f"I couldn't adjust the volume ({error}). Let me notify our support team."
            
            notification_sent = self.send_support_notification(
                venue_name=zone_name,
                issue=f"Volume control failed: {error}",
                phone="WhatsApp"
            )
            if notification_sent:
                response += "\n\n📞 Our team has been notified and will help you shortly!"
            else:
                response += "\n\n📞 Please contact our support team directly for assistance with this issue."
            
            return response
    
    def handle_playlist_request(self, zone_id: str, zone_name: str, request: str, venue_name: str = None, phone: str = "WhatsApp") -> str:
        """Handle playlist change requests with team escalation"""
        logger.info(f"=== HANDLE_PLAYLIST_REQUEST CALLED ===")
        logger.info(f"Zone ID: {zone_id}, Zone Name: {zone_name}, Request: {request}")
        
        request_lower = request.lower()
        
        # Extract what playlist they want
        action_words = ['play', 'let\'s try', 'try', 'switch to', 'change to', 'put on', 'play some', 'change']
        cleaned_request = request_lower
        for action in action_words:
            if cleaned_request.startswith(action + ' '):
                cleaned_request = cleaned_request[len(action):].strip()
                break
        
        if ' at ' in cleaned_request:
            cleaned_request = cleaned_request.split(' at ')[0].strip()
        
        playlist_request = cleaned_request or 'different music'
        
        # Send notification to design team
        issue_description = f"Playlist change request for {zone_name}: Customer wants to play '{playlist_request}'. Please help change the playlist through the Soundtrack app."
        
        notification_sent = self.send_support_notification(
            venue_name=venue_name or zone_name,
            issue=issue_description,
            phone=phone
        )
        
        # Craft response based on notification success
        if notification_sent:
            response = f"I understand you'd like to hear {playlist_request} at {zone_name}.\n\n"
            response += "🎵 **Great news!** I've passed this request to our music design team and they'll take care of it right away. "
            response += "They'll change the playlist for you and may reach out if they need any clarification about your preferences.\n\n"
            response += "**In the meantime, I can help you with:**\n"
            response += "• Adjusting the volume\n"
            response += "• Skipping songs you don't like\n"
            response += "• Pausing or resuming playback\n\n"
            response += "The playlist change should be completed within a few minutes. Is there anything else I can help with while we update your music?"
        else:
            # Fallback if notification fails
            response = f"I understand you'd like to hear {playlist_request} at {zone_name}.\n\n"
            response += "I'll make sure our music design team handles this playlist change for you right away. "
            response += "Due to licensing requirements, playlist changes need to be done through our team, but they're quick to respond!\n\n"
            response += "**While they're updating your playlist, I can help with:**\n"
            response += "• Volume adjustments\n"
            response += "• Skipping tracks\n"
            response += "• Playback control\n\n"
            response += "Your playlist should be updated shortly. Anything else I can assist with?"
        
        logger.info(f"Playlist change request escalated to team: {playlist_request}")
        
        return response
    
    def provide_music_advice(self, venue_name: str, zone_name: str, request: str, phone: str = "WhatsApp") -> str:
        """Provide music design advice and escalate complex requests to team"""
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
            
            response += "\n💡 **Quick Actions I Can Do:**\n"
            response += "• Say 'volume 70%' to adjust sound\n"
            response += "• Say 'skip song' to change tracks\n"
            response += "• Say 'pause music' to stop playback\n"
            response += "\n**For Playlist Changes:**\n"
            response += "Our team needs to handle playlist changes due to licensing. "
            response += "Just let me know what you'd like and I'll get them to update it for you!\n"
            
        else:
            # Provide general design consultation
            response = f"🎨 **Music Design Consultation for {zone_name} at {venue_name}**\n\n"
            response += "I can help you create the perfect atmosphere! Consider:\n\n"
            response += "**🌅 Morning (6-11am):** Start gentle with jazz or acoustic\n"
            response += "**☀️ Lunch (11-3pm):** Upbeat but professional\n"
            response += "**🍸 Happy Hour (5-7pm):** Build energy with pop hits\n"
            response += "**🍽️ Dinner (6-10pm):** Sophisticated and elegant\n"
            response += "**🌙 Late Night (10pm+):** Smooth and atmospheric\n\n"
            
            response += "**I Can Help You Right Now:**\n"
            response += "• Adjust volume (say 'volume up/down')\n"
            response += "• Skip songs you don't like\n"
            response += "• Pause/resume playback\n"
            response += "• Check what's currently playing\n\n"
            response += "**For Playlist Changes:**\n"
            response += "I'll connect you with our team who can update your playlists!\n\n"
            
            response += "What would you like to adjust?"
        
        # Check if this needs design team input
        design_keywords = ['custom', 'brand', 'special event', 'create', 'unique', 'tailor', 'specific']
        needs_design_team = any(keyword in request.lower() for keyword in design_keywords)
        
        if needs_design_team:
            # Send notification to design team
            issue = f"Music design consultation requested for {zone_name}: {request[:200]}"
            notification_sent = self.send_support_notification(
                venue_name=venue_name,
                issue=issue,
                phone=phone
            )
            
            if notification_sent:
                response += "\n\n🎨 **Design Team Notified!**\n"
                response += "I've forwarded your request to our music design specialists. "
                response += "They'll review your needs and either implement the changes directly or reach out to discuss further. "
                response += "You should see updates shortly!"
            else:
                response += "\n\n🎨 **Design Team Support**\n"
                response += "Our music design team will help you create the perfect atmosphere. "
                response += "They'll be in touch shortly to discuss your specific needs."
        
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
        
        message_lower = message.lower()
        
        # PRIORITY 1: Check for urgent/critical issues that need immediate escalation
        urgent_keywords = [
            'urgent', 'emergency', 'all zones offline', 'system down', 'completely broken',
            'not working at all', 'totally dead', 'critical', 'asap', 'immediately',
            'vip event', 'important event', 'help!', 'lawsuit', 'legal action'
        ]
        
        critical_keywords = [
            'cancel', 'cancellation', 'terminate contract', 'unhappy', 'terrible service',
            'compensation', 'refund', 'complaint', 'frustrated', 'angry'
        ]
        
        # Music design/playlist requests that API cannot handle
        music_design_keywords = [
            'redesign', 'music design', 'change playlist', 'different playlist', 'new playlist',
            'create playlist', 'custom playlist', 'block song', 'block this song', 'never play',
            'schedule music', 'morning music', 'evening music', 'dinner music',
            'music atmosphere', 'curate', 'music curation', 'playlist suggestion',
            'recommend playlist', 'better music', 'improve music', 'music strategy',
            'get me some music', 'setup music', 'set up music', 'private event', 'special event',
            'event tomorrow', 'party music', 'wedding music', 'birthday music', 'celebration music',
            'music for', 'playlist for', 'need music', 'want music', 'different music',
            'change the music', 'switch music', 'update music', 'new music'
        ]
        
        is_urgent = any(keyword in message_lower for keyword in urgent_keywords)
        is_critical = any(keyword in message_lower for keyword in critical_keywords)
        
        if is_urgent or is_critical:
            # Determine department and priority
            from google_chat_client import Department, Priority
            
            if 'all zones offline' in message_lower or 'system down' in message_lower or 'completely broken' in message_lower:
                department = Department.OPERATIONS
                priority = Priority.CRITICAL
                issue_type = "System failure"
            elif 'cancel' in message_lower or 'terminate' in message_lower:
                department = Department.SALES
                priority = Priority.CRITICAL
                issue_type = "Cancellation risk"
            elif 'payment' in message_lower or 'invoice' in message_lower or 'refund' in message_lower:
                department = Department.FINANCE
                priority = Priority.HIGH
                issue_type = "Financial issue"
            elif is_urgent:
                department = Department.OPERATIONS
                priority = Priority.CRITICAL
                issue_type = "Urgent technical issue"
            else:
                department = Department.GENERAL
                priority = Priority.HIGH
                issue_type = "Customer complaint"
            
            # Send immediate notification to Google Chat
            venue_name = venue['name'] if venue else 'Unknown Venue'
            
            notification_sent = False
            try:
                from google_chat_client import chat_client
                
                # Build user info
                user_info = {
                    'name': user_name or 'Customer',
                    'phone': phone,
                    'platform': 'WhatsApp'
                }
                
                # Build venue data if available
                venue_data = None
                if venue:
                    venue_data = {
                        'zones': len(venue.get('zones', [])),
                        'contact': venue.get('contact_name', '')
                    }
                
                # Send notification with proper categorization
                notification_sent = chat_client.send_notification(
                    message=message,
                    venue_name=venue_name,
                    venue_data=venue_data,
                    user_info=user_info,
                    department=department,
                    priority=priority,
                    context=f"{issue_type}: Immediate attention required"
                )
                
                if notification_sent:
                    logger.info(f"✅ URGENT notification sent to Google Chat - {issue_type}")
                else:
                    logger.error(f"❌ Failed to send urgent notification")
                    
            except Exception as e:
                logger.error(f"Error sending urgent notification: {e}")
            
            # Return immediate response
            if notification_sent:
                if 'all zones offline' in message_lower or 'system down' in message_lower:
                    response = "🚨 **I understand this is critical!**\n\n"
                    response += "Our technical team has been alerted immediately about your system being offline. "
                    response += "They're mobilizing right now to investigate and restore your music system.\n\n"
                    response += "**What happens next:**\n"
                    response += "• A technician will contact you within minutes\n"
                    response += "• Remote diagnostics will begin immediately\n"
                    response += "• If needed, on-site support will be dispatched\n\n"
                    response += "Your issue has been marked as CRITICAL priority. We'll get your music back online as quickly as possible!"
                elif 'vip event' in message_lower or 'important event' in message_lower:
                    response = "🎯 **VIP Event Support Activated!**\n\n"
                    response += "I've immediately notified our operations team about your event. "
                    response += "They understand the urgency and are prioritizing your venue right now.\n\n"
                    response += "A specialist will contact you within 5-10 minutes to ensure everything runs perfectly for your event."
                elif 'cancel' in message_lower:
                    response = "I understand you're considering cancellation. This has been immediately escalated to our management team.\n\n"
                    response += "A senior account manager will contact you very shortly to address your concerns and find a solution."
                else:
                    response = "I've immediately escalated this to our support team as a high priority issue.\n\n"
                    response += "They've been notified and will address this right away. "
                    response += "You should hear from them very shortly."
            else:
                response = "I understand this is urgent. Our team is being notified right now to assist you immediately. "
                response += "They'll contact you as soon as possible to resolve this issue."
            
            # Save context and return
            context.append({"role": "user", "content": message})
            context.append({"role": "assistant", "content": response})
            if venue:
                context[-1]["venue"] = venue['name']
            self.save_conversation_context(phone, context)
            
            return response
        
        # PRIORITY 2: Check for music design/playlist requests that API cannot handle
        is_music_design = any(keyword in message_lower for keyword in music_design_keywords)
        
        if is_music_design:
            logger.info(f"🎨 Music design request detected: {message[:100]}...")
            
            from google_chat_client import Department, Priority
            
            # Determine the specific request type
            if any(word in message_lower for word in ['private event', 'special event', 'wedding', 'birthday', 'party', 'celebration', 'event tomorrow']):
                issue_type = "Event Music Request"
                department = Department.OPERATIONS
                priority = Priority.HIGH  # Events are time-sensitive
            elif any(word in message_lower for word in ['redesign', 'music design', 'atmosphere', 'curate', 'strategy']):
                issue_type = "Music Design Request"
                department = Department.DESIGN
                priority = Priority.NORMAL
            elif any(word in message_lower for word in ['playlist', 'change playlist', 'different music', 'get me some music', 'setup music']):
                issue_type = "Playlist Change Request"
                department = Department.OPERATIONS
                priority = Priority.NORMAL
            elif any(word in message_lower for word in ['block', 'never play', 'remove song']):
                issue_type = "Song Blocking Request"
                department = Department.OPERATIONS
                priority = Priority.NORMAL
            elif any(word in message_lower for word in ['schedule', 'morning', 'evening', 'dinner']):
                issue_type = "Music Scheduling Request"
                department = Department.DESIGN
                priority = Priority.NORMAL
            else:
                issue_type = "Music Customization Request"
                department = Department.DESIGN
                priority = Priority.NORMAL
            
            # Send notification to support team
            venue_name = venue['name'] if venue else 'Unknown Venue'
            
            notification_sent = False
            try:
                from google_chat_client import chat_client
                
                # Build user info
                user_info = {
                    'name': user_name or 'Customer',
                    'phone': phone,
                    'platform': 'WhatsApp'
                }
                
                # Build venue data if available
                venue_data = None
                if venue:
                    venue_data = {
                        'zones': len(venue.get('zones', [])),
                        'contact': venue.get('contact_name', '')
                    }
                
                # Send notification with proper categorization
                notification_sent = chat_client.send_notification(
                    message=f"🎨 {issue_type}: {message}",
                    venue_name=venue_name,
                    venue_data=venue_data,
                    user_info=user_info,
                    department=department,
                    priority=priority,
                    context=f"{issue_type} - Requires manual configuration"
                )
                
                if notification_sent:
                    logger.info(f"✅ Music design request sent to Google Chat - {issue_type}")
                else:
                    logger.error(f"❌ Failed to send music design notification")
                    
            except Exception as e:
                logger.error(f"Error sending music design notification: {e}")
            
            # Return appropriate response
            if notification_sent:
                response = f"🎨 **{issue_type}**\n\n"
                response += f"I understand you'd like to make changes to the music at {venue_name}.\n\n"
                response += "Due to music licensing requirements, playlist and music design changes need to be handled by our specialist team. "
                response += f"I've forwarded your request to our {department.value} team who will help you right away.\n\n"
                response += "**They will contact you shortly to:**\n"
                if 'playlist' in issue_type.lower():
                    response += "• Change your playlist selection\n"
                    response += "• Recommend playlists that match your needs\n"
                elif 'design' in issue_type.lower():
                    response += "• Redesign your music atmosphere\n"
                    response += "• Create a custom music strategy\n"
                elif 'block' in issue_type.lower():
                    response += "• Block specific songs or artists\n"
                    response += "• Customize your music preferences\n"
                elif 'schedule' in issue_type.lower():
                    response += "• Set up time-based music scheduling\n"
                    response += "• Configure different music for different times\n"
                response += "\n**In the meantime, I can help you with:**\n"
                response += "• Adjusting volume (say 'volume up/down')\n"
                response += "• Skipping songs (say 'skip')\n"
                response += "• Pausing/resuming playback\n"
                response += "• Checking what's currently playing"
            else:
                response = f"I understand you'd like to make changes to your music setup. "
                response += "Our music design team specializes in these requests and will be happy to help. "
                response += "They'll contact you shortly to assist with your music customization needs.\n\n"
                response += "**In the meantime, I can help with:**\n"
                response += "• Volume control\n"
                response += "• Skipping tracks\n"
                response += "• Playback control"
            
            # Save context and return
            context.append({"role": "user", "content": message})
            context.append({"role": "assistant", "content": response})
            if venue:
                context[-1]["venue"] = venue['name']
            self.save_conversation_context(phone, context)
            
            return response
        
        # Check if asking about music playing in a specific zone
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
            
            # Check if this is a zone selection response to a previous music request
            # Look back in context to see if we just asked which zone
            if context and len(context) >= 2:
                last_bot_msg = context[-1].get('content', '') if context[-1].get('role') == 'assistant' else ''
                if 'Which one would you like to control?' in last_bot_msg:
                    # This is a zone selection - check if it's a valid zone
                    for zone in venue.get('zones', []):
                        if zone.lower() in message_lower:
                            # Found the zone! Now look for the original music request
                            logger.info(f"Zone selection detected: {zone}")
                            for i in range(len(context) - 1, max(0, len(context) - 6), -1):
                                if context[i].get('role') == 'user':
                                    original_msg = context[i].get('content', '')
                                    # Check if this was a music-related request
                                    if any(word in original_msg.lower() for word in ['change', 'switch', 'playlist', 'music', 'chill', 'chillhop', 'lounge', 'play', 'jazz', 'volume']):
                                        logger.info(f"Executing original request: {original_msg} for zone: {zone}")
                                        # Execute the original request with the selected zone
                                        response = self.execute_music_change(venue['name'], zone, original_msg, venue, phone)
                                        context.append({"role": "user", "content": message})
                                        context.append({"role": "assistant", "content": response, "venue": venue['name']})
                                        self.save_conversation_context(phone, context)
                                        return response
            
            # Check for music control requests (playlist, volume, skip, etc.)
            music_keywords = ['change', 'switch', 'playlist', 'music', 'volume', 'louder', 'quieter', 
                            'skip', 'next', 'pause', 'stop', 'play', 'resume', 'chill', 'chillhop', 'jazz', 
                            'party', 'dinner', 'morning', 'atmosphere', 'mood', 'vibe', 'hip hop', 'hiphop', 'lounge']
            
            if any(word in message_lower for word in music_keywords):
                # Find which zone they're asking about - check more carefully
                zone_name = None
                for zone in venue.get('zones', []):
                    # Check for exact zone name or partial match
                    if zone.lower() in message_lower or message_lower.endswith(zone.lower()):
                        zone_name = zone
                        logger.info(f"Found zone '{zone}' in message: {message}")
                        break
                
                # If no specific zone mentioned, use first zone or ask
                if not zone_name and venue.get('zones'):
                    if len(venue['zones']) == 1:
                        zone_name = venue['zones'][0]
                    else:
                        # Ask which zone if multiple exist
                        zones = ', '.join(venue['zones'])
                        response = f"You have multiple zones: {zones}. Which one would you like to control?"
                        # Store that we're waiting for zone selection
                        context.append({"role": "user", "content": message})
                        context.append({"role": "assistant", "content": response, "venue": venue['name'], "waiting_for_zone": True})
                        self.save_conversation_context(phone, context)
                        return response
                
                if zone_name:
                    # Determine if this is a simple or complex request (things API cannot do)
                    complex_keywords = ['schedule', 'entire', 'all zones', 'whole venue', 'custom', 
                                      'special event', 'wedding', 'conference', 'brand', 'identity',
                                      'private event', 'party', 'birthday', 'celebration', 'tomorrow',
                                      'get me some music', 'setup music', 'set up music', 'need music',
                                      'event music', 'music for', 'playlist for', 'create playlist',
                                      'change playlist', 'different playlist', 'new playlist',
                                      'block song', 'never play', 'redesign', 'music design',
                                      'atmosphere', 'curate', 'recommend playlist', 'suggest playlist']
                    
                    is_complex = any(word in message_lower for word in complex_keywords)
                    
                    if is_complex:
                        # Complex request - notify support team
                        # Determine the type of request
                        if any(word in message_lower for word in ['event', 'party', 'wedding', 'birthday', 'celebration', 'tomorrow']):
                            response = f"🎉 **Event Music Request for {zone_name}**\n\n"
                            response += "I understand you need music for a special event. "
                            response += "Due to licensing requirements, our team needs to set this up for you.\n\n"
                        elif any(word in message_lower for word in ['playlist', 'change playlist', 'different music', 'get me some music']):
                            response = f"🎵 **Playlist Change Request for {zone_name}**\n\n"
                            response += "I understand you'd like to change the playlist. "
                            response += "Due to licensing restrictions, our team will handle this for you.\n\n"
                        elif any(word in message_lower for word in ['block', 'never play']):
                            response = f"🚫 **Song Blocking Request for {zone_name}**\n\n"
                            response += "I'll get our team to block that song from your playlist.\n\n"
                        else:
                            response = f"🎨 **Music Customization Request for {zone_name}**\n\n"
                            response += "I understand you need specialized music assistance.\n\n"
                        
                        response += "**I've notified our team who will:**\n"
                        if 'event' in message_lower or 'party' in message_lower:
                            response += "• Set up the perfect music for your event\n"
                            response += "• Ensure everything is ready on time\n"
                        elif 'playlist' in message_lower:
                            response += "• Update your playlist selection\n"
                            response += "• Apply the changes immediately\n"
                        else:
                            response += "• Handle your music customization\n"
                            response += "• Make the necessary adjustments\n"
                        
                        # Send Google Chat notification
                        notification_sent = self.send_support_notification(
                            venue_name=venue['name'],
                            issue=f"Complex music design request: {message[:200]}",
                            phone=phone
                        )
                        
                        if notification_sent:
                            response += "They've been notified and will implement these changes for you. "
                            response += "If they need any clarification about your requirements, they'll reach out directly. "
                            response += "You should see the updates take effect soon!"
                        else:
                            response += "Our design team will handle this specialized request immediately. "
                            response += "They'll make the necessary changes and may contact you if they need more details about your preferences."
                    else:
                        # Simple request - EXECUTE IMMEDIATELY via API if possible
                        response = self.execute_music_change(venue['name'], zone_name, message, venue, phone)
                    
                    # Add to context and return
                    context.append({"role": "user", "content": message})
                    context.append({"role": "assistant", "content": response, "venue": venue['name']})
                    self.save_conversation_context(phone, context)
                    
                    return response
        
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
            if needs_human or is_complex:
                issue_summary = f"Customer needs assistance: {message[:200]}"
                department = Department.GENERAL
                
                if needs_human:
                    issue_summary = f"Request beyond bot capabilities - {message[:200]}"
                    # Try to categorize by content
                    if 'playlist' in message.lower() or 'music' in message.lower():
                        department = Department.DESIGN
                    elif 'broken' in message.lower() or 'offline' in message.lower():
                        department = Department.OPERATIONS
                elif is_complex:
                    issue_summary = f"Complex issue requiring assistance - {message[:200]}"
                    if 'contract' in message.lower() or 'pricing' in message.lower():
                        department = Department.SALES
                    elif 'payment' in message.lower() or 'invoice' in message.lower():
                        department = Department.FINANCE
                
                notification_sent = self.send_support_notification(
                    venue_name=venue['name'] if venue else 'Unknown Venue',
                    issue=issue_summary,
                    phone=phone
                )
                
                if notification_sent:
                    # Replace the uncertain response with a confident one
                    bot_response = "I understand your request perfectly! "
                    if 'playlist' in message.lower() or 'music' in message.lower():
                        bot_response += "I've passed this to our music design team and they'll take care of it right away. "
                        bot_response += "They'll implement the changes you need and may reach out if they need any clarification."
                    elif 'broken' in message.lower() or 'offline' in message.lower() or 'not working' in message.lower():
                        bot_response += "I've escalated this technical issue to our operations team immediately. "
                        bot_response += "They'll investigate and resolve this for you as quickly as possible."
                    elif 'contract' in message.lower() or 'renewal' in message.lower():
                        bot_response += "I've forwarded this to our sales team who handle contracts and renewals. "
                        bot_response += "They'll review your account and be in touch with you shortly."
                    else:
                        bot_response += "I've notified the appropriate team about your request. "
                        bot_response += "They'll review this and either implement the necessary changes or contact you directly to discuss further."
                    
                    bot_response += "\n\nIs there anything else I can help you with in the meantime?"
                    logger.info(f"Google Chat notification sent - replaced uncertain response with confident escalation")
                else:
                    # Still give a confident response even if notification fails
                    bot_response = "I understand your request! Our team will handle this for you right away. "
                    bot_response += "They'll review your needs and take the appropriate action. "
                    bot_response += "You should hear back shortly with an update."
                    logger.warning(f"Google Chat notification failed but still gave confident response")
            
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
I can help control your music system using the Soundtrack Your Brand API:
- Check what's currently playing at any zone
- Adjust volume levels (say "volume up" or "set volume to 70%")
- Skip tracks you don't like
- Pause and resume playback

NOTE: Due to licensing restrictions, playlist changes must be done through the Soundtrack app by authorized staff.
I cannot change playlists directly, but I can help with playback controls and volume!
"""
        
        base_prompt = f"""You are a friendly music system support bot for BMA Social. 
You help venues with their background music systems.
Be conversational and natural, not robotic.

HONEST CAPABILITIES (Based on API limitations):
✅ YOU CAN adjust volume levels
✅ YOU CAN skip songs
✅ YOU CAN pause/resume playback
✅ YOU CAN check what's currently playing
❌ YOU CANNOT change playlists (API doesn't support this due to licensing)
❌ YOU CANNOT block songs
❌ YOU CANNOT access or manage playlist libraries

CRITICAL INSTRUCTIONS:
- BE HONEST about what you can and cannot do
- NEVER pretend to change playlists - the API literally cannot do this
- When asked to change playlists, explain the licensing limitation politely
- Offer alternatives: suggest the manager use the Soundtrack app directly
- NEVER say "Done!" for things you cannot actually do
- If someone just says a zone name like "Edge" - that's them selecting a zone
- NEVER ask for email or contact details
- For playlist changes, offer to notify the team to help the venue manager
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
- If you can't help with something, say our team will assist them shortly
- NEVER ask for email addresses or contact information
- Our support team will take over in this same WhatsApp conversation
- Just say "Our team will help you with this shortly" without asking for contact details
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
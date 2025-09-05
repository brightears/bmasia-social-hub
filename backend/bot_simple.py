#!/usr/bin/env python3
"""
BMA Social Music Bot - Simplified Conversational Version
=======================================================
Focuses on user experience with proper error handling when API issues occur
"""

import os
import logging
import json
from typing import Dict, Optional
from datetime import datetime
import google.generativeai as genai
from venue_data_reader import VenueDataReader
from soundtrack_api import soundtrack_api
from venue_accounts import get_zone_id, find_venue_account

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimpleMusicBot:
    """
    Simplified conversational music bot that focuses on user experience
    """
    
    def __init__(self):
        """Initialize the bot"""
        self.venue_reader = VenueDataReader()
        
        # Initialize Gemini
        api_key = os.environ.get('GEMINI_API_KEY', os.environ.get('GOOGLE_AI_API_KEY'))
        if api_key:
            genai.configure(api_key=api_key)
            model_name = os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash')
            
            # Configure generation parameters from environment
            generation_config = {
                "temperature": float(os.environ.get('GEMINI_TEMPERATURE', '0.7')),
                "max_output_tokens": int(os.environ.get('GEMINI_MAX_TOKENS', '8192')),
                "top_p": 0.9,
                "top_k": 40,
            }
            
            self.model = genai.GenerativeModel(
                model_name=model_name,
                generation_config=generation_config
            )
        else:
            logger.warning("No Gemini API key found - using basic intent detection")
            self.model = None
        
        # User context for conversation continuity
        self.user_context = {}
        
        logger.info("Simple Music Bot initialized")
    
    def process_message(self, message: str, user_phone: str, user_name: str = None) -> str:
        """Process incoming message with conversational responses"""
        
        try:
            # Analyze the message
            analysis = self._analyze_message(message)
            
            # Handle venue context
            venue_name = analysis.get('venue', 'unknown')
            if venue_name == 'unknown' and user_phone in self.user_context:
                context = self.user_context[user_phone]
                if datetime.now().timestamp() - context.get('last_update', 0) < 600:  # 10 minutes
                    venue_name = context['venue']
                    analysis['venue'] = venue_name
            
            # Update context
            if venue_name != 'unknown':
                self.user_context[user_phone] = {
                    'venue': venue_name,
                    'last_update': datetime.now().timestamp()
                }
            
            # Route to handlers
            intent = analysis.get('intent', 'general')
            
            if intent == 'volume_control':
                return self._handle_volume(analysis, user_phone)
            elif intent == 'playback_control':
                return self._handle_playback(analysis, user_phone)
            elif intent == 'zone_status':
                return self._handle_status(analysis, user_phone)
            elif intent == 'playlist_change':
                return self._handle_playlist(analysis, user_phone)
            elif intent == 'venue_info':
                return self._handle_venue_info(analysis)
            else:
                return self._handle_general(message)
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return "I'm having a technical issue right now. Please try again in a moment, or contact support if the problem persists."
    
    def _analyze_message(self, message: str) -> Dict:
        """Analyze message using Gemini or basic pattern matching"""
        
        if self.model:
            try:
                prompt = f"""Analyze this music venue message. Extract ONLY explicit information:

Message: "{message}"

Determine intent and extract entities:
- volume_control: wants to change volume
- playback_control: wants to play/pause/skip
- zone_status: asking what's playing or current status  
- playlist_change: wants to change playlist or mentions music type/mood
- venue_info: asking about venue details
- general: other queries

Venue names: Hilton Pattaya, etc.
Zone names: Edge, Drift Bar, Horizon, Shore, Lobby, Restaurant, Pool

Respond in JSON:
{{"intent": "...", "venue": "exact name or unknown", "zone": "exact name or unknown", "action": "specific action", "details": "relevant info"}}"""

                response = self.model.generate_content(prompt)
                response_text = response.text.strip()
                
                # Clean JSON response
                if '```json' in response_text:
                    response_text = response_text.split('```json')[1].split('```')[0].strip()
                elif '```' in response_text:
                    response_text = response_text.split('```')[1].split('```')[0].strip()
                
                result = json.loads(response_text)
                return result
                
            except Exception as e:
                logger.error(f"Gemini analysis failed: {e}")
        
        # Fallback to basic pattern matching
        return self._basic_intent_detection(message)
    
    def _basic_intent_detection(self, message: str) -> Dict:
        """Basic intent detection without AI"""
        
        message_lower = message.lower()
        
        # Volume intent
        if any(word in message_lower for word in ['volume', 'loud', 'quiet', 'turn up', 'turn down']):
            return {'intent': 'volume_control', 'venue': 'unknown', 'zone': 'unknown', 'action': 'volume', 'details': message}
        
        # Status intent
        if any(word in message_lower for word in ['playing', 'song', 'track', 'music', "what's on"]):
            return {'intent': 'zone_status', 'venue': 'unknown', 'zone': 'unknown', 'action': 'status', 'details': message}
        
        # Playback intent
        if any(word in message_lower for word in ['play', 'pause', 'stop', 'skip']):
            return {'intent': 'playback_control', 'venue': 'unknown', 'zone': 'unknown', 'action': 'playback', 'details': message}
        
        return {'intent': 'general', 'venue': 'unknown', 'zone': 'unknown', 'action': None, 'details': message}
    
    def _handle_volume(self, analysis: Dict, user_phone: str) -> str:
        """Handle volume control requests"""
        
        venue_name = analysis.get('venue', 'unknown')
        zone_name = analysis.get('zone', 'unknown')
        
        # Need venue
        if venue_name == 'unknown':
            return "I can help with volume control! What's your venue name?"
        
        # Find venue
        venue = self.venue_reader.get_venue(venue_name)
        if not venue:
            return f"I couldn't find {venue_name} in our system. Could you provide the full venue name?"
        
        # Check if it's a SYB venue
        if venue.get('music_platform') != 'Soundtrack Your Brand':
            return f"{venue.get('property_name', venue_name)} uses {venue.get('music_platform', 'a different system')}. You'll need to adjust the volume manually on the device."
        
        # Find zone ID
        zone_id = get_zone_id(venue_name, zone_name)
        if not zone_id and zone_name == 'unknown':
            zones = venue.get('zone_names', '')
            if isinstance(zones, str):
                zone_list = [z.strip() for z in zones.split(',')]
                if len(zone_list) == 1:
                    zone_name = zone_list[0] 
                    zone_id = get_zone_id(venue_name, zone_name)
                elif zone_list:
                    return f"Which zone needs volume adjustment? Available zones: {', '.join(zone_list)}"
        
        if not zone_id:
            return f"I couldn't find the zone '{zone_name}' for {venue.get('property_name', venue_name)}. Please check the zone name."
        
        # Determine volume level
        details = analysis.get('details', '')
        target_volume = self._extract_volume(details)
        
        # Attempt volume control
        try:
            result = soundtrack_api.set_volume(zone_id, target_volume)
            
            if result.get('success'):
                return f"✅ Volume adjusted to {target_volume}/16 for {zone_name} at {venue.get('property_name', venue_name)}!"
            else:
                # Handle API failure gracefully
                return f"I couldn't adjust the volume for {zone_name} through the API right now. Please use your Soundtrack Your Brand app to set the volume to {target_volume}/16, or contact venue staff for assistance."
                
        except Exception as e:
            logger.error(f"Volume control error: {e}")
            return f"There's a technical issue with volume control right now. Please use your Soundtrack Your Brand app to adjust the volume for {zone_name}, or contact venue staff."
    
    def _handle_playback(self, analysis: Dict, user_phone: str) -> str:
        """Handle playback control requests"""
        
        venue_name = analysis.get('venue', 'unknown')
        zone_name = analysis.get('zone', 'unknown')
        action = analysis.get('action', 'play')
        
        if venue_name == 'unknown':
            return "I can help with music playback! What's your venue name?"
        
        venue = self.venue_reader.get_venue(venue_name)
        if not venue:
            return f"I couldn't find {venue_name} in our system."
        
        if venue.get('music_platform') != 'Soundtrack Your Brand':
            return f"{venue.get('property_name', venue_name)} uses {venue.get('music_platform')}. Please use the device controls to play/pause music."
        
        zone_id = get_zone_id(venue_name, zone_name)
        if not zone_id:
            return f"I couldn't find the zone '{zone_name}' for {venue.get('property_name', venue_name)}."
        
        # Attempt playback control
        try:
            if 'play' in analysis.get('details', '').lower():
                result = soundtrack_api.control_playback(zone_id, 'play')
                action_word = "play"
            elif 'pause' in analysis.get('details', '').lower() or 'stop' in analysis.get('details', '').lower():
                result = soundtrack_api.control_playback(zone_id, 'pause')
                action_word = "pause"
            elif 'skip' in analysis.get('details', '').lower():
                result = soundtrack_api.control_playback(zone_id, 'skip')
                action_word = "skip"
            else:
                result = soundtrack_api.control_playback(zone_id, 'play')
                action_word = "play"
            
            if result.get('success'):
                return f"✅ Music {action_word} command sent to {zone_name} at {venue.get('property_name', venue_name)}!"
            else:
                return f"I couldn't control playback for {zone_name} through the API. Please use your Soundtrack Your Brand app to {action_word} music, or contact venue staff."
                
        except Exception as e:
            logger.error(f"Playback control error: {e}")
            return f"There's a technical issue with playback control. Please use your Soundtrack Your Brand app for {zone_name}, or contact venue staff."
    
    def _handle_status(self, analysis: Dict, user_phone: str) -> str:
        """Handle status check requests"""
        
        venue_name = analysis.get('venue', 'unknown')
        zone_name = analysis.get('zone', 'unknown')
        
        if venue_name == 'unknown':
            return "I can check what's playing! What's your venue name?"
        
        venue = self.venue_reader.get_venue(venue_name)
        if not venue:
            return f"I couldn't find {venue_name} in our system."
        
        if venue.get('music_platform') != 'Soundtrack Your Brand':
            return f"{venue.get('property_name', venue_name)} uses {venue.get('music_platform')}. I can't check what's playing on that system."
        
        zone_id = get_zone_id(venue_name, zone_name)
        if not zone_id:
            if zone_name == 'unknown':
                zones = venue.get('zone_names', '')
                if isinstance(zones, str) and zones:
                    zone_list = [z.strip() for z in zones.split(',')]
                    return f"Which zone would you like me to check? Available zones: {', '.join(zone_list)}"
            return f"I couldn't find the zone '{zone_name}' for {venue.get('property_name', venue_name)}."
        
        # Get zone status
        try:
            status = soundtrack_api.get_zone_status(zone_id)
            
            if status and 'error' not in status:
                zone_display_name = status.get('name', zone_name)
                venue_display_name = venue.get('property_name', venue_name)
                
                # Check if playing
                playing = status.get('playing', False)
                playback_state = status.get('playback_state', 'unknown')
                
                if playback_state == 'offline' or not status.get('device_online', True):
                    return f"The {zone_display_name} zone at {venue_display_name} appears to be offline."
                
                # Build response
                if playing:
                    current_track = status.get('current_track')
                    if current_track:
                        track_name = current_track.get('name', 'Unknown track')
                        artist = current_track.get('artist', 'Unknown artist')
                        response = f"🎵 At {zone_display_name} in {venue_display_name}, \"{track_name}\" by {artist} is currently playing"
                        
                        playlist = status.get('current_playlist')
                        if playlist:
                            response += f" from the {playlist} playlist"
                        response += "."
                    else:
                        response = f"🎵 Music is playing at {zone_display_name} in {venue_display_name}"
                        playlist = status.get('current_playlist') 
                        if playlist:
                            response += f" from the {playlist} playlist"
                        response += "."
                else:
                    response = f"⏸️ Music is currently paused at {zone_display_name} in {venue_display_name}."
                
                return response
                
            else:
                return f"I can see {zone_name} at {venue.get('property_name', venue_name)} but couldn't get the current status. The zone might be offline or there may be a connection issue."
                
        except Exception as e:
            logger.error(f"Status check error: {e}")
            return f"I'm having trouble checking the status for {zone_name}. Please check your Soundtrack Your Brand app or contact venue staff."
    
    def _handle_playlist(self, analysis: Dict, user_phone: str) -> str:
        """Handle playlist change requests"""
        
        venue_name = analysis.get('venue', 'unknown')
        details = analysis.get('details', '')
        
        if venue_name == 'unknown':
            return "I can help change playlists! What's your venue name?"
        
        venue = self.venue_reader.get_venue(venue_name)
        if not venue:
            return f"I couldn't find {venue_name} in our system."
        
        if venue.get('music_platform') != 'Soundtrack Your Brand':
            return f"{venue.get('property_name', venue_name)} uses {venue.get('music_platform')}. You'll need to change playlists manually on the device."
        
        # For now, provide guidance since playlist control is complex
        response = f"🎵 I can help you find the perfect playlist for {venue.get('property_name', venue_name)}!\n\n"
        
        if details:
            # Try to find matching playlists
            try:
                playlists = soundtrack_api.find_playlists_by_context(details, limit=5)
                if playlists:
                    response += f"Based on '{details}', here are some great playlist options:\n"
                    for i, playlist in enumerate(playlists[:5], 1):
                        response += f"{i}. **{playlist['name']}**"
                        if playlist.get('description'):
                            response += f" - {playlist['description'][:60]}..."
                        response += "\n"
                    response += "\nPlease search for one of these playlists in your Soundtrack Your Brand app and assign it to your zone."
                else:
                    response += f"I couldn't find specific playlists for '{details}', but you can search for that style in your Soundtrack Your Brand app!"
            except:
                response += f"You can search for '{details}' playlists in your Soundtrack Your Brand app!"
        else:
            response += "Tell me what style or mood you want (like '80s hits', 'relaxing jazz', 'upbeat pop') and I'll help you find the perfect playlist!"
        
        return response
    
    def _handle_venue_info(self, analysis: Dict) -> str:
        """Handle venue information requests"""
        
        venue_name = analysis.get('venue', 'unknown')
        if venue_name == 'unknown':
            return "I'd be happy to help with venue information! Which venue are you asking about?"
        
        venue = self.venue_reader.get_venue(venue_name)
        if not venue:
            return f"I couldn't find {venue_name} in our system."
        
        # Provide basic venue info
        venue_display_name = venue.get('property_name', venue_name)
        platform = venue.get('music_platform', 'Unknown')
        zones = venue.get('zone_names', '')
        
        response = f"📍 **{venue_display_name}**\n"
        response += f"🎵 Music System: {platform}\n"
        
        if isinstance(zones, str) and zones:
            zone_list = [z.strip() for z in zones.split(',')]
            response += f"🏢 Zones ({len(zone_list)}): {', '.join(zone_list)}\n"
        
        response += "\nWhat specific information would you like to know?"
        return response
    
    def _handle_general(self, message: str) -> str:
        """Handle general queries"""
        
        response = "👋 Hi! I'm your music system assistant.\n\n"
        response += "I can help you with:\n"
        response += "🔊 **Volume control** - 'Turn up the music in Edge'\n"
        response += "🎵 **Current music** - 'What's playing in the lobby?'\n"
        response += "▶️ **Playback** - 'Play music' or 'Pause the music'\n"
        response += "🎶 **Playlists** - 'I want 80s hits' or 'Play jazz music'\n"
        response += "🏢 **Venue info** - Ask about your zones or system details\n\n"
        response += "Just tell me your venue name and what you need! I understand natural language, so ask in your own words. 😊"
        
        return response
    
    def _extract_volume(self, text: str) -> int:
        """Extract volume level from text"""
        
        import re
        
        # Look for numbers
        numbers = re.findall(r'\d+', text)
        if numbers:
            volume = int(numbers[0])
            # Convert percentage to 0-16 scale if needed
            if volume > 16:
                volume = int(volume * 16 / 100)
            return max(0, min(16, volume))
        
        # Keywords
        text_lower = text.lower()
        if any(word in text_lower for word in ['mute', 'off', 'silent']):
            return 0
        elif any(word in text_lower for word in ['max', 'maximum', 'full', 'loud']):
            return 14
        elif any(word in text_lower for word in ['up', 'higher', 'increase']):
            return 11
        elif any(word in text_lower for word in ['down', 'lower', 'quiet', 'soft']):
            return 6
        else:
            return 8  # Default moderate level

# Create instance
simple_bot = SimpleMusicBot()

if __name__ == "__main__":
    print("=== Simple Music Bot Test ===")
    
    test_messages = [
        "What's playing at Edge in Hilton Pattaya?",
        "Turn up the volume in Drift Bar", 
        "I want 80s music",
        "Pause the music in Edge"
    ]
    
    for msg in test_messages:
        print(f"\nUser: {msg}")
        response = simple_bot.process_message(msg, "+66123456789")
        print(f"Bot: {response}")
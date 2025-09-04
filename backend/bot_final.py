#!/usr/bin/env python3
"""
BMA Social Music Bot - Final Deployment Version
==============================================
Corrected implementation that understands control is at app/cloud level, not device level
"""

import os
import logging
import re
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import google.generativeai as genai
from venue_data_reader import VenueDataReader
from soundtrack_api import soundtrack_api

# Import Google Chat for escalations
try:
    from google_chat_client import GoogleChatClient, Department, Priority
    GCHAT_AVAILABLE = True
except ImportError:
    GCHAT_AVAILABLE = False
    logging.warning("Google Chat client not available for escalations")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BMASocialMusicBot:
    """
    Final bot implementation with corrected SYB understanding:
    - Control happens at app/cloud level, NOT device level
    - API access determines control capability, NOT subscription tier
    - Always attempts control first, analyzes failures properly
    """
    
    def __init__(self):
        """Initialize bot with all services"""
        # Initialize venue data reader
        self.venue_reader = VenueDataReader()
        
        # Initialize Gemini
        api_key = os.environ.get('GOOGLE_AI_API_KEY', os.environ.get('GEMINI_API_KEY'))
        if not api_key:
            raise ValueError("GOOGLE_AI_API_KEY or GEMINI_API_KEY must be set")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Initialize Google Chat for escalations
        self.gchat = GoogleChatClient() if GCHAT_AVAILABLE else None
        
        # Control capabilities understanding (CORRECTED)
        self.control_understanding = {
            'principle': 'Control happens at SYB app/cloud level, not device level',
            'evidence': 'Volume control works from iPhone, Android, any device',
            'requirement': 'API access must be enabled for the account',
            'not_required': 'Subscription tier does not determine control capability'
        }
        
        # Conversation context tracking (stores recent venue context per user)
        self.user_context = {}  # {user_phone: {'venue': 'Hilton Pattaya', 'last_update': timestamp}}
        
        logger.info("BMA Social Music Bot initialized (Final Version)")
        logger.info(f"Control Understanding: {self.control_understanding['principle']}")
        logger.info(f"Google Chat available: {GCHAT_AVAILABLE}")
    
    def process_message(self, message: str, user_phone: str, user_name: str = None) -> str:
        """
        Process incoming message with corrected control logic and context tracking
        """
        try:
            # Extract intent and entities
            analysis = self._analyze_message(message)
            
            # Check if venue is mentioned or use context
            if analysis.get('venue') == 'unknown' and user_phone in self.user_context:
                # Use stored context if venue not mentioned
                context = self.user_context[user_phone]
                import time
                # Context expires after 10 minutes
                if time.time() - context.get('last_update', 0) < 600:
                    analysis['venue'] = context['venue']
                    logger.info(f"Using context venue: {context['venue']} for user {user_phone}")
            
            # Update context if venue is mentioned
            if analysis.get('venue') != 'unknown':
                import time
                self.user_context[user_phone] = {
                    'venue': analysis['venue'],
                    'last_update': time.time()
                }
            
            # Route to appropriate handler
            if analysis['intent'] == 'volume_control':
                return self._handle_volume_control(analysis, user_phone)
            elif analysis['intent'] == 'playback_control':
                return self._handle_playback_control(analysis, user_phone)
            elif analysis['intent'] == 'playlist_change':
                return self._handle_playlist_change(analysis, user_phone)
            elif analysis['intent'] == 'zone_status':
                return self._handle_zone_status(analysis)
            elif analysis['intent'] == 'troubleshooting':
                return self._handle_troubleshooting(analysis, user_phone)
            elif analysis['intent'] == 'venue_info':
                return self._handle_venue_info(analysis)
            else:
                return self._handle_general_query(message, analysis)
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return "I apologize, but I encountered an error. Please try rephrasing your request or contact support."
    
    def _analyze_message(self, message: str) -> Dict:
        """Analyze message using Gemini with anti-hallucination guidelines"""
        
        prompt = f"""Analyze this music venue support message. Extract ONLY what is explicitly stated.

Message: "{message}"

Rules:
1. NEVER make up venue names, zone names, or issues
2. Only extract entities that are explicitly mentioned
3. If venue/zone is unclear, mark as "unknown"
4. Extract specific questions asked (e.g., "when contract expires", "how many zones", "who is the manager")
5. Common zone names: Edge, Drift Bar, Horizon, Shore, Lobby, Restaurant, Pool - these are zones, not venues
6. If a location name could be a zone (like Edge, Lobby, Restaurant), mark it as zone, not venue

Determine the intent and extract entities:

Intents:
- volume_control: User wants to change volume
- playback_control: User wants to play/pause/skip music
- playlist_change: User wants to change playlist or mentions music genre/mood (80s, jazz, upbeat, relaxing, etc.)
- zone_status: User asking what's currently playing, zone status, current song, what music is on
- troubleshooting: User reporting an issue
- venue_info: User asking about venue details (contract, zones, contacts, pricing, etc.)
- general: Other queries

Response format:
{{
    "intent": "...",
    "venue": "exact venue/hotel name or unknown (e.g., Hilton Pattaya, Marriott)",
    "zone": "exact zone name or unknown (e.g., Edge, Drift Bar, Lobby)",
    "action": "specific action or null",
    "details": "relevant details",
    "specific_question": "what specifically they're asking about (e.g., contract_expiry, zone_count, manager_contact, what_song_playing, etc.)"
}}

Important: "Edge", "Drift Bar", "Horizon", "Shore" are zone names, not venue names!"""
        
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Try to extract JSON from the response
            import json
            
            # Sometimes Gemini adds markdown formatting
            if '```json' in response_text:
                response_text = response_text.split('```json')[1].split('```')[0].strip()
            elif '```' in response_text:
                response_text = response_text.split('```')[1].split('```')[0].strip()
            
            result = json.loads(response_text)
            logger.info(f"Message analysis: {result}")
            return result
        except Exception as e:
            logger.error(f"Error analyzing message: {e}")
            return {
                'intent': 'general',
                'venue': 'unknown',
                'zone': 'unknown',
                'action': None,
                'details': message
            }
    
    def _handle_volume_control(self, analysis: Dict, user_phone: str) -> str:
        """
        Handle volume control with CORRECTED logic:
        ALWAYS attempts control first (app-level control, not device-dependent)
        """
        venue_name = analysis.get('venue', 'unknown')
        zone_name = analysis.get('zone', 'unknown')
        
        # Need to identify the venue and zone
        if venue_name == 'unknown':
            return "Hi! I can help with volume control. What's the name of your venue or hotel?"
        
        # Find venue in our data
        venue = self.venue_reader.get_venue(venue_name)
        if not venue:
            # Try fuzzy matching
            all_venues = self.venue_reader.get_all_venues()
            for v in all_venues:
                if venue_name.lower() in v['name'].lower() or v['name'].lower() in venue_name.lower():
                    venue = v
                    break
        
        if not venue:
            return f"I couldn't find {venue_name} in our system. Could you provide the full venue name?"
        
        # Check platform
        if venue.get('music_platform') != 'Soundtrack Your Brand':
            return f"Volume control for {venue.get('property_name', venue_name)} requires manual adjustment as it uses {venue.get('music_platform', 'a non-API platform')}."
        
        # Find the zone
        if zone_name == 'unknown':
            zones = venue.get('zone_names', [])
            if len(zones) == 1:
                zone_name = zones[0]
            else:
                return f"Which zone needs volume adjustment? Available zones: {', '.join(zones)}"
        
        # Find zone ID in SYB
        zone_id = self._find_zone_id(venue.get('property_name', venue_name), zone_name)
        if not zone_id:
            return f"I couldn't find zone '{zone_name}' in the Soundtrack system for {venue.get('property_name', venue_name)}."
        
        # ALWAYS attempt control first (app-level, not device-dependent)
        target_volume = self._determine_volume_level(analysis.get('details', ''))
        
        # Try to control via API
        try:
            result = soundtrack_api.set_volume(zone_id, target_volume)
            if result:
                return f"✅ Volume adjusted to level {target_volume}/16 for {zone_name} at {venue.get('property_name', venue_name)}."
            else:
                # Control failed - check why
                capabilities = soundtrack_api.get_zone_capabilities(zone_id)
                if 'trial' in capabilities.get('control_failure_reason', ''):
                    return self._escalate_trial_zone(venue, zone_name, f"volume adjustment to {target_volume}/16", user_phone)
                else:
                    return self._escalate_api_failure(venue, zone_name, f"volume adjustment to {target_volume}/16", user_phone)
                    
        except Exception as e:
            logger.error(f"Volume control error: {e}")
            return self._escalate_api_failure(venue, zone_name, f"volume adjustment to {target_volume}/16", user_phone)
    
    def _handle_playback_control(self, analysis: Dict, user_phone: str) -> str:
        """Handle play/pause/skip with corrected logic"""
        venue_name = analysis.get('venue', 'unknown')
        zone_name = analysis.get('zone', 'unknown')
        action = analysis.get('action', 'play')
        
        # Similar logic to volume control - ALWAYS attempt first
        if venue_name == 'unknown':
            return "Hi! I can help with playback control. What's the name of your venue or hotel?"
        
        venue = self.venue_reader.get_venue(venue_name)
        if not venue:
            return f"I couldn't find {venue_name} in our system. Could you provide the full venue name?"
        
        if venue.get('music_platform') != 'Soundtrack Your Brand':
            return f"Playback control for {venue.get('property_name', venue_name)} requires manual adjustment as it uses {venue.get('music_platform', 'a non-API platform')}."
        
        # Find zone ID
        zone_id = self._find_zone_id(venue.get('property_name', venue_name), zone_name)
        if not zone_id:
            return f"I couldn't find zone '{zone_name}' in the Soundtrack system."
        
        # ALWAYS attempt control first
        try:
            if action == 'play':
                result = soundtrack_api.play_zone(zone_id)
            elif action == 'pause':
                result = soundtrack_api.pause_zone(zone_id)
            else:
                result = False
            
            if result:
                return f"✅ Music {action} command sent to {zone_name} at {venue.get('property_name', venue_name)}."
            else:
                capabilities = soundtrack_api.get_zone_capabilities(zone_id)
                if 'trial' in capabilities.get('control_failure_reason', ''):
                    return self._escalate_trial_zone(venue, zone_name, f"{action} command", user_phone)
                else:
                    return self._escalate_api_failure(venue, zone_name, f"{action} command", user_phone)
                    
        except Exception as e:
            logger.error(f"Playback control error: {e}")
            return self._escalate_api_failure(venue, zone_name, f"{action} command", user_phone)
    
    def _handle_playlist_change(self, analysis: Dict, user_phone: str) -> str:
        """Handle playlist switching with intelligent context matching"""
        venue_name = analysis.get('venue', 'unknown')
        zone_name = analysis.get('zone', 'unknown')
        playlist_request = analysis.get('details', '')
        
        if venue_name == 'unknown':
            return "Hi! I can help change playlists. What's the name of your venue or hotel?"
        
        venue = self.venue_reader.get_venue(venue_name)
        if not venue:
            return f"I couldn't find {venue_name} in our system. Could you provide the full venue name?"
        
        if venue.get('music_platform') != 'Soundtrack Your Brand':
            return f"Playlist control for {venue.get('property_name', venue_name)} requires manual adjustment as it uses {venue.get('music_platform', 'a non-API platform')}."
        
        # Find zone ID
        zone_id = self._find_zone_id(venue.get('property_name', venue_name), zone_name)
        if not zone_id:
            zones = venue.get('zone_names', '')
            # Handle zones as string (from venue_data.md)
            if isinstance(zones, str) and zones:
                zone_list = [z.strip() for z in zones.split(',')]
            else:
                zone_list = zones if isinstance(zones, list) else []
            
            if len(zone_list) == 1:
                zone_id = self._find_zone_id(venue.get('property_name', venue_name), zone_list[0])
                zone_name = zone_list[0]
            elif zone_list:
                return f"Which zone needs a playlist change? Available zones: {', '.join(zone_list)}"
            else:
                return "I couldn't find the zones for this venue."
        
        # INTELLIGENT PLAYLIST SELECTION
        # First try to find playlists based on context (80s, jazz, upbeat, etc.)
        if playlist_request:
            logger.info(f"Searching for playlists matching context: {playlist_request}")
            
            # Use the intelligent playlist search
            context_playlists = soundtrack_api.find_playlists_by_context(playlist_request)
            
            if context_playlists:
                # Found matching playlists from SYB's curated library
                best_match = context_playlists[0]  # Already sorted by relevance
                
                # Attempt to set the playlist
                try:
                    result = soundtrack_api.set_playlist(zone_id, best_match['id'])
                    
                    if result.get('success'):
                        return f"✅ Changed to '{best_match['name']}' playlist in {zone_name} at {venue.get('property_name', venue_name)}.\n\n{best_match.get('description', '')}"
                    else:
                        # Check failure reason
                        if 'no_api_control' in result.get('error_type', ''):
                            # Provide manual instructions with specific playlist name
                            response = f"⚠️ {zone_name} requires manual playlist change.\n\n"
                            response += f"**Please use the SYB app to search for and select:**\n"
                            response += f"🎵 '{best_match['name']}'\n"
                            if best_match.get('description'):
                                response += f"Description: {best_match['description']}\n"
                            response += f"\nAlternatives you might like:\n"
                            for i, alt in enumerate(context_playlists[1:4], 1):  # Show 3 alternatives
                                response += f"{i}. {alt['name']}\n"
                            return response
                        else:
                            return self._escalate_api_failure(venue, zone_name, f"playlist change to {best_match['name']}", user_phone)
                            
                except Exception as e:
                    logger.error(f"Error setting playlist: {e}")
                    
                    # Even if setting fails, provide helpful manual instructions
                    response = f"I found the perfect playlist but couldn't set it automatically.\n\n"
                    response += f"**Please search for these playlists in the SYB app:**\n"
                    for i, playlist in enumerate(context_playlists[:5], 1):
                        response += f"{i}. '{playlist['name']}'"
                        if playlist.get('description'):
                            response += f" - {playlist['description'][:50]}"
                        response += "\n"
                    return response
            else:
                # No context match found, fall back to account playlists
                logger.info("No context match found, checking account playlists")
        
        # Fall back to account's custom playlists
        playlists = soundtrack_api.get_playlists(zone_id)
        if not playlists:
            # No account playlists, but try curated search anyway
            if playlist_request:
                curated = soundtrack_api.search_curated_playlists(playlist_request)
                if curated:
                    response = f"I found these playlists in SYB's library for '{playlist_request}':\n\n"
                    for i, playlist in enumerate(curated[:5], 1):
                        response += f"{i}. {playlist['name']}"
                        if playlist.get('description'):
                            response += f" - {playlist['description'][:50]}"
                        response += "\n"
                    response += "\nPlease search for one of these in your SYB app to add it to your account."
                    return response
            return self._escalate_api_failure(venue, zone_name, "playlist retrieval", user_phone)
        
        # Try to match from account playlists
        playlist_to_set = None
        if playlist_request:
            playlist_lower = playlist_request.lower()
            for playlist in playlists:
                if playlist_lower in playlist['name'].lower() or playlist['name'].lower() in playlist_lower:
                    playlist_to_set = playlist
                    break
        
        if not playlist_to_set:
            # Show available playlists
            venue_display_name = venue.get('property_name', venue_name)
            response = f"Your account playlists for {zone_name} at {venue_display_name}:\n"
            for i, playlist in enumerate(playlists[:10], 1):  # Show max 10
                response += f"{i}. {playlist['name']}"
                if playlist.get('description'):
                    response += f" - {playlist['description'][:50]}"
                response += "\n"
            
            # Also suggest searching for curated playlists
            if playlist_request:
                response += f"\n💡 Want something different? I can search SYB's library for '{playlist_request}' playlists."
            else:
                response += "\n💡 Tell me what mood or genre you want (e.g., '80s hits', 'relaxing jazz', 'upbeat pop')"
            
            return response
        
        # ALWAYS attempt to set playlist (app-level control)
        try:
            result = soundtrack_api.set_playlist(zone_id, playlist_to_set['id'])
            
            if result.get('success'):
                return f"✅ Playlist changed to '{playlist_to_set['name']}' for {zone_name} at {venue.get('property_name', venue_name)}."
            else:
                # Check failure reason
                if 'no_api_control' in result.get('error_type', ''):
                    return self._escalate_trial_zone(venue, zone_name, f"playlist change to {playlist_to_set['name']}", user_phone)
                else:
                    return self._escalate_api_failure(venue, zone_name, f"playlist change to {playlist_to_set['name']}", user_phone)
                    
        except Exception as e:
            logger.error(f"Playlist change error: {e}")
            return self._escalate_api_failure(venue, zone_name, "playlist change", user_phone)
    
    def _handle_zone_status(self, analysis: Dict) -> str:
        """Check zone status and currently playing music"""
        venue_name = analysis.get('venue', 'unknown')
        zone_name = analysis.get('zone', 'unknown')
        specific_question = analysis.get('specific_question', '').lower()
        
        if venue_name == 'unknown':
            return "Which venue would you like me to check the music status for?"
        
        venue = self.venue_reader.get_venue(venue_name)
        if not venue:
            return f"I couldn't find {venue_name} in our system."
        
        venue_display_name = venue.get('property_name', venue_name)
        
        if venue.get('music_platform') != 'Soundtrack Your Brand':
            return f"I can't check what's playing at {venue_display_name} as it uses {venue.get('music_platform', 'a non-API platform')}. You'll need to check the music system directly."
        
        # If zone not specified, check if venue has only one zone or ask
        if zone_name == 'unknown':
            zones = venue.get('zone_names', '')
            if isinstance(zones, str) and zones:
                zone_list = [z.strip() for z in zones.split(',')]
                if len(zone_list) == 1:
                    zone_name = zone_list[0]
                else:
                    return f"Which zone would you like me to check? Available zones at {venue_display_name}: {', '.join(zone_list)}"
            else:
                return f"I need to know which zone to check at {venue_display_name}."
        
        # Get zone status from API
        zone_id = self._find_zone_id(venue_display_name, zone_name)
        logger.info(f"Initial zone_id search for {zone_name} at {venue_display_name}: {zone_id}")
        
        if not zone_id:
            # Try to find zone in Soundtrack system
            venue_zones = soundtrack_api.find_venue_zones(venue_display_name)
            logger.info(f"Found {len(venue_zones)} zones for {venue_display_name}")
            for z in venue_zones:
                logger.info(f"Checking zone: {z.get('name')} (id: {z.get('id')})")
                if zone_name.lower() in z.get('name', '').lower():
                    zone_id = z.get('id')
                    logger.info(f"Matched zone {zone_name} to ID: {zone_id}")
                    break
        
        if not zone_id:
            # Log available zones for debugging
            zone_names = [z.get('name', 'unknown') for z in soundtrack_api.find_venue_zones(venue_display_name)]
            logger.warning(f"Could not find zone '{zone_name}' for {venue_display_name}. Available: {zone_names}")
            return f"I couldn't find the '{zone_name}' zone in the Soundtrack system for {venue_display_name}. The zone might be named differently in the system. Please try the exact zone name as it appears in your Soundtrack dashboard."
        
        logger.info(f"Getting status for zone_id: {zone_id}")
        status = soundtrack_api.get_zone_status(zone_id)
        logger.info(f"Zone status response: {status}")
        
        if status and 'error' not in status:
            # Check if we have real data or just basic info
            playing = status.get('playing')
            volume = status.get('volume')
            current_track = status.get('current_track')
            playlist = status.get('current_playlist')
            device_online = status.get('device_online')
            
            # Check if user is asking about volume specifically
            if 'volume' in specific_question:
                if volume is not None:
                    return f"The volume at {zone_name} is currently set to {volume} out of 16."
                else:
                    return f"I couldn't retrieve the volume level for {zone_name}. You can check it in your Soundtrack app."
            
            # Don't make up status if we don't have it
            if playing is None:
                # We don't have playing status from API
                if device_online is False:
                    return f"The {zone_name} zone at {venue_display_name} appears to be offline."
                else:
                    return f"I can see the {zone_name} zone at {venue_display_name} in the system, but I cannot determine what's currently playing. You may need to check the Soundtrack dashboard directly."
            
            # Build natural response about what's playing
            if current_track:
                track_name = current_track.get('name', 'Unknown track')
                artist = current_track.get('artist', 'Unknown artist')
                if playing:
                    response = f"At {zone_name} in {venue_display_name}, \"{track_name}\" by {artist} is currently playing"
                    if playlist:
                        response += f" from the {playlist} playlist"
                    if volume is not None:
                        response += f". Volume is set to {volume}/16."
                    else:
                        response += "."
                else:
                    response = f"Music is currently paused at {zone_name} in {venue_display_name}."
            else:
                if playing:
                    response = f"Music is playing at {zone_name} in {venue_display_name}"
                    if playlist:
                        response += f" from the {playlist} playlist"
                    if volume is not None:
                        response += f". Volume is set to {volume}/16."
                    else:
                        response += "."
                else:
                    response = f"Music is currently paused at {zone_name} in {venue_display_name}."
            
            return response
        else:
            error = status.get('error', 'Unknown error') if status else 'No response'
            logger.error(f"Failed to get zone status: {error}")
            return f"I found the {zone_name} zone at {venue_display_name} but couldn't retrieve its current status. The zone might be offline or there may be a connection issue."
    
    def _handle_troubleshooting(self, analysis: Dict, user_phone: str) -> str:
        """Handle troubleshooting with quick fix attempts"""
        venue_name = analysis.get('venue', 'unknown')
        zone_name = analysis.get('zone', 'unknown')
        
        if venue_name == 'unknown':
            return "I can help troubleshoot your music system. What's your venue name?"
        
        venue = self.venue_reader.get_venue(venue_name)
        if not venue:
            return f"I couldn't find {venue_name} in our system."
        
        if venue.get('music_platform') != 'Soundtrack Your Brand':
            return self._provide_manual_troubleshooting(venue)
        
        # Try quick fix
        zone_id = self._find_zone_id(venue.get('property_name', venue_name), zone_name)
        if zone_id:
            fix_result = soundtrack_api.quick_fix_zone(zone_id)
            if fix_result.get('success'):
                fixes = fix_result.get('fixes_attempted', [])
                response = f"✅ I've attempted to fix {zone_name} at {venue.get('property_name', venue_name)}:\n"
                for fix in fixes:
                    response += f"• {fix}\n"
                response += "\nPlease check if the issue is resolved."
                return response
            else:
                # Quick fix failed - check why
                reason = fix_result.get('message', 'Unknown error')
                if 'trial' in reason.lower() or 'permission' in reason.lower():
                    return self._escalate_trial_zone(venue, zone_name, "troubleshooting", user_phone)
                else:
                    return self._escalate_api_failure(venue, zone_name, "troubleshooting", user_phone)
        
        return self._provide_manual_troubleshooting(venue)
    
    def _handle_venue_info(self, analysis: Dict) -> str:
        """Provide conversational venue information based on what's asked"""
        venue_name = analysis.get('venue', 'unknown')
        specific_question = analysis.get('specific_question', '').lower()
        
        if venue_name == 'unknown':
            return "I'd be happy to help! Which venue are you asking about?"
        
        venue = self.venue_reader.get_venue(venue_name)
        if not venue:
            return f"I couldn't find {venue_name} in our system. Could you tell me the full name of your property?"
        
        venue_display_name = venue.get('property_name', venue_name)
        
        # Answer specific questions conversationally
        if 'contract' in specific_question and 'expir' in specific_question:
            contract_end = venue.get('contract_end', 'Not specified')
            return f"Your contract at {venue_display_name} expires on {contract_end}."
        
        elif 'contract' in specific_question and 'start' in specific_question:
            contract_start = venue.get('contract_start', 'Not specified')
            return f"Your contract at {venue_display_name} started on {contract_start}."
        
        elif 'zone' in specific_question and ('count' in specific_question or 'many' in specific_question):
            zone_count = venue.get('zone_count', 'Unknown')
            zones = venue.get('zone_names', '')
            if isinstance(zones, str) and zones:
                zone_list = [z.strip() for z in zones.split(',')]
                return f"{venue_display_name} has {zone_count} zones: {', '.join(zone_list)}."
            return f"{venue_display_name} has {zone_count} zones."
        
        elif 'zone' in specific_question and 'name' in specific_question:
            zones = venue.get('zone_names', '')
            if isinstance(zones, str) and zones:
                zone_list = [z.strip() for z in zones.split(',')]
                return f"The zones at {venue_display_name} are: {', '.join(zone_list)}."
            return f"I don't have the zone names for {venue_display_name} in my records."
        
        elif 'manager' in specific_question or 'gm' in specific_question:
            contacts = venue.get('contacts', [])
            for contact in contacts:
                if 'general manager' in contact.get('title', '').lower():
                    name = contact.get('name', 'Not listed')
                    email = contact.get('email', '')
                    phone = contact.get('phone', '')
                    response = f"The General Manager at {venue_display_name} is {name}."
                    if email:
                        response += f" You can reach them at {email}"
                    if phone and phone != '-':
                        response += f" or call {phone}"
                    return response + "."
            return f"I don't have the General Manager's contact information for {venue_display_name} in my records."
        
        elif 'contact' in specific_question or 'email' in specific_question or 'phone' in specific_question:
            contacts = venue.get('contacts', [])
            if contacts:
                response = f"Here are the contacts for {venue_display_name}:\n"
                for contact in contacts[:3]:  # Limit to top 3 contacts
                    response += f"• {contact.get('title', 'Contact')}: {contact.get('name', 'N/A')}"
                    if contact.get('email'):
                        response += f" - {contact.get('email')}"
                    response += "\n"
                return response.strip()
            return f"I don't have contact information for {venue_display_name} in my records."
        
        elif 'price' in specific_question or 'cost' in specific_question or 'pay' in specific_question:
            price = venue.get('annual_price_per_zone', 'Not specified')
            zone_count = venue.get('zone_count', 0)
            currency = venue.get('currency', 'THB')
            
            # Calculate total if possible
            if 'THB' in price and zone_count:
                try:
                    import re
                    price_match = re.search(r'[\d,]+', price)
                    if price_match:
                        price_per_zone = int(price_match.group().replace(',', ''))
                        total = price_per_zone * int(zone_count)
                        return f"You're currently paying {currency} {price_per_zone:,} per zone annually. With {zone_count} zones at {venue_display_name}, that's {currency} {total:,} per year."
                except:
                    pass
            
            return f"{venue_display_name} pays {price} per zone annually, with {zone_count} zones."
        
        elif 'platform' in specific_question or 'system' in specific_question:
            platform = venue.get('music_platform', 'Unknown')
            return f"{venue_display_name} uses {platform} for their background music."
        
        # Default: provide a brief overview
        else:
            zones = venue.get('zone_names', '')
            zone_count = venue.get('zone_count', 'Unknown')
            platform = venue.get('music_platform', 'Unknown')
            contract_end = venue.get('contract_end')
            
            response = f"Sure! {venue_display_name} uses {platform} across {zone_count} zones"
            
            if isinstance(zones, str) and zones:
                zone_list = [z.strip() for z in zones.split(',')]
                response += f" ({', '.join(zone_list)})"
            
            if contract_end:
                response += f". Your contract runs until {contract_end}"
            
            response += ". What specific information would you like to know?"
            return response
    
    def _handle_general_query(self, message: str, analysis: Dict) -> str:
        """Handle general queries"""
        # Use venue data to provide accurate responses
        response = "I can help you with:\n"
        response += "• Volume control (0-16 levels)\n"
        response += "• Playback control (play/pause)\n"
        response += "• **Smart playlist selection** - Just tell me the mood or genre!\n"
        response += "  Examples: '80s hits', 'relaxing jazz', 'upbeat pop'\n"
        response += "• Zone status checks\n"
        response += "• Music troubleshooting\n"
        response += "• Venue information\n\n"
        response += "Please let me know your venue name and what you need help with."
        
        return response
    
    def _find_zone_id(self, venue_name: str, zone_name: str) -> Optional[str]:
        """Find zone ID in SYB system"""
        if not zone_name:
            return None
            
        # Search in SYB
        accounts = soundtrack_api.get_accounts()
        for account in accounts:
            # Check if account name matches venue
            if venue_name.lower() in account.get('name', '').lower():
                for loc_edge in account.get('locations', {}).get('edges', []):
                    location = loc_edge['node']
                    for zone_edge in location.get('soundZones', {}).get('edges', []):
                        zone = zone_edge['node']
                        if zone_name.lower() in zone.get('name', '').lower():
                            return zone.get('id')
        
        return None
    
    def _determine_volume_level(self, details: str) -> int:
        """Determine target volume level (0-16)"""
        details_lower = details.lower()
        
        # Check for specific levels
        import re
        match = re.search(r'(\d+)', details)
        if match:
            level = int(match.group(1))
            # Convert percentage to 0-16 scale if needed
            if level > 16:
                level = int(level * 16 / 100)
            return min(max(level, 0), 16)
        
        # Keywords to levels
        if any(word in details_lower for word in ['mute', 'silent', 'off']):
            return 0
        elif any(word in details_lower for word in ['very loud', 'maximum', 'max']):
            return 14
        elif any(word in details_lower for word in ['loud', 'up', 'higher']):
            return 11
        elif any(word in details_lower for word in ['quiet', 'soft', 'down', 'lower']):
            return 5
        elif any(word in details_lower for word in ['very quiet', 'minimum']):
            return 3
        else:
            return 8  # Default moderate level
    
    def _escalate_trial_zone(self, venue: Dict, zone_name: str, action: str, user_phone: str) -> str:
        """Escalate for trial/demo zones"""
        response = f"⚠️ Zone '{zone_name}' appears to be in trial/demo mode or lacks API control permissions.\n\n"
        response += "**Manual adjustment needed:**\n"
        response += f"1. Open Soundtrack app on the device\n"
        response += f"2. Navigate to {zone_name}\n"
        response += f"3. Adjust {action} manually\n\n"
        response += "To enable remote control, ensure API access is enabled for this account."
        
        # Log for follow-up
        self._log_escalation(venue, zone_name, action, 'trial_zone', user_phone)
        
        return response
    
    def _escalate_api_failure(self, venue: Dict, zone_name: str, action: str, user_phone: str) -> str:
        """Escalate for API failures"""
        response = f"⚠️ Unable to complete {action} for {zone_name} at {venue.get('property_name', venue_name)}.\n\n"
        response += "I'm escalating this to our technical team who will:\n"
        response += "1. Check the zone connectivity\n"
        response += "2. Verify API permissions\n"
        response += "3. Contact you with a solution\n\n"
        
        # Get venue contacts
        contacts = self.venue_reader.get_venue_contacts(venue.get('property_name', venue_name))
        if contacts:
            response += "We'll reach out to your registered contacts shortly."
        
        # Log escalation
        self._log_escalation(venue, zone_name, action, 'api_failure', user_phone)
        
        return response
    
    def _provide_manual_troubleshooting(self, venue: Dict) -> str:
        """Provide manual troubleshooting steps"""
        platform = venue.get('music_platform', 'your music system')
        
        response = f"**Troubleshooting steps for {platform}:**\n"
        response += "1. Check device power and connections\n"
        response += "2. Verify internet connectivity\n"
        response += "3. Restart the music app/device\n"
        response += "4. Check if the correct playlist is selected\n"
        response += "5. Verify volume is not muted\n\n"
        response += "If issues persist, please contact support."
        
        return response
    
    def _log_escalation(self, venue: Dict, zone_name: str, action: str, reason: str, user_phone: str):
        """Log escalation and send to Google Chat"""
        escalation = {
            'timestamp': datetime.now().isoformat(),
            'venue': venue.get('property_name', venue_name),
            'zone': zone_name,
            'action': action,
            'reason': reason,
            'user_phone': user_phone,
            'status': 'pending'
        }
        
        logger.info(f"Escalation logged: {escalation}")
        
        # Send to Google Chat
        if self.gchat:
            # Determine department and priority based on action
            if 'volume' in action.lower() or 'playlist' in action.lower():
                department = Department.DESIGN
                priority = Priority.HIGH
                title = "🎵 Music Control Issue"
            else:
                department = Department.OPERATIONS
                priority = Priority.CRITICAL if 'stopped' in action.lower() else Priority.HIGH
                title = "🔧 Music System Issue"
            
            # Build escalation message
            message = f"**{title}**\n\n"
            message += f"**Venue:** {venue.get('property_name', venue_name)}\n"
            message += f"**Zone:** {zone_name}\n"
            message += f"**Requested Action:** {action}\n"
            message += f"**Issue:** "
            
            if reason == 'trial_zone':
                message += "Zone lacks API control permissions (trial/demo)\n"
                message += "**Resolution:** Manual adjustment via SYB app required\n"
            elif reason == 'api_failure':
                message += "API control failed (connectivity/permission issue)\n"
                message += "**Resolution:** Check zone connectivity and API permissions\n"
            else:
                message += f"{reason}\n"
            
            message += f"\n**User Contact:** {user_phone}\n"
            message += f"**Time:** {escalation['timestamp']}\n"
            
            # Add venue contact info if available
            contacts = self.venue_reader.get_venue_contacts(venue.get('property_name', venue_name))
            if contacts:
                message += "\n**Venue Contacts:**\n"
                for contact in contacts[:2]:  # Show max 2 contacts
                    message += f"• {contact.get('name', 'Unknown')}: {contact.get('email', '')} {contact.get('phone', '')}\n"
            
            try:
                self.gchat.send_message(
                    message=message,
                    department=department,
                    priority=priority,
                    venue_name=venue.get('property_name', venue_name)
                )
                logger.info(f"Escalation sent to Google Chat for {venue.get('property_name', venue_name)}")
            except Exception as e:
                logger.error(f"Failed to send to Google Chat: {e}")
        else:
            logger.warning("Google Chat not available - escalation only logged locally")

# Create singleton instance
music_bot = BMASocialMusicBot()

# Example usage
if __name__ == "__main__":
    print("\n=== BMA Social Music Bot - Final Version ===")
    print("Understanding: Control is at app/cloud level, not device level")
    print("Requirement: API access must be enabled for the account\n")
    
    # Test messages
    test_messages = [
        "Volume is too loud in the lobby at Hilton Pattaya",
        "Music stopped playing in Edge zone",
        "Can you check the status of our zones?",
        "Fix the music in all zones"
    ]
    
    for msg in test_messages:
        print(f"\nUser: {msg}")
        response = music_bot.process_message(msg, "+6612345678", "Test User")
        print(f"Bot: {response}")
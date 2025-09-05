#!/usr/bin/env python3
"""
BMA Social Music Bot - Enhanced Conversational Version
======================================================
A complete rewrite that transforms the bot from a JSON-returning classifier
to a natural, helpful conversational assistant for venue managers.

Key Improvements:
- Natural conversational responses instead of JSON
- Proactive suggestions and contextual help  
- Venue data integration for informed responses
- Multi-turn conversation support with context retention
- Time-aware and personality-driven interactions
"""

import os
import json
import logging
import re
import time
import random
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
from openai import OpenAI
from venue_data_reader import VenueDataReader
from soundtrack_api import soundtrack_api
from improved_bot_prompt import get_enhanced_prompt, get_bot_config

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

class EnhancedBMASocialBot:
    """
    Enhanced conversational bot that provides natural, helpful responses
    while managing venue music systems via Soundtrack Your Brand.
    """
    
    def __init__(self):
        """Initialize enhanced bot with conversational capabilities"""
        # Load enhanced configuration
        self.config = get_bot_config()
        self.system_prompt = get_enhanced_prompt()
        
        # Initialize venue data reader
        self.venue_reader = VenueDataReader()
        
        # Initialize OpenAI with enhanced settings
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY must be set")
        
        self.client = OpenAI(api_key=api_key)
        self.model_name = self.config['model']
        self.temperature = self.config['temperature']
        self.max_tokens = self.config['max_tokens']
        
        # Initialize Google Chat for escalations
        self.gchat = GoogleChatClient() if GCHAT_AVAILABLE else None
        
        # Enhanced conversation context tracking
        self.user_context = {}  # {user_phone: {'venue': str, 'last_venue_mention': timestamp, 'recent_actions': [], 'conversation_state': str}}
        
        # Action patterns for intent extraction from natural responses
        self.action_patterns = {
            'volume': r'(turn(?:ing)?|adjust(?:ing)?|set(?:ting)?|chang(?:ing|e)).*volume|make.*(?:loud|quiet)|volume.*(?:up|down|level)',
            'playlist': r'(chang(?:ing|e)|switch(?:ing)?|play(?:ing)?|set(?:ting)?).*(?:playlist|music|genre)',
            'status': r"what's playing|now playing|current(?:ly)?.*play|check(?:ing)?.*(?:song|track|music)",
            'playback': r'(paus(?:e|ing)|stop(?:ping)?|resum(?:e|ing)|play(?:ing)?|start(?:ing)?)',
            'troubleshoot': r'(fix(?:ing)?|troubleshoot|diagnos(?:ing|tics)|reset(?:ting)?|check(?:ing)?.*issue)',
            'venue_info': r'contract|expir|renewal|pric(?:e|ing)|cost|payment|zone|contact|manager|email'
        }
        
        logger.info("Enhanced BMA Social Music Bot initialized")
        logger.info(f"Using {self.model_name} with conversational temperature {self.temperature}")
        logger.info(f"Context retention: {self.config['context_window']} seconds")
    
    def process_message(self, message: str, user_phone: str, user_name: str = None) -> str:
        """
        Process message with enhanced conversational capabilities
        
        Args:
            message: The user's message
            user_phone: User's phone number for context tracking
            user_name: Optional user name for personalization
            
        Returns:
            Natural, conversational response with actions taken
        """
        try:
            # Get or create user context
            context = self._get_user_context(user_phone)
            
            # Add time awareness to context
            current_time = datetime.now()
            time_context = self._get_time_context(current_time)
            
            # Build conversational prompt with context
            conversation_prompt = self._build_conversation_prompt(
                message, context, time_context, user_name
            )
            
            # Get natural response from LLM
            response = self._get_conversational_response(conversation_prompt)
            
            # Extract and execute any actions from the response
            actions_taken = self._execute_implied_actions(response, message, context)
            
            # Update user context based on conversation
            self._update_user_context(user_phone, message, response, actions_taken)
            
            # If actions were taken, append results to response
            if actions_taken:
                response = self._append_action_results(response, actions_taken)
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return self._get_error_response(e, context)
    
    def _get_user_context(self, user_phone: str) -> Dict:
        """Get or initialize user context with conversation history"""
        if user_phone not in self.user_context:
            self.user_context[user_phone] = {
                'venue': None,
                'last_venue_mention': 0,
                'recent_actions': [],  # Last 5 actions
                'conversation_state': 'new',
                'last_interaction': time.time()
            }
        
        context = self.user_context[user_phone]
        
        # Check if context has expired
        if time.time() - context['last_interaction'] > self.config['context_window']:
            # Reset conversation state but keep venue if mentioned recently
            if context['venue'] and (time.time() - context['last_venue_mention'] < self.config['context_window']):
                context['conversation_state'] = 'returning'
            else:
                context['venue'] = None
                context['conversation_state'] = 'new'
            context['recent_actions'] = []
        
        context['last_interaction'] = time.time()
        return context
    
    def _get_time_context(self, current_time: datetime) -> str:
        """Generate time-aware context for greetings"""
        hour = current_time.hour
        
        if 6 <= hour < 12:
            return "morning"
        elif 12 <= hour < 18:
            return "afternoon"
        elif 18 <= hour < 24:
            return "evening"
        else:
            return "late_night"
    
    def _build_conversation_prompt(self, message: str, context: Dict, 
                                  time_context: str, user_name: str = None) -> str:
        """Build a rich conversational prompt with all context"""
        prompt_parts = []
        
        # Add conversation state context
        if context['conversation_state'] == 'new':
            prompt_parts.append("This is a new conversation.")
        elif context['conversation_state'] == 'returning':
            prompt_parts.append(f"This user is returning. Their venue is {context['venue']}.")
        else:
            prompt_parts.append("This is an ongoing conversation.")
        
        # Add venue context if known
        if context['venue']:
            venue_data = self.venue_reader.get_venue(context['venue'])
            if venue_data:
                prompt_parts.append(f"Current venue: {context['venue']}")
                prompt_parts.append(f"Platform: {venue_data.get('music_platform')}")
                prompt_parts.append(f"Zones: {venue_data.get('zone_names')}")
        
        # Add recent actions for context awareness
        if context['recent_actions']:
            prompt_parts.append(f"Recent actions: {', '.join(context['recent_actions'][-3:])}")
        
        # Add time context
        prompt_parts.append(f"Time of day: {time_context}")
        
        # Add user name if provided
        if user_name:
            prompt_parts.append(f"User name: {user_name}")
        
        # Add the actual message
        prompt_parts.append(f"\nUser message: {message}")
        
        # Add response instruction
        prompt_parts.append("\nProvide a natural, helpful response. If you need to perform actions (like changing volume or playlists), indicate what you're doing conversationally. Be proactive and suggest next steps when appropriate.")
        
        return "\n".join(prompt_parts)
    
    def _get_conversational_response(self, prompt: str) -> str:
        """Get natural conversational response from LLM"""
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"LLM response error: {str(e)}")
            return "I'm having trouble processing that right now. Let me try another way..."
    
    def _execute_implied_actions(self, response: str, original_message: str, 
                                context: Dict) -> Dict[str, Any]:
        """Extract and execute actions implied in the conversational response"""
        actions_taken = {}
        
        # Combine response and original message for intent detection
        combined_text = f"{original_message} {response}".lower()
        
        # Detect venue from response or message
        venue_name = self._extract_venue(combined_text, context)
        if venue_name:
            context['venue'] = venue_name
            context['last_venue_mention'] = time.time()
        
        # Only proceed with actions if we have a venue
        if not context['venue']:
            return actions_taken
        
        venue = self.venue_reader.get_venue(context['venue'])
        if not venue or venue.get('music_platform') != 'Soundtrack Your Brand':
            return actions_taken
        
        # Detect and execute volume control
        if re.search(self.action_patterns['volume'], combined_text):
            zone_name = self._extract_zone(combined_text, venue)
            if zone_name:
                level = self._extract_volume_level(combined_text)
                result = self._execute_volume_change(venue, zone_name, level)
                if result:
                    actions_taken['volume'] = result
        
        # Detect and execute playlist change
        elif re.search(self.action_patterns['playlist'], combined_text):
            zone_name = self._extract_zone(combined_text, venue)
            playlist = self._extract_playlist(combined_text)
            if zone_name and playlist:
                result = self._execute_playlist_change(venue, zone_name, playlist)
                if result:
                    actions_taken['playlist'] = result
        
        # Detect and execute status check
        elif re.search(self.action_patterns['status'], combined_text):
            zone_name = self._extract_zone(combined_text, venue)
            if zone_name:
                result = self._check_now_playing(venue, zone_name)
                if result:
                    actions_taken['status'] = result
        
        # Detect and execute troubleshooting
        elif re.search(self.action_patterns['troubleshoot'], combined_text):
            zone_name = self._extract_zone(combined_text, venue)
            if zone_name:
                result = self._execute_troubleshooting(venue, zone_name)
                if result:
                    actions_taken['troubleshoot'] = result
        
        return actions_taken
    
    def _extract_venue(self, text: str, context: Dict) -> Optional[str]:
        """Extract venue name from text or use context"""
        text_lower = text.lower()
        
        # Check for explicit venue mentions
        if 'hilton' in text_lower or 'pattaya' in text_lower or 'pattay' in text_lower:
            return 'Hilton Pattaya'
        elif 'mana' in text_lower or 'beach club' in text_lower:
            return 'Mana Beach Club'
        
        # Use context if available and recent
        if context['venue'] and context['last_venue_mention'] > 0:
            if time.time() - context['last_venue_mention'] < self.config['context_window']:
                return context['venue']
        
        return None
    
    def _extract_zone(self, text: str, venue: Dict) -> Optional[str]:
        """Extract zone name from text"""
        text_lower = text.lower()
        zones_str = venue.get('zone_names', '')
        
        if not zones_str:
            return None
        
        zones = [z.strip() for z in zones_str.split(',')]
        
        # Check for exact zone matches
        for zone in zones:
            if zone.lower() in text_lower:
                return zone
        
        # Check for partial matches
        for zone in zones:
            zone_words = zone.lower().split()
            if any(word in text_lower for word in zone_words):
                return zone
        
        return None
    
    def _extract_volume_level(self, text: str) -> int:
        """Extract or infer volume level from text"""
        text_lower = text.lower()
        
        # Check for specific numbers
        match = re.search(r'\b(\d+)\b', text)
        if match:
            level = int(match.group(1))
            if level <= 16:
                return level
            elif level <= 100:
                # Convert percentage to 0-16 scale
                return int((level / 100) * 16)
        
        # Infer from descriptive words
        if any(word in text_lower for word in ['max', 'maximum', 'loudest', 'full']):
            return 16
        elif any(word in text_lower for word in ['loud', 'louder', 'up', 'higher']):
            return 12
        elif any(word in text_lower for word in ['medium', 'normal', 'moderate']):
            return 8
        elif any(word in text_lower for word in ['quiet', 'soft', 'low', 'down']):
            return 4
        elif any(word in text_lower for word in ['silent', 'mute', 'off']):
            return 0
        
        return 10  # Default moderate level
    
    def _extract_playlist(self, text: str) -> Optional[str]:
        """Extract playlist name or genre from text"""
        text_lower = text.lower()
        
        # Common playlist/genre keywords
        playlists = {
            'jazz': ['jazz', 'jazzy', 'smooth jazz'],
            'lounge': ['lounge', 'chill', 'relaxed', 'ambient'],
            'pop': ['pop', 'popular', 'hits', 'top 40'],
            'rock': ['rock', 'rock music', 'classic rock'],
            'electronic': ['electronic', 'edm', 'dance', 'house', 'techno'],
            'classical': ['classical', 'orchestra', 'symphony'],
            'acoustic': ['acoustic', 'unplugged', 'folk'],
            'party': ['party', 'upbeat', 'energetic', 'club'],
            'dinner': ['dinner', 'dining', 'restaurant'],
            'breakfast': ['breakfast', 'morning', 'easy listening'],
            '80s': ['80s', 'eighties', '1980s'],
            '90s': ['90s', 'nineties', '1990s'],
            'beach': ['beach', 'tropical', 'summer', 'island']
        }
        
        for playlist_name, keywords in playlists.items():
            if any(keyword in text_lower for keyword in keywords):
                return playlist_name
        
        # Check for quoted playlist names
        match = re.search(r'["\']([^"\']+)["\']', text)
        if match:
            return match.group(1)
        
        return None
    
    def _execute_volume_change(self, venue: Dict, zone_name: str, level: int) -> Dict:
        """Execute volume change via Soundtrack API"""
        try:
            zone_id = self._find_zone_id(venue.get('property_name'), zone_name)
            if not zone_id:
                return {'success': False, 'message': f"Couldn't find {zone_name} in the system"}
            
            result = soundtrack_api.set_volume(zone_id, level)
            
            if result.get('success'):
                return {
                    'success': True,
                    'zone': zone_name,
                    'level': level,
                    'message': f"Volume set to {level} in {zone_name}"
                }
            else:
                return {
                    'success': False,
                    'message': result.get('message', 'Volume change failed')
                }
                
        except Exception as e:
            logger.error(f"Volume change error: {str(e)}")
            return {'success': False, 'message': 'Technical issue with volume control'}
    
    def _execute_playlist_change(self, venue: Dict, zone_name: str, playlist: str) -> Dict:
        """Execute playlist change via Soundtrack API"""
        try:
            zone_id = self._find_zone_id(venue.get('property_name'), zone_name)
            if not zone_id:
                return {'success': False, 'message': f"Couldn't find {zone_name} in the system"}
            
            result = soundtrack_api.change_playlist(zone_id, playlist)
            
            if result.get('success'):
                return {
                    'success': True,
                    'zone': zone_name,
                    'playlist': playlist,
                    'message': f"Changed to {playlist} in {zone_name}"
                }
            else:
                return {
                    'success': False,
                    'message': result.get('message', 'Playlist change failed')
                }
                
        except Exception as e:
            logger.error(f"Playlist change error: {str(e)}")
            return {'success': False, 'message': 'Technical issue with playlist control'}
    
    def _check_now_playing(self, venue: Dict, zone_name: str) -> Dict:
        """Check what's currently playing via Soundtrack API"""
        try:
            zone_id = self._find_zone_id(venue.get('property_name'), zone_name)
            if not zone_id:
                return {'success': False, 'message': f"Couldn't find {zone_name} in the system"}
            
            result = soundtrack_api.get_now_playing(zone_id)
            
            if result.get('success'):
                track = result.get('track', {})
                return {
                    'success': True,
                    'zone': zone_name,
                    'track': track.get('name', 'Unknown'),
                    'artist': track.get('artists', [{'name': 'Unknown'}])[0].get('name'),
                    'playlist': result.get('playlist', 'Unknown'),
                    'message': f"Now playing in {zone_name}: {track.get('name')} by {track.get('artists', [{'name': 'Unknown'}])[0].get('name')}"
                }
            else:
                return {
                    'success': False,
                    'message': result.get('message', 'Could not get current track')
                }
                
        except Exception as e:
            logger.error(f"Now playing check error: {str(e)}")
            return {'success': False, 'message': 'Could not check what\'s playing'}
    
    def _execute_troubleshooting(self, venue: Dict, zone_name: str) -> Dict:
        """Execute troubleshooting via Soundtrack API quick fix"""
        try:
            zone_id = self._find_zone_id(venue.get('property_name'), zone_name)
            if not zone_id:
                return {'success': False, 'message': f"Couldn't find {zone_name} in the system"}
            
            result = soundtrack_api.quick_fix_zone(zone_id)
            
            if result.get('success'):
                fixes = result.get('fixes_attempted', [])
                return {
                    'success': True,
                    'zone': zone_name,
                    'fixes': fixes,
                    'message': f"Ran diagnostics on {zone_name}: {', '.join(fixes)}"
                }
            else:
                return {
                    'success': False,
                    'message': result.get('message', 'Troubleshooting failed'),
                    'needs_escalation': True
                }
                
        except Exception as e:
            logger.error(f"Troubleshooting error: {str(e)}")
            return {'success': False, 'message': 'Could not run diagnostics', 'needs_escalation': True}
    
    def _find_zone_id(self, venue_name: str, zone_name: str) -> Optional[str]:
        """Find zone ID in Soundtrack Your Brand system"""
        if not zone_name or not venue_name:
            return None
        
        try:
            accounts = soundtrack_api.get_accounts()
            for account in accounts:
                if venue_name.lower() in account.get('name', '').lower():
                    for loc_edge in account.get('locations', {}).get('edges', []):
                        location = loc_edge['node']
                        for zone_edge in location.get('soundZones', {}).get('edges', []):
                            zone = zone_edge['node']
                            if zone_name.lower() in zone.get('name', '').lower():
                                return zone.get('id')
        except Exception as e:
            logger.error(f"Error finding zone ID: {str(e)}")
        
        return None
    
    def _update_user_context(self, user_phone: str, message: str, 
                            response: str, actions_taken: Dict) -> None:
        """Update user context based on conversation"""
        context = self.user_context[user_phone]
        
        # Update conversation state
        if context['conversation_state'] == 'new':
            context['conversation_state'] = 'ongoing'
        
        # Track recent actions
        if actions_taken:
            for action_type, result in actions_taken.items():
                if result.get('success'):
                    action_desc = f"{action_type}:{result.get('zone', 'unknown')}"
                    context['recent_actions'].append(action_desc)
                    # Keep only last 5 actions
                    context['recent_actions'] = context['recent_actions'][-5:]
    
    def _append_action_results(self, response: str, actions_taken: Dict) -> str:
        """Append action results to response if needed"""
        # Only append if the response doesn't already mention the result
        for action_type, result in actions_taken.items():
            if not result.get('success') and result.get('needs_escalation'):
                response += f"\n\nI'll need to escalate this to our technical team. They'll be in touch within 30 minutes."
        
        return response
    
    def _get_error_response(self, error: Exception, context: Dict) -> str:
        """Generate appropriate error response"""
        error_responses = [
            "I'm having a technical moment here. Let me try a different approach...",
            "Something's not quite right. Give me a second to figure this out...",
            "Hmm, running into a small hiccup. Let me work around this..."
        ]
        
        response = random.choice(error_responses)
        
        # Add specific guidance based on error type
        if 'API' in str(error):
            response += " There might be a connection issue with the music system."
        elif 'venue' in str(error).lower():
            response += " Could you tell me which venue you're calling from?"
        
        return response

# Example usage
if __name__ == "__main__":
    bot = EnhancedBMASocialBot()
    
    # Test conversations
    test_messages = [
        ("Hi there", "+66891234567", "James"),
        ("This is Dennis from Hilton", "+66901234567", "Dennis"),
        ("Can you turn up the volume in Edge?", "+66901234567", "Dennis"),
        ("What's playing in Drift Bar right now?", "+66901234567", "Dennis"),
        ("When does our contract expire?", "+66901234567", "Dennis"),
        ("The music stopped in Shore, can you fix it?", "+66901234567", "Dennis")
    ]
    
    print("Testing Enhanced Conversational Bot:\n" + "="*50)
    
    for message, phone, name in test_messages:
        print(f"\n[{name}]: {message}")
        response = bot.process_message(message, phone, name)
        print(f"[Bot]: {response}")
        print("-" * 50)
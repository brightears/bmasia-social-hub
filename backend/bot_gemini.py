"""
Gemini-powered bot for intelligent conversation and Soundtrack integration
Uses Gemini 2.0 Flash for natural language understanding
"""

import os
import json
import logging
from typing import Dict, Any, Optional
import google.generativeai as genai
from soundtrack_api import soundtrack_api
from venue_identifier import conversation_context
from email_verification import email_verifier

# Import Google Sheets client
try:
    from google_sheets_client import GoogleSheetsClient
    sheets_client = GoogleSheetsClient()
    SHEETS_AVAILABLE = True
except Exception as e:
    logger.warning(f"Google Sheets not available: {e}")
    sheets_client = None
    SHEETS_AVAILABLE = False

logger = logging.getLogger(__name__)

class GeminiBot:
    """AI-powered bot using Google Gemini for natural conversation"""
    
    def __init__(self):
        """Initialize Gemini bot with API configuration"""
        # Configure Gemini
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        genai.configure(api_key=api_key)
        
        # Use gemini-2.0-flash-exp for latest features
        model_name = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash-exp')
        self.model = genai.GenerativeModel(model_name)
        
        # Initialize components
        self.soundtrack = soundtrack_api
        self.sheets = sheets_client if SHEETS_AVAILABLE else None
        
        logger.info(f"Gemini bot initialized with model: {model_name}")
        if SHEETS_AVAILABLE:
            logger.info("Google Sheets integration enabled")
    
    def process_message(self, message: str, user_phone: str, user_name: str = None) -> str:
        """Process message using Gemini AI with Soundtrack integration"""
        
        # First check if message mentions a venue
        venue_name = self._extract_venue_name(message)
        if venue_name:
            conversation_context.update_context(user_phone, venue={'name': venue_name})
            logger.info(f"Venue identified: {venue_name}")
        
        # Get user context
        context = conversation_context.get_context(user_phone)
        venue = context.get('venue')
        
        # Check if message asks about a zone
        zone_name = self._extract_zone_name(message)
        if zone_name and venue:
            # Fetch real zone data
            zone_data = self._fetch_zone_data(zone_name, venue)
            if zone_data:
                return zone_data
        
        # Check if message asks about venue information from sheets
        message_lower = message.lower()
        if venue and any(keyword in message_lower for keyword in ['contact', 'it support', 'phone', 'email', 'details', 'information', 'sheet']):
            sheets_data = self._get_sheets_data(venue.get('name'), message)
            if sheets_data:
                return sheets_data
        
        # Build the system prompt with context
        system_prompt = self._build_system_prompt(venue, user_phone)
        
        # Add tools/functions context for Gemini
        tools_context = self._build_tools_context()
        
        # Combine prompts
        full_prompt = f"""{system_prompt}

{tools_context}

User Context:
- Phone: {user_phone}
- Name: {user_name or 'Unknown'}
- Venue: {venue.get('name') if venue else 'Not identified'}
- Trusted: {email_verifier.is_trusted_device(user_phone, venue.get('name', '')) if venue else False}

User Message: {message}

Response Instructions:
1. If user mentions a venue (e.g., "I am from Hilton Pattaya"), acknowledge it
2. If user asks about a zone and venue is known, provide the zone information
3. Be helpful, conversational, and concise
4. Format responses with **bold** for emphasis

Response:"""
        
        try:
            # Generate response with Gemini
            response = self.model.generate_content(full_prompt)
            ai_response = response.text
            
            # Process any actions detected by Gemini
            processed_response = self._process_ai_response(ai_response, message, user_phone, venue)
            
            return processed_response
            
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            # Fallback to basic response
            return "I'm having trouble processing your request right now. Could you please try again or rephrase your question?"
    
    def _build_system_prompt(self, venue: Optional[Dict], user_phone: str) -> str:
        """Build the system prompt with current context"""
        
        base_prompt = """You are the BMA Social AI Assistant, helping venue staff with their Soundtrack Your Brand music systems.

Your capabilities:
- Check music zone status and what's currently playing
- Diagnose music playback issues
- Provide troubleshooting steps
- Access real-time zone data from Soundtrack API

Key Information:
- Venues use Soundtrack Your Brand for background music
- Common zones: Lobby, Restaurant, Bar, Pool, Spa, Edge, Horizon, Shore
- Issues include: music stopped, volume problems, device offline, network issues"""
        
        if venue:
            # Add venue-specific context
            venue_name = venue.get('name')
            zones_info = self._get_venue_zones_info(venue_name)
            
            base_prompt += f"""

Current Venue: {venue_name}
Available Zones: {zones_info}"""
        
        return base_prompt
    
    def _build_tools_context(self) -> str:
        """Build context about available tools/functions"""
        
        return """
Available Actions:
- SEARCH_ZONES: When user asks about zones or what's playing
- CHECK_ZONE_STATUS: When user mentions a specific zone name
- IDENTIFY_VENUE: When user mentions their venue name
- REQUEST_AUTH: When privileged action needs email verification
- CHECK_SHEETS: When user asks about venue data, contacts, or configurations

Examples:
- "What's playing at Edge?" -> CHECK_ZONE_STATUS for Edge zone
- "I'm from Hilton Pattaya" -> IDENTIFY_VENUE as Hilton Pattaya
- "Show me all zones" -> SEARCH_ZONES for current venue
- "What's our IT contact?" -> CHECK_SHEETS for venue contacts
- "Show venue details" -> CHECK_SHEETS for venue information
"""
    
    def _get_venue_zones_info(self, venue_name: str) -> str:
        """Get formatted zone information for a venue"""
        
        try:
            zones = self.soundtrack.find_venue_zones(venue_name)
            if not zones:
                return "No zones found"
            
            zone_names = [z.get('name') for z in zones]
            online_count = sum(1 for z in zones if z.get('online') or z.get('isOnline'))
            
            return f"{', '.join(zone_names)} ({online_count}/{len(zones)} online)"
            
        except Exception as e:
            logger.error(f"Error getting zones for {venue_name}: {e}")
            return "Unable to fetch zones"
    
    def _get_sheets_data(self, venue_name: str, query_type: str) -> Optional[str]:
        """Get data from Google Sheets for a venue"""
        
        if not self.sheets:
            return None
        
        try:
            # Find venue in master sheet
            venue_data = self.sheets.find_venue_by_name(venue_name)
            
            if not venue_data:
                return f"Venue '{venue_name}' not found in Google Sheets"
            
            # Format response based on query type
            response = f"**{venue_data.get('name', venue_name)} Information:**\n\n"
            
            if 'contact' in query_type.lower() or 'it' in query_type.lower():
                # Show contact information
                response += f"📞 **IT Contact:** {venue_data.get('it_contact', 'Not specified')}\n"
                response += f"📧 **Email:** {venue_data.get('email', 'Not specified')}\n"
                response += f"☎️ **Phone:** {venue_data.get('phone', 'Not specified')}\n"
            
            elif 'venue' in query_type.lower() or 'detail' in query_type.lower():
                # Show venue details
                response += f"📍 **Address:** {venue_data.get('address', 'Not specified')}\n"
                response += f"🏢 **Type:** {venue_data.get('type', 'Not specified')}\n"
                response += f"🎵 **Zones:** {venue_data.get('zones_count', 'Not specified')}\n"
                response += f"📅 **Contract:** {venue_data.get('contract_end', 'Not specified')}\n"
            
            elif 'zone' in query_type.lower():
                # Show zone configuration from sheets
                response += f"**Zone Configuration:**\n"
                zones = venue_data.get('zones', '').split(',') if venue_data.get('zones') else []
                for zone in zones:
                    response += f"• {zone.strip()}\n"
            
            else:
                # Show all available data
                for key, value in venue_data.items():
                    if value and key not in ['id', 'sheet_id']:
                        formatted_key = key.replace('_', ' ').title()
                        response += f"**{formatted_key}:** {value}\n"
            
            return response
            
        except Exception as e:
            logger.error(f"Error accessing Google Sheets: {e}")
            return None
    
    def _process_ai_response(self, ai_response: str, original_message: str, user_phone: str, venue: Optional[Dict]) -> str:
        """Process AI response and handle any detected actions"""
        
        # Check if AI detected specific actions in the response
        response_lower = ai_response.lower()
        
        # If AI wants to check zone status
        if 'check_zone_status' in response_lower or 'playing at' in response_lower:
            # Extract zone name from original message
            zone_name = self._extract_zone_name(original_message)
            if zone_name:
                zone_data = self._fetch_zone_data(zone_name, venue)
                if zone_data:
                    # Replace placeholder with actual data
                    ai_response = ai_response.replace('[ZONE_DATA]', zone_data)
                    return ai_response
        
        # If AI detected venue identification
        if 'identify_venue' in response_lower:
            venue_name = self._extract_venue_name(original_message)
            if venue_name:
                conversation_context.update_context(user_phone, venue={'name': venue_name})
                logger.info(f"Venue identified through Gemini: {venue_name}")
        
        return ai_response
    
    def _extract_zone_name(self, message: str) -> Optional[str]:
        """Extract zone name from message using Gemini"""
        
        prompt = f"""Extract the zone or area name from this message. 
Return ONLY the zone name, nothing else.
If no zone is mentioned, return NONE.

Examples:
"What's playing at Edge?" -> Edge
"The music in Horizon stopped" -> Horizon  
"Check the lobby zone" -> lobby
"How are things?" -> NONE

Message: {message}

Zone name:"""
        
        try:
            response = self.model.generate_content(prompt)
            zone = response.text.strip()
            if zone and zone != 'NONE':
                return zone
        except:
            pass
        
        return None
    
    def _extract_venue_name(self, message: str) -> Optional[str]:
        """Extract venue name from message using Gemini"""
        
        prompt = f"""Extract the venue/hotel name from this message.
Return ONLY the venue name, nothing else.
If no venue is mentioned, return NONE.

Examples:
"I am from Hilton Pattaya" -> Hilton Pattaya
"Calling from Millennium Hilton Bangkok" -> Millennium Hilton Bangkok
"The music stopped" -> NONE

Message: {message}

Venue name:"""
        
        try:
            response = self.model.generate_content(prompt)
            venue = response.text.strip()
            if venue and venue != 'NONE':
                return venue
        except:
            pass
        
        return None
    
    def _fetch_zone_data(self, zone_name: str, venue: Optional[Dict]) -> Optional[str]:
        """Fetch actual zone data from Soundtrack API"""
        
        try:
            # Search for zone
            if venue:
                zones = self.soundtrack.find_venue_zones(venue.get('name'))
                matching_zone = None
                for zone in zones:
                    if zone_name.lower() in zone.get('name', '').lower():
                        matching_zone = zone
                        break
            else:
                # Search across all venues
                return None
            
            if not matching_zone:
                return f"Zone '{zone_name}' not found"
            
            # Get now playing data
            zone_id = matching_zone.get('id')
            is_online = matching_zone.get('online') or matching_zone.get('isOnline')
            
            if not is_online:
                return f"Zone '{zone_name}' is currently offline"
            
            # Fetch now playing
            now_playing = self.soundtrack.get_now_playing(zone_id)
            
            if now_playing and now_playing.get('track'):
                track = now_playing['track']
                track_name = track.get('name', 'Unknown')
                
                # Handle artists
                artists_data = track.get('artists', [])
                if isinstance(artists_data, list) and artists_data:
                    if isinstance(artists_data[0], dict):
                        artists = ', '.join([a.get('name', '') for a in artists_data])
                    else:
                        artists = ', '.join(artists_data)
                else:
                    artists = 'Unknown Artist'
                
                return f"🎵 Now playing at {zone_name}: {track_name} by {artists}"
            else:
                return f"No music currently playing at {zone_name}"
                
        except Exception as e:
            logger.error(f"Error fetching zone data: {e}")
            return None


# Global instance
gemini_bot = GeminiBot()
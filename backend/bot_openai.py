"""
OpenAI GPT-4 powered bot alternative for BMA Social
Provides more reliable conversation with strict anti-hallucination measures
"""

import os
import json
import logging
from typing import Dict, Any, Optional
import openai
from soundtrack_api import soundtrack_api
from venue_identifier import conversation_context
from email_verification import email_verifier

# Import Google Sheets client with validation
try:
    from google_sheets_client import GoogleSheetsClient
    sheets_client = GoogleSheetsClient()
    # Test if sheets client can actually access data
    test_venues = sheets_client.get_all_venues()
    if test_venues:
        SHEETS_AVAILABLE = True
        logging.info(f"OpenAI Bot: Google Sheets integration active - {len(test_venues)} venues loaded")
    else:
        SHEETS_AVAILABLE = False
        logging.warning("OpenAI Bot: Google Sheets client created but no data accessible")
except Exception as e:
    logging.warning(f"OpenAI Bot: Google Sheets not available: {e}")
    sheets_client = None
    SHEETS_AVAILABLE = False

# Import smart email search (limited usage)
try:
    from smart_email_search import init_smart_search
    smart_email_searcher = init_smart_search()
    GMAIL_AVAILABLE = True
except Exception as e:
    logging.warning(f"OpenAI Bot: Gmail search not available: {e}")
    smart_email_searcher = None
    GMAIL_AVAILABLE = False

logger = logging.getLogger(__name__)

class OpenAIBot:
    """AI-powered bot using OpenAI GPT-4 with strict anti-hallucination measures"""
    
    def __init__(self):
        """Initialize OpenAI bot with API configuration"""
        
        # Configure OpenAI
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        openai.api_key = api_key
        
        # Use GPT-4 for better reasoning and less hallucination
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4-turbo')
        
        # Initialize components
        self.soundtrack = soundtrack_api
        self.sheets = sheets_client if SHEETS_AVAILABLE else None
        
        logger.info(f"OpenAI bot initialized with model: {self.model}")
        if SHEETS_AVAILABLE:
            logger.info("Google Sheets integration enabled")
    
    def process_message(self, message: str, user_phone: str, user_name: str = None, platform: str = "WhatsApp") -> str:
        """Process message using OpenAI GPT-4 with verified data sources"""
        
        # Venue identification
        venue_name = self._extract_venue_name(message)
        if venue_name:
            conversation_context.update_context(user_phone, venue={'name': venue_name})
            logger.info(f"OpenAI Bot: Venue identified: {venue_name}")
        
        # Get user context
        context = conversation_context.get_context(user_phone)
        venue = context.get('venue')
        
        # Gather verified data from sources
        data_status = self._check_data_sources()
        combined_data = self._gather_verified_venue_data(venue, message) if venue else {}
        
        # Handle specific direct queries first (to avoid AI processing overhead)
        message_lower = message.lower()
        
        # Zone listing query
        if venue and any(phrase in message_lower for phrase in ['what zones', 'our zones', 'list zones', 'all zones', 'which zones']):
            return self._handle_zone_listing(venue)
        
        # Volume control
        if venue and any(phrase in message_lower for phrase in ['volume', 'turn down', 'turn up', 'louder', 'quieter']):
            return self._handle_volume_request(message, venue)
        
        # Now playing queries
        zone_name = self._extract_zone_name(message)
        if zone_name and venue and any(phrase in message_lower for phrase in ['what\'s playing', 'now playing', 'playing at']):
            zone_data = self._get_zone_status(zone_name, venue)
            if zone_data:
                return zone_data
        
        # Contract/pricing queries - only process if we have verified data
        if any(word in message_lower for word in ['rate', 'price', 'cost', 'contract', 'expire', 'renewal']):
            if SHEETS_AVAILABLE and combined_data.get('sheets_data'):
                return self._handle_contract_query(message, venue, combined_data['sheets_data'])
            else:
                return "I'm unable to access our contract database right now. Let me connect you with our account manager who can provide current pricing and contract details."
        
        # Build OpenAI messages
        messages = self._build_openai_messages(message, venue, combined_data, data_status, user_phone, user_name)
        
        try:
            # Call OpenAI with strict parameters to reduce hallucination
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=messages,
                temperature=0.1,  # Low temperature for consistency
                max_tokens=300,   # Keep responses concise
                presence_penalty=0.3,  # Reduce repetition
                frequency_penalty=0.3,  # Reduce repetition
                top_p=0.9  # Focus on most likely tokens
            )
            
            ai_response = response.choices[0].message.content.strip()
            logger.info(f"OpenAI Bot generated response for {venue.get('name') if venue else 'unknown venue'}")
            
            return ai_response
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return "I'm having technical difficulties right now. Let me escalate this to our support team for immediate assistance."
    
    def _check_data_sources(self) -> Dict[str, bool]:
        """Check which data sources are actually working"""
        
        return {
            'sheets_available': SHEETS_AVAILABLE,
            'soundtrack_available': True,  # Assume working unless proven otherwise
            'gmail_available': GMAIL_AVAILABLE
        }
    
    def _gather_verified_venue_data(self, venue: Dict, message: str) -> Dict:
        """Gather only verified data from working sources"""
        
        combined_data = {}
        venue_name = venue.get('name') if venue else None
        
        if not venue_name:
            return combined_data
        
        # Google Sheets data with strict validation
        if SHEETS_AVAILABLE and self.sheets:
            try:
                sheets_venue = self.sheets.find_venue_by_name(venue_name)
                if sheets_venue and self._validate_sheets_data(sheets_venue):
                    combined_data['sheets_data'] = sheets_venue
                    logger.info(f"Retrieved verified sheets data for {venue_name}")
                else:
                    logger.warning(f"Sheets data for {venue_name} failed validation")
            except Exception as e:
                logger.error(f"Error accessing sheets for {venue_name}: {e}")
        
        # Soundtrack zones data
        try:
            zones = self.soundtrack.find_venue_zones(venue_name)
            if zones and isinstance(zones, list):
                combined_data['soundtrack_zones'] = zones
                combined_data['online_zones'] = [z for z in zones if z.get('online') or z.get('isOnline')]
        except Exception as e:
            logger.error(f"Error accessing Soundtrack data: {e}")
        
        # Gmail search (only for support-related queries)
        if GMAIL_AVAILABLE and smart_email_searcher:
            if any(word in message.lower() for word in ['problem', 'issue', 'support', 'help', 'previous', 'before']):
                try:
                    email_results = smart_email_searcher.smart_search(message, venue_name)
                    if email_results and email_results.get('relevance_score', 0) > 0.8:
                        combined_data['email_context'] = email_results
                except Exception as e:
                    logger.debug(f"Email search failed: {e}")
        
        return combined_data
    
    def _validate_sheets_data(self, data: Dict) -> bool:
        """Validate that sheets data contains real information"""
        
        if not data or not isinstance(data, dict):
            return False
        
        # Check for meaningful data in key fields
        key_fields = ['property_name', 'current_price_per_zone_venue_per_year', 'contract_expiry', 'expiry_date']
        
        return any(
            data.get(field) and 
            str(data.get(field)).strip() and 
            data.get(field) not in ['Not specified', 'N/A', '', 'null', 'None']
            for field in key_fields
        )
    
    def _build_openai_messages(self, message: str, venue: Dict, combined_data: Dict, data_status: Dict, user_phone: str, user_name: str) -> list:
        """Build OpenAI message format with context"""
        
        system_message = {
            "role": "system",
            "content": self._get_system_prompt(venue, data_status)
        }
        
        # Build data context
        data_context = ""
        if combined_data.get('sheets_data'):
            sheets = combined_data['sheets_data']
            data_context += f"\\nVERIFIED VENUE DATA:\\n"
            data_context += f"- Property: {sheets.get('property_name', 'N/A')}\\n"
            if sheets.get('current_price_per_zone_venue_per_year'):
                data_context += f"- Rate: {sheets.get('current_price_per_zone_venue_per_year')}\\n"
            if sheets.get('contract_expiry') or sheets.get('expiry_date'):
                expiry = sheets.get('contract_expiry') or sheets.get('expiry_date')
                data_context += f"- Contract expires: {expiry}\\n"
        
        if combined_data.get('soundtrack_zones'):
            zones = combined_data['soundtrack_zones']
            online = combined_data.get('online_zones', [])
            data_context += f"\\nZONE STATUS:\\n"
            data_context += f"- Total zones: {len(zones)}\\n"
            data_context += f"- Online: {len(online)}\\n"
            data_context += f"- Zone names: {', '.join([z.get('name', '') for z in zones])}\\n"
        
        user_message = {
            "role": "user", 
            "content": f"User: {user_name or 'Unknown'} (Phone: {user_phone})\\n"
                      f"Venue: {venue.get('name') if venue else 'Not identified'}\\n"
                      f"Message: {message}\\n"
                      f"{data_context}"
        }
        
        return [system_message, user_message]
    
    def _get_system_prompt(self, venue: Dict, data_status: Dict) -> str:
        """Get system prompt with current data source status"""
        
        return f"""You are Scott from BMA Social support, helping venues with their music systems via WhatsApp.

CRITICAL - DATA SOURCE STATUS:
- Google Sheets (contracts/pricing): {'✅ AVAILABLE' if data_status['sheets_available'] else '❌ UNAVAILABLE'}
- Soundtrack API (music zones): {'✅ AVAILABLE' if data_status['soundtrack_available'] else '❌ UNAVAILABLE'}
- Email search: {'✅ AVAILABLE' if data_status['gmail_available'] else '❌ UNAVAILABLE'}

🚨 ANTI-HALLUCINATION PROTOCOL:
1. NEVER invent contract rates, dates, or pricing information
2. If Google Sheets is unavailable, say "I need to check with our team for pricing/contract info"
3. Only provide information explicitly given in VERIFIED VENUE DATA section
4. If you don't have data, offer to escalate: "Let me connect you with our account manager"
5. Be honest about system limitations

PERSONALITY:
- Conversational and helpful like a real colleague
- Use contractions (I'm, you're, let's)
- Keep responses short and natural (this is WhatsApp)
- Show empathy for problems
- ONE response only - never repeat information

VENUE TERMINOLOGY:
- PROPERTY = Main establishment (e.g., "Hilton Pattaya")
- ZONE = Music areas within property (e.g., "Lobby", "Pool", "Edge Bar")
- When they say "I'm from Hilton Pattaya" - that's their PROPERTY name

RESPONSE GUIDELINES:
- Answer directly and briefly
- Acknowledge their property: "Got it, checking Hilton Pattaya..."
- For problems, show empathy: "That's frustrating, let me help..."
- Only offer additional help if relevant
- Use verified data only - never guess or speculate"""
    
    def _handle_contract_query(self, message: str, venue: Dict, sheets_data: Dict) -> str:
        """Handle contract/pricing queries with verified data only"""
        
        message_lower = message.lower()
        response_parts = []
        
        # Rate information
        if any(word in message_lower for word in ['rate', 'price', 'cost', 'fee', 'pricing']):
            rate_info = (
                sheets_data.get('current_price_per_zone_venue_per_year') or
                sheets_data.get('annual_price_per_zone') or
                sheets_data.get('rate')
            )
            
            if rate_info and str(rate_info).strip() not in ['', 'N/A', 'Not specified']:
                response = f"Your current rate is {rate_info}"
                
                # Add zone calculation if available
                zone_count = sheets_data.get('amount_of_zones_venues') or sheets_data.get('no_of_zones')
                if zone_count and str(zone_count).isdigit():
                    zones = int(zone_count)
                    if 'THB' in str(rate_info) and zones > 0:
                        import re
                        numbers = re.findall(r'[\\d,]+', str(rate_info))
                        if numbers:
                            per_zone = int(numbers[0].replace(',', ''))
                            total = per_zone * zones
                            response += f" per zone per year. With your {zones} zones, that's THB {total:,} total annually"
                
                response_parts.append(response)
        
        # Contract expiry
        if any(word in message_lower for word in ['contract', 'expire', 'expiry', 'renewal']):
            expiry = sheets_data.get('contract_expiry') or sheets_data.get('expiry_date')
            if expiry and str(expiry).strip() not in ['', 'N/A', 'Not specified']:
                response_parts.append(f"Your contract expires on {expiry}")
        
        if response_parts:
            return ". ".join(response_parts) + "."
        else:
            return "I don't see that information in our records. Let me connect you with our account manager for current details."
    
    def _handle_zone_listing(self, venue: Dict) -> str:
        """Handle zone listing requests"""
        
        try:
            zones = self.soundtrack.find_venue_zones(venue.get('name'))
            if zones:
                zone_names = [z.get('name', 'Unknown') for z in zones]
                online_count = len([z for z in zones if z.get('online') or z.get('isOnline')])
                
                response = f"You have {len(zones)} music zones: "
                response += ", ".join(zone_names[:-1])
                if len(zone_names) > 1:
                    response += f", and {zone_names[-1]}"
                else:
                    response += zone_names[0] if zone_names else ""
                response += f". {online_count} {'is' if online_count == 1 else 'are'} currently online."
                return response
            else:
                return "I'm not seeing any zones for your property. Let me check the system setup with our tech team."
        except Exception as e:
            logger.error(f"Error getting zones: {e}")
            return "I'm having trouble accessing your zone information right now. Let me escalate this to our tech team."
    
    def _handle_volume_request(self, message: str, venue: Dict) -> str:
        """Handle volume control requests"""
        
        zone_name = self._extract_zone_name(message)
        
        if 'adjust' in message.lower() or 'change' in message.lower() or 'set' in message.lower():
            if zone_name:
                return self._set_volume(message, zone_name, venue)
            else:
                return "Which zone would you like me to adjust? Just let me know the zone name."
        elif zone_name:
            return self._set_volume(message, zone_name, venue)
        else:
            return "Which zone's volume needs adjusting? Let me know the zone name and if you want it louder or quieter."
    
    def _set_volume(self, message: str, zone_name: str, venue: Dict) -> str:
        """Set volume for a specific zone"""
        
        try:
            zones = self.soundtrack.find_venue_zones(venue.get('name'))
            matching_zone = None
            
            if zones:
                for zone in zones:
                    if zone_name.lower() in zone.get('name', '').lower():
                        matching_zone = zone
                        break
            
            if not matching_zone:
                return f"I couldn't find a zone called '{zone_name}'. Could you check the name?"
            
            # Parse volume from message (simplified)
            message_lower = message.lower()
            if any(word in message_lower for word in ['down', 'lower', 'quieter']):
                volume = 30
                action = "lowered"
            elif any(word in message_lower for word in ['up', 'higher', 'louder']):
                volume = 70
                action = "raised"
            else:
                return f"Would you like me to turn {zone_name} up or down?"
            
            # Set volume via API
            zone_id = matching_zone.get('id')
            success = self.soundtrack.set_volume(zone_id, volume)
            
            if success:
                return f"Done! I've {action} the volume for {zone_name}."
            else:
                return f"I'm having trouble adjusting {zone_name} right now. You can try the Soundtrack app, or I can escalate this to our tech team."
                
        except Exception as e:
            logger.error(f"Volume control error: {e}")
            return "I'm having technical difficulties with volume control. Let me get our tech team to help you directly."
    
    def _get_zone_status(self, zone_name: str, venue: Dict) -> str:
        """Get current status/music for a zone"""
        
        try:
            zones = self.soundtrack.find_venue_zones(venue.get('name'))
            matching_zone = None
            
            for zone in zones:
                if zone_name.lower() in zone.get('name', '').lower():
                    matching_zone = zone
                    break
            
            if not matching_zone:
                return f"I couldn't find a zone called '{zone_name}' at your property."
            
            is_online = matching_zone.get('online') or matching_zone.get('isOnline')
            if not is_online:
                return f"The {zone_name} zone appears to be offline. Would you like me to help troubleshoot?"
            
            # Get now playing
            zone_id = matching_zone.get('id')
            now_playing = self.soundtrack.get_now_playing(zone_id)
            
            if now_playing and now_playing.get('track'):
                track = now_playing['track']
                track_name = track.get('name', 'Unknown')
                artists = track.get('artists', [])
                
                if isinstance(artists, list) and artists:
                    if isinstance(artists[0], dict):
                        artist_names = ', '.join([a.get('name', '') for a in artists])
                    else:
                        artist_names = ', '.join(artists)
                else:
                    artist_names = 'Unknown Artist'
                
                return f"🎵 {zone_name} is playing: {track_name} by {artist_names}"
            else:
                return f"{zone_name} is online but I don't see any music playing right now."
                
        except Exception as e:
            logger.error(f"Zone status error: {e}")
            return f"I'm having trouble checking {zone_name} right now. Let me escalate this to our tech team."
    
    def _extract_venue_name(self, message: str) -> Optional[str]:
        """Extract venue name using OpenAI"""
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",  # Use cheaper model for extraction
                messages=[{
                    "role": "system",
                    "content": "Extract ONLY the property/hotel name from the message. Return just the name or 'NONE' if no property mentioned. Examples: 'I'm from Hilton Pattaya' -> 'Hilton Pattaya', 'Edge Bar music stopped' -> 'NONE'"
                }, {
                    "role": "user",
                    "content": message
                }],
                temperature=0.1,
                max_tokens=50
            )
            
            result = response.choices[0].message.content.strip()
            return result if result != 'NONE' else None
            
        except Exception as e:
            logger.debug(f"Venue extraction failed: {e}")
            return None
    
    def _extract_zone_name(self, message: str) -> Optional[str]:
        """Extract zone name using OpenAI"""
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{
                    "role": "system", 
                    "content": "Extract ONLY the zone/area name from the message. Return just the name or 'NONE'. Examples: 'Edge Bar music' -> 'Edge', 'lobby volume' -> 'lobby', 'general question' -> 'NONE'"
                }, {
                    "role": "user",
                    "content": message
                }],
                temperature=0.1,
                max_tokens=20
            )
            
            result = response.choices[0].message.content.strip()
            return result if result != 'NONE' else None
            
        except Exception as e:
            logger.debug(f"Zone extraction failed: {e}")
            return None


# Global instance
openai_bot = OpenAIBot()
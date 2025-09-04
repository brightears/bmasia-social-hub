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

# Set up logging first
logger = logging.getLogger(__name__)

# Import Google Sheets client
try:
    from google_sheets_client import GoogleSheetsClient
    sheets_client = GoogleSheetsClient()
    # Test if sheets client can actually access data
    test_venues = sheets_client.get_all_venues()
    if test_venues:
        SHEETS_AVAILABLE = True
        logger.info(f"Google Sheets integration active - {len(test_venues)} venues loaded")
    else:
        SHEETS_AVAILABLE = False
        logger.warning("Google Sheets client created but no data accessible - credentials may be missing")
except Exception as e:
    logger.warning(f"Google Sheets not available: {e}")
    sheets_client = None
    SHEETS_AVAILABLE = False

# Import Gmail smart search
try:
    from smart_email_search import init_smart_search
    smart_email_searcher = init_smart_search()
    GMAIL_AVAILABLE = True
except Exception as e:
    logger.warning(f"Gmail search not available: {e}")
    smart_email_searcher = None
    GMAIL_AVAILABLE = False

# Import Google Chat for escalations
try:
    from google_chat_client import chat_client, should_escalate, Department, Priority
    CHAT_AVAILABLE = True
except Exception as e:
    logger.warning(f"Google Chat not available: {e}")
    chat_client = None
    CHAT_AVAILABLE = False

# Import Google Drive for documents
try:
    from google_drive_client import drive_client, find_venue_contract, find_troubleshooting_guide
    DRIVE_AVAILABLE = True
except Exception as e:
    logger.warning(f"Google Drive not available: {e}")
    drive_client = None
    DRIVE_AVAILABLE = False

class GeminiBot:
    """AI-powered bot using Google Gemini for natural conversation"""
    
    def __init__(self):
        """Initialize Gemini bot with API configuration"""
        # Configure Gemini
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        genai.configure(api_key=api_key)
        
        # Use gemini-2.5-flash for better performance
        model_name = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
        self.model = genai.GenerativeModel(model_name)
        
        # Initialize components
        self.soundtrack = soundtrack_api
        self.sheets = sheets_client if SHEETS_AVAILABLE else None
        
        logger.info(f"Gemini bot initialized with model: {model_name}")
        if SHEETS_AVAILABLE:
            logger.info("Google Sheets integration enabled")
    
    def process_message(self, message: str, user_phone: str, user_name: str = None, platform: str = "WhatsApp") -> str:
        """Process message using Gemini AI with integrated data from multiple sources"""
        
        # First check if message mentions a venue
        venue_name = self._extract_venue_name(message)
        if venue_name:
            conversation_context.update_context(user_phone, venue={'name': venue_name})
            logger.info(f"Venue identified: {venue_name}")
        
        # Get user context
        context = conversation_context.get_context(user_phone)
        venue = context.get('venue')
        
        # Gather all available data from multiple sources
        combined_data = self._gather_all_venue_data(venue, message) if venue else {}
        
        # Check for specific queries that need immediate data
        message_lower = message.lower()
        
        # Check if asking for list of zones for the property
        if venue and any(phrase in message_lower for phrase in ['what zones', 'our zones', 'list zones', 'all zones', 'which zones', 'name of our zones', 'names of zones', 'zone names', 'music zones']):
            zones = self.soundtrack.find_venue_zones(venue.get('name'))
            if zones:
                zone_names = [z.get('name', 'Unknown') for z in zones]
                online_count = len([z for z in zones if z.get('online') or z.get('isOnline')])
                
                # Natural response about zones
                response = f"You currently have {len(zones)} music zones registered: "
                response += ", ".join(zone_names[:-1])
                if len(zone_names) > 1:
                    response += f", and {zone_names[-1]}"
                else:
                    response += zone_names[0] if zone_names else ""
                response += f". 👍\n\n{online_count} {'zone is' if online_count == 1 else 'zones are'} currently online."
                return response
        
        # For volume control requests
        if venue and any(phrase in message_lower for phrase in ['volume', 'turn down', 'turn up', 'louder', 'quieter', 'softer']):
            # Extract zone name if specified, otherwise ask which zone
            zone_name = self._extract_zone_name(message)
            
            if 'adjust' in message_lower or 'change' in message_lower or 'set' in message_lower:
                if zone_name:
                    return self._handle_volume_control(message, zone_name, venue)
                else:
                    return "Which zone are you looking to adjust the volume for? Just let me know which one and I can get that sorted for you."
            elif zone_name:
                # Just asking about a specific zone
                return self._handle_volume_control(message, zone_name, venue)
            else:
                return "Which zone's volume do you want to adjust? Let me know the zone name and what level you'd like."
        
        # For specific zone/music queries - check Soundtrack API
        # Only return direct data if it's a simple status query
        zone_name = self._extract_zone_name(message)
        if zone_name and venue and any(phrase in message_lower for phrase in ['what\'s playing', 'now playing', 'playing at', 'music at']):
            zone_data = self._fetch_zone_data(zone_name, venue)
            if zone_data and 'offline' not in zone_data.lower():
                return zone_data
        
        # Note: Most queries will be handled by Gemini with combined data context
        # This prevents duplicate responses while ensuring all data sources are available
        
        # Build the system prompt with context
        system_prompt = self._build_system_prompt(venue, user_phone)
        
        # Add tools/functions context for Gemini
        tools_context = self._build_tools_context()
        
        # Add combined data context
        data_context = ""
        
        # CRITICAL: Only use pre-formatted response if we have VERIFIED data
        if combined_data.get('sheets_response') and combined_data.get('sheets_data'):
            # Double-check the response contains real information (not fallback text)
            response = combined_data['sheets_response']
            if response and not any(phrase in response for phrase in [
                "I don't see that information",
                "Let me find the right contact", 
                "Let me check with the team"
            ]):
                message_lower = message.lower()
                if any(word in message_lower for word in ['rate', 'price', 'cost', 'contract', 'expire', 'renewal']):
                    logger.info(f"Returning verified sheets data for {venue.get('name')}")
                    return response
        
        if combined_data:
            data_context = "\n\nAvailable Data:\n"
            if combined_data.get('sheets_data'):
                sheets = combined_data['sheets_data']
                data_context += f"- Contract expires: {sheets.get('contract_expiry', sheets.get('expiry_date', 'N/A'))}\n"
                data_context += f"- Rate: {sheets.get('current_price_per_zone_venue_per_year', 'N/A')}\n"
                data_context += f"- Contact: {sheets.get('contact_name_1', 'N/A')}\n"
                data_context += f"- Zones in property: {sheets.get('amount_of_zones_venues', sheets.get('no_of_zones', 'N/A'))}\n"
            if combined_data.get('soundtrack_zones'):
                zones = combined_data['soundtrack_zones']
                online = combined_data.get('online_zones', [])
                data_context += f"- Active zones: {len(online)}/{len(zones)} online\n"
                data_context += f"- Zone names: {', '.join([z.get('name', '') for z in zones])}\n"
            if combined_data.get('email_summary'):
                data_context += f"\nEmail History:\n{combined_data['email_summary']}\n"
            if combined_data.get('contract_document'):
                data_context += f"\n📄 Contract Documents:\n{combined_data['contract_document']}\n"
            if combined_data.get('tech_documents'):
                data_context += f"\n📚 Technical Documentation:\n{combined_data['tech_documents']}\n"
        
        # Combine prompts
        full_prompt = f"""{system_prompt}

{tools_context}
{data_context}

User Context:
- Phone: {user_phone}
- Name: {user_name or 'Unknown'}
- Venue: {venue.get('name') if venue else 'Not identified'}
- Trusted: {email_verifier.is_trusted_device(user_phone, venue.get('name', '')) if venue else False}

User Message: {message}

Response Guidelines:
1. Answer their question directly - don't repeat information unless asked
2. If they mention their property, acknowledge it briefly: "Got it, checking Hilton Pattaya..."
3. For data questions - give just what they asked for, not everything you know
4. Keep it short and natural - this is WhatsApp, not a report
5. When something's wrong, show empathy: "Oh that's not right, let me check..."
6. Only offer additional help if relevant: "Want me to check the other zones too?"
7. CRITICAL: Give ONE response only - never repeat the same information twice
8. If you have contract/rate data, give it once clearly and stop there
9. Property identification: Always treat property names as containing zones, never AS zones
10. ANTI-HALLUCINATION: Never make up information. If you don't have data, say so honestly
11. VERIFIED DATA ONLY: Only provide information that comes from verified sources (sheets, API)
12. NO SPECULATION: Don't guess rates, dates, or contact details

Remember: You're Scott, a real person helping via WhatsApp. Be human, be helpful, be brief.
NEVER give duplicate responses or repeat information unnecessarily.

🚨 CRITICAL ANTI-HALLUCINATION RULES:
- If you don't have contract/pricing data from Google Sheets, say "I need to check with our team"
- Never invent contract rates, expiry dates, or contact information
- If sheets integration is down, admit it: "I'm having trouble accessing our records right now"
- Only state facts from verified API responses or sheets data
- When in doubt, offer to escalate rather than guess

Response:"""
        
        try:
            # Generate response with Gemini
            response = self.model.generate_content(full_prompt)
            ai_response = response.text
            
            # Process any actions detected by Gemini
            processed_response = self._process_ai_response(ai_response, message, user_phone, venue)
            
            # Check if this needs escalation to Google Chat
            if CHAT_AVAILABLE and chat_client and should_escalate(message):
                try:
                    # Gather context for escalation
                    venue_data_for_chat = {}
                    if combined_data.get('sheets_data'):
                        sheets = combined_data['sheets_data']
                        venue_data_for_chat = {
                            'contract_end': sheets.get('expiry_date'),
                            'zones': sheets.get('no_of_zones'),
                            'contact': sheets.get('client_contact')
                        }
                    
                    # Send to Google Chat
                    chat_client.send_notification(
                        message=message,
                        venue_name=venue.get('name') if venue else None,
                        venue_data=venue_data_for_chat,
                        user_info={
                            'name': user_name or 'Unknown',
                            'phone': user_phone,
                            'platform': platform
                        },
                        context=f"Bot response: {processed_response[:200]}..."
                    )
                    
                    # Add escalation notice to response
                    processed_response += "\n\n🚨 *This issue has been escalated to our support team for immediate attention.*"
                    
                except Exception as e:
                    logger.error(f"Failed to escalate to Google Chat: {e}")
            
            return processed_response
            
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            # Fallback to basic response
            return "I'm having trouble processing your request right now. Could you please try again or rephrase your question?"
    
    def _gather_all_venue_data(self, venue: Dict, message: str) -> Dict:
        """Gather data from all available sources for comprehensive response"""
        
        combined_data = {}
        venue_name = venue.get('name') if venue else None
        
        if not venue_name:
            return combined_data
        
        # 1. Get Google Sheets data - STRICT DATA VALIDATION
        sheets_venue = None
        if SHEETS_AVAILABLE and self.sheets:
            try:
                sheets_venue = self.sheets.find_venue_by_name(venue_name)
                if sheets_venue and isinstance(sheets_venue, dict):
                    # Verify we have meaningful data
                    has_real_data = any(
                        sheets_venue.get(key) and str(sheets_venue.get(key)).strip() != ''
                        for key in ['property_name', 'current_price_per_zone_venue_per_year', 'annual_price_per_zone', 'contract_expiry', 'expiry_date']
                    )
                    
                    if has_real_data:
                        combined_data['sheets_data'] = sheets_venue
                        logger.info(f"Retrieved valid sheets data for {venue_name}")
                        
                        # Pre-format common queries ONLY if we have actual data
                        message_lower = message.lower()
                        if any(word in message_lower for word in ['rate', 'price', 'cost', 'fee', 'pricing', 'charge']):
                            rate_response = self._format_contract_info(sheets_venue, venue_name, include_rate=True)
                            if rate_response and "I don't see that information" not in rate_response:
                                combined_data['sheets_response'] = rate_response
                        elif any(word in message_lower for word in ['contract', 'renewal', 'expire']):
                            include_rate = any(word in message_lower for word in ['rate', 'price', 'cost'])
                            contract_response = self._format_contract_info(sheets_venue, venue_name, include_rate=include_rate)
                            if contract_response and "I don't see that information" not in contract_response:
                                combined_data['sheets_response'] = contract_response
                        elif any(word in message_lower for word in ['contact', 'email', 'phone']):
                            contact_response = self._format_contact_info(sheets_venue, venue_name)
                            if contact_response and "Let me find the right contact" not in contact_response:
                                combined_data['sheets_response'] = contact_response
                    else:
                        logger.warning(f"Found venue {venue_name} in sheets but data appears empty")
                else:
                    logger.info(f"Venue {venue_name} not found in Google Sheets")
            except Exception as e:
                logger.error(f"Error accessing sheets data for {venue_name}: {e}")
        else:
            logger.warning("Google Sheets integration not available - cannot access contract/pricing data")
        
        # 2. Get Soundtrack zones data
        try:
            zones = self.soundtrack.find_venue_zones(venue_name)
            if zones:
                combined_data['soundtrack_zones'] = zones
                combined_data['zone_count'] = len(zones)
                combined_data['online_zones'] = [z for z in zones if z.get('online') or z.get('isOnline')]
        except Exception as e:
            logger.debug(f"Could not get Soundtrack data: {e}")
        
        # 3. Google Drive search (for contracts and docs)
        try:
            if DRIVE_AVAILABLE and drive_client:
                # Check for contract queries
                if any(word in message.lower() for word in ['contract', 'agreement', 'terms', 'renewal']):
                    contract_info = find_venue_contract(venue_name)
                    if contract_info:
                        combined_data['contract_document'] = contract_info
                
                # Check for troubleshooting queries  
                if any(word in message.lower() for word in ['troubleshoot', 'problem', 'issue', 'help', 'guide', 'manual']):
                    tech_docs = find_troubleshooting_guide(message)
                    if tech_docs:
                        combined_data['tech_documents'] = tech_docs
        except Exception as e:
            logger.debug(f"Could not search Drive: {e}")
        
        # 4. Smart Email Search (only when contextually relevant to avoid noise)
        if GMAIL_AVAILABLE and smart_email_searcher:
            try:
                # Only search emails if the query is support-related or historical
                search_relevant = any(word in message.lower() for word in [
                    'previous', 'before', 'last time', 'history', 'earlier', 'problem', 'issue', 'support', 'help'
                ])
                
                if search_relevant:
                    # Extract domain from sheets data if available
                    domain = None
                    if sheets_venue:
                        email = sheets_venue.get('client_contact', '')
                        if '@' in email:
                            domain = email.split('@')[1]
                    
                    # Perform targeted search
                    email_results = smart_email_searcher.smart_search(message, venue_name, domain)
                    if email_results and email_results.get('found') and email_results.get('relevance_score', 0) > 0.7:
                        combined_data['email_context'] = email_results
                        combined_data['email_summary'] = smart_email_searcher.format_for_bot(email_results)
                        logger.info(f"Added relevant email context for {venue_name}")
            except Exception as e:
                logger.debug(f"Could not search emails: {e}")
        
        return combined_data
    
    def _format_contract_info(self, venue_data: Dict, venue_name: str, include_rate: bool = False) -> str:
        """Format contract information from sheets data - natural conversation style"""
        response_parts = []
        
        # Get contract expiry
        expiry = venue_data.get('contract_expiry') or venue_data.get('expiry_date')
        
        # Get rate information
        rate_info = (venue_data.get('current_price_per_zone_venue_per_year') or
                    venue_data.get('rate') or
                    venue_data.get('monthly_rate') or
                    venue_data.get('contract_rate'))
        
        zone_count = venue_data.get('amount_of_zones_venues', '')
        
        # Handle rate questions
        if include_rate and rate_info:
            rate_response = f"Your current rate is {rate_info}"
            if 'per_zone' in str(venue_data.keys()):
                rate_response += " per zone per year"
            
            if zone_count:
                try:
                    zones = int(zone_count)
                    if 'THB' in str(rate_info):
                        # Extract number from rate
                        import re
                        numbers = re.findall(r'[\d,]+', str(rate_info))
                        if numbers:
                            per_zone = numbers[0].replace(',', '')
                            total = int(per_zone) * zones
                            rate_response += f". With your {zones} zones, that's THB {total:,} total per year"
                except:
                    pass
            response_parts.append(rate_response)
        
        # Handle expiry questions
        if expiry and expiry != 'Not specified':
            expiry_response = f"Your contract expires on {expiry}"
            
            # Add a helpful note if renewal is coming up
            if "2025" in str(expiry):
                if not include_rate:  # Don't repeat if we already mentioned rate
                    expiry_response += ". You might want to start thinking about renewal options soon"
            else:
                expiry_response += " - plenty of time left! 👍"
            response_parts.append(expiry_response)
        
        if response_parts:
            return ". ".join(response_parts) + "."
        else:
            return "I don't see that information in our records. Let me check with the team and get back to you."
    
    def _get_contract_info_from_sheets(self, venue_name: str) -> str:
        """Get contract information directly from sheets"""
        if not self.sheets or not venue_name:
            return "I need to know your venue to check contract information."
        
        try:
            venue_data = self.sheets.find_venue_by_name(venue_name)
            if venue_data:
                return self._format_contract_info(venue_data, venue_name)
            else:
                return f"I couldn't find contract information for {venue_name} in our records."
        except Exception as e:
            logger.error(f"Error getting contract info: {e}")
            return "I'm having trouble accessing the contract information right now. Please try again."
    
    def _format_contact_info(self, venue_data: Dict, venue_name: str) -> str:
        """Format contact information from sheets data - natural conversation style"""
        
        # Get primary contact
        contact_name = venue_data.get('contact_name_1')
        contact_email = venue_data.get('contact_email_1')
        contact_title = venue_data.get('contact_title_1')
        
        if contact_name:
            response = f"Your main contact is {contact_name}"
            if contact_title:
                response += f" ({contact_title})"
            if contact_email:
                response += f" - you can reach them at {contact_email}"
            
            # Check for additional contacts
            if venue_data.get('contact_name_2'):
                response += f". You also have {venue_data.get('contact_name_2')}"
                if venue_data.get('contact_email_2'):
                    response += f" at {venue_data.get('contact_email_2')}"
        else:
            response = "Let me find the right contact person for you. One moment..."
        
        return response
    
    def _build_system_prompt(self, venue: Optional[Dict], user_phone: str) -> str:
        """Build the system prompt with current context"""
        
        base_prompt = """You're Scott from the BMA support team, helping venues with their music systems.

CRITICAL UNDERSTANDING - PROPERTY vs ZONE:
- PROPERTY = The main establishment/hotel (e.g., "Hilton Pattaya", "Marriott Bangkok")
- ZONE = Individual music areas within a property (e.g., "Lobby", "Pool", "Restaurant", "Edge Bar")

IMPORTANT: When someone says "I'm from Hilton Pattaya" - that's their PROPERTY name.
- NEVER search for zones called "Hilton Pattaya" 
- INSTEAD: Search for zones WITHIN Hilton Pattaya property
- The property contains multiple zones, each with separate music players

CONVERSATION FLOW:
1. User identifies their property: "I'm from Hilton Pattaya"
2. You acknowledge: "Got it, checking Hilton Pattaya's music zones..."
3. You then work with their zones: Edge, Lobby, Pool, etc.
4. NEVER say "Zone 'Hilton Pattaya' not found" - that's wrong logic!

Personality & Style:
- Be conversational and natural, like a helpful colleague chatting on WhatsApp
- Use contractions (I'm, you're, let's, that's) 
- Show empathy when there are problems ("Oh no, that's frustrating!" or "I understand how annoying that must be")
- Be friendly but professional
- Keep responses concise - this is WhatsApp, not email

How to respond:
- When they mention their property: "Got it, let me check Hilton Pattaya's music system..."
- Acknowledge issues naturally: "Let me check what's happening with your music zones..."
- Explain simply: "Looks like your Edge Bar zone went offline about 10 minutes ago"
- Offer help conversationally: "I can help you get that sorted"
- Use their name occasionally if you know it
- Add appropriate emojis sparingly (👍 ✅ 🎵) but don't overdo it

What you know:
- Properties use Soundtrack Your Brand for their background music across multiple zones
- Common zone names within properties: Lobby, Restaurant, Bar, Pool, Spa, Edge, Horizon, Shore
- Each zone is a separate music player within the property
- Common issues: music stopped, offline zones, volume problems, network issues
- You have access to real-time zone status and what's playing
- "Rate" usually means contract pricing/fees, not music tempo
- You can adjust zone volumes - just ask to turn it up/down or set a specific level (0-100)

Never:
- Say you're an AI, bot, or assistant
- Use overly formal language
- Give long technical explanations
- Start with "Greetings" or "Hello, I am..."
- Use robotic phrases like "How may I assist you today?"
- Confuse properties with zones - they are completely different things! """
        
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
Intelligent Data Sources:
I automatically check multiple sources to provide comprehensive information:

1. **Google Sheets** - For:
   - Contract details and expiry dates
   - Contact information (names, emails, phones)
   - Venue configuration and metadata
   - Business information

2. **Soundtrack API** - For:
   - Real-time music playing in zones
   - Zone online/offline status
   - Current track information
   - Playback control

3. **Gmail Search** - Smart contextual search for:
   - Previous support issues and resolutions
   - Contract negotiations and pricing discussions
   - Follow-ups and ongoing conversations
   - Historical context when mentioned

I intelligently combine data from all sources to give complete answers.
Email search only activates when contextually relevant to save resources.
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
            venue_display_name = venue_data.get('outlet_name') or venue_data.get('client_name') or venue_name
            response = f"**{venue_display_name} Information:**\n\n"
            
            if 'contact' in query_type.lower() or 'it' in query_type.lower():
                # Show contact information
                contact_name = venue_data.get('name', venue_data.get('client_contact', 'Not specified'))
                email = venue_data.get('email', venue_data.get('client_contact', 'Not specified'))
                phone = venue_data.get('phone_number', venue_data.get('phone', 'Not specified'))
                
                response += f"👤 **Contact Person:** {contact_name}\n"
                response += f"📧 **Email:** {email}\n"
                response += f"☎️ **Phone:** {phone}\n"
                response += f"💼 **Position:** {venue_data.get('position_/_job_title', 'Not specified')}\n"
            
            elif 'venue' in query_type.lower() or 'detail' in query_type.lower():
                # Show venue details
                response += f"📍 **Address:** {venue_data.get('address', 'Not specified')}\n"
                response += f"🏢 **Type:** {venue_data.get('client_type', 'Not specified')}\n"
                response += f"🎵 **Zones:** {venue_data.get('no_of_zones', 'Not specified')}\n"
                response += f"📅 **Contract Expiry:** {venue_data.get('expiry_date', 'Not specified')}\n"
                response += f"🏨 **Group:** {venue_data.get('group', 'Not specified')}\n"
            
            elif 'contract' in query_type.lower() or 'renewal' in query_type.lower() or 'expire' in query_type.lower():
                # Show contract information
                expiry = venue_data.get('expiry_date', 'Not specified')
                response += f"📅 **Contract Expiry Date:** {expiry}\n"
                response += f"📝 **Commencement Date:** {venue_data.get('commencement_date_', 'Not specified')}\n"
                response += f"🏨 **Group:** {venue_data.get('group', 'Not specified')}\n"
                response += f"📧 **Contact:** {venue_data.get('client_contact', 'Not specified')}\n"
                
                # Add renewal reminder if date is available
                if expiry and expiry != 'Not specified':
                    response += f"\n💡 Your contract expires on {expiry}. Please contact your account manager for renewal options."
            
            elif 'zone' in query_type.lower():
                # Show zone configuration from sheets
                response += f"**Zone Configuration:**\n"
                response += f"🎵 **Number of Zones:** {venue_data.get('no_of_zones', 'Not specified')}\n"
                response += f"🎮 **Platform:** {venue_data.get('platform', 'Not specified')}\n"
                response += f"📍 **Outlet:** {venue_data.get('outlet_name', 'Not specified')}\n"
            
            else:
                # Show all available data
                for key, value in venue_data.items():
                    if value and key not in ['id', 'sheet_id', 'index']:
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
        """Extract property/hotel name from message using Gemini"""
        
        prompt = f"""Extract the PROPERTY/HOTEL name from this message.
Return ONLY the property/hotel name, nothing else.
If no property is mentioned, return NONE.

Important: Look for PROPERTY names (hotels/establishments), NOT zone names.
- Properties: Hilton Pattaya, Marriott Bangkok, etc.
- Zones (ignore these): Lobby, Restaurant, Pool, Edge Bar, etc.

Examples:
"I am from Hilton Pattaya" -> Hilton Pattaya
"Calling from Millennium Hilton Bangkok" -> Millennium Hilton Bangkok
"The Edge Bar music stopped" -> NONE (Edge Bar is a zone, not a property)
"Our lobby music is offline" -> NONE (Lobby is a zone, not a property)
"We're at Centara Grand and the pool music stopped" -> Centara Grand

Message: {message}

Property name:"""
        
        try:
            response = self.model.generate_content(prompt)
            venue = response.text.strip()
            if venue and venue != 'NONE':
                return venue
        except:
            pass
        
        return None
    
    def _handle_volume_control(self, message: str, zone_name: str, venue: Dict) -> str:
        """Handle volume control requests for a zone"""
        try:
            # Find the zone
            zones = self.soundtrack.find_venue_zones(venue.get('name'))
            matching_zone = None
            
            if zones:
                zone_name_lower = zone_name.lower()
                matching_zone = next(
                    (z for z in zones if z.get('name', '').lower() == zone_name_lower),
                    None
                )
            
            if not matching_zone:
                return f"I couldn't find a zone called '{zone_name}' at your property. Which zone did you mean?"
            
            zone_id = matching_zone.get('id')
            
            # Parse volume level from message
            message_lower = message.lower()
            volume = None
            
            # Check for specific volume levels
            if any(word in message_lower for word in ['down', 'lower', 'quieter', 'softer']):
                # Decrease by 20%
                current_status = self.soundtrack.get_zone_status(zone_id)
                if current_status and 'volume' in current_status:
                    current_vol = current_status.get('volume', 50)
                    volume = max(10, current_vol - 20)  # Decrease by 20%, minimum 10
                else:
                    volume = 30  # Default lower volume
                    
            elif any(word in message_lower for word in ['up', 'louder', 'higher']):
                # Increase by 20%
                current_status = self.soundtrack.get_zone_status(zone_id)
                if current_status and 'volume' in current_status:
                    current_vol = current_status.get('volume', 50)
                    volume = min(90, current_vol + 20)  # Increase by 20%, max 90
                else:
                    volume = 70  # Default higher volume
                    
            else:
                # Try to extract a number from the message
                import re
                numbers = re.findall(r'\b(\d{1,3})\b', message)
                if numbers:
                    vol = int(numbers[0])
                    if 0 <= vol <= 100:
                        volume = vol
            
            if volume is None:
                return f"What volume level would you like for {zone_name}? You can say 'turn it down', 'turn it up', or give me a number from 0-100."
            
            # Set the volume
            success = self.soundtrack.set_volume(zone_id, volume)
            
            if success:
                return f"Done! I've adjusted {zone_name}'s volume to {volume}%. Let me know if you need any other adjustments."
            else:
                return f"Hmm, I'm having trouble adjusting the volume for {zone_name} right now. You might need to adjust it manually in the Soundtrack dashboard, or I can escalate this to our tech team."
                
        except Exception as e:
            logger.error(f"Error handling volume control: {e}")
            return "I'm having trouble with the volume control right now. You can adjust it manually in the Soundtrack dashboard, or I can escalate this to our tech team."
    
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
                return f"Zone '{zone_name}' is currently offline. Let me know if you need help getting it back online!"
            
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
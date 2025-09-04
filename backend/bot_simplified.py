"""
Simplified Gemini bot - uses only venue_data.md and Soundtrack API
Email access is conditional (only when explicitly mentioned)
"""

import os
import logging
from typing import Dict, Any, Optional
import google.generativeai as genai
from soundtrack_api import soundtrack_api
from venue_identifier import conversation_context
from venue_data_reader import get_all_venues, find_venue, get_venue_pricing

# Set up logging
logger = logging.getLogger(__name__)

class SimplifiedBot:
    """Simplified AI bot using only essential data sources"""
    
    def __init__(self):
        """Initialize bot with Gemini and core data sources"""
        # Configure Gemini
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        genai.configure(api_key=api_key)
        
        # Use gemini-2.5-flash for better performance
        model_name = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
        self.model = genai.GenerativeModel(model_name)
        
        # Core data sources only
        self.soundtrack = soundtrack_api
        self.venues = get_all_venues()
        
        # Optional email (lazy loaded)
        self.email_searcher = None
        
        logger.info(f"Simplified bot initialized with {len(self.venues)} venues")
    
    def _load_email_if_needed(self, message: str) -> bool:
        """Only load email integration if user mentions email"""
        email_keywords = ['email', 'sent you', 'wrote to you', 'mailed', 'gmail', 'message you']
        
        if any(keyword in message.lower() for keyword in email_keywords):
            if not self.email_searcher:
                try:
                    from smart_email_search import init_smart_search
                    self.email_searcher = init_smart_search()
                    logger.info("Email integration loaded on-demand")
                    return True
                except Exception as e:
                    logger.warning(f"Could not load email integration: {e}")
                    return False
            return True
        return False
    
    def process_message(self, message: str, user_phone: str, user_name: str = None, platform: str = "WhatsApp") -> str:
        """Process message using only essential data sources"""
        
        # Extract venue if mentioned
        venue_name = self._extract_venue_name(message)
        venue_data = None
        
        if venue_name:
            venue_data = find_venue(venue_name)
            if venue_data:
                conversation_context.update_context(user_phone, venue={'name': venue_data['property_name']})
                logger.info(f"Venue identified: {venue_data['property_name']}")
        
        # Get user context
        context = conversation_context.get_context(user_phone)
        current_venue = context.get('venue')
        
        message_lower = message.lower()
        
        # Handle pricing queries
        if any(word in message_lower for word in ['price', 'pricing', 'cost', 'rate', 'fee', 'charge', 'annual', 'monthly']):
            if venue_data or current_venue:
                venue_to_check = venue_data['property_name'] if venue_data else current_venue.get('name')
                pricing = get_venue_pricing(venue_to_check)
                
                if pricing:
                    return self._format_pricing_response(pricing)
                else:
                    return f"I couldn't find pricing information for {venue_to_check}. Let me connect you with our team for accurate details."
            else:
                return "Which property would you like pricing information for?"
        
        # Handle zone queries
        if any(phrase in message_lower for phrase in ['zone', 'music area', 'location']):
            if venue_data or current_venue:
                venue_to_check = venue_data['property_name'] if venue_data else current_venue.get('name')
                
                # Get from local data
                local_venue = find_venue(venue_to_check)
                if local_venue and local_venue.get('zone_names'):
                    zones = [z.strip() for z in local_venue['zone_names'].split(',')]
                    return f"{venue_to_check} has {len(zones)} zones: {', '.join(zones)}"
                
                # Try Soundtrack API
                zones = self.soundtrack.find_venue_zones(venue_to_check)
                if zones:
                    zone_names = [z.get('name', 'Unknown') for z in zones]
                    return f"{venue_to_check} has {len(zones)} zones: {', '.join(zone_names)}"
                
                return f"I couldn't find zone information for {venue_to_check}."
        
        # Check if email is mentioned - only load if needed
        if self._load_email_if_needed(message):
            return self._handle_email_query(message, user_name)
        
        # Default to Gemini for general conversation
        return self._generate_ai_response(message, venue_data, user_name)
    
    def _extract_venue_name(self, message: str) -> Optional[str]:
        """Extract venue name from message"""
        message_lower = message.lower()
        
        for venue in self.venues:
            venue_name = venue.get('property_name', '').lower()
            if venue_name in message_lower:
                return venue['property_name']
            
            # Check partial matches
            venue_words = venue_name.split()
            if any(word in message_lower for word in venue_words if len(word) > 3):
                return venue['property_name']
        
        return None
    
    def _format_pricing_response(self, pricing: Dict) -> str:
        """Format pricing information naturally"""
        property_name = pricing.get('property_name')
        zones = pricing.get('zone_count', 0)
        price_per = pricing.get('annual_price_per_zone', 'N/A')
        total = pricing.get('total_annual_price', 'N/A')
        contract_end = pricing.get('contract_end', 'N/A')
        
        response = f"Here's the pricing for {property_name}:\n\n"
        response += f"• {zones} music zones\n"
        response += f"• {price_per} per zone annually\n"
        response += f"• Total: {total} per year\n"
        
        if contract_end != 'N/A':
            response += f"• Current contract ends: {contract_end}\n"
        
        return response
    
    def _handle_email_query(self, message: str, user_name: str) -> str:
        """Handle email-related queries"""
        if not self.email_searcher:
            return "I'm having trouble accessing emails right now. Could you tell me more about what you sent?"
        
        try:
            # Search for recent emails from this user
            results = self.email_searcher.search_emails(
                query=f"from:{user_name}" if user_name else "recent emails",
                max_results=5
            )
            
            if results:
                return f"I found {len(results)} recent emails. The most recent was about: {results[0].get('subject', 'No subject')}. How can I help with that?"
            else:
                return "I couldn't find any recent emails from you. Could you tell me more about what you sent?"
                
        except Exception as e:
            logger.error(f"Email search failed: {e}")
            return "I'm having trouble accessing emails right now. Could you describe what you need help with?"
    
    def _generate_ai_response(self, message: str, venue_data: Optional[Dict], user_name: str) -> str:
        """Generate AI response using Gemini"""
        try:
            # Build context
            context = f"""You are a helpful assistant for BMA Social, a B2B music service provider.
            
            User: {user_name or 'Customer'}
            Message: {message}
            """
            
            if venue_data:
                context += f"\nVenue Information: {venue_data}"
            
            context += """
            
            Guidelines:
            - Be friendly and professional
            - Focus on music service support
            - Don't make up information
            - If unsure, offer to connect them with the team
            """
            
            response = self.model.generate_content(context)
            return response.text
            
        except Exception as e:
            logger.error(f"AI generation failed: {e}")
            return "I'm here to help! Could you tell me more about what you need?"


# Create singleton instance
simplified_bot = SimplifiedBot()

def process_message(message: str, user_phone: str, user_name: str = None, platform: str = "WhatsApp") -> str:
    """Process message with simplified bot"""
    return simplified_bot.process_message(message, user_phone, user_name, platform)
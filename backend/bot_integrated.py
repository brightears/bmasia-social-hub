"""
Fully integrated bot with venue identification, email verification, and smart responses
This is the production-ready version combining all features
"""

import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Import all our modules
from bot_simple import SimpleBot
from venue_identifier import venue_identifier, conversation_context
# Use test email verifier with admin bypass for BMA staff
try:
    from email_verification_test import test_email_verifier as email_verifier
    logger.info("Using test email verifier with admin bypass")
except ImportError:
    from email_verification import email_verifier
    logger.info("Using standard email verifier")
from terminology_handler import terminology
from smart_authentication import smart_auth, trust_manager

# Try imports for optional features
try:
    from google_sheets_client import sheets_client
    SHEETS_AVAILABLE = True
except:
    SHEETS_AVAILABLE = False
    sheets_client = None

try:
    from database import db_manager
    DB_AVAILABLE = True
except:
    DB_AVAILABLE = False
    db_manager = None

try:
    from email_integration import email_manager
    EMAIL_AVAILABLE = True
except:
    EMAIL_AVAILABLE = False
    email_manager = None

class IntegratedBot(SimpleBot):
    """Production-ready bot with all features integrated"""
    
    def __init__(self):
        super().__init__()
        self.venues_list = []
        self.load_venues()
        logger.info("Integrated bot initialized with all features")
    
    def load_venues(self):
        """Load venues from available sources"""
        # Priority: Google Sheets > Database > Sample
        if SHEETS_AVAILABLE and sheets_client:
            self.venues_list = sheets_client.get_all_venues()
            logger.info(f"Loaded {len(self.venues_list)} venues from Google Sheets")
        elif DB_AVAILABLE and db_manager:
            with db_manager.get_cursor() as cursor:
                if cursor:
                    cursor.execute("SELECT * FROM venues WHERE active = true")
                    venues = cursor.fetchall()
                    self.venues_list = venues
                    logger.info(f"Loaded {len(self.venues_list)} venues from database")
        
        if not self.venues_list:
            self.venues_list = self.get_sample_venues()
            logger.info(f"Using {len(self.venues_list)} sample venues")
    
    def get_sample_venues(self):
        """Sample venues for testing"""
        return [
            {
                "name": "Hilton Bangkok",
                "location": "Bangkok, Thailand",
                "metadata": {
                    "venue_type": "Hotel",
                    "zone_count": 5,
                    "has_soundtrack": True
                }
            },
            {
                "name": "Grand Plaza Hotel",
                "location": "Bangkok, Thailand",
                "metadata": {
                    "venue_type": "Hotel",
                    "zone_count": 8,
                    "has_soundtrack": False
                }
            }
        ]
    
    def process_message(self, user_message: str, user_phone: str, user_name: str = None) -> str:
        """Main message processing with all features"""
        
        # Get conversation context
        context = conversation_context.get_context(user_phone)
        conversation_context.add_message(user_phone, "user", user_message)
        
        # Get current state
        state = context.get('state', 'initial')
        venue = context.get('venue')
        
        # Route to appropriate handler
        if state == 'initial':
            return self._handle_initial(user_message, user_phone, user_name)
        
        elif state == 'awaiting_venue':
            return self._handle_venue_identification(user_message, user_phone)
        
        elif state == 'venue_multiple_matches':
            return self._handle_venue_selection(user_message, user_phone)
        
        elif state == 'awaiting_email':
            return self._handle_email_verification_request(user_message, user_phone)
        
        elif state == 'awaiting_verification_code':
            return self._handle_verification_code(user_message, user_phone)
        
        elif state == 'authenticated':
            return self._handle_authenticated_request(user_message, user_phone)
        
        else:
            return self._handle_general_help(user_message, user_phone)
    
    def _handle_initial(self, message: str, user_phone: str, user_name: str) -> str:
        """Handle initial contact"""
        
        # Check if this is a general help request (no auth needed)
        if email_verifier.can_help_without_verification(message):
            # Provide general help without venue identification
            return super().generate_response(message, user_name or "User")
        
        # Venue-specific request - need identification
        conversation_context.update_context(user_phone, 
                                           state='awaiting_venue',
                                           initial_issue=message)
        
        return "Hi! I can help with that. First, what's the name of your venue or hotel?"
    
    def _handle_venue_identification(self, message: str, user_phone: str) -> str:
        """Handle venue identification with terminology understanding"""
        
        # Use venue identifier with fuzzy matching
        venue, response, state = venue_identifier.identify_venue(
            message, user_phone, self.venues_list
        )
        
        if venue:
            # Venue identified - check authentication
            conversation_context.update_context(user_phone, venue=venue)
            
            # Check if already authenticated for this venue
            is_auth, auth_message, auth_type = smart_auth.check_authentication(user_phone, venue)
            
            if is_auth:
                # Already authenticated
                conversation_context.update_context(user_phone, state='authenticated')
                context = conversation_context.get_context(user_phone)
                initial_issue = context.get('initial_issue', '')
                
                if initial_issue:
                    # Handle their original request
                    return self._handle_authenticated_request(initial_issue, user_phone)
                else:
                    return auth_message + " How can I help you today?"
            
            else:
                # Need authentication
                conversation_context.update_context(user_phone, state='awaiting_email')
                return f"I found {venue['name']}. To help with venue-specific requests, I need to verify your access. What's your company email address?"
        
        elif state == 'venue_multiple_matches':
            conversation_context.update_context(user_phone, state=state)
            return response
        
        else:
            return response
    
    def _handle_email_verification_request(self, message: str, user_phone: str) -> str:
        """Handle email verification"""
        
        context = conversation_context.get_context(user_phone)
        venue = context.get('venue', {})
        
        # Validate email domain
        email = message.strip().lower()
        is_valid, validation_msg = email_verifier.validate_email_domain(email, venue.get('name', ''))
        
        if not is_valid:
            return validation_msg
        
        # Generate and send verification code
        code = email_verifier.generate_verification_code(user_phone, email)
        
        if EMAIL_AVAILABLE and email_manager:
            success = email_manager.send_verification_code(email, code, venue.get('name', 'your venue'))
            if success:
                conversation_context.update_context(user_phone, 
                                                   state='awaiting_verification_code',
                                                   verification_email=email)
                return f"✅ I've sent a 6-digit verification code to {email}. Please type the code here when you receive it."
            else:
                return "I had trouble sending the email. Please check the email address and try again."
        else:
            # Testing mode - show code in response
            conversation_context.update_context(user_phone, 
                                               state='awaiting_verification_code',
                                               verification_email=email)
            return f"[TEST MODE] Your verification code is: {code}\nPlease type this code to verify."
    
    def _handle_verification_code(self, message: str, user_phone: str) -> str:
        """Handle verification code entry"""
        
        context = conversation_context.get_context(user_phone)
        venue = context.get('venue', {})
        
        # Verify the code
        is_valid, verify_msg = email_verifier.verify_code(
            user_phone, 
            message.strip(), 
            venue.get('name', '')
        )
        
        if is_valid:
            # Mark as authenticated
            conversation_context.update_context(user_phone, state='authenticated')
            
            # Log successful authentication if sheets available
            if SHEETS_AVAILABLE and sheets_client:
                sheets_client.log_venue_access(venue.get('name', ''), {
                    'user_phone': user_phone,
                    'user_name': context.get('user_name', ''),
                    'auth_method': 'email',
                    'auth_result': 'success'
                })
            
            # Check if there was an initial issue
            initial_issue = context.get('initial_issue', '')
            if initial_issue:
                return verify_msg + f"\n\nNow, about your request: '{initial_issue}'\n" + self._handle_authenticated_request(initial_issue, user_phone)
            else:
                return verify_msg
        else:
            return verify_msg
    
    def _handle_authenticated_request(self, message: str, user_phone: str) -> str:
        """Handle requests from authenticated users"""
        
        context = conversation_context.get_context(user_phone)
        venue = context.get('venue', {})
        
        # Use terminology handler to understand the request
        term_context = terminology.identify_context(message, venue)
        
        # Check if clarification needed about zones/areas
        if term_context.get('clarification_needed'):
            return term_context.get('suggested_question')
        
        # Generate context-aware response
        enhanced_prompt = f"""
        Venue: {venue.get('name', 'Unknown')}
        Location: {venue.get('location', 'Unknown')}
        Type: {venue.get('metadata', {}).get('venue_type', 'Unknown')}
        Has Soundtrack: {venue.get('metadata', {}).get('has_soundtrack', False)}
        
        Request: {message}
        Specific Zone: {term_context.get('specific_zone', 'Not specified')}
        All Zones: {term_context.get('all_zones', False)}
        
        Provide specific, actionable help for this request.
        """
        
        response = super().generate_response(enhanced_prompt, context.get('user_name', 'User'))
        
        # Log the interaction if sheets available
        if SHEETS_AVAILABLE and sheets_client:
            venue_sheet_id = venue.get('metadata', {}).get('sheet_id')
            if venue_sheet_id:
                sheets_client.write_conversation_log(venue_sheet_id, {
                    'user_name': context.get('user_name', ''),
                    'user_role': context.get('user_role', ''),
                    'channel': 'whatsapp',
                    'issue': message,
                    'resolution': response
                })
        
        return response
    
    def _handle_venue_selection(self, message: str, user_phone: str) -> str:
        """Handle venue selection from multiple options"""
        venue, response = venue_identifier.handle_venue_selection(message, user_phone)
        
        if venue:
            conversation_context.update_context(user_phone, venue=venue)
            # Continue to authentication check
            return self._handle_venue_identification(venue['name'], user_phone)
        else:
            return response
    
    def _handle_general_help(self, message: str, user_phone: str) -> str:
        """Handle general help requests that don't need authentication"""
        
        # Topics that don't need auth
        general_topics = [
            'price', 'pricing', 'cost',
            'how to', 'what is', 'explain',
            'help', 'support', 'contact',
            'features', 'benefits'
        ]
        
        message_lower = message.lower()
        
        if any(topic in message_lower for topic in general_topics):
            return super().generate_response(message, "User")
        
        # Might be venue-specific, start identification flow
        conversation_context.update_context(user_phone, state='awaiting_venue')
        return "I can help with that! What's the name of your venue?"


# Create global instance
integrated_bot = IntegratedBot()
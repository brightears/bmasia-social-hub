"""
Enhanced bot with venue identification and context awareness
Uses Google Sheets for venue data and conversation history
"""

import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

# Import our modules
from bot_simple import SimpleBot
from venue_identifier import venue_identifier, conversation_context

# Try to import Google Sheets client
try:
    from google_sheets_client import sheets_client
    SHEETS_AVAILABLE = True
except:
    SHEETS_AVAILABLE = False
    sheets_client = None
    logging.warning("Google Sheets not available - using local venue data")

# Try to import database
try:
    from database import db_manager
    DB_AVAILABLE = True
except:
    DB_AVAILABLE = False
    db_manager = None

logger = logging.getLogger(__name__)

class VenueAwareBot(SimpleBot):
    """Bot that identifies venues and provides context-aware responses"""
    
    def __init__(self):
        super().__init__()
        self.venues_list = []
        self.load_venues()
    
    def load_venues(self):
        """Load venues from available sources"""
        # Try Google Sheets first
        if SHEETS_AVAILABLE and sheets_client:
            self.venues_list = sheets_client.get_all_venues()
            logger.info(f"Loaded {len(self.venues_list)} venues from Google Sheets")
        
        # Fallback to database
        elif DB_AVAILABLE and db_manager:
            with db_manager.get_cursor() as cursor:
                if cursor:
                    cursor.execute("SELECT * FROM venues WHERE active = true")
                    venues = cursor.fetchall()
                    self.venues_list = venues
                    logger.info(f"Loaded {len(self.venues_list)} venues from database")
        
        # Fallback to hardcoded sample venues
        if not self.venues_list:
            self.venues_list = self.get_sample_venues()
            logger.info(f"Using {len(self.venues_list)} sample venues")
    
    def get_sample_venues(self) -> List[Dict]:
        """Get sample venues for testing"""
        return [
            {
                "name": "Grand Plaza Hotel Bangkok",
                "phone": "+66812345678",
                "location": "Bangkok, Thailand",
                "has_soundtrack": "TRUE",
                "soundtrack_id": "SYB_GRAND_PLAZA_BKK"
            },
            {
                "name": "Marina Bay Resort Singapore",
                "phone": "+6591234567",
                "location": "Singapore",
                "has_soundtrack": "FALSE"
            },
            {
                "name": "Zen Garden Restaurant",
                "phone": "+60123456789",
                "location": "Kuala Lumpur, Malaysia",
                "has_soundtrack": "TRUE",
                "soundtrack_id": "SYB_ZEN_GARDEN_KL"
            }
        ]
    
    def process_message(self, user_message: str, user_phone: str, user_name: str = None) -> str:
        """Process message with venue identification"""
        
        # Get conversation context
        context = conversation_context.get_context(user_phone)
        
        # Add message to history
        conversation_context.add_message(user_phone, "user", user_message)
        
        # Check conversation state
        venue = context.get('venue')
        state = context.get('state', 'initial')
        
        # State machine for conversation flow
        if state == 'initial':
            # Greeting and ask for venue
            response = self._handle_initial_greeting(user_message, user_phone, user_name)
        
        elif state == 'awaiting_venue':
            # Try to identify venue
            response = self._handle_venue_identification(user_message, user_phone)
        
        elif state == 'venue_multiple_matches':
            # Handle venue selection from options
            response = self._handle_venue_selection(user_message, user_phone)
        
        elif state == 'venue_confirmed':
            # Ask for person details
            response = self._handle_person_identification(user_message, user_phone)
        
        elif state == 'awaiting_issue':
            # Get the issue description
            response = self._handle_issue_description(user_message, user_phone)
        
        elif state == 'providing_support':
            # Provide context-aware support
            response = self._handle_support_interaction(user_message, user_phone)
        
        else:
            # Default handler
            response = self._handle_general_query(user_message, user_phone)
        
        # Add response to history
        conversation_context.add_message(user_phone, "assistant", response)
        
        return response
    
    def _handle_initial_greeting(self, message: str, user_phone: str, user_name: str) -> str:
        """Handle initial greeting"""
        greetings = ['hi', 'hello', 'help', 'hey', 'good']
        
        if any(greet in message.lower() for greet in greetings):
            conversation_context.update_context(user_phone, 
                                               state='awaiting_venue',
                                               user_name=user_name)
            return "Hi! I'm here to help with your music system. What's the name of your venue?"
        else:
            # User might have directly stated their issue
            conversation_context.update_context(user_phone, 
                                               state='awaiting_venue',
                                               initial_issue=message)
            return "I can help with that! First, could you tell me the name of your venue?"
    
    def _handle_venue_identification(self, message: str, user_phone: str) -> str:
        """Handle venue identification"""
        venue, response, state = venue_identifier.identify_venue(
            message, user_phone, self.venues_list
        )
        
        if venue:
            conversation_context.update_context(user_phone,
                                               venue=venue,
                                               state='venue_confirmed')
            # Check if we have an initial issue
            context = conversation_context.get_context(user_phone)
            if context.get('initial_issue'):
                return f"Great! I found {venue['name']}. Now, who am I speaking with?"
            else:
                return f"Perfect! I've identified your venue as {venue['name']}. May I have your name?"
        
        elif state == 'venue_multiple_matches':
            conversation_context.update_context(user_phone, state=state)
            return response
        
        else:
            conversation_context.update_context(user_phone, state='awaiting_venue')
            return response
    
    def _handle_venue_selection(self, message: str, user_phone: str) -> str:
        """Handle venue selection from multiple options"""
        venue, response = venue_identifier.handle_venue_selection(message, user_phone)
        
        if venue:
            conversation_context.update_context(user_phone,
                                               venue=venue,
                                               state='venue_confirmed')
            return response + " May I have your name?"
        else:
            return response
    
    def _handle_person_identification(self, message: str, user_phone: str) -> str:
        """Handle person identification"""
        conversation_context.update_context(user_phone,
                                           person_name=message,
                                           state='awaiting_role')
        return f"Thanks {message}! What's your position at the venue?"
    
    def _handle_issue_description(self, message: str, user_phone: str) -> str:
        """Handle issue description and provide solution"""
        context = conversation_context.get_context(user_phone)
        venue = context.get('venue', {})
        
        # Store the issue
        conversation_context.update_context(user_phone,
                                           issue=message,
                                           state='providing_support')
        
        # Generate context-aware response
        response = self._generate_solution(message, venue, context)
        
        # Log to Google Sheets if available
        if SHEETS_AVAILABLE and sheets_client:
            venue_sheet_id = venue.get('metadata', {}).get('sheet_id')
            if venue_sheet_id:
                sheets_client.write_conversation_log(venue_sheet_id, {
                    'user_name': context.get('person_name'),
                    'user_role': context.get('person_role'),
                    'channel': 'whatsapp',
                    'issue': message,
                    'resolution': response,
                    'satisfaction': 'pending'
                })
        
        return response
    
    def _generate_solution(self, issue: str, venue: Dict, context: Dict) -> str:
        """Generate context-aware solution"""
        has_soundtrack = venue.get('has_soundtrack') == 'TRUE' or venue.get('metadata', {}).get('has_soundtrack')
        venue_name = venue.get('name', 'your venue')
        
        # Use AI to generate response with context
        enhanced_prompt = f"""
        Venue: {venue_name}
        Location: {venue.get('location', 'Unknown')}
        Has Soundtrack System: {has_soundtrack}
        Person: {context.get('person_name', 'User')} ({context.get('person_role', 'Staff')})
        Issue: {issue}
        
        Provide a specific, helpful solution. If they have Soundtrack, include system-specific steps.
        """
        
        # Use parent class AI generation
        return super().generate_response(enhanced_prompt, context.get('person_name', 'User'))
    
    def _handle_support_interaction(self, message: str, user_phone: str) -> str:
        """Handle ongoing support interaction"""
        context = conversation_context.get_context(user_phone)
        venue = context.get('venue', {})
        
        # Check if issue is resolved
        if 'fixed' in message.lower() or 'working' in message.lower() or 'thanks' in message.lower():
            conversation_context.update_context(user_phone, state='resolved')
            return "Great! I'm glad I could help. Is there anything else you need assistance with?"
        
        # Continue providing support
        return self._generate_solution(message, venue, context)
    
    def _handle_general_query(self, message: str, user_phone: str) -> str:
        """Handle general queries without venue context"""
        # Try to determine if they need venue-specific help
        music_keywords = ['music', 'volume', 'playlist', 'zone', 'speaker', 'sound']
        
        if any(keyword in message.lower() for keyword in music_keywords):
            conversation_context.update_context(user_phone, 
                                               state='awaiting_venue',
                                               initial_issue=message)
            return "I can help with that! First, what's the name of your venue?"
        
        # Use parent class for general response
        return super().generate_response(message, "User")


# Create enhanced bot instance
venue_bot = VenueAwareBot()
"""
Venue Identification Service
Handles natural language venue identification through conversational flow
"""

import logging
import re
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from enum import Enum
import hashlib
import json

logger = logging.getLogger(__name__)

class IdentificationState(Enum):
    """States for venue identification flow"""
    INITIAL = "initial"
    ASKING_VENUE_NAME = "asking_venue_name"
    CONFIRMING_VENUE = "confirming_venue"
    ASKING_PERSON_NAME = "asking_person_name"
    ASKING_POSITION = "asking_position"
    ASKING_ISSUE = "asking_issue"
    IDENTIFIED = "identified"
    MULTIPLE_MATCHES = "multiple_matches"
    NOT_FOUND = "not_found"

class VenueIdentifier:
    """
    Manages natural conversation flow for venue identification
    Prioritizes venue NAME over phone number for identification
    """
    
    def __init__(self, data_aggregator=None, cache_manager=None):
        self.data_aggregator = data_aggregator
        self.cache = cache_manager
        self.conversation_states = {}  # Track state per conversation
        
        # Fuzzy matching thresholds
        self.exact_match_threshold = 1.0
        self.high_confidence_threshold = 0.85
        self.low_confidence_threshold = 0.60
        
        # Common venue name variations
        self.venue_patterns = {
            'hotel': ['hotel', 'resort', 'inn', 'lodge', 'suites'],
            'restaurant': ['restaurant', 'cafe', 'bistro', 'kitchen', 'grill', 'dining'],
            'retail': ['shop', 'store', 'boutique', 'market', 'mall'],
            'spa': ['spa', 'wellness', 'massage', 'salon'],
            'bar': ['bar', 'pub', 'lounge', 'club', 'tavern']
        }
    
    def get_conversation_state(self, conversation_id: str) -> Dict[str, Any]:
        """Get or create conversation state"""
        if conversation_id not in self.conversation_states:
            self.conversation_states[conversation_id] = {
                'state': IdentificationState.INITIAL,
                'venue_name': None,
                'venue_id': None,
                'person_name': None,
                'position': None,
                'issue': None,
                'confidence': 0.0,
                'possible_matches': [],
                'attempts': 0,
                'started_at': datetime.utcnow().isoformat()
            }
        return self.conversation_states[conversation_id]
    
    def process_identification(self, 
                              conversation_id: str,
                              user_message: str,
                              phone_number: Optional[str] = None) -> Tuple[Dict[str, Any], str]:
        """
        Process venue identification through conversation
        Returns: (identification_data, bot_response)
        """
        state_data = self.get_conversation_state(conversation_id)
        current_state = state_data['state']
        
        # Clean and analyze user message
        message_lower = user_message.lower().strip()
        
        # Check for restart keywords
        if any(word in message_lower for word in ['start over', 'restart', 'reset']):
            self.conversation_states[conversation_id] = {
                'state': IdentificationState.INITIAL,
                'venue_name': None,
                'venue_id': None,
                'person_name': None,
                'position': None,
                'issue': None,
                'confidence': 0.0,
                'possible_matches': [],
                'attempts': 0,
                'started_at': datetime.utcnow().isoformat()
            }
            return self.get_conversation_state(conversation_id), "Let's start fresh. What's the name of your venue?"
        
        # State machine for identification flow
        if current_state == IdentificationState.INITIAL:
            return self._handle_initial_state(conversation_id, user_message, phone_number)
        
        elif current_state == IdentificationState.ASKING_VENUE_NAME:
            return self._handle_venue_name_state(conversation_id, user_message)
        
        elif current_state == IdentificationState.CONFIRMING_VENUE:
            return self._handle_venue_confirmation(conversation_id, user_message)
        
        elif current_state == IdentificationState.MULTIPLE_MATCHES:
            return self._handle_multiple_matches(conversation_id, user_message)
        
        elif current_state == IdentificationState.ASKING_PERSON_NAME:
            return self._handle_person_name(conversation_id, user_message)
        
        elif current_state == IdentificationState.ASKING_POSITION:
            return self._handle_position(conversation_id, user_message)
        
        elif current_state == IdentificationState.ASKING_ISSUE:
            return self._handle_issue(conversation_id, user_message)
        
        elif current_state == IdentificationState.IDENTIFIED:
            return self._handle_identified_state(conversation_id, user_message)
        
        else:
            # Fallback
            state_data['state'] = IdentificationState.ASKING_VENUE_NAME
            return state_data, "I need to identify your venue first. What's the name of your venue?"
    
    def _handle_initial_state(self, conversation_id: str, user_message: str, phone_number: Optional[str]) -> Tuple[Dict, str]:
        """Handle initial contact"""
        state_data = self.get_conversation_state(conversation_id)
        
        # Extract potential venue name from message
        venue_hint = self._extract_venue_name(user_message)
        
        if venue_hint:
            # User provided venue name in initial message
            state_data['venue_name'] = venue_hint
            matches = self._search_venue(venue_hint, phone_number)
            
            if matches and len(matches) == 1 and matches[0]['confidence'] >= self.high_confidence_threshold:
                # High confidence single match
                venue = matches[0]
                state_data['venue_id'] = venue['id']
                state_data['venue_name'] = venue['name']
                state_data['confidence'] = venue['confidence']
                state_data['state'] = IdentificationState.ASKING_PERSON_NAME
                
                return state_data, f"Great! I found your venue: {venue['name']}. May I have your name, please?"
            
            elif matches and len(matches) > 1:
                # Multiple possible matches
                state_data['possible_matches'] = matches[:5]  # Limit to top 5
                state_data['state'] = IdentificationState.MULTIPLE_MATCHES
                
                response = "I found several venues with similar names. Which one is yours?\n\n"
                for i, match in enumerate(matches[:5], 1):
                    response += f"{i}. {match['name']}"
                    if match.get('location'):
                        response += f" - {match['location']}"
                    response += "\n"
                response += "\nPlease reply with the number or full name of your venue."
                
                return state_data, response
            
            else:
                # No good matches
                state_data['state'] = IdentificationState.ASKING_VENUE_NAME
                return state_data, f"I couldn't find a venue named '{venue_hint}'. Could you please provide the exact name of your venue as it appears in our system?"
        
        else:
            # No venue name detected, ask for it
            state_data['state'] = IdentificationState.ASKING_VENUE_NAME
            
            greeting = "Hello! I'm the BMA Social support assistant. "
            greeting += "To help you effectively, I need to identify your venue first.\n\n"
            greeting += "What's the name of your venue?"
            
            return state_data, greeting
    
    def _handle_venue_name_state(self, conversation_id: str, user_message: str) -> Tuple[Dict, str]:
        """Handle venue name collection"""
        state_data = self.get_conversation_state(conversation_id)
        
        # Search for venue
        matches = self._search_venue(user_message, None)
        
        if matches and len(matches) == 1 and matches[0]['confidence'] >= self.high_confidence_threshold:
            # Single high-confidence match
            venue = matches[0]
            state_data['venue_id'] = venue['id']
            state_data['venue_name'] = venue['name']
            state_data['confidence'] = venue['confidence']
            state_data['state'] = IdentificationState.CONFIRMING_VENUE
            
            return state_data, f"Is this your venue: {venue['name']} located at {venue.get('location', 'N/A')}? (Yes/No)"
        
        elif matches and len(matches) > 0:
            # Multiple or low-confidence matches
            state_data['possible_matches'] = matches[:5]
            state_data['state'] = IdentificationState.MULTIPLE_MATCHES
            
            if len(matches) == 1:
                # Single low-confidence match
                venue = matches[0]
                state_data['venue_name'] = venue['name']
                return state_data, f"Did you mean {venue['name']}? (Yes/No)"
            else:
                # Multiple matches
                response = "I found several possible venues. Which one is yours?\n\n"
                for i, match in enumerate(matches[:5], 1):
                    response += f"{i}. {match['name']}"
                    if match.get('location'):
                        response += f" - {match['location']}"
                    response += "\n"
                response += "\n0. None of these\n"
                response += "\nPlease reply with the number."
                
                return state_data, response
        
        else:
            # No matches found
            state_data['attempts'] += 1
            
            if state_data['attempts'] >= 3:
                state_data['state'] = IdentificationState.NOT_FOUND
                return state_data, ("I'm having trouble finding your venue in our system. "
                                   "Please contact support@bmasiamusic.com with your venue details "
                                   "and we'll assist you directly.")
            
            return state_data, ("I couldn't find that venue name in our system. "
                               "Please provide the exact venue name as registered with BMA Social, "
                               "or type 'help' for assistance.")
    
    def _handle_venue_confirmation(self, conversation_id: str, user_message: str) -> Tuple[Dict, str]:
        """Handle venue confirmation"""
        state_data = self.get_conversation_state(conversation_id)
        message_lower = user_message.lower().strip()
        
        if any(word in message_lower for word in ['yes', 'correct', 'right', 'yeah', 'yup', 'confirm']):
            state_data['state'] = IdentificationState.ASKING_PERSON_NAME
            return state_data, "Perfect! Now, may I have your name, please?"
        
        elif any(word in message_lower for word in ['no', 'wrong', 'incorrect', 'nope']):
            state_data['state'] = IdentificationState.ASKING_VENUE_NAME
            state_data['venue_id'] = None
            state_data['venue_name'] = None
            return state_data, "I apologize for the confusion. Could you please provide the correct venue name?"
        
        else:
            return state_data, "Please confirm with 'Yes' or 'No' - is this your venue?"
    
    def _handle_multiple_matches(self, conversation_id: str, user_message: str) -> Tuple[Dict, str]:
        """Handle selection from multiple venue matches"""
        state_data = self.get_conversation_state(conversation_id)
        message_clean = user_message.strip()
        
        # Check if user selected by number
        if message_clean.isdigit():
            selection = int(message_clean)
            
            if selection == 0:
                # None of these
                state_data['state'] = IdentificationState.ASKING_VENUE_NAME
                state_data['possible_matches'] = []
                return state_data, "Please provide the exact name of your venue as it appears in our system."
            
            elif 1 <= selection <= len(state_data['possible_matches']):
                # Valid selection
                venue = state_data['possible_matches'][selection - 1]
                state_data['venue_id'] = venue['id']
                state_data['venue_name'] = venue['name']
                state_data['confidence'] = venue['confidence']
                state_data['state'] = IdentificationState.ASKING_PERSON_NAME
                
                return state_data, f"Great! I've identified your venue as {venue['name']}. May I have your name, please?"
            
            else:
                return state_data, f"Please select a number between 1 and {len(state_data['possible_matches'])}, or 0 for none."
        
        else:
            # Try to match by name
            for venue in state_data['possible_matches']:
                if venue['name'].lower() in message_clean.lower() or message_clean.lower() in venue['name'].lower():
                    state_data['venue_id'] = venue['id']
                    state_data['venue_name'] = venue['name']
                    state_data['confidence'] = venue['confidence']
                    state_data['state'] = IdentificationState.ASKING_PERSON_NAME
                    
                    return state_data, f"Perfect! I've identified your venue as {venue['name']}. May I have your name, please?"
            
            return state_data, "Please select from the list by number (1-5) or type the venue name exactly as shown."
    
    def _handle_person_name(self, conversation_id: str, user_message: str) -> Tuple[Dict, str]:
        """Handle person name collection"""
        state_data = self.get_conversation_state(conversation_id)
        
        # Extract and validate name
        name = self._extract_person_name(user_message)
        
        if name:
            state_data['person_name'] = name
            state_data['state'] = IdentificationState.ASKING_POSITION
            return state_data, f"Thank you, {name}. What's your position at {state_data['venue_name']}?"
        
        else:
            return state_data, "Could you please tell me your name?"
    
    def _handle_position(self, conversation_id: str, user_message: str) -> Tuple[Dict, str]:
        """Handle position/role collection"""
        state_data = self.get_conversation_state(conversation_id)
        
        # Common positions
        position_keywords = {
            'manager': ['manager', 'mgr', 'management'],
            'supervisor': ['supervisor', 'supervise'],
            'staff': ['staff', 'employee', 'worker'],
            'owner': ['owner', 'proprietor'],
            'engineer': ['engineer', 'tech', 'technical', 'it'],
            'front desk': ['front desk', 'reception', 'receptionist'],
            'operations': ['operations', 'ops'],
            'maintenance': ['maintenance', 'facility']
        }
        
        message_lower = user_message.lower().strip()
        position = None
        
        # Match against known positions
        for role, keywords in position_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                position = role.title()
                break
        
        if not position:
            # Use the raw input if no match
            position = user_message.strip().title()
        
        state_data['position'] = position
        state_data['state'] = IdentificationState.ASKING_ISSUE
        
        return state_data, (f"Thank you, {state_data['person_name']}. "
                           f"I have you registered as {position} at {state_data['venue_name']}.\n\n"
                           "How can I help you today? Please describe the issue you're experiencing.")
    
    def _handle_issue(self, conversation_id: str, user_message: str) -> Tuple[Dict, str]:
        """Handle issue description"""
        state_data = self.get_conversation_state(conversation_id)
        
        state_data['issue'] = user_message
        state_data['state'] = IdentificationState.IDENTIFIED
        
        # Create identification summary
        summary = f"✅ Venue Identified:\n"
        summary += f"• Venue: {state_data['venue_name']}\n"
        summary += f"• Contact: {state_data['person_name']} ({state_data['position']})\n"
        summary += f"• Issue: {user_message[:100]}...\n" if len(user_message) > 100 else f"• Issue: {user_message}\n"
        summary += f"\nI'm now checking your venue's status and will help resolve this issue."
        
        # Log successful identification
        logger.info(f"Venue identified: {state_data['venue_name']} (ID: {state_data['venue_id']})")
        
        return state_data, summary
    
    def _handle_identified_state(self, conversation_id: str, user_message: str) -> Tuple[Dict, str]:
        """Handle conversation after venue is identified"""
        state_data = self.get_conversation_state(conversation_id)
        
        # Continue with normal support conversation
        response = f"I'm helping {state_data['person_name']} from {state_data['venue_name']} with their query."
        
        return state_data, response
    
    def _search_venue(self, query: str, phone_number: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for venue by name (primary) and phone (secondary)
        Returns list of matches with confidence scores
        """
        if not self.data_aggregator:
            # Fallback for testing
            return self._mock_venue_search(query)
        
        try:
            # Search venues using data aggregator
            results = self.data_aggregator.search_venues(
                name_query=query,
                phone_number=phone_number
            )
            
            # Sort by confidence score
            results.sort(key=lambda x: x.get('confidence', 0), reverse=True)
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching venues: {e}")
            return []
    
    def _extract_venue_name(self, message: str) -> Optional[str]:
        """Extract potential venue name from message"""
        message_lower = message.lower()
        
        # Look for venue type indicators
        for venue_type, keywords in self.venue_patterns.items():
            for keyword in keywords:
                if keyword in message_lower:
                    # Extract text around the keyword
                    pattern = rf"([\w\s]+\s+{keyword}[\w\s]*|{keyword}\s+[\w\s]+)"
                    match = re.search(pattern, message_lower, re.IGNORECASE)
                    if match:
                        return match.group(0).strip().title()
        
        # Look for "at" or "from" patterns
        patterns = [
            r"(?:at|from)\s+([\w\s]+?)(?:\.|,|$)",
            r"(?:hotel|restaurant|venue|property|location)\s*:?\s*([\w\s]+?)(?:\.|,|$)",
            r"^([\w\s]+?)(?:\s+here|\s+calling|\s+messaging)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message_lower, re.IGNORECASE)
            if match:
                venue_name = match.group(1).strip()
                if len(venue_name) > 3:  # Minimum length check
                    return venue_name.title()
        
        return None
    
    def _extract_person_name(self, message: str) -> Optional[str]:
        """Extract person name from message"""
        message = message.strip()
        
        # Remove common prefixes
        prefixes = ["my name is", "i am", "i'm", "this is", "name:", "call me"]
        message_lower = message.lower()
        
        for prefix in prefixes:
            if message_lower.startswith(prefix):
                name = message[len(prefix):].strip()
                return name.title() if name else None
        
        # If no prefix, check if it looks like a name (2-4 words, starts with capital)
        words = message.split()
        if 1 <= len(words) <= 4:
            if message[0].isupper() or all(word[0].isupper() for word in words if word):
                return message.title()
        
        return None
    
    def _mock_venue_search(self, query: str) -> List[Dict[str, Any]]:
        """Mock venue search for testing"""
        mock_venues = [
            {"id": 1, "name": "Hilton Bangkok", "location": "Bangkok, Thailand", "confidence": 0.9},
            {"id": 2, "name": "Marriott Sukhum", "location": "Bangkok, Thailand", "confidence": 0.85},
            {"id": 3, "name": "The Coffee Club", "location": "Siam Paragon", "confidence": 0.8},
        ]
        
        results = []
        query_lower = query.lower()
        
        for venue in mock_venues:
            if query_lower in venue['name'].lower():
                results.append(venue)
        
        return results
    
    def clear_conversation(self, conversation_id: str):
        """Clear conversation state"""
        if conversation_id in self.conversation_states:
            del self.conversation_states[conversation_id]
    
    def is_identified(self, conversation_id: str) -> bool:
        """Check if venue is identified for this conversation"""
        state_data = self.get_conversation_state(conversation_id)
        return state_data['state'] == IdentificationState.IDENTIFIED and state_data['venue_id'] is not None
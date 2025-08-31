"""
Venue identification through natural conversation
Handles venue name recognition with fuzzy matching and clarification
"""

import os
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import difflib
import re

logger = logging.getLogger(__name__)

class VenueIdentifier:
    """Identify venues through natural conversation"""
    
    def __init__(self):
        self.conversation_state = {}  # Track state per user
        self.venue_cache = {}  # Cache venue data
        
    def identify_venue(self, user_input: str, user_phone: str, 
                       venues_list: List[Dict]) -> Tuple[Optional[Dict], str, str]:
        """
        Identify venue from user input
        Returns: (venue_dict, response_message, state)
        """
        
        # Clean input
        user_input = user_input.strip().lower()
        
        # Direct matching attempts
        exact_match = self._find_exact_match(user_input, venues_list)
        if exact_match:
            return (exact_match, 
                   f"Great! I found {exact_match['name']}. Is this correct?",
                   "venue_confirmed")
        
        # Fuzzy matching
        fuzzy_matches = self._find_fuzzy_matches(user_input, venues_list)
        
        if len(fuzzy_matches) == 0:
            # No matches found
            return (None,
                   "I couldn't find that venue in our system. Could you check the spelling or try the full venue name?",
                   "venue_not_found")
        
        elif len(fuzzy_matches) == 1:
            # Single fuzzy match
            venue = fuzzy_matches[0]['venue']
            confidence = fuzzy_matches[0]['score']
            
            if confidence > 0.8:
                return (venue,
                       f"I think you mean {venue['name']}. Is this correct?",
                       "venue_suggested")
            else:
                return (None,
                       f"Did you mean {venue['name']}? If not, please try the full venue name.",
                       "venue_uncertain")
        
        else:
            # Multiple matches
            top_matches = fuzzy_matches[:3]  # Show top 3
            options = "\n".join([f"{i+1}. {m['venue']['name']} - {m['venue'].get('location', 'Location not specified')}" 
                                for i, m in enumerate(top_matches)])
            
            # Store matches in conversation state
            self.conversation_state[user_phone] = {
                'matches': top_matches,
                'timestamp': datetime.utcnow()
            }
            
            return (None,
                   f"I found several venues matching '{user_input}':\n{options}\n\nWhich one are you calling from? (Reply with the number)",
                   "venue_multiple_matches")
    
    def _find_exact_match(self, user_input: str, venues_list: List[Dict]) -> Optional[Dict]:
        """Find exact venue name match"""
        for venue in venues_list:
            venue_name = venue.get('name', '').lower()
            if venue_name == user_input:
                return venue
        return None
    
    def _find_fuzzy_matches(self, user_input: str, venues_list: List[Dict]) -> List[Dict]:
        """Find fuzzy matches with confidence scores"""
        matches = []
        
        for venue in venues_list:
            venue_name = venue.get('name', '').lower()
            
            # Calculate similarity score
            score = 0.0
            
            # Check if input is contained in venue name
            if user_input in venue_name:
                score = len(user_input) / len(venue_name)
            # Check if venue name is contained in input
            elif venue_name in user_input:
                score = len(venue_name) / len(user_input)
            else:
                # Use difflib for fuzzy matching
                score = difflib.SequenceMatcher(None, user_input, venue_name).ratio()
            
            # Check individual words
            input_words = set(user_input.split())
            venue_words = set(venue_name.split())
            word_overlap = len(input_words & venue_words) / max(len(input_words), len(venue_words))
            
            # Combine scores
            final_score = max(score, word_overlap)
            
            if final_score > 0.5:  # Threshold for considering a match
                matches.append({
                    'venue': venue,
                    'score': final_score
                })
        
        # Sort by score
        matches.sort(key=lambda x: x['score'], reverse=True)
        return matches
    
    def handle_venue_selection(self, user_input: str, user_phone: str) -> Tuple[Optional[Dict], str]:
        """Handle venue selection from multiple options"""
        
        # Check if user has pending selection
        if user_phone not in self.conversation_state:
            return None, "Let's start over. What's the name of your venue?"
        
        state = self.conversation_state[user_phone]
        matches = state.get('matches', [])
        
        # Try to parse number selection
        try:
            selection = int(user_input.strip()) - 1
            if 0 <= selection < len(matches):
                venue = matches[selection]['venue']
                # Clear state
                del self.conversation_state[user_phone]
                return venue, f"Perfect! I've identified your venue as {venue['name']}."
        except ValueError:
            pass
        
        # Check if they typed a venue name instead
        for match in matches:
            if user_input.lower() in match['venue']['name'].lower():
                venue = match['venue']
                del self.conversation_state[user_phone]
                return venue, f"Got it! You're at {venue['name']}."
        
        return None, "Please select a number from the list or type the venue name again."
    
    def get_clarifying_questions(self, venue: Dict, issue_context: str) -> List[str]:
        """Generate clarifying questions based on venue and issue"""
        questions = []
        
        # Always ask for person's name if not provided
        questions.append("May I have your name?")
        
        # Role is important for access levels
        questions.append("What's your position at the venue?")
        
        # Issue-specific questions
        if 'music' in issue_context.lower() or 'volume' in issue_context.lower():
            if venue.get('metadata', {}).get('has_soundtrack'):
                questions.append("Which zone or area is affected?")
        
        if 'stopped' in issue_context.lower() or 'not working' in issue_context.lower():
            questions.append("When did this start happening?")
            questions.append("Is this affecting all areas or just one zone?")
        
        if 'playlist' in issue_context.lower() or 'song' in issue_context.lower():
            questions.append("What type of music would you prefer?")
        
        return questions


class ConversationContext:
    """Manage conversation context and state"""
    
    def __init__(self):
        self.contexts = {}  # Store context per user
    
    def update_context(self, user_phone: str, **kwargs):
        """Update conversation context"""
        if user_phone not in self.contexts:
            self.contexts[user_phone] = {
                'started_at': datetime.utcnow(),
                'messages': []
            }
        
        self.contexts[user_phone].update(kwargs)
        self.contexts[user_phone]['last_updated'] = datetime.utcnow()
    
    def get_context(self, user_phone: str) -> Dict:
        """Get conversation context"""
        return self.contexts.get(user_phone, {})
    
    def add_message(self, user_phone: str, role: str, content: str):
        """Add message to conversation history"""
        if user_phone not in self.contexts:
            self.contexts[user_phone] = {
                'started_at': datetime.utcnow(),
                'messages': []
            }
        
        self.contexts[user_phone]['messages'].append({
            'role': role,
            'content': content,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    def clear_context(self, user_phone: str):
        """Clear conversation context"""
        if user_phone in self.contexts:
            del self.contexts[user_phone]
    
    def get_conversation_summary(self, user_phone: str) -> str:
        """Get a summary of the conversation"""
        context = self.get_context(user_phone)
        if not context:
            return "No conversation history"
        
        messages = context.get('messages', [])
        venue = context.get('venue', {})
        person = context.get('person_name', 'Unknown')
        role = context.get('person_role', 'Unknown')
        issue = context.get('issue', 'Not specified')
        
        summary = f"""
Venue: {venue.get('name', 'Not identified')}
Person: {person} ({role})
Issue: {issue}
Messages: {len(messages)}
Duration: {(datetime.utcnow() - context.get('started_at', datetime.utcnow())).seconds // 60} minutes
"""
        return summary


# Global instances
venue_identifier = VenueIdentifier()
conversation_context = ConversationContext()
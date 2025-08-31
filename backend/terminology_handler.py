"""
Handle varying terminology for music zones/venues/outlets
Understand what customers mean regardless of their wording
"""

import logging
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)

class TerminologyHandler:
    """
    Handle different terms customers use for music zones
    Hotel: zones, venues, outlets, areas, spaces
    Retail: stores, branches, locations
    Fitness: gyms, studios, clubs
    Restaurant: sections, areas, dining rooms
    """
    
    def __init__(self):
        # Synonyms for different concepts
        self.zone_terms = {
            'hotel': ['zone', 'venue', 'outlet', 'area', 'space', 'room', 'restaurant', 'bar', 'lobby', 'pool', 'spa', 'gym', 'ballroom'],
            'retail': ['store', 'branch', 'location', 'shop', 'outlet', 'department', 'section', 'floor'],
            'fitness': ['gym', 'studio', 'club', 'branch', 'location', 'area', 'room', 'zone'],
            'restaurant': ['section', 'area', 'room', 'zone', 'floor', 'terrace', 'bar', 'lounge'],
            'mall': ['zone', 'area', 'floor', 'wing', 'section', 'court', 'atrium'],
            'corporate': ['office', 'branch', 'location', 'building', 'floor', 'department']
        }
        
        # Company/Property level terms
        self.property_terms = ['hotel', 'resort', 'property', 'establishment', 'company', 'brand', 'chain', 'group']
        
        # Action indicators
        self.specific_zone_indicators = [
            'in the', 'at the', 'in our', 'at our',
            'lobby', 'restaurant', 'bar', 'pool', 'spa', 'gym',
            'first floor', 'second floor', 'ground floor',
            'main', 'upstairs', 'downstairs', 'outdoor', 'indoor'
        ]
        
        self.all_zones_indicators = [
            'all', 'every', 'entire', 'whole', 'everywhere',
            'all zones', 'all outlets', 'all venues', 'all areas',
            'property wide', 'hotel wide', 'company wide',
            'across the', 'throughout'
        ]
    
    def identify_context(self, message: str, company_info: Dict) -> Dict:
        """
        Identify what the user is referring to
        Returns: {
            'level': 'zone' or 'property' or 'chain',
            'specific_zone': 'lobby' or None,
            'all_zones': True/False,
            'clarification_needed': True/False,
            'suggested_question': 'Which area specifically?'
        }
        """
        
        message_lower = message.lower()
        company_type = self._identify_company_type(company_info)
        
        context = {
            'level': None,
            'specific_zone': None,
            'all_zones': False,
            'clarification_needed': False,
            'suggested_question': None
        }
        
        # Check if referring to all zones
        if any(indicator in message_lower for indicator in self.all_zones_indicators):
            context['level'] = 'property'
            context['all_zones'] = True
            return context
        
        # Check for specific zone mentions
        specific_zone = self._extract_specific_zone(message_lower, company_type)
        if specific_zone:
            context['level'] = 'zone'
            context['specific_zone'] = specific_zone
            return context
        
        # Check if the message is ambiguous
        if self._is_ambiguous(message_lower):
            context['clarification_needed'] = True
            context['suggested_question'] = self._generate_clarification(message_lower, company_type)
        
        return context
    
    def _identify_company_type(self, company_info: Dict) -> str:
        """Identify the type of business"""
        company_name = company_info.get('name', '').lower()
        venue_type = company_info.get('metadata', {}).get('venue_type', '').lower()
        
        # Check explicit type
        if venue_type:
            if 'hotel' in venue_type or 'resort' in venue_type:
                return 'hotel'
            elif 'restaurant' in venue_type or 'cafe' in venue_type:
                return 'restaurant'
            elif 'gym' in venue_type or 'fitness' in venue_type:
                return 'fitness'
            elif 'retail' in venue_type or 'shop' in venue_type or 'store' in venue_type:
                return 'retail'
            elif 'mall' in venue_type or 'shopping' in venue_type:
                return 'mall'
        
        # Check company name
        hotel_keywords = ['hotel', 'resort', 'inn', 'suites']
        if any(keyword in company_name for keyword in hotel_keywords):
            return 'hotel'
        
        fitness_keywords = ['fitness', 'gym', 'athletic', 'sport', 'yoga', 'pilates']
        if any(keyword in company_name for keyword in fitness_keywords):
            return 'fitness'
        
        restaurant_keywords = ['restaurant', 'cafe', 'bistro', 'kitchen', 'grill', 'dining']
        if any(keyword in company_name for keyword in restaurant_keywords):
            return 'restaurant'
        
        return 'general'
    
    def _extract_specific_zone(self, message: str, company_type: str) -> Optional[str]:
        """Extract specific zone/venue/outlet from message"""
        
        # Common zone names for hotels
        hotel_zones = {
            'lobby': ['lobby', 'reception', 'entrance', 'foyer'],
            'restaurant': ['restaurant', 'dining', 'breakfast', 'all day dining', 'adr'],
            'bar': ['bar', 'lounge', 'pub', 'cocktail'],
            'pool': ['pool', 'swimming', 'poolside'],
            'spa': ['spa', 'wellness', 'massage', 'treatment'],
            'gym': ['gym', 'fitness', 'workout', 'exercise'],
            'ballroom': ['ballroom', 'function', 'event', 'meeting'],
            'rooftop': ['rooftop', 'roof', 'sky bar', 'skybar']
        }
        
        # Check hotel zones
        if company_type == 'hotel':
            for zone_name, keywords in hotel_zones.items():
                if any(keyword in message for keyword in keywords):
                    return zone_name
        
        # Check floor mentions
        floor_patterns = [
            'ground floor', 'first floor', 'second floor', 'third floor',
            '1st floor', '2nd floor', '3rd floor', '4th floor',
            'floor 1', 'floor 2', 'floor 3', 'floor 4',
            'level 1', 'level 2', 'level 3', 'level 4'
        ]
        
        for pattern in floor_patterns:
            if pattern in message:
                return pattern
        
        # Check for "the [zone name]"
        if 'the ' in message:
            parts = message.split('the ')
            for part in parts[1:]:
                words = part.split()
                if words:
                    potential_zone = words[0]
                    # Check if it's a valid zone term
                    if len(potential_zone) > 2 and potential_zone not in ['music', 'volume', 'sound']:
                        return potential_zone
        
        return None
    
    def _is_ambiguous(self, message: str) -> bool:
        """Check if the message is ambiguous about which zone"""
        
        # Ambiguous phrases
        ambiguous_phrases = [
            'the music', 'our music', 'the volume', 'the sound',
            'it\'s too', 'can you', 'please change', 'please adjust',
            'not working', 'stopped playing', 'no sound'
        ]
        
        # If message has these phrases without specific zone mention
        has_ambiguous = any(phrase in message for phrase in ambiguous_phrases)
        has_specific = any(indicator in message for indicator in self.specific_zone_indicators)
        
        return has_ambiguous and not has_specific
    
    def _generate_clarification(self, message: str, company_type: str) -> str:
        """Generate appropriate clarification question"""
        
        # Volume/music related
        if 'volume' in message or 'loud' in message or 'quiet' in message:
            if company_type == 'hotel':
                return "Which area needs volume adjustment? (e.g., lobby, restaurant, pool)"
            elif company_type == 'fitness':
                return "Which area? (e.g., main gym, studio, reception)"
            else:
                return "Which zone or area specifically?"
        
        # Not working / stopped
        if 'not working' in message or 'stopped' in message or 'no music' in message:
            if company_type == 'hotel':
                return "Where is the music not working? (e.g., lobby, restaurant, or all areas?)"
            else:
                return "Is this affecting one specific area or all zones?"
        
        # Change request
        if 'change' in message or 'different' in message or 'playlist' in message:
            if company_type == 'hotel':
                return "Which area would you like to change? (e.g., lobby, restaurant, or all outlets?)"
            else:
                return "Should I change this for all zones or a specific area?"
        
        # Default
        return "Which specific area or zone are you referring to?"
    
    def translate_user_terms(self, user_term: str, company_type: str) -> str:
        """
        Translate user's terminology to standard terms
        e.g., "venue" in hotel context -> "zone"
        """
        
        user_term_lower = user_term.lower()
        
        # For hotels, normalize to "zone"
        if company_type == 'hotel':
            if user_term_lower in ['venue', 'outlet', 'area', 'space']:
                return 'zone'
        
        # For retail, normalize to "store"
        elif company_type == 'retail':
            if user_term_lower in ['branch', 'location', 'outlet', 'shop']:
                return 'store'
        
        # For fitness, normalize to "area"
        elif company_type == 'fitness':
            if user_term_lower in ['zone', 'room', 'studio']:
                return 'area'
        
        return user_term
    
    def format_zone_list(self, zones: List[str], company_type: str) -> str:
        """
        Format zone list using appropriate terminology
        """
        
        if company_type == 'hotel':
            term = 'areas'
        elif company_type == 'retail':
            term = 'stores'
        elif company_type == 'fitness':
            term = 'zones'
        else:
            term = 'zones'
        
        if len(zones) == 0:
            return f"No {term} found"
        elif len(zones) == 1:
            return zones[0]
        elif len(zones) == 2:
            return f"{zones[0]} and {zones[1]}"
        else:
            return f"{', '.join(zones[:-1])}, and {zones[-1]}"


# Global instance
terminology = TerminologyHandler()
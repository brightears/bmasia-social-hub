"""
Venue data manager for BMA Social
Loads and manages venue information from venue_data.md
"""

import logging
import re
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)


class VenueManager:
    """Manages venue data from markdown files"""
    
    def __init__(self):
        self.venues = {}
        self.load_venue_data()
        
    def load_venue_data(self):
        """Load venue data from venue_data.md"""
        try:
            with open('venue_data.md', 'r') as f:
                content = f.read()
                
            # Parse venues from markdown
            # Split on ### followed by any non-whitespace character
            venue_sections = re.split(r'\n### (?=.)', content)
            
            for venue_section in venue_sections[1:]:  # Skip header
                lines = venue_section.strip().split('\n')
                if not lines:
                    continue
                    
                venue_name = lines[0].strip()
                venue_info = {
                    'name': venue_name,
                    'zones': [],
                    'contract_end': None,
                    'annual_price': None,
                    'platform': None,
                    'hardware_type': None,
                    'account_id': None,
                    'contacts': []
                }
                
                for line in lines[1:]:
                    if '**Zone Names**:' in line:
                        zones_text = line.split(':', 1)[1].strip()
                        venue_info['zones'] = [z.strip() for z in zones_text.split(',')]
                    elif '**Contract End**:' in line:
                        venue_info['contract_end'] = line.split(':', 1)[1].strip()
                    elif '**Annual Price per Zone**:' in line:
                        venue_info['annual_price'] = line.split(':', 1)[1].strip()
                    elif '**Music Platform**:' in line:
                        venue_info['platform'] = line.split(':', 1)[1].strip()
                    elif '**Hardware Type**:' in line:
                        venue_info['hardware_type'] = line.split(':', 1)[1].strip()
                    elif '**Soundtrack Account ID**:' in line:
                        venue_info['account_id'] = line.split(':', 1)[1].strip()
                
                # Store with lowercase key for easy lookup
                self.venues[venue_name.lower()] = venue_info
                
            logger.info(f"Loaded {len(self.venues)} venues from venue_data.md")
            
        except FileNotFoundError:
            logger.warning("venue_data.md not found - no venue data loaded")
        except Exception as e:
            logger.error(f"Error loading venue data: {e}")
    
    def find_venue(self, message: str) -> Optional[Dict]:
        """Find venue mentioned in message - returns None for low confidence matches"""
        venue, confidence = self.find_venue_with_confidence(message)
        if confidence >= 0.7:
            return venue
        return None

    def find_venue_with_confidence(self, message: str) -> tuple[Optional[Dict], float]:
        """
        Find venue mentioned in message with confidence score
        Returns: (venue_dict, confidence_score)
        Confidence levels:
        - 1.0: Exact full venue name match
        - 0.8: Most of venue name matches
        - 0.5: Partial match (e.g., "Hilton" for "Hilton Pattaya")
        - 0.0: No match
        """
        message_lower = message.lower()
        best_match = None
        best_confidence = 0.0

        # First check for exact full name matches
        for venue_key, venue_info in self.venues.items():
            if venue_key in message_lower:
                # Full venue name found - high confidence
                logger.info(f"Found exact venue match: {venue_info['name']}")
                return venue_info, 1.0

        # Check for partial matches with confidence scoring
        matches = []
        for venue_key, venue_info in self.venues.items():
            venue_words = venue_key.split()
            matched_words = 0

            for word in venue_words:
                if len(word) > 3 and word in message_lower:
                    matched_words += 1

            if matched_words > 0:
                # Calculate confidence based on how many words matched
                confidence = matched_words / len(venue_words)

                # Penalize if it's a common word match only
                if matched_words == 1 and venue_words[0] in ['hotel', 'resort', 'club', 'bar', 'restaurant']:
                    confidence *= 0.3

                matches.append((venue_info, confidence))

        if matches:
            # Sort by confidence and return best match
            matches.sort(key=lambda x: x[1], reverse=True)
            best_match, best_confidence = matches[0]

            if best_confidence >= 0.5:
                logger.info(f"Found venue with confidence {best_confidence:.2f}: {best_match['name']}")
            else:
                logger.info(f"Low confidence venue match ({best_confidence:.2f}): {best_match['name']}")

            return best_match, best_confidence

        return None, 0.0

    def find_possible_venues(self, message: str, threshold: float = 0.3) -> List[tuple[Dict, float]]:
        """
        Find all possible venue matches above threshold
        Returns list of (venue_dict, confidence_score) tuples
        """
        message_lower = message.lower()
        matches = []

        for venue_key, venue_info in self.venues.items():
            # Check exact match
            if venue_key in message_lower:
                matches.append((venue_info, 1.0))
                continue

            # Check partial matches
            venue_words = venue_key.split()
            matched_words = 0

            for word in venue_words:
                if len(word) > 3 and word in message_lower:
                    matched_words += 1

            if matched_words > 0:
                confidence = matched_words / len(venue_words)

                # Penalize common word only matches
                if matched_words == 1 and venue_words[0] in ['hotel', 'resort', 'club', 'bar', 'restaurant']:
                    confidence *= 0.3

                if confidence >= threshold:
                    matches.append((venue_info, confidence))

        # Sort by confidence
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches
    
    def get_venue_info(self, venue_name: str) -> Optional[Dict]:
        """Get venue info by name"""
        return self.venues.get(venue_name.lower())
    
    def list_venues(self) -> List[str]:
        """List all venue names"""
        return [v['name'] for v in self.venues.values()]
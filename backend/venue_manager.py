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
            venue_sections = re.split(r'\n### (?=\w)', content)
            
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
        """Find venue mentioned in message"""
        message_lower = message.lower()
        
        # Check each venue name
        for venue_key, venue_info in self.venues.items():
            # Check if venue name is in message
            if venue_key in message_lower:
                logger.info(f"Found venue: {venue_info['name']}")
                return venue_info
            
            # Also check partial matches (e.g., "Hilton" for "Hilton Pattaya")
            venue_words = venue_key.split()
            for word in venue_words:
                if len(word) > 4 and word in message_lower:  # Only match significant words
                    logger.info(f"Found venue by partial match: {venue_info['name']}")
                    return venue_info
        
        return None
    
    def get_venue_info(self, venue_name: str) -> Optional[Dict]:
        """Get venue info by name"""
        return self.venues.get(venue_name.lower())
    
    def list_venues(self) -> List[str]:
        """List all venue names"""
        return [v['name'] for v in self.venues.values()]
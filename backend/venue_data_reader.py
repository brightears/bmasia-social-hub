#!/usr/bin/env python3
"""
Simple venue data reader from Markdown file.
Replaces Google Sheets for more reliable data access.
"""

import re
import logging
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class VenueDataReader:
    """Read venue data from local Markdown file"""
    
    def __init__(self, file_path: str = "venue_data.md"):
        """Initialize with path to markdown file"""
        self.file_path = Path(__file__).parent / file_path
        self.venues = []
        self.load_data()
    
    def load_data(self):
        """Load and parse venue data from markdown file"""
        try:
            if not self.file_path.exists():
                logger.error(f"Venue data file not found: {self.file_path}")
                return
            
            with open(self.file_path, 'r') as f:
                content = f.read()
            
            # Parse venues from markdown
            self.venues = self.parse_markdown(content)
            logger.info(f"Loaded {len(self.venues)} venues from {self.file_path}")
            
        except Exception as e:
            logger.error(f"Error loading venue data: {e}")
            self.venues = []
    
    def parse_markdown(self, content: str) -> List[Dict]:
        """Parse venue data from markdown content"""
        venues = []
        
        # Split by venue headers (### VenueName)
        venue_sections = re.split(r'^### ', content, flags=re.MULTILINE)[1:]
        
        for section in venue_sections:
            if not section.strip():
                continue
                
            lines = section.strip().split('\n')
            venue_name = lines[0].strip()
            
            # Skip summary sections
            if any(skip in venue_name.lower() for skip in ['summary', 'quick reference', 'properties with', 'technical contacts', 'common issues']):
                continue
            
            venue = {
                'property_name': venue_name,
                'contacts': [],
                'issue_history': [],
                'special_notes': []
            }
            
            current_section = 'main'
            current_contact = None
            
            for i, line in enumerate(lines[1:]):
                # Check for section headers
                if line.startswith('#### Contacts'):
                    current_section = 'contacts'
                    continue
                elif line.startswith('#### Issue History'):
                    current_section = 'issue_history'
                    continue
                elif line.startswith('#### Special Notes'):
                    current_section = 'special_notes'
                    continue
                elif line.startswith('---'):
                    break
                
                # Parse based on current section
                if current_section == 'main' and line.startswith('- **'):
                    # Main property data
                    match = re.match(r'- \*\*(.+?)\*\*:\s*(.+)', line)
                    if match:
                        key = match.group(1).lower().replace(' ', '_').replace('/', '_')
                        value = match.group(2).strip()
                        venue[key] = value
                        
                elif current_section == 'contacts':
                    if line.startswith('- **'):
                        # New contact
                        match = re.match(r'- \*\*(.+?)\*\*:\s*(.+)', line)
                        if match:
                            if current_contact:
                                venue['contacts'].append(current_contact)
                            current_contact = {
                                'title': match.group(1),
                                'name': match.group(2)
                            }
                    elif line.strip().startswith('- ') and current_contact:
                        # Contact detail
                        detail_match = re.match(r'\s*- (.+?):\s*(.+)', line)
                        if detail_match:
                            key = detail_match.group(1).lower().replace(' ', '_')
                            current_contact[key] = detail_match.group(2)
                            
                elif current_section == 'issue_history':
                    if line.startswith('- **'):
                        match = re.match(r'- \*\*(.+?)\*\*:\s*(.+)', line)
                        if match:
                            venue['issue_history'].append({
                                'date': match.group(1),
                                'issue': match.group(2)
                            })
                            
                elif current_section == 'special_notes':
                    if line.startswith('- '):
                        venue['special_notes'].append(line[2:].strip())
            
            # Add last contact if exists
            if current_contact:
                venue['contacts'].append(current_contact)
            
            if venue.get('property_name'):
                venues.append(venue)
                logger.debug(f"Parsed venue: {venue['property_name']} with {len(venue['contacts'])} contacts")
        
        return venues
    
    def get_all_venues(self) -> List[Dict]:
        """Get all venues"""
        return self.venues
    
    def find_venue_by_name(self, venue_name: str) -> Optional[Dict]:
        """Find venue by name with fuzzy matching"""
        venue_name_lower = venue_name.lower()
        
        for venue in self.venues:
            property_name = venue.get('property_name', '').lower()
            
            # Exact match
            if property_name == venue_name_lower:
                return venue
            
            # Partial match
            if venue_name_lower in property_name or property_name in venue_name_lower:
                return venue
            
            # Check individual words
            venue_words = venue_name_lower.split()
            property_words = property_name.split()
            
            for word in venue_words:
                if any(word in prop_word for prop_word in property_words):
                    return venue
        
        return None
    
    def get_venue(self, venue_name: str) -> Optional[Dict]:
        """Get a specific venue by name"""
        return self.find_venue_by_name(venue_name)
    
    def get_venue_zones(self, venue_name: str) -> List[str]:
        """Get zones for a venue"""
        venue = self.find_venue_by_name(venue_name)
        if venue and venue.get('zone_names'):
            return [z.strip() for z in venue['zone_names'].split(',')]
        return []
    
    def get_venue_pricing(self, venue_name: str) -> Dict:
        """Get pricing information for a venue"""
        venue = self.find_venue_by_name(venue_name)
        if venue:
            return {
                'property_name': venue.get('property_name'),
                'zone_count': venue.get('zone_count'),
                'annual_price_per_zone': venue.get('annual_price_per_zone'),
                'currency': venue.get('currency'),
                'contract_start': venue.get('contract_start'),
                'contract_end': venue.get('contract_end'),
                'total_annual_price': self._calculate_total_price(venue)
            }
        return {}
    
    def _calculate_total_price(self, venue: Dict) -> str:
        """Calculate total annual price for venue"""
        try:
            zone_count = int(venue.get('zone_count', 0))
            # Extract number from price string (e.g., "THB 10,500" -> 10500)
            price_str = venue.get('annual_price_per_zone', '')
            price_match = re.search(r'[\d,]+', price_str)
            if price_match:
                price_per_zone = int(price_match.group().replace(',', ''))
                total = zone_count * price_per_zone
                currency = venue.get('currency', 'THB')
                return f"{currency} {total:,}"
        except:
            pass
        return "N/A"
    
    def get_venue_contacts(self, venue_name: str, role: str = None) -> List[Dict]:
        """Get contacts for a venue, optionally filtered by role"""
        venue = self.find_venue_by_name(venue_name)
        if not venue:
            return []
        
        contacts = venue.get('contacts', [])
        if role:
            role_lower = role.lower()
            return [c for c in contacts if role_lower in c.get('title', '').lower()]
        return contacts
    
    def get_venue_issues(self, venue_name: str) -> List[Dict]:
        """Get issue history for a venue"""
        venue = self.find_venue_by_name(venue_name)
        if venue:
            return venue.get('issue_history', [])
        return []
    
    def get_venue_notes(self, venue_name: str) -> List[str]:
        """Get special notes for a venue"""
        venue = self.find_venue_by_name(venue_name)
        if venue:
            return venue.get('special_notes', [])
        return []
    
    def find_similar_issue(self, issue_description: str) -> List[Dict]:
        """Find similar issues from history across all venues"""
        similar = []
        issue_lower = issue_description.lower()
        keywords = issue_lower.split()
        
        for venue in self.venues:
            for issue in venue.get('issue_history', []):
                issue_text = issue.get('issue', '').lower()
                # Check if any keyword matches
                if any(kw in issue_text for kw in keywords if len(kw) > 3):
                    similar.append({
                        'venue': venue.get('property_name'),
                        'date': issue.get('date'),
                        'issue': issue.get('issue')
                    })
        
        return similar


# Singleton instance
venue_reader = VenueDataReader()


# Convenience functions
def get_all_venues() -> List[Dict]:
    """Get all venues from data file"""
    return venue_reader.get_all_venues()


def find_venue(venue_name: str) -> Optional[Dict]:
    """Find venue by name"""
    return venue_reader.find_venue_by_name(venue_name)


def get_venue_pricing(venue_name: str) -> Dict:
    """Get venue pricing information"""
    return venue_reader.get_venue_pricing(venue_name)


# Test the module
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("\nTesting Venue Data Reader")
    print("-" * 40)
    
    venues = get_all_venues()
    print(f"Total venues loaded: {len(venues)}")
    
    for venue in venues:
        print(f"\n{venue['property_name']}:")
        print(f"  - Type: {venue.get('business_type')}")
        print(f"  - Zones: {venue.get('zone_count')}")
        print(f"  - Price: {venue.get('annual_price_per_zone')}")
    
    print("\n" + "-" * 40)
    print("Testing venue search:")
    
    test_venue = find_venue("Hilton")
    if test_venue:
        print(f"Found: {test_venue['property_name']}")
        pricing = get_venue_pricing("Hilton")
        print(f"Pricing: {pricing}")
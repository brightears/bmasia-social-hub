#!/usr/bin/env python3
"""
Music Design reader from Markdown file.
Provides schedule and playlist information for bot intelligence.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime, time

logger = logging.getLogger(__name__)


class MusicDesignReader:
    """Read music design schedules from MD file"""
    
    def __init__(self, file_path: str = "music_design.md"):
        """Initialize with path to markdown file"""
        self.file_path = Path(__file__).parent / file_path
        self.designs = {}
        self.load_data()
    
    def load_data(self):
        """Load and parse music design data"""
        try:
            if not self.file_path.exists():
                logger.error(f"Music design file not found: {self.file_path}")
                return
            
            with open(self.file_path, 'r') as f:
                content = f.read()
            
            # Parse designs from markdown
            self.designs = self.parse_markdown(content)
            logger.info(f"Loaded music designs for {len(self.designs)} properties")
            
        except Exception as e:
            logger.error(f"Error loading music design: {e}")
            self.designs = {}
    
    def parse_markdown(self, content: str) -> Dict:
        """Parse music design from markdown content"""
        designs = {}
        
        # For now, simple structure - can be enhanced
        # This is a simplified parser for the current format
        current_property = None
        current_zone = None
        
        lines = content.split('\n')
        for line in lines:
            # Check for property header
            if line.startswith('## ') and 'Hilton Pattaya' in line:
                current_property = 'Hilton Pattaya'
                designs[current_property] = {'zones': {}}
            
            # Check for zone headers
            elif line.startswith('### ') and current_property:
                zone_name = line.replace('### ', '').strip()
                if zone_name not in ['Zone Overview', 'Recent Changes & Issues', 'Design Guidelines', 'API Integration Notes', 'Contact for Music Changes', 'Notes for Bot Intelligence']:
                    current_zone = zone_name
                    designs[current_property]['zones'][current_zone] = {
                        'schedules': [],
                        'settings': {},
                        'issues': []
                    }
        
        return designs
    
    def get_current_schedule(self, property_name: str, zone_name: str) -> Optional[Dict]:
        """Get current schedule for a zone based on time and day"""
        now = datetime.now()
        current_time = now.time()
        day_type = 'weekend' if now.weekday() >= 4 else 'weekday'
        
        # This would return the active schedule
        # For now, return a sample structure
        return {
            'playlist': 'Afternoon Energy',
            'energy': 'Medium',
            'volume': '65%',
            'notes': 'Upbeat pop, tropical house'
        }
    
    def get_zone_settings(self, property_name: str, zone_name: str) -> Dict:
        """Get special settings for a zone"""
        # Would parse from the MD file
        return {
            'crossfade': '30 seconds',
            'explicit_filter': True,
            'shuffle': 'smart',
            'holiday_override': True
        }
    
    def find_similar_music_issue(self, issue_description: str) -> List[Dict]:
        """Find similar music-related issues from history"""
        similar = []
        issue_lower = issue_description.lower()
        
        # Check common patterns
        if 'loud' in issue_lower or 'volume' in issue_lower:
            similar.append({
                'issue': 'Volume complaints',
                'solution': 'Check time-based volume schedule, reduce after 22:00',
                'zone': 'Common to all bars'
            })
        
        if 'wrong' in issue_lower or 'playlist' in issue_lower:
            similar.append({
                'issue': 'Wrong playlist playing',
                'solution': 'Zone may need restart, check schedule configuration',
                'zone': 'Common issue'
            })
        
        if 'boring' in issue_lower or 'repetitive' in issue_lower:
            similar.append({
                'issue': 'Music too repetitive',
                'solution': 'Enable smart shuffle, refresh playlist, increase playlist size',
                'zone': 'Common issue'
            })
        
        return similar
    
    def get_schedule_for_time(self, property_name: str, zone_name: str, check_time: str = None) -> Optional[Dict]:
        """Get what should be playing at a specific time"""
        # Parse time and determine schedule
        # This is simplified - would need full parsing
        
        schedules = {
            'Drift Bar': {
                'weekday': [
                    {'start': '11:00', 'end': '14:00', 'playlist': 'Chill Lunch Vibes', 'volume': '60%'},
                    {'start': '14:00', 'end': '18:00', 'playlist': 'Afternoon Energy', 'volume': '65%'},
                    {'start': '18:00', 'end': '22:00', 'playlist': 'Sunset Sessions', 'volume': '65%'},
                    {'start': '22:00', 'end': '02:00', 'playlist': 'Late Night Cocktails', 'volume': '55%'}
                ],
                'weekend': [
                    {'start': '11:00', 'end': '14:00', 'playlist': 'Weekend Brunch', 'volume': '65%'},
                    {'start': '14:00', 'end': '18:00', 'playlist': 'Pool Party Vibes', 'volume': '70%'},
                    {'start': '18:00', 'end': '22:00', 'playlist': 'Golden Hour', 'volume': '70%'},
                    {'start': '22:00', 'end': '03:00', 'playlist': 'Weekend Nights', 'volume': '60%'}
                ]
            }
        }
        
        # Return appropriate schedule
        if zone_name in schedules:
            return schedules[zone_name]
        return None
    
    def suggest_change_for_issue(self, issue: str, zone: str) -> str:
        """Suggest a change based on the issue reported"""
        issue_lower = issue.lower()
        
        if 'loud' in issue_lower:
            current = self.get_current_schedule('Hilton Pattaya', zone)
            if current:
                return f"Current volume is {current.get('volume', 'unknown')}. Suggest reducing by 10%."
        
        if 'energy' in issue_lower or 'boring' in issue_lower:
            return "Suggest switching to higher energy playlist or refreshing current playlist with new tracks."
        
        if 'inappropriate' in issue_lower or 'explicit' in issue_lower:
            return "Enable explicit content filter and review playlist curation."
        
        return "Escalate to design team for custom solution."


# Singleton instance
music_reader = MusicDesignReader()


# Convenience functions for bot integration
def get_current_music(property_name: str, zone_name: str) -> Dict:
    """Get what's currently scheduled to play"""
    return music_reader.get_current_schedule(property_name, zone_name)


def find_music_issue_solution(issue: str) -> List[Dict]:
    """Find solutions for common music issues"""
    return music_reader.find_similar_music_issue(issue)


def get_music_change_suggestion(issue: str, zone: str) -> str:
    """Get suggestion for fixing a music issue"""
    return music_reader.suggest_change_for_issue(issue, zone)


# Integration with Soundtrack API (when available)
def sync_with_soundtrack_api(property_name: str):
    """
    Sync current schedules from Soundtrack API
    This would be called periodically to update the MD file
    """
    try:
        from soundtrack_api import soundtrack_api
        
        # Get zones for property
        zones = soundtrack_api.find_venue_zones(property_name)
        
        for zone in zones:
            zone_id = zone.get('id')
            zone_name = zone.get('name')
            
            # Get current playing info
            now_playing = soundtrack_api.get_now_playing(zone_id)
            
            # Get zone status
            status = soundtrack_api.get_zone_status(zone_id)
            
            # Update our local data with API info
            logger.info(f"Synced {zone_name}: {now_playing}")
            
            # TODO: Parse and update MD file with actual schedule data
            
        return True
        
    except Exception as e:
        logger.error(f"Could not sync with Soundtrack API: {e}")
        return False


# Test the module
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("\nTesting Music Design Reader")
    print("-" * 40)
    
    # Test current schedule
    current = get_current_music("Hilton Pattaya", "Drift Bar")
    print(f"Current at Drift Bar: {current}")
    
    # Test issue solutions
    solutions = find_music_issue_solution("music too loud at night")
    print(f"\nSolutions for 'too loud': {solutions}")
    
    # Test change suggestions
    suggestion = get_music_change_suggestion("too loud", "Drift Bar")
    print(f"\nChange suggestion: {suggestion}")
    
    # Try to sync with API (if available)
    print("\n" + "-" * 40)
    print("Attempting API sync...")
    sync_success = sync_with_soundtrack_api("Hilton Pattaya")
    print(f"Sync result: {sync_success}")
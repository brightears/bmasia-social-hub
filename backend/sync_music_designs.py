#!/usr/bin/env python3
"""
Sync music designs from Soundtrack API to music_design.md
Run this periodically (daily/weekly) to keep data current
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import re

logger = logging.getLogger(__name__)


class MusicDesignSync:
    """Sync music schedules from Soundtrack API to MD file"""
    
    def __init__(self):
        self.md_file_path = Path(__file__).parent / "music_design.md"
        self.venue_data_path = Path(__file__).parent / "venue_data.md"
        
    def sync_all_syb_venues(self):
        """Sync all Soundtrack Your Brand venues"""
        try:
            from soundtrack_api import soundtrack_api
            from venue_data_reader import get_all_venues
            
            venues = get_all_venues()
            syb_venues = [v for v in venues if v.get('music_platform') == 'Soundtrack Your Brand']
            
            logger.info(f"Found {len(syb_venues)} SYB venues to sync")
            
            for venue in syb_venues:
                venue_name = venue.get('property_name')
                logger.info(f"Syncing {venue_name}...")
                self.sync_venue(venue_name)
                
        except Exception as e:
            logger.error(f"Sync failed: {e}")
    
    def sync_venue(self, venue_name: str):
        """Sync a specific venue's music design"""
        try:
            from soundtrack_api import soundtrack_api
            
            # Get zones from API
            zones = soundtrack_api.find_venue_zones(venue_name)
            
            if not zones:
                logger.warning(f"No zones found for {venue_name}")
                return
            
            venue_design = {
                'property_name': venue_name,
                'last_synced': datetime.now().isoformat(),
                'zones': {}
            }
            
            for zone in zones:
                zone_id = zone.get('id')
                zone_name = zone.get('name')
                
                # Get current status
                status = soundtrack_api.get_zone_status(zone_id)
                now_playing = soundtrack_api.get_now_playing(zone_id)
                
                # Try to get schedule via custom query
                schedule_data = self._get_zone_schedule(zone_id)
                
                venue_design['zones'][zone_name] = {
                    'zone_id': zone_id,
                    'online': zone.get('online', False),
                    'current_playlist': now_playing.get('soundtrack', {}).get('name', 'Unknown'),
                    'current_track': now_playing.get('track', {}).get('name', 'Unknown'),
                    'schedule': schedule_data
                }
                
                logger.info(f"  - {zone_name}: {now_playing.get('soundtrack', {}).get('name', 'Unknown')}")
            
            # Update MD file
            self._update_md_file(venue_design)
            
            return venue_design
            
        except Exception as e:
            logger.error(f"Failed to sync {venue_name}: {e}")
            return None
    
    def _get_zone_schedule(self, zone_id: str) -> Dict:
        """Try to get schedule information for a zone"""
        try:
            from soundtrack_api import soundtrack_api
            
            # This query attempts to get schedule info
            # Note: Actual query structure depends on SYB API capabilities
            query = """
            query GetZoneSchedule($zoneId: ID!) {
                node(id: $zoneId) {
                    ... on Zone {
                        id
                        name
                        currentSoundtrack {
                            id
                            name
                        }
                        soundtrackSchedule {
                            scheduleItems {
                                startTime
                                endTime
                                soundtrack {
                                    name
                                }
                                daysOfWeek
                            }
                        }
                        playbackSettings {
                            volume
                        }
                    }
                }
            }
            """
            
            result = soundtrack_api._make_graphql_request(
                query,
                {"zoneId": zone_id}
            )
            
            # Parse and return schedule
            if result and 'data' in result:
                return result['data'].get('node', {})
            
        except Exception as e:
            logger.debug(f"Could not get schedule for zone {zone_id}: {e}")
        
        return {}
    
    def _update_md_file(self, venue_design: Dict):
        """Update the music_design.md file with new data"""
        venue_name = venue_design['property_name']
        
        # Read existing file
        if self.md_file_path.exists():
            with open(self.md_file_path, 'r') as f:
                content = f.read()
        else:
            content = "# Music Design Schedules\n\n"
        
        # Find and update venue section
        venue_section_start = content.find(f"## {venue_name}")
        
        if venue_section_start == -1:
            # Add new venue section
            new_section = self._create_venue_section(venue_design)
            content += f"\n{new_section}"
        else:
            # Update existing section
            # Find next venue section or end of file
            next_venue = content.find("\n## ", venue_section_start + 1)
            if next_venue == -1:
                next_venue = len(content)
            
            # Replace the section
            new_section = self._create_venue_section(venue_design)
            content = content[:venue_section_start] + new_section + content[next_venue:]
        
        # Update the Last Updated date at the top
        content = re.sub(
            r'Last Updated: \d{4}-\d{2}-\d{2}',
            f'Last Updated: {datetime.now().strftime("%Y-%m-%d")}',
            content
        )
        
        # Write back to file
        with open(self.md_file_path, 'w') as f:
            f.write(content)
        
        logger.info(f"Updated music_design.md for {venue_name}")
    
    def _create_venue_section(self, venue_design: Dict) -> str:
        """Create markdown section for a venue"""
        venue_name = venue_design['property_name']
        last_synced = venue_design.get('last_synced', 'Unknown')
        
        section = f"## {venue_name}\n\n"
        section += f"**Last API Sync**: {last_synced}\n\n"
        
        for zone_name, zone_data in venue_design.get('zones', {}).items():
            section += f"### {zone_name}\n"
            section += f"- **Zone ID**: {zone_data.get('zone_id', 'Unknown')}\n"
            section += f"- **Status**: {'Online' if zone_data.get('online') else 'Offline'}\n"
            section += f"- **Current Playlist**: {zone_data.get('current_playlist', 'Unknown')}\n"
            section += f"- **Now Playing**: {zone_data.get('current_track', 'Unknown')}\n\n"
            
            # Add schedule if available
            schedule = zone_data.get('schedule', {})
            if schedule and schedule.get('soundtrackSchedule'):
                section += "#### Schedule\n"
                section += "| Time | Days | Playlist |\n"
                section += "|------|------|----------|\n"
                
                for item in schedule['soundtrackSchedule'].get('scheduleItems', []):
                    start = item.get('startTime', 'Unknown')
                    end = item.get('endTime', 'Unknown')
                    days = ', '.join(item.get('daysOfWeek', []))
                    playlist = item.get('soundtrack', {}).get('name', 'Unknown')
                    section += f"| {start}-{end} | {days} | {playlist} |\n"
                
                section += "\n"
        
        return section


def main():
    """Run sync for all venues"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    syncer = MusicDesignSync()
    
    print("\n" + "="*60)
    print("MUSIC DESIGN SYNC")
    print("="*60)
    print()
    
    # Sync all SYB venues
    syncer.sync_all_syb_venues()
    
    print("\n✅ Sync complete!")
    print(f"Data saved to: music_design.md")
    
    # You could also sync a specific venue
    # syncer.sync_venue("Hilton Pattaya")


if __name__ == "__main__":
    main()
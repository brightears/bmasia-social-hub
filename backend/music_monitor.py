#!/usr/bin/env python3
"""
Real-time music monitoring - compares intended design with actual playing
"""

import logging
from datetime import datetime
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class MusicMonitor:
    """Monitor music in real-time and compare with intended design"""
    
    def __init__(self):
        """Initialize with both data sources"""
        from music_design_reader import music_reader
        from venue_data_reader import venue_reader
        
        self.design_reader = music_reader
        self.venue_reader = venue_reader
        
        # Try to import Soundtrack API
        try:
            from soundtrack_api import soundtrack_api
            self.syb_api = soundtrack_api
            self.api_available = True
        except:
            self.syb_api = None
            self.api_available = False
            logger.warning("Soundtrack API not available")
    
    def check_zone_status(self, property_name: str, zone_name: str) -> Dict:
        """
        Check zone status - different approach per platform
        SYB: Live data, history, and schedule
        Beat Breeze: Design specs from MD file only (no API)
        """
        
        # Check if this is a SYB venue
        venue = self.venue_reader.find_venue_by_name(property_name)
        is_syb = venue and venue.get('music_platform') == 'Soundtrack Your Brand'
        
        if is_syb:
            # For SYB: Get current status, schedule, and history
            actual = self.get_actual_music(property_name, zone_name)
            schedule = self.get_zone_schedule(property_name, zone_name)
            history = self.get_playlist_history(property_name, zone_name)
            
            return {
                'property': property_name,
                'zone': zone_name,
                'actual': actual,
                'schedule': schedule,
                'history': history,
                'platform': 'SYB',
                'timestamp': datetime.now().isoformat()
            }
        else:
            # For Beat Breeze: Only use design specs (no real-time API)
            intended = self.get_intended_music(property_name, zone_name)
            
            return {
                'property': property_name,
                'zone': zone_name,
                'intended': intended,
                'actual': {'status': 'No API available for Beat Breeze'},
                'platform': 'Beat Breeze',
                'note': 'Beat Breeze venues are managed directly. Contact venue for current status.',
                'timestamp': datetime.now().isoformat()
            }
    
    def get_intended_music(self, property_name: str, zone_name: str) -> Dict:
        """Get what should be playing based on design"""
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        day_type = 'weekend' if now.weekday() >= 4 else 'weekday'
        
        # This reads from music_design.md
        # Would parse the schedule for current time/day
        intended = {
            'playlist': 'Unknown',
            'energy': 'Unknown'
        }
        
        # Example logic (simplified) with SYB volume levels (0-16)
        if zone_name == 'Drift Bar':
            hour = now.hour
            if 11 <= hour < 14:
                intended['playlist'] = 'Chill Lunch Vibes'
                intended['energy'] = 'Low-Medium'
                intended['volume_level'] = 10  # Medium volume
            elif 14 <= hour < 18:
                intended['playlist'] = 'Afternoon Energy'
                intended['energy'] = 'Medium'
                intended['volume_level'] = 11  # Medium-high
            elif 18 <= hour < 22:
                intended['playlist'] = 'Sunset Sessions'
                intended['energy'] = 'Medium'
                intended['volume_level'] = 11  # Medium-high
            elif hour >= 22 or hour < 2:
                intended['playlist'] = 'Late Night Cocktails'
                intended['energy'] = 'Low-Medium'
                intended['volume_level'] = 9  # Reduced for late night
        elif zone_name == 'Lobby':
            # Lobby typically quieter
            intended['playlist'] = 'Lobby Ambiance'
            intended['energy'] = 'Low'
            intended['volume_level'] = 7  # Low volume for lobby
        
        intended['time'] = current_time
        intended['day_type'] = day_type
        
        return intended
    
    def get_zone_schedule(self, property_name: str, zone_name: str) -> Dict:
        """Get the weekly schedule for a SYB zone"""
        
        if not self.api_available:
            return {'error': 'API not available'}
        
        try:
            # Find the zone
            zones = self.syb_api.find_venue_zones(property_name)
            target_zone = None
            
            for zone in zones:
                if zone.get('name', '').lower() == zone_name.lower():
                    target_zone = zone
                    break
            
            if not target_zone:
                return {'error': 'Zone not found'}
            
            zone_id = target_zone.get('id')
            
            # Query for schedule information
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
                            id
                            name
                            isActive
                            scheduleItems {
                                id
                                startTime
                                endTime
                                soundtrack {
                                    id
                                    name
                                }
                                daysOfWeek
                            }
                        }
                        playbackSettings {
                            volume
                            crossfadeDuration
                            gaplessModeEnabled
                        }
                    }
                }
            }
            """
            
            result = self.syb_api._make_graphql_request(
                query,
                {"zoneId": zone_id}
            )
            
            if result and 'data' in result:
                zone_data = result['data'].get('node', {})
                schedule_data = zone_data.get('soundtrackSchedule', {})
                
                if schedule_data and schedule_data.get('scheduleItems'):
                    # Parse schedule into readable format
                    schedule_by_day = {}
                    
                    for item in schedule_data.get('scheduleItems', []):
                        days = item.get('daysOfWeek', [])
                        start = item.get('startTime', 'Unknown')
                        end = item.get('endTime', 'Unknown')
                        playlist = item.get('soundtrack', {}).get('name', 'Unknown')
                        
                        for day in days:
                            if day not in schedule_by_day:
                                schedule_by_day[day] = []
                            schedule_by_day[day].append({
                                'time': f"{start}-{end}",
                                'playlist': playlist
                            })
                    
                    # Get current playback settings
                    settings = zone_data.get('playbackSettings', {})
                    
                    return {
                        'has_schedule': True,
                        'schedule_name': schedule_data.get('name', 'Unknown'),
                        'is_active': schedule_data.get('isActive', False),
                        'weekly_schedule': schedule_by_day,
                        'volume_level': settings.get('volume'),
                        'crossfade': settings.get('crossfadeDuration'),
                        'gapless': settings.get('gaplessModeEnabled')
                    }
                else:
                    return {
                        'has_schedule': False,
                        'current_playlist': zone_data.get('currentSoundtrack', {}).get('name', 'Unknown'),
                        'note': 'Zone is not using a scheduled playlist rotation'
                    }
            
            return {'error': 'Could not retrieve schedule'}
            
        except Exception as e:
            logger.error(f"Failed to get zone schedule: {e}")
            return {'error': str(e)}
    
    def get_playlist_history(self, property_name: str, zone_name: str, weeks_back: int = 3) -> Dict:
        """Get playlist history from SYB for the past N weeks"""
        
        if not self.api_available:
            return {'error': 'API not available'}
        
        try:
            from datetime import timedelta
            
            # Find the zone
            zones = self.syb_api.find_venue_zones(property_name)
            target_zone = None
            
            for zone in zones:
                if zone.get('name', '').lower() == zone_name.lower():
                    target_zone = zone
                    break
            
            if not target_zone:
                return {'error': 'Zone not found'}
            
            zone_id = target_zone.get('id')
            
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(weeks=weeks_back)
            
            # GraphQL query for playlist history
            query = """
            query GetPlaylistHistory($zoneId: ID!, $startDate: DateTime!, $endDate: DateTime!) {
                node(id: $zoneId) {
                    ... on Zone {
                        playbackHistory(
                            startDate: $startDate
                            endDate: $endDate
                        ) {
                            items {
                                timestamp
                                soundtrack {
                                    name
                                    id
                                }
                                track {
                                    name
                                    artists {
                                        name
                                    }
                                }
                            }
                        }
                    }
                }
            }
            """
            
            result = self.syb_api._make_graphql_request(
                query,
                {
                    "zoneId": zone_id,
                    "startDate": start_date.isoformat(),
                    "endDate": end_date.isoformat()
                }
            )
            
            if result and 'data' in result:
                history_data = result['data'].get('node', {}).get('playbackHistory', {})
                
                # Analyze patterns
                playlist_counts = {}
                for item in history_data.get('items', []):
                    playlist = item.get('soundtrack', {}).get('name', 'Unknown')
                    playlist_counts[playlist] = playlist_counts.get(playlist, 0) + 1
                
                return {
                    'weeks_analyzed': weeks_back,
                    'playlist_patterns': playlist_counts,
                    'most_common': max(playlist_counts, key=playlist_counts.get) if playlist_counts else None,
                    'total_tracks': len(history_data.get('items', []))
                }
            
            return {'error': 'Could not retrieve history'}
            
        except Exception as e:
            logger.error(f"Failed to get playlist history: {e}")
            return {'error': str(e)}
    
    def get_actual_music(self, property_name: str, zone_name: str) -> Dict:
        """Get what's actually playing right now from SYB API"""
        
        if not self.api_available:
            return {
                'status': 'API not available',
                'playlist': 'Unknown',
                'track': 'Unknown',
                'volume': 'Unknown'
            }
        
        try:
            # Find the zone
            zones = self.syb_api.find_venue_zones(property_name)
            target_zone = None
            
            for zone in zones:
                if zone.get('name', '').lower() == zone_name.lower():
                    target_zone = zone
                    break
            
            if not target_zone:
                return {
                    'status': 'Zone not found',
                    'playlist': 'Unknown',
                    'track': 'Unknown'
                }
            
            zone_id = target_zone.get('id')
            
            # Get real-time status
            status = self.syb_api.get_zone_status(zone_id)
            now_playing = self.syb_api.get_now_playing(zone_id)
            
            actual = {
                'status': 'online' if target_zone.get('online') else 'offline',
                'playlist': now_playing.get('soundtrack', {}).get('name', 'Unknown'),
                'track': now_playing.get('track', {}).get('name', 'Unknown'),
                'artist': now_playing.get('track', {}).get('artists', [{}])[0].get('name', 'Unknown'),
                'zone_id': zone_id
            }
            
            # Get volume level (0-16 scale in SYB)
            if 'volume' in status:
                actual['volume_level'] = status.get('volume')  # This will be 0-16
            elif 'playbackSettings' in status:
                actual['volume_level'] = status.get('playbackSettings', {}).get('volume')
            
            return actual
            
        except Exception as e:
            logger.error(f"Failed to get actual music: {e}")
            return {
                'status': 'Error',
                'error': str(e)
            }
    
    def analyze_discrepancy(self, intended: Dict, actual: Dict) -> Dict:
        """Analyze the difference between intended and actual"""
        
        analysis = {
            'match': False,
            'issues': [],
            'recommendations': []
        }
        
        # Check if offline
        if actual.get('status') == 'offline':
            analysis['issues'].append('Zone is offline')
            analysis['recommendations'].append('Check network connection and restart zone')
            return analysis
        
        # Check playlist match
        intended_playlist = intended.get('playlist', '').lower()
        actual_playlist = actual.get('playlist', '').lower()
        
        if intended_playlist != 'unknown' and actual_playlist != 'unknown':
            if intended_playlist not in actual_playlist and actual_playlist not in intended_playlist:
                analysis['issues'].append(f"Wrong playlist: Playing '{actual.get('playlist')}' instead of '{intended.get('playlist')}'")
                analysis['recommendations'].append(f"Switch to '{intended.get('playlist')}' playlist")
        
        # Check volume if available (SYB uses 0-16 scale)
        if intended.get('volume_level') and actual.get('volume_level'):
            intended_vol = intended['volume_level']
            actual_vol = actual['volume_level']
            
            # Consider significant if difference > 2 levels
            if abs(intended_vol - actual_vol) > 2:
                analysis['issues'].append(f"Volume mismatch: level {actual_vol} instead of {intended_vol}")
                analysis['recommendations'].append(f"Adjust volume to level {intended_vol}")
        
        # If no issues found
        if not analysis['issues']:
            analysis['match'] = True
            analysis['issues'].append('Everything matches the intended design')
        
        return analysis
    
    def generate_alert_message(self, check_result: Dict) -> str:
        """Generate a message for the design team if there's an issue"""
        
        if check_result['analysis']['match']:
            return None
        
        property_name = check_result['property']
        zone_name = check_result['zone']
        issues = check_result['analysis']['issues']
        recommendations = check_result['analysis']['recommendations']
        
        message = f"🚨 Music Discrepancy at {property_name} - {zone_name}\n\n"
        message += "Issues Found:\n"
        for issue in issues:
            message += f"• {issue}\n"
        
        message += "\nRecommended Actions:\n"
        for rec in recommendations:
            message += f"• {rec}\n"
        
        message += f"\nIntended: {check_result['intended'].get('playlist')}"
        if check_result['intended'].get('volume_level'):
            message += f" (volume level {check_result['intended']['volume_level']})"
        message += f"\nActual: {check_result['actual'].get('playlist')} ({check_result['actual'].get('status')})"
        if check_result['actual'].get('volume_level'):
            message += f" (volume level {check_result['actual']['volume_level']})"
        
        return message
    
    def change_playlist(self, zone_id: str, playlist_name: str) -> bool:
        """Try to change playlist via SYB API"""
        if not self.api_available:
            return False
        
        try:
            # This would need the actual API method to change playlist
            # For now, returning False means we can't fix it via API
            logger.info(f"Attempting to change playlist for zone {zone_id} to {playlist_name}")
            
            # TODO: Implement actual playlist change via API
            # query = """
            # mutation ChangePlaylist($zoneId: ID!, $soundtrackId: ID!) {
            #     updateZone(id: $zoneId, soundtrack: $soundtrackId) {
            #         id
            #         currentSoundtrack {
            #             name
            #         }
            #     }
            # }
            # """
            
            return False  # For now, can't change via API
            
        except Exception as e:
            logger.error(f"Failed to change playlist: {e}")
            return False
    
    def change_volume(self, zone_id: str, volume_level: int) -> bool:
        """Try to change volume via SYB API (0-16 scale)"""
        if not self.api_available:
            return False
        
        try:
            # Ensure volume is in valid range
            volume_level = max(0, min(16, volume_level))
            
            logger.info(f"Attempting to change volume for zone {zone_id} to level {volume_level}")
            
            # Use the working SYB API volume control
            from soundtrack_api import soundtrack_api
            result = soundtrack_api.set_volume(zone_id, volume_level)
            
            if result.get('success'):
                logger.info(f"Successfully set volume for zone {zone_id} to {volume_level}")
                return True
            else:
                logger.warning(f"Volume control failed for zone {zone_id}: {result.get('error')}")
                return False
            
        except Exception as e:
            logger.error(f"Failed to change volume: {e}")
            return False
    
    def notify_design_team(self, message: str) -> bool:
        """Send notification to design team via Google Chat"""
        try:
            # Try to import and use Google Chat
            from google_chat_client import chat_client
            
            if chat_client:
                # Send to design team channel
                chat_client.send_message(
                    space="spaces/AAQA3gAn8GY",  # BMAsia All space
                    message=message,
                    thread_key="music-issues"
                )
                logger.info("Notified design team via Google Chat")
                return True
        except Exception as e:
            logger.error(f"Failed to notify team: {e}")
        
        return False
    
    def quick_check_all_zones(self, property_name: str) -> Dict:
        """Quick check all zones for a property"""
        results = {}
        
        # Get zones from venue data
        venue = self.venue_reader.find_venue_by_name(property_name)
        if not venue:
            return {'error': 'Property not found'}
        
        zone_names = [z.strip() for z in venue.get('zone_names', '').split(',')]
        
        for zone_name in zone_names:
            results[zone_name] = self.check_zone_status(property_name, zone_name)
        
        return results


# Create singleton instance
music_monitor = MusicMonitor()


def check_music_status(property_name: str, zone_name: str) -> Dict:
    """Check if music is playing as intended"""
    return music_monitor.check_zone_status(property_name, zone_name)


def check_property(property_name: str) -> Dict:
    """Check all zones for a property"""
    return music_monitor.quick_check_all_zones(property_name)


# Test functionality
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "="*60)
    print("REAL-TIME MUSIC MONITOR")
    print("="*60)
    
    # Test checking a zone
    result = check_music_status("Hilton Pattaya", "Drift Bar")
    
    print(f"\nProperty: {result['property']}")
    print(f"Zone: {result['zone']}")
    print(f"\nIntended: {result['intended']}")
    print(f"Actual: {result['actual']}")
    print(f"\nAnalysis: {result['analysis']}")
    
    # Generate alert if needed
    alert = music_monitor.generate_alert_message(result)
    if alert:
        print("\n" + "="*60)
        print("ALERT MESSAGE FOR DESIGN TEAM:")
        print("="*60)
        print(alert)
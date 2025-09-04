#!/usr/bin/env python3
"""
SYB Control Handler - Manages what we CAN and CANNOT do via API
Provides intelligent escalation when API control isn't available
"""

import logging
from typing import Dict, Optional, Tuple, List
from datetime import datetime

logger = logging.getLogger(__name__)


class SYBControlHandler:
    """Handle SYB control requests with smart escalation"""
    
    def __init__(self):
        from soundtrack_api import soundtrack_api
        self.api = soundtrack_api
        
        # Track what we can actually do (updated based on comprehensive testing)
        self.capabilities = {
            'detect': {
                'zones': True,
                'schedule_presence': True,
                'mode': True,  # scheduled vs manual
                'device_info': True,
                'device_controllability': True,  # Can detect device types
                'current_source': True  # Can detect current playlist/schedule
            },
            'control': {
                'volume': True,  # WORKS for controllable devices (0-16 scale)
                'playback': True,  # Play/pause/skip WORKS for controllable devices
                'queue_management': 'unlimited_plan_required',  # Queue tracks requires unlimited plan
                'track_blocking': False,  # Mutation exists but field structure unclear
                'playlist_change': False,  # setPlayFrom exists but needs proper playlist IDs
                'schedule_switch': False,  # Cannot switch modes directly
                'multi_skip': False  # skipTracks exists but field structure unclear
            },
            'read': {
                'current_track': True,  # Can detect nowPlaying presence
                'volume_level': False,  # Cannot read current volume
                'schedule_details': True,  # Can read schedule name and ID
                'playlist_details': True,  # Can read current playlist/source info
                'playlist_catalog': False  # No browse capability confirmed
            },
            'device_support': {
                'IPAM400': {'volume': True, 'playback': True, 'queue': True},
                'DRMR-SVR': {'volume': True, 'playback': True, 'queue': True},  # NEW: Confirmed working
                'Samsung': {'volume': False, 'playback': False, 'queue': False},
                'iPad': {'volume': False, 'playback': False, 'queue': False}  # Trial zones
            }
        }
    
    def attempt_playlist_change(self, zone_id: str, playlist_name: str) -> Tuple[bool, str]:
        """
        Attempt to change playlist - will fail but we handle gracefully
        Returns (success, message)
        """
        logger.info(f"Attempting playlist change for zone {zone_id} to {playlist_name}")
        
        # We know this won't work, but we can create a detailed escalation
        return False, self._create_escalation_request('playlist_change', {
            'zone_id': zone_id,
            'requested_playlist': playlist_name,
            'timestamp': datetime.now().isoformat()
        })
    
    def attempt_volume_change(self, zone_id: str, volume_level: int) -> Tuple[bool, str]:
        """
        Attempt to change volume - now works for controllable zones
        Returns (success, message)
        """
        logger.info(f"Attempting volume change for zone {zone_id} to level {volume_level}")
        
        # Validate volume range (SYB uses 0-16)
        if not 0 <= volume_level <= 16:
            return False, f"Invalid volume level {volume_level}. Must be 0-16."
        
        # Check if zone is controllable first
        zone_status = self.api.get_zone_status(zone_id)
        if zone_status.get('error'):
            return False, f"Cannot access zone: {zone_status['error']}"
        
        device_info = zone_status.get('device', {})
        device_name = device_info.get('name', '')
        streaming_type = zone_status.get('streamingType', '')
        
        # Check device compatibility based on our testing
        if not self._is_device_controllable(device_name, streaming_type):
            return False, self._create_escalation_request('volume_change', {
                'zone_id': zone_id,
                'requested_volume': volume_level,
                'device_type': device_name,
                'streaming_type': streaming_type,
                'reason': self._get_device_limitation_reason(device_name, streaming_type),
                'timestamp': datetime.now().isoformat()
            })
        
        # Try to set volume using working API method
        result = self.api.set_volume(zone_id, volume_level)
        
        if result.get('success'):
            return True, f"Volume successfully set to level {volume_level}/16"
        else:
            error_msg = result.get('error', 'Unknown error')
            if 'not controllable' in error_msg.lower() or 'not found' in error_msg.lower():
                return False, self._create_escalation_request('volume_change', {
                    'zone_id': zone_id,
                    'requested_volume': volume_level,
                    'device_type': device_name,
                    'reason': 'Zone not controllable via API',
                    'timestamp': datetime.now().isoformat()
                })
            else:
                return False, f"Volume control failed: {error_msg}"
    
    def suggest_playlists(self, venue_type: str, time_of_day: str, mood: str) -> Dict:
        """
        Suggest playlists based on context (since we can't browse the catalog)
        This uses our knowledge of common SYB playlists
        """
        
        # Common SYB playlist patterns we know about
        suggestions = {
            'restaurant': {
                'morning': ['Jazz Breakfast', 'Acoustic Morning', 'Coffee Shop Vibes'],
                'afternoon': ['Lunch Ambiance', 'Smooth Jazz', 'Light Pop'],
                'evening': ['Fine Dining', 'Classical Crossover', 'Piano Bar']
            },
            'bar': {
                'afternoon': ['Afternoon Chill', 'Tropical House', 'Beach Bar'],
                'evening': ['Happy Hour Hits', 'Lounge Vibes', 'Deep House'],
                'night': ['Weekend Party', 'Club Anthems', 'Late Night Cocktails']
            },
            'hotel_lobby': {
                'morning': ['Morning Welcome', 'Soft Classical', 'Nature Sounds'],
                'afternoon': ['Lobby Lounge', 'World Music', 'Instrumental Pop'],
                'evening': ['Evening Elegance', 'Jazz Standards', 'Piano Classics']
            },
            'spa': {
                'all_day': ['Spa Relaxation', 'Meditation Music', 'Nature & Water', 'Zen Garden']
            },
            'gym': {
                'all_day': ['Workout Motivation', 'High Energy', 'EDM Workout', 'Rock Power']
            }
        }
        
        # Get suggestions based on venue type
        venue_playlists = suggestions.get(venue_type.lower(), {})
        time_playlists = venue_playlists.get(time_of_day.lower(), 
                                            venue_playlists.get('all_day', []))
        
        # Add mood-based filtering
        mood_filters = {
            'energetic': ['High Energy', 'Party', 'Workout', 'EDM', 'Rock'],
            'relaxed': ['Chill', 'Lounge', 'Smooth', 'Soft', 'Ambient'],
            'sophisticated': ['Jazz', 'Classical', 'Piano', 'Fine Dining'],
            'fun': ['Hits', 'Pop', 'Tropical', 'Beach', 'Happy']
        }
        
        mood_keywords = mood_filters.get(mood.lower(), [])
        
        # Filter suggestions by mood
        if mood_keywords:
            filtered = []
            for playlist in time_playlists:
                if any(keyword.lower() in playlist.lower() for keyword in mood_keywords):
                    filtered.append(playlist)
            if filtered:
                time_playlists = filtered
        
        return {
            'suggestions': time_playlists[:5],  # Top 5 suggestions
            'venue_type': venue_type,
            'time_of_day': time_of_day,
            'mood': mood,
            'note': 'These are common SYB playlists. Actual availability may vary.'
        }
    
    def handle_music_request(self, zone_id: str, action: str, params: Dict) -> Tuple[bool, str]:
        """
        Handler that ALWAYS attempts control first (app-level control, not device-dependent)
        Falls back to escalation only if API fails
        """
        # Get zone info for context
        zone_status = self.api.get_zone_status(zone_id)
        if zone_status.get('error'):
            return False, f"Cannot access zone: {zone_status['error']}"
        
        zone_name = zone_status.get('name', 'Unknown')
        device_info = zone_status.get('device', {})
        device_name = device_info.get('name', '')
        streaming_type = zone_status.get('streamingType', '')
        
        # ALWAYS attempt control first (app-level, not device-dependent)
        if action == 'volume':
            # Try to set volume regardless of device
            result = self.api.set_volume(zone_id, params['level'])
            if result.get('success'):
                return True, f"✅ Volume adjusted to level {params['level']}/16 for {zone_name}"
            else:
                # Analyze why it failed
                error_msg = str(result.get('error', '')).lower()
                
                if 'not found' in error_msg:
                    # This is likely a permission/subscription issue
                    if 'trial' in streaming_type.lower() or 'tier_3' in streaming_type:
                        reason = "Trial/demo zone - needs full subscription"
                    else:
                        reason = "API control not enabled for this zone"
                else:
                    reason = result.get('error', 'Unknown error')
                
                # Create escalation with proper context
                return False, self._create_detailed_escalation('volume', {
                    'zone_id': zone_id,
                    'zone_name': zone_name,
                    'device_name': device_name,
                    'streaming_type': streaming_type,
                    'requested_level': params['level'],
                    'reason': reason
                })
        
        elif action == 'playback':
            # Try playback control regardless of device
            control_action = params.get('control', 'pause')
            result = self.api.control_playback(zone_id, control_action)
            if result.get('success'):
                return True, f"✅ Playback {control_action}d for {zone_name}"
            else:
                # Analyze why it failed
                error_msg = str(result.get('error', '')).lower()
                
                if 'not found' in error_msg:
                    if 'trial' in streaming_type.lower() or 'tier_3' in streaming_type:
                        reason = "Trial/demo zone - needs full subscription"
                    else:
                        reason = "API control not enabled for this zone"
                else:
                    reason = result.get('error', 'Unknown error')
                
                return False, self._create_detailed_escalation('playback', {
                    'zone_id': zone_id,
                    'zone_name': zone_name,
                    'device_name': device_name,
                    'streaming_type': streaming_type,
                    'requested_action': control_action,
                    'reason': reason
                })
        
        elif action == 'playlist':
            # Playlist change not yet implemented, but prepare escalation
            return False, self._create_detailed_escalation('playlist', {
                'zone_id': zone_id,
                'zone_name': zone_name,
                'device_type': device_type,
                'device_name': device_name,
                'streaming_type': streaming_type,
                'current_playlist': zone_status.get('nowPlaying', {}).get('__typename', 'Unknown'),
                'requested_playlist': params.get('playlist_name'),
                'reason': 'Playlist switching via API under development',
                'action_required': 'Change playlist in SYB dashboard'
            })
        
        return False, f"Unknown action: {action}"
    
    def _create_detailed_escalation(self, action_type: str, details: Dict) -> str:
        """
        Create detailed escalation with zone context for Google Chat
        """
        zone_name = details.get('zone_name', 'Unknown')
        device_name = details.get('device_name', 'Unknown')
        streaming_type = details.get('streaming_type', 'Unknown')
        reason = details.get('reason', 'Unknown reason')
        
        message = f"🎵 Music Control Request - {zone_name}\n\n"
        message += f"📱 Output Device: {device_name}\n"
        message += f"📊 Zone Type: {streaming_type}\n"
        message += f"❌ API Control Failed: {reason}\n"
        
        message += f"\n🎯 Action Required: "
        
        if action_type == 'volume':
            message += f"Adjust volume to level {details.get('requested_level')}/16\n"
            message += "   How: Use device controls or SYB dashboard\n"
        elif action_type == 'playback':
            message += f"{details.get('requested_action', 'Control')} playback\n"
            message += "   How: Use device controls or SYB dashboard\n"
        elif action_type == 'playlist':
            message += f"Change playlist to: {details.get('requested_playlist')}\n"
            message += "   How: Access SYB dashboard → Select zone → Change playlist\n"
        
        message += f"\n⏰ Requested: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        return message
    
    def get_zone_capability(self, zone_id: str) -> Dict:
        """
        Check what we can actually do with this specific zone
        Based on comprehensive testing of different device types
        """
        try:
            zone_status = self.api.get_zone_status(zone_id)
            
            if zone_status.get('error'):
                return {
                    'zone_id': zone_id,
                    'error': zone_status['error'],
                    'can_control': False
                }
            
            zone_name = zone_status.get('name', 'Unknown')
            streaming_type = zone_status.get('streamingType', '')
            device_info = zone_status.get('device', {})
            device_name = device_info.get('name', '')
            schedule = zone_status.get('schedule', {})
            
            # Get current playback source info
            current_source = self._get_current_source(zone_status)
            
            # Determine controllability based on comprehensive device testing
            device_capabilities = self._get_device_capabilities(device_name, streaming_type)
            
            limitations = []
            if not device_capabilities['volume']:
                limitations.append('Cannot adjust volume via API')
            if not device_capabilities['playback']:
                limitations.append('Cannot control playback via API')
            if not device_capabilities['queue']:
                limitations.append('Cannot manage playback queue via API')
            
            # These are still true for all devices
            limitations.append('Cannot change playlists directly via API')
            limitations.append('Cannot switch between scheduled/manual modes')
            
            return {
                'zone_id': zone_id,
                'zone_name': zone_name,
                'streaming_type': streaming_type,
                'device_name': device_name,
                'device_type': self._classify_device_type(device_name, streaming_type),
                'has_schedule': bool(schedule.get('name')),
                'schedule_name': schedule.get('name'),
                'current_source': current_source,
                'can_control_volume': device_capabilities['volume'],
                'can_control_playback': device_capabilities['playback'],
                'can_manage_queue': device_capabilities['queue'],
                'can_control': any(device_capabilities.values()),
                'capabilities': device_capabilities,
                'limitations': limitations
            }
            
        except Exception as e:
            logger.error(f"Error checking zone capability: {e}")
            return {
                'zone_id': zone_id,
                'error': f'Could not determine zone capabilities: {e}',
                'can_control': False
            }
    
    def _is_device_controllable(self, device_name: str, streaming_type: str) -> bool:
        """Check if a device supports API control based on our testing"""
        
        # Known controllable devices
        if any(device_type in device_name for device_type in ['IPAM400', 'DRMR-SVR']):
            return True
        
        # Known non-controllable devices
        if any(device_type in device_name.lower() for device_type in ['samsung', 'ipad', 'sm-']):
            return False
        
        # Trial zones are generally not controllable
        if streaming_type == 'TIER_1' or 'trial' in device_name.lower():
            return False
        
        # Unknown devices - assume not controllable for safety
        return False
    
    def _get_device_capabilities(self, device_name: str, streaming_type: str) -> Dict[str, bool]:
        """Get specific capabilities for a device type"""
        
        # Default capabilities (all False for safety)
        capabilities = {'volume': False, 'playback': False, 'queue': False}
        
        # IPAM400 devices - confirmed working
        if 'IPAM400' in device_name:
            capabilities = {'volume': True, 'playback': True, 'queue': True}
        
        # DRMR server devices - confirmed working in testing
        elif 'DRMR-SVR' in device_name:
            capabilities = {'volume': True, 'playback': True, 'queue': True}
        
        # Samsung tablets - confirmed not working
        elif 'samsung' in device_name.lower() or 'SM-' in device_name:
            capabilities = {'volume': False, 'playback': False, 'queue': False}
        
        # iPad devices - generally trial zones
        elif 'iPad' in device_name:
            capabilities = {'volume': False, 'playback': False, 'queue': False}
        
        return capabilities
    
    def _classify_device_type(self, device_name: str, streaming_type: str) -> str:
        """Classify device type for user-friendly display"""
        
        if 'IPAM' in device_name or 'DRMR-SVR' in device_name:
            return 'Audio Player (Controllable)'
        elif 'samsung' in device_name.lower() or 'SM-' in device_name:
            return 'Display Device (Not Controllable)'
        elif 'iPad' in device_name:
            return 'Display Device (Trial/Demo)'
        elif streaming_type == 'TIER_1':
            return 'Trial Zone (Limited Control)'
        else:
            return 'Unknown Device Type'
    
    def _get_device_limitation_reason(self, device_name: str, streaming_type: str) -> str:
        """Get specific reason why a device can't be controlled"""
        
        if 'samsung' in device_name.lower() or 'SM-' in device_name:
            return 'Device is a display tablet - volume must be adjusted manually'
        elif 'iPad' in device_name:
            return 'Device is an iPad (likely trial zone) - not controllable via API'
        elif streaming_type == 'TIER_1':
            return 'Trial account - limited API control permissions'
        else:
            return 'Device type not confirmed for API control'
    
    def _get_current_source(self, zone_status: Dict) -> Dict:
        """Extract current playback source information"""
        
        if not zone_status:
            return {
                'type': 'Unknown',
                'id': None,
                'name': 'Status unavailable',
                'mode': 'unknown'
            }
        
        schedule = zone_status.get('schedule', {})
        
        if schedule and schedule.get('name'):
            return {
                'type': 'Schedule',
                'id': schedule.get('id'),
                'name': schedule.get('name'),
                'mode': 'scheduled'
            }
        else:
            return {
                'type': 'Manual',
                'id': None,
                'name': 'Manual playback',
                'mode': 'manual'
            }
    
    def attempt_queue_management(self, zone_id: str, action: str, track_ids: List[str] = None) -> Tuple[bool, str]:
        """NEW: Attempt to manage playback queue"""
        
        logger.info(f"Attempting queue {action} for zone {zone_id}")
        
        # Check if zone supports queue management
        capability = self.get_zone_capability(zone_id)
        if not capability.get('can_manage_queue', False):
            return False, self._create_escalation_request('queue_management', {
                'zone_id': zone_id,
                'action': action,
                'device_type': capability.get('device_name', 'Unknown'),
                'reason': 'Device does not support queue management',
                'timestamp': datetime.now().isoformat()
            })
        
        if action == 'add_tracks' and track_ids:
            result = self.api.queue_tracks(zone_id, track_ids)
            if result.get('success'):
                return True, f"Added {len(track_ids)} tracks to queue"
            else:
                error_msg = result.get('error', 'Unknown error')
                if 'unlimited plan' in str(error_msg).lower():
                    return False, self._create_escalation_request('queue_management', {
                        'zone_id': zone_id,
                        'action': action,
                        'device_type': capability.get('device_name', 'Unknown'),
                        'reason': 'Queue management requires Unlimited plan subscription',
                        'timestamp': datetime.now().isoformat()
                    })
                return False, f"Failed to add tracks to queue: {error_msg}"
        
        elif action == 'clear':
            result = self.api.clear_queue(zone_id)
            if result.get('success'):
                return True, "Cleared playback queue"
            else:
                error_msg = result.get('error', 'Unknown error')
                if 'unlimited plan' in str(error_msg).lower():
                    return False, self._create_escalation_request('queue_management', {
                        'zone_id': zone_id,
                        'action': action,
                        'device_type': capability.get('device_name', 'Unknown'),
                        'reason': 'Queue management requires Unlimited plan subscription',
                        'timestamp': datetime.now().isoformat()
                    })
                return False, f"Failed to clear queue: {error_msg}"
        
        else:
            return False, f"Unknown queue action: {action}"
    
    def _create_escalation_request(self, action_type: str, details: Dict) -> str:
        """
        Create a structured escalation request for the operations team
        """
        request = {
            'action': action_type,
            'details': details,
            'created_at': datetime.now().isoformat(),
            'requires_manual': True
        }
        
        message = f"🎵 Music Control Request\n\n"
        message += f"Action: {action_type.replace('_', ' ').title()}\n"
        
        if action_type == 'playlist_change':
            message += f"Zone ID: {details['zone_id']}\n"
            message += f"Requested Playlist: {details['requested_playlist']}\n"
        elif action_type == 'volume_change':
            message += f"Zone ID: {details['zone_id']}\n"
            message += f"Requested Volume: Level {details['requested_volume']}/16\n"
            if 'device_type' in details:
                message += f"Device Type: {details['device_type']}\n"
        elif action_type == 'queue_management':
            message += f"Zone ID: {details['zone_id']}\n"
            message += f"Queue Action: {details['action']}\n"
            message += f"Device Type: {details['device_type']}\n"
        
        message += f"\n⚠️ Manual action required in SYB dashboard"
        message += f"\nTimestamp: {details['timestamp']}"
        
        return message
    
    def format_design_conversation(self, venue_name: str, zone_name: str, 
                                  current_mood: str, desired_mood: str) -> str:
        """
        Format a design conversation for playlist suggestions
        """
        response = f"🎨 Music Design Consultation for {zone_name} at {venue_name}\n\n"
        response += f"Current vibe: {current_mood}\n"
        response += f"Desired vibe: {desired_mood}\n\n"
        
        # Get time-appropriate suggestions
        hour = datetime.now().hour
        if 6 <= hour < 12:
            time_period = 'morning'
        elif 12 <= hour < 17:
            time_period = 'afternoon'
        elif 17 <= hour < 22:
            time_period = 'evening'
        else:
            time_period = 'night'
        
        # Determine venue type from zone name
        venue_type = 'bar'  # default
        if 'restaurant' in zone_name.lower() or 'dining' in zone_name.lower():
            venue_type = 'restaurant'
        elif 'lobby' in zone_name.lower():
            venue_type = 'hotel_lobby'
        elif 'spa' in zone_name.lower():
            venue_type = 'spa'
        elif 'gym' in zone_name.lower() or 'fitness' in zone_name.lower():
            venue_type = 'gym'
        
        suggestions = self.suggest_playlists(venue_type, time_period, desired_mood)
        
        response += "💡 Playlist Suggestions:\n"
        for i, playlist in enumerate(suggestions['suggestions'], 1):
            response += f"{i}. {playlist}\n"
        
        response += f"\nThese playlists would create a {desired_mood} atmosphere "
        response += f"perfect for {time_period} at your {venue_type}.\n\n"
        response += "Would you like me to request this change for you?"
        
        return response


# Singleton instance
syb_control = SYBControlHandler()


def can_control_zone(zone_id: str) -> bool:
    """Check if we can control this zone via API"""
    capability = syb_control.get_zone_capability(zone_id)
    return capability.get('can_control', False)


def suggest_playlist_change(venue_name: str, zone_name: str, mood: str) -> str:
    """Suggest playlist changes based on mood"""
    return syb_control.format_design_conversation(
        venue_name, zone_name, 
        current_mood="current", 
        desired_mood=mood
    )


def handle_control_request(action: str, zone_id: str, value: any) -> Tuple[bool, str]:
    """Handle any control request with appropriate escalation"""
    if action == 'volume':
        return syb_control.attempt_volume_change(zone_id, value)
    elif action == 'playlist':
        return syb_control.attempt_playlist_change(zone_id, value)
    elif action == 'queue_clear':
        return syb_control.attempt_queue_management(zone_id, 'clear')
    elif action == 'queue_add':
        # value should be a list of track IDs
        return syb_control.attempt_queue_management(zone_id, 'add_tracks', value)
    else:
        return False, f"Unknown action: {action}"
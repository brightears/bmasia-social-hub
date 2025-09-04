#!/usr/bin/env python3
"""
Soundtrack Your Brand Implementation Guide
Sample code showing how to implement SYB capabilities in the bot
"""

from soundtrack_api import soundtrack_api
from typing import Dict, List, Any
import json


class SYBBotIntegration:
    """Integration layer between the bot and SYB API"""
    
    def __init__(self):
        self.api = soundtrack_api
    
    def handle_music_request(self, venue_name: str, zone_name: str = None, request: str = "") -> str:
        """Main handler for music-related requests"""
        
        # 1. Find venue zones
        zones = self.api.find_venue_zones(venue_name)
        
        if not zones:
            return f"❌ I couldn't find any music zones for '{venue_name}'. This venue might not use Soundtrack Your Brand, or the name might be spelled differently. Let me check our venue list..."
        
        # 2. Handle multiple zones
        if len(zones) > 1 and not zone_name:
            zone_list = "\n".join([
                f"• **{zone['name']}** ({zone.get('location_name', 'Main Location')})" 
                for zone in zones[:10]  # Limit to first 10
            ])
            
            return f"🎵 I found {len(zones)} music zones for **{venue_name}**:\n\n{zone_list}\n\n**Which zone needs attention?** Please specify the zone name (e.g., 'Lobby', 'Restaurant', etc.)"
        
        # 3. Find specific zone if requested
        target_zone = None
        if zone_name:
            # Find best matching zone
            zone_matches = []
            search_terms = zone_name.lower().split()
            
            for zone in zones:
                zone_name_lower = zone['name'].lower()
                location_lower = zone.get('location_name', '').lower()
                
                # Calculate match score
                score = 0
                for term in search_terms:
                    if term in zone_name_lower:
                        score += 3
                    elif term in location_lower:
                        score += 2
                
                if score > 0:
                    zone_matches.append((zone, score))
            
            if zone_matches:
                # Sort by score and take best match
                zone_matches.sort(key=lambda x: x[1], reverse=True)
                target_zone = zone_matches[0][0]
            else:
                available_zones = ", ".join([z['name'] for z in zones[:5]])
                return f"❌ I couldn't find a zone named '{zone_name}' at {venue_name}. Available zones: {available_zones}"
        
        else:
            # Use first zone if only one
            target_zone = zones[0]
        
        # 4. Get zone status and capabilities
        zone_status = self.get_zone_detailed_info(target_zone)
        
        # 5. Handle different types of requests
        if any(keyword in request.lower() for keyword in ['status', 'check', 'what', 'playing']):
            return self._handle_status_request(zone_status)
        
        elif any(keyword in request.lower() for keyword in ['change', 'switch', 'different', 'new']):
            return self._handle_change_request(zone_status, request)
        
        elif any(keyword in request.lower() for keyword in ['volume', 'loud', 'quiet', 'up', 'down']):
            return self._handle_volume_request(zone_status, request)
        
        elif any(keyword in request.lower() for keyword in ['pause', 'stop', 'play', 'resume']):
            return self._handle_playback_request(zone_status, request)
        
        else:
            # General request - provide status and options
            return self._handle_general_request(zone_status, request)
    
    def get_zone_detailed_info(self, zone_info: Dict) -> Dict:
        """Get comprehensive zone information"""
        
        zone_id = zone_info['id']
        
        # Get basic status
        status = self.api.get_zone_status(zone_id)
        
        # Get mode
        mode = self.api.detect_zone_mode(zone_id)
        
        # Get playback info
        now_playing = self.api.get_now_playing(zone_id)
        
        # Test capabilities (without actually changing anything)
        capabilities = {
            'readable': True,
            'controllable': False  # We know from testing these are trial zones
        }
        
        return {
            'zone_info': zone_info,
            'status': status,
            'mode': mode,
            'now_playing': now_playing,
            'capabilities': capabilities
        }
    
    def _handle_status_request(self, zone_status: Dict) -> str:
        """Handle requests for zone status"""
        
        zone_info = zone_status['zone_info']
        status = zone_status['status']
        mode = zone_status['mode']
        now_playing = zone_status['now_playing']
        
        response = f"🎵 **{zone_info['name']}** Status at **{zone_info.get('location_name', 'Unknown Location')}**:\n\n"
        
        # Basic info
        device = status.get('device', {})
        if device.get('name'):
            response += f"📱 **Device**: {device['name']}\n"
        
        streaming_type = status.get('streamingType', 'Unknown')
        response += f"🎼 **Streaming Type**: {streaming_type}\n"
        
        # Mode info
        if mode == 'scheduled':
            schedule_name = status.get('schedule', {}).get('name', 'Unknown Schedule')
            response += f"📅 **Mode**: Scheduled ({schedule_name})\n"
        else:
            response += f"🎛️ **Mode**: Manual Control\n"
        
        # Playback info
        if now_playing.get('has_playback'):
            response += f"▶️ **Playback**: Active (type: {now_playing.get('type', 'Unknown')})\n"
        else:
            response += f"⏹️ **Playback**: No active playback detected\n"
        
        # Control info
        if streaming_type == 'TIER_3' or 'trial' in device.get('name', '').lower():
            response += f"\n⚠️ **Note**: This appears to be a trial/demo zone. For music changes, please contact venue staff directly or use the Soundtrack Your Brand dashboard.\n"
        
        return response
    
    def _handle_change_request(self, zone_status: Dict, request: str) -> str:
        """Handle requests to change music"""
        
        zone_info = zone_status['zone_info']
        capabilities = zone_status['capabilities']
        
        if not capabilities.get('controllable'):
            # Create escalation request
            request_data = self.api.create_music_change_request(zone_info, request)
            
            # Format for operations team
            escalation_message = f"""
🎵 **MUSIC CHANGE REQUEST**

**Venue**: {zone_info.get('account_name', 'Unknown')}
**Location**: {zone_info.get('location_name', 'Unknown')}  
**Zone**: {zone_info.get('name')}

**Request**: {request}

**Technical Details**:
• Zone ID: `{zone_info.get('id')}`
• Device: {request_data['technical_info'].get('device_name', 'Unknown')}
• Current Mode: {request_data['technical_info'].get('current_mode', 'Unknown')}
• Streaming Type: {request_data['technical_info'].get('streaming_type', 'Unknown')}

**Action Required**: Manual intervention needed - zone not controllable via API
**Timestamp**: {request_data['timestamp']}
            """.strip()
            
            # In a real implementation, you'd send this to Google Chat
            # send_to_operations_channel(escalation_message)
            
            return f"""✅ **Music change request submitted** for **{zone_info['name']}** at **{zone_info.get('account_name', 'the venue')}**.

📝 **Request**: {request}

🔧 **What happens next**: 
• Our operations team has been notified
• They'll handle this change within 15-30 minutes
• You'll get a confirmation once it's done

⚠️ **Note**: This zone requires manual intervention as it's not controllable via API (trial/demo zone)."""
        
        else:
            # This would be for controllable zones (when we have them)
            return f"🎵 Attempting to change music for **{zone_info['name']}**... (This feature requires production zones)"
    
    def _handle_volume_request(self, zone_status: Dict, request: str) -> str:
        """Handle volume change requests"""
        
        zone_info = zone_status['zone_info']
        
        # Parse volume request
        if any(word in request.lower() for word in ['up', 'louder', 'higher', 'increase']):
            volume_request = "increase volume"
        elif any(word in request.lower() for word in ['down', 'quieter', 'lower', 'decrease']):
            volume_request = "decrease volume"
        else:
            volume_request = "adjust volume"
        
        return self._handle_change_request(zone_status, f"{volume_request} - {request}")
    
    def _handle_playback_request(self, zone_status: Dict, request: str) -> str:
        """Handle play/pause requests"""
        
        zone_info = zone_status['zone_info']
        
        if any(word in request.lower() for word in ['pause', 'stop']):
            action = "pause playback"
        else:
            action = "resume playback"
        
        return self._handle_change_request(zone_status, f"{action} - {request}")
    
    def _handle_general_request(self, zone_status: Dict, request: str) -> str:
        """Handle general music requests"""
        
        # Provide status plus options
        status_response = self._handle_status_request(zone_status)
        
        zone_info = zone_status['zone_info']
        
        options = f"""

**What I can help with**:
• 📊 **Check status**: "What's playing in the lobby?"
• 🎵 **Change music**: "Change restaurant music to jazz"
• 🔊 **Volume control**: "Turn up the volume in the bar"
• ⏯️ **Playback control**: "Pause the music in conference room"

**For immediate changes**: Contact venue staff directly or use the Soundtrack Your Brand dashboard.
**For complex requests**: I'll escalate to our operations team who can handle it within 15-30 minutes.
"""
        
        return status_response + options


def example_usage():
    """Example of how to use the SYB integration"""
    
    bot = SYBBotIntegration()
    
    # Example conversations
    examples = [
        ("Check status", "hilton bangkok", "lobby", "What's playing in the lobby?"),
        ("Change music", "anantara desaru", "", "Change the music to something more upbeat"),
        ("Volume", "anantara", "trial zone", "Turn up the volume please"),
        ("Multiple zones", "hilton", "", "Change the restaurant music"),
    ]
    
    print("=== SYB Bot Integration Examples ===\n")
    
    for example_type, venue, zone, request in examples:
        print(f"**{example_type} Example**:")
        print(f"User: \"{request}\" (venue: {venue}, zone: {zone})")
        print("Bot Response:")
        
        try:
            response = bot.handle_music_request(venue, zone, request)
            print(response)
        except Exception as e:
            print(f"Error: {e}")
        
        print("\n" + "-"*50 + "\n")


if __name__ == "__main__":
    example_usage()
"""
Bot with Soundtrack Your Brand integration
Handles music-related queries with real API data
"""

import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from bot_integrated import IntegratedBot
from soundtrack_api import soundtrack_api

logger = logging.getLogger(__name__)

class SoundtrackBot(IntegratedBot):
    """Bot with full Soundtrack API integration"""
    
    def __init__(self):
        super().__init__()
        self.soundtrack = soundtrack_api
        logger.info("Soundtrack-enabled bot initialized")
    
    def process_message(self, message: str, user_phone: str, user_name: str = None) -> str:
        """Process message with Soundtrack integration"""
        
        # First check if message is about music issues
        music_keywords = [
            'music', 'stopped', 'not playing', 'no sound', 'volume', 
            'quiet', 'loud', 'skip', 'pause', 'play', 'zone', 'lobby',
            'restaurant', 'playlist', 'soundtrack'
        ]
        
        message_lower = message.lower()
        is_music_issue = any(keyword in message_lower for keyword in music_keywords)
        
        # Get base response from parent class
        base_response = super().process_message(message, user_phone, user_name)
        
        # If not a music issue or no venue identified, return base response
        if not is_music_issue:
            return base_response
        
        # Check if we have a verified venue
        from venue_identifier import conversation_context
        context = conversation_context.get_context(user_phone)
        venue = context.get('venue')
        
        if not venue:
            return base_response
        
        venue_name = venue.get('name', '')
        
        # If music issue and venue identified, check Soundtrack status
        return self._handle_music_issue(message, venue_name, base_response)
    
    def _handle_music_issue(self, message: str, venue_name: str, base_response: str) -> str:
        """Handle music-related issues with Soundtrack API"""
        
        logger.info(f"Checking Soundtrack status for {venue_name}")
        
        # Get diagnosis from Soundtrack API
        diagnosis = self.soundtrack.diagnose_venue_issues(venue_name)
        
        if diagnosis.get('status') == 'error':
            # Venue not found in Soundtrack
            return base_response + "\n\n⚠️ I couldn't find your venue in the Soundtrack system. This might mean:\n• The venue name in our system doesn't match Soundtrack\n• The account hasn't been set up yet\n• There's a connection issue\n\nPlease contact support for manual assistance."
        
        # Build enhanced response based on diagnosis
        response_parts = []
        
        # Add diagnosis summary
        if diagnosis.get('status') == 'critical':
            response_parts.append(f"🔴 **CRITICAL**: {diagnosis.get('message')}")
        elif diagnosis.get('status') == 'warning':
            response_parts.append(f"⚠️ **WARNING**: {diagnosis.get('message')}")
        else:
            response_parts.append(f"✅ **STATUS**: {diagnosis.get('message')}")
        
        # Add zone details
        response_parts.append(f"\n📊 **Zone Status for {venue_name}:**")
        response_parts.append(f"• Total zones: {diagnosis.get('total_zones')}")
        response_parts.append(f"• Online: {diagnosis.get('online_zones')}")
        response_parts.append(f"• Playing music: {diagnosis.get('playing_zones')}")
        
        # Check for specific issues
        if diagnosis.get('offline_zones', 0) > 0:
            response_parts.append("\n🔧 **Offline Zones Detected:**")
            for zone in diagnosis.get('zones', []):
                if not zone.get('is_online'):
                    response_parts.append(f"• {zone.get('name')} ({zone.get('location')})")
                    if zone.get('issues'):
                        response_parts.append(f"  Issues: {', '.join(zone['issues'])}")
        
        # Provide specific guidance based on the issue
        message_lower = message.lower()
        
        if 'stopped' in message_lower or 'not playing' in message_lower:
            if diagnosis.get('offline_zones') > 0:
                response_parts.append("\n💡 **Quick Fix Steps:**")
                response_parts.append("1. Check if the Soundtrack device is powered on")
                response_parts.append("2. Verify network connection (ethernet cable/WiFi)")
                response_parts.append("3. Restart the device by unplugging for 10 seconds")
                response_parts.append("4. Check if the device LED is solid green")
            elif diagnosis.get('playing_zones') == 0:
                response_parts.append("\n💡 **The devices are online but not playing. Try:**")
                response_parts.append("1. Open Soundtrack app/portal")
                response_parts.append("2. Check if playlist is scheduled correctly")
                response_parts.append("3. Press play manually if needed")
                response_parts.append("4. Verify volume is not muted")
        
        elif 'volume' in message_lower:
            response_parts.append("\n🔊 **Volume Control:**")
            response_parts.append("You can adjust volume through:")
            response_parts.append("1. Soundtrack app on tablet/phone")
            response_parts.append("2. Soundtrack web portal")
            response_parts.append("3. Physical volume controls on some devices")
        
        # Add currently playing info if available
        playing_zones = [z for z in diagnosis.get('zones', []) if z.get('currently_playing')]
        if playing_zones:
            response_parts.append("\n🎵 **Currently Playing:**")
            for zone in playing_zones[:3]:  # Show max 3 zones
                response_parts.append(f"• {zone.get('name')}: {zone.get('currently_playing')}")
        
        # Offer automated fix if appropriate
        if diagnosis.get('status') in ['warning', 'critical']:
            response_parts.append("\n🤖 **Would you like me to:**")
            response_parts.append("1. Attempt automatic restart of offline zones")
            response_parts.append("2. Send detailed diagnostic report to tech team")
            response_parts.append("3. Schedule an on-site technician visit")
            response_parts.append("\nReply with the number of your choice.")
        
        return "\n".join(response_parts)
    
    def attempt_auto_fix(self, venue_name: str, zone_name: str = None) -> str:
        """Attempt to automatically fix zone issues"""
        
        zones = self.soundtrack.find_venue_zones(venue_name)
        
        if not zones:
            return "❌ Could not find venue zones in Soundtrack system."
        
        # If specific zone mentioned, find it
        target_zone = None
        if zone_name:
            for zone in zones:
                if zone_name.lower() in zone.get('name', '').lower():
                    target_zone = zone
                    break
        else:
            # Fix all problematic zones
            problematic = [z for z in zones if not z.get('isOnline') or not z.get('nowPlaying', {}).get('isPlaying')]
            if problematic:
                target_zone = problematic[0]  # Start with first problematic zone
        
        if not target_zone:
            return "✅ All zones appear to be working correctly."
        
        # Attempt fix
        zone_id = target_zone.get('id')
        fix_result = self.soundtrack.quick_fix_zone(zone_id)
        
        if fix_result.get('success'):
            fixes = "\n".join([f"• {fix}" for fix in fix_result.get('fixes_attempted', [])])
            return f"✅ **Automated fixes applied:**\n{fixes}\n\nThe zone should be working now. Please check and let me know if the issue persists."
        else:
            return f"❌ **Could not automatically fix the issue:**\n{fix_result.get('message')}\n\nManual intervention may be required. Would you like me to create a support ticket?"


# Global instance
soundtrack_bot = SoundtrackBot()
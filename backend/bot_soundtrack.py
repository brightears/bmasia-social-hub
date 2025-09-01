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
            'restaurant', 'playlist', 'soundtrack', 'active', 'status', 'running'
        ]
        
        message_lower = message.lower()
        is_music_issue = any(keyword in message_lower for keyword in music_keywords)
        
        # Check if user is asking about a specific zone
        import re
        zone_query = None
        
        # Look for patterns like "playing at Edge", "playing in Edge", etc.
        zone_patterns = [
            r'playing\s+(?:at|in)\s+([^\s?,]+)',  # playing at Edge
            r'currently\s+playing\s+(?:at|in)\s+([^\s?,]+)',  # currently playing at Edge
            r'what.*playing\s+(?:at|in)\s+([^\s?,]+)',  # what is playing at Edge
            r'zone\s+(?:called|named)?\s*["\']?([^"\'?,]+)["\']?',  # zone called 'Edge'
            r'area\s+(?:called|named)?\s*["\']?([^"\'?,]+)["\']?',  # area called 'Edge'
            r'(?:at|in)\s+([A-Z][a-z]+)(?:\?|$)',  # at Edge? (capitalized word at end)
        ]
        
        for pattern in zone_patterns:
            match = re.search(pattern, message_lower.replace('edge', 'Edge'))  # Preserve proper names
            if match:
                zone_query = match.group(1).strip()
                break
        
        # Fallback to simpler detection for known zones
        if not zone_query and is_music_issue:
            # Known zone names for Hilton Pattaya
            known_zones = ['edge', 'horizon', 'shore', 'drift bar']
            for zone in known_zones:
                if zone in message_lower:
                    zone_query = zone.title() if zone != 'drift bar' else 'Drift Bar'
                    break
        
        # Check if user is mentioning they're from a venue (but not asking about zones)
        venue_intro_patterns = ['i am from', "i'm from", 'calling from']
        is_venue_intro = any(pattern in message_lower for pattern in venue_intro_patterns) and not zone_query
        
        # Extract potential venue name if user is introducing their venue
        potential_venue = None
        if is_venue_intro:
            # Try to extract venue name (e.g., "I am from Hilton Bangkok")
            for pattern in venue_intro_patterns:
                if pattern in message_lower:
                    parts = message_lower.split(pattern)
                    if len(parts) > 1:
                        # Get the part after the pattern and clean it
                        venue_part = parts[1].strip()
                        # Remove common endings
                        venue_part = venue_part.replace('.', '').replace('!', '').replace('?', '')
                        # Remove "can you" or similar if present
                        if 'can you' in venue_part:
                            venue_part = venue_part.split('can you')[0].strip()
                        if ',' in venue_part:
                            venue_part = venue_part.split(',')[0].strip()
                        if venue_part and len(venue_part.split()) <= 4:  # Reasonable venue name length
                            potential_venue = venue_part
                            break
        
        # If user is asking about a specific zone, try to find it across all accounts
        if zone_query and is_music_issue:
            logger.info(f"User asking about specific zone: {zone_query}")
            return self._handle_zone_query(zone_query, user_phone, message)
        
        # If user mentioned a venue and is asking about music, handle it directly
        if potential_venue and is_music_issue:
            logger.info(f"User from {potential_venue} asking about music zones")
            # Store venue in context
            from venue_identifier import conversation_context
            conversation_context.update_context(user_phone, venue={'name': potential_venue.title()})
            # Check if already verified for this venue
            from email_verification import email_verifier
            if email_verifier.is_trusted_device(user_phone, potential_venue):
                return self._handle_music_query(message, potential_venue.title(), user_phone)
            else:
                # Direct to zone query without verification check for now
                return self._handle_music_query(message, potential_venue.title(), user_phone)
        
        # Check if user is already authenticated
        from venue_identifier import conversation_context
        
        # Check context for existing venue
        context = conversation_context.get_context(user_phone)
        venue = context.get('venue')
        
        # For users with identified venue asking about music, handle directly
        if venue and is_music_issue:
            venue_name = venue.get('name', '')
            
            # Check if this is a simple query (not requiring verification)
            if 'zone' in message_lower or 'active' in message_lower or 'status' in message_lower:
                # For zone queries, check if already verified
                from email_verification import email_verifier
                if email_verifier.is_trusted_device(user_phone, venue_name):
                    logger.info(f"Verified user {user_phone} querying zones for {venue_name}")
                    return self._handle_music_query(message, venue_name, user_phone)
        
        # Get base response from parent class (includes authentication if needed)
        base_response = super().process_message(message, user_phone, user_name)
        
        # If not a music issue or no venue identified, return base response
        if not is_music_issue:
            return base_response
        
        # Check if we have a verified venue after authentication
        context = conversation_context.get_context(user_phone)
        venue = context.get('venue')
        
        if not venue:
            return base_response
        
        venue_name = venue.get('name', '')
        
        # If music issue and venue identified, check Soundtrack status
        return self._handle_music_issue(message, venue_name, base_response)
    
    def _handle_zone_query(self, zone_name: str, user_phone: str, message: str) -> str:
        """Handle queries about specific zones across all accounts"""
        
        logger.info(f"Searching for zone '{zone_name}' across all accounts")
        
        # First check if user has a venue context
        from venue_identifier import conversation_context
        context = conversation_context.get_context(user_phone)
        venue = context.get('venue')
        
        try:
            matching_zones = []
            
            if venue:
                # User has identified venue - search specifically in that venue
                venue_name = venue.get('name', '')
                logger.info(f"User from {venue_name}, searching for zone '{zone_name}'")
                zones = self.soundtrack.find_venue_zones(venue_name)
                
                for zone in zones:
                    zone_zone_name = zone.get('name', '').lower()
                    # Check if zone name matches
                    if zone_name.lower() in zone_zone_name or zone_zone_name in zone_name.lower():
                        zone_info = {
                            'zone': zone,
                            'account_name': zone.get('account_name', venue_name),
                            'location_name': zone.get('location_name', venue_name),
                            'exact_match': zone_name.lower() == zone_zone_name
                        }
                        matching_zones.append(zone_info)
            else:
                # No venue context - search all accounts
                accounts = self.soundtrack.get_accounts()
                
                for account in accounts:
                    account_name = account.get('name', '')
                    for loc_edge in account.get('locations', {}).get('edges', []):
                        location = loc_edge['node']
                        location_name = location.get('name', '')
                        for zone_edge in location.get('soundZones', {}).get('edges', []):
                            zone = zone_edge['node']
                            zone_zone_name = zone.get('name', '').lower()
                            
                            # Check if zone name matches (case insensitive)
                            if zone_name.lower() in zone_zone_name or zone_zone_name in zone_name.lower():
                                zone_info = {
                                    'zone': zone,
                                    'account_name': account_name,
                                    'location_name': location_name,
                                    'exact_match': zone_name.lower() == zone_zone_name
                                }
                                matching_zones.append(zone_info)
            
            if not matching_zones:
                return f"I couldn't find any zone named '{zone_name}' in the Soundtrack system. Could you check the exact zone name?"
            
            # Sort by exact matches first
            matching_zones.sort(key=lambda x: x['exact_match'], reverse=True)
            
            if len(matching_zones) == 1:
                # Single match - provide detailed info
                zone_info = matching_zones[0]
                return self._format_zone_status(zone_info, message)
            else:
                # Multiple matches - show list
                response = f"I found {len(matching_zones)} zones matching '{zone_name}':\n\n"
                for i, zone_info in enumerate(matching_zones[:5], 1):
                    zone = zone_info['zone']
                    is_online = zone.get('isOnline') or zone.get('online', False)
                    status = "🟢 Online" if is_online else "🔴 Offline"
                    response += f"{i}. **{zone.get('name')}** - {status}\n"
                    response += f"   Location: {zone_info['location_name']}\n"
                    response += f"   Account: {zone_info['account_name']}\n\n"
                
                response += "Which zone would you like to check? Reply with the number."
                return response
                
        except Exception as e:
            logger.error(f"Error searching for zone '{zone_name}': {e}")
            return f"Sorry, I'm having trouble connecting to the Soundtrack system right now. Please try again in a moment."
    
    def _format_zone_status(self, zone_info: dict, original_message: str) -> str:
        """Format detailed status for a specific zone"""
        
        zone = zone_info['zone']
        zone_id = zone.get('id')
        zone_name = zone.get('name')
        is_online = zone.get('isOnline') or zone.get('online', False)
        is_paired = zone.get('isPaired', False)
        
        response = f"**Zone Status: {zone_name}**\n"
        response += f"Location: {zone_info['location_name']}\n"
        response += f"Account: {zone_info['account_name']}\n\n"
        
        if not is_paired:
            response += "🔴 **Status: Device Not Paired**\n"
            response += "The Soundtrack device needs to be paired. Please check the device setup.\n"
        elif not is_online:
            response += "🔴 **Status: Offline**\n"
            response += "The device is not connected. Please check:\n"
            response += "• Power connection\n• Network connectivity\n• Device LED status\n"
        else:
            response += "🟢 **Status: Online**\n"
            
            # Fetch current now playing data for this zone
            try:
                now_playing = self.soundtrack.get_now_playing(zone_id)
                
                if now_playing and now_playing.get('track'):
                    track = now_playing['track']
                    track_name = track.get('name', 'Unknown Track')
                    
                    # Handle artists array properly
                    artists_data = track.get('artists', [])
                    if isinstance(artists_data, list) and artists_data:
                        # If it's a list of dicts with 'name' field
                        if isinstance(artists_data[0], dict):
                            artist_names = ', '.join([a.get('name', '') for a in artists_data])
                        else:
                            # If it's a list of strings
                            artist_names = ', '.join(artists_data)
                    else:
                        artist_names = 'Unknown Artist'
                    
                    response += f"🎵 **Now Playing:**\n{track_name} by {artist_names}\n"
                    
                    if now_playing.get('startedAt'):
                        response += f"Started at: {now_playing['startedAt']}\n"
                else:
                    response += "⏸️ **Status: No music currently playing**\n"
                    
            except Exception as e:
                logger.error(f"Error fetching now playing for zone {zone_id}: {e}")
                response += "⚠️ **Status: Unable to fetch current track information**\n"
        
        return response
    
    def _handle_music_query(self, message: str, venue_name: str, user_phone: str) -> str:
        """Handle direct music queries from authenticated users"""
        
        message_lower = message.lower()
        
        # Check if asking about zones/status
        if 'zone' in message_lower and ('active' in message_lower or 'have' in message_lower or 'status' in message_lower):
            return self._list_venue_zones(venue_name, user_phone)
        
        # Otherwise handle as issue
        return self._handle_music_issue(message, venue_name, "")
    
    def _list_venue_zones(self, venue_name: str, user_phone: str) -> str:
        """List all zones for a venue"""
        
        logger.info(f"Listing zones for {venue_name}")
        
        # Find matching accounts
        try:
            matching_accounts = self.soundtrack.find_matching_accounts(venue_name)
        except Exception as e:
            logger.error(f"Error finding matching accounts: {e}")
            return f"Sorry, I'm having trouble connecting to the Soundtrack system right now. The error was: {str(e)[:100]}. Please try again in a moment."
        
        if not matching_accounts:
            return f"I couldn't find '{venue_name}' in the Soundtrack system. The account name might be different. Could you provide the exact name as shown in Soundtrack?"
        
        if len(matching_accounts) > 1:
            # Multiple matches - ask for clarification
            response = f"I found multiple Soundtrack accounts for Hilton:\n\n"
            for i, match in enumerate(matching_accounts[:3], 1):
                response += f"{i}. **{match['account_name']}**\n"
                response += f"   • {match['total_zones']} zones ({match['online_zones']} online)\n\n"
            
            response += "Which one is your venue? Reply with the number or full name."
            
            # Store in context
            from venue_identifier import conversation_context
            conversation_context.update_context(
                user_phone=user_phone,
                soundtrack_matches=matching_accounts,
                pending_action='list_zones'
            )
            
            return response
        
        # Single match - show zones
        account_name = matching_accounts[0]['account_name']
        zones = self.soundtrack.find_venue_zones(account_name)
        
        if not zones:
            return f"No zones found for {account_name}."
        
        response = f"**Music Zones for {account_name}:**\n\n"
        
        # Group zones by status
        online_zones = [z for z in zones if z.get('isOnline')]
        offline_zones = [z for z in zones if not z.get('isOnline')]
        
        if online_zones:
            response += f"✅ **Online Zones ({len(online_zones)}):**\n"
            for zone in online_zones[:10]:  # Limit to 10 to avoid too long message
                status = "🎵 Playing" if zone.get('nowPlaying', {}).get('isPlaying') else "⏸️ Paused"
                response += f"• {zone.get('name')} - {status}\n"
                if zone.get('nowPlaying', {}).get('track'):
                    track = zone['nowPlaying']['track']
                    response += f"  Now: {track.get('name')} by {', '.join(track.get('artists', ['Unknown']))}\n"
        
        if offline_zones:
            response += f"\n❌ **Offline Zones ({len(offline_zones)}):**\n"
            for zone in offline_zones[:5]:  # Show fewer offline zones
                response += f"• {zone.get('name')}\n"
        
        response += f"\n**Summary:** {len(online_zones)} online, {len(offline_zones)} offline"
        
        if offline_zones:
            response += "\n\nNeed help with the offline zones? Just let me know!"
        
        return response
    
    def _handle_music_issue(self, message: str, venue_name: str, base_response: str) -> str:
        """Handle music-related issues with Soundtrack API"""
        
        logger.info(f"Checking Soundtrack status for {venue_name}")
        
        # First try to find matching accounts
        try:
            matching_accounts = self.soundtrack.find_matching_accounts(venue_name)
        except Exception as e:
            logger.error(f"Error connecting to Soundtrack API: {e}")
            return f"Sorry, I'm having trouble connecting to the Soundtrack system right now. The error was: {str(e)[:100]}.\n\nThis could be due to:\n• API credentials not configured\n• Network connectivity issues\n• Soundtrack API being temporarily unavailable\n\nPlease try again in a moment, or contact support if the issue persists."
        
        if not matching_accounts:
            # No matches found
            return f"I couldn't find '{venue_name}' in the Soundtrack system. This might mean:\n• The venue name in Soundtrack is different\n• The account hasn't been set up yet\n\nCould you provide the exact account name as it appears in Soundtrack Your Brand?"
        
        elif len(matching_accounts) > 1:
            # Multiple matches found - ask for clarification
            response = f"I found multiple Soundtrack accounts that might be yours:\n\n"
            for i, match in enumerate(matching_accounts[:3], 1):  # Show max 3 matches
                response += f"{i}. **{match['account_name']}**\n"
                response += f"   • {match['total_zones']} zones ({match['online_zones']} online)\n\n"
            
            response += "Which account is yours? Reply with the number or the full account name."
            
            # Store matches in context for follow-up
            from venue_identifier import conversation_context
            conversation_context.update_context(
                user_phone=conversation_context.contexts.get(list(conversation_context.contexts.keys())[0], {}).get('user_phone', ''),
                soundtrack_matches=matching_accounts
            )
            
            return response
        
        # Single match found - use it
        account_name = matching_accounts[0]['account_name']
        logger.info(f"Found Soundtrack account: {account_name}")
        
        # Get diagnosis from Soundtrack API using the matched account name
        diagnosis = self.soundtrack.diagnose_venue_issues(account_name)
        
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
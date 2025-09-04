"""
Simplified Gemini bot - uses only venue_data.md and Soundtrack API
Email access is conditional (only when explicitly mentioned)
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
import google.generativeai as genai
from soundtrack_api import soundtrack_api
from venue_identifier import conversation_context
from venue_data_reader import (
    get_all_venues, find_venue, get_venue_pricing,
    venue_reader
)
try:
    from music_monitor import music_monitor, check_music_status
    MUSIC_MONITOR_AVAILABLE = True
except:
    MUSIC_MONITOR_AVAILABLE = False

try:
    from syb_control_handler import syb_control, suggest_playlist_change
    SYB_CONTROL_AVAILABLE = True
except:
    SYB_CONTROL_AVAILABLE = False

# Set up logging
logger = logging.getLogger(__name__)

class SimplifiedBot:
    """Simplified AI bot using only essential data sources"""
    
    def __init__(self):
        """Initialize bot with Gemini and core data sources"""
        # Configure Gemini
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        genai.configure(api_key=api_key)
        
        # Use gemini-2.5-flash for better performance
        model_name = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
        self.model = genai.GenerativeModel(model_name)
        
        # Core data sources only
        self.soundtrack = soundtrack_api
        self.venues = get_all_venues()
        
        # Optional email (lazy loaded)
        self.email_searcher = None
        
        # Track pending fixes for follow-up
        self.pending_fixes = {}
        
        logger.info(f"Simplified bot initialized with {len(self.venues)} venues")
    
    def _load_email_if_needed(self, message: str) -> bool:
        """Only load email integration if user mentions email"""
        email_keywords = ['email', 'sent you', 'wrote to you', 'mailed', 'gmail', 'message you']
        
        if any(keyword in message.lower() for keyword in email_keywords):
            if not self.email_searcher:
                try:
                    from smart_email_search import init_smart_search
                    self.email_searcher = init_smart_search()
                    logger.info("Email integration loaded on-demand")
                    return True
                except Exception as e:
                    logger.warning(f"Could not load email integration: {e}")
                    return False
            return True
        return False
    
    def process_message(self, message: str, user_phone: str, user_name: str = None, platform: str = "WhatsApp") -> str:
        """Process message using only essential data sources"""
        
        # Check if this is a response to a pending fix
        if self._is_confirmation_response(message, user_phone):
            return self._handle_fix_confirmation(message, user_phone)
        
        # Extract venue if mentioned
        venue_name = self._extract_venue_name(message)
        venue_data = None
        
        if venue_name:
            venue_data = find_venue(venue_name)
            if venue_data:
                conversation_context.update_context(user_phone, venue={'name': venue_data['property_name']})
                logger.info(f"Venue identified: {venue_data['property_name']}")
        
        # Get user context
        context = conversation_context.get_context(user_phone)
        current_venue = context.get('venue')
        
        message_lower = message.lower()
        
        # Handle pricing queries
        if any(word in message_lower for word in ['price', 'pricing', 'cost', 'rate', 'fee', 'charge', 'annual', 'monthly']):
            if venue_data or current_venue:
                venue_to_check = venue_data['property_name'] if venue_data else current_venue.get('name')
                pricing = get_venue_pricing(venue_to_check)
                
                if pricing:
                    return self._format_pricing_response(pricing)
                else:
                    return f"I couldn't find pricing information for {venue_to_check}. Let me connect you with our team for accurate details."
            else:
                return "Which property would you like pricing information for?"
        
        # Handle zone queries
        if any(phrase in message_lower for phrase in ['zone', 'music area', 'location']):
            if venue_data or current_venue:
                venue_to_check = venue_data['property_name'] if venue_data else current_venue.get('name')
                
                # Get from local data
                local_venue = find_venue(venue_to_check)
                if local_venue and local_venue.get('zone_names'):
                    zones = [z.strip() for z in local_venue['zone_names'].split(',')]
                    return f"{venue_to_check} has {len(zones)} zones: {', '.join(zones)}"
                
                # Try Soundtrack API
                zones = self.soundtrack.find_venue_zones(venue_to_check)
                if zones:
                    zone_names = [z.get('name', 'Unknown') for z in zones]
                    return f"{venue_to_check} has {len(zones)} zones: {', '.join(zone_names)}"
                
                return f"I couldn't find zone information for {venue_to_check}."
        
        # Handle contact queries
        if any(word in message_lower for word in ['contact', 'email', 'phone', 'who', 'manager']):
            if venue_data or current_venue:
                venue_to_check = venue_data['property_name'] if venue_data else current_venue.get('name')
                
                # Check for specific role
                role = None
                if 'it' in message_lower or 'tech' in message_lower:
                    role = 'IT'
                elif 'general manager' in message_lower:
                    role = 'General Manager'
                
                contacts = venue_reader.get_venue_contacts(venue_to_check, role)
                if contacts:
                    return self._format_contacts_response(venue_to_check, contacts)
        
        # Handle music/playlist queries with REAL-TIME checking
        if any(word in message_lower for word in ['music', 'playing', 'playlist', 'song', 'wrong music', 'should be', 'schedule', 'design', 'pause', 'stop', 'play', 'skip']):
            if MUSIC_MONITOR_AVAILABLE and (venue_data or current_venue):
                venue_to_check = venue_data['property_name'] if venue_data else current_venue.get('name')
                
                # Extract zone if mentioned
                zone_to_check = self._extract_zone_from_message(message, venue_to_check)
                
                if zone_to_check:
                    # Check for playback control requests
                    if SYB_CONTROL_AVAILABLE and any(word in message_lower for word in ['pause', 'stop', 'play', 'resume', 'skip']):
                        return self._handle_playback_control(message, venue_to_check, zone_to_check, user_phone)
                    
                    # Check for design conversation triggers
                    if SYB_CONTROL_AVAILABLE and any(phrase in message_lower for phrase in 
                        ['want more', 'change to', 'prefer', 'too boring', 'more energy', 
                         'more relaxed', 'different vibe', 'change the mood']):
                        return self._handle_design_conversation(message, venue_to_check, zone_to_check, user_phone)
                    
                    # Get zone status based on platform
                    music_status = check_music_status(venue_to_check, zone_to_check)
                    
                    # Check if asking for full schedule or design advice
                    if any(word in message_lower for word in ['full schedule', 'weekly schedule', 'week', 'design advice', 'recommend', 'suggest']):
                        return self._format_schedule_details(music_status, user_phone)
                    
                    return self._format_music_status_response(music_status, user_phone)
        
        # Handle issue/problem queries
        if any(word in message_lower for word in ['issue', 'problem', 'offline', 'disconnect', 'volume']):
            # If it's music-related, do real-time check first
            if MUSIC_MONITOR_AVAILABLE and any(word in message_lower for word in ['music', 'volume', 'loud', 'quiet']):
                if venue_data or current_venue:
                    venue_to_check = venue_data['property_name'] if venue_data else current_venue.get('name')
                    zone_to_check = self._extract_zone_from_message(message, venue_to_check)
                    
                    if zone_to_check:
                        music_status = check_music_status(venue_to_check, zone_to_check)
                        if music_status['analysis']['issues']:
                            return self._format_music_issue_response(music_status, user_phone)
            
            # Check for similar issues in history
            similar_issues = venue_reader.find_similar_issue(message)
            if similar_issues:
                return self._format_similar_issues_response(similar_issues, venue_data or current_venue)
        
        # Check if email is mentioned - only load if needed
        if self._load_email_if_needed(message):
            return self._handle_email_query(message, user_name)
        
        # Default to Gemini for general conversation
        return self._generate_ai_response(message, venue_data, user_name)
    
    def _extract_venue_name(self, message: str) -> Optional[str]:
        """Extract venue name from message"""
        message_lower = message.lower()
        
        for venue in self.venues:
            venue_name = venue.get('property_name', '').lower()
            if venue_name in message_lower:
                return venue['property_name']
            
            # Check partial matches
            venue_words = venue_name.split()
            if any(word in message_lower for word in venue_words if len(word) > 3):
                return venue['property_name']
        
        return None
    
    def _format_pricing_response(self, pricing: Dict) -> str:
        """Format pricing information naturally"""
        property_name = pricing.get('property_name')
        zones = pricing.get('zone_count', 0)
        price_per = pricing.get('annual_price_per_zone', 'N/A')
        total = pricing.get('total_annual_price', 'N/A')
        contract_end = pricing.get('contract_end', 'N/A')
        
        response = f"Here's the pricing for {property_name}:\n\n"
        response += f"• {zones} music zones\n"
        response += f"• {price_per} per zone annually\n"
        response += f"• Total: {total} per year\n"
        
        if contract_end != 'N/A':
            response += f"• Current contract ends: {contract_end}\n"
        
        return response
    
    def _handle_email_query(self, message: str, user_name: str) -> str:
        """Handle email-related queries"""
        if not self.email_searcher:
            return "I'm having trouble accessing emails right now. Could you tell me more about what you sent?"
        
        try:
            # Search for recent emails from this user
            results = self.email_searcher.search_emails(
                query=f"from:{user_name}" if user_name else "recent emails",
                max_results=5
            )
            
            if results:
                return f"I found {len(results)} recent emails. The most recent was about: {results[0].get('subject', 'No subject')}. How can I help with that?"
            else:
                return "I couldn't find any recent emails from you. Could you tell me more about what you sent?"
                
        except Exception as e:
            logger.error(f"Email search failed: {e}")
            return "I'm having trouble accessing emails right now. Could you describe what you need help with?"
    
    def _format_contacts_response(self, venue_name: str, contacts: List[Dict]) -> str:
        """Format contact information naturally"""
        if len(contacts) == 1:
            c = contacts[0]
            response = f"For {venue_name}, your contact is {c.get('name')} ({c.get('title')})"
            if c.get('email'):
                response += f"\nEmail: {c['email']}"
            if c.get('phone'):
                response += f"\nPhone: {c['phone']}"
            if c.get('preferred_contact'):
                response += f"\nThey prefer: {c['preferred_contact']}"
            return response
        else:
            response = f"Here are your contacts at {venue_name}:\n\n"
            for c in contacts:
                response += f"• {c.get('name')} - {c.get('title')}\n"
                if c.get('email'):
                    response += f"  Email: {c['email']}\n"
                if c.get('phone'):
                    response += f"  Phone: {c['phone']}\n"
            return response
    
    def _extract_zone_from_message(self, message: str, venue_name: str) -> Optional[str]:
        """Extract zone name from message"""
        venue = find_venue(venue_name)
        if not venue:
            return None
        
        zones = [z.strip() for z in venue.get('zone_names', '').split(',')]
        message_lower = message.lower()
        
        for zone in zones:
            if zone.lower() in message_lower:
                return zone
        
        # If no specific zone mentioned, return first zone or None
        return zones[0] if zones and len(zones) == 1 else None
    
    def _format_music_status_response(self, music_status: Dict, user_phone: str) -> str:
        """Format real-time music status response"""
        zone = music_status.get('zone', 'Unknown')
        platform = music_status.get('platform', 'Unknown')
        
        # Handle SYB venues (with schedule info)
        if platform == 'SYB':
            actual = music_status.get('actual', {})
            schedule = music_status.get('schedule', {})
            history = music_status.get('history', {})
            
            response = f"📊 Current status for {zone}:\n\n"
            
            # Current playing info
            if actual.get('status') == 'offline':
                response += f"⚠️ Zone is currently offline\n"
            else:
                response += f"🎵 Now playing: {actual.get('playlist', 'Unknown')}"
                if actual.get('track'):
                    response += f"\n   Track: '{actual['track']}'"
                    if actual.get('artist'):
                        response += f" by {actual['artist']}"
                if actual.get('volume_level'):
                    response += f"\n🔊 Volume level: {actual['volume_level']}/16"
            
            # Add schedule info if available
            if schedule and schedule.get('has_schedule'):
                response += f"\n\n📋 Weekly Schedule ({schedule.get('schedule_name', 'Custom')}):"
                if schedule.get('is_active'):
                    weekly = schedule.get('weekly_schedule', {})
                    today = datetime.now().strftime('%A')
                    
                    # Show today's schedule
                    if today in weekly:
                        response += f"\n\nToday ({today}):"
                        for slot in weekly[today]:
                            response += f"\n   • {slot['time']}: {slot['playlist']}"
                    
                    # Offer to show full week if asked
                    if len(weekly) > 1:
                        response += f"\n\n(Ask me to see the full weekly schedule if needed)"
                else:
                    response += " (Currently inactive)"
            elif schedule and not schedule.get('has_schedule'):
                response += f"\n\n📋 Manual mode: {schedule.get('current_playlist', 'Unknown')}"
                response += f"\n   (No weekly schedule configured)"
            
            # Add history insights if available
            if history and not history.get('error'):
                response += f"\n\n📅 Past {history.get('weeks_analyzed', 3)} weeks insights:"
                if history.get('most_common'):
                    response += f"\n   Most played: {history['most_common']}"
                if history.get('playlist_patterns'):
                    patterns = history['playlist_patterns']
                    if len(patterns) > 1:
                        response += "\n   Playlist variety:"
                        for playlist, count in sorted(patterns.items(), key=lambda x: x[1], reverse=True)[:3]:
                            response += f"\n   • {playlist}: {count} plays"
            
            return response
        
        # Handle Beat Breeze venues (with design comparison)
        else:
            intended = music_status.get('intended', {})
            actual = music_status.get('actual', {})
            analysis = music_status.get('analysis', {})
            
            if analysis.get('match'):
                response = f"✅ {zone} is playing as intended: '{actual['playlist']}'"
                if actual.get('track'):
                    response += f" - currently '{actual['track']}'"
                    if actual.get('artist'):
                        response += f" by {actual['artist']}"
                if actual.get('volume_level'):
                    response += f" (Volume level: {actual['volume_level']}/16)"
                return response
            
            response = f"I've checked {zone} in real-time:\n\n"
            response += f"📋 Should be: {intended['playlist']}\n"
            response += f"🎵 Actually playing: {actual['playlist']}"
            
            if actual.get('track'):
                response += f" ('{actual['track']}')"
            
            if actual.get('volume_level'):
                response += f"\n🔊 Current volume level: {actual['volume_level']}/16"
            
            if analysis.get('issues'):
                response += "\n\n⚠️ Issues detected:\n"
                for issue in analysis['issues']:
                    response += f"• {issue}\n"
            
            # Ask customer if they want to change it back
            response += "\n\nWould you like me to change it back to the correct playlist?"
            
            # Store the issue context for follow-up
            self.pending_fixes[user_phone] = {
                'type': 'playlist_change',
                'zone': zone,
                'music_status': music_status
            }
            
            return response
    
    def _format_music_issue_response(self, music_status: Dict, user_phone: str) -> str:
        """Format response when music issue is detected"""
        zone = music_status.get('zone', 'Unknown')
        platform = music_status.get('platform', 'Unknown')
        
        # For SYB venues, handle differently since no design comparison
        if platform == 'SYB':
            actual = music_status.get('actual', {})
            
            if actual.get('status') == 'offline':
                response = f"⚠️ {zone} appears to be offline.\n\n"
                response += "I can notify our team to check the connection. Would you like me to do that?"
                self.pending_fixes[user_phone] = {
                    'type': 'notify_team',
                    'zone': zone,
                    'music_status': music_status
                }
            else:
                # For SYB, we just report status, no "issues" to fix
                response = f"I've checked {zone} status. "
                response += "If you need any adjustments, please let me know what changes you'd like."
            
            return response
        
        # For Beat Breeze venues with design comparison
        analysis = music_status.get('analysis', {})
        
        response = f"I've identified the issue at {zone}:\n\n"
        
        for issue in analysis.get('issues', []):
            response += f"• {issue}\n"
        
        # Determine the type of issue
        issue_text = ' '.join(analysis.get('issues', [])).lower()
        
        if 'volume' in issue_text:
            response += "\n\nWould you like me to adjust the volume to the correct level?"
            self.pending_fixes[user_phone] = {
                'type': 'volume_change',
                'zone': zone,
                'music_status': music_status,
                'target_volume': 10  # Default, could be extracted from intended
            }
        elif 'playlist' in issue_text or 'wrong' in issue_text:
            response += "\n\nWould you like me to change it to the correct playlist?"
            self.pending_fixes[user_phone] = {
                'type': 'playlist_change',
                'zone': zone,
                'music_status': music_status
            }
        else:
            response += "\n\nWould you like me to notify our design team to fix this immediately?"
            self.pending_fixes[user_phone] = {
                'type': 'notify_team',
                'zone': zone,
                'music_status': music_status
            }
        
        return response
    
    def _handle_playback_control(self, message: str, venue_name: str, zone_name: str, user_phone: str) -> str:
        """Handle playback control requests (pause, play, skip)"""
        message_lower = message.lower()
        
        # Find the zone ID
        zones = music_monitor.syb_api.find_venue_zones(venue_name) if MUSIC_MONITOR_AVAILABLE else []
        zone_id = None
        
        for z in zones:
            if z.get('name', '').lower() == zone_name.lower():
                zone_id = z.get('id')
                break
        
        if not zone_id:
            return f"I couldn't find the zone ID for {zone_name}. Please check the zone name."
        
        # Determine action
        action = 'pause'  # default
        if any(word in message_lower for word in ['play', 'resume', 'start']):
            action = 'play'
        elif any(word in message_lower for word in ['skip', 'next']):
            action = 'skip'
        elif any(word in message_lower for word in ['pause', 'stop']):
            action = 'pause'
        
        # Use smart handler that routes based on device type
        if SYB_CONTROL_AVAILABLE:
            success, message = syb_control.handle_music_request(
                zone_id, 'playback', {'control': action}
            )
            
            if success:
                return message
            else:
                # Check if it's a device limitation
                if 'display-only' in message.lower() or 'samsung' in message.lower():
                    return message  # Clear device limitation message
                else:
                    # It's an escalation request - notify team
                    if MUSIC_MONITOR_AVAILABLE:
                        music_monitor.notify_design_team(message)
                        return f"I've forwarded your request to our team. They'll {action} the music at {zone_name} shortly."
                    return message
        
        return f"Playback control is not available for {zone_name}."
    
    def _handle_design_conversation(self, message: str, venue_name: str, zone_name: str, user_phone: str) -> str:
        """Handle design conversations with playlist suggestions"""
        message_lower = message.lower()
        
        # Determine desired mood from message
        mood = 'balanced'  # default
        if any(word in message_lower for word in ['energy', 'upbeat', 'party', 'fun']):
            mood = 'energetic'
        elif any(word in message_lower for word in ['relax', 'chill', 'calm', 'quiet']):
            mood = 'relaxed'
        elif any(word in message_lower for word in ['sophisticated', 'elegant', 'classy']):
            mood = 'sophisticated'
        
        # Generate playlist suggestions
        response = syb_control.format_design_conversation(
            venue_name, zone_name,
            current_mood="current",
            desired_mood=mood
        )
        
        # Store pending change request
        self.pending_fixes[user_phone] = {
            'type': 'design_change',
            'venue': venue_name,
            'zone': zone_name,
            'mood': mood,
            'suggestions': response
        }
        
        return response
    
    def _format_schedule_details(self, music_status: Dict, user_phone: str) -> str:
        """Format detailed schedule view and design advice"""
        zone = music_status.get('zone', 'Unknown')
        platform = music_status.get('platform', 'Unknown')
        
        if platform == 'SYB':
            schedule = music_status.get('schedule', {})
            history = music_status.get('history', {})
            
            response = f"📋 Full Schedule Analysis for {zone}:\n\n"
            
            if schedule and schedule.get('has_schedule'):
                weekly = schedule.get('weekly_schedule', {})
                
                # Show full weekly schedule
                days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                
                for day in days_order:
                    if day in weekly:
                        response += f"\n{day}:"
                        for slot in weekly[day]:
                            response += f"\n   • {slot['time']}: {slot['playlist']}"
                
                # Provide design insights
                response += "\n\n💡 Design Insights:"
                
                # Analyze schedule patterns
                all_playlists = set()
                for day_slots in weekly.values():
                    for slot in day_slots:
                        all_playlists.add(slot['playlist'])
                
                response += f"\n• You're using {len(all_playlists)} different playlists"
                
                # Check weekend vs weekday differences
                weekday_playlists = set()
                weekend_playlists = set()
                
                for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
                    if day in weekly:
                        for slot in weekly[day]:
                            weekday_playlists.add(slot['playlist'])
                
                for day in ['Saturday', 'Sunday']:
                    if day in weekly:
                        for slot in weekly[day]:
                            weekend_playlists.add(slot['playlist'])
                
                if weekday_playlists != weekend_playlists:
                    response += "\n• Good: Different vibes for weekdays vs weekends"
                else:
                    response += "\n• Consider: Different playlists for weekends"
                
                # Volume recommendations
                if schedule.get('volume_level'):
                    vol = schedule['volume_level']
                    if vol > 12:
                        response += f"\n• Volume level {vol}/16 is quite high - consider reducing after 22:00"
                    elif vol < 8:
                        response += f"\n• Volume level {vol}/16 is conservative - could increase during peak hours"
                
                # History-based recommendations
                if history and history.get('playlist_patterns'):
                    patterns = history['playlist_patterns']
                    if len(patterns) < 3:
                        response += "\n• Low variety detected - consider adding more playlist rotation"
                    elif len(patterns) > 10:
                        response += "\n• High variety - ensure consistency for regular guests"
                
            else:
                response += "No weekly schedule configured.\n\n"
                response += "💡 Recommendation: Set up a weekly schedule in your SYB account for:\n"
                response += "• Automated playlist rotation\n"
                response += "• Time-based energy levels\n"
                response += "• Weekend vs weekday differentiation"
            
            return response
        
        elif platform == 'Beat Breeze':
            response = f"📋 Beat Breeze Design for {zone}:\n\n"
            intended = music_status.get('intended', {})
            
            if intended and intended.get('playlist') != 'Unknown':
                response += f"Current time slot:\n"
                response += f"• Playlist: {intended.get('playlist')}\n"
                response += f"• Energy: {intended.get('energy')}\n"
                response += f"• Volume: Level {intended.get('volume_level', 'Not set')}\n\n"
                response += "Note: Beat Breeze designs are managed directly. Contact your venue manager for schedule changes."
            else:
                response += "No design specifications found for this Beat Breeze zone.\n"
                response += "Please check with the design team."
            
            return response
        
        return "Unable to retrieve schedule information."
    
    def _format_similar_issues_response(self, similar_issues: List[Dict], current_venue: Optional[Dict]) -> str:
        """Format similar issues found in history"""
        if not similar_issues:
            return "I'll help you with that issue. Could you provide more details?"
        
        response = "I found similar issues we've resolved before:\n\n"
        for issue in similar_issues[:3]:  # Show max 3
            response += f"• {issue['venue']} ({issue['date']}): {issue['issue']}\n"
        
        response += "\nBased on past experience, this usually requires contacting the property's IT team. Should I help you reach out?"
        return response
    
    def _is_confirmation_response(self, message: str, user_phone: str) -> bool:
        """Check if this is a response to a pending fix"""
        if user_phone not in self.pending_fixes:
            return False
        
        message_lower = message.lower().strip()
        confirmation_words = ['yes', 'yeah', 'sure', 'ok', 'okay', 'please', 'do it', 'go ahead', 'fix it', 'change it']
        
        return any(word in message_lower for word in confirmation_words)
    
    def _handle_fix_confirmation(self, message: str, user_phone: str) -> str:
        """Handle customer's response to fix confirmation"""
        if user_phone not in self.pending_fixes:
            return "I'm not sure what you're referring to. How can I help you?"
        
        fix_request = self.pending_fixes[user_phone]
        message_lower = message.lower().strip()
        
        # Check for negative response
        if any(word in message_lower for word in ['no', "don't", 'leave it', 'never mind', 'cancel']):
            del self.pending_fixes[user_phone]
            return "Understood. I won't make any changes. Let me know if you need anything else."
        
        # Handle positive confirmation
        if fix_request['type'] == 'playlist_change':
            return self._attempt_playlist_fix(fix_request, user_phone)
        elif fix_request['type'] == 'volume_change':
            return self._attempt_volume_fix(fix_request, user_phone)
        elif fix_request['type'] == 'notify_team':
            return self._notify_team_for_fix(fix_request, user_phone)
        elif fix_request['type'] == 'design_change':
            return self._attempt_design_change(fix_request, user_phone)
        
        return "I'll look into that for you."
    
    def _attempt_playlist_fix(self, fix_request: Dict, user_phone: str) -> str:
        """Try to fix playlist via API, notify team if can't"""
        music_status = fix_request['music_status']
        zone = music_status['zone']
        intended_playlist = music_status['intended']['playlist']
        zone_id = music_status['actual'].get('zone_id')
        
        # Try to fix via API
        if MUSIC_MONITOR_AVAILABLE and zone_id:
            success = music_monitor.change_playlist(zone_id, intended_playlist)
            
            if success:
                del self.pending_fixes[user_phone]
                return f"✅ I've successfully changed {zone} back to '{intended_playlist}'. It should update within a minute."
        
        # If we can't fix via API, notify team automatically
        self._notify_design_team(music_status)
        del self.pending_fixes[user_phone]
        
        return f"I've notified our design team about the playlist issue at {zone}. They'll fix it remotely within 15 minutes."
    
    def _attempt_volume_fix(self, fix_request: Dict, user_phone: str) -> str:
        """Try to fix volume via API (works for IPAM400 devices)"""
        music_status = fix_request['music_status']
        zone = music_status.get('zone', 'Unknown')
        target_volume = fix_request.get('target_volume', 10)  # Default to level 10
        
        # For SYB venues, get zone_id from actual status
        if music_status.get('platform') == 'SYB':
            zone_id = music_status.get('actual', {}).get('zone_id')
            
            if not zone_id:
                # Try to find zone ID
                if MUSIC_MONITOR_AVAILABLE:
                    zones = music_monitor.syb_api.find_venue_zones(music_status.get('property'))
                    for z in zones:
                        if z.get('name', '').lower() == zone.lower():
                            zone_id = z.get('id')
                            break
            
            if zone_id:
                # Use the working volume control
                if MUSIC_MONITOR_AVAILABLE:
                    success = music_monitor.change_volume(zone_id, target_volume)
                    
                    if success:
                        del self.pending_fixes[user_phone]
                        return f"✅ I've adjusted the volume at {zone} to level {target_volume}/16. Changes should take effect immediately."
                
                # If API failed, might be a display-only device
                if SYB_CONTROL_AVAILABLE:
                    success, message = syb_control.attempt_volume_change(zone_id, target_volume)
                    del self.pending_fixes[user_phone]
                    
                    if success:
                        return f"✅ {message}"
                    else:
                        # Check if it's a device limitation
                        if 'display-only' in message.lower() or 'samsung' in message.lower():
                            return (f"This zone uses a display-only device. "
                                  f"Volume must be adjusted on the device itself or through your SYB dashboard.")
                        else:
                            # Notify team for other issues
                            self._notify_design_team(music_status)
                            return f"I've notified our design team about the volume issue at {zone}. They'll adjust it within 15 minutes."
        
        # For Beat Breeze or unknown platforms
        del self.pending_fixes[user_phone]
        return f"Volume control is not available for this zone. Please adjust manually or contact support."
    
    def _attempt_design_change(self, fix_request: Dict, user_phone: str) -> str:
        """Attempt to implement design change via API or escalate"""
        venue = fix_request['venue']
        zone = fix_request['zone'] 
        mood = fix_request['mood']
        
        # Since we know API control doesn't work with current credentials,
        # create a detailed escalation for the design team
        escalation_msg = f"🎨 Music Design Change Request\n\n"
        escalation_msg += f"Venue: {venue}\n"
        escalation_msg += f"Zone: {zone}\n"
        escalation_msg += f"Requested mood: {mood}\n\n"
        escalation_msg += "Customer has approved the following playlist suggestions:\n"
        
        # Extract suggestions from the stored response
        if 'suggestions' in fix_request:
            lines = fix_request['suggestions'].split('\n')
            for line in lines:
                if line.startswith(('1.', '2.', '3.', '4.', '5.')):
                    escalation_msg += f"  {line}\n"
        
        escalation_msg += f"\nRequested at: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        escalation_msg += "Action needed: Update playlist in SYB dashboard"
        
        # Notify design team
        if MUSIC_MONITOR_AVAILABLE:
            # Use existing notification system
            success = music_monitor.notify_design_team(escalation_msg)
            if success:
                del self.pending_fixes[user_phone]
                return (f"✅ I've forwarded your playlist preferences to our design team.\n"
                       f"They'll implement the {mood} mood changes for {zone} within 30 minutes.\n"
                       f"You'll receive confirmation once the changes are live.")
        
        del self.pending_fixes[user_phone]
        return (f"I've logged your playlist preferences for {zone}.\n"
               f"Our design team will implement the {mood} mood changes shortly.")
    
    def _notify_team_for_fix(self, fix_request: Dict, user_phone: str) -> str:
        """Notify team about issue that can't be fixed via API"""
        music_status = fix_request['music_status']
        zone = music_status['zone']
        
        success = self._notify_design_team(music_status)
        del self.pending_fixes[user_phone]
        
        if success:
            return f"✅ I've notified our design team about the issue at {zone}. They'll investigate and fix it within 15 minutes."
        else:
            return f"I've logged the issue at {zone} for our team. They'll fix it as soon as possible."
    
    def _notify_design_team(self, music_status: Dict) -> bool:
        """Automatically notify design team via Google Chat"""
        if MUSIC_MONITOR_AVAILABLE:
            alert_message = music_monitor.generate_alert_message(music_status)
            success = music_monitor.notify_design_team(alert_message)
            if success:
                logger.info("Design team notified via Google Chat")
                return True
        
        logger.warning("Could not notify design team")
        return False
    
    def _generate_ai_response(self, message: str, venue_data: Optional[Dict], user_name: str) -> str:
        """Generate AI response using Gemini"""
        try:
            # Build context including rich venue data
            context = f"""You are a helpful assistant for BMA Social, a B2B music service provider.
            
            User: {user_name or 'Customer'}
            Message: {message}
            """
            
            if venue_data:
                context += f"\nVenue: {venue_data.get('property_name')}"
                
                # Include special notes if available
                notes = venue_reader.get_venue_notes(venue_data['property_name'])
                if notes:
                    context += f"\nImportant notes about this venue:\n"
                    for note in notes:
                        context += f"- {note}\n"
            
            context += """
            
            Guidelines:
            - Be friendly and professional
            - Focus on music service support
            - Don't make up information
            - If unsure, offer to connect them with the team
            """
            
            response = self.model.generate_content(context)
            return response.text
            
        except Exception as e:
            logger.error(f"AI generation failed: {e}")
            return "I'm here to help! Could you tell me more about what you need?"


# Create singleton instance
simplified_bot = SimplifiedBot()

def process_message(message: str, user_phone: str, user_name: str = None, platform: str = "WhatsApp") -> str:
    """Process message with simplified bot"""
    return simplified_bot.process_message(message, user_phone, user_name, platform)
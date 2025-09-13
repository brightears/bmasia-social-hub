"""
BMA Social WhatsApp Bot - AI-First Architecture
AI is the brain that makes ALL decisions
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Optional, List, Tuple
from openai import OpenAI
from dotenv import load_dotenv

# Import managers
from venue_manager import VenueManager
from conversation_tracker import conversation_tracker

# Import Google Chat
try:
    from google_chat_client import chat_client, Department, Priority
    HAS_GOOGLE_CHAT = True
except ImportError:
    HAS_GOOGLE_CHAT = False
    chat_client = None

# Import Soundtrack API
try:
    from soundtrack_api import SoundtrackAPI
    HAS_SOUNDTRACK = True
except ImportError:
    HAS_SOUNDTRACK = False
    SoundtrackAPI = None

load_dotenv()
logger = logging.getLogger(__name__)


class AIFirstBot:
    """AI-driven bot where OpenAI makes ALL decisions"""

    def __init__(self):
        self.openai = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.model = 'gpt-4o-mini'
        self.venue_manager = VenueManager()

        # Load public product information
        self.product_info = self._load_product_info()

        # Initialize Soundtrack API if available
        self.soundtrack = None
        if HAS_SOUNDTRACK:
            try:
                self.soundtrack = SoundtrackAPI()
                logger.info("Soundtrack API initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Soundtrack API: {e}")

    def _load_product_info(self) -> str:
        """Load product information from markdown file - PUBLIC information, no verification needed"""
        try:
            product_file = os.path.join(os.path.dirname(__file__), 'product_info.md')
            with open(product_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract key sections for the AI prompt (avoid overwhelming the model)
            sections = []

            # SYB Pricing
            if "### Pricing Tiers" in content:
                sections.append("SYB PRICING: Essential $29/zone/month, Unlimited $39/zone/month, Enterprise custom pricing")

            # Beat Breeze Pricing
            if "### Pricing" in content and "Beat Breeze" in content:
                sections.append("BEAT BREEZE PRICING: Basic $15/location/month, Pro $25/location/month")

            # Key differences
            sections.append("KEY DIFFERENCE: SYB supports multiple zones per venue, Beat Breeze is one zone per location")
            sections.append("FEATURES: SYB has Spotify integration & API access, Beat Breeze is more affordable but basic")
            sections.append("LICENSING: Both include proper commercial music licensing (cannot use consumer Spotify/YouTube)")

            # Support escalation
            sections.append("SUPPORT: Bot handles volume/skip/pause. Humans handle playlist changes, billing, setup")

            return "\n".join(sections)

        except Exception as e:
            logger.error(f"Failed to load product info: {e}")
            return "PRODUCT INFO: SYB ($29-39/zone/month) and Beat Breeze ($15-25/location/month) - both include commercial licensing"
    
    def process_message(self, message: str, phone: str, user_name: Optional[str] = None) -> str:
        """
        AI-FIRST: Every message goes through AI for analysis and decision-making
        """
        logger.info(f"Processing message from {phone}: {message[:100]}...")
        
        # Get conversation context
        context = conversation_tracker.get_conversation_by_phone(phone) or []
        
        # Find venue if mentioned
        venue = self.venue_manager.find_venue(message)
        if not venue and context:
            # Check previous messages for venue
            for msg in context:
                if isinstance(msg, dict) and 'venue' in msg:
                    venue = self.venue_manager.get_venue_info(msg.get('venue'))
                    if venue:
                        break
        
        # STEP 1: AI ANALYZES THE MESSAGE
        ai_analysis = self._ai_analyze_message(message, venue, context)
        
        # STEP 2: AI DECIDES WHAT TO DO
        action = ai_analysis.get('action', 'respond')
        department = ai_analysis.get('department')
        priority = ai_analysis.get('priority')
        response = ai_analysis.get('response', '')
        needs_escalation = ai_analysis.get('escalate', False)
        
        # STEP 3: EXECUTE AI'S DECISION
        if needs_escalation and HAS_GOOGLE_CHAT:
            # AI decided this needs human help
            success = self._escalate_to_team(
                message=message,
                venue=venue,
                phone=phone,
                user_name=user_name,
                department=department,
                priority=priority,
                ai_analysis=ai_analysis
            )
            
            if success:
                # When escalated, DON'T send an immediate response
                # The human will respond via Google Chat
                # Only exception: critical system failures need immediate acknowledgment
                if priority == 'CRITICAL':
                    response = "🚨 We're checking your system immediately."
                else:
                    # For normal escalations, return empty string to indicate no response
                    # The conversation will continue when human responds via Google Chat
                    response = ""
        
        # STEP 4: EXECUTE API ACTIONS IF NEEDED
        if action == 'control_music' and self.soundtrack and venue:
            api_result = self._execute_music_control(
                venue=venue,
                command=ai_analysis.get('music_command'),
                parameters=ai_analysis.get('parameters', {})
            )
            if api_result:
                response = api_result
        
        # Save conversation context
        context.append({"role": "user", "content": message})
        # Only save assistant response if we're actually sending one
        if response:  # Don't save empty responses when waiting for human
            context.append({"role": "assistant", "content": response})
            if venue:
                context[-1]["venue"] = venue.get('name')
        conversation_tracker.save_conversation(phone, context)
        
        return response
    
    def _ai_analyze_message(self, message: str, venue: Optional[Dict], context: List) -> Dict:
        """
        Let AI analyze the message and decide what to do
        Returns: {
            'action': 'respond'|'escalate'|'control_music',
            'department': 'TECHNICAL'|'DESIGN'|'SALES',
            'priority': 'CRITICAL'|'HIGH'|'NORMAL',
            'response': 'AI generated response',
            'escalate': True/False,
            'music_command': 'skip'|'volume'|'pause'|'play',
            'parameters': {}
        }
        """
        
        # Build context for AI
        venue_info = ""
        if venue:
            venue_info = f"""
Venue: {venue.get('name')}
Zones: {', '.join(venue.get('zones', []))}
Platform: {venue.get('platform', 'Unknown')}
Contract End: {venue.get('contract_end', 'Unknown')}
Annual Price per Zone: {venue.get('annual_price', 'Unknown')}
Total Zones: {len(venue.get('zones', []))}
"""
        
        # System prompt that makes AI understand its role
        system_prompt = f"""You are the AI brain of BMA Social's customer support system.
You handle background music systems for venues globally, operating in over 50 countries.

{venue_info}

📋 PRODUCT INFORMATION (PUBLIC - NO VERIFICATION NEEDED):
{self.product_info}

YOUR CAPABILITIES via Soundtrack API:
✅ You CAN: Adjust volume, skip songs, pause/play music, check what's playing/current song
❌ You CANNOT: Change playlists, block songs, schedule music (due to licensing)

INFORMATION YOU HAVE ACCESS TO:
✅ Contract end dates (you can answer when contracts expire)
✅ Zone names and counts
✅ Annual pricing per zone
✅ Music platform being used
✅ Basic venue information

ANALYZE every message and return a JSON decision:
{{
    "action": "respond" or "escalate" or "control_music",
    "escalate": true/false (true if human help needed),
    "department": "TECHNICAL" or "DESIGN" or "SALES" or null,
    "priority": "CRITICAL" or "HIGH" or "NORMAL",  
    "response": "Your response to the customer",
    "music_command": "volume_up" or "volume_down" or "skip" or "pause" or "play" or "check_playing" or null,
    "parameters": {{"zone": "zone name from request if mentioned"}},
    "reasoning": "Why you made this decision"
}}

IMPORTANT for music commands: 
- Always extract the zone name from the request and put it in parameters.zone
- Example: "What's playing at Edge?" → parameters: {{"zone": "Edge"}}
- Set response to empty string "" for music commands - the actual response will come from the API
- The system will replace your response with the actual result

WHEN TO ANSWER DIRECTLY (don't escalate):
- Contract renewal dates (you have this info)
- Zone names and counts
- Current pricing information
- Basic venue details
- Volume/skip/pause/play controls
- What song is currently playing (via API)
- Product information (SYB vs Beat Breeze features, pricing, capabilities)
- General questions about our services and offerings

WHEN TO ESCALATE:
- CRITICAL + TECHNICAL: System down, all zones offline, complete failure
- HIGH + TECHNICAL: Zone offline, hardware issues, errors
- HIGH + DESIGN: Event music (time-sensitive), playlist changes
- NORMAL + DESIGN: Music customization, song blocking
- HIGH + SALES: Cancellations, complaints, unhappy customers
- NORMAL + SALES: NEW pricing quotes, adding NEW zones, contract CHANGES

RESPONSE STYLE:
- Write SHORT, CHAT-STYLE messages (not emails)
- Be conversational and natural
- NO email formatting (no subject lines, greetings, signatures)
- When escalating, just acknowledge the request naturally
- Do NOT mention "forwarding" or "escalating" to teams
- Do NOT say "Let me check..." or "I'll check..." - just execute the action
- For music commands, respond AFTER execution with the result

IMPORTANT: 
- If asking what song is playing → use 'check_playing' command
- If asking to control music (volume/skip/pause) → use appropriate music_command
- If asking about existing contract info → USE SUBTLE VERIFICATION (see below)
- If requesting NEW services or changes → escalate to SALES
- If system is offline/down → ALWAYS escalate as CRITICAL to TECHNICAL
- If playlist change requested → ALWAYS escalate to DESIGN

🔐 SUBTLE VERIFICATION FOR SENSITIVE DATA:
When users ask about pricing, contracts, or rates ("how much are we paying", "our rate", "contract renewal"):

1. NEVER say "I need to verify you" or mention security
2. Ask ONE natural question that venue staff would know:
   - "Happy to check that! Just to pull up the right details - is Rudolf still your GM there?"
   - "I can get those rates for you. Quick question - which zone do you manage most? Drift Bar or one of the others?"
   - "Let me grab your pricing. By the way, is Dennis still handling the day-to-day music operations?"
   - "Sure thing! Just confirming - you guys still have the four zones right? Drift Bar, Edge, and the others?"

3. EVALUATE their response:
   ✅ CORRECT if they mention: Rudolf (GM), Dennis (F&B), Drift Bar/Edge/Horizon/Shore (zones), or "Drift plays in lobby too"
   ❌ WRONG if they say: wrong names, "the manager", "upstairs", generic responses like "yes the manager", "I don't know"

4. RESPOND based on verification:
   - CORRECT → Provide the sensitive info: "Perfect! Your rate is THB 12,000 per zone per year..."
   - WRONG/UNSURE → Escalate gracefully: "Let me connect you with our account manager who has all your current details."

5. IMPORTANT: Only ask verification for truly sensitive data (pricing, contracts, financial info). 
   Music queries, volume control, and general info do NOT need verification.
"""
        
        # Prepare messages for AI
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Add recent context
        for ctx in context[-3:]:
            if isinstance(ctx, dict):
                messages.append({
                    "role": ctx.get("role", "user"),
                    "content": ctx.get("content", "")
                })
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        try:
            # Let AI analyze and decide
            response = self.openai.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,  # Lower temp for more consistent decisions
                response_format={"type": "json_object"}
            )
            
            ai_decision = json.loads(response.choices[0].message.content)
            logger.info(f"AI Decision: {ai_decision.get('action')} - Escalate: {ai_decision.get('escalate')}")
            
            return ai_decision
            
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            # Fallback response
            return {
                "action": "respond",
                "escalate": False,
                "response": "I'm here to help with your music system. Could you please tell me more about what you need?",
                "department": None,
                "priority": "NORMAL"
            }
    
    def _escalate_to_team(self, message: str, venue: Optional[Dict], phone: str, 
                          user_name: str, department: str, priority: str, 
                          ai_analysis: Dict) -> bool:
        """
        Escalate to the appropriate Google Chat space based on AI's decision
        """
        if not chat_client:
            return False
        
        try:
            # Map string values to enums
            dept_map = {
                'TECHNICAL': Department.OPERATIONS,
                'DESIGN': Department.DESIGN,
                'SALES': Department.SALES,
                'FINANCE': Department.FINANCE
            }
            
            prio_map = {
                'CRITICAL': Priority.CRITICAL,
                'HIGH': Priority.HIGH,
                'NORMAL': Priority.NORMAL
            }
            
            dept_enum = dept_map.get(department, Department.GENERAL)
            prio_enum = prio_map.get(priority, Priority.NORMAL)
            
            # Build notification with AI's analysis
            enhanced_message = f"{message}\n\n🤖 AI Analysis:\n{ai_analysis.get('reasoning', '')}"
            
            success = chat_client.send_notification(
                message=enhanced_message,
                venue_name=venue.get('name') if venue else 'Unknown Venue',
                venue_data=venue,
                user_info={'name': user_name or 'Customer', 'phone': phone, 'platform': 'WhatsApp'},
                department=dept_enum,
                priority=prio_enum,
                context=f"AI flagged: {ai_analysis.get('action')}"
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to escalate: {e}")
            return False
    
    def _execute_music_control(self, venue: Dict, command: str, parameters: Dict) -> Optional[str]:
        """
        Execute music control commands via Soundtrack API
        """
        if not self.soundtrack or not command:
            return None
        
        try:
            zone_name = parameters.get('zone') or venue.get('zones', [''])[0]
            zone_id = self._get_zone_id(venue, zone_name)
            
            if not zone_id:
                return f"I couldn't find the zone {zone_name}. Please specify which zone you'd like to control."
            
            if command == 'skip':
                result = self.soundtrack.skip_track(zone_id)
                if result:
                    return f"✅ Skipped to the next track in {zone_name}!"
                    
            elif command in ['volume_up', 'volume_down']:
                try:
                    current = self.soundtrack.get_zone_status(zone_id)
                    current_vol = current.get('volume')
                    
                    # If volume is None (API doesn't return it), use default middle value
                    if current_vol is None:
                        logger.warning(f"Volume not available for {zone_name}, using default 10")
                        current_vol = 10
                    
                    if command == 'volume_up':
                        new_vol = min(16, current_vol + 2)
                    else:
                        new_vol = max(0, current_vol - 2)
                    
                    logger.info(f"Setting volume for {zone_name} from {current_vol} to {new_vol}")
                    result = self.soundtrack.set_volume(zone_id, new_vol)
                    if result:
                        return f"✅ Volume adjusted to {new_vol}/16 in {zone_name}"
                    else:
                        logger.error(f"Failed to set volume for {zone_name}")
                        return f"I couldn't adjust the volume in {zone_name}. Please try again."
                except Exception as e:
                    logger.error(f"Volume control failed: {e}")
                    return f"I'm having trouble adjusting the volume. Please try again."
                    
            elif command == 'pause':
                result = self.soundtrack.control_playback(zone_id, 'pause')
                if result:
                    return f"⏸️ Music paused in {zone_name}"
                    
            elif command == 'play':
                result = self.soundtrack.control_playback(zone_id, 'play')
                if result:
                    return f"▶️ Music resumed in {zone_name}"
                    
            elif command == 'check_playing':
                try:
                    logger.info(f"Checking what's playing in zone {zone_id} ({zone_name})")
                    status = self.soundtrack.get_zone_status(zone_id)
                    logger.info(f"Zone status response: {status}")
                    
                    # Check for API errors first
                    if status and 'error' in status:
                        logger.error(f"API error getting zone status: {status['error']}")
                        return f"Unable to get current track info for {zone_name}."
                    
                    # Check if we got a valid status response
                    if status:
                        # Check if music is playing using the processed playing state
                        is_playing = status.get('playing', False)
                        playback_state = status.get('playback_state', 'unknown')
                        
                        logger.info(f"Zone playing status: {is_playing}, playback_state: {playback_state}")
                        
                        if is_playing:
                            # Get current track from processed status
                            current_track = status.get('current_track')
                            if current_track:
                                title = current_track.get('name', 'Unknown Title')
                                artist = current_track.get('artist', 'Unknown Artist')
                                logger.info(f"Found playing track: {title} by {artist}")
                                return f"🎵 Currently playing in {zone_name}: {title} by {artist}"
                            else:
                                logger.info("Zone is playing but no current track info available")
                                return f"Music is playing in {zone_name}, but track details are not available."
                        else:
                            if playback_state == 'paused':
                                return f"Music is paused in {zone_name}."
                            else:
                                return f"No music is currently playing in {zone_name}."
                    else:
                        logger.error("No status response received from API")
                        return f"Unable to get current track info for {zone_name}."
                        
                except Exception as e:
                    logger.error(f"Failed to check playing status: {e}")
                    return f"I'm having trouble connecting to {zone_name} right now. Please try again in a moment."
            
            return None
            
        except Exception as e:
            logger.error(f"Music control failed: {e}")
            return None
    
    def _get_zone_id(self, venue: Dict, zone_name: str) -> Optional[str]:
        """Get zone ID from Soundtrack API"""
        if not self.soundtrack:
            logger.error("No soundtrack API connection available")
            return None
            
        venue_name = venue.get('name', '')
        logger.info(f"Looking for zone '{zone_name}' for venue '{venue_name}'")
        
        # Use the scalable zone discovery service
        try:
            from zone_discovery import get_zone_id
            zone_id = get_zone_id(venue_name, zone_name)
            
            if zone_id:
                logger.info(f"✅ Found zone ID via discovery service: {zone_id[:30]}...")
                return zone_id
            else:
                logger.warning(f"Zone '{zone_name}' not found for venue '{venue_name}'")
                
        except ImportError:
            logger.warning("Zone discovery service not available, using fallback")
            # Fallback to hardcoded zone IDs
            try:
                from venue_accounts import get_zone_id as get_hardcoded_zone
                zone_id = get_hardcoded_zone(venue_name, zone_name)
                if zone_id:
                    logger.info(f"✅ Found zone ID from hardcoded fallback")
                    return zone_id
            except Exception as e:
                logger.warning(f"Could not get zone from venue_accounts: {e}")
        except Exception as e:
            logger.error(f"Zone discovery failed: {e}")
        
        return None
    
    def process_human_reply(self, reply: str, phone: str, thread_key: str) -> str:
        """
        AI reviews and potentially enhances human replies before sending to customer
        """
        system_prompt = """You are reviewing a support team member's reply before it goes to the customer via WhatsApp.
        
Your job:
1. Fix any grammar or spelling errors
2. Ensure the tone is professional and friendly
3. Add helpful information if needed
4. Translate to customer's language if they wrote in Thai
5. Keep the core message intact

IMPORTANT FORMAT RULES:
- Return a SHORT, CHAT-STYLE message (NOT an email)
- NO subject lines, NO formal greetings like "Dear/Hi [Name]"
- NO signatures, NO "Best regards", NO position titles
- Keep it conversational like WhatsApp chat
- Maximum 2-3 sentences unless complex explanation needed

Return the enhanced chat message ready to send."""
        
        try:
            response = self.openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Review and enhance this reply: {reply}"}
                ],
                temperature=0.3
            )
            
            enhanced_reply = response.choices[0].message.content
            logger.info("AI enhanced human reply")
            return enhanced_reply
            
        except Exception as e:
            logger.error(f"Failed to enhance reply: {e}")
            return reply  # Return original if enhancement fails


# Global instance
ai_bot = AIFirstBot()


def process_whatsapp_message(message: str, phone: str, user_name: Optional[str] = None) -> str:
    """
    Main entry point for WhatsApp messages
    AI processes EVERYTHING
    """
    return ai_bot.process_message(message, phone, user_name)


def enhance_human_reply(reply: str, phone: str, thread_key: str) -> str:
    """
    Entry point for human replies
    AI reviews and enhances before sending
    """
    return ai_bot.process_human_reply(reply, phone, thread_key)
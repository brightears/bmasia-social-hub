"""
Intent recognition for music control commands.
Identifies what the user wants to do with their music system.
"""

import re
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass


class Intent(Enum):
    """Supported intent types"""
    # Music Control
    VOLUME_UP = "volume_up"
    VOLUME_DOWN = "volume_down"
    VOLUME_SET = "volume_set"
    MUTE = "mute"
    UNMUTE = "unmute"
    
    # Playback Control
    PLAY = "play"
    PAUSE = "pause"
    STOP = "stop"
    SKIP = "skip"
    RESTART = "restart"
    
    # Playlist/Genre
    CHANGE_PLAYLIST = "change_playlist"
    CHANGE_GENRE = "change_genre"
    
    # Information
    STATUS_CHECK = "status_check"
    WHAT_PLAYING = "what_playing"
    LIST_ZONES = "list_zones"
    
    # Issues/Problems
    REPORT_ISSUE = "report_issue"
    NO_SOUND = "no_sound"
    DEVICE_OFFLINE = "device_offline"
    
    # Scheduling
    SCHEDULE_MUSIC = "schedule_music"
    CANCEL_SCHEDULE = "cancel_schedule"
    
    # General
    GREETING = "greeting"
    THANKS = "thanks"
    HELP = "help"
    UNKNOWN = "unknown"


@dataclass
class IntentResult:
    """Result of intent recognition"""
    intent: Intent
    confidence: float
    entities: Dict[str, Any]
    zone_specified: Optional[str] = None
    original_text: str = ""


class IntentRecognizer:
    """
    Rule-based intent recognition with pattern matching.
    Fast and reliable for music control commands.
    """
    
    def __init__(self):
        self.patterns = self._build_patterns()
    
    def _build_patterns(self) -> Dict[Intent, List[Tuple[re.Pattern, float]]]:
        """Build regex patterns for each intent with confidence scores"""
        return {
            # Volume Control
            Intent.VOLUME_UP: [
                (re.compile(r'\b(louder|increase volume|turn up|volume up|raise volume)\b', re.I), 0.95),
                (re.compile(r'\b(too quiet|can\'t hear|barely hear)\b', re.I), 0.85),
                (re.compile(r'\b(make it louder|more volume)\b', re.I), 0.9),
            ],
            Intent.VOLUME_DOWN: [
                (re.compile(r'\b(quieter|decrease volume|turn down|volume down|lower volume)\b', re.I), 0.95),
                (re.compile(r'\b(too loud|very loud|noisy)\b', re.I), 0.85),
                (re.compile(r'\b(make it quieter|less volume|softer)\b', re.I), 0.9),
            ],
            Intent.VOLUME_SET: [
                (re.compile(r'\b(set volume to|volume at|volume to|change volume to)\s*(\d+)\b', re.I), 0.95),
                (re.compile(r'\b(\d+)\s*(%|percent)\s*volume\b', re.I), 0.9),
            ],
            Intent.MUTE: [
                (re.compile(r'\b(mute|silence|no sound|turn off sound)\b', re.I), 0.95),
                (re.compile(r'\b(stop the music|quiet please)\b', re.I), 0.8),
            ],
            Intent.UNMUTE: [
                (re.compile(r'\b(unmute|sound on|turn on sound|enable sound)\b', re.I), 0.95),
            ],
            
            # Playback Control
            Intent.PLAY: [
                (re.compile(r'\b(play|start|resume|begin|continue)\b(?!\s*(next|previous))', re.I), 0.9),
                (re.compile(r'\b(music on|start music|play music)\b', re.I), 0.95),
            ],
            Intent.PAUSE: [
                (re.compile(r'\b(pause|hold|wait)\b', re.I), 0.9),
                (re.compile(r'\b(stop for now|pause music)\b', re.I), 0.95),
            ],
            Intent.STOP: [
                (re.compile(r'\b(stop|end|finish|turn off)\b(?!\s*for)', re.I), 0.85),
                (re.compile(r'\b(stop music|music off|no music)\b', re.I), 0.95),
            ],
            Intent.SKIP: [
                (re.compile(r'\b(skip|next|next song|next track|change song)\b', re.I), 0.95),
                (re.compile(r'\b(don\'t like this|change this)\b', re.I), 0.7),
            ],
            
            # Playlist/Genre
            Intent.CHANGE_PLAYLIST: [
                (re.compile(r'\b(play|change to|switch to|put on)\s+(\w+)\s*(playlist|music)?\b', re.I), 0.85),
                (re.compile(r'\b(playlist)\s+(\w+)\b', re.I), 0.9),
            ],
            Intent.CHANGE_GENRE: [
                (re.compile(r'\b(play|change to|switch to)\s+(jazz|classical|pop|rock|lounge|chill|ambient|electronic)\b', re.I), 0.95),
                (re.compile(r'\b(jazz|classical|pop|rock|lounge|chill|ambient|electronic)\s*(music|please)?\b', re.I), 0.8),
            ],
            
            # Information
            Intent.STATUS_CHECK: [
                (re.compile(r'\b(status|check|how is|what\'s the status)\b', re.I), 0.85),
                (re.compile(r'\b(is.*working|is.*online|is.*playing)\b', re.I), 0.8),
            ],
            Intent.WHAT_PLAYING: [
                (re.compile(r'\b(what\'s playing|what is playing|current song|which song|what song)\b', re.I), 0.95),
                (re.compile(r'\b(name.*song|tell me.*song)\b', re.I), 0.85),
            ],
            Intent.LIST_ZONES: [
                (re.compile(r'\b(list zones|show zones|which zones|what zones|all zones)\b', re.I), 0.95),
                (re.compile(r'\b(zones available|my zones)\b', re.I), 0.9),
            ],
            
            # Issues
            Intent.NO_SOUND: [
                (re.compile(r'\b(no sound|no music|can\'t hear|not playing|silent|dead)\b', re.I), 0.9),
                (re.compile(r'\b(not working|broken|stopped working)\b', re.I), 0.8),
            ],
            Intent.DEVICE_OFFLINE: [
                (re.compile(r'\b(offline|disconnected|not connected|no connection)\b', re.I), 0.95),
                (re.compile(r'\b(device.*not.*responding|player.*down)\b', re.I), 0.9),
            ],
            
            # Scheduling
            Intent.SCHEDULE_MUSIC: [
                (re.compile(r'\b(schedule|set timer|play at|start at|play later)\b', re.I), 0.9),
                (re.compile(r'\b(tomorrow|tonight|morning|evening|(\d+)\s*(am|pm))\b', re.I), 0.7),
            ],
            
            # General
            Intent.GREETING: [
                (re.compile(r'^(hi|hello|hey|good morning|good evening|greetings)\b', re.I), 0.95),
            ],
            Intent.THANKS: [
                (re.compile(r'\b(thank|thanks|appreciated|perfect|great|excellent)\b', re.I), 0.9),
            ],
            Intent.HELP: [
                (re.compile(r'\b(help|what can you do|commands|how to|guide|instructions)\b', re.I), 0.95),
            ],
        }
    
    def recognize(self, text: str) -> IntentResult:
        """
        Recognize intent from text message.
        Returns the most confident match.
        """
        text = text.strip()
        best_match = None
        best_confidence = 0.0
        entities = {}
        
        # Check each intent's patterns
        for intent, patterns in self.patterns.items():
            for pattern, base_confidence in patterns:
                match = pattern.search(text)
                if match:
                    confidence = base_confidence
                    
                    # Extract entities based on intent
                    if intent == Intent.VOLUME_SET:
                        # Extract volume level
                        volume_match = re.search(r'\b(\d+)\b', text)
                        if volume_match:
                            entities["volume"] = int(volume_match.group(1))
                    
                    elif intent in [Intent.CHANGE_PLAYLIST, Intent.CHANGE_GENRE]:
                        # Extract playlist/genre name
                        groups = match.groups()
                        if len(groups) > 1:
                            entities["name"] = groups[1]
                    
                    # Update best match
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = intent
        
        # Extract zone information if mentioned
        zone = self._extract_zone(text)
        
        # Default to UNKNOWN if no match
        if not best_match:
            best_match = Intent.UNKNOWN
            best_confidence = 0.0
        
        return IntentResult(
            intent=best_match,
            confidence=best_confidence,
            entities=entities,
            zone_specified=zone,
            original_text=text
        )
    
    def _extract_zone(self, text: str) -> Optional[str]:
        """Extract zone name from text"""
        zone_patterns = [
            r'\b(lobby|restaurant|pool|spa|gym|bar|rooftop|terrace|garden)\b',
            r'\b(main|ground|first|second)\s*(floor|level)\b',
            r'\b(zone|area|section)\s+(\w+)\b',
        ]
        
        for pattern in zone_patterns:
            match = re.search(pattern, text, re.I)
            if match:
                return match.group(0).lower()
        
        return None
    
    def requires_clarification(self, result: IntentResult) -> bool:
        """Check if the intent needs clarification"""
        # Low confidence
        if result.confidence < 0.7:
            return True
        
        # Volume set without specific level
        if result.intent == Intent.VOLUME_SET and "volume" not in result.entities:
            return True
        
        # Playlist/genre change without name
        if result.intent in [Intent.CHANGE_PLAYLIST, Intent.CHANGE_GENRE] and "name" not in result.entities:
            return True
        
        return False
    
    def get_clarification_prompt(self, result: IntentResult) -> str:
        """Get appropriate clarification prompt"""
        if result.confidence < 0.7:
            return "I'm not sure what you'd like me to do. Could you please rephrase?"
        
        if result.intent == Intent.VOLUME_SET:
            return "What volume level would you like? (0-100)"
        
        if result.intent == Intent.CHANGE_PLAYLIST:
            return "Which playlist would you like to play?"
        
        if result.intent == Intent.CHANGE_GENRE:
            return "Which genre would you prefer? (Jazz, Classical, Pop, Lounge, etc.)"
        
        return "Could you provide more details?"
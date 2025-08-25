"""Intent Classification System for BMA Social AI Assistant Bot

This module handles natural language understanding and intent classification
for venue support messages across WhatsApp and Line platforms.
"""

from enum import Enum
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import re


class Intent(Enum):
    """Primary intent categories for venue support"""
    
    # Music Control Intents
    VOLUME_ADJUST = "volume_adjust"
    PLAYLIST_CHANGE = "playlist_change"
    MUSIC_START = "music_start"
    MUSIC_STOP = "music_stop"
    SCHEDULE_MUSIC = "schedule_music"
    
    # Troubleshooting Intents
    MUSIC_NOT_PLAYING = "music_not_playing"
    APP_ISSUE = "app_issue"
    ZONE_ISSUE = "zone_issue"
    SYSTEM_STATUS = "system_status"
    
    # Query Intents
    CURRENT_PLAYING = "current_playing"
    SCHEDULE_QUERY = "schedule_query"
    HELP_REQUEST = "help_request"
    
    # Feedback & Social
    COMPLAINT = "complaint"
    COMPLIMENT = "compliment"
    GREETING = "greeting"
    THANKS = "thanks"
    
    # Administrative
    BUSINESS_HOURS = "business_hours"
    ACCOUNT_QUERY = "account_query"
    BILLING_QUERY = "billing_query"
    
    # Unknown
    UNKNOWN = "unknown"


class Sentiment(Enum):
    """Sentiment analysis for escalation logic"""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    URGENT = "urgent"


@dataclass
class Entity:
    """Extracted entity from user message"""
    type: str  # zone, volume_level, genre, time, etc.
    value: str
    confidence: float
    position: Tuple[int, int]  # Start and end position in text


@dataclass
class ClassificationResult:
    """Complete classification result for a message"""
    intent: Intent
    confidence: float
    sentiment: Sentiment
    entities: List[Entity]
    requires_clarification: bool
    suggested_response_type: str
    escalation_recommended: bool
    alternative_intents: List[Tuple[Intent, float]]  # Backup intents with confidence


class IntentClassifier:
    """Advanced intent classification with context awareness"""
    
    def __init__(self):
        self.intent_patterns = self._initialize_intent_patterns()
        self.entity_patterns = self._initialize_entity_patterns()
        self.sentiment_indicators = self._initialize_sentiment_indicators()
        self.context_keywords = self._initialize_context_keywords()
    
    def _initialize_intent_patterns(self) -> Dict[Intent, List[str]]:
        """Initialize regex patterns and keywords for each intent"""
        return {
            Intent.VOLUME_ADJUST: [
                r'\b(volume|sound|loud|quiet|louder|quieter|turn up|turn down|too loud|too quiet|can\'t hear|noisy)\b',
                r'\b(adjust|change|increase|decrease|raise|lower|mute|unmute)\s*(the)?\s*(volume|sound)\b',
                r'\b(music|audio|sound)\s*(is)?\s*(too)?\s*(loud|quiet|soft|high|low)\b',
                r'\b(customers? complain\w* about (volume|noise|sound))\b',
            ],
            
            Intent.PLAYLIST_CHANGE: [
                r'\b(play|change|switch|put on|start playing|queue)\s*(?:some)?\s*(jazz|rock|pop|classical|lounge|chill|upbeat|relaxing|dinner|lunch|breakfast)\b',
                r'\b(playlist|music|genre|style|songs?|tracks?)\s*(change|switch|different|new|other)\b',
                r'\b(want|need|prefer|like)\s*(?:to play)?\s*(different|other|new)\s*(music|playlist|genre)\b',
                r'\b(stop playing|don\'t like|hate|sick of)\s*(this|current)?\s*(music|playlist|song)\b',
                r'\b(mood|atmosphere|vibe|ambiance)\s*(change|different|update)\b',
            ],
            
            Intent.MUSIC_STOP: [
                r'\b(stop|pause|halt|cease|end|kill|turn off|shut off|silence)\s*(?:the)?\s*(music|audio|sound|playback|playlist)\b',
                r'\b(music|audio|sound|playlist)\s*(stop|pause|off|silence)\b',
                r'\b(emergency stop|immediately stop|urgent stop)\b',
                r'\b(no music|silence please|quiet time)\b',
            ],
            
            Intent.MUSIC_START: [
                r'\b(start|play|resume|begin|turn on|activate)\s*(?:the)?\s*(music|audio|sound|playlist)\b',
                r'\b(music|audio|playlist)\s*(start|play|on|resume)\b',
                r'\b(ready to open|opening time|start service)\b',
                r'\b(resume playback|continue playing|unpause)\b',
            ],
            
            Intent.SCHEDULE_MUSIC: [
                r'\b(schedule|set|program|plan)\s*(?:the)?\s*(music|playlist|audio)\s*(?:for|at)?\s*(\d+|tomorrow|tonight|evening|morning)\b',
                r'\b(play|start)\s*(music|playlist)?\s*(?:at|from|after)\s*(\d+:\d+|\d+\s*(am|pm)|midnight|noon)\b',
                r'\b(event|party|celebration|special)\s*(?:at|on)?\s*(\d+|tomorrow|tonight|next week)\b',
                r'\b(timer|automatic|auto)\s*(play|start|stop)\b',
            ],
            
            Intent.MUSIC_NOT_PLAYING: [
                r'\b(music|audio|sound|playlist)\s*(stopped|not playing|dead|silent|no sound|isn\'t working|not working)\b',
                r'\b(no music|no sound|no audio|nothing playing|dead silence)\b',
                r'\b(can\'t hear|don\'t hear|not hearing)\s*(?:any)?\s*(music|sound|audio)\b',
                r'\b(system|player|device)\s*(down|offline|not responding|crashed)\b',
                r'\b(stopped working|broke|broken|failed|failure)\b',
            ],
            
            Intent.APP_ISSUE: [
                r'\b(app|application|software)\s*(issue|problem|bug|crash|error|not working|frozen|stuck)\b',
                r'\b(can\'t|cannot|unable to)\s*(login|access|connect|open|use)\s*(?:the)?\s*(app|system)\b',
                r'\b(error message|error code|warning|alert)\b',
                r'\b(keeps crashing|won\'t open|not responding)\b',
            ],
            
            Intent.ZONE_ISSUE: [
                r'\b(zone|area|section|room|floor)\s*(\d+|one|two|three|main|bar|dining|patio|terrace)?\s*(issue|problem|not working|dead|offline)\b',
                r'\b(only|just|specific)\s*(zone|area|section)\s*(working|not working|has sound)\b',
                r'\b(multi.?zone|multiple zones?)\s*(issue|problem|failure)\b',
                r'\b(speaker|device)\s*(?:in)?\s*(zone|area|room)\s*(\d+|[a-z]+)?\s*(not working|offline|dead)\b',
            ],
            
            Intent.CURRENT_PLAYING: [
                r'\b(what\'s?|what is)\s*(playing|on|current)\b',
                r'\b(current|now playing|active)\s*(song|music|playlist|track)\b',
                r'\b(tell me|show me|display)\s*(?:the)?\s*(playlist|music|song)\b',
                r'\b(which|what)\s*(playlist|genre|music)\s*(is this|playing now)\b',
            ],
            
            Intent.COMPLAINT: [
                r'\b(terrible|awful|horrible|worst|unacceptable|disgusting|pathetic)\b',
                r'\b(complain|complaint|unhappy|dissatisfied|frustrated|angry|upset|mad)\b',
                r'\b(this is ridiculous|can\'t believe|never works|always problems)\b',
                r'\b(waste of money|cancel service|switch provider)\b',
            ],
            
            Intent.GREETING: [
                r'^(hi|hello|hey|good morning|good afternoon|good evening|greetings)\b',
                r'\b(how are you|how\'s it going|what\'s up)\b',
                r'^(morning|afternoon|evening)\b',
            ],
            
            Intent.THANKS: [
                r'\b(thank you|thanks|thx|appreciate|grateful|cheers)\b',
                r'\b(perfect|great|excellent|awesome|wonderful)\s*(thanks|thank you)?\b',
                r'\b(that\'s all|all good|sorted|fixed|done)\b',
            ],
            
            Intent.HELP_REQUEST: [
                r'\b(help|assist|support|guide|explain|how to|how do)\b',
                r'\b(don\'t know|not sure|confused|lost|stuck)\b',
                r'\b(what can you do|what are options|menu|commands)\b',
            ],
        }
    
    def _initialize_entity_patterns(self) -> Dict[str, str]:
        """Initialize patterns for entity extraction"""
        return {
            'zone': r'\b(zone|area|section|room|floor)\s*(\d+|one|two|three|four|five|main|bar|dining|patio|terrace|entrance|kitchen|restroom|lobby|vip)\b',
            'volume_level': r'\b(\d{1,3})\s*(%|percent)?\b',
            'volume_direction': r'\b(up|down|increase|decrease|raise|lower|higher|louder|quieter|softer)\b',
            'genre': r'\b(jazz|rock|pop|classical|lounge|chill|upbeat|relaxing|dinner|lunch|breakfast|acoustic|electronic|latin|reggae|country|blues|soul|funk|disco|house|techno)\b',
            'time': r'\b(\d{1,2}:\d{2}\s*(am|pm)?|\d{1,2}\s*(am|pm)|morning|afternoon|evening|night|midnight|noon|now|immediately|urgent|asap)\b',
            'duration': r'\b(\d+)\s*(minutes?|mins?|hours?|hrs?)\b',
            'day': r'\b(today|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday|weekend|weekday)\b',
        }
    
    def _initialize_sentiment_indicators(self) -> Dict[Sentiment, List[str]]:
        """Initialize sentiment detection patterns"""
        return {
            Sentiment.URGENT: [
                r'\b(urgent|emergency|immediately|asap|now|right now|critical|important)\b',
                r'\b(help!|please help|need help now)\b',
                r'(!{2,}|\?{2,})',  # Multiple exclamation or question marks
                r'\b(customers? complaining|customers? leaving|losing business)\b',
            ],
            Sentiment.NEGATIVE: [
                r'\b(not working|broken|failed|error|issue|problem|trouble|wrong)\b',
                r'\b(frustrated|annoyed|disappointed|unhappy|upset|angry)\b',
                r'\b(terrible|awful|horrible|bad|poor|worst)\b',
                r'\b(can\'t|cannot|won\'t|unable|impossible)\b',
            ],
            Sentiment.POSITIVE: [
                r'\b(great|excellent|perfect|wonderful|awesome|fantastic|amazing)\b',
                r'\b(works|working|fixed|solved|good|nice|love|like)\b',
                r'\b(thank you|thanks|appreciate|grateful)\b',
                r'(😊|😄|👍|✨|🎵|🎶)',  # Positive emojis
            ],
        }
    
    def _initialize_context_keywords(self) -> Dict[str, List[str]]:
        """Initialize context-specific keywords for better understanding"""
        return {
            'peak_hours': ['lunch', 'dinner', 'busy', 'crowded', 'full', 'packed', 'rush'],
            'quiet_hours': ['closed', 'empty', 'quiet', 'slow', 'morning', 'afternoon'],
            'special_event': ['party', 'event', 'celebration', 'birthday', 'wedding', 'corporate', 'gathering'],
            'technical': ['device', 'system', 'network', 'connection', 'wifi', 'bluetooth', 'speaker'],
        }
    
    def classify(self, message: str, context: Optional[Dict] = None) -> ClassificationResult:
        """
        Classify user message with full NLU processing
        
        Args:
            message: User's message text
            context: Optional conversation context
            
        Returns:
            ClassificationResult with intent, entities, sentiment, and recommendations
        """
        message_lower = message.lower()
        
        # Extract entities first
        entities = self._extract_entities(message)
        
        # Detect sentiment
        sentiment = self._detect_sentiment(message_lower)
        
        # Score all intents
        intent_scores = {}
        for intent, patterns in self.intent_patterns.items():
            score = self._score_intent(message_lower, patterns, entities, context)
            if score > 0:
                intent_scores[intent] = score
        
        # Get primary intent and alternatives
        if not intent_scores:
            primary_intent = Intent.UNKNOWN
            confidence = 0.0
            alternatives = []
        else:
            sorted_intents = sorted(intent_scores.items(), key=lambda x: x[1], reverse=True)
            primary_intent = sorted_intents[0][0]
            confidence = sorted_intents[0][1]
            alternatives = [(intent, score) for intent, score in sorted_intents[1:4] if score > 0.3]
        
        # Determine if clarification is needed
        requires_clarification = self._needs_clarification(primary_intent, confidence, entities)
        
        # Determine response type
        response_type = self._determine_response_type(primary_intent, sentiment, confidence)
        
        # Check for escalation
        escalation_recommended = self._should_escalate(sentiment, confidence, message_lower)
        
        return ClassificationResult(
            intent=primary_intent,
            confidence=confidence,
            sentiment=sentiment,
            entities=entities,
            requires_clarification=requires_clarification,
            suggested_response_type=response_type,
            escalation_recommended=escalation_recommended,
            alternative_intents=alternatives
        )
    
    def _extract_entities(self, message: str) -> List[Entity]:
        """Extract entities from message text"""
        entities = []
        
        for entity_type, pattern in self.entity_patterns.items():
            matches = re.finditer(pattern, message, re.IGNORECASE)
            for match in matches:
                entities.append(Entity(
                    type=entity_type,
                    value=match.group(),
                    confidence=0.9,  # Simple pattern matching gives high confidence
                    position=(match.start(), match.end())
                ))
        
        return entities
    
    def _detect_sentiment(self, message: str) -> Sentiment:
        """Detect sentiment from message"""
        scores = {
            Sentiment.URGENT: 0,
            Sentiment.NEGATIVE: 0,
            Sentiment.POSITIVE: 0,
        }
        
        for sentiment, patterns in self.sentiment_indicators.items():
            for pattern in patterns:
                if re.search(pattern, message, re.IGNORECASE):
                    scores[sentiment] += 1
        
        # Check for urgency first
        if scores[Sentiment.URGENT] > 0:
            return Sentiment.URGENT
        
        # Then check positive vs negative
        if scores[Sentiment.NEGATIVE] > scores[Sentiment.POSITIVE]:
            return Sentiment.NEGATIVE
        elif scores[Sentiment.POSITIVE] > 0:
            return Sentiment.POSITIVE
        
        return Sentiment.NEUTRAL
    
    def _score_intent(self, message: str, patterns: List[str], 
                     entities: List[Entity], context: Optional[Dict]) -> float:
        """Score an intent based on pattern matching and context"""
        score = 0.0
        matched_patterns = 0
        
        for pattern in patterns:
            if re.search(pattern, message, re.IGNORECASE):
                matched_patterns += 1
                score += 1.0
        
        if matched_patterns == 0:
            return 0.0
        
        # Normalize by number of patterns
        score = score / len(patterns)
        
        # Boost score based on entity presence
        relevant_entities = self._get_relevant_entities_for_intent(entities)
        if relevant_entities:
            score *= 1.2
        
        # Adjust based on context if available
        if context:
            score = self._adjust_score_with_context(score, context)
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _get_relevant_entities_for_intent(self, entities: List[Entity]) -> List[Entity]:
        """Get entities relevant to the current intent being scored"""
        # Simplified - in production, would map specific entities to intents
        return entities
    
    def _adjust_score_with_context(self, score: float, context: Dict) -> float:
        """Adjust intent score based on conversation context"""
        # Boost score if this intent matches recent conversation topic
        if 'last_intent' in context:
            # Intent continuation gets a boost
            score *= 1.1
        return score
    
    def _needs_clarification(self, intent: Intent, confidence: float, 
                            entities: List[Entity]) -> bool:
        """Determine if clarification is needed"""
        # Unknown intent always needs clarification
        if intent == Intent.UNKNOWN:
            return True
        
        # Low confidence needs clarification
        if confidence < 0.6:
            return True
        
        # Check for missing required entities
        required_entities = {
            Intent.VOLUME_ADJUST: ['zone', 'volume_direction'],
            Intent.PLAYLIST_CHANGE: ['genre'],
            Intent.SCHEDULE_MUSIC: ['time'],
            Intent.ZONE_ISSUE: ['zone'],
        }
        
        if intent in required_entities:
            entity_types = {e.type for e in entities}
            for required in required_entities[intent]:
                if required not in entity_types:
                    return True
        
        return False
    
    def _determine_response_type(self, intent: Intent, sentiment: Sentiment, 
                                confidence: float) -> str:
        """Determine the type of response needed"""
        if confidence < 0.5:
            return "clarification"
        
        if sentiment == Sentiment.URGENT:
            return "immediate_action"
        
        if intent in [Intent.COMPLAINT]:
            return "empathetic_resolution"
        
        if intent in [Intent.GREETING, Intent.THANKS]:
            return "social_acknowledgment"
        
        if intent in [Intent.VOLUME_ADJUST, Intent.PLAYLIST_CHANGE, Intent.MUSIC_STOP, Intent.MUSIC_START]:
            return "action_confirmation"
        
        return "informational"
    
    def _should_escalate(self, sentiment: Sentiment, confidence: float, 
                        message: str) -> bool:
        """Determine if human escalation is needed"""
        # Urgent sentiment with low confidence
        if sentiment == Sentiment.URGENT and confidence < 0.7:
            return True
        
        # Multiple negative indicators
        negative_count = len(re.findall(r'\b(hate|terrible|awful|worst|unacceptable)\b', message))
        if negative_count >= 2:
            return True
        
        # Threat to cancel or leave
        if re.search(r'\b(cancel|leave|switch|competitor|sue|legal|lawyer)\b', message):
            return True
        
        # Very low confidence on any intent
        if confidence < 0.3:
            return True
        
        return False
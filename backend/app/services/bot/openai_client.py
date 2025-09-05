"""
OpenAI GPT-5-Mini integration for conversational bot intelligence.
Provides natural, friendly conversation handling with design suggestions.
"""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import json
from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class OpenAIResponse:
    """Response from OpenAI GPT-5-Mini"""
    content: str
    confidence: float
    metadata: Dict[str, Any]


class OpenAIClient:
    """
    OpenAI GPT-5-Mini client for conversational intelligence.
    Focuses on natural, friendly responses with proactive design suggestions.
    """
    
    def __init__(self):
        self.client = None
        self.initialized = False
        
    async def initialize(self):
        """Initialize OpenAI client with GPT-5-Mini"""
        try:
            # Use GPT-5-Mini as specified by user
            self.client = OpenAI(api_key=settings.openai_api_key)
            self.model = 'gpt-5-mini'  # User specified GPT-5-Mini
            self.initialized = True
            logger.info("OpenAI GPT-5-Mini client initialized for conversational AI")
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI: {e}")
            self.initialized = False
    
    async def analyze_conversation(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        venue_info: Optional[Dict[str, Any]] = None
    ) -> OpenAIResponse:
        """
        Analyze conversation with natural understanding.
        Returns friendly, helpful responses with design suggestions.
        """
        if not self.initialized:
            await self.initialize()
        
        if not self.client:
            return OpenAIResponse(
                content="Hey, I'm having a little technical hiccup. Let me try again or I can get someone from our team to help!",
                confidence=0.0,
                metadata={"error": "Client not initialized"}
            )
        
        try:
            # Build conversational prompt
            prompt = self._build_conversational_prompt(message, context, venue_info)
            
            # Generate response with GPT-5-Mini
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": message}
                ],
                temperature=0.9,  # Higher for more natural conversation
                max_tokens=settings.openai_max_tokens
            )
            
            # Parse and structure response
            return self._parse_response(response)
            
        except Exception as e:
            logger.error(f"OpenAI analysis error: {e}")
            return OpenAIResponse(
                content="Let me get someone from our team to help you with that right away!",
                confidence=0.5,
                metadata={"error": str(e)}
            )
    
    async def generate_response(
        self,
        intent: str,
        entities: Dict[str, Any],
        action_result: Optional[Dict[str, Any]] = None,
        tone: str = "friendly"
    ) -> str:
        """
        Generate natural, conversational responses.
        Sometimes suggests design services proactively.
        """
        if not self.initialized:
            await self.initialize()
        
        try:
            import random
            
            # Decide if we should mention design services
            mention_design = random.random() > 0.7
            
            prompt = f"""
            You're a friendly music venue assistant. Generate a natural, conversational response.
            
            Intent: {intent}
            Entities: {entities}
            Action Result: {action_result or 'pending'}
            
            Guidelines:
            - Be friendly and conversational, like talking to a friend
            - Use casual language ("Hey", "Sure thing", "No worries")
            - If successful, be enthusiastic
            - If there's an error, be helpful and offer alternatives
            - Keep it brief (1-2 sentences max)
            {"- Mention that our design team can create custom playlists" if mention_design and intent == 'playlist_change' else ""}
            {"- Suggest upgrading to full remote control" if mention_design and intent == 'volume_control' else ""}
            
            Response:
            """
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": prompt}],
                temperature=0.9,
                max_tokens=150
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            # Fallback to friendly template responses
            return self._get_friendly_fallback(intent, action_result)
    
    async def extract_entities(
        self,
        message: str,
        expected_entities: List[str]
    ) -> Dict[str, Any]:
        """
        Extract entities naturally from conversation.
        """
        if not self.initialized:
            await self.initialize()
        
        try:
            prompt = f"""
            You're helping understand what a venue staff member needs.
            Extract these details from their message: {', '.join(expected_entities)}
            
            Message: "{message}"
            
            Be smart about context:
            - "Edge", "Lobby", "Restaurant" are usually zones
            - "Hilton", "Marriott", "Sheraton" are venues
            - "turn it up" means increase volume
            - "too quiet" means volume is low
            - "80s", "jazz", "chill" are playlist moods
            
            Return as simple JSON with just the entities found.
            """
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": prompt}],
                temperature=0.3,
                max_tokens=200
            )
            
            # Parse JSON from response
            text = response.choices[0].message.content.strip()
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0].strip()
            elif '```' in text:
                text = text.split('```')[1].split('```')[0].strip()
            
            return json.loads(text)
            
        except Exception as e:
            logger.error(f"Entity extraction error: {e}")
            return {}
    
    def _build_conversational_prompt(
        self,
        message: str,
        context: Optional[Dict[str, Any]],
        venue_info: Optional[Dict[str, Any]]
    ) -> str:
        """Build natural conversation prompt"""
        prompt = f"""
        You're a friendly assistant for music venue management. Be helpful, casual, and proactive.
        
        The venue staff member says: "{message}"
        
        Context:
        - Venue: {venue_info.get('name', 'their venue')} 
        - Type: {venue_info.get('type', 'hospitality')}
        - Recent conversation: {context.get('history', ['First message'])[-3:]}
        
        Understand what they need and respond naturally. If it's about:
        - Music control: Offer to help adjust it
        - Playlists: Suggest mood-based options or custom design
        - Problems: Be empathetic and offer solutions
        - Questions: Answer directly and offer additional help
        
        Sometimes mention that our music design team can create custom solutions.
        Keep responses friendly and conversational.
        """
        
        return prompt
    
    def _parse_response(self, response) -> OpenAIResponse:
        """Parse OpenAI response"""
        try:
            text = response.choices[0].message.content
            
            # Gauge confidence based on response
            confidence = 0.85  # Default for GPT-5-Mini
            
            return OpenAIResponse(
                content=text,
                confidence=confidence,
                metadata={
                    "model": self.model,
                    "tokens_used": response.usage.total_tokens if hasattr(response, 'usage') else 0
                }
            )
            
        except Exception as e:
            logger.error(f"Error parsing OpenAI response: {e}")
            return OpenAIResponse(
                content="Let me help you with that! Could you tell me a bit more?",
                confidence=0.0,
                metadata={"error": str(e)}
            )
    
    def _get_friendly_fallback(self, intent: str, action_result: Optional[Dict[str, Any]]) -> str:
        """Get friendly fallback responses"""
        templates = {
            "volume_up": "I've cranked up the volume for you! 🎵",
            "volume_down": "Turned it down a notch. Better?",
            "play": "Music's back on! Let the good times roll!",
            "pause": "Paused! Just let me know when you want it back on.",
            "change_playlist": "Switched it up for you! How's this vibe?",
            "status_check": "Let me check what's playing for you...",
            "help": "Hey! I can help with volume, playlists, or any music issues. What do you need?",
            "unknown": "Hmm, not quite sure what you need. Could you tell me more?",
        }
        
        if action_result and not action_result.get("success"):
            return f"Oops, hit a snag: {action_result.get('error', 'technical issue')}. Want me to get our team to look at it?"
        
        return templates.get(intent, "On it! Give me just a sec...")


# Global OpenAI client instance
openai_client = OpenAIClient()
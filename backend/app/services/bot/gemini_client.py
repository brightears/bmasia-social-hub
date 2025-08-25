"""
Google Gemini AI integration for advanced conversation handling.
Provides natural language understanding and response generation.
"""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import google.generativeai as genai

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class GeminiResponse:
    """Response from Gemini AI"""
    content: str
    confidence: float
    metadata: Dict[str, Any]


class GeminiClient:
    """
    Google Gemini AI client for conversation intelligence.
    Handles complex queries that rule-based intent recognition can't handle.
    """
    
    def __init__(self):
        self.model = None
        self.initialized = False
        
    async def initialize(self):
        """Initialize Gemini client"""
        try:
            genai.configure(api_key=settings.gemini_api_key)
            
            # Create model with specific settings for music control
            self.model = genai.GenerativeModel(
                model_name=settings.gemini_model,
                generation_config={
                    "temperature": settings.gemini_temperature,
                    "max_output_tokens": settings.gemini_max_tokens,
                    "top_p": 0.9,
                    "top_k": 40,
                }
            )
            
            self.initialized = True
            logger.info("Gemini AI client initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            self.initialized = False
    
    async def analyze_conversation(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        venue_info: Optional[Dict[str, Any]] = None
    ) -> GeminiResponse:
        """
        Analyze conversation for complex understanding.
        Used when rule-based intent recognition isn't sufficient.
        """
        if not self.initialized:
            await self.initialize()
        
        if not self.model:
            return GeminiResponse(
                content="I'm having trouble understanding. Could you rephrase?",
                confidence=0.0,
                metadata={"error": "Model not initialized"}
            )
        
        try:
            # Build context-aware prompt
            prompt = self._build_analysis_prompt(message, context, venue_info)
            
            # Generate response
            response = await self.model.generate_content_async(prompt)
            
            # Parse and structure response
            return self._parse_response(response)
            
        except Exception as e:
            logger.error(f"Gemini analysis error: {e}")
            return GeminiResponse(
                content="I understand you need help. Let me connect you with our team.",
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
        Generate natural language response based on intent and action result.
        Makes responses feel human and contextual.
        """
        if not self.initialized:
            await self.initialize()
        
        try:
            prompt = f"""
            Generate a {tone} response for a music venue support bot.
            
            Intent: {intent}
            Entities: {entities}
            Action Result: {action_result or 'pending'}
            
            Guidelines:
            - Be concise and helpful
            - Confirm the action taken
            - Use natural, conversational language
            - If there was an error, be apologetic and offer alternatives
            - Maximum 2 sentences
            
            Response:
            """
            
            response = await self.model.generate_content_async(prompt)
            return response.text.strip()
            
        except Exception as e:
            # Fallback to template responses
            return self._get_fallback_response(intent, action_result)
    
    async def extract_entities(
        self,
        message: str,
        expected_entities: List[str]
    ) -> Dict[str, Any]:
        """
        Extract specific entities from a message using AI.
        More flexible than regex patterns.
        """
        if not self.initialized:
            await self.initialize()
        
        try:
            prompt = f"""
            Extract the following information from this message:
            Message: "{message}"
            
            Information to extract:
            {', '.join(expected_entities)}
            
            Return as JSON format with entity names as keys.
            If an entity is not found, omit it.
            
            JSON:
            """
            
            response = await self.model.generate_content_async(prompt)
            
            # Parse JSON from response
            import json
            text = response.text.strip()
            # Find JSON in response
            start = text.find('{')
            end = text.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = text[start:end]
                return json.loads(json_str)
            
            return {}
            
        except Exception as e:
            logger.error(f"Entity extraction error: {e}")
            return {}
    
    def _build_analysis_prompt(
        self,
        message: str,
        context: Optional[Dict[str, Any]],
        venue_info: Optional[Dict[str, Any]]
    ) -> str:
        """Build context-aware prompt for Gemini"""
        prompt = f"""
        You are an AI assistant for a music venue management system.
        A venue staff member has sent this message: "{message}"
        
        Context:
        - Venue: {venue_info.get('name', 'Unknown')} ({venue_info.get('type', 'hotel')})
        - Location: {venue_info.get('city', 'Unknown')}, {venue_info.get('country', 'Unknown')}
        - Previous messages: {context.get('history', [])}
        
        Analyze this message and determine:
        1. What action the user wants to take with their music system
        2. Any specific zones or areas mentioned
        3. Any time-related requests
        4. The urgency level (low/medium/high)
        5. Whether this requires human intervention
        
        Provide a structured analysis.
        """
        
        return prompt
    
    def _parse_response(self, response) -> GeminiResponse:
        """Parse Gemini response into structured format"""
        try:
            text = response.text
            
            # Extract confidence (look for confidence indicators in response)
            confidence = 0.8  # Default confidence
            if "uncertain" in text.lower() or "not sure" in text.lower():
                confidence = 0.5
            elif "definitely" in text.lower() or "certain" in text.lower():
                confidence = 0.95
            
            return GeminiResponse(
                content=text,
                confidence=confidence,
                metadata={
                    "model": settings.gemini_model,
                    "tokens_used": response.usage_metadata.total_token_count if hasattr(response, 'usage_metadata') else 0
                }
            )
            
        except Exception as e:
            logger.error(f"Error parsing Gemini response: {e}")
            return GeminiResponse(
                content="I need a moment to process that request.",
                confidence=0.0,
                metadata={"error": str(e)}
            )
    
    def _get_fallback_response(self, intent: str, action_result: Optional[Dict[str, Any]]) -> str:
        """Get fallback response when AI fails"""
        templates = {
            "volume_up": "I've increased the volume for you.",
            "volume_down": "I've lowered the volume as requested.",
            "play": "Music is now playing.",
            "pause": "I've paused the music.",
            "change_playlist": "I've changed the playlist for you.",
            "status_check": "Let me check the system status for you.",
            "help": "I can help you control music volume, change playlists, and check system status. What would you like to do?",
            "unknown": "I'm not sure how to help with that. Could you please rephrase?",
        }
        
        if action_result and not action_result.get("success"):
            return f"I encountered an issue: {action_result.get('error', 'Unknown error')}. Please try again or contact support."
        
        return templates.get(intent, "I'm processing your request.")


# Global Gemini client instance
gemini_client = GeminiClient()
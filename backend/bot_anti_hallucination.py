#!/usr/bin/env python3
"""
Anti-hallucination wrapper for BMA Social bot
CRITICAL: Prevents bot from making up pricing/contract information
"""

import logging
import re
from typing import Dict, Optional, Any
from bot_gemini import GeminiBot

logger = logging.getLogger(__name__)

class SafeBot:
    """Bot wrapper that prevents hallucination of business-critical data"""
    
    # Hallucination triggers - if bot mentions these without data, it's making things up
    CRITICAL_TERMS = {
        'pricing': ['$', 'USD', 'THB', 'per month', 'monthly', 'rate', 'cost', 'price'],
        'contracts': ['contract', 'expires', 'renewal', 'October 2025', 'September 2026'],
        'fake_companies': ['Bright Ears', 'BrightEars']  # This doesn't exist!
    }
    
    def __init__(self):
        """Initialize safe bot with strict validation"""
        self.bot = GeminiBot()
        self.sheets_available = False
        
        # Check if venue data is actually working
        try:
            from venue_data_reader import get_all_venues
            test_venues = get_all_venues()
            if test_venues:
                self.sheets_available = True
                logger.info(f"✅ Venue data loaded with {len(test_venues)} venues")
            else:
                logger.error("❌ No venue data found")
        except Exception as e:
            logger.error(f"❌ Venue data loading failed: {e}")
    
    def process_message(self, message: str, user_phone: str, user_name: str = None, platform: str = "WhatsApp") -> str:
        """Process message with anti-hallucination safeguards"""
        
        message_lower = message.lower()
        
        # Check if asking about pricing/contracts
        asking_about_pricing = any(term in message_lower for term in 
                                  ['rate', 'price', 'cost', 'paying', 'subscription', 'fee'])
        asking_about_contract = any(term in message_lower for term in 
                                   ['contract', 'expire', 'renewal', 'when does', 'when will'])
        
        # If sheets aren't working and asking about critical data, DON'T HALLUCINATE
        if (asking_about_pricing or asking_about_contract) and not self.sheets_available:
            logger.warning("⚠️ Critical query without sheets access - preventing hallucination")
            return ("I'm having trouble accessing our pricing database right now. "
                   "Let me connect you with our team who can provide accurate information. "
                   "Someone will reach out to you shortly! 🙏")
        
        # Get bot response
        try:
            response = self.bot.process_message(message, user_phone, user_name, platform)
            
            # CRITICAL: Validate response for hallucination
            response = self._validate_response(response, message)
            
            return response
            
        except Exception as e:
            logger.error(f"Bot error: {e}")
            return "I'm having technical difficulties. Let me get someone from our team to help you."
    
    def _validate_response(self, response: str, original_message: str) -> str:
        """Validate bot response to prevent hallucination"""
        
        response_lower = response.lower()
        
        # Check for made-up prices
        price_patterns = [
            r'\$\d+',  # $179, $129 etc
            r'\d+\s*per\s*month',  # "179 per month"
            r'thb\s*\d+',  # "THB 129"
        ]
        
        for pattern in price_patterns:
            if re.search(pattern, response_lower):
                # Check if we actually have this data
                if not self._verify_price_data(response):
                    logger.error(f"🚨 HALLUCINATION DETECTED: Made-up price in '{response}'")
                    return ("I need to check our current pricing for your account. "
                           "Let me have someone from our team send you the accurate information.")
        
        # Check for "Bright Ears" (doesn't exist!)
        if 'bright ears' in response_lower or 'brightears' in response_lower:
            logger.error(f"🚨 HALLUCINATION: Mentioned non-existent 'Bright Ears'")
            return ("I apologize for the confusion. Let me get the correct information "
                   "from our records and have someone follow up with you.")
        
        # Check for made-up contract dates
        if any(date in response_lower for date in ['october 2025', 'september 2026', '2025', '2026']):
            if not self._verify_contract_data(response):
                logger.error(f"🚨 HALLUCINATION: Made-up contract date")
                return ("Let me verify your exact contract details. "
                       "I'll have our team send you the accurate information shortly.")
        
        return response
    
    def _verify_price_data(self, response: str) -> bool:
        """Verify if price mentioned in response is from actual data"""
        # If sheets aren't available, we can't verify
        if not self.sheets_available:
            return False
        
        # Check if the response mentions actual data we have
        # This is a simplified check - enhance based on your data structure
        return 'THB 10,500' in response or 'THB 10500' in response
    
    def _verify_contract_data(self, response: str) -> bool:
        """Verify if contract data mentioned is from actual data"""
        if not self.sheets_available:
            return False
        
        # Check for known valid dates from your sheet
        valid_dates = ['31st October 2025', '2025-10-31', '31/10/2025']
        return any(date in response for date in valid_dates)


# Create singleton instance
safe_bot = SafeBot()

def process_message(message: str, user_phone: str, user_name: str = None, platform: str = "WhatsApp") -> str:
    """Safe message processing that prevents hallucination"""
    return safe_bot.process_message(message, user_phone, user_name, platform)
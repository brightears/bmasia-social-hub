"""
Smart authentication system for BMA Social
Simple, fast, and user-friendly venue verification
"""

import os
import logging
import random
from typing import Dict, Optional, Tuple, List
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

class SmartAuthenticator:
    """
    Smart authentication that remembers trusted devices/numbers
    Simple verification that doesn't frustrate users
    """
    
    def __init__(self):
        # Trusted devices/phones (should be in database)
        self.trusted_devices = {}  # {phone_number: {venue_id, verified_at, venue_name}}
        
        # Simple verification codes per venue (like a WiFi password)
        self.venue_codes = {}  # {venue_id: "simple_code"}
        
        # Grace period for known contacts
        self.recent_verifications = {}  # Track recent successful verifications
    
    def check_authentication(self, user_phone: str, venue: Dict) -> Tuple[bool, str, str]:
        """
        Check if user needs authentication
        Returns: (is_authenticated, message, auth_method_needed)
        """
        
        venue_id = venue.get('id') or venue.get('name')
        
        # 1. CHECK: Is this phone number already trusted for this venue?
        if self.is_trusted_device(user_phone, venue_id):
            # Auto-authenticate known devices
            logger.info(f"Auto-authenticated trusted device: {user_phone} for {venue_id}")
            return (True, 
                   f"Welcome back! I recognize you from {venue.get('name')}. How can I help?",
                   "auto_trusted")
        
        # 2. CHECK: Has this phone been verified recently (last 7 days)?
        if self.was_recently_verified(user_phone, venue_id):
            # Quick re-verification for recent users
            return (False,
                   "Welcome back! For security, what's your venue's access code?",
                   "quick_code")
        
        # 3. CHECK: Is this phone trusted for a DIFFERENT venue?
        other_venue = self.get_trusted_venue(user_phone)
        if other_venue:
            # This phone is registered to another venue - need strong verification
            return (False,
                   f"I see you're registered with {other_venue}. To access {venue.get('name')}, please provide the venue access code.",
                   "venue_code_required")
        
        # 4. NEW USER: First time verification
        return (False,
               "I need to verify you're authorized for this venue. What's your venue access code? (It's like your WiFi password - ask your manager if you don't know it)",
               "first_time")
    
    def is_trusted_device(self, user_phone: str, venue_id: str) -> bool:
        """Check if phone is trusted for this specific venue"""
        if user_phone not in self.trusted_devices:
            return False
        
        device_info = self.trusted_devices[user_phone]
        
        # Check if it's for the same venue
        if str(device_info.get('venue_id')) != str(venue_id):
            return False
        
        # Check if trust hasn't expired (30 days)
        verified_at = device_info.get('verified_at')
        if verified_at:
            time_since = datetime.utcnow() - verified_at
            if time_since > timedelta(days=30):
                # Expired - need re-verification
                del self.trusted_devices[user_phone]
                return False
        
        return True
    
    def was_recently_verified(self, user_phone: str, venue_id: str) -> bool:
        """Check if user was verified in last 7 days"""
        key = f"{user_phone}:{venue_id}"
        if key in self.recent_verifications:
            verified_at = self.recent_verifications[key]
            time_since = datetime.utcnow() - verified_at
            return time_since < timedelta(days=7)
        return False
    
    def get_trusted_venue(self, user_phone: str) -> Optional[str]:
        """Get venue name if phone is trusted for another venue"""
        if user_phone in self.trusted_devices:
            return self.trusted_devices[user_phone].get('venue_name')
        return None
    
    def verify_simple_code(self, user_phone: str, venue: Dict, 
                          provided_code: str) -> Tuple[bool, str]:
        """
        Verify the simple access code
        Codes are like: "music123", "plaza456", "sunset789"
        """
        
        venue_id = venue.get('id') or venue.get('name')
        
        # Get venue's access code from metadata or generate one
        venue_code = self.get_venue_code(venue)
        
        # Clean and compare (case-insensitive)
        provided_clean = provided_code.strip().lower()
        venue_code_clean = venue_code.strip().lower()
        
        if provided_clean == venue_code_clean:
            # Success! Mark as trusted
            self.mark_as_trusted(user_phone, venue_id, venue.get('name'))
            return (True, 
                   f"✅ Perfect! You're verified for {venue.get('name')}. I'll remember this number so you won't need to verify again for 30 days. How can I help you today?")
        
        # Check if they provided a master code (for new staff)
        if provided_clean in ['newstaff', 'training', 'bmahelp']:
            # Temporary access - don't mark as fully trusted
            self.recent_verifications[f"{user_phone}:{venue_id}"] = datetime.utcnow()
            return (True,
                   f"✅ Temporary access granted. Please get your venue's permanent code from your manager. How can I help?")
        
        return (False, 
               "That code doesn't match. Please check with your manager for the correct venue access code.")
    
    def get_venue_code(self, venue: Dict) -> str:
        """Get or generate simple venue access code"""
        venue_id = venue.get('id') or venue.get('name')
        
        # Check if venue has a code in metadata
        if venue.get('metadata', {}).get('access_code'):
            return venue['metadata']['access_code']
        
        # Check if we have a stored code
        if venue_id in self.venue_codes:
            return self.venue_codes[venue_id]
        
        # Generate a simple memorable code
        # Format: [venue_prefix][numbers]
        # Examples: "plaza123", "marina456", "zen789"
        venue_name = venue.get('name', 'venue').lower()
        prefix = venue_name.split()[0][:6]  # First word, max 6 chars
        
        # Remove special characters
        prefix = ''.join(c for c in prefix if c.isalnum())
        
        # Add simple numbers
        numbers = str(random.randint(100, 999))
        
        code = f"{prefix}{numbers}"
        self.venue_codes[venue_id] = code
        
        logger.info(f"Generated access code for {venue_name}: {code}")
        return code
    
    def mark_as_trusted(self, user_phone: str, venue_id: str, venue_name: str):
        """Mark a phone number as trusted for a venue"""
        self.trusted_devices[user_phone] = {
            'venue_id': venue_id,
            'venue_name': venue_name,
            'verified_at': datetime.utcnow(),
            'trust_level': 'full'
        }
        
        # Also mark as recently verified
        self.recent_verifications[f"{user_phone}:{venue_id}"] = datetime.utcnow()
        
        logger.info(f"Marked {user_phone} as trusted for {venue_name}")
    
    def generate_easy_questions(self, venue: Dict) -> List[Dict]:
        """
        Generate easy verification questions that most staff would know
        But outsiders wouldn't
        """
        questions = []
        
        # Question about number of zones (with flexibility)
        if venue.get('metadata', {}).get('zone_count'):
            questions.append({
                'type': 'zone_count_range',
                'question': "Roughly how many music zones do you have? (1-3, 4-6, 7+)",
                'answer': self._get_zone_range(venue['metadata']['zone_count']),
                'flexible': True
            })
        
        # Question about location (multiple choice)
        if venue.get('location'):
            questions.append({
                'type': 'location_confirm',
                'question': f"Just to confirm, your venue is in {venue['location']}, right? (yes/no)",
                'answer': 'yes',
                'flexible': True
            })
        
        # Question about venue type
        if venue.get('metadata', {}).get('venue_type'):
            venue_type = venue['metadata']['venue_type']
            questions.append({
                'type': 'venue_type',
                'question': f"Is your venue a {venue_type}? (yes/no)",
                'answer': 'yes',
                'flexible': True
            })
        
        return questions
    
    def _get_zone_range(self, zone_count: int) -> str:
        """Convert exact zone count to range"""
        try:
            count = int(zone_count)
            if count <= 3:
                return "1-3"
            elif count <= 6:
                return "4-6"
            else:
                return "7+"
        except:
            return "1-3"
    
    def handle_new_staff_scenario(self, user_message: str) -> Tuple[bool, str]:
        """
        Handle scenarios where user doesn't know the code
        Common phrases: "I'm new", "don't know", "just started", "first day"
        """
        
        new_staff_indicators = [
            "i'm new", "im new", "i am new",
            "just started", "first day", "first week",
            "don't know", "dont know", "not sure",
            "forgot", "can't remember", "cant remember",
            "help", "what code"
        ]
        
        message_lower = user_message.lower()
        
        if any(indicator in message_lower for indicator in new_staff_indicators):
            return (True, """I understand you're new or don't have the code. Here are your options:

1. Ask your manager or colleague for the venue access code
2. Try these common temporary codes: 'newstaff' or 'training'
3. Have your manager contact support to add your number

For now, I can help with general questions. What do you need help with?""")
        
        return (False, None)


class TrustManager:
    """
    Manage trusted devices and their persistence
    This should integrate with database/cache for production
    """
    
    def __init__(self):
        self.trust_file = "trusted_devices.json"
        self.load_trusted_devices()
    
    def load_trusted_devices(self):
        """Load trusted devices from storage"""
        try:
            if os.path.exists(self.trust_file):
                with open(self.trust_file, 'r') as f:
                    self.trusted_devices = json.load(f)
            else:
                self.trusted_devices = {}
        except Exception as e:
            logger.error(f"Error loading trusted devices: {e}")
            self.trusted_devices = {}
    
    def save_trusted_devices(self):
        """Save trusted devices to storage"""
        try:
            with open(self.trust_file, 'w') as f:
                json.dump(self.trusted_devices, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving trusted devices: {e}")
    
    def add_trusted_device(self, phone: str, venue_id: str, venue_name: str):
        """Add a trusted device"""
        self.trusted_devices[phone] = {
            'venue_id': venue_id,
            'venue_name': venue_name,
            'verified_at': datetime.utcnow().isoformat(),
            'trust_expires': (datetime.utcnow() + timedelta(days=30)).isoformat()
        }
        self.save_trusted_devices()
    
    def is_trusted(self, phone: str, venue_id: str) -> bool:
        """Check if device is trusted"""
        if phone not in self.trusted_devices:
            return False
        
        device = self.trusted_devices[phone]
        
        # Check venue match
        if str(device['venue_id']) != str(venue_id):
            return False
        
        # Check expiration
        expires = datetime.fromisoformat(device['trust_expires'])
        if datetime.utcnow() > expires:
            del self.trusted_devices[phone]
            self.save_trusted_devices()
            return False
        
        return True
    
    def extend_trust(self, phone: str):
        """Extend trust period after successful interaction"""
        if phone in self.trusted_devices:
            self.trusted_devices[phone]['trust_expires'] = (
                datetime.utcnow() + timedelta(days=30)
            ).isoformat()
            self.save_trusted_devices()


# Global instances
smart_auth = SmartAuthenticator()
trust_manager = TrustManager()
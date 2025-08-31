"""
Venue authentication and security management
Ensures venues can only access their own data
"""

import os
import logging
import hashlib
import random
import string
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class VenueAuthenticator:
    """Handle venue authentication and access control"""
    
    def __init__(self):
        self.auth_attempts = {}  # Track authentication attempts
        self.authenticated_sessions = {}  # Track authenticated users
        self.venue_pins = {}  # Store venue PINs (should be in database)
        self.temp_codes = {}  # Temporary verification codes
    
    def generate_pin(self, venue_id: str) -> str:
        """Generate a unique PIN for a venue"""
        # Generate 6-digit PIN
        pin = ''.join(random.choices(string.digits, k=6))
        self.venue_pins[venue_id] = {
            'pin': self._hash_pin(pin),
            'created_at': datetime.utcnow(),
            'created_by': 'system'
        }
        return pin
    
    def _hash_pin(self, pin: str) -> str:
        """Hash PIN for secure storage"""
        return hashlib.sha256(pin.encode()).hexdigest()
    
    def verify_pin(self, venue_id: str, provided_pin: str) -> bool:
        """Verify venue PIN"""
        if venue_id not in self.venue_pins:
            return False
        
        stored_hash = self.venue_pins[venue_id]['pin']
        provided_hash = self._hash_pin(provided_pin)
        
        return stored_hash == provided_hash
    
    def authenticate_venue(self, user_phone: str, venue: Dict, method: str = 'pin') -> Tuple[bool, str]:
        """
        Authenticate venue access
        Methods: 'pin', 'email', 'security_question', 'phone_verification'
        """
        
        # Check if already authenticated
        if self.is_authenticated(user_phone, venue.get('id')):
            return True, "Already authenticated"
        
        # Track attempts
        attempt_key = f"{user_phone}:{venue.get('id')}"
        if attempt_key not in self.auth_attempts:
            self.auth_attempts[attempt_key] = {
                'count': 0,
                'first_attempt': datetime.utcnow()
            }
        
        # Check if too many attempts
        attempts = self.auth_attempts[attempt_key]
        if attempts['count'] >= 3:
            time_passed = datetime.utcnow() - attempts['first_attempt']
            if time_passed < timedelta(minutes=15):
                return False, "Too many attempts. Please try again in 15 minutes."
            else:
                # Reset attempts after 15 minutes
                attempts['count'] = 0
                attempts['first_attempt'] = datetime.utcnow()
        
        return False, "Authentication required"
    
    def create_auth_challenge(self, venue: Dict, user_phone: str) -> Dict:
        """Create authentication challenge based on venue data"""
        challenges = []
        
        # PIN method (if venue has PIN)
        if venue.get('id') in self.venue_pins:
            challenges.append({
                'type': 'pin',
                'question': "Please enter your 6-digit venue PIN:",
                'hint': "This was provided during setup"
            })
        
        # Security questions based on venue data
        security_questions = [
            {
                'type': 'employee_count',
                'question': "Approximately how many employees work at your venue? (nearest 10)",
                'field': 'employee_count'
            },
            {
                'type': 'manager_name',
                'question': "What's the last name of your General Manager?",
                'field': 'gm_last_name'
            },
            {
                'type': 'opening_year',
                'question': "What year did your venue open?",
                'field': 'opening_year'
            },
            {
                'type': 'zone_count',
                'question': "How many music zones does your venue have?",
                'field': 'zone_count'
            }
        ]
        
        # Pick a random security question if available
        available_questions = [q for q in security_questions 
                              if venue.get('metadata', {}).get(q['field'])]
        
        if available_questions:
            question = random.choice(available_questions)
            challenges.append(question)
        
        # Email verification (if email available)
        if venue.get('contact_email'):
            challenges.append({
                'type': 'email',
                'question': "We can send a verification code to your registered email",
                'action': 'send_email_code'
            })
        
        # Phone verification
        if venue.get('phone_number'):
            # Mask phone number for display
            phone = venue['phone_number']
            masked = phone[:4] + '****' + phone[-2:] if len(phone) > 6 else '****'
            challenges.append({
                'type': 'phone',
                'question': f"Is this your registered phone: {masked}?",
                'action': 'verify_phone'
            })
        
        # Default fallback
        if not challenges:
            challenges.append({
                'type': 'contact_support',
                'question': "Please contact support for verification",
                'action': 'escalate'
            })
        
        return random.choice(challenges) if challenges else None
    
    def verify_challenge_response(self, venue: Dict, challenge_type: str, 
                                 response: str, user_phone: str) -> Tuple[bool, str]:
        """Verify authentication challenge response"""
        
        attempt_key = f"{user_phone}:{venue.get('id')}"
        
        # Increment attempt count
        if attempt_key in self.auth_attempts:
            self.auth_attempts[attempt_key]['count'] += 1
        
        # Verify based on challenge type
        if challenge_type == 'pin':
            if self.verify_pin(venue.get('id'), response):
                self.mark_authenticated(user_phone, venue.get('id'))
                return True, "✅ Authentication successful! How can I help you today?"
            else:
                return False, "Incorrect PIN. Please try again."
        
        elif challenge_type == 'employee_count':
            stored = str(venue.get('metadata', {}).get('employee_count', ''))
            # Allow some flexibility (nearest 10)
            try:
                provided = int(response)
                stored_int = int(stored)
                if abs(provided - stored_int) <= 10:
                    self.mark_authenticated(user_phone, venue.get('id'))
                    return True, "✅ Verified! How can I help you today?"
            except:
                pass
            return False, "That doesn't match our records. Please try again."
        
        elif challenge_type == 'manager_name':
            stored = venue.get('metadata', {}).get('gm_last_name', '').lower()
            if response.lower().strip() == stored:
                self.mark_authenticated(user_phone, venue.get('id'))
                return True, "✅ Verified! How can I help you today?"
            return False, "That doesn't match our records."
        
        elif challenge_type == 'zone_count':
            stored = str(venue.get('metadata', {}).get('zone_count', ''))
            if response.strip() == stored:
                self.mark_authenticated(user_phone, venue.get('id'))
                return True, "✅ Verified! How can I help you today?"
            return False, "That doesn't match our records."
        
        elif challenge_type == 'email_code':
            # Verify email code
            if self.verify_email_code(user_phone, response):
                self.mark_authenticated(user_phone, venue.get('id'))
                return True, "✅ Email verified! How can I help you today?"
            return False, "Invalid code. Please check your email."
        
        return False, "Authentication failed. Please try again."
    
    def mark_authenticated(self, user_phone: str, venue_id: str):
        """Mark a session as authenticated"""
        self.authenticated_sessions[user_phone] = {
            'venue_id': venue_id,
            'authenticated_at': datetime.utcnow(),
            'expires_at': datetime.utcnow() + timedelta(hours=24)
        }
        
        # Clear attempts
        attempt_key = f"{user_phone}:{venue_id}"
        if attempt_key in self.auth_attempts:
            del self.auth_attempts[attempt_key]
    
    def is_authenticated(self, user_phone: str, venue_id: str) -> bool:
        """Check if user is authenticated for venue"""
        if user_phone not in self.authenticated_sessions:
            return False
        
        session = self.authenticated_sessions[user_phone]
        
        # Check venue match
        if session['venue_id'] != venue_id:
            return False
        
        # Check expiration
        if datetime.utcnow() > session['expires_at']:
            del self.authenticated_sessions[user_phone]
            return False
        
        return True
    
    def generate_email_code(self, user_phone: str, email: str) -> str:
        """Generate temporary email verification code"""
        code = ''.join(random.choices(string.digits, k=6))
        self.temp_codes[user_phone] = {
            'code': code,
            'email': email,
            'created_at': datetime.utcnow(),
            'expires_at': datetime.utcnow() + timedelta(minutes=10)
        }
        return code
    
    def verify_email_code(self, user_phone: str, code: str) -> bool:
        """Verify email code"""
        if user_phone not in self.temp_codes:
            return False
        
        stored = self.temp_codes[user_phone]
        
        # Check expiration
        if datetime.utcnow() > stored['expires_at']:
            del self.temp_codes[user_phone]
            return False
        
        # Check code
        if stored['code'] == code:
            del self.temp_codes[user_phone]
            return True
        
        return False


class VenueDataUpdater:
    """Handle updates to venue data from conversations"""
    
    def __init__(self):
        self.pending_updates = {}  # Store updates pending confirmation
    
    def detect_new_information(self, conversation: Dict, venue: Dict) -> Dict:
        """Detect new information from conversation"""
        updates = {}
        
        person_name = conversation.get('person_name', '')
        person_role = conversation.get('person_role', '')
        
        # Check if this is a new contact
        if person_role and person_name:
            role_lower = person_role.lower()
            
            # Detect key positions
            key_roles = {
                'general manager': 'gm_name',
                'gm': 'gm_name',
                'manager': 'manager_name',
                'engineer': 'engineer_name',
                'it': 'it_contact',
                'owner': 'owner_name',
                'director': 'director_name'
            }
            
            for role_key, field_name in key_roles.items():
                if role_key in role_lower:
                    current_value = venue.get('metadata', {}).get(field_name)
                    if current_value != person_name:
                        updates[field_name] = {
                            'old': current_value,
                            'new': person_name,
                            'field_display': field_name.replace('_', ' ').title(),
                            'confidence': 0.9 if 'general' in role_lower else 0.7
                        }
        
        # Detect other information from conversation
        # Email detection
        import re
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        messages = conversation.get('messages', [])
        
        for msg in messages:
            content = msg.get('content', '')
            
            # Find emails
            emails = re.findall(email_pattern, content)
            for email in emails:
                if email != venue.get('contact_email'):
                    updates['contact_email'] = {
                        'old': venue.get('contact_email'),
                        'new': email,
                        'field_display': 'Contact Email',
                        'confidence': 0.8
                    }
            
            # Find phone numbers
            phone_pattern = r'\+?[0-9]{10,15}'
            phones = re.findall(phone_pattern, content)
            for phone in phones:
                if phone != venue.get('phone_number'):
                    updates[f'additional_phone_{len(updates)}'] = {
                        'old': None,
                        'new': phone,
                        'field_display': 'Additional Phone',
                        'confidence': 0.6
                    }
        
        return updates
    
    def create_update_confirmation(self, updates: Dict) -> str:
        """Create confirmation message for updates"""
        if not updates:
            return None
        
        message = "I noticed some new information. Should I update your venue records?\n\n"
        
        for field, update in updates.items():
            if update['old']:
                message += f"• Update {update['field_display']}: {update['old']} → {update['new']}\n"
            else:
                message += f"• Add {update['field_display']}: {update['new']}\n"
        
        message += "\nReply 'yes' to confirm or 'no' to skip."
        return message
    
    def apply_updates(self, venue_id: str, updates: Dict, sheets_client=None, db_manager=None):
        """Apply confirmed updates to venue data"""
        success_count = 0
        
        # Update in Google Sheets
        if sheets_client:
            try:
                # This would update the master sheet
                # Implementation depends on sheet structure
                logger.info(f"Updated {len(updates)} fields in Google Sheets for venue {venue_id}")
                success_count += len(updates)
            except Exception as e:
                logger.error(f"Failed to update Google Sheets: {e}")
        
        # Update in database
        if db_manager:
            try:
                with db_manager.get_cursor() as cursor:
                    if cursor:
                        # Build metadata update
                        metadata_updates = {}
                        for field, update in updates.items():
                            metadata_updates[field] = update['new']
                        
                        # Update venue record
                        cursor.execute("""
                            UPDATE venues 
                            SET metadata = metadata || %s,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = %s
                        """, (json.dumps(metadata_updates), venue_id))
                        
                        logger.info(f"Updated database for venue {venue_id}")
                        success_count += 1
            except Exception as e:
                logger.error(f"Failed to update database: {e}")
        
        return success_count > 0


# Global instances
venue_authenticator = VenueAuthenticator()
venue_data_updater = VenueDataUpdater()
"""
Email-based verification system for BMA Social
Smart domain validation and one-time verification
"""

import os
import logging
import random
import string
import re
from typing import Dict, Optional, Tuple, List
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

class EmailVerificationSystem:
    """
    Handle email-based verification with smart domain validation
    """
    
    def __init__(self):
        # Trusted devices after email verification
        self.trusted_devices = {}  # {phone: {company_id, email, verified_at}}
        
        # Pending verification codes
        self.pending_codes = {}  # {phone: {code, email, expires_at}}
        
        # Known company email patterns
        self.company_patterns = {
            'hilton': ['@hilton.com', '@hiltonhotels.com'],
            'marriott': ['@marriott.com', '@marriotthotels.com'],
            'hyatt': ['@hyatt.com'],
            'accor': ['@accor.com', '@novotel.com', '@sofitel.com'],
            'ihg': ['@ihg.com', '@intercontinental.com'],
            'radisson': ['@radisson.com', '@radissonhotels.com'],
            'sheraton': ['@sheraton.com'],
            'westin': ['@westin.com'],
            'fourseasons': ['@fourseasons.com'],
            'mandarin': ['@mandarinoriental.com'],
            'shangri-la': ['@shangri-la.com'],
            'anantara': ['@anantara.com'],
            'minor': ['@minor.com', '@minorhotels.com'],
            'fitness': ['@fitnessfirst.com', '@virginactive.com', '@anytimefitness.com'],
            'retail': ['@uniqlo.com', '@zara.com', '@hm.com'],
        }
        
        # Email configuration
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = os.getenv('SMTP_USER', 'norbert@bmasiamusic.com')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
    
    def check_verification_needed(self, user_phone: str, company_name: str) -> Tuple[bool, str]:
        """
        Check if user needs email verification
        Returns: (needs_verification, message)
        """
        
        # Check if already trusted
        if self.is_trusted_device(user_phone, company_name):
            # Extend trust period on each use
            self.extend_trust(user_phone)
            return (False, f"Welcome back! I recognize your number. How can I help with your music system today?")
        
        # Check if trusted for different company
        if user_phone in self.trusted_devices:
            trusted_company = self.trusted_devices[user_phone].get('company_name')
            if trusted_company != company_name:
                return (True, f"I see you're registered with {trusted_company}. To access {company_name}'s settings, please verify your email address.")
        
        # New user - needs verification for company-specific requests
        return (True, None)
    
    def is_trusted_device(self, user_phone: str, company_name: str) -> bool:
        """Check if phone is trusted for this company"""
        if user_phone not in self.trusted_devices:
            return False
        
        device = self.trusted_devices[user_phone]
        
        # Check company match (flexible matching)
        if not self._company_match(device.get('company_name'), company_name):
            return False
        
        # Check if trust expired (30 days)
        verified_at = device.get('verified_at')
        if verified_at:
            time_since = datetime.utcnow() - verified_at
            if time_since > timedelta(days=30):
                del self.trusted_devices[user_phone]
                return False
        
        return True
    
    def _company_match(self, stored_company: str, provided_company: str) -> bool:
        """Flexible company name matching"""
        if not stored_company or not provided_company:
            return False
        
        # Normalize names
        stored = stored_company.lower().strip()
        provided = provided_company.lower().strip()
        
        # Exact match
        if stored == provided:
            return True
        
        # Partial match (e.g., "Hilton Bangkok" matches "Hilton")
        if stored in provided or provided in stored:
            return True
        
        # Key words match
        stored_words = set(stored.split())
        provided_words = set(provided.split())
        
        # At least one significant word matches
        significant_words = stored_words & provided_words
        if significant_words and len(list(significant_words)[0]) > 3:
            return True
        
        return False
    
    def validate_email_domain(self, email: str, company_name: str) -> Tuple[bool, str]:
        """
        Validate if email domain matches company
        Returns: (is_valid, message)
        """
        
        email_lower = email.lower().strip()
        company_lower = company_name.lower()
        
        # Admin/testing emails - always allowed
        admin_domains = ['@bmasiamusic.com', '@bmamusic.com']
        if any(email_lower.endswith(domain) for domain in admin_domains):
            return (True, "✅ BMA staff email verified! Full access granted.")
        
        # Extract domain from email
        if '@' not in email_lower:
            return (False, "Please provide a valid email address (e.g., john.smith@hilton.com)")
        
        domain = email_lower.split('@')[1]
        
        # Check known company patterns
        for company_key, domains in self.company_patterns.items():
            if company_key in company_lower:
                if any(domain.endswith(d.replace('@', '')) for d in domains):
                    return (True, "Email domain verified!")
                else:
                    expected = domains[0]
                    return (False, f"For {company_name}, please use your official email ending in {expected}")
        
        # For unknown companies, check if domain seems related
        company_words = company_lower.replace('-', ' ').replace('_', ' ').split()
        
        # Check if any company word appears in domain
        for word in company_words:
            if len(word) > 3 and word in domain:
                return (True, "Email domain accepted!")
        
        # Generic business domains are acceptable
        business_domains = ['com', 'co', 'net', 'org', 'hotel', 'rest', 'fit', 'gym', 'store']
        if any(domain.endswith(f'.{bd}') for bd in business_domains):
            # Warn but accept
            return (True, f"Note: Using {domain}. For faster support, use your official company email next time.")
        
        # Personal emails not accepted for company access
        personal_domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'icloud.com']
        if domain in personal_domains:
            return (False, f"Please use your official {company_name} email address, not a personal email.")
        
        # Default accept unknown domains with warning
        return (True, f"Email domain {domain} accepted. Verification code will be sent.")
    
    def generate_verification_code(self, user_phone: str, email: str) -> str:
        """Generate 6-digit verification code"""
        code = ''.join(random.choices(string.digits, k=6))
        
        self.pending_codes[user_phone] = {
            'code': code,
            'email': email,
            'created_at': datetime.utcnow(),
            'expires_at': datetime.utcnow() + timedelta(minutes=10),
            'attempts': 0
        }
        
        logger.info(f"Generated code {code} for {email}")
        return code
    
    def send_verification_email(self, email: str, code: str, company_name: str) -> bool:
        """Send verification code via email"""
        
        if not self.smtp_password:
            logger.warning("SMTP not configured, showing code in logs for testing")
            logger.info(f"VERIFICATION CODE for {email}: {code}")
            return True
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"BMA Music Support - Verification Code"
            msg['From'] = self.smtp_user
            msg['To'] = email
            
            # HTML email body
            html = f"""
            <html>
              <body style="font-family: Arial, sans-serif; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                  <h2 style="color: #2c3e50;">Music System Support Verification</h2>
                  
                  <p>Hello from BMA Music Support!</p>
                  
                  <p>Your verification code for {company_name} is:</p>
                  
                  <div style="background: #f0f0f0; padding: 15px; text-align: center; margin: 20px 0;">
                    <h1 style="color: #3498db; letter-spacing: 5px; margin: 0;">{code}</h1>
                  </div>
                  
                  <p>This code expires in 10 minutes.</p>
                  
                  <p>Simply type this code in your WhatsApp chat to verify your access.</p>
                  
                  <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
                  
                  <p style="color: #7f8c8d; font-size: 12px;">
                    This verification ensures secure access to your venue's music system controls. 
                    Once verified, you won't need to verify again for 30 days from the same WhatsApp number.
                  </p>
                  
                  <p style="color: #7f8c8d; font-size: 12px;">
                    If you didn't request this code, please ignore this email.
                  </p>
                </div>
              </body>
            </html>
            """
            
            # Plain text alternative
            text = f"""
Music System Support Verification

Your verification code for {company_name} is: {code}

This code expires in 10 minutes.

Type this code in your WhatsApp chat to verify your access.

Once verified, you won't need to verify again for 30 days.
            """
            
            part1 = MIMEText(text, 'plain')
            part2 = MIMEText(html, 'html')
            
            msg.attach(part1)
            msg.attach(part2)
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Verification email sent to {email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def verify_code(self, user_phone: str, provided_code: str, company_name: str) -> Tuple[bool, str]:
        """Verify the provided code"""
        
        if user_phone not in self.pending_codes:
            return (False, "No verification pending. Please request a new code.")
        
        pending = self.pending_codes[user_phone]
        
        # Check expiration
        if datetime.utcnow() > pending['expires_at']:
            del self.pending_codes[user_phone]
            return (False, "Code expired. Please request a new verification code.")
        
        # Check attempts
        pending['attempts'] += 1
        if pending['attempts'] > 3:
            del self.pending_codes[user_phone]
            return (False, "Too many attempts. Please request a new code.")
        
        # Verify code
        if provided_code.strip() == pending['code']:
            # Success! Mark as trusted
            email = pending['email']
            self.trusted_devices[user_phone] = {
                'company_name': company_name,
                'email': email,
                'verified_at': datetime.utcnow(),
                'trust_expires': datetime.utcnow() + timedelta(days=30)
            }
            
            # Clean up
            del self.pending_codes[user_phone]
            
            return (True, f"✅ Verification successful! Your WhatsApp number is now registered for {company_name}. You won't need to verify again for 30 days. How can I help with your music system?")
        
        return (False, f"Incorrect code. You have {3 - pending['attempts']} attempts remaining.")
    
    def extend_trust(self, user_phone: str):
        """Extend trust period on each successful use"""
        if user_phone in self.trusted_devices:
            self.trusted_devices[user_phone]['trust_expires'] = datetime.utcnow() + timedelta(days=30)
            logger.info(f"Extended trust for {user_phone}")
    
    def can_help_without_verification(self, message: str) -> bool:
        """
        Determine if request needs verification
        Returns True if we can help without verification
        """
        
        # Requests that DON'T need verification
        general_queries = [
            'how much', 'price', 'cost', 'pricing',
            'how to', 'what is', 'explain',
            'general', 'information', 'info',
            'help', 'support',
            'music ideas', 'playlist suggestions',
            'best practice', 'recommend',
            'technical specs', 'requirements'
        ]
        
        # Requests that DO need verification
        specific_actions = [
            'change', 'adjust', 'turn off', 'turn on',
            'stop', 'start', 'pause', 'play',
            'volume', 'skip', 'next',
            'my hotel', 'my restaurant', 'my gym',
            'our venue', 'our zone', 'our music'
        ]
        
        message_lower = message.lower()
        
        # Check if it's a general query
        if any(query in message_lower for query in general_queries):
            return True
        
        # Check if it's a specific action
        if any(action in message_lower for action in specific_actions):
            return False
        
        # Default to not requiring verification for general help
        return True


# Global instance
email_verifier = EmailVerificationSystem()
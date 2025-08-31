"""
Email verification with test mode for development
Allows specific test emails to bypass domain validation
"""

from email_verification import EmailVerificationSystem

class TestEmailVerificationSystem(EmailVerificationSystem):
    """Email verification with test bypass"""
    
    def __init__(self):
        super().__init__()
        # Test emails that bypass domain validation
        self.test_emails = [
            'norbert@bmasiamusic.com',
            'test@bmasiamusic.com',
            'production@bmasiamusic.com'
        ]
    
    def validate_email_domain(self, email: str, company_name: str):
        """Validate email with test bypass"""
        
        email_lower = email.lower().strip()
        
        # Check if it's a test email
        if email_lower in self.test_emails:
            return (True, f"✅ Test email accepted for {company_name}")
        
        # Otherwise use normal validation
        return super().validate_email_domain(email, company_name)

# For testing, use this instead
test_email_verifier = TestEmailVerificationSystem()
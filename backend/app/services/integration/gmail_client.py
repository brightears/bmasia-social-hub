"""
Gmail Integration Client
Manages email history and correspondence tracking for venues
"""

import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import base64
import re
from email.mime.text import MIMEText

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GMAIL_AVAILABLE = True
except ImportError:
    GMAIL_AVAILABLE = False
    service_account = None
    build = None
    HttpError = None

logger = logging.getLogger(__name__)

class GmailClient:
    """
    Client for Gmail API integration
    Manages email correspondence history for venues
    """
    
    def __init__(self, credentials_path: Optional[str] = None, 
                 email_account: Optional[str] = None):
        self.credentials_path = credentials_path or os.getenv('GMAIL_CREDENTIALS_PATH')
        self.email_account = email_account or os.getenv('GMAIL_ACCOUNT', 'norbert@bmasiamusic.com')
        
        self.service = None
        self.last_sync = None
        
        # Email patterns for venue identification
        self.venue_patterns = [
            r'venue:\s*([^,\n]+)',
            r'property:\s*([^,\n]+)',
            r'hotel:\s*([^,\n]+)',
            r'restaurant:\s*([^,\n]+)',
            r're:\s*\[([^\]]+)\]',  # Subject tags
        ]
        
        # Issue keywords for categorization
        self.issue_keywords = {
            'urgent': ['urgent', 'emergency', 'critical', 'down', 'not working', 'stopped'],
            'volume': ['volume', 'loud', 'quiet', 'sound level', 'audio level'],
            'playlist': ['playlist', 'music selection', 'songs', 'tracks'],
            'connectivity': ['offline', 'connection', 'network', 'internet', 'disconnected'],
            'hardware': ['player', 'device', 'equipment', 'hardware', 'speaker'],
            'licensing': ['license', 'subscription', 'payment', 'billing', 'account'],
        }
        
        if GMAIL_AVAILABLE:
            self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Gmail API client"""
        try:
            if self.credentials_path and os.path.exists(self.credentials_path):
                credentials = service_account.Credentials.from_service_account_file(
                    self.credentials_path,
                    scopes=['https://www.googleapis.com/auth/gmail.readonly',
                           'https://www.googleapis.com/auth/gmail.send']
                )
            else:
                # Try using environment variable
                credentials_json = os.getenv('GMAIL_CREDENTIALS_JSON')
                if credentials_json:
                    import json
                    credentials_info = json.loads(credentials_json)
                    credentials = service_account.Credentials.from_service_account_info(
                        credentials_info,
                        scopes=['https://www.googleapis.com/auth/gmail.readonly',
                               'https://www.googleapis.com/auth/gmail.send']
                    )
                else:
                    logger.warning("No Gmail credentials found")
                    return
            
            # For service account, we need to impersonate the user
            if hasattr(credentials, 'with_subject'):
                credentials = credentials.with_subject(self.email_account)
            
            self.service = build('gmail', 'v1', credentials=credentials)
            logger.info(f"Gmail client initialized for {self.email_account}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gmail client: {e}")
            self.service = None
    
    async def search_emails(self, venue_email: str, 
                          limit: int = 10,
                          days_back: int = 30) -> List[Dict[str, Any]]:
        """
        Search for emails related to a venue
        Returns recent correspondence history
        """
        if not self.service:
            logger.warning("Gmail service not initialized")
            return []
        
        try:
            # Build search query
            after_date = (datetime.utcnow() - timedelta(days=days_back)).strftime('%Y/%m/%d')
            query = f'from:{venue_email} OR to:{venue_email} after:{after_date}'
            
            # Search for messages
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=limit
            ).execute()
            
            messages = results.get('messages', [])
            email_data = []
            
            for msg in messages:
                # Get full message details
                message = self.service.users().messages().get(
                    userId='me',
                    id=msg['id']
                ).execute()
                
                # Parse email data
                parsed = self._parse_email(message)
                if parsed:
                    email_data.append(parsed)
            
            return email_data
            
        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Error searching emails: {e}")
            return []
    
    def _parse_email(self, message: Dict) -> Dict[str, Any]:
        """Parse Gmail message into structured data"""
        try:
            headers = message['payload'].get('headers', [])
            
            # Extract header information
            email_data = {
                'id': message['id'],
                'thread_id': message.get('threadId'),
                'labels': message.get('labelIds', []),
                'timestamp': None,
                'from': None,
                'to': None,
                'subject': None,
                'snippet': message.get('snippet', ''),
                'body': None,
                'issue_category': None,
                'urgency': 'normal'
            }
            
            # Parse headers
            for header in headers:
                name = header['name'].lower()
                value = header['value']
                
                if name == 'from':
                    email_data['from'] = value
                elif name == 'to':
                    email_data['to'] = value
                elif name == 'subject':
                    email_data['subject'] = value
                elif name == 'date':
                    try:
                        # Parse date
                        from email.utils import parsedate_to_datetime
                        email_data['timestamp'] = parsedate_to_datetime(value).isoformat()
                    except:
                        email_data['timestamp'] = value
            
            # Extract body
            body = self._get_email_body(message['payload'])
            email_data['body'] = body[:1000] if body else None  # Limit body length
            
            # Categorize issue
            if body or email_data['subject']:
                content = f"{email_data['subject'] or ''} {body or ''} {email_data['snippet']}".lower()
                
                # Check for urgency
                for keyword in self.issue_keywords['urgent']:
                    if keyword in content:
                        email_data['urgency'] = 'high'
                        break
                
                # Categorize issue type
                for category, keywords in self.issue_keywords.items():
                    if any(keyword in content for keyword in keywords):
                        email_data['issue_category'] = category
                        break
            
            # Extract venue information from content
            email_data['mentioned_venue'] = self._extract_venue_from_email(email_data)
            
            return email_data
            
        except Exception as e:
            logger.error(f"Error parsing email: {e}")
            return None
    
    def _get_email_body(self, payload: Dict) -> Optional[str]:
        """Extract email body from payload"""
        body = None
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data')
                    if data:
                        body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                        break
        elif payload['body'].get('data'):
            body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
        
        return body
    
    def _extract_venue_from_email(self, email_data: Dict) -> Optional[str]:
        """Extract venue name from email content"""
        content = f"{email_data.get('subject', '')} {email_data.get('body', '')}".lower()
        
        for pattern in self.venue_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    async def get_conversation_thread(self, thread_id: str) -> List[Dict[str, Any]]:
        """Get all emails in a conversation thread"""
        if not self.service:
            return []
        
        try:
            thread = self.service.users().threads().get(
                userId='me',
                id=thread_id
            ).execute()
            
            messages = []
            for msg in thread.get('messages', []):
                parsed = self._parse_email(msg)
                if parsed:
                    messages.append(parsed)
            
            # Sort by timestamp
            messages.sort(key=lambda x: x.get('timestamp', ''))
            
            return messages
            
        except Exception as e:
            logger.error(f"Error getting thread: {e}")
            return []
    
    async def send_email(self, to_email: str, subject: str, body: str, 
                        venue_name: Optional[str] = None) -> bool:
        """Send an email through Gmail"""
        if not self.service:
            logger.warning("Gmail service not initialized")
            return False
        
        try:
            # Add venue tag to subject if provided
            if venue_name:
                subject = f"[{venue_name}] {subject}"
            
            # Create message
            message = MIMEText(body)
            message['to'] = to_email
            message['from'] = self.email_account
            message['subject'] = subject
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode('utf-8')
            
            # Send message
            result = self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            logger.info(f"Email sent successfully: {result['id']}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False
    
    async def get_venue_communication_summary(self, venue_email: str) -> Dict[str, Any]:
        """Get summary of communications with a venue"""
        emails = await self.search_emails(venue_email, limit=50, days_back=90)
        
        if not emails:
            return {
                'total_emails': 0,
                'recent_issues': [],
                'last_contact': None
            }
        
        # Analyze communications
        summary = {
            'total_emails': len(emails),
            'last_contact': emails[0]['timestamp'] if emails else None,
            'recent_issues': [],
            'issue_categories': {},
            'urgency_breakdown': {'normal': 0, 'high': 0},
            'response_needed': False
        }
        
        # Count issue categories and urgency
        for email in emails:
            category = email.get('issue_category')
            if category:
                summary['issue_categories'][category] = summary['issue_categories'].get(category, 0) + 1
            
            urgency = email.get('urgency', 'normal')
            summary['urgency_breakdown'][urgency] += 1
            
            # Check if response needed (email from venue without reply)
            if email.get('from') and venue_email in email['from']:
                # This is from the venue, check if we replied
                # (Simplified - would need thread analysis for accuracy)
                summary['response_needed'] = True
        
        # Get recent issues
        for email in emails[:5]:  # Last 5 emails
            if email.get('issue_category'):
                summary['recent_issues'].append({
                    'date': email['timestamp'],
                    'category': email['issue_category'],
                    'urgency': email['urgency'],
                    'subject': email['subject']
                })
        
        return summary
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get Gmail service status"""
        return {
            'connected': self.service is not None,
            'email_account': self.email_account,
            'last_sync': self.last_sync.isoformat() if self.last_sync else None
        }
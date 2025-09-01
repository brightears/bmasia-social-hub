"""
Gmail integration for BMA Social
Search across multiple BMA team email accounts for venue correspondence
"""

import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
from functools import lru_cache
import re

# Google Gmail API imports
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    import base64
    GMAIL_AVAILABLE = True
except ImportError:
    GMAIL_AVAILABLE = False
    logging.warning("Gmail API not installed. Run: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")

logger = logging.getLogger(__name__)

class GmailClient:
    """Manage Gmail operations for BMA Social support context"""
    
    # BMA team email addresses to search
    BMA_EMAILS = [
        'norbert@bmasiamusic.com',
        'production@bmasiamusic.com',
        'keith@bmasiamusic.com',
        # Add more team members as needed
    ]
    
    # Performance limits
    MAX_RESULTS = 20  # Maximum emails per search
    CACHE_TTL = 300  # Cache for 5 minutes
    DEFAULT_DAYS_BACK = 30  # Default search window
    
    def __init__(self):
        self.service = None
        self.cache = {}
        self.cache_timestamps = {}
        self.connect()
    
    def connect(self):
        """Connect to Gmail API using service account delegation"""
        if not GMAIL_AVAILABLE:
            logger.error("Gmail API not available")
            return False
        
        try:
            # Use same credentials as Google Sheets
            creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
            if creds_json:
                creds_dict = json.loads(creds_json)
                SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
                
                # Create delegated credentials for each BMA email
                self.services = {}
                
                for email in self.BMA_EMAILS:
                    try:
                        # Create credentials with domain-wide delegation
                        credentials = service_account.Credentials.from_service_account_info(
                            creds_dict, 
                            scopes=SCOPES
                        )
                        
                        # Delegate to specific email
                        delegated_creds = credentials.with_subject(email)
                        
                        # Build service for this email
                        service = build('gmail', 'v1', credentials=delegated_creds)
                        self.services[email] = service
                        logger.info(f"✅ Connected to Gmail for {email}")
                        
                    except Exception as e:
                        logger.warning(f"Could not connect to {email}: {e}")
                        # Try without delegation (for service account's own inbox)
                        try:
                            credentials = service_account.Credentials.from_service_account_info(
                                creds_dict, 
                                scopes=SCOPES
                            )
                            service = build('gmail', 'v1', credentials=credentials)
                            self.services[email] = service
                            logger.info(f"✅ Connected to Gmail (limited) for {email}")
                        except:
                            pass
                
                if self.services:
                    logger.info(f"✅ Gmail client initialized for {len(self.services)} accounts")
                    return True
                else:
                    logger.warning("Could not connect to any Gmail accounts")
                    return False
                    
            else:
                logger.warning("No Google credentials found")
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect to Gmail: {e}")
            return False
    
    def search_venue_emails(self, venue_name: str, domain: str = None, days_back: int = None) -> List[Dict]:
        """
        Search all BMA emails for correspondence about a venue
        """
        if not self.services:
            return []
        
        # Check cache first
        cache_key = f"{venue_name}_{domain}_{days_back}"
        if self._is_cached(cache_key):
            return self.cache[cache_key]
        
        all_results = []
        days = days_back or self.DEFAULT_DAYS_BACK
        date_after = (datetime.now() - timedelta(days=days)).strftime('%Y/%m/%d')
        
        # Build search query
        query_parts = []
        if venue_name:
            query_parts.append(f'"{venue_name}"')
        if domain:
            query_parts.append(f'from:@{domain}')
        query_parts.append(f'after:{date_after}')
        
        query = ' '.join(query_parts)
        
        # Search each BMA inbox
        for email, service in self.services.items():
            try:
                results = self._search_inbox(service, email, query)
                all_results.extend(results)
            except Exception as e:
                logger.debug(f"Could not search {email}: {e}")
        
        # Deduplicate by message ID
        unique_results = self._deduplicate_emails(all_results)
        
        # Sort by date (most recent first)
        unique_results.sort(key=lambda x: x.get('date', ''), reverse=True)
        
        # Limit results
        limited_results = unique_results[:self.MAX_RESULTS]
        
        # Cache results
        self._cache_results(cache_key, limited_results)
        
        return limited_results
    
    def _search_inbox(self, service, email_address: str, query: str) -> List[Dict]:
        """Search a specific inbox"""
        try:
            # Execute search
            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=self.MAX_RESULTS
            ).execute()
            
            messages = results.get('messages', [])
            
            # Get message details
            email_data = []
            for msg in messages:
                try:
                    message = service.users().messages().get(
                        userId='me',
                        id=msg['id'],
                        format='metadata',
                        metadataHeaders=['From', 'To', 'Subject', 'Date']
                    ).execute()
                    
                    # Extract headers
                    headers = {h['name']: h['value'] 
                              for h in message['payload'].get('headers', [])}
                    
                    email_data.append({
                        'id': msg['id'],
                        'from': headers.get('From', ''),
                        'to': headers.get('To', ''),
                        'subject': headers.get('Subject', ''),
                        'date': headers.get('Date', ''),
                        'inbox': email_address,
                        'snippet': message.get('snippet', '')
                    })
                    
                except Exception as e:
                    logger.debug(f"Could not get message {msg['id']}: {e}")
            
            return email_data
            
        except Exception as e:
            logger.debug(f"Search error in {email_address}: {e}")
            return []
    
    def get_recent_issues(self, venue_name: str, domain: str = None) -> Dict:
        """
        Get a summary of recent issues for a venue
        """
        # Search with issue keywords
        issue_keywords = ['issue', 'problem', 'offline', 'not working', 'down', 'stopped']
        
        emails = self.search_venue_emails(venue_name, domain, days_back=14)
        
        # Filter for issues
        issues = []
        for email in emails:
            subject_lower = email.get('subject', '').lower()
            snippet_lower = email.get('snippet', '').lower()
            
            if any(keyword in subject_lower or keyword in snippet_lower 
                   for keyword in issue_keywords):
                issues.append({
                    'subject': email['subject'],
                    'date': email['date'],
                    'snippet': email['snippet'][:200]  # First 200 chars
                })
        
        return {
            'total_emails': len(emails),
            'recent_issues': issues[:5],  # Top 5 issues
            'last_contact': emails[0]['date'] if emails else None
        }
    
    def get_conversation_context(self, venue_name: str, domain: str = None) -> str:
        """
        Get a formatted context summary for the bot
        """
        summary = self.get_recent_issues(venue_name, domain)
        
        if not summary['total_emails']:
            return None
        
        context = f"📧 Email History: {summary['total_emails']} emails in last 30 days\n"
        
        if summary['last_contact']:
            context += f"Last contact: {summary['last_contact']}\n"
        
        if summary['recent_issues']:
            context += "\nRecent issues:\n"
            for issue in summary['recent_issues'][:3]:
                context += f"• {issue['subject']}\n"
        
        return context
    
    def _deduplicate_emails(self, emails: List[Dict]) -> List[Dict]:
        """Remove duplicate emails by ID"""
        seen = set()
        unique = []
        for email in emails:
            if email['id'] not in seen:
                seen.add(email['id'])
                unique.append(email)
        return unique
    
    def _is_cached(self, key: str) -> bool:
        """Check if cache is still valid"""
        if key not in self.cache:
            return False
        
        timestamp = self.cache_timestamps.get(key, 0)
        return (datetime.now().timestamp() - timestamp) < self.CACHE_TTL
    
    def _cache_results(self, key: str, results: List[Dict]):
        """Cache search results"""
        self.cache[key] = results
        self.cache_timestamps[key] = datetime.now().timestamp()
    
    def clear_cache(self):
        """Clear all cached results"""
        self.cache.clear()
        self.cache_timestamps.clear()


# Global instance
gmail_client = GmailClient()


# Helper functions for bot integration
def get_venue_email_context(venue_name: str) -> Optional[str]:
    """
    Quick helper to get email context for a venue
    """
    if not gmail_client.services:
        return None
    
    # Extract domain from venue name if possible
    domain = None
    if 'hilton' in venue_name.lower():
        domain = 'hilton.com'
    elif 'marriott' in venue_name.lower():
        domain = 'marriott.com'
    # Add more domain mappings as needed
    
    return gmail_client.get_conversation_context(venue_name, domain)
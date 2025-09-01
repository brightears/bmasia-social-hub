"""
Smart Email Search Strategy
Only searches when contextually relevant to save tokens and API calls
"""

import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import re

logger = logging.getLogger(__name__)

class SmartEmailSearcher:
    """
    Intelligent email search that only queries when relevant
    """
    
    # Define trigger keywords that warrant email search
    SEARCH_TRIGGERS = {
        'history': ['previous', 'last time', 'before', 'history', 'earlier', 'past'],
        'contract': ['contract', 'renewal', 'pricing', 'negotiate', 'rate', 'cost', 'invoice'],
        'technical': ['issue', 'problem', 'fixed', 'resolved', 'ticket', 'support'],
        'follow_up': ['follow up', 'following up', 'update on', 'status of', 'progress'],
        'reference': ['email', 'sent', 'mentioned', 'discussed', 'agreed', 'confirmed']
    }
    
    # Search depth based on query type
    SEARCH_DEPTH = {
        'history': 60,      # 60 days for general history
        'contract': 180,    # 6 months for contract discussions
        'technical': 30,    # 30 days for technical issues
        'follow_up': 14,    # 2 weeks for follow-ups
        'reference': 30     # 30 days for references
    }
    
    def __init__(self, gmail_client):
        self.gmail = gmail_client
        self.last_search = {}  # Track last search per venue
        self.search_results_cache = {}  # Cache full results
        
    def should_search_emails(self, message: str, venue_name: str) -> tuple[bool, str]:
        """
        Determine if email search is warranted based on message content
        Returns: (should_search, search_type)
        """
        message_lower = message.lower()
        
        # Check each trigger category
        for search_type, keywords in self.SEARCH_TRIGGERS.items():
            if any(keyword in message_lower for keyword in keywords):
                # Check if we recently searched for this venue
                last_search_time = self.last_search.get(f"{venue_name}_{search_type}")
                if last_search_time:
                    time_since = datetime.now() - last_search_time
                    if time_since < timedelta(minutes=5):  # Don't repeat search within 5 mins
                        return False, None
                
                return True, search_type
        
        return False, None
    
    def smart_search(self, message: str, venue_name: str, domain: str = None) -> Optional[Dict]:
        """
        Perform smart contextual email search
        """
        should_search, search_type = self.should_search_emails(message, venue_name)
        
        if not should_search:
            # Check if we have cached results
            cache_key = f"{venue_name}_latest"
            if cache_key in self.search_results_cache:
                return self.search_results_cache[cache_key]
            return None
        
        # Build specific search query based on type
        search_query = self._build_smart_query(message, venue_name, search_type)
        days_back = self.SEARCH_DEPTH.get(search_type, 30)
        
        # Perform search
        logger.info(f"Smart search triggered: {search_type} for {venue_name}")
        
        try:
            from gmail_client import gmail_client
            
            # Search with specific query
            emails = gmail_client.search_venue_emails(
                venue_name=venue_name,
                domain=domain,
                days_back=days_back
            )
            
            # Process results based on search type
            processed = self._process_search_results(emails, search_type, message)
            
            # Update tracking
            self.last_search[f"{venue_name}_{search_type}"] = datetime.now()
            self.search_results_cache[f"{venue_name}_latest"] = processed
            
            return processed
            
        except Exception as e:
            logger.error(f"Smart search failed: {e}")
            return None
    
    def _build_smart_query(self, message: str, venue_name: str, search_type: str) -> str:
        """
        Build optimized search query based on context
        """
        queries = []
        
        if search_type == 'contract':
            # Look for contract/pricing discussions
            queries = [
                f'"{venue_name}" contract',
                f'"{venue_name}" renewal',
                f'"{venue_name}" pricing',
                f'"{venue_name}" invoice'
            ]
        
        elif search_type == 'technical':
            # Extract specific issue mentioned
            issue_keywords = ['zone', 'offline', 'music', 'stopped', 'volume']
            for keyword in issue_keywords:
                if keyword in message.lower():
                    queries.append(f'"{venue_name}" {keyword}')
                    break
            else:
                queries.append(f'"{venue_name}" issue')
        
        elif search_type == 'follow_up':
            queries.append(f'"{venue_name}" follow')
        
        elif search_type == 'reference':
            # Try to extract what they're referencing
            if 'email' in message.lower():
                # Extract date references if any
                date_patterns = [
                    r'yesterday',
                    r'last week',
                    r'last month',
                    r'\d+ days? ago'
                ]
                for pattern in date_patterns:
                    if re.search(pattern, message.lower()):
                        queries.append(f'"{venue_name}"')
                        break
        
        else:
            # General history query
            queries.append(f'"{venue_name}"')
        
        return ' OR '.join(queries) if queries else venue_name
    
    def _process_search_results(self, emails: List[Dict], search_type: str, original_message: str) -> Dict:
        """
        Process and summarize search results based on type
        """
        if not emails:
            return {
                'found': False,
                'summary': None
            }
        
        result = {
            'found': True,
            'count': len(emails),
            'search_type': search_type
        }
        
        if search_type == 'contract':
            # Find most recent contract/pricing discussion
            contract_emails = [
                e for e in emails 
                if any(word in e.get('subject', '').lower() 
                      for word in ['contract', 'renewal', 'pricing', 'rate'])
            ]
            
            if contract_emails:
                latest = contract_emails[0]
                result['summary'] = f"Latest contract discussion: '{latest['subject']}' on {latest['date'][:10]}"
                result['details'] = {
                    'subject': latest['subject'],
                    'date': latest['date'],
                    'snippet': latest['snippet']
                }
            
        elif search_type == 'technical':
            # Find recent issues
            issues = []
            for email in emails[:5]:  # Last 5 relevant emails
                if any(word in email.get('snippet', '').lower() 
                      for word in ['issue', 'problem', 'offline', 'fixed']):
                    issues.append({
                        'subject': email['subject'],
                        'date': email['date'][:10],
                        'resolved': 'fixed' in email.get('snippet', '').lower() or 
                                  'resolved' in email.get('snippet', '').lower()
                    })
            
            if issues:
                result['summary'] = f"Found {len(issues)} technical issues in recent emails"
                result['issues'] = issues
        
        elif search_type == 'follow_up':
            # Get latest follow-up
            latest = emails[0]
            result['summary'] = f"Last follow-up: '{latest['subject']}' on {latest['date'][:10]}"
            result['last_contact'] = latest['date']
        
        else:
            # General summary
            result['summary'] = f"Found {len(emails)} emails about this venue in the last {self.SEARCH_DEPTH.get(search_type, 30)} days"
            result['last_contact'] = emails[0]['date'] if emails else None
        
        return result
    
    def format_for_bot(self, search_result: Dict) -> str:
        """
        Format search results for bot response
        """
        if not search_result or not search_result.get('found'):
            return None
        
        response = ""
        
        if search_result.get('search_type') == 'contract':
            if details := search_result.get('details'):
                response = f"📧 {search_result.get('summary', '')}\n"
                response += f"   Subject: {details['subject']}\n"
                response += f"   Preview: {details['snippet'][:150]}..."
        
        elif search_result.get('search_type') == 'technical':
            if issues := search_result.get('issues'):
                response = "📧 Recent technical issues:\n"
                for issue in issues[:3]:
                    status = "✅ Resolved" if issue['resolved'] else "⚠️ Open"
                    response += f"   • {issue['subject']} ({issue['date']}) {status}\n"
        
        else:
            response = f"📧 {search_result.get('summary', '')}"
        
        return response


# Global instance
smart_searcher = None

def init_smart_search():
    """Initialize smart searcher with gmail client"""
    global smart_searcher
    from gmail_client import gmail_client
    smart_searcher = SmartEmailSearcher(gmail_client)
    return smart_searcher
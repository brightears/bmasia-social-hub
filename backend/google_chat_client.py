"""
Google Chat integration for BMA Social
Send targeted notifications to specific department groups
"""

import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import asyncio
from enum import Enum

# Google Chat API imports
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    CHAT_AVAILABLE = True
except ImportError:
    CHAT_AVAILABLE = False
    logging.warning("Google Chat API not installed. Run: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")

logger = logging.getLogger(__name__)


class Department(Enum):
    """Department tags for categorizing messages"""
    SALES = "💰 Sales"
    OPERATIONS = "⚙️ Operations"
    DESIGN = "🎨 Design"
    FINANCE = "💳 Finance"
    GENERAL = "📢 General"


class Priority(Enum):
    """Message priority levels"""
    CRITICAL = "🔴"  # Immediate attention required
    HIGH = "🟡"      # Important but not critical
    NORMAL = "🟢"    # Regular notification
    INFO = "ℹ️"      # Information only


class GoogleChatClient:
    """Manage Google Chat notifications for BMA Social support"""
    
    # Single BMAsia All group space
    BMASIA_ALL_SPACE = os.getenv('GCHAT_BMASIA_ALL_SPACE', '')
    
    # Smart routing rules to categorize messages by department and priority
    ROUTING_RULES = {
        # Sales-related
        'renewal': (Department.SALES, Priority.HIGH),
        'contract': (Department.SALES, Priority.HIGH),
        'pricing': (Department.SALES, Priority.NORMAL),
        'new location': (Department.SALES, Priority.HIGH),
        'expansion': (Department.SALES, Priority.HIGH),
        'cancel': (Department.SALES, Priority.CRITICAL),
        'competitor': (Department.SALES, Priority.HIGH),
        'quote': (Department.SALES, Priority.NORMAL),
        'proposal': (Department.SALES, Priority.NORMAL),
        
        # Operations-related
        'all zones offline': (Department.OPERATIONS, Priority.CRITICAL),
        'zone offline': (Department.OPERATIONS, Priority.HIGH),
        'not playing': (Department.OPERATIONS, Priority.HIGH),
        'no music': (Department.OPERATIONS, Priority.HIGH),
        'technical issue': (Department.OPERATIONS, Priority.HIGH),
        'system down': (Department.OPERATIONS, Priority.CRITICAL),
        'error': (Department.OPERATIONS, Priority.NORMAL),
        'broken': (Department.OPERATIONS, Priority.HIGH),
        'hardware': (Department.OPERATIONS, Priority.HIGH),
        'speaker': (Department.OPERATIONS, Priority.NORMAL),
        'offline': (Department.OPERATIONS, Priority.HIGH),
        'connection': (Department.OPERATIONS, Priority.NORMAL),
        
        # Design-related
        'playlist': (Department.DESIGN, Priority.NORMAL),
        'music selection': (Department.DESIGN, Priority.NORMAL),
        'genre': (Department.DESIGN, Priority.NORMAL),
        'volume': (Department.DESIGN, Priority.NORMAL),
        'schedule': (Department.DESIGN, Priority.NORMAL),
        'song': (Department.DESIGN, Priority.NORMAL),
        
        # Finance-related
        'payment': (Department.FINANCE, Priority.HIGH),
        'invoice': (Department.FINANCE, Priority.NORMAL),
        'billing': (Department.FINANCE, Priority.NORMAL),
        'overdue': (Department.FINANCE, Priority.HIGH),
        'finance': (Department.FINANCE, Priority.NORMAL),
        'refund': (Department.FINANCE, Priority.HIGH),
        
        # Critical issues (any department)
        'urgent': (Department.GENERAL, Priority.CRITICAL),
        'emergency': (Department.GENERAL, Priority.CRITICAL),
        'immediate': (Department.GENERAL, Priority.CRITICAL),
        'unhappy': (Department.GENERAL, Priority.HIGH),
        'terrible': (Department.GENERAL, Priority.HIGH),
        'lawsuit': (Department.GENERAL, Priority.CRITICAL),
        'legal': (Department.GENERAL, Priority.CRITICAL),
    }
    
    def __init__(self):
        self.service = None
        self.space_verified = False
        self.connect()
    
    def connect(self):
        """Connect to Google Chat API using service account"""
        if not CHAT_AVAILABLE:
            logger.error("Google Chat API not available")
            return False
        
        try:
            # Use same credentials as other Google services
            creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
            if creds_json:
                creds_dict = json.loads(creds_json)
                SCOPES = ['https://www.googleapis.com/auth/chat.bot']
                
                credentials = service_account.Credentials.from_service_account_info(
                    creds_dict, 
                    scopes=SCOPES
                )
                
                self.service = build('chat', 'v1', credentials=credentials)
                logger.info("✅ Google Chat client initialized")
                
                # Verify space access
                self._verify_space()
                return True
            else:
                logger.warning("No Google credentials found")
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect to Google Chat: {e}")
            return False
    
    def _verify_space(self):
        """Verify access to BMAsia All Chat space"""
        if self.BMASIA_ALL_SPACE:
            try:
                # Test space access
                self.service.spaces().get(name=self.BMASIA_ALL_SPACE).execute()
                self.space_verified = True
                logger.info("✅ Verified access to BMAsia All space")
            except Exception as e:
                self.space_verified = False
                logger.warning(f"Cannot access BMAsia All space: {e}")
    
    def analyze_message(self, message: str, venue_name: str = None) -> tuple[Department, Priority]:
        """
        Analyze message content to determine routing
        Returns (Department, Priority)
        """
        message_lower = message.lower()
        
        # Check each routing rule
        best_match = (Department.OPERATIONS, Priority.NORMAL)  # Default
        
        for keyword, (dept, priority) in self.ROUTING_RULES.items():
            if keyword in message_lower:
                # Critical issues take precedence
                if priority == Priority.CRITICAL:
                    return (dept, priority)
                # Otherwise keep the highest priority match
                if priority.value < best_match[1].value:
                    best_match = (dept, priority)
        
        return best_match
    
    def send_notification(
        self,
        message: str,
        venue_name: str = None,
        venue_data: Dict = None,
        user_info: Dict = None,
        department: Department = None,
        priority: Priority = None,
        context: str = None
    ) -> bool:
        """
        Send a notification to BMAsia All Google Chat space
        
        Args:
            message: The user's message or issue description
            venue_name: Name of the venue reporting the issue
            venue_data: Additional venue data from sheets/API
            user_info: Information about the user (name, phone, platform)
            department: Department tag for categorization
            priority: Priority level for the message
            context: Additional context from the bot
        """
        if not self.service:
            logger.error("Google Chat not connected")
            return False
        
        # Determine categorization if not specified
        if not department or not priority:
            auto_dept, auto_priority = self.analyze_message(message, venue_name)
            department = department or auto_dept
            priority = priority or auto_priority
        
        # Check if space is configured and verified
        if not self.BMASIA_ALL_SPACE:
            logger.warning("No BMAsia All space configured")
            return False
        
        if not self.space_verified:
            logger.warning("Cannot access BMAsia All space")
            return False
        
        # Build the Chat message with department tag
        chat_message = self._build_chat_message(
            message, venue_name, venue_data, user_info, department, priority, context
        )
        
        try:
            # Send to Google Chat
            result = self.service.spaces().messages().create(
                parent=self.BMASIA_ALL_SPACE,
                body=chat_message
            ).execute()
            
            logger.info(f"✅ Notification sent to BMAsia All - {department.value} issue with {priority.value} priority")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Chat notification: {e}")
            return False
    
    def _build_chat_message(
        self,
        message: str,
        venue_name: str,
        venue_data: Dict,
        user_info: Dict,
        department: Department,
        priority: Priority,
        context: str
    ) -> Dict:
        """Build a formatted Google Chat message with card"""
        
        # Current time
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Build header with department tag and priority
        header_title = f"{priority.value} {department.value} - {venue_name or 'Unknown Venue'}"
        
        # Build the card sections
        sections = []
        
        # Main issue section
        sections.append({
            "header": "Issue Description",
            "widgets": [
                {
                    "textParagraph": {
                        "text": message
                    }
                }
            ]
        })
        
        # Venue information section
        if venue_name or venue_data:
            venue_widgets = []
            
            if venue_name:
                venue_widgets.append({
                    "keyValue": {
                        "topLabel": "Venue",
                        "content": venue_name
                    }
                })
            
            if venue_data:
                if venue_data.get('contract_end'):
                    venue_widgets.append({
                        "keyValue": {
                            "topLabel": "Contract Expires",
                            "content": venue_data['contract_end']
                        }
                    })
                
                if venue_data.get('zones'):
                    venue_widgets.append({
                        "keyValue": {
                            "topLabel": "Total Zones",
                            "content": str(venue_data['zones'])
                        }
                    })
                
                if venue_data.get('contact'):
                    venue_widgets.append({
                        "keyValue": {
                            "topLabel": "Contact",
                            "content": venue_data['contact']
                        }
                    })
            
            if venue_widgets:
                sections.append({
                    "header": "Venue Information",
                    "widgets": venue_widgets
                })
        
        # User information section
        if user_info:
            user_widgets = []
            
            if user_info.get('name'):
                user_widgets.append({
                    "keyValue": {
                        "topLabel": "Reported By",
                        "content": user_info['name']
                    }
                })
            
            if user_info.get('phone'):
                user_widgets.append({
                    "keyValue": {
                        "topLabel": "Phone",
                        "content": user_info['phone']
                    }
                })
            
            if user_info.get('platform'):
                user_widgets.append({
                    "keyValue": {
                        "topLabel": "Platform",
                        "content": user_info['platform']
                    }
                })
            
            if user_widgets:
                sections.append({
                    "header": "Contact Information",
                    "widgets": user_widgets
                })
        
        # Additional context section
        if context:
            sections.append({
                "header": "Bot Analysis",
                "widgets": [
                    {
                        "textParagraph": {
                            "text": context
                        }
                    }
                ]
            })
        
        # Add timestamp
        sections.append({
            "widgets": [
                {
                    "textParagraph": {
                        "text": f"<i>Received at {timestamp}</i>"
                    }
                }
            ]
        })
        
        # Build the complete message
        chat_message = {
            "cards": [
                {
                    "header": {
                        "title": header_title,
                        "subtitle": "BMA Social Support Bot Alert"
                    },
                    "sections": sections
                }
            ]
        }
        
        # For critical issues, also add a text message for immediate visibility
        if priority == Priority.CRITICAL:
            chat_message["text"] = f"🚨 URGENT: {message[:100]}..."
        
        return chat_message
    
    def send_batch_summary(self, issues: List[Dict]):
        """Send a summary of multiple issues (for daily/weekly reports)"""
        if not issues:
            return False
        
        # Build summary message
        summary_text = f"📊 Daily Issues Summary - {datetime.now().strftime('%Y-%m-%d')}\n\n"
        
        # Group by department
        by_dept = {}
        for issue in issues:
            dept = issue.get('department', Department.GENERAL)
            if dept not in by_dept:
                by_dept[dept] = []
            by_dept[dept].append(issue)
        
        # Show breakdown by department
        for dept, dept_issues in by_dept.items():
            summary_text += f"{dept.value} ({len(dept_issues)} issues):\n"
            
            # Group by priority within department
            critical = [i for i in dept_issues if i.get('priority') == Priority.CRITICAL]
            high = [i for i in dept_issues if i.get('priority') == Priority.HIGH]
            
            if critical:
                for issue in critical[:3]:  # Top 3 critical
                    summary_text += f"  🔴 {issue['venue']}: {issue['message'][:40]}...\n"
            
            if high:
                for issue in high[:2]:  # Top 2 high
                    summary_text += f"  🟡 {issue['venue']}: {issue['message'][:40]}...\n"
            
            summary_text += "\n"
        
        summary_text += f"📈 Total Issues Today: {len(issues)}\n"
        
        # Send summary
        return self.send_notification(
            message=summary_text,
            department=Department.GENERAL,
            priority=Priority.INFO,
            context="Automated daily summary"
        )


# Global instance
chat_client = GoogleChatClient()


# Helper functions for bot integration
def escalate_to_chat(
    message: str,
    venue_name: str = None,
    venue_data: Dict = None,
    force_department: str = None
) -> bool:
    """
    Quick helper to escalate an issue to Google Chat
    
    Args:
        message: The issue description
        venue_name: Name of the venue
        venue_data: Additional venue context
        force_department: Override routing (sales/operations/design/all)
    """
    if not chat_client.service:
        logger.warning("Google Chat not available for escalation")
        return False
    
    # Convert string department to enum if provided
    department = None
    if force_department:
        try:
            department = Department[force_department.upper()]
        except KeyError:
            logger.warning(f"Invalid department: {force_department}")
    
    return chat_client.send_notification(
        message=message,
        venue_name=venue_name,
        venue_data=venue_data,
        department=department
    )


def should_escalate(message: str) -> bool:
    """
    Determine if a message should be escalated to Google Chat
    Returns True for critical issues that need human intervention
    """
    critical_keywords = [
        'all zones offline',
        'system down',
        'urgent',
        'emergency',
        'cancel',
        'lawsuit',
        'unhappy customer',
        'completely broken'
    ]
    
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in critical_keywords)
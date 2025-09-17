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
    
    # Legacy spaces (kept for backward compatibility)
    BMASIA_ALL_SPACE = os.getenv('GCHAT_BMASIA_ALL_SPACE', '')
    CUSTOMER_SUPPORT_SPACE = os.getenv('GCHAT_CUSTOMER_SUPPORT_SPACE', 'spaces/AAQA1j6BK08')
    
    # Department-specific spaces for better organization
    TECHNICAL_SPACE = os.getenv('GCHAT_TECHNICAL_SPACE', '')  # Technical support & operations
    DESIGN_SPACE = os.getenv('GCHAT_DESIGN_SPACE', '')  # Music design & playlists
    SALES_SPACE = os.getenv('GCHAT_SALES_SPACE', '')  # Sales, finance & complaints
    
    # Smart routing rules to categorize messages by department and priority
    ROUTING_RULES = {
        # Sales-related (goes to SALES_SPACE)
        'renewal': (Department.SALES, Priority.HIGH),
        'contract': (Department.SALES, Priority.HIGH),
        'pricing': (Department.SALES, Priority.NORMAL),
        'new location': (Department.SALES, Priority.HIGH),
        'expansion': (Department.SALES, Priority.HIGH),
        'cancel': (Department.SALES, Priority.CRITICAL),
        'competitor': (Department.SALES, Priority.HIGH),
        'quote': (Department.SALES, Priority.NORMAL),
        'proposal': (Department.SALES, Priority.NORMAL),
        'prospect': (Department.SALES, Priority.NORMAL),
        'how much': (Department.SALES, Priority.NORMAL),
        'package': (Department.SALES, Priority.NORMAL),
        
        # Operations/Technical-related (goes to TECHNICAL_SPACE)
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
        'api': (Department.OPERATIONS, Priority.HIGH),
        'not working': (Department.OPERATIONS, Priority.HIGH),
        'crashed': (Department.OPERATIONS, Priority.CRITICAL),
        
        # Design-related (goes to DESIGN_SPACE)
        'playlist': (Department.DESIGN, Priority.NORMAL),
        'music selection': (Department.DESIGN, Priority.NORMAL),
        'genre': (Department.DESIGN, Priority.NORMAL),
        'volume': (Department.DESIGN, Priority.NORMAL),
        'schedule': (Department.DESIGN, Priority.NORMAL),
        'song': (Department.DESIGN, Priority.NORMAL),
        'event music': (Department.DESIGN, Priority.HIGH),
        'private event': (Department.DESIGN, Priority.HIGH),
        'party': (Department.DESIGN, Priority.HIGH),
        'wedding': (Department.DESIGN, Priority.HIGH),
        'block song': (Department.DESIGN, Priority.NORMAL),
        'music design': (Department.DESIGN, Priority.NORMAL),
        'atmosphere': (Department.DESIGN, Priority.NORMAL),
        'tomorrow': (Department.DESIGN, Priority.HIGH),  # Time-sensitive
        
        # Finance-related (goes to SALES_SPACE as Sales handles finance too)
        'payment': (Department.FINANCE, Priority.HIGH),
        'invoice': (Department.FINANCE, Priority.NORMAL),
        'billing': (Department.FINANCE, Priority.NORMAL),
        'overdue': (Department.FINANCE, Priority.HIGH),
        'finance': (Department.FINANCE, Priority.NORMAL),
        'refund': (Department.FINANCE, Priority.HIGH),
        'complaint': (Department.FINANCE, Priority.HIGH),
        'unhappy': (Department.FINANCE, Priority.HIGH),
        
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
            # Try to load credentials from various sources
            from google_credentials_loader import load_google_credentials
            creds_dict = load_google_credentials()
            
            if creds_dict:
                SCOPES = ['https://www.googleapis.com/auth/chat.bot']
                
                credentials = service_account.Credentials.from_service_account_info(
                    creds_dict, 
                    scopes=SCOPES
                )
                
                self.service = build('chat', 'v1', credentials=credentials)
                logger.info("✅ Google Chat client initialized with BMA Social Support Bot")
                
                # Verify space access
                self._verify_space()
                return True
            else:
                logger.warning("No Google credentials found - notifications disabled")
                logger.warning("To enable: Add bamboo-theorem-399923-credentials.json or set GOOGLE_CREDENTIALS_JSON")
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect to Google Chat: {e}")
            return False
    
    def _verify_space(self):
        """Verify access to all configured Google Chat spaces"""
        spaces_to_verify = [
            (self.CUSTOMER_SUPPORT_SPACE, "Customer Support"),
            (self.TECHNICAL_SPACE, "Technical Support"),
            (self.DESIGN_SPACE, "Music Design"),
            (self.SALES_SPACE, "Sales & Finance")
        ]
        
        verified_count = 0
        for space_id, space_name in spaces_to_verify:
            if space_id:
                try:
                    # Test space access
                    self.service.spaces().get(name=space_id).execute()
                    verified_count += 1
                    logger.info(f"✅ Verified access to {space_name} space")
                except Exception as e:
                    logger.warning(f"Cannot access {space_name} space: {e}")
        
        # Consider verified if at least one space is accessible
        self.space_verified = verified_count > 0
        if self.space_verified:
            logger.info(f"✅ Successfully verified {verified_count} Google Chat space(s)")
        else:
            logger.error("❌ No Google Chat spaces are accessible")
    
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
    
    def _get_target_space(self, department: Department) -> str:
        """
        Get the target Google Chat space based on department
        Returns the space ID or None if not configured
        """
        # Map departments to their respective spaces
        space_mapping = {
            Department.OPERATIONS: self.TECHNICAL_SPACE,  # Technical issues go to tech space
            Department.DESIGN: self.DESIGN_SPACE,  # Music design goes to design space
            Department.SALES: self.SALES_SPACE,  # Sales inquiries go to sales space
            Department.FINANCE: self.SALES_SPACE,  # Finance also goes to sales space
            Department.GENERAL: self.CUSTOMER_SUPPORT_SPACE,  # General goes to default space
        }
        
        # Get the space for this department
        target_space = space_mapping.get(department)
        
        # If specific space not configured, fallback to Customer Support space
        if not target_space:
            logger.info(f"No specific space for {department.value}, using Customer Support space")
            target_space = self.CUSTOMER_SUPPORT_SPACE
        
        return target_space
    
    def _get_space_name(self, space_id: str) -> str:
        """
        Get a friendly name for the space based on its ID
        """
        if space_id == self.TECHNICAL_SPACE:
            return "Technical Support"
        elif space_id == self.DESIGN_SPACE:
            return "Music Design"
        elif space_id == self.SALES_SPACE:
            return "Sales & Finance"
        elif space_id == self.CUSTOMER_SUPPORT_SPACE:
            return "Customer Support"
        elif space_id == self.BMASIA_ALL_SPACE:
            return "BMAsia All"
        else:
            return "Support"
    
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
        
        # Determine which space to send to based on department
        target_space = self._get_target_space(department)
        
        if not target_space:
            logger.warning(f"No space configured for department {department.value}")
            # Fallback to Customer Support space if available
            target_space = self.CUSTOMER_SUPPORT_SPACE
            if not target_space:
                logger.error("No fallback space available")
                return False
        
        # Create thread key for conversation tracking
        customer_phone = user_info.get('phone', 'unknown')
        customer_name = user_info.get('name', 'Customer')
        platform = user_info.get('platform', 'WhatsApp')
        thread_key = f"{platform.lower()}_{customer_phone}_{venue_name}".replace(" ", "_").replace("+", "")
        
        # Track the conversation
        from conversation_tracker import conversation_tracker
        conversation_tracker.create_conversation(
            customer_phone=customer_phone,
            customer_name=customer_name,
            venue_name=venue_name or "Unknown Venue",
            platform=platform,
            thread_key=thread_key
        )
        
        # Add the initial message to conversation history
        conversation_tracker.add_message(
            thread_key=thread_key,
            message=message,
            sender=customer_name,
            direction="inbound"
        )
        
        # Build the Chat message with department tag
        chat_message = self._build_chat_message(
            message, venue_name, venue_data, user_info, department, priority, context, thread_key
        )
        
        # Add instruction for two-way communication
        chat_message["text"] = f"{chat_message.get('text', '')}\n\n💬 Reply in this thread to respond to the customer"
        
        try:
            # Send to the appropriate department space
            result = self.service.spaces().messages().create(
                parent=target_space,
                body=chat_message,
                threadKey=thread_key
            ).execute()
            
            space_name = self._get_space_name(target_space)
            logger.info(f"✅ Notification sent to {space_name} - {department.value} issue with {priority.value} priority")
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
        context: str,
        thread_key: str = None
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
                    # Format zones properly
                    zones_text = ', '.join(venue_data['zones']) if isinstance(venue_data['zones'], list) else str(venue_data['zones'])
                    venue_widgets.append({
                        "keyValue": {
                            "topLabel": "Total Zones",
                            "content": zones_text
                        }
                    })

                if venue_data.get('platform'):
                    venue_widgets.append({
                        "keyValue": {
                            "topLabel": "Music Platform",
                            "content": venue_data['platform']
                        }
                    })

                if venue_data.get('hardware_type'):
                    venue_widgets.append({
                        "keyValue": {
                            "topLabel": "Hardware Type",
                            "content": venue_data['hardware_type']
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
        
        # Add reply button
        sections.append({
            "widgets": [
                {
                    "buttons": [
                        {
                            "textButton": {
                                "text": "📝 Reply to Customer",
                                "onClick": {
                                    "openLink": {
                                        "url": f"https://bma-social-api-q9uu.onrender.com/reply/{thread_key}"
                                    }
                                }
                            }
                        }
                    ]
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
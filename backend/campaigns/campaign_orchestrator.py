"""
Campaign Orchestrator - Main campaign management interface
Coordinates AI, customer data, and sending for BMA Social campaigns
"""

import os
import json
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from campaigns.campaign_ai import AICampaignManager
from campaigns.customer_manager import CustomerManager
from campaigns.campaign_sender import CampaignSender

logger = logging.getLogger(__name__)


class CampaignOrchestrator:
    """
    Main orchestrator for AI-powered campaigns
    Coordinates between AI brain, customer data, and multi-channel sending
    """

    def __init__(self):
        self.ai_manager = AICampaignManager()
        self.customer_manager = CustomerManager()
        self.sender = CampaignSender()
        self.active_campaigns = {}

    def create_campaign(
        self,
        campaign_type: str,
        filters: Dict[str, Any] = None,
        context: str = None,
        human_request: str = None
    ) -> Dict[str, Any]:
        """
        Create new AI-powered campaign

        Args:
            campaign_type: renewal, seasonal, announcement, etc.
            filters: Customer filtering criteria
            context: Additional context for AI
            human_request: Original human request in natural language

        Returns:
            Campaign object with ID and details
        """

        campaign_id = str(uuid.uuid4())
        logger.info(f"Creating campaign {campaign_id} - Type: {campaign_type}")

        # If human request provided, let AI interpret it
        if human_request:
            filters, campaign_type = self._interpret_human_request(human_request)

        # Get AI to create campaign strategy
        campaign_plan = self.ai_manager.create_campaign(
            campaign_type=campaign_type,
            filters=filters or {},
            context=context
        )

        # Filter customers based on criteria
        target_customers = self.customer_manager.filter_customers(filters or {})
        logger.info(f"Found {len(target_customers)} customers matching filters")

        # Generate messages for each customer
        messages_by_customer = {}
        for customer in target_customers:
            messages = self.ai_manager.compose_message(
                customer=customer,
                campaign_type=campaign_type,
                campaign_context=campaign_plan
            )
            messages_by_customer[customer['customer_id']] = messages

        # Create campaign object
        campaign = {
            'id': campaign_id,
            'type': campaign_type,
            'plan': campaign_plan,
            'filters': filters,
            'human_request': human_request,
            'target_customers': target_customers,
            'messages': messages_by_customer,
            'status': 'draft',
            'created_at': datetime.now().isoformat(),
            'created_by': 'AI Campaign Manager',
            'statistics': {
                'total_customers': len(target_customers),
                'total_zones': sum(c['total_zones'] for c in target_customers),
                'by_brand': self._count_by_brand(target_customers),
                'by_platform': self._count_by_platform(target_customers)
            }
        }

        self.active_campaigns[campaign_id] = campaign
        logger.info(f"Campaign {campaign_id} created successfully")

        return campaign

    def preview_campaign(self, campaign_id: str, sample_size: int = 3) -> Dict[str, Any]:
        """
        Preview campaign with sample messages

        Args:
            campaign_id: Campaign to preview
            sample_size: Number of sample messages to show

        Returns:
            Preview with sample messages and statistics
        """

        campaign = self.active_campaigns.get(campaign_id)
        if not campaign:
            return {'error': 'Campaign not found'}

        # Get sample customers
        sample_customers = campaign['target_customers'][:sample_size]
        sample_messages = []

        for customer in sample_customers:
            customer_id = customer['customer_id']
            messages = campaign['messages'].get(customer_id, {})

            sample_messages.append({
                'customer': customer['name'],
                'brand': customer.get('brand', 'Independent'),
                'zones': customer.get('zones', []),
                'contact': customer.get('primary_contact', {}).get('name', 'Unknown'),
                'whatsapp': messages.get('whatsapp', '')[:200] + '...',
                'email_subject': messages.get('email_subject', ''),
                'channels': self._determine_channels(customer)
            })

        return {
            'campaign_id': campaign_id,
            'type': campaign['type'],
            'plan': campaign['plan'],
            'statistics': campaign['statistics'],
            'sample_messages': sample_messages,
            'total_customers': len(campaign['target_customers']),
            'estimated_sends': {
                'whatsapp': self._count_channel(campaign['target_customers'], 'whatsapp'),
                'line': self._count_channel(campaign['target_customers'], 'line'),
                'email': self._count_channel(campaign['target_customers'], 'email')
            }
        }

    def send_campaign(
        self,
        campaign_id: str,
        channels: List[str] = None,
        test_mode: bool = False,
        schedule_time: str = None
    ) -> Dict[str, Any]:
        """
        Execute campaign sending

        Args:
            campaign_id: Campaign to send
            channels: Channels to use (default: all available)
            test_mode: Send to first customer only
            schedule_time: ISO format time to schedule (optional)

        Returns:
            Send results
        """

        campaign = self.active_campaigns.get(campaign_id)
        if not campaign:
            return {'error': 'Campaign not found'}

        # Default channels if not specified
        if not channels:
            channels = ['whatsapp', 'email']  # Line requires prior interaction

        logger.info(f"Sending campaign {campaign_id} via {channels}")

        # Update status
        campaign['status'] = 'sending'
        campaign['sent_at'] = datetime.now().isoformat()

        # Prepare recipients with their messages
        results = {
            'campaign_id': campaign_id,
            'channels': channels,
            'results_by_customer': []
        }

        total_sent = 0
        total_failed = 0

        # Send to each customer
        for customer in campaign['target_customers']:
            customer_id = customer['customer_id']
            messages = campaign['messages'].get(customer_id, {})

            # Determine available channels for this customer
            available_channels = self._determine_channels(customer)
            send_channels = [c for c in channels if c in available_channels]

            if not send_channels:
                logger.warning(f"No valid channels for {customer['name']}")
                continue

            # Send campaign
            send_result = self.sender.send_campaign(
                recipients=[customer],
                messages=messages,
                channels=send_channels,
                campaign_id=campaign_id,
                test_mode=test_mode
            )

            # Track results
            customer_result = {
                'customer': customer['name'],
                'channels_used': send_channels,
                'sent': send_result.get('sent', {}),
                'failed': send_result.get('failed', {})
            }

            results['results_by_customer'].append(customer_result)

            # Update totals
            for channel in send_channels:
                total_sent += send_result.get('sent', {}).get(channel, 0)
                total_failed += send_result.get('failed', {}).get(channel, 0)

            # Test mode - stop after first
            if test_mode:
                break

        # Update campaign status
        campaign['status'] = 'completed' if not test_mode else 'tested'
        campaign['results'] = {
            'total_sent': total_sent,
            'total_failed': total_failed,
            'details': results
        }

        # Generate AI report
        report = self.ai_manager.generate_campaign_report(
            campaign_data={
                'name': campaign['plan'].get('campaign_name', 'Campaign'),
                'type': campaign['type'],
                'recipients_count': len(campaign['target_customers']),
                'sent': total_sent,
                'failed': total_failed
            },
            responses=[]  # Will be populated as responses come in
        )

        results['ai_report'] = report

        logger.info(f"Campaign {campaign_id} completed - Sent: {total_sent}, Failed: {total_failed}")
        return results

    def handle_campaign_response(
        self,
        phone_or_email: str,
        message: str,
        channel: str
    ) -> Dict[str, Any]:
        """
        Handle response to campaign message

        Args:
            phone_or_email: Sender identifier
            message: Response message
            channel: Channel response came from

        Returns:
            AI analysis and suggested action
        """

        # Find relevant campaign and customer
        campaign_found = None
        customer_found = None

        for campaign_id, campaign in self.active_campaigns.items():
            for customer in campaign['target_customers']:
                # Check if this customer matches
                if self._match_customer_contact(customer, phone_or_email, channel):
                    campaign_found = campaign
                    customer_found = customer
                    break

        if not campaign_found:
            return {
                'status': 'no_campaign_found',
                'action': 'treat_as_general_inquiry'
            }

        # AI analyzes response
        analysis = self.ai_manager.analyze_response(
            response_text=message,
            campaign_context=campaign_found['plan'],
            customer_context=customer_found
        )

        # Log response
        if 'responses' not in campaign_found:
            campaign_found['responses'] = []

        campaign_found['responses'].append({
            'customer': customer_found['name'],
            'channel': channel,
            'message': message,
            'analysis': analysis,
            'timestamp': datetime.now().isoformat()
        })

        logger.info(f"Campaign response from {customer_found['name']} - Intent: {analysis['intent']}")

        return {
            'campaign_id': campaign_found['id'],
            'customer': customer_found['name'],
            'analysis': analysis,
            'suggested_action': analysis.get('next_action'),
            'suggested_reply': analysis.get('suggested_reply')
        }

    def _interpret_human_request(self, request: str) -> tuple:
        """
        Interpret natural language request into filters and campaign type

        Args:
            request: Human natural language request

        Returns:
            (filters, campaign_type) tuple
        """

        # Let AI interpret the request
        prompt = f"""Interpret this campaign request into filters and type:

Request: "{request}"

Determine:
1. Campaign type (renewal, seasonal, announcement, follow_up, survey)
2. Filters to apply

Return JSON with:
{{
    "campaign_type": "type",
    "filters": {{
        "brand": "brand name if mentioned",
        "business_type": "Hotel/Restaurant/etc if mentioned",
        "region": "region if mentioned",
        "contract_expiry": {{"days": number}} if renewal mentioned,
        "platform": "SYB/Beat Breeze if mentioned"
    }}
}}"""

        try:
            response = self.ai_manager.openai.chat.completions.create(
                model=self.ai_manager.model,
                messages=[
                    {"role": "system", "content": "You interpret campaign requests."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            return result.get('filters', {}), result.get('campaign_type', 'general')

        except Exception as e:
            logger.error(f"Error interpreting request: {e}")
            return {}, 'general'

    def _count_by_brand(self, customers: List[Dict]) -> Dict[str, int]:
        """Count customers by brand"""
        brands = {}
        for customer in customers:
            brand = customer.get('brand', 'Independent')
            brands[brand] = brands.get(brand, 0) + 1
        return brands

    def _count_by_platform(self, customers: List[Dict]) -> Dict[str, int]:
        """Count customers by platform"""
        platforms = {}
        for customer in customers:
            platform = customer.get('platform', 'Unknown')
            platforms[platform] = platforms.get(platform, 0) + 1
        return platforms

    def _determine_channels(self, customer: Dict) -> List[str]:
        """Determine available channels for customer"""
        channels = []

        # Check for contact methods
        if customer.get('primary_contact'):
            contact = customer['primary_contact']
            if contact.get('phone'):
                channels.append('whatsapp')
            if contact.get('email'):
                channels.append('email')

        # Line requires prior interaction (would check database)
        if customer.get('line_user_id'):
            channels.append('line')

        return channels

    def _count_channel(self, customers: List[Dict], channel: str) -> int:
        """Count customers with specific channel available"""
        count = 0
        for customer in customers:
            if channel in self._determine_channels(customer):
                count += 1
        return count

    def _match_customer_contact(
        self,
        customer: Dict,
        identifier: str,
        channel: str
    ) -> bool:
        """Check if identifier matches customer contact"""
        if customer.get('primary_contact'):
            contact = customer['primary_contact']

            if channel == 'whatsapp' and contact.get('phone'):
                # Clean and compare phone
                clean_phone = ''.join(filter(str.isdigit, contact['phone']))
                clean_identifier = ''.join(filter(str.isdigit, identifier))
                return clean_phone == clean_identifier

            if channel == 'email' and contact.get('email'):
                return contact['email'].lower() == identifier.lower()

            if channel == 'line' and customer.get('line_user_id'):
                return customer['line_user_id'] == identifier

        return False

    def get_campaign_statistics(self) -> Dict[str, Any]:
        """Get overall campaign statistics"""
        return {
            'active_campaigns': len(self.active_campaigns),
            'customer_statistics': self.customer_manager.get_statistics(),
            'send_statistics': self.sender.get_send_statistics(),
            'campaigns_by_type': self._count_campaigns_by_type(),
            'campaigns_by_status': self._count_campaigns_by_status()
        }

    def _count_campaigns_by_type(self) -> Dict[str, int]:
        """Count campaigns by type"""
        types = {}
        for campaign in self.active_campaigns.values():
            campaign_type = campaign.get('type', 'unknown')
            types[campaign_type] = types.get(campaign_type, 0) + 1
        return types

    def _count_campaigns_by_status(self) -> Dict[str, int]:
        """Count campaigns by status"""
        statuses = {}
        for campaign in self.active_campaigns.values():
            status = campaign.get('status', 'unknown')
            statuses[status] = statuses.get(status, 0) + 1
        return statuses
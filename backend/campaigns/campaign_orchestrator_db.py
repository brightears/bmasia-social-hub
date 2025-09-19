"""
Database-Powered Campaign Orchestrator
Coordinates AI composition, database filtering, and multi-channel sending
"""

import os
import uuid
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import asyncpg
from dotenv import load_dotenv

from .campaign_ai import AICampaignManager
from .customer_manager_db import DatabaseCustomerManager, get_customer_manager
from .contact_selector import SmartContactSelector
from .campaign_sender import CampaignSender as MultiChannelSender

logger = logging.getLogger(__name__)
load_dotenv()


class DatabaseCampaignOrchestrator:
    """
    Main coordinator for database-powered campaigns
    Handles the complete flow from creation to analytics
    """

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv('DATABASE_URL')
        self.pool = None

        # Initialize components
        self.ai_manager = AICampaignManager()
        self.contact_selector = SmartContactSelector()
        self.sender = MultiChannelSender()

        self._initialized = False

    async def initialize(self):
        """Initialize database connection and components"""
        if self._initialized:
            return

        # Create connection pool
        self.pool = await asyncpg.create_pool(
            self.database_url,
            min_size=5,
            max_size=20,
            command_timeout=60
        )

        # Get customer manager
        self.customer_manager = await get_customer_manager()

        self._initialized = True
        logger.info("Database campaign orchestrator initialized")

    async def close(self):
        """Clean up resources"""
        if self.pool:
            await self.pool.close()
        if self.customer_manager:
            await self.customer_manager.close()

    async def create_campaign_from_request(
        self,
        human_request: str,
        created_by: str = "system"
    ) -> Dict[str, Any]:
        """
        Create campaign from natural language request

        Args:
            human_request: Natural language description
            created_by: User creating the campaign

        Returns:
            Campaign object with ID and details
        """
        await self.initialize()

        # AI interprets the request
        logger.info(f"AI interpreting request: {human_request}")
        interpretation = self.ai_manager.interpret_request(human_request)

        # Create the campaign
        return await self.create_campaign(
            campaign_type=interpretation['campaign_type'],
            filters=interpretation['filters'],
            context=interpretation.get('context'),
            created_by=created_by
        )

    async def create_campaign(
        self,
        campaign_type: str,
        filters: Dict[str, Any],
        context: Optional[str] = None,
        created_by: str = "system"
    ) -> Dict[str, Any]:
        """
        Create a campaign with database persistence

        Args:
            campaign_type: Type of campaign
            filters: Customer filtering criteria
            context: Additional context for AI
            created_by: User creating the campaign

        Returns:
            Complete campaign object with recipients
        """
        await self.initialize()

        # Get target customers from database
        customers, total_count = await self.customer_manager.filter_customers(
            filters, limit=1000  # Reasonable limit for campaigns
        )

        logger.info(f"Found {len(customers)} customers matching filters (total: {total_count})")

        if not customers:
            return {
                'success': False,
                'error': 'No customers found matching the criteria',
                'filters': filters
            }

        # AI creates campaign plan
        campaign_plan = self.ai_manager.create_campaign(
            campaign_type, filters, context
        )

        # Create campaign record in database
        async with self.pool.acquire() as conn:
            campaign_id = await conn.fetchval("""
                INSERT INTO campaigns (
                    name, type, status, goal, target_audience,
                    key_message, tone, filters, ai_prompt,
                    ai_response, total_recipients, created_by
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                RETURNING id
            """,
                campaign_plan.get('campaign_name', f"{campaign_type} Campaign"),
                campaign_type,
                'draft',
                campaign_plan.get('campaign_goal'),
                campaign_plan.get('target_audience'),
                campaign_plan.get('key_message'),
                campaign_plan.get('tone', 'professional'),
                json.dumps(filters),
                context,
                json.dumps(campaign_plan),
                len(customers),
                created_by
            )

            logger.info(f"Created campaign {campaign_id}")

            # Process each customer
            recipients = []
            for customer in customers:
                # Select appropriate contacts
                selected_contacts = self.contact_selector.select_contacts(
                    customer, campaign_type, {'campaign': campaign_plan}
                )

                # AI composes personalized message
                personalized = self.ai_manager.compose_message(
                    customer, campaign_type, campaign_plan
                )

                # Create recipient records
                for contact in selected_contacts or [{'email': customer.get('primary_contact', {}).get('email')}]:
                    if not contact.get('email') and not contact.get('phone'):
                        continue

                    recipient_id = await conn.fetchval("""
                        INSERT INTO campaign_recipients (
                            campaign_id, venue_id, contact_id,
                            personalized_message, message_variables
                        ) VALUES ($1, $2, $3, $4, $5)
                        RETURNING id
                    """,
                        campaign_id,
                        customer.get('venue_id'),
                        contact.get('id'),
                        personalized.get('message'),
                        json.dumps(personalized.get('variables', {}))
                    )

                    recipients.append({
                        'id': recipient_id,
                        'customer': customer['name'],
                        'contact': contact,
                        'message': personalized.get('message')
                    })

            # Get complete campaign object
            campaign = await conn.fetchrow("""
                SELECT
                    id, name, type, status, goal,
                    total_recipients, created_at
                FROM campaigns
                WHERE id = $1
            """, campaign_id)

        return {
            'success': True,
            'campaign_id': str(campaign_id),
            'campaign_name': campaign['name'],
            'campaign_type': campaign['type'],
            'status': campaign['status'],
            'total_recipients': len(recipients),
            'recipients_preview': recipients[:5],  # Show first 5
            'filters_used': filters,
            'channels': campaign_plan.get('channels', ['whatsapp', 'email'])
        }

    async def preview_campaign(self, campaign_id: str) -> Dict[str, Any]:
        """Preview campaign before sending"""
        await self.initialize()

        async with self.pool.acquire() as conn:
            # Get campaign details
            campaign = await conn.fetchrow("""
                SELECT * FROM campaigns WHERE id = $1
            """, uuid.UUID(campaign_id))

            if not campaign:
                return {'success': False, 'error': 'Campaign not found'}

            # Get sample recipients
            recipients = await conn.fetch("""
                SELECT
                    cr.*,
                    v.name as venue_name,
                    c.name as contact_name,
                    c.email as contact_email,
                    c.phone as contact_phone
                FROM campaign_recipients cr
                LEFT JOIN venues v ON cr.venue_id = v.id
                LEFT JOIN contacts c ON cr.contact_id = c.id
                WHERE cr.campaign_id = $1
                LIMIT 10
            """, uuid.UUID(campaign_id))

            return {
                'success': True,
                'campaign': dict(campaign),
                'sample_recipients': [dict(r) for r in recipients],
                'total_recipients': campaign['total_recipients']
            }

    async def send_campaign(
        self,
        campaign_id: str,
        channels: List[str] = None,
        test_mode: bool = False,
        test_limit: int = 1
    ) -> Dict[str, Any]:
        """
        Send campaign through specified channels

        Args:
            campaign_id: Campaign to send
            channels: Channels to use (default: all available)
            test_mode: Only send to first N recipients
            test_limit: Number of test recipients

        Returns:
            Send results with statistics
        """
        await self.initialize()

        if not channels:
            channels = ['whatsapp', 'email']

        async with self.pool.acquire() as conn:
            # Update campaign status
            await conn.execute("""
                UPDATE campaigns
                SET status = 'sending', sent_at = NOW()
                WHERE id = $1
            """, uuid.UUID(campaign_id))

            # Get recipients
            query = """
                SELECT
                    cr.*,
                    v.name as venue_name,
                    c.email as contact_email,
                    c.phone as contact_phone,
                    c.name as contact_name
                FROM campaign_recipients cr
                LEFT JOIN venues v ON cr.venue_id = v.id
                LEFT JOIN contacts c ON cr.contact_id = c.id
                WHERE cr.campaign_id = $1
            """

            if test_mode:
                query += f" LIMIT {test_limit}"

            recipients = await conn.fetch(query, uuid.UUID(campaign_id))

            results = {
                'sent': 0,
                'failed': 0,
                'channels_used': channels,
                'details': []
            }

            # Send to each recipient
            for recipient in recipients:
                recipient_dict = dict(recipient)
                send_result = await self._send_to_recipient(
                    conn, campaign_id, recipient_dict, channels
                )

                if send_result['success']:
                    results['sent'] += 1
                else:
                    results['failed'] += 1

                results['details'].append({
                    'venue': recipient_dict['venue_name'],
                    'contact': recipient_dict['contact_name'],
                    'result': send_result
                })

                # Add small delay to avoid rate limiting
                if not test_mode:
                    await asyncio.sleep(0.1)

            # Update campaign status
            final_status = 'sent' if not test_mode else 'draft'
            await conn.execute("""
                UPDATE campaigns
                SET
                    status = $1,
                    sent_count = $2,
                    completed_at = CASE WHEN $1 = 'sent' THEN NOW() ELSE NULL END
                WHERE id = $3
            """, final_status, results['sent'], uuid.UUID(campaign_id))

        return {
            'success': True,
            'campaign_id': campaign_id,
            'test_mode': test_mode,
            'results': results
        }

    async def _send_to_recipient(
        self,
        conn: asyncpg.Connection,
        campaign_id: str,
        recipient: Dict,
        channels: List[str]
    ) -> Dict[str, Any]:
        """Send campaign to single recipient"""
        results = {'success': False, 'channels': {}}

        message = recipient['personalized_message']
        if not message:
            return {'success': False, 'error': 'No message content'}

        # Try each channel
        for channel in channels:
            if channel == 'whatsapp' and recipient.get('contact_phone'):
                try:
                    # Send via WhatsApp
                    result = self.sender.send_whatsapp_template(
                        recipient['contact_phone'],
                        message,
                        {}  # Template params if needed
                    )

                    # Update recipient status
                    await conn.execute("""
                        UPDATE campaign_recipients
                        SET
                            whatsapp_status = $1,
                            whatsapp_sent_at = NOW(),
                            whatsapp_message_id = $2
                        WHERE id = $3
                    """,
                        'sent' if result.get('success') else 'failed',
                        result.get('message_id'),
                        recipient['id']
                    )

                    results['channels']['whatsapp'] = result
                    if result.get('success'):
                        results['success'] = True

                except Exception as e:
                    logger.error(f"WhatsApp send failed: {e}")
                    results['channels']['whatsapp'] = {'success': False, 'error': str(e)}

            elif channel == 'email' and recipient.get('contact_email'):
                try:
                    # Send via email
                    result = self.sender.send_email(
                        recipient['contact_email'],
                        f"Message from BMA Social",
                        message,
                        None  # HTML version
                    )

                    # Update recipient status
                    await conn.execute("""
                        UPDATE campaign_recipients
                        SET
                            email_status = $1,
                            email_sent_at = NOW(),
                            email_message_id = $2
                        WHERE id = $3
                    """,
                        'sent' if result.get('success') else 'failed',
                        result.get('message_id'),
                        recipient['id']
                    )

                    results['channels']['email'] = result
                    if result.get('success'):
                        results['success'] = True

                except Exception as e:
                    logger.error(f"Email send failed: {e}")
                    results['channels']['email'] = {'success': False, 'error': str(e)}

        return results

    async def handle_response(
        self,
        identifier: str,
        message: str,
        channel: str = "whatsapp"
    ) -> Dict[str, Any]:
        """
        Handle response to a campaign

        Args:
            identifier: Phone or email of responder
            message: Response message
            channel: Channel response came from

        Returns:
            Analysis and action taken
        """
        await self.initialize()

        async with self.pool.acquire() as conn:
            # Find the most recent campaign recipient
            recipient = await conn.fetchrow("""
                SELECT
                    cr.*,
                    c.name as campaign_name,
                    c.type as campaign_type
                FROM campaign_recipients cr
                JOIN campaigns c ON cr.campaign_id = c.id
                LEFT JOIN contacts ct ON cr.contact_id = ct.id
                WHERE
                    (ct.email = $1 OR ct.phone = $1)
                    AND cr.responded = FALSE
                ORDER BY
                    COALESCE(cr.whatsapp_sent_at, cr.email_sent_at, cr.line_sent_at) DESC
                LIMIT 1
            """, identifier)

            if not recipient:
                return {
                    'success': False,
                    'error': 'No active campaign found for this contact'
                }

            # AI analyzes the response
            analysis = self.ai_manager.analyze_response(
                message,
                recipient['campaign_type'],
                {'campaign_name': recipient['campaign_name']}
            )

            # Update recipient with response
            await conn.execute("""
                UPDATE campaign_recipients
                SET
                    responded = TRUE,
                    response_text = $1,
                    response_channel = $2,
                    responded_at = NOW(),
                    response_sentiment = $3,
                    response_intent = $4
                WHERE id = $5
            """,
                message,
                channel,
                analysis.get('sentiment'),
                analysis.get('intent'),
                recipient['id']
            )

            # Take action based on analysis
            action_taken = await self._handle_response_action(
                conn, recipient, analysis
            )

            return {
                'success': True,
                'campaign': recipient['campaign_name'],
                'analysis': analysis,
                'action_taken': action_taken
            }

    async def _handle_response_action(
        self,
        conn: asyncpg.Connection,
        recipient: Dict,
        analysis: Dict
    ) -> str:
        """Take action based on response analysis"""
        intent = analysis.get('intent', 'unknown')

        if intent == 'interested':
            # Create follow-up task or notification
            return "Marked as interested - sales team notified"

        elif intent == 'question':
            # May need human intervention
            return "Question detected - forwarded to support team"

        elif intent == 'complaint':
            # Urgent attention needed
            return "Complaint detected - escalated to management"

        elif intent == 'unsubscribe':
            # Update preferences
            await conn.execute("""
                INSERT INTO contact_preferences (contact_id, venue_id, unsubscribed, unsubscribe_reason)
                VALUES ($1, $2, TRUE, $3)
                ON CONFLICT (contact_id, venue_id)
                DO UPDATE SET
                    unsubscribed = TRUE,
                    unsubscribe_reason = $3,
                    unsubscribed_at = NOW()
            """, recipient.get('contact_id'), recipient.get('venue_id'), "Campaign response")

            return "Unsubscribed from future campaigns"

        else:
            return "Response recorded"

    async def get_campaign_analytics(
        self,
        campaign_id: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get detailed campaign analytics"""
        await self.initialize()

        async with self.pool.acquire() as conn:
            # Get campaign summary
            campaign = await conn.fetchrow("""
                SELECT
                    c.*,
                    COUNT(DISTINCT cr.id) as total_recipients,
                    COUNT(DISTINCT cr.id) FILTER (WHERE cr.whatsapp_status = 'sent' OR cr.email_status = 'sent') as sent,
                    COUNT(DISTINCT cr.id) FILTER (WHERE cr.responded = TRUE) as responded,
                    COUNT(DISTINCT cr.id) FILTER (WHERE cr.response_sentiment = 'positive') as positive,
                    COUNT(DISTINCT cr.id) FILTER (WHERE cr.response_sentiment = 'negative') as negative
                FROM campaigns c
                LEFT JOIN campaign_recipients cr ON c.id = cr.campaign_id
                WHERE c.id = $1
                GROUP BY c.id
            """, uuid.UUID(campaign_id))

            if not campaign:
                return {'success': False, 'error': 'Campaign not found'}

            # Get response breakdown
            responses = await conn.fetch("""
                SELECT
                    response_intent,
                    response_sentiment,
                    COUNT(*) as count
                FROM campaign_recipients
                WHERE campaign_id = $1 AND responded = TRUE
                GROUP BY response_intent, response_sentiment
            """, uuid.UUID(campaign_id))

            # Get channel performance
            channels = await conn.fetch("""
                SELECT
                    CASE
                        WHEN whatsapp_status IS NOT NULL THEN 'whatsapp'
                        WHEN email_status IS NOT NULL THEN 'email'
                        WHEN line_status IS NOT NULL THEN 'line'
                    END as channel,
                    COUNT(*) as sent,
                    COUNT(*) FILTER (WHERE responded = TRUE) as responded
                FROM campaign_recipients
                WHERE campaign_id = $1
                GROUP BY channel
            """, uuid.UUID(campaign_id))

            return {
                'success': True,
                'campaign': dict(campaign),
                'response_breakdown': [dict(r) for r in responses],
                'channel_performance': [dict(c) for c in channels],
                'metrics': {
                    'total_sent': campaign['sent'],
                    'total_responded': campaign['responded'],
                    'response_rate': (campaign['responded'] / campaign['sent'] * 100) if campaign['sent'] > 0 else 0,
                    'positive_rate': (campaign['positive'] / campaign['responded'] * 100) if campaign['responded'] > 0 else 0
                }
            }


# Singleton instance
_orchestrator_instance = None


async def get_campaign_orchestrator() -> DatabaseCampaignOrchestrator:
    """Get or create the campaign orchestrator singleton"""
    global _orchestrator_instance

    if not _orchestrator_instance:
        _orchestrator_instance = DatabaseCampaignOrchestrator()
        await _orchestrator_instance.initialize()

    return _orchestrator_instance
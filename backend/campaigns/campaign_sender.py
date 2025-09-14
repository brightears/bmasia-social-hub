"""
Multi-channel Campaign Sender for BMA Social
Handles WhatsApp, Line, and Email campaigns with compliance
"""

import os
import json
import time
import logging
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


class CampaignSender:
    """Handles sending campaigns across multiple channels"""

    def __init__(self):
        # WhatsApp configuration
        self.whatsapp_token = os.environ.get('WHATSAPP_ACCESS_TOKEN')
        self.whatsapp_phone_id = os.environ.get('WHATSAPP_PHONE_NUMBER_ID', '742462142273418')

        # Line configuration
        self.line_token = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')

        # Email configuration (using Gmail for now, can be changed)
        self.email_sender = os.environ.get('CAMPAIGN_EMAIL_SENDER', 'campaigns@bmasocial.com')
        self.email_password = os.environ.get('CAMPAIGN_EMAIL_PASSWORD')
        self.smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.environ.get('SMTP_PORT', '587'))

        # Test mode override contacts - always send to these when in test mode
        self.test_override_contacts = {
            'whatsapp': '+66856644142',
            'email': 'norbert@bmasiamusic.com',
            'line': '+66856644142'
        }

        # Rate limiting
        self.whatsapp_daily_limit = 1000  # Template messages per day
        self.line_batch_size = 500  # Messages per broadcast
        self.email_hourly_limit = 100

        # Tracking
        self.sent_today = {
            'whatsapp': 0,
            'line': 0,
            'email': 0
        }
        self.last_reset = datetime.now().date()

    def send_campaign(
        self,
        recipients: List[Dict[str, Any]],
        messages: Dict[str, str],
        channels: List[str],
        campaign_id: str,
        test_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Send campaign to multiple recipients across specified channels

        Args:
            recipients: List of customer dictionaries with contact info
            messages: Channel-specific messages from AI
            channels: List of channels to use ['whatsapp', 'line', 'email']
            campaign_id: Campaign identifier for tracking
            test_mode: If True, only send to first recipient

        Returns:
            Send results with success/failure counts
        """

        results = {
            'campaign_id': campaign_id,
            'total_recipients': len(recipients),
            'channels': channels,
            'sent': {},
            'failed': {},
            'errors': []
        }

        # Reset daily counters if needed
        self._check_daily_reset()

        # Test mode - override with test contacts and limit to first recipient
        if test_mode:
            recipients = recipients[:1]
            # Override recipient contacts with test contacts
            for recipient in recipients:
                if recipient.get('primary_contact'):
                    # Store original for logging before overriding
                    recipient['original_contact'] = recipient['primary_contact'].copy()
                    # Override with test contact details
                    recipient['primary_contact']['phone'] = self.test_override_contacts['whatsapp']
                    recipient['primary_contact']['email'] = self.test_override_contacts['email']
                # Add Line user ID for test mode (using the phone number as Line ID)
                recipient['line_user_id'] = self.test_override_contacts.get('line', self.test_override_contacts['whatsapp'])
            logger.info(f"TEST MODE: Overriding contacts to send to {self.test_override_contacts}")

        # Process each channel
        for channel in channels:
            if channel not in ['whatsapp', 'line', 'email']:
                logger.warning(f"Unknown channel: {channel}")
                continue

            results['sent'][channel] = 0
            results['failed'][channel] = 0

            # Send based on channel
            if channel == 'whatsapp':
                self._send_whatsapp_batch(recipients, messages.get('whatsapp', ''), results)
            elif channel == 'line':
                self._send_line_batch(recipients, messages.get('line', ''), results)
            elif channel == 'email':
                self._send_email_batch(
                    recipients,
                    messages.get('email_subject', 'BMA Social Update'),
                    messages.get('email_body', ''),
                    results
                )

        logger.info(f"Campaign {campaign_id} sent - Results: {results}")
        return results

    def _send_whatsapp_batch(
        self,
        recipients: List[Dict[str, Any]],
        message: str,
        results: Dict[str, Any]
    ):
        """Send WhatsApp messages with rate limiting"""

        if not self.whatsapp_token:
            logger.error("WhatsApp token not configured")
            results['errors'].append("WhatsApp not configured")
            return

        url = f"https://graph.facebook.com/v17.0/{self.whatsapp_phone_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.whatsapp_token}",
            "Content-Type": "application/json"
        }

        for recipient in recipients:
            # Check daily limit
            if self.sent_today['whatsapp'] >= self.whatsapp_daily_limit:
                logger.warning("WhatsApp daily limit reached")
                results['errors'].append("WhatsApp daily limit reached")
                break

            # Get phone number from primary contact
            phone = None
            if recipient.get('primary_contact'):
                phone = recipient['primary_contact'].get('phone')

            if not phone:
                logger.warning(f"No phone for {recipient.get('name')}")
                results['failed']['whatsapp'] += 1
                continue

            # Clean phone number (remove spaces, dashes)
            phone = ''.join(filter(str.isdigit, phone))
            if not phone.startswith('66'):  # Add Thailand country code if needed
                phone = '66' + phone.lstrip('0')

            # Personalize message
            personalized = self._personalize_message(message, recipient)

            # Send message
            payload = {
                "messaging_product": "whatsapp",
                "to": phone,
                "type": "text",
                "text": {"body": personalized}
            }

            try:
                response = requests.post(url, headers=headers, json=payload)
                if response.status_code == 200:
                    results['sent']['whatsapp'] += 1
                    self.sent_today['whatsapp'] += 1
                    logger.info(f"WhatsApp sent to {recipient.get('name')}")
                else:
                    results['failed']['whatsapp'] += 1
                    logger.error(f"WhatsApp failed: {response.text}")

                # Rate limiting - avoid hitting API too fast
                time.sleep(0.5)

            except Exception as e:
                results['failed']['whatsapp'] += 1
                logger.error(f"WhatsApp error: {e}")

    def _send_line_batch(
        self,
        recipients: List[Dict[str, Any]],
        message: str,
        results: Dict[str, Any]
    ):
        """Send Line messages using broadcast API"""

        if not self.line_token:
            logger.error("Line token not configured")
            results['errors'].append("Line not configured")
            return

        # For Line, we need user IDs from previous interactions
        # This would typically come from a database of Line users
        # For now, we'll check if recipient has a line_user_id field

        line_users = []
        for recipient in recipients:
            if recipient.get('line_user_id'):
                line_users.append(recipient['line_user_id'])

        if not line_users:
            logger.warning("No Line user IDs found for recipients")
            results['errors'].append("No Line users found")
            return

        # Line broadcast API
        url = "https://api.line.me/v2/bot/message/broadcast"
        headers = {
            "Authorization": f"Bearer {self.line_token}",
            "Content-Type": "application/json"
        }

        # Personalize for broadcast (use general version)
        broadcast_message = self._personalize_message(message, {})

        payload = {
            "messages": [
                {
                    "type": "text",
                    "text": broadcast_message
                }
            ]
        }

        try:
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                results['sent']['line'] = len(line_users)
                self.sent_today['line'] += len(line_users)
                logger.info(f"Line broadcast sent to {len(line_users)} users")
            else:
                results['failed']['line'] = len(line_users)
                logger.error(f"Line broadcast failed: {response.text}")
        except Exception as e:
            results['failed']['line'] = len(line_users)
            logger.error(f"Line error: {e}")

    def _send_email_batch(
        self,
        recipients: List[Dict[str, Any]],
        subject: str,
        body: str,
        results: Dict[str, Any]
    ):
        """Send email campaigns with rate limiting"""

        if not self.email_password:
            logger.error(f"Email not configured - password missing. Sender: {self.email_sender}")
            results['errors'].append("Email not configured - check EMAIL_PASSWORD environment variable")
            return

        sent_this_hour = 0

        for recipient in recipients:
            # Check hourly limit
            if sent_this_hour >= self.email_hourly_limit:
                logger.warning("Email hourly limit reached")
                time.sleep(3600)  # Wait an hour
                sent_this_hour = 0

            # Get email from primary contact
            email = None
            if recipient.get('primary_contact'):
                email = recipient['primary_contact'].get('email')

            if not email:
                logger.warning(f"No email for {recipient.get('name')}")
                results['failed']['email'] += 1
                continue

            # Personalize message
            personalized_subject = self._personalize_message(subject, recipient)
            personalized_body = self._personalize_message(body, recipient)

            # Send email
            if self._send_single_email(email, personalized_subject, personalized_body):
                results['sent']['email'] += 1
                self.sent_today['email'] += 1
                sent_this_hour += 1
                logger.info(f"Email sent to {recipient.get('name')}")
            else:
                results['failed']['email'] += 1

            # Rate limiting
            time.sleep(2)  # 2 seconds between emails

    def _send_single_email(self, to_email: str, subject: str, body: str) -> bool:
        """Send single email via SMTP"""
        try:
            logger.info(f"Attempting to send email to {to_email} via {self.smtp_server}:{self.smtp_port}")

            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.email_sender
            msg['To'] = to_email
            msg['Subject'] = subject

            # Check if body contains HTML tags
            if '<' in body and '>' in body:
                # HTML email
                html_part = MIMEText(body, 'html')
                msg.attach(html_part)
                logger.info("Sending as HTML email")
            else:
                # Plain text email
                text_part = MIMEText(body, 'plain')
                msg.attach(text_part)
                logger.info("Sending as plain text email")

            # Send via SMTP
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_sender, self.email_password)
                server.send_message(msg)

            logger.info(f"Email successfully sent to {to_email}")
            return True

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"Email authentication failed for {self.email_sender}: {e}")
            return False
        except Exception as e:
            logger.error(f"Email send error to {to_email}: {type(e).__name__}: {e}")
            return False

    def _personalize_message(self, template: str, recipient: Dict[str, Any]) -> str:
        """Replace template variables with recipient data"""

        message = template

        # Customer details
        message = message.replace('{{customer_name}}', recipient.get('name', 'Customer'))
        message = message.replace('{{brand}}', recipient.get('brand', ''))

        # Contact details
        if recipient.get('primary_contact'):
            contact = recipient['primary_contact']
            message = message.replace('{{contact_name}}', contact.get('name', ''))
            message = message.replace('{{contact_role}}', contact.get('role', ''))

        # Venue/zone details
        zones = recipient.get('zones', [])
        if zones:
            message = message.replace('{{zones}}', ', '.join(zones))
            message = message.replace('{{zone_count}}', str(len(zones)))
            message = message.replace('{{first_zone}}', zones[0] if zones else '')

        # Contract details
        message = message.replace('{{contract_end}}', recipient.get('contract_end', ''))
        message = message.replace('{{platform}}', recipient.get('platform', 'music service'))
        message = message.replace('{{annual_price}}', str(recipient.get('annual_price_per_zone', '')))

        # Date variables
        message = message.replace('{{today}}', datetime.now().strftime('%B %d, %Y'))
        message = message.replace('{{year}}', str(datetime.now().year))

        return message

    def _check_daily_reset(self):
        """Reset daily counters if new day"""
        today = datetime.now().date()
        if today > self.last_reset:
            self.sent_today = {
                'whatsapp': 0,
                'line': 0,
                'email': 0
            }
            self.last_reset = today
            logger.info("Daily send counters reset")

    def send_test_message(
        self,
        test_recipient: Dict[str, Any],
        message: str,
        channel: str
    ) -> bool:
        """Send single test message for campaign preview"""

        logger.info(f"Sending test {channel} message to {test_recipient.get('name')}")

        if channel == 'whatsapp':
            results = {'sent': {'whatsapp': 0}, 'failed': {'whatsapp': 0}, 'errors': []}
            self._send_whatsapp_batch([test_recipient], message, results)
            return results['sent']['whatsapp'] > 0

        elif channel == 'line':
            # For Line test, we'd need the user to have interacted before
            logger.warning("Line test requires previous interaction")
            return False

        elif channel == 'email':
            email = test_recipient.get('primary_contact', {}).get('email')
            if email:
                return self._send_single_email(
                    email,
                    "Test Campaign",
                    message
                )

        return False

    def get_send_statistics(self) -> Dict[str, Any]:
        """Get current sending statistics"""
        return {
            'sent_today': self.sent_today,
            'limits': {
                'whatsapp_daily': self.whatsapp_daily_limit,
                'line_batch': self.line_batch_size,
                'email_hourly': self.email_hourly_limit
            },
            'remaining': {
                'whatsapp': self.whatsapp_daily_limit - self.sent_today['whatsapp'],
                'email_this_hour': self.email_hourly_limit  # Simplified
            },
            'last_reset': str(self.last_reset)
        }
"""
AI-Powered Campaign Manager for BMA Social
Uses ChatGPT to compose, manage, and monitor customer campaigns
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# Try to import OpenAI, but make it optional for now
try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    logger.warning("OpenAI not available - campaign AI features disabled")


class AICampaignManager:
    """AI-first campaign management using ChatGPT 4o"""

    def __init__(self):
        if HAS_OPENAI and os.getenv('OPENAI_API_KEY'):
            self.openai = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            self.model = 'gpt-4o-mini'  # Using same model as main bot
            self.ai_enabled = True
        else:
            self.openai = None
            self.model = None
            self.ai_enabled = False
            logger.warning("AI features disabled - OpenAI not configured")

    def create_campaign(
        self,
        campaign_type: str,
        filters: Dict[str, Any],
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        AI creates complete campaign based on requirements

        Args:
            campaign_type: renewal, seasonal, announcement, etc.
            filters: Customer filtering criteria
            context: Additional context for AI

        Returns:
            Complete campaign object with messages
        """

        # Build prompt for AI
        prompt = f"""You are the campaign manager for BMA Social's music service.
Create a campaign with these requirements:

Campaign Type: {campaign_type}
Filters: {json.dumps(filters, indent=2)}
Additional Context: {context or 'None'}

Consider:
1. Each CUSTOMER is a business (like Hilton Pattaya) with multiple VENUES/ZONES
2. Messages should reference ALL their venues when relevant
3. Personalize based on their history and preferences
4. Use appropriate tone for the brand (formal for Hilton, casual for beach clubs)
5. Include clear call-to-action

Return a JSON with:
{{
    "campaign_name": "descriptive name",
    "campaign_goal": "what we want to achieve",
    "target_audience": "who we're targeting",
    "key_message": "main point to communicate",
    "tone": "formal/casual/friendly",
    "timing": "when to send",
    "channels": ["whatsapp", "email", "line"],
    "success_metrics": ["what to measure"]
}}"""

        if self.ai_enabled:
            try:
                response = self.openai.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are BMA Social's expert campaign strategist."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )

                campaign_plan = json.loads(response.choices[0].message.content)
                logger.info(f"AI created campaign: {campaign_plan['campaign_name']}")
                return campaign_plan

            except Exception as e:
                logger.error(f"Error creating campaign: {e}")
                return self._get_default_campaign(campaign_type, filters)
        else:
            # Return default campaign without AI
            return self._get_default_campaign(campaign_type, filters)

    def _get_default_campaign(self, campaign_type: str, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Get default campaign plan when AI is not available"""
        campaigns = {
            "renewal": {
                "campaign_name": "Contract Renewal Reminder",
                "campaign_goal": "Remind customers about upcoming contract renewals",
                "target_audience": "Customers with expiring contracts",
                "key_message": "Your music service contract is expiring soon",
                "tone": "professional",
                "timing": "30 days before expiry",
                "channels": ["whatsapp", "email"],
                "success_metrics": ["Response rate", "Renewal rate"]
            },
            "seasonal": {
                "campaign_name": "Seasonal Music Promotion",
                "campaign_goal": "Promote seasonal music features",
                "target_audience": "All active customers",
                "key_message": "Enhance your venue's atmosphere with seasonal playlists",
                "tone": "friendly",
                "timing": "Start of season",
                "channels": ["whatsapp", "email"],
                "success_metrics": ["Engagement rate", "Feature adoption"]
            }
        }

        default = campaigns.get(campaign_type, {
            "campaign_name": f"{campaign_type.title()} Campaign",
            "campaign_goal": "Engage with customers",
            "target_audience": "Selected customers",
            "key_message": "Important update from BMA Social",
            "tone": "professional",
            "timing": "As needed",
            "channels": ["whatsapp", "email"],
            "success_metrics": ["Response rate"]
        })

        # Add filter info to campaign name
        if filters.get('brand'):
            default['campaign_name'] = f"{filters['brand']} - {default['campaign_name']}"

        return default

    def compose_message(
        self,
        customer: Dict[str, Any],
        campaign_type: str,
        campaign_context: Dict[str, Any],
        multiple_recipients: bool = False
    ) -> Dict[str, str]:
        """
        AI composes personalized message for specific customer

        Args:
            customer: Complete customer data including all venues
            campaign_type: Type of campaign
            campaign_context: Campaign details and goals

        Returns:
            Messages for each channel
        """

        # Extract customer details
        customer_name = customer.get('name', 'Customer')
        brand = customer.get('brand', '')
        venues = customer.get('zones', [])
        contact = customer.get('primary_contact', {})
        contract_end = customer.get('contract_end', '')
        platform = customer.get('platform', 'Soundtrack Your Brand')

        # Determine greeting style based on multiple recipients
        greeting_guidance = ""
        if multiple_recipients:
            greeting_guidance = """
IMPORTANT: This message will be sent to MULTIPLE contacts for this customer.
Use team/generic greetings like "Hello team", "Greetings", "Dear team at [Customer]", or "Hi there"
instead of personal names. DO NOT use individual names in greetings.
"""
        else:
            greeting_guidance = """
GREETING STYLE: This will be sent to a single contact, so you can use their name if available.
"""

        prompt = f"""Compose a personalized campaign message for this customer:

CUSTOMER: {customer_name}
BRAND: {brand}
VENUES/ZONES: {', '.join(venues) if venues else 'Unknown'}
PRIMARY CONTACT: {contact.get('name', 'Manager')} ({contact.get('role', 'Manager')})
CONTRACT END: {contract_end}
PLATFORM: {platform}

CAMPAIGN TYPE: {campaign_type}
CAMPAIGN CONTEXT: {json.dumps(campaign_context, indent=2)}

{greeting_guidance}

Requirements:
1. Use appropriate greeting based on recipient count (see guidance above)
2. Reference ALL their venues/zones specifically
3. Match tone to brand (Hilton = formal, Beach Club = casual)
4. Include specific value proposition
5. Clear call-to-action
6. Keep WhatsApp under 1024 chars
7. Make email version more detailed
8. IMPORTANT: Always end emails with "Best regards,\nBMAsia Team" signature

Return JSON with:
{{
    "whatsapp": "message for WhatsApp",
    "line": "message for Line",
    "email_subject": "email subject line",
    "email_body": "email body (can use simple HTML)",
    "sms": "short SMS version"
}}"""

        if self.ai_enabled:
            try:
                response = self.openai.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are BMA Social's expert copywriter. Write compelling, personalized messages."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )

                messages = json.loads(response.choices[0].message.content)
                logger.info(f"AI composed messages for {customer_name}")
                return messages

            except Exception as e:
                logger.error(f"Error composing message: {e}")
                return self._get_template_message(customer, campaign_type, campaign_context, multiple_recipients)
        else:
            return self._get_template_message(customer, campaign_type, campaign_context, multiple_recipients)

    def _get_template_message(
        self,
        customer: Dict[str, Any],
        campaign_type: str,
        campaign_context: Dict[str, Any],
        multiple_recipients: bool = False
    ) -> Dict[str, str]:
        """Get template message when AI is not available"""
        customer_name = customer.get('name', 'Customer')
        contact = customer.get('primary_contact', {})

        # Use generic greeting for multiple recipients
        if multiple_recipients:
            greeting = f"Hello team at {customer_name}"
        else:
            contact_name = contact.get('name', 'there')
            greeting = f"Hi {contact_name}"

        venues = customer.get('zones', [])
        venues_text = ', '.join(venues) if venues else 'your venue'

        templates = {
            "renewal": {
                "whatsapp": f"{greeting}! This is BMA Social. Your music service at {customer_name} ({venues_text}) is expiring on {customer.get('contract_end', 'soon')}. Would you like to renew for another year? Reply to discuss renewal options.",
                "email_subject": f"Renewal Reminder - {customer_name} Music Service",
                "email_body": f"<p>{greeting},</p><p>Your BMA Social music service for {customer_name} is expiring on {customer.get('contract_end', 'soon')}.</p><p>Zones: {venues_text}</p><p>Please contact us to discuss renewal options.</p><p><br>Best regards,<br>BMAsia Team</p>"
            },
            "seasonal": {
                "whatsapp": f"{greeting}! Enhance the atmosphere at {customer_name} with our special seasonal playlists. Available now for all your zones: {venues_text}. Reply to learn more!",
                "email_subject": f"Seasonal Music Update - {customer_name}",
                "email_body": f"<p>{greeting},</p><p>New seasonal playlists are available for {customer_name}!</p><p>Available for: {venues_text}</p><p>Contact us to activate these special playlists.</p><p><br>Best regards,<br>BMAsia Team</p>"
            }
        }

        template = templates.get(campaign_type, {
            "whatsapp": f"{greeting}, this is BMA Social with an update about your music service at {customer_name} ({venues_text}). Please reply for more information.",
            "email_subject": f"BMA Social - Update for {customer_name}",
            "email_body": f"<p>{greeting},</p><p>We have an important update regarding your music service at {customer_name}.</p><p>Zones: {venues_text}</p><p><br>Best regards,<br>BMAsia Team</p>"
        })

        # Add Line and SMS
        template["line"] = template["whatsapp"][:500]  # Line has character limit
        template["sms"] = f"BMA Social: Update for {customer_name}. Check WhatsApp/email for details."

        return template

    def analyze_response(
        self,
        response_text: str,
        campaign_context: Dict[str, Any],
        customer_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        AI analyzes campaign response to determine intent and next action

        Args:
            response_text: Customer's response message
            campaign_context: Original campaign details
            customer_context: Customer information

        Returns:
            Analysis with intent and suggested action
        """

        prompt = f"""Analyze this campaign response:

CUSTOMER RESPONSE: "{response_text}"

CAMPAIGN CONTEXT: {json.dumps(campaign_context, indent=2)}
CUSTOMER: {customer_context.get('name')}
VENUES: {', '.join(customer_context.get('zones', []))}

Determine:
1. Intent (interested, not interested, question, complaint, confirmation)
2. Urgency (immediate, normal, low)
3. Sentiment (positive, neutral, negative)
4. Requires human? (yes/no)
5. Suggested reply
6. Next action

Return JSON with:
{{
    "intent": "interested/not_interested/question/complaint/confirmation/unclear",
    "urgency": "immediate/normal/low",
    "sentiment": "positive/neutral/negative",
    "requires_human": true/false,
    "suggested_reply": "AI suggested response",
    "next_action": "what to do next",
    "key_points": ["main points from response"]
}}"""

        if self.ai_enabled:
            try:
                response = self.openai.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You analyze customer responses to understand intent and determine best action."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )

                analysis = json.loads(response.choices[0].message.content)
                logger.info(f"AI analyzed response - Intent: {analysis['intent']}")
                return analysis

            except Exception as e:
                logger.error(f"Error analyzing response: {e}")
                return self._get_default_analysis(response_text)
        else:
            return self._get_default_analysis(response_text)

    def _get_default_analysis(self, response_text: str) -> Dict[str, Any]:
        """Basic response analysis without AI"""
        response_lower = response_text.lower()

        # Simple intent detection
        if any(word in response_lower for word in ['yes', 'confirm', 'agree', 'renew']):
            intent = "interested"
            sentiment = "positive"
        elif any(word in response_lower for word in ['no', 'cancel', 'stop']):
            intent = "not_interested"
            sentiment = "negative"
        elif '?' in response_text:
            intent = "question"
            sentiment = "neutral"
        else:
            intent = "unclear"
            sentiment = "neutral"

        return {
            "intent": intent,
            "urgency": "normal",
            "sentiment": sentiment,
            "requires_human": True,
            "suggested_reply": "Thank you for your response. Our team will follow up shortly.",
            "next_action": "escalate_to_human",
            "key_points": [response_text[:100]]
        }

    def generate_campaign_report(
        self,
        campaign_data: Dict[str, Any],
        responses: List[Dict[str, Any]]
    ) -> str:
        """
        AI generates human-readable campaign report

        Args:
            campaign_data: Campaign details and metrics
            responses: List of customer responses

        Returns:
            Formatted report text
        """

        prompt = f"""Generate a campaign performance report:

CAMPAIGN: {campaign_data.get('name')}
TYPE: {campaign_data.get('type')}
SENT TO: {campaign_data.get('recipients_count')} customers
RESPONSES: {len(responses)}

METRICS:
- Sent: {campaign_data.get('sent', 0)}
- Delivered: {campaign_data.get('delivered', 0)}
- Read: {campaign_data.get('read', 0)}
- Responded: {len(responses)}

TOP RESPONSES:
{json.dumps(responses[:5], indent=2) if responses else 'No responses yet'}

Create a professional report with:
1. Executive summary
2. Key metrics and response rate
3. Sentiment analysis
4. Notable responses
5. Recommendations for improvement
6. Next steps

Format in clear sections with insights."""

        try:
            response = self.openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a marketing analyst creating insightful campaign reports."},
                    {"role": "user", "content": prompt}
                ]
            )

            report = response.choices[0].message.content
            logger.info("AI generated campaign report")
            return report

        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return f"Campaign Report\n\nCampaign: {campaign_data.get('name')}\nStatus: Error generating detailed report\nError: {e}"

    def suggest_best_time(
        self,
        customer: Dict[str, Any],
        campaign_type: str
    ) -> Dict[str, Any]:
        """
        AI suggests optimal send time based on customer profile

        Args:
            customer: Customer data
            campaign_type: Type of campaign

        Returns:
            Suggested timing with reasoning
        """

        prompt = f"""Suggest optimal send time for campaign:

CUSTOMER: {customer.get('name')}
TYPE: {customer.get('business_type', 'Hotel')}
LOCATION: {customer.get('country', 'Unknown')}
TIMEZONE: {customer.get('timezone', 'Asia/Bangkok')}
CAMPAIGN TYPE: {campaign_type}
PRIMARY CONTACT: {customer.get('primary_contact', {}).get('role', 'Manager')}

Consider:
1. Business type operating hours
2. Decision maker availability
3. Time zone
4. Campaign urgency
5. Industry best practices

Return JSON with:
{{
    "suggested_time": "HH:MM",
    "suggested_day": "weekday/weekend/specific day",
    "timezone": "timezone",
    "reasoning": "why this time",
    "alternative_time": "backup option"
}}"""

        try:
            response = self.openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert in B2B communication timing."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )

            timing = json.loads(response.choices[0].message.content)
            logger.info(f"AI suggested time: {timing['suggested_time']} {timing['suggested_day']}")
            return timing

        except Exception as e:
            logger.error(f"Error suggesting time: {e}")
            # Default to business hours
            return {
                "suggested_time": "10:00",
                "suggested_day": "weekday",
                "timezone": "Asia/Bangkok",
                "reasoning": "Standard business hours",
                "alternative_time": "14:00"
            }
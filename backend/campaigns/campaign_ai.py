"""
AI-Powered Campaign Manager for BMA Social
Uses ChatGPT to compose, manage, and monitor customer campaigns
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from openai import OpenAI

logger = logging.getLogger(__name__)


class AICampaignManager:
    """AI-first campaign management using ChatGPT 4o"""

    def __init__(self):
        self.openai = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.model = 'gpt-4o-mini'  # Using same model as main bot

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
            return {
                "error": str(e),
                "campaign_name": f"{campaign_type} Campaign",
                "status": "failed"
            }

    def compose_message(
        self,
        customer: Dict[str, Any],
        campaign_type: str,
        campaign_context: Dict[str, Any]
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

        prompt = f"""Compose a personalized campaign message for this customer:

CUSTOMER: {customer_name}
BRAND: {brand}
VENUES/ZONES: {', '.join(venues) if venues else 'Unknown'}
PRIMARY CONTACT: {contact.get('name', 'Manager')} ({contact.get('role', 'Manager')})
CONTRACT END: {contract_end}
PLATFORM: {platform}

CAMPAIGN TYPE: {campaign_type}
CAMPAIGN CONTEXT: {json.dumps(campaign_context, indent=2)}

Requirements:
1. Address the primary contact by name if known
2. Reference ALL their venues/zones specifically
3. Match tone to brand (Hilton = formal, Beach Club = casual)
4. Include specific value proposition
5. Clear call-to-action
6. Keep WhatsApp under 1024 chars
7. Make email version more detailed

Return JSON with:
{{
    "whatsapp": "message for WhatsApp",
    "line": "message for Line",
    "email_subject": "email subject line",
    "email_body": "email body (can use simple HTML)",
    "sms": "short SMS version"
}}"""

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
            # Fallback to template
            return {
                "whatsapp": f"Hi {contact.get('name', '')}, this is BMA Social with an update about your music service at {customer_name}. Please reply for more information.",
                "line": f"Hello from BMA Social! We have an update regarding {customer_name}. Reply for details.",
                "email_subject": f"BMA Social - Update for {customer_name}",
                "email_body": f"<p>Dear {contact.get('name', 'Team')},</p><p>We have an important update regarding your music service.</p>",
                "sms": f"BMA Social update for {customer_name}. Please check your email or WhatsApp."
            }

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
            return {
                "intent": "unclear",
                "urgency": "normal",
                "sentiment": "neutral",
                "requires_human": True,
                "suggested_reply": "Thank you for your response. Our team will follow up shortly.",
                "next_action": "escalate_to_human",
                "error": str(e)
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
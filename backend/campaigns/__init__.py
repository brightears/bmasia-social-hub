"""
BMA Social AI-Powered Campaign Management System

This module provides intelligent campaign management with ChatGPT 4o composing
and managing campaigns across WhatsApp, Line, and Email channels.
"""

from campaigns.campaign_orchestrator import CampaignOrchestrator
from campaigns.campaign_ai import AICampaignManager
from campaigns.customer_manager import CustomerManager
from campaigns.campaign_sender import CampaignSender

__all__ = [
    'CampaignOrchestrator',
    'AICampaignManager',
    'CustomerManager',
    'CampaignSender'
]

# Version
__version__ = '1.0.0'
"""
Smart Contact Selector for Campaign System
Intelligently selects which contacts to include based on campaign type
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class SmartContactSelector:
    """AI-based contact selection based on campaign context"""

    # Role relevance matrix for different campaign types
    CAMPAIGN_CONTACT_RULES = {
        'renewal': {
            'required_roles': ['General Manager', 'GM'],
            'recommended_roles': ['Purchasing Manager', 'Finance Manager', 'Accounting'],
            'optional_roles': [],
            'reason': 'Contract renewals require management approval and finance processing'
        },
        'seasonal': {
            'required_roles': ['General Manager', 'GM'],
            'recommended_roles': ['Director of Food & Beverage', 'F&B Manager', 'Operations Manager'],
            'optional_roles': ['IT Manager', 'Marketing Manager'],
            'reason': 'Seasonal campaigns need management approval and operational implementation'
        },
        'announcement': {
            'required_roles': ['General Manager', 'GM'],
            'recommended_roles': ['Director of Food & Beverage', 'Operations Manager', 'IT Manager'],
            'optional_roles': ['Purchasing Manager'],
            'reason': 'Feature announcements need broad awareness across departments'
        },
        'technical': {
            'required_roles': ['IT Manager', 'Technical Manager'],
            'recommended_roles': ['Director of Food & Beverage', 'Operations Manager'],
            'optional_roles': ['General Manager', 'GM'],
            'reason': 'Technical issues need IT attention with operational awareness'
        },
        'survey': {
            'required_roles': ['General Manager', 'GM'],
            'recommended_roles': ['Director of Food & Beverage', 'Operations Manager'],
            'optional_roles': ['Marketing Manager'],
            'reason': 'Feedback surveys need management oversight and operational input'
        },
        'follow_up': {
            'required_roles': [],  # Use whoever was in the original conversation
            'recommended_roles': ['General Manager', 'GM'],
            'optional_roles': ['Director of Food & Beverage'],
            'reason': 'Follow-ups should go to relevant parties from initial contact'
        }
    }

    def select_contacts(
        self,
        customer: Dict[str, Any],
        campaign_type: str,
        campaign_context: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Select appropriate contacts for a campaign

        Args:
            customer: Customer data with contacts list
            campaign_type: Type of campaign (renewal, seasonal, etc.)
            campaign_context: Additional context about the campaign

        Returns:
            List of selected contacts with their preferred channels
        """

        all_contacts = customer.get('contacts', [])
        if not all_contacts:
            # Fallback to primary contact if no contacts list
            if customer.get('primary_contact'):
                return [customer['primary_contact']]
            return []

        # Get rules for this campaign type
        rules = self.CAMPAIGN_CONTACT_RULES.get(
            campaign_type,
            self.CAMPAIGN_CONTACT_RULES['announcement']  # Default to announcement
        )

        selected_contacts = []
        selected_roles = set()

        # First, add all required roles
        for contact in all_contacts:
            role = contact.get('role', '').lower()

            # Check if this role is required
            for required_role in rules['required_roles']:
                if required_role.lower() in role:
                    if contact not in selected_contacts:
                        selected_contacts.append(contact)
                        selected_roles.add(role)
                        logger.info(f"Selected {contact['name']} ({contact['role']}) as required for {campaign_type}")
                    break

        # Then add recommended roles if not already included
        for contact in all_contacts:
            role = contact.get('role', '').lower()

            # Skip if already selected
            if role in selected_roles:
                continue

            # Check if this role is recommended
            for recommended_role in rules['recommended_roles']:
                if recommended_role.lower() in role:
                    selected_contacts.append(contact)
                    selected_roles.add(role)
                    logger.info(f"Selected {contact['name']} ({contact['role']}) as recommended for {campaign_type}")
                    break

        # Add optional roles based on campaign context
        if campaign_context:
            # If it's a technical update, include IT
            if any(word in str(campaign_context).lower() for word in ['technical', 'system', 'update', 'maintenance']):
                for contact in all_contacts:
                    role = contact.get('role', '').lower()
                    if 'it' in role or 'technical' in role:
                        if contact not in selected_contacts:
                            selected_contacts.append(contact)
                            logger.info(f"Selected {contact['name']} ({contact['role']}) for technical context")

            # If it's about money/pricing, include finance
            if any(word in str(campaign_context).lower() for word in ['price', 'cost', 'payment', 'invoice', 'discount']):
                for contact in all_contacts:
                    role = contact.get('role', '').lower()
                    if any(fin_word in role for fin_word in ['finance', 'purchasing', 'accounting']):
                        if contact not in selected_contacts:
                            selected_contacts.append(contact)
                            logger.info(f"Selected {contact['name']} ({contact['role']}) for financial context")

        # If no contacts selected, use primary contact as fallback
        if not selected_contacts:
            if customer.get('primary_contact'):
                selected_contacts.append(customer['primary_contact'])
                logger.warning(f"No matching roles found, using primary contact")
            elif all_contacts:
                selected_contacts.append(all_contacts[0])
                logger.warning(f"No matching roles found, using first contact")

        # Add preferred channel info to each contact
        for contact in selected_contacts:
            # Determine best channel for this contact
            contact['selected_channel'] = self._determine_channel(contact)

        logger.info(f"Selected {len(selected_contacts)} contacts for {campaign_type} campaign to {customer['name']}")
        return selected_contacts

    def _determine_channel(self, contact: Dict[str, Any]) -> str:
        """
        Determine the best channel for a contact

        Args:
            contact: Contact information

        Returns:
            Best channel to use (whatsapp, email, line)
        """

        # Check preferred contact method
        preferred = contact.get('preferred_contact', '').lower()

        if 'whatsapp' in preferred and contact.get('phone'):
            return 'whatsapp'
        elif 'line' in preferred and contact.get('line_id'):
            return 'line'
        elif 'email' in preferred and contact.get('email'):
            return 'email'

        # Fallback order: email -> whatsapp -> line
        if contact.get('email'):
            return 'email'
        elif contact.get('phone'):
            return 'whatsapp'
        elif contact.get('line_id'):
            return 'line'
        else:
            return 'email'  # Default

    def get_role_explanation(self, campaign_type: str) -> str:
        """
        Get explanation of why certain roles were selected

        Args:
            campaign_type: Type of campaign

        Returns:
            Human-readable explanation
        """

        rules = self.CAMPAIGN_CONTACT_RULES.get(
            campaign_type,
            self.CAMPAIGN_CONTACT_RULES['announcement']
        )

        return rules.get('reason', 'Standard contact selection for this campaign type')
#!/usr/bin/env python3
"""
Gmail Contact Extractor for BMA Social Venue Database
Searches Gmail for venue-related emails and extracts contact information
"""

import os
import sys
import re
import json
import logging
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import shutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VenueContactExtractor:
    """Extract contact information from Gmail for venues"""

    # Common email domains for hotel chains
    HOTEL_DOMAINS = [
        'hilton.com',
        'marriott.com',
        'hyatt.com',
        'ihg.com',
        'accor.com',
        'centarahotelsresorts.com',
        'anantara.com',
        'avanihotels.com',
        'minorhotels.com',
        'shangri-la.com',
        'fourseasons.com',
        'mandarin-oriental.com',
        'rosewoodhotels.com',
        'sixsenses.com'
    ]

    # Common titles to look for
    CONTACT_TITLES = [
        'general manager', 'gm',
        'director of food', 'f&b director', 'food & beverage',
        'operations manager', 'ops manager',
        'it manager', 'information technology',
        'purchasing manager', 'procurement',
        'revenue manager',
        'sales manager', 'sales director',
        'marketing manager', 'marketing director',
        'human resources', 'hr manager',
        'finance manager', 'finance director',
        'executive chef', 'chef'
    ]

    # Email signature patterns
    SIGNATURE_PATTERNS = [
        r'(?:regards|best|sincerely|thanks|cheers),?\s*\n+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
        r'\n([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\n(?:General Manager|Director|Manager)',
        r'^\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s*$',
    ]

    # Phone patterns
    PHONE_PATTERNS = [
        r'(?:tel|phone|mobile|m|t|p)[\s:]*(\+?\d{1,4}[\s\-\.]?\(?\d{1,4}\)?[\s\-\.]?\d{1,4}[\s\-\.]?\d{1,4})',
        r'(\+\d{1,3}[\s\-]?\d{2,4}[\s\-]?\d{3,4}[\s\-]?\d{3,4})',
        r'(\d{2,4}[\s\-]?\d{3,4}[\s\-]?\d{3,4})',
    ]

    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.gmail_client = None
        self.venues = []
        self.contacts_found = {}
        self.init_gmail()

    def init_gmail(self):
        """Initialize Gmail client"""
        try:
            # Import Gmail client
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from gmail_client import GmailClient

            self.gmail_client = GmailClient()
            if self.gmail_client.services:
                logger.info(f"✅ Gmail client initialized with {len(self.gmail_client.services)} accounts")
            else:
                logger.warning("⚠️  Gmail client initialized but no accounts connected")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Gmail client: {e}")
            logger.info("Make sure gmail_client.py is available and Google credentials are configured")

    def load_venues(self):
        """Load venues from venue_data.md"""
        venue_file = os.path.join(os.path.dirname(__file__), 'venue_data.md')

        if not os.path.exists(venue_file):
            logger.error(f"❌ Venue file not found: {venue_file}")
            return False

        with open(venue_file, 'r') as f:
            content = f.read()

        # Parse venues
        current_venue = None
        self.venues = []

        for line in content.split('\n'):
            if line.startswith('### '):
                # New venue
                venue_name = line.replace('### ', '').strip()
                current_venue = {
                    'name': venue_name,
                    'has_contacts': False,
                    'contacts': []
                }
                self.venues.append(current_venue)
            elif current_venue and '- Email:' in line and '—' not in line:
                # This venue has contact info
                current_venue['has_contacts'] = True

        logger.info(f"📊 Loaded {len(self.venues)} venues from database")

        # Count venues without contacts
        no_contacts = [v for v in self.venues if not v['has_contacts']]
        logger.info(f"📧 {len(no_contacts)} venues need contact information")

        return True

    def search_venue_contacts(self, venue_name: str, days_back: int = 180) -> List[Dict]:
        """Search Gmail for contacts related to a venue"""
        if not self.gmail_client:
            return []

        contacts = []

        try:
            # Clean venue name for search
            search_name = venue_name.replace('&', '').replace('-', ' ')

            # Search for emails
            logger.debug(f"🔍 Searching for: {search_name}")
            emails = self.gmail_client.search_venue_emails(
                venue_name=search_name,
                days_back=days_back
            )

            if not emails:
                # Try with just first part of name (e.g., "Hilton" from "Hilton Pattaya")
                first_part = search_name.split()[0] if ' ' in search_name else search_name
                if len(first_part) > 4:  # Only if meaningful
                    emails = self.gmail_client.search_venue_emails(
                        venue_name=first_part,
                        days_back=days_back
                    )

            # Extract contacts from emails
            for email in emails[:10]:  # Process first 10 emails
                contact = self.extract_contact_from_email(email, venue_name)
                if contact and contact not in contacts:
                    contacts.append(contact)

        except Exception as e:
            logger.debug(f"Error searching for {venue_name}: {e}")

        return contacts

    def extract_contact_from_email(self, email: Dict, venue_name: str) -> Optional[Dict]:
        """Extract contact information from an email"""
        try:
            # Get sender info
            from_header = email.get('from', '')

            # Parse email address and name
            email_match = re.search(r'<([^>]+@[^>]+)>', from_header)
            if email_match:
                email_address = email_match.group(1)
                name = from_header.split('<')[0].strip().strip('"')
            else:
                email_address = from_header
                name = None

            # Skip if not from a relevant domain
            domain = email_address.split('@')[1] if '@' in email_address else ''
            if not any(hotel_domain in domain for hotel_domain in self.HOTEL_DOMAINS):
                # Also check if venue name is in domain
                if venue_name.split()[0].lower() not in domain.lower():
                    return None

            # Get email body
            body = email.get('body', '') or email.get('snippet', '')

            # Try to extract name from signature if not in header
            if not name and body:
                for pattern in self.SIGNATURE_PATTERNS:
                    match = re.search(pattern, body, re.MULTILINE | re.IGNORECASE)
                    if match:
                        name = match.group(1).strip()
                        break

            # Extract title
            title = self.extract_title(body)

            # Extract phone
            phone = self.extract_phone(body)

            if name and email_address:
                return {
                    'name': name,
                    'email': email_address,
                    'title': title or 'Manager',
                    'phone': phone or '',
                    'source_date': email.get('timestamp', ''),
                    'confidence': 0.8 if title else 0.5
                }

        except Exception as e:
            logger.debug(f"Error extracting contact: {e}")

        return None

    def extract_title(self, text: str) -> Optional[str]:
        """Extract job title from email text"""
        if not text:
            return None

        text_lower = text.lower()

        # Look for title patterns
        for title_keyword in self.CONTACT_TITLES:
            if title_keyword in text_lower:
                # Try to get the full title
                patterns = [
                    rf'((?:{title_keyword}[\w\s&]+?))\n',
                    rf'\n([\w\s&]*{title_keyword}[\w\s&]*)\n',
                ]

                for pattern in patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        full_title = match.group(1).strip()
                        # Clean up and capitalize
                        return self.clean_title(full_title)

                # Return basic title if no pattern match
                return self.clean_title(title_keyword)

        return None

    def clean_title(self, title: str) -> str:
        """Clean and format a job title"""
        # Common replacements
        replacements = {
            'gm': 'General Manager',
            'f&b': 'Food & Beverage',
            'ops': 'Operations',
            'it': 'IT',
            'hr': 'Human Resources'
        }

        words = []
        for word in title.split():
            word_lower = word.lower()
            if word_lower in replacements:
                words.append(replacements[word_lower])
            else:
                words.append(word.capitalize())

        return ' '.join(words)

    def extract_phone(self, text: str) -> Optional[str]:
        """Extract phone number from email text"""
        if not text:
            return None

        for pattern in self.PHONE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                phone = match.group(1)
                # Clean up phone number
                phone = re.sub(r'[^\d\+\-\s]', '', phone)
                if len(phone) >= 10:  # Valid phone length
                    return phone.strip()

        return None

    def update_venue_data(self):
        """Update venue_data.md with found contacts"""
        venue_file = os.path.join(os.path.dirname(__file__), 'venue_data.md')

        # Create backup
        if not self.dry_run:
            backup_file = f"{venue_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy(venue_file, backup_file)
            logger.info(f"💾 Backup saved to {backup_file}")

        # Read current content
        with open(venue_file, 'r') as f:
            lines = f.readlines()

        # Update contacts
        updated = False
        current_venue = None
        in_contacts = False

        for i, line in enumerate(lines):
            if line.startswith('### '):
                venue_name = line.replace('### ', '').strip()
                current_venue = venue_name
                in_contacts = False

            elif current_venue and '#### Contacts' in line:
                in_contacts = True

            elif in_contacts and current_venue in self.contacts_found:
                # Update contact lines
                if '- **General Manager**:' in line and '—' in lines[i+1]:
                    contact = self.get_best_contact(self.contacts_found[current_venue], 'General Manager')
                    if contact:
                        lines[i+1] = f"  - Email: {contact['email']}\n"
                        if contact.get('name'):
                            lines[i] = f"- **General Manager**: {contact['name']}\n"
                        if contact.get('phone') and '—' in lines[i+2]:
                            lines[i+2] = f"  - Phone: {contact['phone']}\n"
                        updated = True
                        logger.info(f"  ✅ Updated GM for {current_venue}")

        # Write updated content
        if updated and not self.dry_run:
            with open(venue_file, 'w') as f:
                f.writelines(lines)
            logger.info(f"✅ Updated venue_data.md with new contacts")
        elif self.dry_run:
            logger.info("🔍 DRY RUN - No files were modified")

    def get_best_contact(self, contacts: List[Dict], title_filter: str) -> Optional[Dict]:
        """Get the best matching contact for a specific title"""
        # Filter by title if specified
        if title_filter:
            title_lower = title_filter.lower()
            filtered = [c for c in contacts if title_lower in (c.get('title', '') or '').lower()]
            if filtered:
                contacts = filtered

        # Sort by confidence
        contacts.sort(key=lambda x: x.get('confidence', 0), reverse=True)

        return contacts[0] if contacts else None

    def run(self, specific_venue: Optional[str] = None, limit: int = 10):
        """Run the contact extraction process"""
        logger.info("🚀 Starting venue contact extraction...")

        # Load venues
        if not self.load_venues():
            return

        # Filter venues
        if specific_venue:
            venues_to_process = [v for v in self.venues if specific_venue.lower() in v['name'].lower()]
            if not venues_to_process:
                logger.error(f"❌ Venue '{specific_venue}' not found")
                return
        else:
            # Process venues without contacts
            venues_to_process = [v for v in self.venues if not v['has_contacts']][:limit]

        logger.info(f"🔍 Processing {len(venues_to_process)} venues...")

        # Search for contacts
        for venue in venues_to_process:
            logger.info(f"\n🏨 Searching for: {venue['name']}")

            contacts = self.search_venue_contacts(venue['name'])

            if contacts:
                self.contacts_found[venue['name']] = contacts
                logger.info(f"  ✅ Found {len(contacts)} contact(s)")

                # Show first contact as example
                best = self.get_best_contact(contacts, '')
                if best:
                    logger.info(f"    - {best.get('name', 'Unknown')} ({best.get('title', 'Unknown')})")
                    logger.info(f"    - {best.get('email', 'Unknown')}")
            else:
                logger.info(f"  ⚠️  No contacts found")

        # Update venue data
        if self.contacts_found:
            logger.info(f"\n📝 Found contacts for {len(self.contacts_found)} venues")
            self.update_venue_data()
        else:
            logger.info("\n❌ No new contacts found")

def main():
    parser = argparse.ArgumentParser(description='Extract venue contacts from Gmail')
    parser.add_argument('--venue', help='Search for specific venue')
    parser.add_argument('--limit', type=int, default=10, help='Maximum venues to process')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without updating')
    parser.add_argument('--days', type=int, default=180, help='Days to search back in Gmail')

    args = parser.parse_args()

    extractor = VenueContactExtractor(dry_run=args.dry_run)
    extractor.run(specific_venue=args.venue, limit=args.limit)

if __name__ == '__main__':
    main()
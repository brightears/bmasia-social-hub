#!/usr/bin/env python3
"""
Migration script to parse venue_data.md and import into PostgreSQL
Handles 923 venues with 4,342 contacts and their associated zones
"""

import os
import re
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor, execute_batch
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VenueDataMigrator:
    """Parse venue_data.md and migrate to PostgreSQL database"""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.conn = None
        self.venues_created = 0
        self.zones_created = 0
        self.contacts_created = 0

    def connect(self):
        """Connect to PostgreSQL database"""
        try:
            self.conn = psycopg2.connect(self.database_url)
            self.conn.autocommit = False
            logger.info("Connected to PostgreSQL database")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def disconnect(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Disconnected from database")

    def parse_venue_data(self, file_path: str) -> List[Dict]:
        """Parse venue_data.md file and extract all venue information"""
        venues = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Split by venue separator (### followed by venue name)
            venue_sections = re.split(r'\n### ', content)

            for section in venue_sections[1:]:  # Skip header
                lines = section.strip().split('\n')
                if not lines:
                    continue

                # Extract venue name (first line)
                venue_name = lines[0].strip()

                # Skip if it's a header or empty
                if not venue_name or venue_name.startswith('#'):
                    continue

                venue_data = {
                    'name': venue_name,
                    'business_type': None,
                    'zones': [],
                    'zone_count': 0,
                    'platform': None,
                    'annual_price': None,
                    'currency': None,
                    'contract_start': None,
                    'contract_end': None,
                    'soundtrack_account_id': None,
                    'hardware_type': None,
                    'special_notes': None,
                    'contacts': []
                }

                # Parse venue details
                contact_section = False
                current_contact = None

                for line in lines[1:]:
                    line = line.strip()

                    # Skip empty lines
                    if not line or line == '---':
                        continue

                    # Check for contacts section
                    if line.startswith('#### Contacts'):
                        contact_section = True
                        continue

                    if contact_section:
                        # Parse contact information
                        if line.startswith('- **') and '**:' in line:
                            # Save previous contact if exists
                            if current_contact:
                                venue_data['contacts'].append(current_contact)

                            # Start new contact
                            role_match = re.match(r'- \*\*(.*?)\*\*:\s*(.*)', line)
                            if role_match:
                                role = role_match.group(1).strip()
                                name = role_match.group(2).strip()
                                current_contact = {
                                    'role': role,
                                    'name': name if name and name != '—' else None,
                                    'email': None,
                                    'phone': None
                                }
                        elif current_contact and line.startswith('- '):
                            # Parse contact details
                            detail_line = line[2:].strip()
                            if 'Email:' in detail_line:
                                email = detail_line.split('Email:', 1)[1].strip()
                                if email and email != '—':
                                    current_contact['email'] = email
                            elif 'Phone:' in detail_line:
                                phone = detail_line.split('Phone:', 1)[1].strip()
                                if phone and phone != '—':
                                    current_contact['phone'] = phone
                    else:
                        # Parse venue details
                        if '**Business Type**:' in line:
                            value = line.split(':', 1)[1].strip()
                            if value and value != '—':
                                venue_data['business_type'] = value

                        elif '**Zone Count**:' in line:
                            value = line.split(':', 1)[1].strip()
                            if value and value != '—':
                                try:
                                    venue_data['zone_count'] = int(value)
                                except:
                                    pass

                        elif '**Zone Names**:' in line:
                            zones_text = line.split(':', 1)[1].strip()
                            if zones_text and zones_text != '—':
                                # Split by comma and clean each zone name
                                zones = [z.strip() for z in zones_text.split(',')]
                                venue_data['zones'] = [z for z in zones if z]

                        elif '**Music Platform**:' in line:
                            value = line.split(':', 1)[1].strip()
                            if value and value != '—':
                                venue_data['platform'] = value

                        elif '**Annual Price per Zone**:' in line:
                            value = line.split(':', 1)[1].strip()
                            if value and value != '—':
                                # Extract number from string like "12,000" or "$1,000"
                                num_str = re.sub(r'[^0-9.]', '', value.replace(',', ''))
                                if num_str:
                                    try:
                                        venue_data['annual_price'] = float(num_str)
                                    except:
                                        pass

                        elif '**Currency**:' in line:
                            value = line.split(':', 1)[1].strip()
                            if value and value != '—':
                                venue_data['currency'] = value[:3]  # Get currency code

                        elif '**Contract Start**:' in line:
                            value = line.split(':', 1)[1].strip()
                            if value and value != '—':
                                try:
                                    venue_data['contract_start'] = datetime.strptime(value, '%Y-%m-%d').date()
                                except:
                                    pass

                        elif '**Contract End**:' in line:
                            value = line.split(':', 1)[1].strip()
                            if value and value != '—':
                                try:
                                    venue_data['contract_end'] = datetime.strptime(value, '%Y-%m-%d').date()
                                except:
                                    pass

                        elif '**Soundtrack Account ID**:' in line:
                            value = line.split(':', 1)[1].strip()
                            if value and value != '—':
                                venue_data['soundtrack_account_id'] = value

                        elif '**Hardware Type**:' in line:
                            value = line.split(':', 1)[1].strip()
                            if value and value != '—':
                                venue_data['hardware_type'] = value

                # Add last contact if exists
                if current_contact:
                    venue_data['contacts'].append(current_contact)

                # Validate and add venue
                if venue_data['name']:
                    venues.append(venue_data)

        except Exception as e:
            logger.error(f"Failed to parse venue data: {e}")
            raise

        logger.info(f"Parsed {len(venues)} venues from {file_path}")
        return venues

    def migrate_to_database(self, venues: List[Dict]):
        """Migrate parsed venue data to PostgreSQL database"""
        try:
            cursor = self.conn.cursor()

            # Insert venues
            logger.info("Inserting venues...")
            venue_ids = {}

            for venue in venues:
                cursor.execute("""
                    INSERT INTO venues (
                        name, business_type, zone_count, platform,
                        annual_price_per_zone, currency, contract_start,
                        contract_end, soundtrack_account_id, hardware_type,
                        is_active
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    ) RETURNING id
                """, (
                    venue['name'],
                    venue['business_type'],
                    venue['zone_count'] or len(venue['zones']),
                    venue['platform'],
                    venue['annual_price'],
                    venue['currency'],
                    venue['contract_start'],
                    venue['contract_end'],
                    venue['soundtrack_account_id'],
                    venue['hardware_type'],
                    True
                ))

                venue_id = cursor.fetchone()[0]
                venue_ids[venue['name']] = venue_id
                self.venues_created += 1

            logger.info(f"Created {self.venues_created} venues")

            # Insert zones
            logger.info("Inserting zones...")
            zones_data = []

            for venue in venues:
                venue_id = venue_ids[venue['name']]
                for idx, zone_name in enumerate(venue['zones']):
                    zones_data.append((
                        venue_id,
                        zone_name,
                        idx,
                        'active'
                    ))

            if zones_data:
                execute_batch(cursor, """
                    INSERT INTO zones (venue_id, name, zone_order, status)
                    VALUES (%s, %s, %s, %s)
                """, zones_data, page_size=100)

                self.zones_created = len(zones_data)
                logger.info(f"Created {self.zones_created} zones")

            # Insert contacts
            logger.info("Inserting contacts...")
            contacts_data = []

            for venue in venues:
                venue_id = venue_ids[venue['name']]
                for idx, contact in enumerate(venue['contacts']):
                    # First contact of each role is primary
                    is_primary = idx == 0

                    contacts_data.append((
                        venue_id,
                        contact['role'],
                        contact['name'],
                        contact['email'],
                        contact['phone'],
                        'email' if contact['email'] else 'phone',
                        is_primary
                    ))

            if contacts_data:
                execute_batch(cursor, """
                    INSERT INTO contacts (
                        venue_id, role, name, email, phone,
                        preferred_contact, is_primary
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, contacts_data, page_size=100)

                self.contacts_created = len(contacts_data)
                logger.info(f"Created {self.contacts_created} contacts")

            # Commit transaction
            self.conn.commit()
            logger.info("Migration completed successfully!")

            # Print summary
            self.print_summary()

        except Exception as e:
            # Rollback on error
            if self.conn:
                self.conn.rollback()
            logger.error(f"Migration failed: {e}")
            raise

    def print_summary(self):
        """Print migration summary"""
        print("\n" + "="*60)
        print("MIGRATION SUMMARY")
        print("="*60)
        print(f"✅ Venues created: {self.venues_created}")
        print(f"✅ Zones created: {self.zones_created}")
        print(f"✅ Contacts created: {self.contacts_created}")
        print(f"✅ Total records: {self.venues_created + self.zones_created + self.contacts_created}")
        print("="*60 + "\n")

    def verify_migration(self):
        """Verify data was migrated correctly"""
        try:
            cursor = self.conn.cursor(cursor_factory=RealDictCursor)

            # Check counts
            cursor.execute("SELECT COUNT(*) as count FROM venues")
            venue_count = cursor.fetchone()['count']

            cursor.execute("SELECT COUNT(*) as count FROM zones")
            zone_count = cursor.fetchone()['count']

            cursor.execute("SELECT COUNT(*) as count FROM contacts")
            contact_count = cursor.fetchone()['count']

            # Sample data check
            cursor.execute("""
                SELECT v.name, v.platform, COUNT(z.id) as zone_count
                FROM venues v
                LEFT JOIN zones z ON v.id = z.venue_id
                GROUP BY v.id, v.name, v.platform
                ORDER BY v.name
                LIMIT 5
            """)
            sample_venues = cursor.fetchall()

            print("\n" + "="*60)
            print("VERIFICATION RESULTS")
            print("="*60)
            print(f"Database venue count: {venue_count}")
            print(f"Database zone count: {zone_count}")
            print(f"Database contact count: {contact_count}")
            print("\nSample venues:")
            for venue in sample_venues:
                print(f"  - {venue['name']} ({venue['platform']}): {venue['zone_count']} zones")
            print("="*60 + "\n")

            return True

        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return False

def main():
    """Main migration function"""
    # Load environment variables
    load_dotenv('../.env')

    # Get database URL from environment or use default
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        # Try to build from components
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME', 'bma_social')
        db_user = os.getenv('DB_USER', 'postgres')
        db_pass = os.getenv('DB_PASSWORD', '')

        database_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

    # Venue data file path
    venue_data_file = '../venue_data.md'

    # Check if file exists
    if not os.path.exists(venue_data_file):
        logger.error(f"Venue data file not found: {venue_data_file}")
        return

    # Create migrator
    migrator = VenueDataMigrator(database_url)

    try:
        # Connect to database
        migrator.connect()

        # Parse venue data
        logger.info(f"Parsing venue data from {venue_data_file}")
        venues = migrator.parse_venue_data(venue_data_file)

        # Migrate to database
        logger.info("Starting database migration...")
        migrator.migrate_to_database(venues)

        # Verify migration
        logger.info("Verifying migration...")
        success = migrator.verify_migration()

        if success:
            logger.info("✅ Migration completed and verified successfully!")
        else:
            logger.warning("⚠️ Migration completed but verification showed issues")

    except Exception as e:
        logger.error(f"Migration failed: {e}")

    finally:
        # Disconnect
        migrator.disconnect()

if __name__ == "__main__":
    main()
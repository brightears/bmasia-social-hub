#!/usr/bin/env python3
"""
Migration script to parse product_info.md and import into PostgreSQL
Converts product information into structured database records
"""

import os
import json
import logging
from typing import Dict, List
import psycopg2
from psycopg2.extras import execute_batch
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ProductInfoMigrator:
    """Parse product_info.md and migrate to PostgreSQL database"""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.conn = None
        self.records_created = 0

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

    def create_product_records(self) -> List[tuple]:
        """Create structured product information records"""
        records = []

        # Soundtrack Your Brand (SYB) Information
        syb_records = [
            ('SYB', 'pricing', 'essential_monthly', json.dumps({'price': 29, 'currency': 'USD', 'per': 'zone/month'})),
            ('SYB', 'pricing', 'unlimited_monthly', json.dumps({'price': 39, 'currency': 'USD', 'per': 'zone/month'})),
            ('SYB', 'pricing', 'enterprise', json.dumps({'type': 'custom', 'contact': 'sales'})),

            ('SYB', 'features', 'track_library', json.dumps({
                'count': '100+ million',
                'type': 'licensed tracks from major labels and independent artists',
                'sources': ['major labels', 'independent artists', 'Spotify integration']
            })),
            ('SYB', 'features', 'zones', json.dumps({
                'multiple_zones': True,
                'per_zone_control': True,
                'scheduling': True,
                'messaging': True
            })),
            ('SYB', 'features', 'api_access', json.dumps({
                'available': True,
                'capabilities': ['volume control', 'skip tracks', 'pause/play', 'check playing'],
                'limitations': ['cannot change playlists', 'cannot block songs']
            })),
            ('SYB', 'features', 'spotify_integration', json.dumps({
                'available': True,
                'plan': 'Unlimited',
                'sync': 'automatic'
            })),

            ('SYB', 'licensing', 'reproduction_rights', json.dumps({
                'included': True,
                'covers': 'streaming and caching for background music'
            })),
            ('SYB', 'licensing', 'pro_license', json.dumps({
                'required': True,
                'exceptions': ['US', 'Canada'],
                'note': 'Most countries require local PRO license (e.g., MCPT in Thailand)'
            })),

            ('SYB', 'availability', 'countries', json.dumps({
                'count': '70+',
                'regions': {
                    'asia_pacific': ['Australia', 'India', 'Indonesia', 'Malaysia', 'Maldives', 'New Zealand', 'Singapore', 'Thailand'],
                    'europe': ['Austria', 'Belgium', 'Bulgaria', 'Croatia', 'Cyprus', 'Czech Republic', 'Denmark', 'Estonia', 'Finland', 'France', 'Germany', 'Greece', 'Hungary', 'Iceland', 'Ireland', 'Italy', 'Latvia', 'Lithuania', 'Luxembourg', 'Malta', 'Netherlands', 'Norway', 'Poland', 'Portugal', 'Slovakia', 'Spain', 'Sweden', 'Switzerland', 'UK'],
                    'north_america': ['Canada', 'Mexico', 'United States'],
                    'latin_america': ['Argentina', 'Bolivia', 'Chile', 'Colombia', 'Costa Rica', 'Ecuador', 'Guatemala', 'Honduras', 'Nicaragua', 'Panama', 'Paraguay', 'Peru', 'Uruguay'],
                    'middle_east': ['Bahrain', 'Jordan', 'Kuwait', 'Lebanon', 'Oman', 'Qatar', 'Saudi Arabia', 'UAE'],
                    'africa': ['Egypt', 'Morocco', 'South Africa']
                },
                'not_available': ['Hong Kong', 'China', 'Japan', 'South Korea', 'Russia', 'Taiwan', 'Vietnam']
            })),

            ('SYB', 'hardware', 'supported_devices', json.dumps({
                'ios': 'iOS 15.1+',
                'android': 'Android 8+',
                'windows': 'Windows 8/10/11',
                'macos': 'macOS 14.2+',
                'chrome_os': '2019+ devices',
                'dedicated': ['Soundtrack Player', 'Sonos', 'Axis speakers', 'AUDAC NMP40', 'WiiM devices']
            })),
            ('SYB', 'hardware', 'requirements', json.dumps({
                'ram': '512MB minimum',
                'storage': '2GB for install and cache',
                'network': '0.5 Mbps per device/zone',
                'connection': 'Wired or dedicated Wi-Fi recommended'
            }))
        ]

        # Beat Breeze Information
        beat_breeze_records = [
            ('Beat Breeze', 'pricing', 'basic_monthly', json.dumps({'price': 15, 'currency': 'USD', 'per': 'location/month'})),
            ('Beat Breeze', 'pricing', 'pro_monthly', json.dumps({'price': 25, 'currency': 'USD', 'per': 'location/month'})),

            ('Beat Breeze', 'features', 'track_library', json.dumps({
                'count': '30,000',
                'type': '100% royalty-free tracks',
                'sources': ['royalty-free music', 'no copyright issues']
            })),
            ('Beat Breeze', 'features', 'zones', json.dumps({
                'multiple_zones': False,
                'per_location': True,
                'note': 'One zone per location'
            })),

            ('Beat Breeze', 'licensing', 'royalty_free', json.dumps({
                'completely_royalty_free': True,
                'pro_fees': False,
                'note': 'No PRO payments ever required'
            })),
            ('Beat Breeze', 'licensing', 'global', json.dumps({
                'works_everywhere': True,
                'no_restrictions': True,
                'simple_payment': True
            })),

            ('Beat Breeze', 'availability', 'countries', json.dumps({
                'global': True,
                'note': 'Works in all countries without licensing complications'
            })),

            ('Beat Breeze', 'hardware', 'supported_devices', json.dumps({
                'android': 'Android devices and tablets',
                'windows': 'Windows PCs and compatible devices',
                'note': 'More limited device support than SYB'
            }))
        ]

        # Comparison information
        comparison_records = [
            ('Comparison', 'features', 'key_differences', json.dumps({
                'track_library': {'SYB': '100+ million', 'Beat Breeze': '30,000'},
                'music_type': {'SYB': 'Licensed major labels', 'Beat Breeze': 'Royalty-free'},
                'pro_license': {'SYB': 'Required in most countries', 'Beat Breeze': 'Never required'},
                'zones': {'SYB': 'Multiple zones per venue', 'Beat Breeze': 'One zone per location'},
                'spotify': {'SYB': 'Yes (Unlimited plan)', 'Beat Breeze': 'No'},
                'api': {'SYB': 'Full API access', 'Beat Breeze': 'Limited'},
                'price': {'SYB': '$29-39/zone/month', 'Beat Breeze': '$15-25/location/month'}
            })),

            ('Comparison', 'recommendations', 'choose_syb', json.dumps({
                'when': [
                    'Need popular, recognizable music from major labels',
                    'Want Spotify integration',
                    'Multiple zones in single venue',
                    'API integration requirements',
                    'Premium brand experience'
                ]
            })),

            ('Comparison', 'recommendations', 'choose_beat_breeze', json.dumps({
                'when': [
                    'Want completely royalty-free music',
                    'Operating in countries with expensive PRO licenses',
                    'Prefer simple, one-time payment',
                    'Budget-conscious operations',
                    '30,000 tracks is sufficient'
                ]
            }))
        ]

        # Combine all records
        records = syb_records + beat_breeze_records + comparison_records

        # Add version and is_active to all records
        return [(r[0], r[1], r[2], r[3], 1, True) for r in records]

    def migrate_to_database(self, records: List[tuple]):
        """Migrate product information to PostgreSQL database"""
        try:
            cursor = self.conn.cursor()

            # Clear existing product info
            logger.info("Clearing existing product information...")
            cursor.execute("DELETE FROM product_info")

            # Insert new records
            logger.info(f"Inserting {len(records)} product information records...")
            execute_batch(cursor, """
                INSERT INTO product_info (
                    product_name, category, key, value, version, is_active
                )
                VALUES (%s, %s, %s, %s, %s, %s)
            """, records, page_size=50)

            self.records_created = len(records)

            # Commit transaction
            self.conn.commit()
            logger.info("Product information migration completed successfully!")

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
        print("PRODUCT INFO MIGRATION SUMMARY")
        print("="*60)
        print(f"✅ Product records created: {self.records_created}")
        print("="*60 + "\n")

    def verify_migration(self):
        """Verify product data was migrated correctly"""
        try:
            cursor = self.conn.cursor()

            # Check counts by product
            cursor.execute("""
                SELECT product_name, category, COUNT(*) as count
                FROM product_info
                WHERE is_active = TRUE
                GROUP BY product_name, category
                ORDER BY product_name, category
            """)
            results = cursor.fetchall()

            print("\n" + "="*60)
            print("PRODUCT INFO VERIFICATION")
            print("="*60)
            for product, category, count in results:
                print(f"{product} - {category}: {count} records")

            # Sample some data
            cursor.execute("""
                SELECT product_name, category, key
                FROM product_info
                WHERE is_active = TRUE
                ORDER BY product_name, category, key
                LIMIT 10
            """)
            samples = cursor.fetchall()

            print("\nSample records:")
            for product, category, key in samples:
                print(f"  - {product}/{category}/{key}")
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

    # Create migrator
    migrator = ProductInfoMigrator(database_url)

    try:
        # Connect to database
        migrator.connect()

        # Create product records
        logger.info("Creating product information records...")
        records = migrator.create_product_records()

        # Migrate to database
        logger.info("Starting database migration...")
        migrator.migrate_to_database(records)

        # Verify migration
        logger.info("Verifying migration...")
        success = migrator.verify_migration()

        if success:
            logger.info("✅ Product information migration completed and verified successfully!")
        else:
            logger.warning("⚠️ Migration completed but verification showed issues")

    except Exception as e:
        logger.error(f"Migration failed: {e}")

    finally:
        # Disconnect
        migrator.disconnect()

if __name__ == "__main__":
    main()
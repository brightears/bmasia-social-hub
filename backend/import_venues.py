#!/usr/bin/env python3
"""
Import venue master data into the database
This script can import venues from CSV or JSON files
"""

import os
import sys
import json
import csv
import logging
from datetime import datetime
from typing import List, Dict, Any

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import db_manager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def import_venues_from_json(file_path: str) -> int:
    """Import venues from a JSON file"""
    with open(file_path, 'r') as f:
        venues = json.load(f)
    
    if not isinstance(venues, list):
        venues = [venues]
    
    return import_venues(venues)


def import_venues_from_csv(file_path: str) -> int:
    """Import venues from a CSV file"""
    venues = []
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert CSV row to venue dict
            venue = {
                'name': row.get('name', '').strip(),
                'phone_number': row.get('phone_number', '').strip(),
                'location': row.get('location', '').strip(),
                'soundtrack_account_id': row.get('soundtrack_account_id', '').strip(),
                'contact_name': row.get('contact_name', '').strip(),
                'contact_email': row.get('contact_email', '').strip(),
                'active': row.get('active', 'true').lower() == 'true',
                'metadata': {}
            }
            
            # Add any extra fields to metadata
            standard_fields = {'name', 'phone_number', 'location', 'soundtrack_account_id', 
                             'contact_name', 'contact_email', 'active'}
            for key, value in row.items():
                if key not in standard_fields and value:
                    venue['metadata'][key] = value
            
            venues.append(venue)
    
    return import_venues(venues)


def import_venues(venues: List[Dict[str, Any]]) -> int:
    """Import a list of venues into the database"""
    if not db_manager.ensure_connection():
        logger.error("Failed to connect to database")
        return 0
    
    imported_count = 0
    updated_count = 0
    
    with db_manager.get_cursor() as cursor:
        if not cursor:
            logger.error("Failed to get database cursor")
            return 0
        
        for venue in venues:
            try:
                # Check if venue exists by phone number
                if venue.get('phone_number'):
                    cursor.execute("""
                        SELECT id FROM venues 
                        WHERE phone_number = %s
                        LIMIT 1
                    """, (venue['phone_number'],))
                    
                    existing = cursor.fetchone()
                    
                    if existing:
                        # Update existing venue
                        cursor.execute("""
                            UPDATE venues 
                            SET name = %s,
                                location = %s,
                                soundtrack_account_id = %s,
                                contact_name = %s,
                                contact_email = %s,
                                active = %s,
                                metadata = %s,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE phone_number = %s
                            RETURNING id
                        """, (
                            venue.get('name'),
                            venue.get('location'),
                            venue.get('soundtrack_account_id'),
                            venue.get('contact_name'),
                            venue.get('contact_email'),
                            venue.get('active', True),
                            json.dumps(venue.get('metadata', {})),
                            venue['phone_number']
                        ))
                        updated_count += 1
                        logger.info(f"Updated venue: {venue.get('name')} ({venue['phone_number']})")
                    else:
                        # Insert new venue
                        cursor.execute("""
                            INSERT INTO venues 
                            (name, phone_number, location, soundtrack_account_id, 
                             contact_name, contact_email, active, metadata)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            RETURNING id
                        """, (
                            venue.get('name'),
                            venue.get('phone_number'),
                            venue.get('location'),
                            venue.get('soundtrack_account_id'),
                            venue.get('contact_name'),
                            venue.get('contact_email'),
                            venue.get('active', True),
                            json.dumps(venue.get('metadata', {}))
                        ))
                        imported_count += 1
                        logger.info(f"Imported venue: {venue.get('name')} ({venue['phone_number']})")
                else:
                    logger.warning(f"Skipping venue without phone number: {venue.get('name')}")
                    
            except Exception as e:
                logger.error(f"Failed to import venue {venue.get('name')}: {e}")
                db_manager.connection.rollback()
                continue
    
    logger.info(f"Import complete: {imported_count} new venues, {updated_count} updated")
    return imported_count + updated_count


def create_sample_venues():
    """Create sample venue data for testing"""
    sample_venues = [
        {
            "name": "Grand Plaza Hotel Bangkok",
            "phone_number": "+66812345678",
            "location": "Bangkok, Thailand",
            "soundtrack_account_id": "SYB_GRAND_PLAZA_BKK",
            "contact_name": "Somchai Jaidee",
            "contact_email": "somchai@grandplaza.com",
            "active": True,
            "metadata": {
                "zones": ["Lobby", "Restaurant", "Pool", "Spa"],
                "venue_type": "Hotel",
                "capacity": 500
            }
        },
        {
            "name": "Marina Bay Resort Singapore",
            "phone_number": "+6591234567",
            "location": "Singapore",
            "soundtrack_account_id": "SYB_MARINA_BAY_SG",
            "contact_name": "David Tan",
            "contact_email": "david@marinabay.sg",
            "active": True,
            "metadata": {
                "zones": ["Main Lobby", "Skybar", "Beach Club"],
                "venue_type": "Resort",
                "capacity": 800
            }
        },
        {
            "name": "Zen Garden Restaurant",
            "phone_number": "+60123456789",
            "location": "Kuala Lumpur, Malaysia",
            "soundtrack_account_id": "SYB_ZEN_GARDEN_KL",
            "contact_name": "Michelle Wong",
            "contact_email": "michelle@zengarden.my",
            "active": True,
            "metadata": {
                "zones": ["Dining Hall", "Private Rooms", "Terrace"],
                "venue_type": "Restaurant",
                "capacity": 200
            }
        },
        {
            "name": "Sunset Beach Club Bali",
            "phone_number": "+62811234567",
            "location": "Bali, Indonesia",
            "soundtrack_account_id": "SYB_SUNSET_BALI",
            "contact_name": "Made Wijaya",
            "contact_email": "made@sunsetbeach.id",
            "active": True,
            "metadata": {
                "zones": ["Beach Bar", "Pool Area", "Lounge"],
                "venue_type": "Beach Club",
                "capacity": 350
            }
        },
        {
            "name": "Phoenix Mall Manila",
            "phone_number": "+639123456789",
            "location": "Manila, Philippines",
            "soundtrack_account_id": "SYB_PHOENIX_MALL_MNL",
            "contact_name": "Carlos Santos",
            "contact_email": "carlos@phoenixmall.ph",
            "active": True,
            "metadata": {
                "zones": ["Main Atrium", "Food Court", "Entertainment Zone"],
                "venue_type": "Shopping Mall",
                "capacity": 5000
            }
        }
    ]
    
    # Save sample data to file
    with open('sample_venues.json', 'w') as f:
        json.dump(sample_venues, f, indent=2)
    
    logger.info(f"Created sample_venues.json with {len(sample_venues)} venues")
    return sample_venues


def main():
    """Main function to run the import"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Import venue data into database')
    parser.add_argument('--file', help='Path to JSON or CSV file to import')
    parser.add_argument('--create-sample', action='store_true', 
                       help='Create and import sample venue data')
    
    args = parser.parse_args()
    
    if args.create_sample:
        logger.info("Creating and importing sample venue data...")
        sample_venues = create_sample_venues()
        count = import_venues(sample_venues)
        logger.info(f"Successfully imported {count} sample venues")
        
    elif args.file:
        file_path = args.file
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            sys.exit(1)
        
        logger.info(f"Importing venues from {file_path}...")
        
        if file_path.endswith('.json'):
            count = import_venues_from_json(file_path)
        elif file_path.endswith('.csv'):
            count = import_venues_from_csv(file_path)
        else:
            logger.error("Unsupported file format. Use .json or .csv")
            sys.exit(1)
        
        logger.info(f"Successfully imported {count} venues")
        
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
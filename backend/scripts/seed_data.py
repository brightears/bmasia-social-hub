#!/usr/bin/env python3
"""
Seed initial data for BMA Social.
Creates sample venues, zones, and team members for testing.
"""

import asyncio
import sys
import uuid
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.core.database import db_manager
from app.models import Venue, Zone, TeamMember
from app.models.team import TeamRole


# Sample venue data
SAMPLE_VENUES = [
    {
        "name": "Anantara Riverside Bangkok",
        "code": "ANANTARA-BKK-001",
        "brand": "Anantara",
        "venue_type": "hotel",
        "country": "TH",
        "city": "Bangkok",
        "timezone": "Asia/Bangkok",
        "whatsapp_number": "+66812345678",
        "soundtrack_account_id": "demo_account_1",
        "priority": 3,  # VIP
        "zones": [
            {"name": "Main Lobby", "zone_type": "lobby", "soundtrack_device_id": "device_001"},
            {"name": "Pool Bar", "zone_type": "pool", "soundtrack_device_id": "device_002"},
            {"name": "Riverside Restaurant", "zone_type": "restaurant", "soundtrack_device_id": "device_003"},
            {"name": "Spa Reception", "zone_type": "spa", "soundtrack_device_id": "device_004"},
        ]
    },
    {
        "name": "Hilton Sukhumvit Bangkok",
        "code": "HILTON-BKK-001",
        "brand": "Hilton",
        "venue_type": "hotel",
        "country": "TH",
        "city": "Bangkok",
        "timezone": "Asia/Bangkok",
        "whatsapp_number": "+66823456789",
        "soundtrack_account_id": "demo_account_2",
        "priority": 2,  # Premium
        "zones": [
            {"name": "Lobby Lounge", "zone_type": "lobby", "soundtrack_device_id": "device_005"},
            {"name": "Rooftop Bar", "zone_type": "bar", "soundtrack_device_id": "device_006"},
            {"name": "All Day Dining", "zone_type": "restaurant", "soundtrack_device_id": "device_007"},
        ]
    },
    {
        "name": "Central World Mall",
        "code": "CENTRAL-BKK-001",
        "brand": "Central",
        "venue_type": "retail",
        "country": "TH",
        "city": "Bangkok",
        "timezone": "Asia/Bangkok",
        "whatsapp_number": "+66834567890",
        "soundtrack_account_id": "demo_account_3",
        "priority": 2,
        "zones": [
            {"name": "Main Atrium", "zone_type": "retail", "soundtrack_device_id": "device_008"},
            {"name": "Food Court", "zone_type": "restaurant", "soundtrack_device_id": "device_009"},
            {"name": "Fashion Zone", "zone_type": "retail", "soundtrack_device_id": "device_010"},
            {"name": "Kids Zone", "zone_type": "retail", "soundtrack_device_id": "device_011"},
        ]
    },
    {
        "name": "Starbucks Siam Paragon",
        "code": "STARBUCKS-BKK-001",
        "brand": "Starbucks",
        "venue_type": "restaurant",
        "country": "TH",
        "city": "Bangkok",
        "timezone": "Asia/Bangkok",
        "whatsapp_number": "+66845678901",
        "soundtrack_account_id": "demo_account_4",
        "priority": 1,  # Standard
        "zones": [
            {"name": "Main Floor", "zone_type": "restaurant", "soundtrack_device_id": "device_012"},
            {"name": "Outdoor Terrace", "zone_type": "outdoor", "soundtrack_device_id": "device_013"},
        ]
    },
    {
        "name": "Four Seasons Dubai",
        "code": "FOURSEASONS-DXB-001",
        "brand": "Four Seasons",
        "venue_type": "hotel",
        "country": "AE",
        "city": "Dubai",
        "timezone": "Asia/Dubai",
        "whatsapp_number": "+971501234567",
        "soundtrack_account_id": "demo_account_5",
        "priority": 3,  # VIP
        "prayer_time_pause": True,  # Enable for Middle East
        "zones": [
            {"name": "Grand Lobby", "zone_type": "lobby", "soundtrack_device_id": "device_014"},
            {"name": "Beach Club", "zone_type": "pool", "soundtrack_device_id": "device_015"},
            {"name": "Fine Dining", "zone_type": "restaurant", "soundtrack_device_id": "device_016"},
            {"name": "Shisha Lounge", "zone_type": "bar", "soundtrack_device_id": "device_017"},
        ]
    }
]

# Sample team members
SAMPLE_TEAM_MEMBERS = [
    {
        "email": "admin@bma-social.com",
        "name": "Admin User",
        "role": TeamRole.ADMIN,
        "password": "admin123",  # In production, this would be hashed
    },
    {
        "email": "manager@bma-social.com",
        "name": "Manager User",
        "role": TeamRole.MANAGER,
        "password": "manager123",
    },
    {
        "email": "support1@bma-social.com",
        "name": "Support Agent 1",
        "role": TeamRole.SUPPORT,
        "password": "support123",
        "specializations": ["technical", "music"],
        "language_skills": ["en", "th"],
    },
    {
        "email": "support2@bma-social.com",
        "name": "Support Agent 2",
        "role": TeamRole.SUPPORT,
        "password": "support123",
        "specializations": ["billing", "general"],
        "language_skills": ["en", "ar"],
    }
]


def clear_existing_data():
    """Clear existing data from tables"""
    print("Clearing existing data...")
    
    with db_manager.get_session() as session:
        # Clear in order due to foreign keys
        from sqlalchemy import text
        session.execute(text("DELETE FROM zones"))
        session.execute(text("DELETE FROM venues"))
        session.execute(text("DELETE FROM team_members"))
        session.commit()
    
    print("✅ Existing data cleared")


def seed_team_members():
    """Create team members"""
    print("\nCreating team members...")
    
    with db_manager.get_session() as session:
        for member_data in SAMPLE_TEAM_MEMBERS:
            # Check if already exists
            result = session.execute(
                select(TeamMember).where(TeamMember.email == member_data["email"])
            )
            existing = result.scalar_one_or_none()
            
            if not existing:
                # Create new team member
                member = TeamMember(
                    id=uuid.uuid4(),
                    email=member_data["email"],
                    name=member_data["name"],
                    role=member_data["role"],
                    password_hash=f"hashed_{member_data['password']}",  # In production, use proper hashing
                    is_active=True,
                    specializations=member_data.get("specializations", []),
                    language_skills=member_data.get("language_skills", ["en"]),
                )
                
                session.add(member)
                print(f"  ✅ Created team member: {member.name} ({member.role.value})")
            else:
                print(f"  ⏭️  Team member already exists: {existing.name}")
        
        session.commit()


def seed_venues():
    """Create sample venues with zones"""
    print("\nCreating sample venues...")
    
    with db_manager.get_session() as session:
        for venue_data in SAMPLE_VENUES:
            # Check if venue already exists
            result = session.execute(
                select(Venue).where(Venue.code == venue_data["code"])
            )
            existing = result.scalar_one_or_none()
            
            if not existing:
                # Create venue
                venue = Venue(
                    id=uuid.uuid4(),
                    name=venue_data["name"],
                    code=venue_data["code"],
                    brand=venue_data["brand"],
                    venue_type=venue_data["venue_type"],
                    country=venue_data["country"],
                    city=venue_data["city"],
                    timezone=venue_data["timezone"],
                    whatsapp_number=venue_data.get("whatsapp_number"),
                    soundtrack_account_id=venue_data["soundtrack_account_id"],
                    priority=venue_data["priority"],
                    is_active=True,
                    monitoring_enabled=True,
                    prayer_time_pause=venue_data.get("prayer_time_pause", False),
                    total_zones=len(venue_data["zones"]),
                )
                
                session.add(venue)
                print(f"  ✅ Created venue: {venue.name}")
                
                # Create zones for this venue
                for zone_data in venue_data["zones"]:
                    zone = Zone(
                        id=uuid.uuid4(),
                        venue_id=venue.id,
                        name=zone_data["name"],
                        zone_type=zone_data["zone_type"],
                        soundtrack_device_id=zone_data["soundtrack_device_id"],
                        is_online=True,  # Start as online for demo
                        volume=50,
                        is_playing=True,
                        alert_enabled=True,
                        last_checked_at=datetime.utcnow(),
                    )
                    
                    session.add(zone)
                    print(f"    ✅ Created zone: {zone.name}")
            else:
                print(f"  ⏭️  Venue already exists: {existing.name}")
        
        session.commit()


def print_summary():
    """Print summary of seeded data"""
    print("\n" + "="*60)
    print("Seed Data Summary")
    print("="*60)
    
    with db_manager.get_session() as session:
        # Count venues
        from sqlalchemy import text
        venue_count = session.execute(text("SELECT COUNT(*) FROM venues"))
        venues = venue_count.scalar()
        
        # Count zones
        zone_count = session.execute(text("SELECT COUNT(*) FROM zones"))
        zones = zone_count.scalar()
        
        # Count team members
        team_count = session.execute(text("SELECT COUNT(*) FROM team_members"))
        team = team_count.scalar()
        
        print(f"✅ Venues created: {venues}")
        print(f"✅ Zones created: {zones}")
        print(f"✅ Team members created: {team}")


def main():
    """Main seed function"""
    print("="*60)
    print("BMA Social - Seed Data Script")
    print("="*60)
    
    try:
        # Initialize database connection
        db_manager.initialize()
        
        # Ask user if they want to clear existing data
        response = input("\nClear existing data before seeding? (y/N): ")
        if response.lower() == 'y':
            clear_existing_data()
        
        # Seed data
        seed_team_members()
        seed_venues()
        
        # Print summary
        print_summary()
        
        print("\n✅ Seed data creation complete!")
        print("\nYou can now:")
        print("1. Start the API: cd backend && uvicorn app.main:app --reload")
        print("2. View venues at: http://localhost:8000/api/v1/venues")
        print("3. Test webhooks at: http://localhost:8000/docs")
        
    except Exception as e:
        print(f"❌ Error seeding data: {e}")
        sys.exit(1)
    finally:
        db_manager.close()


if __name__ == "__main__":
    main()
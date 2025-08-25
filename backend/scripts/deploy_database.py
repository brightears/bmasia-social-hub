#!/usr/bin/env python3
"""
Deploy database for BMA Social.
Creates database (if not exists) and runs all migrations.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy import create_engine
import psycopg2

from app.config import settings


def create_database_if_not_exists():
    """Create database if it doesn't exist"""
    
    # Parse database URL to get components
    db_url = os.getenv("DATABASE_URL", settings.database_url)
    
    # Extract database name
    if "bma_social" in db_url:
        db_name = "bma_social"
    else:
        # Extract from URL pattern
        parts = db_url.split("/")
        db_name = parts[-1].split("?")[0]
    
    # Create connection to postgres database (not the target database)
    # Convert async URL to sync URL
    if "postgresql+asyncpg://" in db_url:
        postgres_url = db_url.replace("postgresql+asyncpg://", "postgresql://").replace(f"/{db_name}", "/postgres")
    elif "asyncpg://" in db_url:
        postgres_url = db_url.replace("asyncpg://", "postgresql://").replace(f"/{db_name}", "/postgres")
    else:
        postgres_url = db_url
    
    print(f"Checking if database '{db_name}' exists...")
    
    try:
        # Connect to postgres database
        engine = create_engine(postgres_url, isolation_level="AUTOCOMMIT")
        
        with engine.connect() as conn:
            # Check if database exists
            result = conn.execute(
                text(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'")
            )
            exists = result.scalar()
            
            if not exists:
                print(f"Creating database '{db_name}'...")
                conn.execute(text(f"CREATE DATABASE {db_name}"))
                print(f"✅ Database '{db_name}' created successfully!")
            else:
                print(f"✅ Database '{db_name}' already exists")
        
        engine.dispose()
        
    except Exception as e:
        print(f"Note: Could not check/create database: {e}")
        print("This is normal on Render.com as the database is pre-created")


def run_migrations():
    """Run alembic migrations"""
    import subprocess
    
    print("\nRunning database migrations...")
    
    # Change to backend directory
    backend_dir = Path(__file__).parent.parent
    os.chdir(backend_dir)
    
    # Run alembic upgrade
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("✅ Migrations completed successfully!")
        print(result.stdout)
    else:
        print("❌ Migration failed:")
        print(result.stderr)
        sys.exit(1)


def verify_tables():
    """Verify that tables were created"""
    from app.core.database import db_manager
    
    print("\nVerifying database tables...")
    
    try:
        db_manager.initialize()
        
        with db_manager.get_session() as session:
            # Check for key tables
            tables_to_check = [
                "venues",
                "zones", 
                "conversations",
                "messages",
                "team_members",
                "monitoring_logs",
                "alerts"
            ]
            
            for table_name in tables_to_check:
                result = session.execute(
                    text(f"SELECT COUNT(*) FROM information_schema.tables WHERE table_name = :table"),
                    {"table": table_name}
                )
                exists = result.scalar() > 0
                
                if exists:
                    print(f"  ✅ Table '{table_name}' exists")
                else:
                    print(f"  ❌ Table '{table_name}' NOT FOUND")
        
        db_manager.close()
        
    except Exception as e:
        print(f"❌ Error verifying tables: {e}")


def main():
    """Main deployment function"""
    
    print("="*60)
    print("BMA Social Database Deployment")
    print("="*60)
    
    # Step 1: Create database if needed
    create_database_if_not_exists()
    
    # Step 2: Run migrations
    run_migrations()
    
    # Step 3: Verify tables
    verify_tables()
    
    print("\n" + "="*60)
    print("✅ Database deployment complete!")
    print("="*60)
    print("\nNext steps:")
    print("1. Run seed data script: python scripts/seed_data.py")
    print("2. Start the API: cd backend && uvicorn app.main:app --reload")
    print("3. Test the API: http://localhost:8000/docs")


if __name__ == "__main__":
    main()
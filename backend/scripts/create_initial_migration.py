#!/usr/bin/env python3
"""
Create initial database migration for BMA Social.
Run this to generate the migration file from SQLAlchemy models.
"""

import subprocess
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))


def main():
    """Create initial migration"""
    
    print("Creating initial database migration for BMA Social...")
    
    # Change to backend directory
    backend_dir = Path(__file__).parent.parent
    os.chdir(backend_dir)
    
    # Run alembic revision with autogenerate
    try:
        result = subprocess.run(
            [
                "alembic",
                "revision",
                "--autogenerate",
                "-m",
                "Initial schema with venues zones conversations and monitoring"
            ],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✅ Migration created successfully!")
            print(result.stdout)
            
            # Show next steps
            print("\n" + "="*50)
            print("Next steps:")
            print("1. Review the generated migration file in alembic/versions/")
            print("2. Run migrations with: alembic upgrade head")
            print("3. Or use the deploy script: python scripts/deploy_database.py")
        else:
            print("❌ Failed to create migration:")
            print(result.stderr)
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error creating migration: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
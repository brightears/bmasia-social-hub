#!/usr/bin/env python3
"""Test database connection"""

import os
import psycopg2
from urllib.parse import urlparse

# Your database URL
DATABASE_URL = "postgresql://bma_user:wVLGYkim3mf3qYocucd6IhXjogfLbZAb@dpg-d2m6jrre5dus739fr8p0-a/bma_social_esoq"

def test_connection():
    """Test PostgreSQL connection"""
    try:
        # Parse the URL
        result = urlparse(DATABASE_URL)
        
        print(f"Connecting to database...")
        print(f"Host: {result.hostname}")
        print(f"Database: {result.path[1:]}")
        print(f"User: {result.username}")
        
        # Connect
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Test query
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"\n✅ Connection successful!")
        print(f"PostgreSQL version: {version[0]}")
        
        # Check tables
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = cursor.fetchall()
        
        if tables:
            print(f"\nExisting tables:")
            for table in tables:
                print(f"  - {table[0]}")
        else:
            print("\nNo tables yet (database is empty)")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"\n❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    test_connection()
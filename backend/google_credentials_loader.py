"""
Google Credentials Loader for BMA Social
Loads Google service account credentials from various sources
"""

import os
import json
import logging

logger = logging.getLogger(__name__)

def load_google_credentials():
    """
    Load Google service account credentials from available sources
    Returns the credentials dict or None
    """
    
    # Method 1: Check environment variable
    creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
    if creds_json:
        try:
            logger.info("Loading Google credentials from GOOGLE_CREDENTIALS_JSON env var")
            return json.loads(creds_json)
        except:
            logger.warning("Failed to parse GOOGLE_CREDENTIALS_JSON")
    
    # Method 2: Check for bamboo-theorem credentials file (existing setup)
    possible_files = [
        'bamboo-theorem-399923-credentials.json',
        'bamboo-theorem-credentials.json',
        'google-credentials.json',
        'service-account.json',
        'bma-social-support-bot.json',
        'credentials.json'
    ]
    
    for filename in possible_files:
        filepath = os.path.join(os.path.dirname(__file__), filename)
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r') as f:
                    logger.info(f"Loading Google credentials from file: {filename}")
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load {filename}: {e}")
    
    # Method 3: Use the known service account info (bamboo-theorem project)
    # This is based on the service account email we found: bma-social-service@bamboo-theorem-399923.iam.gserviceaccount.com
    # NOTE: This won't work without the private key, but shows the structure
    logger.warning("No Google credentials found. Please add one of these:")
    logger.warning("1. Set GOOGLE_CREDENTIALS_JSON in .env file")
    logger.warning("2. Place credentials file in backend directory")
    logger.warning("3. Named: bamboo-theorem-399923-credentials.json or bma-social-support-bot.json")
    
    return None

def get_space_id():
    """Get the Google Chat space ID"""
    # From .env we know it's: spaces/AAQA3gAn8GY
    space_id = os.getenv('GCHAT_BMASIA_ALL_SPACE', 'spaces/AAQA3gAn8GY')
    
    # Ensure it has the correct format
    if space_id and not space_id.startswith('spaces/'):
        space_id = f'spaces/{space_id}'
    
    return space_id
"""
Google Sheets Integration Client
Manages connection to Google Sheets for venue master data
"""

import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import hashlib
import json
from difflib import SequenceMatcher

# Google Sheets API imports
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    SHEETS_AVAILABLE = True
except ImportError:
    SHEETS_AVAILABLE = False
    service_account = None
    build = None
    HttpError = None

logger = logging.getLogger(__name__)

class GoogleSheetsClient:
    """
    Client for Google Sheets API integration
    Manages venue master data retrieval and synchronization
    """
    
    def __init__(self, credentials_path: Optional[str] = None, spreadsheet_id: Optional[str] = None):
        self.credentials_path = credentials_path or os.getenv('GOOGLE_SHEETS_CREDENTIALS_PATH')
        self.spreadsheet_id = spreadsheet_id or os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID', 
                                                         '1xiXrJCmI-FgqtXcPCn4sKbcicDj2Q8kQe0yXjztpovM')
        
        self.service = None
        self.sheet = None
        self.last_sync = None
        self.sync_interval = timedelta(minutes=30)  # Sync every 30 minutes
        
        # Column mapping for the spreadsheet
        self.column_mapping = {
            'A': 'venue_id',
            'B': 'venue_name',
            'C': 'location',
            'D': 'contact_name',
            'E': 'contact_email',
            'F': 'contact_phone',
            'G': 'soundtrack_account_id',
            'H': 'zone_count',
            'I': 'subscription_status',
            'J': 'last_issue_date',
            'K': 'notes',
            'L': 'priority_level',
            'M': 'sla_tier'
        }
        
        # Cache for venue data
        self.venue_cache = {}
        self.cache_expiry = {}
        
        if SHEETS_AVAILABLE:
            self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Google Sheets API client"""
        try:
            if self.credentials_path and os.path.exists(self.credentials_path):
                credentials = service_account.Credentials.from_service_account_file(
                    self.credentials_path,
                    scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
                )
            else:
                # Try using default credentials or environment variable
                credentials_json = os.getenv('GOOGLE_SHEETS_CREDENTIALS_JSON')
                if credentials_json:
                    credentials_info = json.loads(credentials_json)
                    credentials = service_account.Credentials.from_service_account_info(
                        credentials_info,
                        scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
                    )
                else:
                    logger.warning("No Google Sheets credentials found")
                    return
            
            self.service = build('sheets', 'v4', credentials=credentials)
            self.sheet = self.service.spreadsheets()
            logger.info("Google Sheets client initialized successfully")
            
            # Perform initial sync
            self.sync_venues()
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets client: {e}")
            self.service = None
            self.sheet = None
    
    def sync_venues(self) -> bool:
        """
        Sync venue data from Google Sheets
        Returns True if sync successful
        """
        if not self.sheet:
            logger.warning("Google Sheets client not initialized")
            return False
        
        try:
            # Define the range to read (adjust based on your sheet structure)
            range_name = 'Sheet1!A2:M'  # Skip header row
            
            result = self.sheet.values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            
            if not values:
                logger.warning('No data found in Google Sheet')
                return False
            
            # Clear and rebuild cache
            self.venue_cache.clear()
            self.cache_expiry.clear()
            
            for row in values:
                # Parse row data based on column mapping
                venue_data = self._parse_row(row)
                if venue_data and venue_data.get('venue_name'):
                    # Cache by multiple keys for flexible lookup
                    venue_id = venue_data.get('venue_id')
                    venue_name = venue_data.get('venue_name')
                    
                    if venue_id:
                        self.venue_cache[f"id:{venue_id}"] = venue_data
                    
                    if venue_name:
                        self.venue_cache[f"name:{venue_name.lower()}"] = venue_data
                    
                    # Also cache by phone if available
                    if venue_data.get('contact_phone'):
                        self.venue_cache[f"phone:{venue_data['contact_phone']}"] = venue_data
            
            self.last_sync = datetime.utcnow()
            logger.info(f"Successfully synced {len(self.venue_cache)} venues from Google Sheets")
            return True
            
        except HttpError as e:
            logger.error(f"Google Sheets API error: {e}")
            return False
        except Exception as e:
            logger.error(f"Error syncing venues from Google Sheets: {e}")
            return False
    
    def _parse_row(self, row: List[str]) -> Dict[str, Any]:
        """Parse a row from the spreadsheet into venue data"""
        venue_data = {}
        
        # Map columns to fields
        for i, value in enumerate(row):
            if i >= len(self.column_mapping):
                break
            
            column = chr(ord('A') + i)  # Convert index to column letter
            field_name = self.column_mapping.get(column)
            
            if field_name and value:
                # Clean and convert data types
                if field_name == 'venue_id':
                    try:
                        venue_data[field_name] = int(value)
                    except ValueError:
                        venue_data[field_name] = value
                elif field_name == 'zone_count':
                    try:
                        venue_data[field_name] = int(value)
                    except ValueError:
                        venue_data[field_name] = 0
                elif field_name == 'last_issue_date':
                    # Parse date if needed
                    venue_data[field_name] = value
                else:
                    venue_data[field_name] = value.strip()
        
        # Add metadata
        venue_data['source'] = 'google_sheets'
        venue_data['last_updated'] = datetime.utcnow().isoformat()
        
        return venue_data
    
    async def get_venue(self, venue_id: Optional[int] = None, 
                       venue_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get venue data from cache or fetch from Sheets"""
        
        # Check if we need to resync
        if self._should_resync():
            self.sync_venues()
        
        # Try to find venue in cache
        if venue_id:
            venue = self.venue_cache.get(f"id:{venue_id}")
            if venue:
                return venue
        
        if venue_name:
            # Try exact match first
            venue = self.venue_cache.get(f"name:{venue_name.lower()}")
            if venue:
                return venue
            
            # Try fuzzy matching
            return self._fuzzy_search_venue(venue_name)
        
        return None
    
    def search_venues(self, query: str, phone: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for venues matching query
        Returns list with confidence scores
        """
        # Check if we need to resync
        if self._should_resync():
            self.sync_venues()
        
        results = []
        query_lower = query.lower()
        
        # If phone provided, try exact phone match first
        if phone:
            phone_venue = self.venue_cache.get(f"phone:{phone}")
            if phone_venue:
                phone_venue['confidence'] = 1.0
                results.append(phone_venue)
        
        # Search by name
        for key, venue in self.venue_cache.items():
            if not key.startswith('name:'):
                continue
            
            venue_name = venue.get('venue_name', '').lower()
            
            # Calculate similarity score
            similarity = SequenceMatcher(None, query_lower, venue_name).ratio()
            
            if similarity > 0.5:  # Threshold for matches
                result = venue.copy()
                result['confidence'] = similarity
                
                # Boost confidence if phone also matches
                if phone and venue.get('contact_phone') == phone:
                    result['confidence'] = min(1.0, result['confidence'] + 0.2)
                
                # Avoid duplicates
                if not any(r.get('venue_id') == result.get('venue_id') for r in results):
                    results.append(result)
        
        # Sort by confidence
        results.sort(key=lambda x: x['confidence'], reverse=True)
        
        return results[:10]  # Return top 10 matches
    
    def _fuzzy_search_venue(self, venue_name: str) -> Optional[Dict[str, Any]]:
        """Fuzzy search for venue by name"""
        best_match = None
        best_score = 0
        name_lower = venue_name.lower()
        
        for key, venue in self.venue_cache.items():
            if not key.startswith('name:'):
                continue
            
            cached_name = venue.get('venue_name', '').lower()
            score = SequenceMatcher(None, name_lower, cached_name).ratio()
            
            if score > best_score and score > 0.7:  # 70% similarity threshold
                best_score = score
                best_match = venue.copy()
                best_match['confidence'] = score
        
        return best_match
    
    def _should_resync(self) -> bool:
        """Check if we should resync with Google Sheets"""
        if not self.last_sync:
            return True
        
        time_since_sync = datetime.utcnow() - self.last_sync
        return time_since_sync > self.sync_interval
    
    def get_all_venues(self) -> List[Dict[str, Any]]:
        """Get all venues from cache"""
        if self._should_resync():
            self.sync_venues()
        
        # Return unique venues
        unique_venues = {}
        for key, venue in self.venue_cache.items():
            venue_id = venue.get('venue_id')
            if venue_id and venue_id not in unique_venues:
                unique_venues[venue_id] = venue
        
        return list(unique_venues.values())
    
    def update_spreadsheet_id(self, spreadsheet_id: str):
        """Update the spreadsheet ID and resync"""
        self.spreadsheet_id = spreadsheet_id
        self.venue_cache.clear()
        self.last_sync = None
        
        if self.sheet:
            return self.sync_venues()
        return False
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status"""
        return {
            'connected': self.sheet is not None,
            'last_sync': self.last_sync.isoformat() if self.last_sync else None,
            'venue_count': len(set(v.get('venue_id') for v in self.venue_cache.values() if v.get('venue_id'))),
            'spreadsheet_id': self.spreadsheet_id,
            'next_sync': (self.last_sync + self.sync_interval).isoformat() if self.last_sync else None
        }
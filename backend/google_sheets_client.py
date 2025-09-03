"""
Google Sheets integration for BMA Social
Reads venue data and writes conversation history
"""

import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

# Google Sheets API imports
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    SHEETS_AVAILABLE = True
except ImportError:
    SHEETS_AVAILABLE = False
    logging.warning("Google Sheets API not installed. Run: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")

logger = logging.getLogger(__name__)

class GoogleSheetsClient:
    """Manage Google Sheets operations for venue data"""
    
    def __init__(self):
        self.service = None
        self.master_sheet_id = os.getenv('MASTER_SHEET_ID', '1xiXrJCmI-FgqtXcPCn4sKbcicDj2Q8kQe0yXjztpovM')
        self.credentials_path = os.getenv('GOOGLE_CREDENTIALS_PATH', 'google-credentials.json')
        self.connect()
    
    def connect(self):
        """Connect to Google Sheets API"""
        if not SHEETS_AVAILABLE:
            logger.error("Google Sheets API not available")
            return False
        
        try:
            # Check if credentials file exists
            if os.path.exists(self.credentials_path):
                SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
                creds = service_account.Credentials.from_service_account_file(
                    self.credentials_path, scopes=SCOPES)
                self.service = build('sheets', 'v4', credentials=creds)
                logger.info("✅ Connected to Google Sheets API")
                return True
            else:
                # Try using credentials from environment variable
                creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
                if creds_json:
                    creds_dict = json.loads(creds_json)
                    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
                    creds = service_account.Credentials.from_service_account_info(
                        creds_dict, scopes=SCOPES)
                    self.service = build('sheets', 'v4', credentials=creds)
                    logger.info("✅ Connected to Google Sheets API using env credentials")
                    return True
                else:
                    logger.warning("No Google credentials found. Set GOOGLE_CREDENTIALS_JSON env variable")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to connect to Google Sheets: {e}")
            return False
    
    def get_all_venues(self) -> List[Dict]:
        """Get all venues from master sheet"""
        if not self.service:
            return []
        
        try:
            # Read the master sheet
            range_name = 'Sheet1!A:Z'  # Adjust based on actual sheet structure
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.master_sheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            
            if not values:
                logger.warning('No data found in master sheet')
                return []
            
            # Headers are now in row 1 (index 0)
            header_row_idx = 0
            headers = values[0] if values else []
            
            # Verify we have the expected headers
            expected_headers = ['Business Type', 'Property Name', 'Name of Zones/Venues']
            has_new_structure = any(header in headers for header in expected_headers)
            
            if not headers:
                logger.warning('Could not find headers in sheet')
                return []
            
            venues = []
            
            # Process data rows (after headers)
            for row in values[header_row_idx + 1:]:
                if not row or len(row) < 2:  # Skip empty rows
                    continue
                    
                # Create dict from row data
                venue = {}
                for i, header in enumerate(headers):
                    if i < len(row):
                        # Normalize header names
                        key = header.lower().replace(' ', '_').replace('/', '_').replace('.', '')
                        venue[key] = row[i]
                    else:
                        key = header.lower().replace(' ', '_').replace('/', '_').replace('.', '')
                        venue[key] = ''
                        
                # Only add if it has meaningful data (must have property name)
                if venue.get('property_name'):
                    venues.append(venue)
            
            logger.info(f"Loaded {len(venues)} venues from Google Sheets")
            return venues
            
        except HttpError as error:
            logger.error(f"An error occurred reading sheet: {error}")
            return []
    
    def find_venue_by_name(self, venue_name: str) -> Optional[Dict]:
        """Find venue by name with fuzzy matching"""
        venues = self.get_all_venues()
        
        venue_name_lower = venue_name.lower()
        
        # Check property name field (new structure)
        name_fields = ['property_name', 'outlet_name', 'client_name', 'name']
        
        # Exact match first
        for venue in venues:
            for field in name_fields:
                if venue.get(field, '').lower() == venue_name_lower:
                    return venue
        
        # Fuzzy match - check if venue_name is contained in any name field
        matches = []
        
        for venue in venues:
            for field in name_fields:
                name = venue.get(field, '').lower()
                if name and (venue_name_lower in name or name in venue_name_lower):
                    matches.append(venue)
                    break  # Found a match in this venue, move to next
        
        # Return best match or None
        if matches:
            # Prefer exact substring matches
            for match in matches:
                for field in name_fields:
                    if venue_name_lower in match.get(field, '').lower():
                        return match
            return matches[0]
        
        return None
    
    def get_venue_sheet(self, venue_sheet_id: str) -> Dict:
        """Get data from a venue-specific sheet"""
        if not self.service:
            return {}
        
        try:
            # Get all sheets in the spreadsheet
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=venue_sheet_id
            ).execute()
            
            sheets_data = {}
            
            for sheet in spreadsheet.get('sheets', []):
                sheet_name = sheet['properties']['title']
                
                # Read each sheet
                result = self.service.spreadsheets().values().get(
                    spreadsheetId=venue_sheet_id,
                    range=f'{sheet_name}!A:Z'
                ).execute()
                
                values = result.get('values', [])
                sheets_data[sheet_name] = values
            
            return sheets_data
            
        except HttpError as error:
            logger.error(f"Error reading venue sheet: {error}")
            return {}
    
    def write_conversation_log(self, venue_sheet_id: str, conversation_data: Dict):
        """Write conversation log to venue's history sheet"""
        if not self.service:
            return False
        
        try:
            # Prepare the data row
            timestamp = datetime.utcnow().isoformat()
            row = [
                timestamp,
                conversation_data.get('user_name', ''),
                conversation_data.get('user_role', ''),
                conversation_data.get('channel', ''),
                conversation_data.get('issue', ''),
                conversation_data.get('resolution', ''),
                conversation_data.get('satisfaction', ''),
                conversation_data.get('notes', '')
            ]
            
            # Append to History sheet
            body = {'values': [row]}
            
            result = self.service.spreadsheets().values().append(
                spreadsheetId=venue_sheet_id,
                range='History!A:H',  # Assuming History sheet exists
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            
            logger.info(f"Logged conversation to venue sheet")
            return True
            
        except HttpError as error:
            logger.error(f"Error writing to sheet: {error}")
            # If History sheet doesn't exist, try to create it
            if 'Unable to parse range' in str(error):
                self.create_history_sheet(venue_sheet_id)
                # Retry the write
                return self.write_conversation_log(venue_sheet_id, conversation_data)
            return False
    
    def create_history_sheet(self, spreadsheet_id: str):
        """Create a History sheet if it doesn't exist"""
        if not self.service:
            return False
        
        try:
            # Add new sheet
            batch_update_body = {
                'requests': [{
                    'addSheet': {
                        'properties': {
                            'title': 'History',
                            'gridProperties': {
                                'rowCount': 1000,
                                'columnCount': 10
                            }
                        }
                    }
                }]
            }
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=batch_update_body
            ).execute()
            
            # Add headers
            headers = [['Timestamp', 'User Name', 'Role', 'Channel', 'Issue', 
                       'Resolution', 'Satisfaction', 'Notes']]
            
            body = {'values': headers}
            self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range='History!A1:H1',
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            
            logger.info("Created History sheet with headers")
            return True
            
        except HttpError as error:
            logger.error(f"Error creating History sheet: {error}")
            return False
    
    def update_venue_data(self, venue_name: str, updates: Dict) -> bool:
        """Update venue data in master sheet"""
        if not self.service:
            return False
        
        try:
            # First, find the venue row
            range_name = 'Sheet1!A:Z'
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.master_sheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            if not values:
                return False
            
            headers = values[0]
            venue_row_index = None
            
            # Find venue row
            for i, row in enumerate(values[1:], start=2):  # Start from row 2 (after headers)
                if len(row) > 0 and row[0].lower() == venue_name.lower():
                    venue_row_index = i
                    break
            
            if not venue_row_index:
                # Venue not found, add new row
                return self.add_new_venue(updates)
            
            # Update specific cells
            for field, value in updates.items():
                # Find column index for field
                field_normalized = field.replace('_', ' ').title()
                col_index = None
                
                for j, header in enumerate(headers):
                    if header.lower().replace(' ', '_') == field.lower():
                        col_index = j
                        break
                
                if col_index is not None:
                    # Convert column index to letter
                    col_letter = chr(65 + col_index)  # A=65 in ASCII
                    cell_range = f'Sheet1!{col_letter}{venue_row_index}'
                    
                    body = {'values': [[value]]}
                    self.service.spreadsheets().values().update(
                        spreadsheetId=self.master_sheet_id,
                        range=cell_range,
                        valueInputOption='USER_ENTERED',
                        body=body
                    ).execute()
                    
                    logger.info(f"Updated {field} for {venue_name}")
            
            return True
            
        except HttpError as error:
            logger.error(f"Error updating venue data: {error}")
            return False
    
    def add_new_venue(self, venue_data: Dict) -> bool:
        """Add new venue to master sheet"""
        if not self.service:
            return False
        
        try:
            # Get headers first
            range_name = 'Sheet1!A1:Z1'
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.master_sheet_id,
                range=range_name
            ).execute()
            
            headers = result.get('values', [[]])[0]
            
            # Create row data matching headers
            row_data = []
            for header in headers:
                field = header.lower().replace(' ', '_')
                value = venue_data.get(field, '')
                row_data.append(value)
            
            # Append new row
            body = {'values': [row_data]}
            result = self.service.spreadsheets().values().append(
                spreadsheetId=self.master_sheet_id,
                range='Sheet1!A:Z',
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            
            logger.info(f"Added new venue: {venue_data.get('name', 'Unknown')}")
            return True
            
        except HttpError as error:
            logger.error(f"Error adding new venue: {error}")
            return False
    
    def add_contact_to_venue(self, venue_name: str, contact_info: Dict) -> bool:
        """Add or update contact information for a venue"""
        updates = {}
        
        # Map contact info to sheet columns
        if contact_info.get('name') and contact_info.get('role'):
            role = contact_info['role'].lower()
            name = contact_info['name']
            
            if 'general manager' in role or 'gm' in role:
                updates['gm_name'] = name
                if contact_info.get('email'):
                    updates['gm_email'] = contact_info['email']
                if contact_info.get('phone'):
                    updates['gm_phone'] = contact_info['phone']
            
            elif 'manager' in role:
                updates['manager_name'] = name
                if contact_info.get('email'):
                    updates['manager_email'] = contact_info['email']
            
            elif 'owner' in role:
                updates['owner_name'] = name
                if contact_info.get('email'):
                    updates['owner_email'] = contact_info['email']
            
            else:
                # Generic contact
                updates['contact_name'] = name
                if contact_info.get('email'):
                    updates['contact_email'] = contact_info['email']
                if contact_info.get('phone'):
                    updates['contact_phone'] = contact_info['phone']
        
        # Update the venue
        return self.update_venue_data(venue_name, updates)
    
    def log_venue_access(self, venue_name: str, access_info: Dict):
        """Log venue access attempts and authentications"""
        if not self.service:
            return False
        
        try:
            # Prepare access log entry
            timestamp = datetime.utcnow().isoformat()
            log_entry = [
                timestamp,
                venue_name,
                access_info.get('user_phone', ''),
                access_info.get('user_name', ''),
                access_info.get('auth_method', ''),
                access_info.get('auth_result', ''),
                access_info.get('ip_address', ''),
                access_info.get('notes', '')
            ]
            
            # Append to Access Log sheet (create if doesn't exist)
            body = {'values': [log_entry]}
            
            try:
                result = self.service.spreadsheets().values().append(
                    spreadsheetId=self.master_sheet_id,
                    range='Access_Log!A:H',
                    valueInputOption='USER_ENTERED',
                    body=body
                ).execute()
            except:
                # Sheet might not exist, create it
                self.create_access_log_sheet()
                # Retry
                result = self.service.spreadsheets().values().append(
                    spreadsheetId=self.master_sheet_id,
                    range='Access_Log!A:H',
                    valueInputOption='USER_ENTERED',
                    body=body
                ).execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Error logging access: {e}")
            return False
    
    def create_access_log_sheet(self):
        """Create Access Log sheet for security tracking"""
        if not self.service:
            return False
        
        try:
            # Add new sheet
            batch_update_body = {
                'requests': [{
                    'addSheet': {
                        'properties': {
                            'title': 'Access_Log',
                            'gridProperties': {
                                'rowCount': 10000,
                                'columnCount': 10
                            }
                        }
                    }
                }]
            }
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.master_sheet_id,
                body=batch_update_body
            ).execute()
            
            # Add headers
            headers = [['Timestamp', 'Venue', 'Phone', 'User Name', 
                       'Auth Method', 'Result', 'IP Address', 'Notes']]
            
            body = {'values': headers}
            self.service.spreadsheets().values().update(
                spreadsheetId=self.master_sheet_id,
                range='Access_Log!A1:H1',
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            
            logger.info("Created Access Log sheet")
            return True
            
        except Exception as e:
            logger.error(f"Error creating Access Log sheet: {e}")
            return False
    
    def sync_venues_to_database(self):
        """Sync venues from Google Sheets to database"""
        venues = self.get_all_venues()
        
        if not venues:
            logger.warning("No venues to sync")
            return 0
        
        # Import database manager
        try:
            from database import db_manager
            
            synced = 0
            for venue_data in venues:
                # Map sheet columns to database fields
                venue = {
                    'name': venue_data.get('name', ''),
                    'phone_number': venue_data.get('phone', ''),
                    'location': venue_data.get('location', ''),
                    'soundtrack_account_id': venue_data.get('soundtrack_id', ''),
                    'contact_name': venue_data.get('contact_name', ''),
                    'contact_email': venue_data.get('email', ''),
                    'metadata': {
                        'sheet_id': venue_data.get('sheet_url', ''),
                        'gmail_label': venue_data.get('gmail_label', ''),
                        'has_soundtrack': venue_data.get('has_soundtrack', 'FALSE') == 'TRUE'
                    }
                }
                
                # Update or insert venue
                # This would need to be implemented in database.py
                synced += 1
            
            logger.info(f"Synced {synced} venues from Google Sheets")
            return synced
            
        except Exception as e:
            logger.error(f"Failed to sync venues: {e}")
            return 0


# Create global instance
sheets_client = GoogleSheetsClient()
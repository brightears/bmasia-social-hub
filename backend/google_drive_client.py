"""
Google Drive integration for BMA Social
Access contracts and technical documentation
"""

import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
import io
import re
from functools import lru_cache

# Google Drive API imports
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaIoBaseDownload
    DRIVE_AVAILABLE = True
except ImportError:
    DRIVE_AVAILABLE = False
    logging.warning("Google Drive API not installed. Run: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")

logger = logging.getLogger(__name__)


class GoogleDriveClient:
    """Manage Google Drive operations for contracts and documentation"""
    
    # Folder IDs for different document types (to be configured)
    CONTRACTS_FOLDER_ID = os.getenv('GDRIVE_CONTRACTS_FOLDER', '')
    TECH_DOCS_FOLDER_ID = os.getenv('GDRIVE_TECH_DOCS_FOLDER', '')
    
    # File type mappings
    CONTRACT_KEYWORDS = ['contract', 'agreement', 'renewal', 'addendum', 'amendment']
    TECH_DOC_KEYWORDS = ['manual', 'guide', 'troubleshooting', 'setup', 'installation', 'specification']
    
    # Cache settings
    CACHE_TTL = 600  # 10 minutes
    MAX_RESULTS = 10
    
    def __init__(self):
        self.service = None
        self.cache = {}
        self.cache_timestamps = {}
        self.connect()
    
    def connect(self):
        """Connect to Google Drive API using service account"""
        if not DRIVE_AVAILABLE:
            logger.error("Google Drive API not available")
            return False
        
        try:
            # Use same credentials as other Google services
            creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
            if creds_json:
                creds_dict = json.loads(creds_json)
                SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
                
                credentials = service_account.Credentials.from_service_account_info(
                    creds_dict, 
                    scopes=SCOPES
                )
                
                self.service = build('drive', 'v3', credentials=credentials)
                logger.info("✅ Google Drive client initialized")
                
                # Test access to folders
                self._verify_folders()
                return True
            else:
                logger.warning("No Google credentials found")
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect to Google Drive: {e}")
            return False
    
    def _verify_folders(self):
        """Verify access to configured folders"""
        folders_to_check = [
            ('Contracts', self.CONTRACTS_FOLDER_ID),
            ('Technical Docs', self.TECH_DOCS_FOLDER_ID)
        ]
        
        for name, folder_id in folders_to_check:
            if folder_id:
                try:
                    # Test folder access
                    self.service.files().get(fileId=folder_id).execute()
                    logger.info(f"✅ Verified access to {name} folder")
                except Exception as e:
                    logger.warning(f"Cannot access {name} folder: {e}")
    
    def search_contracts(self, venue_name: str) -> List[Dict]:
        """
        Search for contracts related to a specific venue
        
        Args:
            venue_name: Name of the venue to search for
            
        Returns:
            List of contract files with metadata
        """
        if not self.service:
            return []
        
        # Check cache
        cache_key = f"contract_{venue_name}"
        if self._is_cached(cache_key):
            return self.cache[cache_key]
        
        try:
            # Clean venue name for search
            search_terms = self._clean_venue_name(venue_name)
            
            # Build search query
            query_parts = []
            
            # Search in contracts folder if configured
            if self.CONTRACTS_FOLDER_ID:
                query_parts.append(f"'{self.CONTRACTS_FOLDER_ID}' in parents")
            
            # Search for venue name in filename or content
            name_queries = []
            for term in search_terms.split():
                if len(term) > 2:  # Skip short words
                    name_queries.append(f"fullText contains '{term}'")
            
            if name_queries:
                query_parts.append(f"({' or '.join(name_queries)})")
            
            # Include contract-related files
            type_queries = []
            for keyword in self.CONTRACT_KEYWORDS:
                type_queries.append(f"name contains '{keyword}'")
            query_parts.append(f"({' or '.join(type_queries)})")
            
            # Exclude trashed files
            query_parts.append("trashed = false")
            
            # Combine all query parts
            query = ' and '.join(query_parts)
            
            # Execute search
            results = self.service.files().list(
                q=query,
                pageSize=self.MAX_RESULTS,
                fields="files(id, name, mimeType, createdTime, modifiedTime, size, webViewLink)",
                orderBy="modifiedTime desc"
            ).execute()
            
            files = results.get('files', [])
            
            # Process results
            processed_files = []
            for file in files:
                processed_files.append({
                    'id': file['id'],
                    'name': file['name'],
                    'type': self._get_file_type(file['mimeType']),
                    'modified': file.get('modifiedTime', ''),
                    'size': file.get('size', 0),
                    'link': file.get('webViewLink', ''),
                    'relevance': self._calculate_relevance(file['name'], venue_name)
                })
            
            # Sort by relevance
            processed_files.sort(key=lambda x: x['relevance'], reverse=True)
            
            # Cache results
            self._cache_results(cache_key, processed_files)
            
            return processed_files
            
        except Exception as e:
            logger.error(f"Failed to search contracts: {e}")
            return []
    
    def search_technical_docs(self, query: str) -> List[Dict]:
        """
        Search for technical documentation
        
        Args:
            query: Search query (e.g., "zone setup", "troubleshooting offline")
            
        Returns:
            List of document files with metadata
        """
        if not self.service:
            return []
        
        # Check cache
        cache_key = f"techdoc_{query}"
        if self._is_cached(cache_key):
            return self.cache[cache_key]
        
        try:
            # Build search query
            query_parts = []
            
            # Search in tech docs folder if configured
            if self.TECH_DOCS_FOLDER_ID:
                query_parts.append(f"'{self.TECH_DOCS_FOLDER_ID}' in parents")
            
            # Search for query terms
            for term in query.split():
                if len(term) > 2:
                    query_parts.append(f"fullText contains '{term}'")
            
            # Exclude trashed files
            query_parts.append("trashed = false")
            
            # Combine query
            drive_query = ' and '.join(query_parts)
            
            # Execute search
            results = self.service.files().list(
                q=drive_query,
                pageSize=self.MAX_RESULTS,
                fields="files(id, name, mimeType, modifiedTime, description, webViewLink)",
                orderBy="modifiedTime desc"
            ).execute()
            
            files = results.get('files', [])
            
            # Process results
            processed_files = []
            for file in files:
                processed_files.append({
                    'id': file['id'],
                    'name': file['name'],
                    'type': self._get_file_type(file['mimeType']),
                    'description': file.get('description', ''),
                    'modified': file.get('modifiedTime', ''),
                    'link': file.get('webViewLink', ''),
                    'relevance': self._calculate_relevance(file['name'], query)
                })
            
            # Sort by relevance
            processed_files.sort(key=lambda x: x['relevance'], reverse=True)
            
            # Cache results
            self._cache_results(cache_key, processed_files)
            
            return processed_files
            
        except Exception as e:
            logger.error(f"Failed to search technical docs: {e}")
            return []
    
    def get_file_summary(self, file_id: str) -> Optional[str]:
        """
        Get a text summary of a file (first page or excerpt)
        For PDFs and docs, extracts key information
        """
        if not self.service:
            return None
        
        try:
            # Get file metadata
            file = self.service.files().get(fileId=file_id).execute()
            mime_type = file.get('mimeType', '')
            
            # For Google Docs, get content as plain text
            if 'google-apps/document' in mime_type:
                content = self.service.files().export(
                    fileId=file_id,
                    mimeType='text/plain'
                ).execute()
                
                # Return first 500 characters
                return content.decode('utf-8')[:500]
            
            # For PDFs and other files, just return metadata
            elif 'pdf' in mime_type:
                return f"PDF Document: {file.get('name', 'Unknown')}\nSize: {file.get('size', 0)} bytes\nNote: Full PDF content extraction not implemented"
            
            else:
                return f"File: {file.get('name', 'Unknown')}\nType: {mime_type}"
                
        except Exception as e:
            logger.error(f"Failed to get file summary: {e}")
            return None
    
    def _clean_venue_name(self, venue_name: str) -> str:
        """Clean venue name for better search results"""
        # Remove common words and clean up
        stop_words = ['the', 'hotel', 'resort', 'at', 'by', 'in']
        
        words = venue_name.lower().split()
        cleaned = []
        
        for word in words:
            if word not in stop_words and len(word) > 2:
                cleaned.append(word)
        
        return ' '.join(cleaned)
    
    def _get_file_type(self, mime_type: str) -> str:
        """Get friendly file type from MIME type"""
        type_map = {
            'application/pdf': 'PDF',
            'application/vnd.google-apps/document': 'Google Doc',
            'application/vnd.google-apps/spreadsheet': 'Google Sheet',
            'application/msword': 'Word',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'Word',
            'image/': 'Image',
            'text/': 'Text'
        }
        
        for key, value in type_map.items():
            if key in mime_type:
                return value
        
        return 'File'
    
    def _calculate_relevance(self, filename: str, search_term: str) -> int:
        """Calculate relevance score for search results"""
        score = 0
        filename_lower = filename.lower()
        search_lower = search_term.lower()
        
        # Exact match
        if search_lower in filename_lower:
            score += 10
        
        # Word matches
        for word in search_lower.split():
            if word in filename_lower:
                score += 5
        
        # Recent files get a small boost
        # (would need to parse date for this)
        
        return score
    
    def _is_cached(self, key: str) -> bool:
        """Check if cache is still valid"""
        if key not in self.cache:
            return False
        
        timestamp = self.cache_timestamps.get(key, 0)
        return (datetime.now().timestamp() - timestamp) < self.CACHE_TTL
    
    def _cache_results(self, key: str, results: List[Dict]):
        """Cache search results"""
        self.cache[key] = results
        self.cache_timestamps[key] = datetime.now().timestamp()
    
    def clear_cache(self):
        """Clear all cached results"""
        self.cache.clear()
        self.cache_timestamps.clear()


# Global instance
drive_client = GoogleDriveClient()


# Helper functions for bot integration
def find_venue_contract(venue_name: str) -> Optional[str]:
    """
    Quick helper to find and summarize a venue's contract
    
    Returns a formatted string with contract information
    """
    if not drive_client.service:
        return None
    
    contracts = drive_client.search_contracts(venue_name)
    
    if not contracts:
        return None
    
    # Get the most relevant contract
    contract = contracts[0]
    
    response = f"📄 Found contract: {contract['name']}\n"
    response += f"Last updated: {contract['modified'][:10]}\n"
    
    # Try to get summary
    summary = drive_client.get_file_summary(contract['id'])
    if summary:
        response += f"\nKey information:\n{summary[:200]}...\n"
    
    response += f"\nView full contract: {contract['link']}"
    
    return response


def find_troubleshooting_guide(issue: str) -> Optional[str]:
    """
    Find relevant technical documentation for an issue
    
    Returns formatted help text
    """
    if not drive_client.service:
        return None
    
    docs = drive_client.search_technical_docs(issue)
    
    if not docs:
        return None
    
    response = "📚 Found these helpful documents:\n\n"
    
    for doc in docs[:3]:  # Top 3 results
        response += f"• {doc['name']}\n"
        if doc.get('description'):
            response += f"  {doc['description'][:50]}...\n"
        response += f"  View: {doc['link']}\n\n"
    
    return response
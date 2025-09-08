"""
Soundtrack Your Brand API Integration
GraphQL-based API client for music control and monitoring
"""

import os
import logging
import json
import base64
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import requests
from requests.auth import HTTPBasicAuth
from venue_accounts import VENUE_ACCOUNTS, find_venue_account

logger = logging.getLogger(__name__)

class SoundtrackAPI:
    """
    Complete Soundtrack Your Brand API integration
    Handles authentication, zone control, and monitoring
    """
    
    def __init__(self):
        self.base_url = os.getenv('SOUNDTRACK_BASE_URL', 'https://api.soundtrackyourbrand.com/v2')
        self.graphql_url = self.base_url  # GraphQL endpoint is at /v2, not /v2/graphql
        
        # Use API credentials from environment
        self.api_credentials = os.getenv('SOUNDTRACK_API_CREDENTIALS')
        self.client_id = os.getenv('SOUNDTRACK_CLIENT_ID')
        self.client_secret = os.getenv('SOUNDTRACK_CLIENT_SECRET')
        
        # Initialize session with authentication
        self.session = requests.Session()
        self._setup_authentication()
        
        # Cache for account data
        self.accounts_cache = {}
        self.zones_cache = {}
        self.cache_expiry = {}
        
        logger.info("Soundtrack API client initialized")
    
    def _setup_authentication(self):
        """Setup authentication headers"""
        import base64
        
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'BMA-Social/2.0'
        })
        
        if self.api_credentials:
            # Use the pre-encoded base64 credentials
            logger.info("Using SOUNDTRACK_API_CREDENTIALS for authentication")
            self.session.headers['Authorization'] = f'Basic {self.api_credentials}'
            
        elif self.client_id and self.client_secret:
            # Encode client credentials to base64
            logger.info("Using SOUNDTRACK_CLIENT_ID and SOUNDTRACK_CLIENT_SECRET for authentication")
            credentials_string = f"{self.client_id}:{self.client_secret}"
            encoded_credentials = base64.b64encode(credentials_string.encode()).decode()
            self.session.headers['Authorization'] = f'Basic {encoded_credentials}'
            
        else:
            logger.error("No Soundtrack API credentials configured!")
            logger.error("Please set either:")
            logger.error("  - SOUNDTRACK_API_CREDENTIALS (base64 encoded)")
            logger.error("  - SOUNDTRACK_CLIENT_ID and SOUNDTRACK_CLIENT_SECRET")
            
        logger.info(f"Soundtrack API URL: {self.graphql_url}")
        logger.info(f"Authentication configured: {'Yes' if 'Authorization' in self.session.headers else 'No'}")
    
    def _execute_query(self, query: str, variables: Dict = None) -> Dict:
        """Execute a GraphQL query"""
        
        # Check if authentication is configured
        if 'Authorization' not in self.session.headers:
            logger.error("Cannot execute query: No authentication credentials configured")
            return {'error': 'No authentication credentials configured'}
        
        try:
            payload = {
                'query': query,
                'variables': variables or {}
            }
            
            logger.debug(f"Sending GraphQL query to {self.graphql_url}")
            logger.debug(f"Query: {query[:200]}...")  # First 200 chars
            
            response = self.session.post(self.graphql_url, json=payload, timeout=10)
            
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")
            
            if response.status_code != 200:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"API request failed: {error_msg}")
                return {'error': error_msg}
            
            data = response.json()
            logger.debug(f"Response data keys: {list(data.keys())}")
            
            if 'errors' in data:
                logger.error(f"GraphQL errors: {data['errors']}")
                return {'error': data['errors']}
            
            return data.get('data', {})
            
        except requests.exceptions.Timeout:
            error_msg = "API request timed out after 10 seconds"
            logger.error(error_msg)
            return {'error': error_msg}
            
        except requests.exceptions.ConnectionError:
            error_msg = "Cannot connect to Soundtrack API"
            logger.error(error_msg)
            return {'error': error_msg}
            
        except requests.exceptions.RequestException as e:
            error_msg = f"API request failed: {e}"
            logger.error(error_msg)
            return {'error': error_msg}
            
        except json.JSONDecodeError:
            error_msg = "Invalid JSON response from API"
            logger.error(error_msg)
            return {'error': error_msg}
    
    def get_accounts(self, force_refresh: bool = False) -> List[Dict]:
        """Get all accessible accounts"""
        
        # Check cache
        if not force_refresh and 'accounts' in self.accounts_cache:
            if self.cache_expiry.get('accounts', datetime.min) > datetime.now():
                return self.accounts_cache['accounts']
        
        query = """
        query GetAccounts {
            me {
                ... on PublicAPIClient {
                    id
                    accounts(first: 50) {
                        edges {
                            node {
                                id
                                businessName
                                locations(first: 50) {
                                    edges {
                                        node {
                                            id
                                            name
                                            address
                                            soundZones(first: 50) {
                                                edges {
                                                    node {
                                                        id
                                                        name
                                                        isPaired
                                                        online
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        
        result = self._execute_query(query)
        
        if 'error' in result:
            return []
        
        # Extract accounts from the me.accounts structure
        accounts = []
        me_data = result.get('me', {})
        if me_data and 'accounts' in me_data:
            for edge in me_data['accounts'].get('edges', []):
                account = edge['node']
                # Normalize field names for backward compatibility
                if 'businessName' in account:
                    account['name'] = account['businessName']
                accounts.append(account)
        
        # Cache results
        self.accounts_cache['accounts'] = accounts
        self.cache_expiry['accounts'] = datetime.now() + timedelta(minutes=5)
        
        return accounts
    
    def get_account_by_id(self, account_id: str) -> Dict:
        """Get specific account data by its ID"""
        
        query = """
        query GetAccount($id: ID!) {
            account(id: $id) {
                id
                businessName
                locations(first: 50) {
                    edges {
                        node {
                            id
                            name
                            soundZones(first: 50) {
                                edges {
                                    node {
                                        id
                                        name
                                        isPaired
                                        online
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        
        result = self._execute_query(query, {'id': account_id})
        
        if 'error' in result:
            return None
        
        return result.get('account')
    
    def get_zones_by_account(self, account_id: str) -> List[Dict]:
        """Get all zones for a specific account ID"""
        zones = []
        
        try:
            account_data = self.get_account_by_id(account_id)
            
            if account_data:
                for loc_edge in account_data.get('locations', {}).get('edges', []):
                    location = loc_edge['node']
                    for zone_edge in location.get('soundZones', {}).get('edges', []):
                        zone = zone_edge['node']
                        zone['location_name'] = location.get('name')
                        zone['displayName'] = zone.get('name', '')  # Add displayName for compatibility
                        zones.append(zone)
            
        except Exception as e:
            logger.error(f"Failed to get zones for account {account_id}: {e}")
        
        return zones
    
    def find_venue_zones(self, venue_name: str) -> List[Dict]:
        """Find all zones for a specific venue with fuzzy matching"""
        zones = []
        
        # First check if it's a known venue with direct account ID
        venue_account = find_venue_account(venue_name)
        if venue_account:
            logger.info(f"Found known venue: {venue_account['name']}")
            account_data = self.get_account_by_id(venue_account['account_id'])
            
            if account_data:
                for loc_edge in account_data.get('locations', {}).get('edges', []):
                    location = loc_edge['node']
                    for zone_edge in location.get('soundZones', {}).get('edges', []):
                        zone = zone_edge['node']
                        zone['location_name'] = location.get('name')
                        zone['account_name'] = account_data.get('businessName')
                        zone['match_score'] = 3  # Highest score for exact match
                        # Normalize field names for consistency
                        if 'online' in zone:
                            zone['isOnline'] = zone['online']
                        zones.append(zone)
                
                return zones
        
        # Fall back to searching through accessible accounts
        accounts = self.get_accounts()
        
        # Clean search term
        search_terms = venue_name.lower().split()
        
        for account in accounts:
            account_name = account.get('name', '').lower()
            match_score = 0
            
            # Check if all search terms are in account name
            if all(term in account_name for term in search_terms):
                match_score = 2  # High score for all terms matching
            # Check if any important term matches
            elif any(term in account_name for term in search_terms if len(term) > 3):
                match_score = 1  # Lower score for partial match
            
            # Also check location names
            for loc_edge in account.get('locations', {}).get('edges', []):
                location = loc_edge['node']
                location_name = location.get('name', '').lower()
                
                loc_match_score = 0
                if all(term in location_name for term in search_terms):
                    loc_match_score = 2
                elif any(term in location_name for term in search_terms if len(term) > 3):
                    loc_match_score = 1
                
                # If either account or location matches, include zones
                if match_score > 0 or loc_match_score > 0:
                    for zone_edge in location.get('soundZones', {}).get('edges', []):
                        zone = zone_edge['node']
                        zone['location_name'] = location.get('name')
                        zone['account_name'] = account.get('name')
                        zone['match_score'] = max(match_score, loc_match_score)
                        # Normalize field names for consistency
                        if 'online' in zone:
                            zone['isOnline'] = zone['online']
                        zones.append(zone)
        
        # Sort by match score (best matches first)
        zones.sort(key=lambda x: x.get('match_score', 0), reverse=True)
        
        return zones
    
    def find_matching_accounts(self, venue_name: str) -> List[Dict]:
        """Find all accounts that might match the venue name"""
        accounts = self.get_accounts()
        matches = []
        
        # Clean search term
        search_terms = venue_name.lower().split()
        
        for account in accounts:
            account_name = account.get('name', '').lower()
            
            # Calculate match score
            match_score = 0
            matched_terms = []
            
            for term in search_terms:
                if term in account_name and len(term) > 2:
                    match_score += 1
                    matched_terms.append(term)
            
            # Special handling for common venue names
            if 'hilton' in search_terms and 'hilton' in account_name:
                match_score += 2  # Boost for brand match
            
            if match_score > 0:
                # Count total zones
                total_zones = 0
                online_zones = 0
                for loc_edge in account.get('locations', {}).get('edges', []):
                    location = loc_edge['node']
                    for zone_edge in location.get('soundZones', {}).get('edges', []):
                        total_zones += 1
                        zone_node = zone_edge['node']
                        if zone_node.get('isOnline') or zone_node.get('online'):
                            online_zones += 1
                
                matches.append({
                    'account_id': account.get('id'),
                    'account_name': account.get('name'),
                    'match_score': match_score,
                    'matched_terms': matched_terms,
                    'total_zones': total_zones,
                    'online_zones': online_zones
                })
        
        # Sort by match score
        matches.sort(key=lambda x: x['match_score'], reverse=True)
        
        return matches
    
    def get_zone_status(self, zone_id: str) -> Dict:
        """Get detailed status for a specific zone including playing status and current track"""
        
        # CORRECTED query based on API testing - volume field does NOT exist
        query = """
        query GetZoneStatus($zoneId: ID!) {
            soundZone(id: $zoneId) {
                id
                name
                online
                isPaired
                streamingType
                device {
                    id
                    name
                }
                nowPlaying {
                    track {
                        name
                        artists {
                            name
                        }
                        album {
                            name
                        }
                    }
                }
                playFrom {
                    __typename
                    ... on Playlist {
                        id
                        name
                    }
                    ... on Schedule {
                        id
                        name
                    }
                }
                playback {
                    state
                }
            }
        }
        """
        
        result = self._execute_query(query, {'zoneId': zone_id})
        
        # Check for GraphQL errors first
        if 'error' in result:
            logger.error(f"GraphQL error getting zone status for {zone_id}: {result['error']}")
            return {'error': result['error']}
        
        zone_data = result.get('soundZone', {})
        
        # Process the response to extract useful information
        if zone_data:
            status = {
                'id': zone_data.get('id'),
                'name': zone_data.get('name'),
                'device_name': zone_data.get('device', {}).get('name'),
                'device_online': zone_data.get('online'),
                'streaming_type': zone_data.get('streamingType'),
                'is_paired': zone_data.get('isPaired'),
                'volume': None  # Volume field does NOT exist in API - confirmed by testing
            }
            
            # Extract playback state - this is the reliable way to check if playing
            playback = zone_data.get('playback', {})
            if playback:
                playback_state = playback.get('state', '').lower()
                status['playing'] = playback_state == 'playing'
                status['playback_state'] = playback_state
            else:
                status['playing'] = False
                status['playback_state'] = 'unknown'
            
            # Extract now playing information (updated structure)
            now_playing = zone_data.get('nowPlaying', {})
            if now_playing:
                track = now_playing.get('track', {})
                if track:
                    # Get first artist name
                    artists = track.get('artists', [])
                    artist_name = artists[0].get('name', 'Unknown artist') if artists else 'Unknown artist'
                    
                    album = track.get('album', {})
                    album_name = album.get('name', '') if album else ''
                    
                    status['current_track'] = {
                        'name': track.get('name', 'Unknown track'),
                        'artist': artist_name,
                        'album': album_name
                    }
                
            # Extract playlist/schedule info from playFrom (not nowPlaying.playFrom)
            play_from = zone_data.get('playFrom', {})
            if play_from:
                status['current_playlist'] = play_from.get('name')
                status['current_source_type'] = play_from.get('__typename')
            
            return status
        
        return {'error': 'Zone not found'}
    
    def control_playback(self, zone_id: str, action: str) -> Dict:
        """Control playback - cloud-level control confirmed working"""
        
        # CORRECTED mutations based on successful volume control pattern
        mutations = {
            'play': """
                mutation PlayZone($input: PlayInput!) {
                    play(input: $input) {
                        __typename
                    }
                }
            """,
            'pause': """
                mutation PauseZone($input: PauseInput!) {
                    pause(input: $input) {
                        __typename
                    }
                }
            """,
            'skip': """
                mutation SkipTrack($input: SkipTrackInput!) {
                    skipTrack(input: $input) {
                        __typename
                    }
                }
            """
        }
        
        if action not in mutations:
            logger.error(f"Invalid playback action: {action}")
            return {'success': False, 'error': 'Invalid action', 'error_type': 'invalid_action'}
        
        result = self._execute_query(mutations[action], {
            'input': {
                'soundZone': zone_id
            }
        })
        
        if 'error' in result:
            error_msg = str(result['error'])
            logger.error(f"Playback control failed for {action}: {error_msg}")
            
            # Categorize errors properly
            if 'Not found' in error_msg or 'does not exist' in error_msg:
                return {
                    'success': False, 
                    'error': 'Zone not controllable (trial/demo zone or insufficient permissions)',
                    'error_type': 'no_api_control',
                    'raw_error': error_msg
                }
            elif 'Unauthorized' in error_msg or 'Forbidden' in error_msg:
                return {
                    'success': False,
                    'error': 'Authentication or permission error',
                    'error_type': 'auth_error',
                    'raw_error': error_msg
                }
            else:
                return {
                    'success': False,
                    'error': f'API error: {error_msg}',
                    'error_type': 'api_error',
                    'raw_error': error_msg
                }
        
        # Success - volume control pattern confirmed this works
        return {'success': True, 'action': action}
    
    def set_volume(self, zone_id: str, volume: int) -> Dict:
        """Set volume for a zone (0-16 scale) - CONFIRMED WORKING via API testing"""
        
        if not 0 <= volume <= 16:
            logger.error(f"Invalid volume: {volume} (must be 0-16)")
            return {'success': False, 'error': 'Volume must be between 0 and 16', 'error_type': 'invalid_parameter'}
        
        # CORRECTED mutation - confirmed working via API testing
        query = """
        mutation SetVolume($input: SetVolumeInput!) {
            setVolume(input: $input) {
                __typename
            }
        }
        """
        
        result = self._execute_query(query, {
            'input': {
                'soundZone': zone_id,
                'volume': volume
            }
        })
        
        if 'error' in result:
            error_msg = str(result['error'])
            logger.error(f"Volume control failed: {error_msg}")
            
            # Categorize errors properly  
            if 'Not found' in error_msg or 'does not exist' in error_msg:
                return {
                    'success': False, 
                    'error': 'Zone not controllable (trial/demo zone or insufficient permissions)',
                    'error_type': 'no_api_control',
                    'raw_error': error_msg
                }
            elif 'Unauthorized' in error_msg or 'Forbidden' in error_msg:
                return {
                    'success': False,
                    'error': 'Authentication or permission error',
                    'error_type': 'auth_error', 
                    'raw_error': error_msg
                }
            else:
                return {
                    'success': False,
                    'error': f'API error: {error_msg}',
                    'error_type': 'api_error',
                    'raw_error': error_msg
                }
        
        # Success - confirmed via API testing
        return {'success': True, 'volume': volume}
    
    def play_zone(self, zone_id: str) -> bool:
        """Convenience method to play a zone"""
        result = self.control_playback(zone_id, 'play')
        return result.get('success', False)
    
    def pause_zone(self, zone_id: str) -> bool:
        """Convenience method to pause a zone"""
        result = self.control_playback(zone_id, 'pause')
        return result.get('success', False)
    
    def skip_track(self, zone_id: str) -> bool:
        """Convenience method to skip current track"""
        result = self.control_playback(zone_id, 'skip')
        return result.get('success', False)
    
    def set_playlist(self, zone_id: str, playlist_id: str) -> Dict:
        """Set playlist for a zone - works with both account-specific and curated playlists"""
        
        logger.info(f"=== SET_PLAYLIST API CALLED ===")
        logger.info(f"Zone ID: {zone_id}")
        logger.info(f"Playlist ID: {playlist_id}")
        
        # Skip capability check - just try to set the playlist directly
        # The capability check was changing volume which is disruptive
        
        # CORRECTED: Using the REAL mutation that actually exists
        query = """
        mutation SetPlayFrom($input: SetPlayFromInput!) {
            setPlayFrom(input: $input) {
                __typename
            }
        }
        """
        
        logger.info(f"Attempting to set zone source using setPlayFrom mutation")
        
        result = self._execute_query(query, {
            'input': {
                'soundZone': zone_id,
                'source': playlist_id  # Changed from 'playlist' to 'source'
            }
        })
        
        if 'error' in result:
            error_msg = str(result['error'])
            
            if 'Not found' in error_msg:
                return {
                    'success': False,
                    'error': 'Zone not controllable or playlist not found',
                    'error_type': 'no_api_control',
                    'raw_error': error_msg,
                    'zone_name': capabilities.get('zone_name', 'Unknown')
                }
            elif 'Type of variable' in error_msg:
                return {
                    'success': False,
                    'error': 'Invalid playlist type for this zone',
                    'error_type': 'incompatible_playlist',
                    'raw_error': error_msg,
                    'zone_name': capabilities.get('zone_name', 'Unknown'),
                    'suggestions': [
                        'This may be a curated playlist that requires account-specific playlists',
                        'Try using playlists from your account\'s library instead',
                        'Contact venue staff to change playlist manually'
                    ]
                }
            else:
                return {
                    'success': False,
                    'error': f'API error: {error_msg}',
                    'error_type': 'api_error',
                    'raw_error': error_msg,
                    'zone_name': capabilities.get('zone_name', 'Unknown')
                }
        
        return {
            'success': True, 
            'message': 'Playlist changed successfully',
            'zone_name': capabilities.get('zone_name', 'Unknown'),
            'playlist_id': playlist_id
        }
    
    def suggest_playlists_for_request(self, user_request: str, zone_id: str = None) -> Dict:
        """Comprehensive playlist suggestion system with assignment capability"""
        
        # Find relevant playlists
        playlists = self.find_playlists_by_context(user_request, limit=5)
        
        response = {
            'user_request': user_request,
            'playlists_found': len(playlists),
            'playlists': playlists,
            'can_assign': False,
            'zone_controllable': False
        }
        
        # If zone_id provided, check if we can assign playlists
        if zone_id:
            capabilities = self.get_zone_capabilities(zone_id)
            response['zone_name'] = capabilities.get('zone_name', 'Unknown')
            response['zone_controllable'] = capabilities.get('controllable', False)
            response['can_assign'] = response['zone_controllable']
            
            if not response['zone_controllable']:
                response['control_limitation'] = capabilities.get('control_failure_reason', 'unknown')
                response['manual_instructions'] = [
                    'Use Soundtrack Your Brand mobile app or web dashboard',
                    'Access Settings > Music > Playlists',
                    'Search for the suggested playlist names',
                    'Apply to your zone manually'
                ]
        
        # Add assignment recommendations for each playlist
        for playlist in playlists:
            playlist['assignment_status'] = 'available_for_assignment' if response['can_assign'] else 'manual_assignment_required'
            
            if not response['can_assign']:
                playlist['manual_search_hint'] = f"Search for '{playlist['name']}' in SYB dashboard"
        
        return response
    
    def get_playlists(self, zone_id: str) -> List[Dict]:
        """Get available playlists for a zone's account (DEPRECATED - account playlists not accessible via API)"""
        logger.warning("get_playlists() is deprecated - account playlists field does not exist in GraphQL schema")
        logger.info("Use search_curated_playlists() instead to access Soundtrack's playlist library")
        return []
    
    def search_curated_playlists(self, search_term: str, limit: int = 10) -> List[Dict]:
        """Search Soundtrack's curated playlist library"""
        
        logger.info(f"=== SEARCHING CURATED PLAYLISTS ===")
        logger.info(f"Search term: '{search_term}', Limit: {limit}")
        
        query = """
        query SearchPlaylists($searchTerm: String!, $limit: Int!) {
            search(query: $searchTerm, type: playlist, first: $limit) {
                edges {
                    node {
                        ... on Playlist {
                            id
                            name
                            description
                        }
                    }
                }
            }
        }
        """
        
        result = self._execute_query(query, {
            'searchTerm': search_term,
            'limit': limit
        })
        
        if 'error' in result:
            logger.error(f"Error searching playlists: {result['error']}")
            return []
        
        try:
            playlists = []
            edges = result.get('search', {}).get('edges', [])
            logger.info(f"Found {len(edges)} playlists matching '{search_term}'")
            
            for edge in edges:
                node = edge.get('node', {})
                if node.get('__typename') == 'Playlist' or 'description' in node:
                    playlists.append({
                        'id': node.get('id'),
                        'name': node.get('name'),
                        'description': node.get('description', ''),
                        'source': 'curated_library',
                        'search_term': search_term
                    })
            
            logger.info(f"Found {len(playlists)} curated playlists for '{search_term}'")
            return playlists
            
        except Exception as e:
            logger.error(f"Error parsing search results: {e}")
            return []
    
    def find_playlists_by_context(self, user_request: str, limit: int = 5) -> List[Dict]:
        """Intelligently find playlists based on user conversation context"""
        
        # Map common user requests to search terms
        context_mapping = {
            # Decades/Eras
            '80s': ['80s', 'eighties', '1980s'], 
            '90s': ['90s', 'nineties', '1990s'],
            '70s': ['70s', 'seventies', '1970s'],
            '60s': ['60s', 'sixties', '1960s'],
            '2000s': ['2000s', 'two thousands'],
            
            # Genres
            'rock': ['rock', 'rock music'],
            'pop': ['pop', 'pop music'],
            'jazz': ['jazz', 'jazz music'],
            'classical': ['classical', 'classical music'],
            'electronic': ['electronic', 'edm', 'dance'],
            'hip hop': ['hip hop', 'rap'],
            'country': ['country', 'country music'],
            'blues': ['blues'],
            'reggae': ['reggae'],
            'latin': ['latin', 'latin music'],
            
            # Moods/Atmospheres  
            'chill': ['chill', 'relaxing', 'calm'],
            'upbeat': ['upbeat', 'energetic', 'lively'],
            'relaxing': ['relaxing', 'peaceful', 'calm'],
            'party': ['party', 'dance', 'celebration'],
            'romantic': ['romantic', 'love songs'],
            'background': ['background', 'ambient'],
            
            # Contexts
            'restaurant': ['restaurant', 'dining', 'dinner'],
            'lobby': ['lobby', 'hotel lobby', 'lounge'],
            'cafe': ['cafe', 'coffee shop'],
            'workout': ['workout', 'gym', 'fitness'],
        }
        
        user_request_lower = user_request.lower()
        search_terms = []
        
        # Find matching context terms
        for context, terms in context_mapping.items():
            if any(term in user_request_lower for term in terms):
                search_terms.append(context)
        
        # If no specific context found, extract key words
        if not search_terms:
            words = user_request_lower.split()
            potential_terms = []
            
            for word in words:
                if len(word) > 3 and word not in ['play', 'some', 'music', 'song', 'songs', 'track', 'tracks']:
                    potential_terms.append(word)
            
            search_terms = potential_terms[:2]  # Use first 2 meaningful words
        
        # Search for playlists
        all_playlists = []
        
        for term in search_terms[:3]:  # Limit to 3 search terms
            playlists = self.search_curated_playlists(term, limit=limit)
            
            # Add relevance score based on term match
            for playlist in playlists:
                playlist['relevance_score'] = 1.0
                playlist['matched_term'] = term
                
                # Boost score if playlist name closely matches user request
                playlist_name_lower = playlist['name'].lower()
                if term in playlist_name_lower:
                    playlist['relevance_score'] += 0.5
                
                # Boost for exact matches in description
                if playlist['description'] and term in playlist['description'].lower():
                    playlist['relevance_score'] += 0.3
            
            all_playlists.extend(playlists)
        
        # Remove duplicates and sort by relevance
        unique_playlists = {}
        for playlist in all_playlists:
            playlist_id = playlist['id']
            if playlist_id not in unique_playlists or playlist['relevance_score'] > unique_playlists[playlist_id]['relevance_score']:
                unique_playlists[playlist_id] = playlist
        
        sorted_playlists = sorted(unique_playlists.values(), key=lambda x: x['relevance_score'], reverse=True)
        
        logger.info(f"Found {len(sorted_playlists)} relevant playlists for request: '{user_request}'")
        
        return sorted_playlists[:limit]
    
    def get_now_playing(self, zone_id: str) -> Dict:
        """Get current playing track information (limited availability)"""
        
        query = """
        query NowPlaying($zoneId: ID!) {
            soundZone(id: $zoneId) {
                id
                name
                nowPlaying {
                    __typename
                }
            }
        }
        """
        
        result = self._execute_query(query, {'zoneId': zone_id})
        
        if 'error' in result:
            return {'error': result['error']}
        
        sound_zone = result.get('soundZone', {})
        now_playing = sound_zone.get('nowPlaying')
        
        if now_playing:
            return {
                'has_playback': True,
                'type': now_playing.get('__typename', 'Unknown'),
                'zone_name': sound_zone.get('name')
            }
        else:
            return {
                'has_playback': False,
                'zone_name': sound_zone.get('name')
            }
    
    def diagnose_venue_issues(self, venue_name: str) -> Dict:
        """Comprehensive diagnosis of venue music issues"""
        
        zones = self.find_venue_zones(venue_name)
        
        if not zones:
            return {
                'status': 'error',
                'message': f'No zones found for venue: {venue_name}',
                'zones': []
            }
        
        diagnosis = {
            'venue': venue_name,
            'total_zones': len(zones),
            'online_zones': 0,
            'offline_zones': 0,
            'playing_zones': 0,
            'paused_zones': 0,
            'zones': []
        }
        
        for zone in zones:
            is_online = zone.get('isOnline') or zone.get('online', False)
            zone_status = {
                'name': zone.get('name'),
                'location': zone.get('location_name'),
                'is_online': is_online,
                'is_paired': zone.get('isPaired', False),
                'issues': []
            }
            
            # Check for issues
            if not zone.get('isPaired'):
                zone_status['issues'].append('Device not paired')
            
            if not is_online:
                zone_status['issues'].append('Device offline')
                diagnosis['offline_zones'] += 1
            else:
                diagnosis['online_zones'] += 1
                
                # Check playback status using updated logic
                zone_status = self.get_zone_status(zone.get('id'))
                is_playing = zone_status.get('playing', False) if 'error' not in zone_status else False
                
                if is_playing:
                    diagnosis['playing_zones'] += 1
                    current_track = zone_status.get('current_track')
                    if current_track:
                        zone_status['currently_playing'] = current_track.get('name')
                else:
                    diagnosis['paused_zones'] += 1
                    zone_status['issues'].append('Music paused or stopped')
            
            diagnosis['zones'].append(zone_status)
        
        # Overall status
        if diagnosis['offline_zones'] == len(zones):
            diagnosis['status'] = 'critical'
            diagnosis['message'] = 'All zones are offline'
        elif diagnosis['offline_zones'] > 0:
            diagnosis['status'] = 'warning'
            diagnosis['message'] = f"{diagnosis['offline_zones']} zones offline"
        elif diagnosis['playing_zones'] == 0:
            diagnosis['status'] = 'warning'
            diagnosis['message'] = 'No zones are playing music'
        else:
            diagnosis['status'] = 'ok'
            diagnosis['message'] = f"{diagnosis['playing_zones']} zones playing normally"
        
        return diagnosis
    
    def detect_zone_mode(self, zone_id: str) -> str:
        """Detect if zone is in scheduled or manual mode"""
        
        status = self.get_zone_status(zone_id)
        
        if 'error' in status:
            return 'unknown'
        
        schedule = status.get('schedule')
        if schedule and schedule.get('name'):
            return 'scheduled'
        else:
            return 'manual'
    
    def get_zone_capabilities(self, zone_id: str) -> Dict:
        """Test zone capabilities - ALWAYS try control first regardless of device type"""
        
        status = self.get_zone_status(zone_id)
        
        if 'error' in status:
            return {
                'error': status['error'],
                'controllable': False,
                'readable': False
            }
        
        capabilities = {
            'readable': True,
            'basic_info': True,
            'device_info': bool(status.get('device')),
            'schedule_detection': bool(status.get('schedule')),
            'playback_detection': bool(status.get('nowPlaying')),
            'streaming_type': status.get('streamingType'),
            'zone_name': status.get('name'),
            'device_name': status.get('device', {}).get('name'),
            'mode': self.detect_zone_mode(zone_id)
        }
        
        logger.info(f"Testing capabilities for {capabilities['zone_name']} - Device: {capabilities['device_name']}, StreamingType: {capabilities['streaming_type']}")
        
        # Test control capabilities - CRITICAL: Control is cloud-level, not device-dependent
        
        # Test volume control (safest test)
        volume_test = self.set_volume(zone_id, 8)  # Middle of 0-16 range
        capabilities['volume_control'] = volume_test.get('success', False)
        capabilities['volume_error_type'] = volume_test.get('error_type')
        
        # Test playback control 
        play_test = self.control_playback(zone_id, 'play')
        capabilities['playback_control'] = play_test.get('success', False)
        capabilities['playback_error_type'] = play_test.get('error_type')
        
        # Determine overall controllability
        capabilities['controllable'] = capabilities['volume_control'] or capabilities['playback_control']
        
        # Analyze control failure reasons
        if not capabilities['controllable']:
            error_types = {capabilities.get('volume_error_type'), capabilities.get('playback_error_type')}
            error_types.discard(None)
            
            if 'no_api_control' in error_types:
                capabilities['control_failure_reason'] = 'trial_or_demo_zone'
                capabilities['control_failure_message'] = 'Zone appears to be trial/demo or lacks API control permissions'
            elif 'auth_error' in error_types:
                capabilities['control_failure_reason'] = 'authentication_error'
                capabilities['control_failure_message'] = 'Authentication or permission issue'
            else:
                capabilities['control_failure_reason'] = 'unknown'
                capabilities['control_failure_message'] = 'Unable to determine why control failed'
        
        return capabilities
    
    def create_music_change_request(self, zone_info: Dict, request: str) -> Dict:
        """Create a structured request for manual music changes"""
        
        zone_id = zone_info.get('id')
        capabilities = self.get_zone_capabilities(zone_id) if zone_id else {}
        
        request_data = {
            'timestamp': datetime.now().isoformat(),
            'venue_info': {
                'account_name': zone_info.get('account_name'),
                'location_name': zone_info.get('location_name'),
                'zone_name': zone_info.get('name')
            },
            'technical_info': {
                'zone_id': zone_id,
                'device_name': capabilities.get('device_name'),
                'streaming_type': capabilities.get('streaming_type'),
                'current_mode': capabilities.get('mode'),
                'controllable_via_api': capabilities.get('controllable', False)
            },
            'request_details': {
                'description': request,
                'urgency': 'normal',
                'requires_manual_intervention': not capabilities.get('controllable', False)
            }
        }
        
        return request_data
    
    def queue_tracks(self, zone_id: str, track_ids: List[str]) -> Dict:
        """Queue tracks to a sound zone (NEW capability discovered)"""
        
        if not track_ids:
            return {'success': False, 'error': 'No track IDs provided'}
        
        query = """
        mutation QueueTracks($input: SoundZoneQueueTracksInput!) {
            soundZoneQueueTracks(input: $input) {
                __typename
            }
        }
        """
        
        result = self._execute_query(query, {
            'input': {
                'soundZone': zone_id,
                'tracks': track_ids
            }
        })
        
        if 'error' in result:
            return {'success': False, 'error': result['error']}
        
        return {'success': True}
    
    def clear_queue(self, zone_id: str) -> Dict:
        """Clear all queued tracks for a sound zone (NEW capability discovered)"""
        
        query = """
        mutation ClearQueue($input: SoundZoneClearQueuedTracksInput!) {
            soundZoneClearQueuedTracks(input: $input) {
                __typename
            }
        }
        """
        
        result = self._execute_query(query, {
            'input': {
                'soundZone': zone_id
            }
        })
        
        if 'error' in result:
            return {'success': False, 'error': result['error']}
        
        return {'success': True}
    
    def get_enhanced_zone_status(self, zone_id: str) -> Dict:
        """Get enhanced zone status including current source details"""
        
        query = """
        query GetEnhancedZoneStatus($zoneId: ID!) {
            soundZone(id: $zoneId) {
                id
                name
                streamingType
                device {
                    id
                    name
                }
                schedule {
                    id
                    name
                }
                playFrom {
                    __typename
                    ... on Schedule {
                        id
                        name
                    }
                    ... on Playlist {
                        id
                        name
                    }
                }
                nowPlaying {
                    __typename
                }
            }
        }
        """
        
        result = self._execute_query(query, {'zoneId': zone_id})
        
        if 'error' in result:
            return {'error': result['error']}
        
        return result.get('soundZone', {})
    
    def quick_fix_zone(self, zone_id: str) -> Dict:
        """Attempt to fix common zone issues - ALWAYS try control first regardless of device type"""
        
        fixes_attempted = []
        status = self.get_zone_status(zone_id)
        
        if 'error' in status:
            return {
                'success': False,
                'message': 'Could not get zone status',
                'error': status['error']
            }
        
        zone_name = status.get('name', 'Unknown Zone')
        device_name = status.get('device', {}).get('name', 'Unknown Device')
        mode = self.detect_zone_mode(zone_id)
        streaming_type = status.get('streamingType', 'Unknown')
        
        # CRITICAL: Always try control first - control happens at SYB cloud level, NOT device level
        logger.info(f"Attempting control for zone '{zone_name}' - Device: {device_name}, StreamingType: {streaming_type}")
        
        # Try volume adjustment first (safest test)
        volume_result = self.set_volume(zone_id, 8)
        if volume_result.get('success'):
            fixes_attempted.append('Successfully adjusted volume to moderate level')
        else:
            fixes_attempted.append(f"Volume control failed: {volume_result.get('error')}")
        
        # Try play command
        play_result = self.control_playback(zone_id, 'play')
        if play_result.get('success'):
            fixes_attempted.append('Successfully sent play command')
        else:
            fixes_attempted.append(f"Play control failed: {play_result.get('error')}")
        
        success = any('Successfully' in fix for fix in fixes_attempted)
        
        # Analyze WHY control failed (if it did)
        failure_reason = None
        if not success:
            common_errors = [fix for fix in fixes_attempted if 'failed:' in fix]
            if common_errors:
                error_text = common_errors[0].split('failed: ')[-1]
                if 'trial/demo zone or insufficient permissions' in error_text:
                    failure_reason = 'trial_or_demo_zone'
                elif 'Not found' in error_text:
                    failure_reason = 'api_control_not_available'
                else:
                    failure_reason = 'unknown_error'
        
        result = {
            'success': success,
            'zone_info': {
                'name': zone_name,
                'device': device_name,
                'mode': mode,
                'streaming_type': streaming_type
            },
            'fixes_attempted': fixes_attempted,
            'requires_manual_intervention': not success
        }
        
        # Add appropriate recommendations based on actual failure reason
        if not success:
            if failure_reason == 'trial_or_demo_zone':
                result['message'] = f'Zone "{zone_name}" appears to be a trial/demo zone or lacks API control permissions'
                result['recommendations'] = [
                    'Check if this is a trial/demo account that needs upgrading',
                    'Verify API control permissions are enabled for this zone',
                    'Contact venue staff to use SYB app/dashboard directly',
                    'Consider upgrading subscription if needed'
                ]
            elif failure_reason == 'api_control_not_available':
                result['message'] = f'Zone "{zone_name}" does not support remote API control'
                result['recommendations'] = [
                    'Use SYB mobile app or web dashboard for manual control',
                    'Contact venue staff directly',
                    'Check zone settings in SYB dashboard'
                ]
            else:
                result['message'] = f'Could not control zone "{zone_name}" - reason unclear'
                result['recommendations'] = [
                    'Try controlling via SYB app/dashboard',
                    'Contact venue staff',
                    'Check zone connectivity and status'
                ]
        else:
            result['message'] = f'Successfully applied fixes to zone "{zone_name}"'
        
        return result


# Global instance
soundtrack_api = SoundtrackAPI()
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
                                                        nowPlaying {
                                                            track {
                                                                name
                                                                artists
                                                            }
                                                            playback {
                                                                isPlaying
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
    
    def find_venue_zones(self, venue_name: str) -> List[Dict]:
        """Find all zones for a specific venue with fuzzy matching"""
        accounts = self.get_accounts()
        zones = []
        
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
        """Get detailed status for a specific zone"""
        
        query = """
        query GetZoneStatus($zoneId: ID!) {
            soundZone(id: $zoneId) {
                id
                name
                isPaired
                isOnline
                volume
                nowPlaying {
                    track {
                        id
                        name
                        artists
                        album
                        duration
                    }
                    isPlaying
                    position
                    startedAt
                }
                currentPlaylist {
                    id
                    name
                    trackCount
                }
                device {
                    id
                    name
                    model
                    firmwareVersion
                    lastSeen
                }
            }
        }
        """
        
        result = self._execute_query(query, {'zoneId': zone_id})
        
        if 'error' in result:
            return {'error': result['error']}
        
        return result.get('soundZone', {})
    
    def control_playback(self, zone_id: str, action: str) -> bool:
        """Control playback (play/pause/skip)"""
        
        mutations = {
            'play': """
                mutation PlayZone($zoneId: ID!) {
                    play(soundZone: $zoneId) {
                        success
                    }
                }
            """,
            'pause': """
                mutation PauseZone($zoneId: ID!) {
                    pause(soundZone: $zoneId) {
                        success
                    }
                }
            """,
            'skip': """
                mutation SkipTrack($zoneId: ID!) {
                    skip(soundZone: $zoneId) {
                        success
                    }
                }
            """
        }
        
        if action not in mutations:
            logger.error(f"Invalid playback action: {action}")
            return False
        
        result = self._execute_query(mutations[action], {'zoneId': zone_id})
        
        if 'error' in result:
            return False
        
        return True
    
    def set_volume(self, zone_id: str, volume: int) -> bool:
        """Set volume for a zone (0-100)"""
        
        if not 0 <= volume <= 100:
            logger.error(f"Invalid volume: {volume}")
            return False
        
        query = """
        mutation SetVolume($zoneId: ID!, $volume: Int!) {
            setVolume(soundZone: $zoneId, volume: $volume) {
                success
            }
        }
        """
        
        result = self._execute_query(query, {
            'zoneId': zone_id,
            'volume': volume
        })
        
        if 'error' in result:
            return False
        
        return result.get('setVolume', {}).get('success', False)
    
    def get_now_playing(self, zone_id: str) -> Dict:
        """Get current playing track information"""
        
        query = """
        query NowPlaying($zoneId: ID!) {
            nowPlaying(soundZone: $zoneId) {
                track {
                    id
                    name
                    artists
                    album
                    duration
                    imageUrl
                }
                isPlaying
                position
                startedAt
                playlist {
                    id
                    name
                }
            }
        }
        """
        
        result = self._execute_query(query, {'zoneId': zone_id})
        
        if 'error' in result:
            return {'error': result['error']}
        
        return result.get('nowPlaying', {})
    
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
                
                # Check playback status
                now_playing = zone.get('nowPlaying', {})
                playback = now_playing.get('playback', {}) if now_playing else {}
                is_playing = playback.get('isPlaying', False) if playback else now_playing.get('isPlaying', False)
                
                if is_playing:
                    diagnosis['playing_zones'] += 1
                    if now_playing and now_playing.get('track'):
                        zone_status['currently_playing'] = now_playing['track'].get('name')
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
    
    def quick_fix_zone(self, zone_id: str) -> Dict:
        """Attempt to fix common zone issues"""
        
        fixes_attempted = []
        status = self.get_zone_status(zone_id)
        
        if 'error' in status:
            return {
                'success': False,
                'message': 'Could not get zone status',
                'error': status['error']
            }
        
        # Check if zone is online
        if not status.get('isOnline'):
            return {
                'success': False,
                'message': 'Zone is offline - please check device power and network connection'
            }
        
        # Check if music is playing
        now_playing = status.get('nowPlaying', {})
        if not now_playing.get('isPlaying'):
            # Try to resume playback
            if self.control_playback(zone_id, 'play'):
                fixes_attempted.append('Resumed playback')
            else:
                fixes_attempted.append('Failed to resume playback')
        
        # Check volume
        current_volume = status.get('volume', 0)
        if current_volume < 20:
            # Set to reasonable volume
            if self.set_volume(zone_id, 50):
                fixes_attempted.append(f'Increased volume from {current_volume} to 50')
            else:
                fixes_attempted.append('Failed to adjust volume')
        
        return {
            'success': len(fixes_attempted) > 0,
            'fixes_attempted': fixes_attempted,
            'current_status': {
                'is_playing': now_playing.get('isPlaying'),
                'volume': status.get('volume'),
                'track': now_playing.get('track', {}).get('name')
            }
        }


# Global instance
soundtrack_api = SoundtrackAPI()
#!/usr/bin/env python3
"""
Soundtrack Your Brand API Investigation
Comprehensive test of actual API capabilities
"""

import os
import sys
import json
from typing import Dict, List, Any
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Add current directory to path
sys.path.append('.')
from soundtrack_api import SoundtrackAPI


class SYBInvestigator:
    """Investigates and documents actual SYB API capabilities"""
    
    def __init__(self):
        self.api = SoundtrackAPI()
        self.capabilities = {
            'detection': {},
            'control': {},
            'playlists': {},
            'schedules': {},
            'limitations': []
        }
    
    def investigate_all(self) -> Dict[str, Any]:
        """Run comprehensive investigation"""
        print("🔍 Starting Soundtrack Your Brand API Investigation...\n")
        
        # Get test zones
        zones = self._get_test_zones()
        if not zones:
            print("❌ No zones found for testing")
            return self.capabilities
        
        print(f"Found {len(zones)} zones across {len(set(z['account_name'] for z in zones))} accounts\n")
        
        # Test each capability area
        self._test_detection_capabilities(zones)
        self._test_control_capabilities(zones)
        self._test_playlist_capabilities(zones)
        self._test_schedule_capabilities(zones)
        
        return self.capabilities
    
    def _get_test_zones(self) -> List[Dict]:
        """Get zones for testing"""
        accounts = self.api.get_accounts()
        zones = []
        
        for account in accounts[:5]:  # Test first 5 accounts
            account_data = self.api.get_account_by_id(account['id'])
            if account_data and 'locations' in account_data:
                for loc_edge in account_data['locations']['edges']:
                    location = loc_edge['node']
                    for zone_edge in location.get('soundZones', {}).get('edges', []):
                        zone = zone_edge['node']
                        zone['location_name'] = location.get('name')
                        zone['account_name'] = account_data.get('businessName')
                        zones.append(zone)
        
        return zones
    
    def _test_detection_capabilities(self, zones: List[Dict]):
        """Test what we can detect about zone status"""
        print("🎵 Testing Detection Capabilities...")
        
        # Test status query with corrected fields
        test_zone = zones[0]
        zone_id = test_zone['id']
        
        # Test basic status
        status_query = '''
        query GetZoneStatus($zoneId: ID!) {
            soundZone(id: $zoneId) {
                id
                name
                streamingType
                device {
                    id
                    name
                    model
                    firmwareVersion
                    lastSeen
                }
                nowPlaying {
                    track {
                        id
                        name
                        artists {
                            name
                        }
                        album {
                            name
                        }
                        duration
                    }
                    isPlaying
                    position
                    startedAt
                }
                schedule {
                    id
                    name
                    timezone
                }
                playbackHistory(first: 3) {
                    edges {
                        node {
                            track {
                                name
                                artists {
                                    name
                                }
                            }
                            startedAt
                        }
                    }
                }
            }
        }
        '''
        
        result = self.api._execute_query(status_query, {'zoneId': zone_id})
        
        if 'error' not in result:
            zone = result['soundZone']
            print(f"✅ Basic status detection works")
            
            # Document what we can detect
            self.capabilities['detection']['basic_info'] = True
            self.capabilities['detection']['device_info'] = bool(zone.get('device'))
            self.capabilities['detection']['now_playing'] = bool(zone.get('nowPlaying'))
            self.capabilities['detection']['playback_history'] = bool(zone.get('playbackHistory', {}).get('edges'))
            self.capabilities['detection']['schedule_info'] = bool(zone.get('schedule'))
            
            # Check if playing
            now_playing = zone.get('nowPlaying')
            if now_playing:
                is_playing = now_playing.get('isPlaying', False)
                track = now_playing.get('track')
                print(f"   Currently playing: {is_playing}")
                if track:
                    artists = [a['name'] for a in track.get('artists', [])]
                    print(f"   Track: {track.get('name')} by {', '.join(artists)}")
                    self.capabilities['detection']['track_details'] = True
            
            # Check schedule
            schedule = zone.get('schedule')
            if schedule:
                print(f"   Schedule: {schedule.get('name')} (TZ: {schedule.get('timezone')})")
                self.capabilities['detection']['schedule_mode'] = True
            else:
                print(f"   No schedule detected - likely manual mode")
                self.capabilities['detection']['manual_mode'] = True
        
        else:
            print(f"❌ Basic status detection failed: {result['error']}")
            self.capabilities['detection']['basic_info'] = False
        
        print()
    
    def _test_control_capabilities(self, zones: List[Dict]):
        """Test what control operations are possible"""
        print("🎛️  Testing Control Capabilities...")
        
        test_zone = zones[0]
        zone_id = test_zone['id']
        
        # Test volume control (0-16 scale)
        print("Testing volume control...")
        volume_mutation = '''
        mutation SetVolume($input: SetVolumeInput!) {
            setVolume(input: $input) {
                __typename
            }
        }
        '''
        
        # Try setting volume to 8 (middle of 0-16 range)
        result = self.api._execute_query(volume_mutation, {
            'input': {
                'soundZone': zone_id,
                'volume': 8
            }
        })
        
        if 'error' not in result:
            print("✅ Volume control works (0-16 scale)")
            self.capabilities['control']['volume'] = True
            self.capabilities['control']['volume_range'] = "0-16"
        else:
            print(f"❌ Volume control failed: {result['error']}")
            self.capabilities['control']['volume'] = False
            if 'not found' in str(result['error']).lower():
                self.capabilities['limitations'].append("Zone not controllable (playback device not found)")
        
        # Test playback control
        controls = ['play', 'pause', 'skipTrack']
        
        for control in controls:
            print(f"Testing {control}...")
            
            mutation = f'''
            mutation Test{control.title()}($input: {control.title()}Input!) {{
                {control}(input: $input) {{
                    __typename
                }}
            }}
            '''
            
            result = self.api._execute_query(mutation, {
                'input': {
                    'soundZone': zone_id
                }
            })
            
            if 'error' not in result:
                print(f"✅ {control} works")
                self.capabilities['control'][control] = True
            else:
                print(f"❌ {control} failed: {result['error']}")
                self.capabilities['control'][control] = False
                if 'not found' in str(result['error']).lower():
                    if "Zone not controllable" not in self.capabilities['limitations']:
                        self.capabilities['limitations'].append("Zone not controllable (playback device not found)")
        
        print()
    
    def _test_playlist_capabilities(self, zones: List[Dict]):
        """Test playlist discovery and management"""
        print("📚 Testing Playlist Capabilities...")
        
        # Test playlist search/browse
        playlist_queries = [
            ('searchPlaylists', 'query SearchPlaylists($query: String!) { searchPlaylists(query: $query, first: 5) { edges { node { id name shortDescription } } } }'),
            ('browsePlaylists', 'query BrowsePlaylists { browsePlaylists(first: 10) { edges { node { id name shortDescription } } } }'),
            ('playlists', 'query AllPlaylists { playlists(first: 10) { edges { node { id name shortDescription type } } } }'),
        ]
        
        for query_name, query in playlist_queries:
            print(f"Testing {query_name}...")
            
            variables = {'query': 'coffee'} if 'SearchPlaylists' in query else {}
            result = self.api._execute_query(query, variables)
            
            if 'error' not in result and query_name in result:
                playlists = result[query_name].get('edges', [])
                print(f"✅ {query_name} works - found {len(playlists)} playlists")
                self.capabilities['playlists'][query_name] = True
                
                # Show examples
                for edge in playlists[:3]:
                    playlist = edge['node']
                    print(f"   - {playlist.get('name')}: {playlist.get('shortDescription', 'No description')}")
                
            else:
                print(f"❌ {query_name} failed: {result.get('error', 'No data returned')}")
                self.capabilities['playlists'][query_name] = False
        
        # Test playlist switching
        print("Testing playlist switching...")
        
        # Try to set a playlist on a zone
        set_playlist_mutation = '''
        mutation SetPlaylist($input: SetPlayFromInput!) {
            setPlayFrom(input: $input) {
                soundZone {
                    id
                }
            }
        }
        '''
        
        # This would need a playlist ID - testing structure only
        print("❓ Playlist switching requires specific playlist ID (structure available)")
        self.capabilities['playlists']['can_switch'] = "requires_playlist_id"
        
        print()
    
    def _test_schedule_capabilities(self, zones: List[Dict]):
        """Test schedule detection and management"""
        print("📅 Testing Schedule Capabilities...")
        
        test_zone = zones[0]
        zone_id = test_zone['id']
        
        # Test detailed schedule query
        schedule_query = '''
        query GetScheduleDetails($zoneId: ID!) {
            soundZone(id: $zoneId) {
                id
                schedule {
                    id
                    name
                    timezone
                    entries {
                        id
                        name
                        startTime
                        endTime
                        dayOfWeek
                        playlist {
                            id
                            name
                            trackCount
                        }
                        isActive
                    }
                }
            }
        }
        '''
        
        result = self.api._execute_query(schedule_query, {'zoneId': zone_id})
        
        if 'error' not in result:
            schedule = result['soundZone'].get('schedule')
            if schedule:
                print(f"✅ Schedule detection works")
                print(f"   Schedule: {schedule.get('name')}")
                print(f"   Timezone: {schedule.get('timezone')}")
                
                entries = schedule.get('entries', [])
                print(f"   Entries: {len(entries)}")
                
                # Show first few entries
                for entry in entries[:3]:
                    playlist = entry.get('playlist', {})
                    print(f"   - {entry.get('startTime')}-{entry.get('endTime')}: {playlist.get('name')}")
                
                self.capabilities['schedules']['detection'] = True
                self.capabilities['schedules']['entries_available'] = len(entries) > 0
                
                # Check if we can detect schedule vs manual mode
                active_entries = [e for e in entries if e.get('isActive')]
                if active_entries:
                    print(f"   Currently scheduled mode ({len(active_entries)} active entries)")
                    self.capabilities['schedules']['mode_detection'] = "scheduled"
                else:
                    print(f"   Currently manual mode (no active entries)")
                    self.capabilities['schedules']['mode_detection'] = "manual"
            
            else:
                print("✅ Zone accessible but no schedule (manual mode)")
                self.capabilities['schedules']['detection'] = True
                self.capabilities['schedules']['mode_detection'] = "manual"
        
        else:
            print(f"❌ Schedule query failed: {result['error']}")
            self.capabilities['schedules']['detection'] = False
        
        print()
    
    def print_summary(self):
        """Print comprehensive summary"""
        print("=" * 60)
        print("🎵 SOUNDTRACK YOUR BRAND API CAPABILITIES SUMMARY")
        print("=" * 60)
        
        # Detection capabilities
        print("\n🔍 DETECTION CAPABILITIES:")
        detection = self.capabilities['detection']
        
        if detection.get('basic_info'):
            print("✅ Can detect zone basic info (name, device, streaming type)")
        
        if detection.get('now_playing'):
            print("✅ Can detect current playing status")
            if detection.get('track_details'):
                print("   - Including track name, artists, album, duration, position")
        
        if detection.get('schedule_info'):
            print("✅ Can detect if zone has a schedule")
            if detection.get('schedule_mode'):
                print("   - Can detect scheduled vs manual mode")
        
        if detection.get('playback_history'):
            print("✅ Can access recent playback history")
        
        # Control capabilities  
        print("\n🎛️  CONTROL CAPABILITIES:")
        control = self.capabilities['control']
        
        if control.get('volume'):
            print(f"✅ Volume control available (scale: {control.get('volume_range', 'unknown')})")
        else:
            print("❌ Volume control not available")
        
        for action in ['play', 'pause', 'skipTrack']:
            if control.get(action):
                print(f"✅ {action.title()} control available")
            else:
                print(f"❌ {action.title()} control not available")
        
        # Playlist capabilities
        print("\n📚 PLAYLIST CAPABILITIES:")
        playlists = self.capabilities['playlists']
        
        for capability in ['searchPlaylists', 'browsePlaylists', 'playlists']:
            if playlists.get(capability):
                print(f"✅ Can {capability}")
            else:
                print(f"❌ Cannot {capability}")
        
        if playlists.get('can_switch') == "requires_playlist_id":
            print("❓ Playlist switching possible with specific playlist ID")
        
        # Schedule capabilities
        print("\n📅 SCHEDULE CAPABILITIES:")
        schedules = self.capabilities['schedules']
        
        if schedules.get('detection'):
            print("✅ Can detect schedule information")
            if schedules.get('entries_available'):
                print("   - Can access schedule entries with times and playlists")
            
            mode = schedules.get('mode_detection')
            if mode:
                print(f"   - Can detect mode: {mode}")
        
        # Limitations
        print("\n⚠️  LIMITATIONS:")
        for limitation in self.capabilities['limitations']:
            print(f"❌ {limitation}")
        
        if not self.capabilities['limitations']:
            print("✅ No major limitations detected")
        
        print("\n" + "=" * 60)


def main():
    """Main investigation function"""
    investigator = SYBInvestigator()
    
    try:
        capabilities = investigator.investigate_all()
        investigator.print_summary()
        
        # Save results to JSON
        with open('syb_api_capabilities.json', 'w') as f:
            json.dump(capabilities, f, indent=2)
        
        print(f"\n📄 Full results saved to: syb_api_capabilities.json")
        
    except Exception as e:
        print(f"❌ Investigation failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
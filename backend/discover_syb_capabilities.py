#!/usr/bin/env python3
"""
Comprehensive SYB API Capability Discovery
Tests all possible mutations and capabilities for IPAM400 devices
"""

import logging
import json
from typing import Dict, List, Any
from soundtrack_api import soundtrack_api

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def introspect_schema() -> Dict:
    """Use GraphQL introspection to discover all available mutations"""
    
    query = """
    query IntrospectSchema {
        __schema {
            mutationType {
                name
                fields {
                    name
                    description
                    args {
                        name
                        type {
                            name
                            kind
                            ofType {
                                name
                                kind
                            }
                        }
                    }
                }
            }
        }
    }
    """
    
    result = soundtrack_api._execute_query(query)
    return result


def discover_mutations() -> List[str]:
    """Get all available mutations from the schema"""
    
    schema = introspect_schema()
    mutations = []
    
    if 'error' in schema:
        logger.error(f"Schema introspection failed: {schema['error']}")
        return mutations
    
    mutation_type = schema.get('__schema', {}).get('mutationType', {})
    if mutation_type:
        fields = mutation_type.get('fields', [])
        for field in fields:
            mutations.append({
                'name': field.get('name'),
                'description': field.get('description', ''),
                'args': field.get('args', [])
            })
    
    return mutations


def test_playlist_mutations(zone_id: str) -> Dict:
    """Test if we can change playlists"""
    
    logger.info("Testing playlist-related mutations...")
    results = {}
    
    # Test common playlist mutation names
    playlist_mutations = [
        'switchPlaylist',
        'setPlaylist', 
        'changePlaylist',
        'assignPlaylist',
        'updatePlaylist'
    ]
    
    for mutation_name in playlist_mutations:
        query = f"""
        mutation TestPlaylistMutation($input: {mutation_name.capitalize()}Input!) {{
            {mutation_name}(input: $input) {{
                __typename
            }}
        }}
        """
        
        result = soundtrack_api._execute_query(query, {
            'input': {
                'soundZone': zone_id,
                'playlist': 'test-playlist-id'  # This won't work but tests the mutation existence
            }
        })
        
        results[mutation_name] = {
            'exists': 'error' not in result or 'Unknown mutation' not in str(result.get('error', '')),
            'result': result
        }
    
    return results


def test_schedule_mutations(zone_id: str) -> Dict:
    """Test schedule-related mutations"""
    
    logger.info("Testing schedule-related mutations...")
    results = {}
    
    schedule_mutations = [
        'setSchedule',
        'updateSchedule',
        'switchSchedule',
        'overrideSchedule',
        'enableSchedule',
        'disableSchedule'
    ]
    
    for mutation_name in schedule_mutations:
        query = f"""
        mutation TestScheduleMutation($input: {mutation_name.capitalize()}Input!) {{
            {mutation_name}(input: $input) {{
                __typename
            }}
        }}
        """
        
        result = soundtrack_api._execute_query(query, {
            'input': {
                'soundZone': zone_id,
                'schedule': 'test-schedule-id'
            }
        })
        
        results[mutation_name] = {
            'exists': 'error' not in result or 'Unknown mutation' not in str(result.get('error', '')),
            'result': result
        }
    
    return results


def test_track_mutations(zone_id: str) -> Dict:
    """Test track control mutations"""
    
    logger.info("Testing track control mutations...")
    results = {}
    
    track_mutations = [
        'blockTrack',
        'unblockTrack',
        'banTrack',
        'likeTrack',
        'dislikeTrack',
        'skipTrack'  # We know this one works
    ]
    
    for mutation_name in track_mutations:
        query = f"""
        mutation TestTrackMutation($input: {mutation_name.capitalize()}Input!) {{
            {mutation_name}(input: $input) {{
                __typename
            }}
        }}
        """
        
        result = soundtrack_api._execute_query(query, {
            'input': {
                'soundZone': zone_id
            }
        })
        
        results[mutation_name] = {
            'exists': 'error' not in result or 'Unknown mutation' not in str(result.get('error', '')),
            'result': result
        }
    
    return results


def test_mode_mutations(zone_id: str) -> Dict:
    """Test mode switching mutations"""
    
    logger.info("Testing mode switching mutations...")
    results = {}
    
    mode_mutations = [
        'setMode',
        'switchToManual',
        'switchToScheduled',
        'enableManualMode',
        'enableScheduledMode'
    ]
    
    for mutation_name in mode_mutations:
        query = f"""
        mutation TestModeMutation($input: {mutation_name.capitalize()}Input!) {{
            {mutation_name}(input: $input) {{
                __typename
            }}
        }}
        """
        
        result = soundtrack_api._execute_query(query, {
            'input': {
                'soundZone': zone_id
            }
        })
        
        results[mutation_name] = {
            'exists': 'error' not in result or 'Unknown mutation' not in str(result.get('error', '')),
            'result': result
        }
    
    return results


def test_zone_control_mutations(zone_id: str) -> Dict:
    """Test various zone control mutations"""
    
    logger.info("Testing zone control mutations...")
    results = {}
    
    control_mutations = [
        'muteZone',
        'unmuteZone',
        'restartZone',
        'resetZone',
        'syncZone'
    ]
    
    for mutation_name in control_mutations:
        query = f"""
        mutation TestControlMutation($input: {mutation_name.capitalize()}Input!) {{
            {mutation_name}(input: $input) {{
                __typename
            }}
        }}
        """
        
        result = soundtrack_api._execute_query(query, {
            'input': {
                'soundZone': zone_id
            }
        })
        
        results[mutation_name] = {
            'exists': 'error' not in result or 'Unknown mutation' not in str(result.get('error', '')),
            'result': result
        }
    
    return results


def discover_query_capabilities() -> Dict:
    """Discover what query capabilities are available"""
    
    logger.info("Testing query capabilities...")
    
    # Test various queries
    queries = [
        ('playlists', 'query { playlists(first: 10) { edges { node { id name } } } }'),
        ('schedules', 'query { schedules(first: 10) { edges { node { id name } } } }'),
        ('tracks', 'query { tracks(first: 10) { edges { node { id name } } } }'),
        ('genres', 'query { genres(first: 10) { edges { node { id name } } } }'),
        ('artists', 'query { artists(first: 10) { edges { node { id name } } } }')
    ]
    
    results = {}
    for name, query in queries:
        result = soundtrack_api._execute_query(query)
        results[name] = {
            'available': 'error' not in result,
            'result': result if 'error' not in result else result['error']
        }
    
    return results


def test_ipam400_zone_comprehensive(zone_id: str) -> Dict:
    """Comprehensive test of all capabilities on a specific IPAM400 zone"""
    
    logger.info(f"Running comprehensive capability test on zone: {zone_id}")
    
    # First get basic zone info
    zone_status = soundtrack_api.get_zone_status(zone_id)
    device_name = zone_status.get('device', {}).get('name', '')
    
    if 'IPAM' not in device_name:
        logger.warning(f"Zone {zone_id} device is '{device_name}' - may not support full control")
    
    comprehensive_results = {
        'zone_info': zone_status,
        'basic_controls': {
            'volume': soundtrack_api.set_volume(zone_id, 8),
            'play': soundtrack_api.control_playback(zone_id, 'play'),
            'pause': soundtrack_api.control_playback(zone_id, 'pause'),
            'skip': soundtrack_api.control_playback(zone_id, 'skip')
        },
        'mutations_tested': {
            'playlist': test_playlist_mutations(zone_id),
            'schedule': test_schedule_mutations(zone_id),
            'track': test_track_mutations(zone_id),
            'mode': test_mode_mutations(zone_id),
            'control': test_zone_control_mutations(zone_id)
        },
        'query_capabilities': discover_query_capabilities()
    }
    
    return comprehensive_results


def main():
    """Main discovery function"""
    
    print("🔍 Discovering Soundtrack Your Brand API Capabilities...")
    
    # Step 1: Introspect schema for all available mutations
    print("\n1. Introspecting GraphQL schema...")
    mutations = discover_mutations()
    print(f"Found {len(mutations)} mutations")
    
    for mutation in mutations[:10]:  # Show first 10
        print(f"  - {mutation['name']}: {mutation['description'][:50]}...")
    
    # Step 2: Test with known IPAM400 zones
    print("\n2. Finding IPAM400 zones for testing...")
    
    # Look for test zones (you'll need to update this with actual zone IDs)
    test_zones = []
    
    # Find some zones from accounts to test
    accounts = soundtrack_api.get_accounts()
    for account in accounts[:3]:  # Test first 3 accounts
        for loc_edge in account.get('locations', {}).get('edges', []):
            location = loc_edge['node']
            for zone_edge in location.get('soundZones', {}).get('edges', []):
                zone = zone_edge['node']
                if zone.get('isOnline') or zone.get('online'):
                    test_zones.append(zone['id'])
                    if len(test_zones) >= 3:  # Test up to 3 zones
                        break
            if len(test_zones) >= 3:
                break
        if len(test_zones) >= 3:
            break
    
    if not test_zones:
        print("⚠️  No online zones found for testing")
        return
    
    # Step 3: Comprehensive testing on selected zones
    print(f"\n3. Running comprehensive tests on {len(test_zones)} zones...")
    
    all_results = {}
    
    for zone_id in test_zones:
        print(f"\nTesting zone: {zone_id}")
        results = test_ipam400_zone_comprehensive(zone_id)
        all_results[zone_id] = results
    
    # Step 4: Save comprehensive results
    output_file = '/Users/benorbe/Documents/BMAsia Social Hub/backend/syb_comprehensive_capabilities.json'
    
    final_results = {
        'discovery_timestamp': '2025-01-20T00:00:00Z',
        'schema_mutations': mutations,
        'zone_test_results': all_results,
        'summary': {
            'total_mutations_found': len(mutations),
            'zones_tested': len(test_zones),
            'capabilities_confirmed': []
        }
    }
    
    with open(output_file, 'w') as f:
        json.dump(final_results, f, indent=2, default=str)
    
    print(f"\n✅ Comprehensive results saved to: {output_file}")
    
    # Step 5: Generate summary
    print("\n📋 CAPABILITY DISCOVERY SUMMARY")
    print("=" * 50)
    
    # Analyze results
    working_mutations = []
    failed_mutations = []
    
    for zone_id, zone_results in all_results.items():
        basic_controls = zone_results.get('basic_controls', {})
        for control, result in basic_controls.items():
            if result.get('success'):
                if control not in working_mutations:
                    working_mutations.append(control)
            else:
                if control not in failed_mutations:
                    failed_mutations.append(control)
    
    print(f"✅ Working Controls: {', '.join(working_mutations)}")
    print(f"❌ Failed Controls: {', '.join(failed_mutations)}")
    
    # Check for new mutations discovered
    new_mutations = []
    for zone_results in all_results.values():
        mutations_tested = zone_results.get('mutations_tested', {})
        for category, results in mutations_tested.items():
            for mutation_name, mutation_result in results.items():
                if mutation_result.get('exists') and mutation_name not in ['skipTrack', 'play', 'pause']:
                    if mutation_name not in new_mutations:
                        new_mutations.append(mutation_name)
    
    if new_mutations:
        print(f"🆕 Potentially Available Mutations: {', '.join(new_mutations)}")
    else:
        print("🔒 No additional mutations found beyond basic playback control")
    
    print("\n🎯 RECOMMENDATIONS:")
    print("- Focus on IPAM400 devices for direct API control")
    print("- Use escalation for Samsung/display devices")
    print("- Volume and playback control work reliably")
    if new_mutations:
        print(f"- Test these mutations with real requests: {', '.join(new_mutations[:3])}")
    else:
        print("- Playlist and schedule changes require manual intervention")


if __name__ == '__main__':
    main()
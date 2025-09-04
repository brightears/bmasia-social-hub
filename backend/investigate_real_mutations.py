#!/usr/bin/env python3
"""
Investigate the EXACT structure of available mutations in SYB API
Let's get the correct input types and test more systematically
"""

import logging
import json
from soundtrack_api import soundtrack_api

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_mutation_details():
    """Get detailed information about mutation input types"""
    
    query = """
    query GetMutationDetails {
        __schema {
            mutationType {
                fields {
                    name
                    description
                    args {
                        name
                        description
                        type {
                            name
                            kind
                            ofType {
                                name
                                kind
                                inputFields {
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
            }
        }
    }
    """
    
    result = soundtrack_api._execute_query(query)
    return result


def find_control_mutations():
    """Find all mutations related to playback control"""
    
    mutation_details = get_mutation_details()
    
    if 'error' in mutation_details:
        logger.error(f"Failed to get mutation details: {mutation_details['error']}")
        return {}
    
    control_mutations = {}
    mutation_type = mutation_details.get('__schema', {}).get('mutationType', {})
    
    if not mutation_type:
        return {}
    
    for field in mutation_type.get('fields', []):
        name = field.get('name', '').lower()
        
        # Look for mutations that might control playback or zones
        if any(keyword in name for keyword in ['play', 'pause', 'skip', 'volume', 'mute', 'track', 'zone', 'sound']):
            control_mutations[field['name']] = {
                'description': field.get('description', ''),
                'args': field.get('args', [])
            }
    
    return control_mutations


def test_zone_permissions():
    """Test different zones to see which ones actually allow control"""
    
    logger.info("Testing zone permissions across different accounts...")
    
    accounts = soundtrack_api.get_accounts()
    zone_permissions = {}
    
    tested_zones = 0
    
    for account in accounts:
        if tested_zones >= 5:  # Limit testing
            break
            
        account_name = account.get('name', 'Unknown')
        logger.info(f"Testing account: {account_name}")
        
        for loc_edge in account.get('locations', {}).get('edges', []):
            if tested_zones >= 5:
                break
                
            location = loc_edge['node']
            location_name = location.get('name', 'Unknown')
            
            for zone_edge in location.get('soundZones', {}).get('edges', []):
                if tested_zones >= 5:
                    break
                    
                zone = zone_edge['node']
                zone_id = zone['id']
                zone_name = zone.get('name', 'Unknown')
                
                # Get zone status to check device
                status = soundtrack_api.get_zone_status(zone_id)
                device = status.get('device', {})
                device_name = device.get('name', '')
                streaming_type = status.get('streamingType', '')
                
                logger.info(f"  Testing zone: {zone_name}")
                logger.info(f"    Device: {device_name}")
                logger.info(f"    Streaming: {streaming_type}")
                
                # Test basic volume control
                volume_test = soundtrack_api.set_volume(zone_id, 8)
                play_test = soundtrack_api.control_playback(zone_id, 'play')
                
                zone_permissions[zone_id] = {
                    'zone_name': zone_name,
                    'location': location_name,
                    'account': account_name,
                    'device_name': device_name,
                    'streaming_type': streaming_type,
                    'volume_control': volume_test.get('success', False),
                    'volume_error': volume_test.get('error', ''),
                    'play_control': play_test.get('success', False),
                    'play_error': play_test.get('error', ''),
                    'is_controllable': volume_test.get('success', False) or play_test.get('success', False)
                }
                
                tested_zones += 1
                
                if zone_permissions[zone_id]['is_controllable']:
                    logger.info(f"    ✅ Zone is controllable!")
                    break  # Found a working zone, test more mutations on it
                else:
                    logger.info(f"    ❌ Zone not controllable")
    
    return zone_permissions


def test_advanced_mutations(working_zone_id):
    """Test advanced mutations on a zone that we know works"""
    
    if not working_zone_id:
        return {}
    
    logger.info(f"Testing advanced mutations on working zone: {working_zone_id}")
    
    # Test mutations that might exist based on common music player functionality
    advanced_tests = {}
    
    # Test different approaches to the mutations we know exist
    mutation_variations = [
        # Different volume control approaches
        {
            'name': 'setVolume_v1',
            'query': '''
                mutation SetVolume($soundZone: ID!, $volume: Int!) {
                    setVolume(soundZone: $soundZone, volume: $volume) {
                        ... on SoundZone {
                            id
                            name
                        }
                    }
                }
            ''',
            'variables': {'soundZone': working_zone_id, 'volume': 8}
        },
        
        # Try without input object wrapper
        {
            'name': 'play_direct',
            'query': '''
                mutation Play($soundZone: ID!) {
                    play(soundZone: $soundZone) {
                        ... on SoundZone {
                            id
                            name
                        }
                    }
                }
            ''',
            'variables': {'soundZone': working_zone_id}
        },
        
        # Try mute/unmute
        {
            'name': 'mute_direct',
            'query': '''
                mutation Mute($soundZone: ID!) {
                    mute(soundZone: $soundZone) {
                        ... on SoundZone {
                            id
                            name
                        }
                    }
                }
            ''',
            'variables': {'soundZone': working_zone_id}
        }
    ]
    
    for test in mutation_variations:
        logger.info(f"Testing {test['name']}...")
        result = soundtrack_api._execute_query(test['query'], test['variables'])
        advanced_tests[test['name']] = result
        
        if 'error' not in result:
            logger.info(f"  ✅ {test['name']} might work!")
        else:
            logger.info(f"  ❌ {test['name']} failed: {result.get('error', 'Unknown error')}")
    
    return advanced_tests


def main():
    """Main investigation function"""
    print("🔍 INVESTIGATING REAL SYB MUTATION CAPABILITIES")
    print("=" * 60)
    
    # Step 1: Get all control-related mutations with their exact structure
    logger.info("1. Getting detailed mutation information...")
    control_mutations = find_control_mutations()
    
    print(f"\nFound {len(control_mutations)} control-related mutations:")
    for name, details in control_mutations.items():
        print(f"  - {name}: {details['description']}")
        for arg in details.get('args', [])[:2]:  # Show first 2 args
            print(f"    └─ {arg.get('name')}: {arg.get('type', {}).get('name', 'Complex type')}")
    
    # Step 2: Test zone permissions to find working zones
    logger.info("\n2. Testing zone permissions...")
    zone_permissions = test_zone_permissions()
    
    working_zones = [z_id for z_id, data in zone_permissions.items() if data['is_controllable']]
    
    print(f"\nZone Permission Results:")
    print(f"  Total zones tested: {len(zone_permissions)}")
    print(f"  Controllable zones: {len(working_zones)}")
    
    for zone_id, data in zone_permissions.items():
        status = "✅" if data['is_controllable'] else "❌"
        print(f"  {status} {data['zone_name']} ({data['device_name']})")
        if not data['is_controllable']:
            print(f"      Volume error: {data['volume_error']}")
    
    # Step 3: If we found working zones, test advanced mutations
    advanced_results = {}
    if working_zones:
        logger.info("\n3. Testing advanced mutations on working zone...")
        advanced_results = test_advanced_mutations(working_zones[0])
    else:
        print("\n❌ No controllable zones found - cannot test advanced mutations")
    
    # Step 4: Save comprehensive results
    results = {
        'timestamp': '2025-01-20T00:00:00Z',
        'control_mutations': control_mutations,
        'zone_permissions': zone_permissions,
        'advanced_tests': advanced_results,
        'summary': {
            'total_control_mutations': len(control_mutations),
            'total_zones_tested': len(zone_permissions),
            'controllable_zones': len(working_zones),
            'working_zone_ids': working_zones
        }
    }
    
    output_file = '/Users/benorbe/Documents/BMAsia Social Hub/backend/syb_real_capabilities.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Results saved to: {output_file}")
    
    # Final summary
    print("\n📋 FINAL CAPABILITY ASSESSMENT")
    print("=" * 60)
    
    if working_zones:
        working_data = zone_permissions[working_zones[0]]
        print(f"✅ Found working zone: {working_data['zone_name']}")
        print(f"   Device: {working_data['device_name']}")
        print(f"   Account: {working_data['account']}")
        print(f"   Volume control: {'✅' if working_data['volume_control'] else '❌'}")
        print(f"   Play control: {'✅' if working_data['play_control'] else '❌'}")
        
        print(f"\n🎯 RECOMMENDATIONS:")
        print(f"   - Use zone {working_zones[0]} for testing new mutations")
        print(f"   - Device type '{working_data['device_name']}' supports API control")
        print(f"   - Implement device-based routing in bot logic")
    else:
        print("❌ No working zones found")
        print("\n🎯 RECOMMENDATIONS:")
        print("   - All tested zones may be trial/demo accounts")
        print("   - Focus on escalation strategies for all requests")
        print("   - Check if different API credentials are needed")
    
    return results


if __name__ == '__main__':
    main()
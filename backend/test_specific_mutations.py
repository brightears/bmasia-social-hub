#!/usr/bin/env python3
"""
Test specific SYB mutations that might work for IPAM400 devices
Based on the 113 mutations discovered, focus on the most promising ones
"""

import logging
import json
from soundtrack_api import soundtrack_api

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_working_mutations_from_schema():
    """Extract the actual mutations that exist in the API"""
    
    introspection = """
    query {
        __schema {
            mutationType {
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
    
    result = soundtrack_api._execute_query(introspection)
    
    if 'error' in result:
        return []
    
    mutations = []
    mutation_type = result.get('__schema', {}).get('mutationType', {})
    if mutation_type:
        for field in mutation_type.get('fields', []):
            mutations.append(field)
    
    return mutations


def test_real_mutations_on_ipam_zone():
    """Test the mutations that actually exist on a real IPAM zone"""
    
    # First find an IPAM zone
    logger.info("Looking for IPAM zones...")
    
    accounts = soundtrack_api.get_accounts()
    ipam_zones = []
    
    for account in accounts:
        for loc_edge in account.get('locations', {}).get('edges', []):
            location = loc_edge['node']
            for zone_edge in location.get('soundZones', {}).get('edges', []):
                zone = zone_edge['node']
                zone_id = zone['id']
                
                # Get zone details to check device
                status = soundtrack_api.get_zone_status(zone_id)
                device = status.get('device', {})
                device_name = device.get('name', '')
                
                if 'IPAM' in device_name:
                    ipam_zones.append({
                        'id': zone_id,
                        'name': zone.get('name'),
                        'device_name': device_name,
                        'account': account.get('name'),
                        'location': location.get('name')
                    })
                    
                    if len(ipam_zones) >= 2:  # Test on 2 zones max
                        break
            if len(ipam_zones) >= 2:
                break
        if len(ipam_zones) >= 2:
            break
    
    if not ipam_zones:
        logger.error("No IPAM zones found!")
        return
    
    logger.info(f"Found {len(ipam_zones)} IPAM zones to test")
    for zone in ipam_zones:
        logger.info(f"  {zone['name']} ({zone['device_name']})")
    
    # Test the mutations we know work first
    test_zone = ipam_zones[0]
    zone_id = test_zone['id']
    
    logger.info(f"\nTesting confirmed working mutations on {test_zone['name']}...")
    
    results = {
        'zone_info': test_zone,
        'working_mutations': {},
        'failed_mutations': {},
        'promising_mutations': {}
    }
    
    # Test confirmed working mutations
    working_mutations = {
        'setVolume': {
            'query': """
                mutation SetVolume($input: SetVolumeInput!) {
                    setVolume(input: $input) {
                        __typename
                    }
                }
            """,
            'variables': {
                'input': {
                    'soundZone': zone_id,
                    'volume': 8
                }
            }
        },
        'play': {
            'query': """
                mutation Play($input: PlayInput!) {
                    play(input: $input) {
                        __typename
                    }
                }
            """,
            'variables': {
                'input': {
                    'soundZone': zone_id
                }
            }
        },
        'pause': {
            'query': """
                mutation Pause($input: PauseInput!) {
                    pause(input: $input) {
                        __typename
                    }
                }
            """,
            'variables': {
                'input': {
                    'soundZone': zone_id
                }
            }
        },
        'skipTrack': {
            'query': """
                mutation SkipTrack($input: SkipTrackInput!) {
                    skipTrack(input: $input) {
                        __typename
                    }
                }
            """,
            'variables': {
                'input': {
                    'soundZone': zone_id
                }
            }
        }
    }
    
    for mutation_name, mutation_data in working_mutations.items():
        logger.info(f"Testing {mutation_name}...")
        result = soundtrack_api._execute_query(mutation_data['query'], mutation_data['variables'])
        
        if 'error' in result:
            results['failed_mutations'][mutation_name] = result['error']
        else:
            results['working_mutations'][mutation_name] = result
    
    # Now let's test some promising mutations that might exist
    # Based on common music control patterns
    promising_mutations = {
        'mute': {
            'query': """
                mutation Mute($input: MuteInput!) {
                    mute(input: $input) {
                        __typename
                    }
                }
            """,
            'variables': {
                'input': {
                    'soundZone': zone_id
                }
            }
        },
        'unmute': {
            'query': """
                mutation Unmute($input: UnmuteInput!) {
                    unmute(input: $input) {
                        __typename
                    }
                }
            """,
            'variables': {
                'input': {
                    'soundZone': zone_id
                }
            }
        }
    }
    
    logger.info("Testing potentially available mutations...")
    for mutation_name, mutation_data in promising_mutations.items():
        logger.info(f"Testing {mutation_name}...")
        result = soundtrack_api._execute_query(mutation_data['query'], mutation_data['variables'])
        
        if 'error' in result:
            if 'Unknown mutation' in str(result['error']) or 'does not exist' in str(result['error']):
                logger.info(f"  {mutation_name}: Not available")
            else:
                results['promising_mutations'][mutation_name] = {
                    'available': True,
                    'result': result
                }
        else:
            results['promising_mutations'][mutation_name] = {
                'available': True,
                'result': result
            }
    
    # Test if we can get more info about playlists or schedules through queries
    logger.info("Testing query capabilities...")
    
    query_tests = {
        'account_playlists': """
            query GetAccountPlaylists($accountId: ID!) {
                account(id: $accountId) {
                    musicLibrary {
                        playlists(first: 10) {
                            edges {
                                node {
                                    id
                                    name
                                    description
                                }
                            }
                        }
                    }
                }
            }
        """,
        'zone_schedule': f"""
            query GetZoneSchedule {{
                soundZone(id: "{zone_id}") {{
                    schedule {{
                        id
                        name
                        timezone
                    }}
                }}
            }}
        """
    }
    
    results['query_results'] = {}
    
    # Find the account ID for this zone
    zone_status = soundtrack_api.get_zone_status(zone_id)
    # We'll need to get the account ID differently - for now just test the zone schedule
    
    result = soundtrack_api._execute_query(query_tests['zone_schedule'])
    results['query_results']['zone_schedule'] = result
    
    # Save results
    output_file = '/Users/benorbe/Documents/BMAsia Social Hub/backend/ipam_mutation_tests.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    logger.info(f"\nResults saved to: {output_file}")
    
    # Print summary
    print("\n" + "="*60)
    print("IPAM400 MUTATION TEST RESULTS")
    print("="*60)
    
    print(f"\nTested zone: {test_zone['name']}")
    print(f"Device: {test_zone['device_name']}")
    print(f"Location: {test_zone['location']}")
    print(f"Account: {test_zone['account']}")
    
    print(f"\n✅ Working mutations ({len(results['working_mutations'])}):")
    for mutation in results['working_mutations'].keys():
        print(f"  - {mutation}")
    
    print(f"\n❌ Failed mutations ({len(results['failed_mutations'])}):")
    for mutation in results['failed_mutations'].keys():
        print(f"  - {mutation}")
    
    print(f"\n🔍 Promising mutations ({len(results['promising_mutations'])}):")
    for mutation, data in results['promising_mutations'].items():
        if data.get('available'):
            print(f"  - {mutation} (Available!)")
        else:
            print(f"  - {mutation} (Not available)")
    
    return results


def main():
    """Main function to test specific mutations"""
    print("🎵 Testing Specific SYB Mutations on IPAM Devices")
    print("=" * 60)
    
    # First, let's see what mutations actually exist
    logger.info("Getting all mutations from schema...")
    mutations = get_working_mutations_from_schema()
    
    # Filter for control-related mutations
    control_mutations = []
    for mutation in mutations:
        name = mutation.get('name', '').lower()
        if any(keyword in name for keyword in ['play', 'pause', 'skip', 'volume', 'mute', 'track', 'sound']):
            control_mutations.append(mutation)
    
    print(f"\nFound {len(control_mutations)} control-related mutations:")
    for mutation in control_mutations[:10]:  # Show first 10
        print(f"  - {mutation.get('name')}: {mutation.get('description', 'No description')}")
    
    # Now test them on real IPAM zones
    results = test_real_mutations_on_ipam_zone()
    
    return results


if __name__ == '__main__':
    main()
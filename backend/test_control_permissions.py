#!/usr/bin/env python3
"""
Test API control across different accounts to understand permission patterns
CRITICAL: Control happens at SYB cloud/app level, NOT device level
"""

import os
import json
import logging
from typing import Dict, Any, List
from datetime import datetime
from soundtrack_api import soundtrack_api

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_zone_properties(zone: Dict, account_name: str, location_name: str) -> Dict:
    """Analyze zone properties that might determine control permissions"""
    
    zone_id = zone.get('id')
    zone_name = zone.get('name', 'Unknown')
    
    # Get enhanced status
    try:
        enhanced_status = soundtrack_api.get_enhanced_zone_status(zone_id)
        basic_status = soundtrack_api.get_zone_status(zone_id)
    except Exception as e:
        logger.error(f"Error getting zone status for {zone_name}: {e}")
        return {
            'error': f'Could not get status: {e}',
            'zone_id': zone_id,
            'zone_name': zone_name,
            'account_name': account_name,
            'location_name': location_name
        }
    
    # Extract key properties
    properties = {
        'zone_id': zone_id,
        'zone_name': zone_name,
        'account_name': account_name,
        'location_name': location_name,
        'is_online': zone.get('isOnline') or zone.get('online', False),
        'is_paired': zone.get('isPaired', False),
        
        # From enhanced status
        'streaming_type': enhanced_status.get('streamingType'),
        'device_name': enhanced_status.get('device', {}).get('name') if enhanced_status.get('device') else None,
        'device_id': enhanced_status.get('device', {}).get('id') if enhanced_status.get('device') else None,
        'schedule_id': enhanced_status.get('schedule', {}).get('id') if enhanced_status.get('schedule') else None,
        'schedule_name': enhanced_status.get('schedule', {}).get('name') if enhanced_status.get('schedule') else None,
        'play_from_type': enhanced_status.get('playFrom', {}).get('__typename') if enhanced_status.get('playFrom') else None,
        'play_from_name': enhanced_status.get('playFrom', {}).get('name') if enhanced_status.get('playFrom') else None,
        'now_playing_type': enhanced_status.get('nowPlaying', {}).get('__typename') if enhanced_status.get('nowPlaying') else None,
    }
    
    return properties

def test_control_capabilities(zone_properties: Dict) -> Dict:
    """Test actual control capabilities regardless of device type"""
    
    zone_id = zone_properties['zone_id']
    zone_name = zone_properties['zone_name']
    
    logger.info(f"Testing control for {zone_name} (Device: {zone_properties.get('device_name', 'Unknown')})")
    
    results = {
        'zone_id': zone_id,
        'zone_name': zone_name,
        'tests': {}
    }
    
    # Test 1: Volume Control (try different volumes)
    try:
        # Try setting to middle volume
        volume_result = soundtrack_api.set_volume(zone_id, 8)
        results['tests']['volume_control'] = {
            'success': volume_result.get('success', False),
            'error': volume_result.get('error'),
            'attempted_volume': 8
        }
    except Exception as e:
        results['tests']['volume_control'] = {
            'success': False,
            'error': f'Exception: {e}',
            'attempted_volume': 8
        }
    
    # Test 2: Play Control
    try:
        play_result = soundtrack_api.control_playback(zone_id, 'play')
        results['tests']['play_control'] = {
            'success': play_result.get('success', False),
            'error': play_result.get('error')
        }
    except Exception as e:
        results['tests']['play_control'] = {
            'success': False,
            'error': f'Exception: {e}'
        }
    
    # Test 3: Pause Control  
    try:
        pause_result = soundtrack_api.control_playback(zone_id, 'pause')
        results['tests']['pause_control'] = {
            'success': pause_result.get('success', False),
            'error': pause_result.get('error')
        }
    except Exception as e:
        results['tests']['pause_control'] = {
            'success': False,
            'error': f'Exception: {e}'
        }
    
    # Summary
    successful_tests = [test for test, result in results['tests'].items() if result.get('success')]
    results['controllable'] = len(successful_tests) > 0
    results['successful_operations'] = successful_tests
    results['total_successful'] = len(successful_tests)
    
    return results

def analyze_control_patterns(all_results: List[Dict]) -> Dict:
    """Analyze patterns in what determines control permissions"""
    
    controllable_zones = [r for r in all_results if r.get('controllable')]
    uncontrollable_zones = [r for r in all_results if not r.get('controllable')]
    
    analysis = {
        'summary': {
            'total_zones': len(all_results),
            'controllable': len(controllable_zones),
            'uncontrollable': len(uncontrollable_zones),
            'control_rate': len(controllable_zones) / len(all_results) if all_results else 0
        },
        'patterns': {}
    }
    
    # Analyze by streaming type
    streaming_types = {}
    for zone in all_results:
        st = zone.get('streaming_type', 'Unknown')
        if st not in streaming_types:
            streaming_types[st] = {'total': 0, 'controllable': 0}
        streaming_types[st]['total'] += 1
        if zone.get('controllable'):
            streaming_types[st]['controllable'] += 1
    
    analysis['patterns']['by_streaming_type'] = streaming_types
    
    # Analyze by device type
    device_types = {}
    for zone in all_results:
        device = zone.get('device_name', 'Unknown')
        if device not in device_types:
            device_types[device] = {'total': 0, 'controllable': 0}
        device_types[device]['total'] += 1
        if zone.get('controllable'):
            device_types[device]['controllable'] += 1
    
    analysis['patterns']['by_device_type'] = device_types
    
    # Analyze by account
    accounts = {}
    for zone in all_results:
        account = zone.get('account_name', 'Unknown')
        if account not in accounts:
            accounts[account] = {'total': 0, 'controllable': 0}
        accounts[account]['total'] += 1
        if zone.get('controllable'):
            accounts[account]['controllable'] += 1
    
    analysis['patterns']['by_account'] = accounts
    
    # Look for common error patterns
    error_patterns = {}
    for zone in uncontrollable_zones:
        for test_name, test_result in zone.get('tests', {}).items():
            error = test_result.get('error', 'Unknown error')
            if error not in error_patterns:
                error_patterns[error] = []
            error_patterns[error].append({
                'zone_name': zone.get('zone_name'),
                'account': zone.get('account_name'),
                'streaming_type': zone.get('streaming_type'),
                'device_name': zone.get('device_name')
            })
    
    analysis['error_patterns'] = error_patterns
    
    return analysis

def main():
    """Run comprehensive control permission analysis"""
    
    print("=== SOUNDTRACK API CONTROL PERMISSION ANALYSIS ===\n")
    print("Testing the hypothesis that control permissions are NOT device-dependent")
    print("but rather based on subscription level, account permissions, or trial status.\n")
    
    # Get all accounts and zones
    try:
        accounts = soundtrack_api.get_accounts()
        print(f"Found {len(accounts)} accounts to analyze\n")
    except Exception as e:
        print(f"❌ Failed to get accounts: {e}")
        return
    
    all_zone_results = []
    
    for account in accounts:
        account_name = account.get('name', 'Unknown')
        print(f"\n--- Analyzing Account: {account_name} ---")
        
        total_zones = 0
        for loc_edge in account.get('locations', {}).get('edges', []):
            location = loc_edge['node']
            location_name = location.get('name', 'Unknown Location')
            
            for zone_edge in location.get('soundZones', {}).get('edges', []):
                zone = zone_edge['node']
                total_zones += 1
                
                # Analyze zone properties
                properties = analyze_zone_properties(zone, account_name, location_name)
                
                if 'error' in properties:
                    print(f"⚠️  {properties['zone_name']}: {properties['error']}")
                    continue
                
                # Test control capabilities  
                control_results = test_control_capabilities(properties)
                
                # Combine properties and control results
                combined_results = {**properties, **control_results}
                all_zone_results.append(combined_results)
                
                # Print immediate results
                status = "✅ CONTROLLABLE" if control_results.get('controllable') else "❌ NOT CONTROLLABLE"
                successful_ops = ', '.join(control_results.get('successful_operations', []))
                device_info = f"Device: {properties.get('device_name', 'Unknown')}"
                streaming_info = f"Type: {properties.get('streaming_type', 'Unknown')}"
                
                print(f"  {properties['zone_name']:20} | {status} | {device_info:25} | {streaming_info}")
                if successful_ops:
                    print(f"    ↳ Successful: {successful_ops}")
        
        print(f"Total zones in {account_name}: {total_zones}")
    
    print(f"\n=== ANALYSIS COMPLETE ===")
    print(f"Tested {len(all_zone_results)} zones across {len(accounts)} accounts\n")
    
    # Analyze patterns
    pattern_analysis = analyze_control_patterns(all_zone_results)
    
    print("📊 CONTROL PERMISSION PATTERNS:")
    print(f"  • Total zones tested: {pattern_analysis['summary']['total_zones']}")
    print(f"  • Controllable zones: {pattern_analysis['summary']['controllable']}")
    print(f"  • Control success rate: {pattern_analysis['summary']['control_rate']:.1%}")
    
    print("\n🔍 BY STREAMING TYPE:")
    for st, stats in pattern_analysis['patterns']['by_streaming_type'].items():
        rate = stats['controllable'] / stats['total'] if stats['total'] > 0 else 0
        print(f"  • {st}: {stats['controllable']}/{stats['total']} ({rate:.1%})")
    
    print("\n🔍 BY DEVICE TYPE:")
    for device, stats in pattern_analysis['patterns']['by_device_type'].items():
        rate = stats['controllable'] / stats['total'] if stats['total'] > 0 else 0
        print(f"  • {device}: {stats['controllable']}/{stats['total']} ({rate:.1%})")
    
    print("\n🔍 BY ACCOUNT:")
    for account, stats in pattern_analysis['patterns']['by_account'].items():
        rate = stats['controllable'] / stats['total'] if stats['total'] > 0 else 0
        print(f"  • {account}: {stats['controllable']}/{stats['total']} ({rate:.1%})")
    
    print("\n❌ COMMON ERROR PATTERNS:")
    for error, zones in pattern_analysis['error_patterns'].items():
        print(f"  • \"{error}\": {len(zones)} zones")
        for zone in zones[:3]:  # Show first 3 examples
            print(f"    - {zone['zone_name']} ({zone['account']}) - {zone['streaming_type']} - {zone['device_name']}")
    
    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"/tmp/control_permission_analysis_{timestamp}.json"
    
    full_results = {
        'timestamp': datetime.now().isoformat(),
        'summary': pattern_analysis['summary'],
        'patterns': pattern_analysis['patterns'],
        'error_patterns': pattern_analysis['error_patterns'],
        'detailed_results': all_zone_results
    }
    
    with open(results_file, 'w') as f:
        json.dump(full_results, f, indent=2)
    
    print(f"\n📁 Detailed results saved to: {results_file}")
    
    # Generate recommendations
    print("\n💡 RECOMMENDATIONS:")
    
    streaming_success_rates = {
        st: stats['controllable'] / stats['total'] if stats['total'] > 0 else 0
        for st, stats in pattern_analysis['patterns']['by_streaming_type'].items()
    }
    
    device_success_rates = {
        device: stats['controllable'] / stats['total'] if stats['total'] > 0 else 0
        for device, stats in pattern_analysis['patterns']['by_device_type'].items()
    }
    
    if any(rate == 0 for rate in streaming_success_rates.values()):
        low_control_types = [st for st, rate in streaming_success_rates.items() if rate == 0]
        print(f"  • StreamingType patterns: {', '.join(low_control_types)} have 0% control success")
        print(f"  • These are likely trial/demo subscriptions")
    
    if any(rate == 0 for rate in device_success_rates.values()):
        low_control_devices = [device for device, rate in device_success_rates.items() if rate == 0]
        print(f"  • Device patterns: {', '.join(low_control_devices)} have 0% control success")
        print(f"  • But remember: control is cloud-level, not device-level!")
    
    most_common_error = max(pattern_analysis['error_patterns'].keys(), 
                          key=lambda x: len(pattern_analysis['error_patterns'][x]))
    print(f"  • Most common error: \"{most_common_error}\"")
    print(f"  • This affects {len(pattern_analysis['error_patterns'][most_common_error])} zones")
    
    print("\n🎯 NEXT STEPS:")
    print("  1. Update control logic to check streamingType, not device type")
    print("  2. Implement better error categorization based on these patterns")
    print("  3. Always attempt control first, then provide appropriate error messages")
    print("  4. Focus on subscription/permission level rather than device hardware")

if __name__ == "__main__":
    main()
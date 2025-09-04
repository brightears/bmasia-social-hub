#!/usr/bin/env python3
"""
Quick focused test to understand control permission patterns
"""

import os
import logging
from datetime import datetime

# Load environment variables manually
env_vars = {}
with open('.env', 'r') as f:
    for line in f:
        if '=' in line and not line.strip().startswith('#'):
            key, value = line.strip().split('=', 1)
            os.environ[key] = value

from soundtrack_api import soundtrack_api

# Setup logging
logging.basicConfig(level=logging.WARNING)  # Reduce log noise
logger = logging.getLogger(__name__)

def test_sample_zones():
    """Test a representative sample of zones to understand patterns"""
    
    print("=== QUICK CONTROL PERMISSION TEST ===\n")
    
    # Get accounts
    accounts = soundtrack_api.get_accounts()
    print(f"Found {len(accounts)} accounts\n")
    
    tested_zones = []
    controllable_zones = []
    
    # Test up to 50 zones across different accounts/devices
    zone_count = 0
    max_zones = 50
    
    for account in accounts:
        if zone_count >= max_zones:
            break
            
        account_name = account.get('name', 'Unknown')
        print(f"\nTesting zones in: {account_name}")
        
        for loc_edge in account.get('locations', {}).get('edges', []):
            if zone_count >= max_zones:
                break
                
            location = loc_edge['node']
            location_name = location.get('name', 'Unknown')
            
            for zone_edge in location.get('soundZones', {}).get('edges', []):
                if zone_count >= max_zones:
                    break
                    
                zone = zone_edge['node']
                zone_id = zone.get('id')
                zone_name = zone.get('name', 'Unknown')
                
                # Get enhanced status for properties
                try:
                    enhanced_status = soundtrack_api.get_enhanced_zone_status(zone_id)
                    streaming_type = enhanced_status.get('streamingType', 'Unknown')
                    device_name = enhanced_status.get('device', {}).get('name', 'Unknown')
                except:
                    streaming_type = 'Error'
                    device_name = 'Error'
                
                # Test control (just volume - faster)
                volume_result = soundtrack_api.set_volume(zone_id, 8)
                is_controllable = volume_result.get('success', False)
                error = volume_result.get('error', 'Unknown')
                
                zone_data = {
                    'account': account_name,
                    'location': location_name,
                    'zone_name': zone_name,
                    'zone_id': zone_id,
                    'streaming_type': streaming_type,
                    'device_name': device_name,
                    'controllable': is_controllable,
                    'error': error if not is_controllable else None
                }
                
                tested_zones.append(zone_data)
                if is_controllable:
                    controllable_zones.append(zone_data)
                
                status = "✅ CONTROLLABLE" if is_controllable else "❌ NOT CONTROLLABLE"
                print(f"  {zone_name:30} | {status} | {streaming_type:15} | {device_name[:25]}")
                
                zone_count += 1
    
    print(f"\n=== ANALYSIS RESULTS ===")
    print(f"Total zones tested: {len(tested_zones)}")
    print(f"Controllable zones: {len(controllable_zones)}")
    print(f"Control success rate: {len(controllable_zones)/len(tested_zones)*100:.1f}%")
    
    # Analyze by streaming type
    streaming_stats = {}
    for zone in tested_zones:
        st = zone['streaming_type']
        if st not in streaming_stats:
            streaming_stats[st] = {'total': 0, 'controllable': 0}
        streaming_stats[st]['total'] += 1
        if zone['controllable']:
            streaming_stats[st]['controllable'] += 1
    
    print(f"\n📊 BY STREAMING TYPE:")
    for st, stats in streaming_stats.items():
        rate = stats['controllable'] / stats['total'] * 100 if stats['total'] > 0 else 0
        print(f"  {st:20} | {stats['controllable']}/{stats['total']} ({rate:.0f}%)")
    
    # Analyze by device type
    device_stats = {}
    for zone in tested_zones:
        device = zone['device_name'][:20]  # Truncate long names
        if device not in device_stats:
            device_stats[device] = {'total': 0, 'controllable': 0}
        device_stats[device]['total'] += 1
        if zone['controllable']:
            device_stats[device]['controllable'] += 1
    
    print(f"\n📱 BY DEVICE TYPE (showing patterns):")
    for device, stats in sorted(device_stats.items(), key=lambda x: x[1]['total'], reverse=True)[:10]:
        rate = stats['controllable'] / stats['total'] * 100 if stats['total'] > 0 else 0
        print(f"  {device:20} | {stats['controllable']}/{stats['total']} ({rate:.0f}%)")
    
    # Show error patterns
    error_patterns = {}
    for zone in tested_zones:
        if not zone['controllable'] and zone['error']:
            error = zone['error']
            if error not in error_patterns:
                error_patterns[error] = 0
            error_patterns[error] += 1
    
    print(f"\n❌ ERROR PATTERNS:")
    for error, count in sorted(error_patterns.items(), key=lambda x: x[1], reverse=True):
        print(f"  \"{error}\" | {count} zones")
    
    # Show controllable examples
    if controllable_zones:
        print(f"\n✅ CONTROLLABLE ZONES EXAMPLES:")
        for zone in controllable_zones[:5]:
            print(f"  {zone['zone_name']} | {zone['streaming_type']} | {zone['device_name'][:30]}")
    
    print(f"\n🎯 KEY FINDINGS:")
    
    # Find patterns in streaming types
    controllable_streaming_types = {st for st, stats in streaming_stats.items() 
                                  if stats['controllable'] > 0}
    uncontrollable_streaming_types = {st for st, stats in streaming_stats.items() 
                                    if stats['controllable'] == 0 and stats['total'] > 0}
    
    if controllable_streaming_types:
        print(f"  • StreamingTypes that work: {', '.join(controllable_streaming_types)}")
    if uncontrollable_streaming_types:
        print(f"  • StreamingTypes that DON'T work: {', '.join(uncontrollable_streaming_types)}")
    
    # Device analysis
    device_success_rates = {device: stats['controllable'] / stats['total'] 
                          for device, stats in device_stats.items() if stats['total'] > 2}
    
    if any(rate > 0 for rate in device_success_rates.values()):
        working_devices = [device for device, rate in device_success_rates.items() if rate > 0]
        print(f"  • Device types that have working zones: {', '.join(working_devices[:5])}")
    
    most_common_error = max(error_patterns.keys(), key=lambda x: error_patterns[x]) if error_patterns else None
    if most_common_error:
        print(f"  • Most common error: \"{most_common_error}\" ({error_patterns[most_common_error]} zones)")
    
    print(f"\n💡 CONCLUSION:")
    if len(controllable_zones) == 0:
        print("  • NO zones are controllable via API")
        print("  • This suggests all zones are trial/demo or lack API control permissions")
    elif len(controllable_zones) < len(tested_zones) * 0.1:
        print("  • Very few zones are controllable (<10%)")
        print("  • Most zones appear to be trial/demo or restricted")
    else:
        print(f"  • {len(controllable_zones)/len(tested_zones)*100:.0f}% of zones are controllable")
        print("  • Control is determined by subscription/permission level, NOT device type")

if __name__ == "__main__":
    test_sample_zones()
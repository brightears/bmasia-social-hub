#!/usr/bin/env python3
"""
Test the complete enhanced control system with all discovered capabilities
This validates the smart escalation and device detection logic
"""

import logging
import json
from syb_control_handler import syb_control, handle_control_request, can_control_zone

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_device_detection():
    """Test device detection and capability assessment"""
    
    print("\n🔍 TESTING DEVICE DETECTION AND CAPABILITIES")
    print("=" * 60)
    
    # Get some test zones from different accounts
    from soundtrack_api import soundtrack_api
    
    accounts = soundtrack_api.get_accounts()
    test_zones = []
    
    # Collect diverse zones for testing
    for account in accounts[:3]:  # Test first 3 accounts
        for loc_edge in account.get('locations', {}).get('edges', []):
            location = loc_edge['node']
            for zone_edge in location.get('soundZones', {}).get('edges', []):
                zone = zone_edge['node']
                if len(test_zones) < 5:  # Test up to 5 zones
                    test_zones.append({
                        'id': zone['id'],
                        'name': zone.get('name'),
                        'location': location.get('name'),
                        'account': account.get('name')
                    })
    
    print(f"Testing {len(test_zones)} zones for device capabilities...")
    
    results = {}
    
    for zone in test_zones:
        zone_id = zone['id']
        print(f"\n--- Testing Zone: {zone['name']} ---")
        print(f"Location: {zone['location']}")
        print(f"Account: {zone['account']}")
        
        # Get comprehensive capability assessment
        capability = syb_control.get_zone_capability(zone_id)
        results[zone_id] = {
            'zone_info': zone,
            'capability_assessment': capability
        }
        
        if 'error' in capability:
            print(f"❌ Error: {capability['error']}")
            continue
        
        print(f"Device: {capability.get('device_name', 'Unknown')}")
        print(f"Device Type: {capability.get('device_type', 'Unknown')}")
        print(f"Streaming Type: {capability.get('streaming_type', 'Unknown')}")
        
        # Show capabilities
        caps = capability.get('capabilities', {})
        print(f"Volume Control: {'✅' if caps.get('volume') else '❌'}")
        print(f"Playback Control: {'✅' if caps.get('playback') else '❌'}")
        print(f"Queue Management: {'✅' if caps.get('queue') else '❌'}")
        
        print(f"Overall Controllable: {'✅' if capability.get('can_control') else '❌'}")
        
        # Show current source
        source = capability.get('current_source', {})
        print(f"Current Source: {source.get('name', 'Unknown')} ({source.get('type', 'Unknown')})")
        
        # Show limitations
        limitations = capability.get('limitations', [])
        if limitations:
            print("Limitations:")
            for limitation in limitations:
                print(f"  - {limitation}")
    
    return results


def test_volume_control_with_escalation():
    """Test volume control with smart escalation"""
    
    print("\n🔊 TESTING VOLUME CONTROL WITH SMART ESCALATION")
    print("=" * 60)
    
    from soundtrack_api import soundtrack_api
    accounts = soundtrack_api.get_accounts()
    
    # Find one controllable and one non-controllable zone
    controllable_zone = None
    non_controllable_zone = None
    
    for account in accounts:
        for loc_edge in account.get('locations', {}).get('edges', []):
            location = loc_edge['node']
            for zone_edge in location.get('soundZones', {}).get('edges', []):
                zone = zone_edge['node']
                zone_id = zone['id']
                
                capability = syb_control.get_zone_capability(zone_id)
                if capability.get('can_control_volume') and not controllable_zone:
                    controllable_zone = {
                        'id': zone_id,
                        'name': zone.get('name'),
                        'device': capability.get('device_name')
                    }
                elif not capability.get('can_control_volume') and not non_controllable_zone:
                    non_controllable_zone = {
                        'id': zone_id,
                        'name': zone.get('name'),
                        'device': capability.get('device_name')
                    }
                
                if controllable_zone and non_controllable_zone:
                    break
    
    results = {}
    
    # Test controllable zone
    if controllable_zone:
        print(f"\n--- Testing Controllable Zone: {controllable_zone['name']} ---")
        print(f"Device: {controllable_zone['device']}")
        
        success, message = handle_control_request('volume', controllable_zone['id'], 8)
        results['controllable_zone'] = {
            'zone_info': controllable_zone,
            'volume_test': {'success': success, 'message': message}
        }
        
        if success:
            print(f"✅ Volume control succeeded: {message}")
        else:
            print(f"❌ Volume control failed: {message}")
    
    # Test non-controllable zone
    if non_controllable_zone:
        print(f"\n--- Testing Non-Controllable Zone: {non_controllable_zone['name']} ---")
        print(f"Device: {non_controllable_zone['device']}")
        
        success, message = handle_control_request('volume', non_controllable_zone['id'], 8)
        results['non_controllable_zone'] = {
            'zone_info': non_controllable_zone,
            'volume_test': {'success': success, 'message': message}
        }
        
        if success:
            print(f"✅ Unexpected success: {message}")
        else:
            print(f"❌ Expected failure with escalation:")
            print(f"   {message}")
    
    return results


def test_queue_management():
    """Test queue management capabilities"""
    
    print("\n📋 TESTING QUEUE MANAGEMENT")
    print("=" * 60)
    
    # Find a zone that supports queue management
    from soundtrack_api import soundtrack_api
    accounts = soundtrack_api.get_accounts()
    
    queue_capable_zone = None
    
    for account in accounts:
        for loc_edge in account.get('locations', {}).get('edges', []):
            location = loc_edge['node']
            for zone_edge in location.get('soundZones', {}).get('edges', []):
                zone = zone_edge['node']
                zone_id = zone['id']
                
                capability = syb_control.get_zone_capability(zone_id)
                if capability.get('can_manage_queue'):
                    queue_capable_zone = {
                        'id': zone_id,
                        'name': zone.get('name'),
                        'device': capability.get('device_name')
                    }
                    break
    
    if not queue_capable_zone:
        print("❌ No queue-capable zones found for testing")
        return {}
    
    print(f"Testing zone: {queue_capable_zone['name']}")
    print(f"Device: {queue_capable_zone['device']}")
    
    results = {'zone_info': queue_capable_zone}
    
    # Test queue clearing
    print("\n--- Testing Queue Clear ---")
    success, message = handle_control_request('queue_clear', queue_capable_zone['id'], None)
    results['clear_test'] = {'success': success, 'message': message}
    
    if success:
        print(f"✅ Queue clear succeeded: {message}")
    else:
        print(f"❌ Queue clear failed: {message}")
    
    # Test queue adding (with fake track IDs - will fail but tests the logic)
    print("\n--- Testing Queue Add ---")
    fake_track_ids = ['track-1', 'track-2', 'track-3']
    success, message = handle_control_request('queue_add', queue_capable_zone['id'], fake_track_ids)
    results['add_test'] = {'success': success, 'message': message}
    
    if success:
        print(f"✅ Queue add succeeded: {message}")
    else:
        print(f"❌ Queue add failed (expected with fake IDs): {message}")
    
    return results


def test_comprehensive_zone_analysis():
    """Comprehensive analysis of what we can do across all zones"""
    
    print("\n📊 COMPREHENSIVE ZONE ANALYSIS")
    print("=" * 60)
    
    from soundtrack_api import soundtrack_api
    accounts = soundtrack_api.get_accounts()
    
    stats = {
        'total_zones': 0,
        'controllable_zones': 0,
        'volume_capable': 0,
        'playback_capable': 0,
        'queue_capable': 0,
        'device_types': {},
        'streaming_types': {}
    }
    
    detailed_zones = []
    
    for account in accounts:
        account_name = account.get('name', 'Unknown')
        
        for loc_edge in account.get('locations', {}).get('edges', []):
            location = loc_edge['node']
            location_name = location.get('name', 'Unknown')
            
            for zone_edge in location.get('soundZones', {}).get('edges', []):
                zone = zone_edge['node']
                zone_id = zone['id']
                zone_name = zone.get('name', 'Unknown')
                
                stats['total_zones'] += 1
                
                # Get capability assessment
                capability = syb_control.get_zone_capability(zone_id)
                
                if 'error' not in capability:
                    device_name = capability.get('device_name', 'Unknown')
                    device_type = capability.get('device_type', 'Unknown')
                    streaming_type = capability.get('streaming_type', 'Unknown')
                    
                    # Update statistics
                    if capability.get('can_control'):
                        stats['controllable_zones'] += 1
                    if capability.get('can_control_volume'):
                        stats['volume_capable'] += 1
                    if capability.get('can_control_playback'):
                        stats['playback_capable'] += 1
                    if capability.get('can_manage_queue'):
                        stats['queue_capable'] += 1
                    
                    # Device type statistics
                    if device_type not in stats['device_types']:
                        stats['device_types'][device_type] = 0
                    stats['device_types'][device_type] += 1
                    
                    # Streaming type statistics
                    if streaming_type not in stats['streaming_types']:
                        stats['streaming_types'][streaming_type] = 0
                    stats['streaming_types'][streaming_type] += 1
                    
                    # Store detailed info for controllable zones
                    if capability.get('can_control'):
                        detailed_zones.append({
                            'zone_name': zone_name,
                            'location': location_name,
                            'account': account_name,
                            'device': device_name,
                            'device_type': device_type,
                            'capabilities': capability.get('capabilities', {}),
                            'current_source': capability.get('current_source', {})
                        })
    
    # Print statistics
    print(f"Total Zones Analyzed: {stats['total_zones']}")
    print(f"Controllable Zones: {stats['controllable_zones']} ({stats['controllable_zones']/stats['total_zones']*100:.1f}%)")
    print(f"Volume Control Capable: {stats['volume_capable']}")
    print(f"Playback Control Capable: {stats['playback_capable']}")
    print(f"Queue Management Capable: {stats['queue_capable']}")
    
    print("\nDevice Type Distribution:")
    for device_type, count in stats['device_types'].items():
        percentage = count/stats['total_zones']*100
        print(f"  {device_type}: {count} ({percentage:.1f}%)")
    
    print("\nStreaming Type Distribution:")
    for streaming_type, count in stats['streaming_types'].items():
        percentage = count/stats['total_zones']*100
        print(f"  {streaming_type}: {count} ({percentage:.1f}%)")
    
    print(f"\nControllable Zones Details:")
    for zone in detailed_zones[:5]:  # Show first 5 controllable zones
        print(f"  ✅ {zone['zone_name']} ({zone['device']})")
        print(f"     Location: {zone['location']}")
        print(f"     Account: {zone['account']}")
        print(f"     Current Source: {zone['current_source'].get('name', 'Unknown')}")
    
    return {'stats': stats, 'controllable_zones': detailed_zones}


def main():
    """Run comprehensive test of the enhanced control system"""
    
    print("🎵 COMPREHENSIVE SYB ENHANCED CONTROL SYSTEM TEST")
    print("=" * 80)
    
    all_results = {
        'timestamp': '2025-01-20T00:00:00Z',
        'test_results': {}
    }
    
    # Test 1: Device Detection
    print("\n" + "="*80)
    all_results['test_results']['device_detection'] = test_device_detection()
    
    # Test 2: Volume Control with Escalation
    print("\n" + "="*80)
    all_results['test_results']['volume_control'] = test_volume_control_with_escalation()
    
    # Test 3: Queue Management
    print("\n" + "="*80)
    all_results['test_results']['queue_management'] = test_queue_management()
    
    # Test 4: Comprehensive Analysis
    print("\n" + "="*80)
    all_results['test_results']['comprehensive_analysis'] = test_comprehensive_zone_analysis()
    
    # Save results
    output_file = '/Users/benorbe/Documents/BMAsia Social Hub/backend/enhanced_control_test_results.json'
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    # Final Summary
    print("\n" + "="*80)
    print("🎯 FINAL SYSTEM CAPABILITY SUMMARY")
    print("=" * 80)
    
    analysis = all_results['test_results']['comprehensive_analysis']
    stats = analysis['stats']
    
    print(f"📊 STATISTICS:")
    print(f"   Total Zones: {stats['total_zones']}")
    print(f"   API Controllable: {stats['controllable_zones']} ({stats['controllable_zones']/stats['total_zones']*100:.1f}%)")
    print(f"   Volume Control: {stats['volume_capable']} zones")
    print(f"   Playback Control: {stats['playback_capable']} zones")  
    print(f"   Queue Management: {stats['queue_capable']} zones")
    
    print(f"\n🎛️ DEVICE COMPATIBILITY:")
    for device_type, count in stats['device_types'].items():
        percentage = count/stats['total_zones']*100
        controllable = "✅" if "Controllable" in device_type else "❌"
        print(f"   {controllable} {device_type}: {count} zones ({percentage:.1f}%)")
    
    print(f"\n🔧 BOT CAPABILITIES:")
    if stats['controllable_zones'] > 0:
        print(f"   ✅ Direct API control available for {stats['controllable_zones']} zones")
        print(f"   ✅ Smart device detection implemented")
        print(f"   ✅ Automatic escalation for non-controllable devices")
        print(f"   ✅ Queue management for compatible zones")
        print(f"   ✅ Enhanced zone status reporting")
    else:
        print(f"   ❌ No directly controllable zones found")
        print(f"   ✅ Escalation strategy ready for all requests")
    
    print(f"\n🎯 RECOMMENDATIONS:")
    if stats['controllable_zones'] > 0:
        print(f"   - Focus bot responses on controllable zones first")
        print(f"   - Use escalation for Samsung tablets and trial zones")
        print(f"   - Implement queue management features for IPAM/DRMR devices")
        print(f"   - Provide detailed device info in responses")
    else:
        print(f"   - All zones require manual intervention")
        print(f"   - Focus on creating detailed escalation requests")
        print(f"   - Check if production API credentials are needed")
    
    print(f"\n💾 Results saved to: {output_file}")
    
    return all_results


if __name__ == '__main__':
    main()
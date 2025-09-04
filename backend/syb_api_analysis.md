# Soundtrack Your Brand API Analysis

## Executive Summary

After comprehensive testing of the SYB API with current credentials and available zones, here are the **actual capabilities**:

### ✅ What We CAN Do

#### 1. **Detection Capabilities**
- **Zone Discovery**: Find zones by venue name across all accessible accounts (50+ accounts, 14+ zones)
- **Basic Zone Info**: Get zone ID, name, streaming type, device info, schedule presence
- **Account Structure**: Access business names, locations, and zone hierarchies
- **Device Status**: Detect device name and basic connectivity (though not online/offline status)
- **Schedule Detection**: Determine if a zone has a schedule assigned (manual vs scheduled mode detection)

#### 2. **Limited Status Monitoring**
- **Streaming Type**: Detect tier level (TIER_3 seen in testing)
- **Schedule Name**: Get assigned schedule name for zones
- **Playback Object**: Can detect presence of nowPlaying object (but not contents)

### ❌ What We CANNOT Do

#### 1. **Real-Time Control**
- **Volume Control**: All volume mutations return "Not found" - zones not controllable
- **Playback Control**: Play/pause/skip mutations fail with "Not found" errors
- **Playlist Switching**: No accessible playlist switching capabilities

#### 2. **Detailed Status Information**
- **Current Track**: Cannot get track name, artist, album details
- **Playing Status**: Cannot determine if music is actually playing or paused  
- **Volume Levels**: Cannot read current volume settings
- **Playback Position**: Cannot get track position or duration

#### 3. **Playlist Management**
- **Playlist Search**: No searchPlaylists query available
- **Playlist Browse**: No browsePlaylists or general playlists queries
- **Playlist Discovery**: Cannot explore the thousands of SYB pre-designed playlists

#### 4. **Schedule Management**
- **Schedule Entries**: Cannot read schedule details, times, or assigned playlists
- **Active Entry Detection**: Cannot determine which schedule entry is currently active
- **Schedule Modification**: No schedule editing capabilities

## Root Cause Analysis

### API Limitations vs Account Limitations

The investigation reveals that limitations stem from **account/zone type restrictions** rather than API capabilities:

1. **Zone Type**: Testing zones are "Trial Zone" with TIER_3 streaming type
2. **Device Type**: Connected to "ADES's iPad 2" - appears to be a trial/demo device
3. **Account Level**: While we can access 50+ accounts, most appear to be trial or limited accounts

### API Schema vs Available Operations

The GraphQL schema shows that control mutations exist (`play`, `pause`, `setVolume`, `skipTrack`) but return "Not found" errors, indicating:
- **Mutations exist** but are not accessible for our specific zones/accounts
- **Permission restrictions** based on account type or zone configuration
- **Device compatibility** requirements not met by trial zones

## Implementation Recommendations

### 1. **Immediate Capabilities (Can Implement Now)**

```python
# Zone discovery and basic status
def detect_venue_zones(venue_name: str) -> List[Dict]:
    """Find zones for venue with basic info"""
    zones = soundtrack_api.find_venue_zones(venue_name)
    for zone in zones:
        # Can reliably get:
        # - zone['name']
        # - zone['account_name'] 
        # - zone['location_name']
        # - Basic device info
        # - Schedule presence
    return zones

def detect_playback_mode(zone_id: str) -> str:
    """Detect if zone is in scheduled or manual mode"""
    # Query zone schedule presence
    # Return "scheduled" or "manual"
```

### 2. **Bot Conversation Capabilities**

The bot can currently:
- **Venue Discovery**: "I found 3 zones for Hilton Bangkok: Lobby, Restaurant, Pool Area"
- **Basic Status**: "The Lobby zone has a device connected and is in scheduled mode"
- **Zone Identification**: Help identify the correct zone when multiple zones exist
- **Account Navigation**: Direct users to the right account/location structure

### 3. **Escalation Workflows**

For actual control operations, implement escalation:

```python
def request_music_change(venue_name: str, zone_name: str, request: str) -> str:
    """Handle music change requests via human escalation"""
    
    # 1. Find and identify the zone
    zones = find_venue_zones(venue_name)
    target_zone = find_best_match(zones, zone_name)
    
    if not target_zone:
        return "❌ Could not find that zone. Available zones: ..."
    
    # 2. Create escalation request
    escalation_msg = f"""
    🎵 MUSIC CHANGE REQUEST
    
    Venue: {venue_name}
    Zone: {target_zone['name']} 
    Location: {target_zone['location_name']}
    Device: {target_zone.get('device_name', 'Unknown')}
    
    Request: {request}
    
    Zone ID: {target_zone['id']}
    Account: {target_zone['account_name']}
    """
    
    # 3. Send to Google Chat operations channel
    send_to_operations_team(escalation_msg)
    
    return f"✅ Music change request submitted for {zone_name}. The team will handle this within 15 minutes."
```

### 4. **Future Development Path**

To unlock control capabilities, we need:

1. **Production Account Access**: Move beyond trial zones to actual venue accounts
2. **Device Verification**: Ensure zones have compatible playback devices (not trial iPads)
3. **Permission Elevation**: Request elevated API permissions for control operations
4. **Alternative Integration**: Consider SYB's management interface APIs or direct zone control

### 5. **Playlist Discovery Alternative**

Since direct playlist search isn't available, implement:

```python
def suggest_playlists_by_category(venue_type: str, mood: str) -> List[str]:
    """Suggest playlists based on venue type and mood"""
    # Use static mapping of known good playlists
    # Based on SYB's public playlist categories
    
    suggestions = {
        'hotel_lobby': {
            'morning': ['Gentle Morning', 'Soft Acoustic', 'Light Jazz'],
            'evening': ['Ambient Lounge', 'Smooth Jazz', 'Chill Electronica']
        },
        'restaurant': {
            'lunch': ['Bossa Nova', 'Indie Folk', 'World Music'],  
            'dinner': ['Jazz Standards', 'Soul & R&B', 'Acoustic Covers']
        }
        # ... more mappings
    }
    
    return suggestions.get(venue_type, {}).get(mood, ['Contact team for recommendations'])
```

## Final Recommendation

**Implement a hybrid approach:**

1. **Detection & Navigation** (Available Now):
   - Use current API for zone discovery and basic status
   - Help users identify correct zones and accounts
   - Detect scheduled vs manual modes

2. **Request & Escalation** (Implement Immediately):
   - Create structured escalation workflow for actual changes
   - Generate specific requests with zone IDs for operations team
   - Track request status and follow-up

3. **Future Enhancement** (Requires Account Upgrade):
   - Work with SYB to get production account access
   - Test control capabilities with real venue zones
   - Implement direct control once permissions are available

This approach enables immediate value while building toward full automation as account access improves.

## Sample Bot Implementation

```python
@bot_command("change music")
def handle_music_change_request(venue: str, zone: str, request: str):
    # 1. Find zone
    zones = soundtrack_api.find_venue_zones(venue)
    
    if not zones:
        return f"❌ I couldn't find any zones for {venue}. Let me check our venue list..."
    
    # 2. Show available zones if multiple found
    if len(zones) > 1:
        zone_list = "\n".join([f"- {z['name']} ({z['location_name']})" for z in zones])
        return f"I found multiple zones for {venue}:\n{zone_list}\n\nWhich specific zone needs the music changed?"
    
    # 3. Detect current mode
    target_zone = zones[0]
    current_mode = detect_playback_mode(target_zone['id'])
    
    # 4. Create escalation with context
    escalation_request = create_music_change_request(target_zone, request, current_mode)
    
    # 5. Send to operations
    send_to_operations_channel(escalation_request)
    
    return f"✅ Music change request submitted for {target_zone['name']} at {venue}. The team will handle this within 15 minutes."
```

This provides immediate business value while working within current API constraints.
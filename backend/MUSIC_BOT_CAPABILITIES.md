# BMA Social Music Bot Capabilities

Last Updated: 2025-01-04

## Overview

The bot intelligently handles two different music platforms with platform-specific approaches:

## 1. Soundtrack Your Brand (SYB) Venues

### What the Bot CAN Do:

#### ✅ Detection & Monitoring
- Find zones by venue name
- Check zone online/offline status  
- Detect if zone has a schedule
- Identify scheduled vs manual mode
- Retrieve playlist history (past 3 weeks)
- Show current playlist name (but not track details)

#### ✅ Schedule Analysis
- Retrieve weekly schedule if configured
- Show today's playlist rotation
- Analyze schedule patterns
- Provide design insights based on:
  - Playlist variety
  - Weekend vs weekday differences
  - Volume recommendations
  - Historical patterns

#### ✅ Design Conversations
- Suggest mood-appropriate playlists
- Time-aware recommendations (morning/afternoon/evening)
- Venue-type specific suggestions (bar/restaurant/lobby/spa)
- Structured escalation to design team

### What the Bot CAN Do (with compatible devices):

#### ✅ Volume Control (CONFIRMED WORKING!)
- **CAN adjust volume** on zones with IPAM400 devices
- Uses 0-16 scale (SYB standard)
- Instant changes via API
- Automatic device compatibility checking

### What the Bot CANNOT Do (Current Limitations):

#### ❌ Limited Control
- Cannot change playlists programmatically (yet)
- Cannot switch between scheduled/manual modes
- Cannot pause/resume playback  
- Cannot access full playlist catalog
- Cannot see current track details
- **Cannot control Samsung tablet zones** (display-only devices)

### Smart Workaround:
```
Customer: "Music is too boring"
Bot: Suggests 5 energetic playlists
Customer: "Yes, change it"
Bot: Notifies design team via Google Chat
Design Team: Implements in SYB dashboard within 30 mins
```

---

## 2. Beat Breeze Venues

### Characteristics:
- **NO API AVAILABLE** - Cannot check real-time status
- Design specifications stored in `music_design.md`
- Shows what SHOULD be playing (not what IS playing)
- Venue staff must check/adjust on-site

### Bot Response for Beat Breeze:
```
📋 Beat Breeze Design for [Zone]:
Current time slot:
• Playlist: Morning Vibes
• Energy: Low
• Volume: Level 8

Note: Beat Breeze designs are managed directly. 
Contact your venue manager for schedule changes.
(Cannot verify actual playback - no API available)
```

---

## Implementation Architecture

### Key Files:

1. **bot_simplified.py**
   - Main bot logic
   - Handles conversations
   - Routes to appropriate handlers

2. **music_monitor.py**
   - Checks zone status
   - Retrieves schedules
   - Gets playlist history
   - Platform detection (SYB vs Beat Breeze)

3. **syb_control_handler.py**
   - Manages SYB control attempts
   - Provides playlist suggestions
   - Creates escalation requests
   - Mood-based recommendations

4. **music_design.md**
   - Beat Breeze design specs only
   - No SYB data (managed in customer accounts)

5. **venue_data.md**
   - Venue information
   - Contact details
   - Platform identification

---

## Conversation Examples

### 1. Status Check (SYB)
```
Customer: "What's playing at Drift Bar?"

Bot: 📊 Current status for Drift Bar:
     🎵 Now playing: Pool Party Vibes
     🔊 Volume level: 11/16
     
     📋 Weekly Schedule (Summer Schedule):
     Today (Thursday):
     • 11:00-14:00: Chill Lunch Vibes
     • 14:00-18:00: Afternoon Energy
     
     📅 Past 3 weeks insights:
     Most played: Pool Party Vibes
```

### 2. Design Change Request
```
Customer: "We need more energy at the bar"

Bot: 🎨 Music Design Consultation
     
     💡 Playlist Suggestions:
     1. Happy Hour Hits
     2. Tropical House
     3. Beach Bar
     
     Would you like me to request this change?

Customer: "Yes"

Bot: ✅ I've forwarded to our design team.
     Changes will be live within 30 minutes.
```

### 3. Volume Control (NOW WORKING!)
```
Customer: "Music is too loud in the lobby"

Bot: Current volume level is 12/16.
     Would you like me to adjust the volume?

Customer: "Yes, lower it please"

Bot: ✅ I've adjusted the volume at Lobby to level 8/16.
     Changes should take effect immediately.
```

**Note**: For Samsung tablet zones (display-only):
```
Bot: This zone uses a display-only device (Samsung SM-X200).
     Volume must be adjusted on the device itself or through your SYB dashboard.
```

---

## Google Chat Notifications

When manual action is needed, the bot sends structured requests:

```
🎨 Music Design Change Request

Venue: Hilton Pattaya
Zone: Drift Bar
Requested mood: energetic

Customer approved playlists:
  1. Happy Hour Hits
  2. Tropical House

Requested at: 2025-01-04 15:30
Action needed: Update in SYB dashboard
```

---

## Future Enhancements

When SYB API access improves:
1. Direct playlist switching
2. Real-time volume control
3. Schedule modification
4. Playback control (play/pause)
5. Browse full playlist catalog

Current workaround provides value while building toward full automation.
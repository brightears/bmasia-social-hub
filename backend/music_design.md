# Music Design Schedules (Beat Breeze Venues Only)

**IMPORTANT NOTES:**
- **Beat Breeze has NO API** - We cannot check real-time status
- **This file contains DESIGN SPECIFICATIONS ONLY** - Not live data
- **For Soundtrack Your Brand (SYB) venues:** We use live API data with schedules and history

Last Updated: 2025-09-04

## Beat Breeze Venues

Beat Breeze is our proprietary music platform. Since there's no API:
- Bot can only show what SHOULD be playing (from this file)
- Cannot verify what IS actually playing
- Venue staff must manually check/adjust on-site

### Example: [Venue Name]
#### Zone: [Zone Name]

**Schedule Design**
| Time | Playlist | Energy | Volume Level (0-16) | Notes |
|------|----------|---------|---------------------|--------|
| 09:00-12:00 | Morning Vibes | Low | 8 | Gentle start |
| 12:00-18:00 | Afternoon Energy | Medium | 10 | Upbeat |
| 18:00-23:00 | Evening Sessions | Medium-High | 11 | Dynamic |

---

## SYB Venues (For Reference Only)

Soundtrack Your Brand venues are NOT tracked here. The bot will:
- Check live status via SYB API
- Review playlist history (past 3 weeks)
- Report current playing information
- Show volume levels and zone status

No design comparison is performed for SYB venues.

---

## Design Guidelines (Beat Breeze Only)

### Energy Levels
- **Low**: Ambient, gentle (morning, late night)
- **Medium**: Balanced, conversational (afternoon)
- **High**: Energetic, party (peak hours)

### Volume Guidelines (0-16 scale)
- **Quiet zones**: 6-8 (lobbies, restaurants)
- **Standard zones**: 9-11 (bars, lounges)  
- **Active zones**: 12-14 (dance floors, pool areas)
- **Late night reduction**: -2 levels after 22:00

---

## Contact for Music Changes
- **Beat Breeze Design Team**: design@bmasiamusic.com
- **SYB Issues**: Handled directly via customer's SYB account
- **Escalation**: Operations on WhatsApp
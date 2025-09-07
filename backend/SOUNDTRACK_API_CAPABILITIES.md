# Soundtrack Your Brand API - Technical Capabilities Report

## Executive Summary
The Soundtrack Your Brand v2 API is designed for **authorized staff control only**, not for customer-facing "jukebox" functionality. Due to licensing restrictions, visitors/customers are explicitly prohibited from controlling playback.

## API Capabilities Matrix

### ✅ SUPPORTED - What the Bot CAN Do

| Feature | API Support | Details |
|---------|------------|---------|
| **Access Zones & See What's Playing** | YES | Via queries and subscriptions (read-only) |
| **Adjust Volume** | YES | `setVolume` mutation with soundZone ID |
| **Skip Songs** | YES | `skip` mutation |
| **Pause/Play Playback** | YES | `play/pause` mutations |
| **Get Current Track Info** | YES | Track name, artist(s), album art |
| **Monitor Zone Status** | YES | Zone connectivity, playback state |

### ❌ NOT SUPPORTED - What the Bot CANNOT Do

| Feature | API Support | Reason |
|---------|------------|--------|
| **Change Playlists** | NO | Not supported by API |
| **Create/Edit Playlists** | NO | Deliberate design choice |
| **Access Pre-designed Playlists** | NO | Not exposed via API |
| **Suggest Playlists** | NO | Requires playlist management (unavailable) |
| **Block/Unblock Songs** | NO | Not supported by API |
| **Customer Playback Control** | NO | Licensing restrictions prohibit "jukebox" functionality |
| **Schedule Music Changes** | NO | Not available via API |
| **Access Music Library** | NO | Curated content only |

## Key Restrictions

### Legal/Licensing Constraint
> "Due to licensing restrictions, visitors are currently not allowed to control playback, meaning 'jukebox' functionality is not possible"

This is a **fundamental legal constraint**, not a technical limitation. The API's design reflects commercial music licensing agreements for background music, not on-demand selection.

### Business Model Alignment
- Soundtrack Your Brand provides **curated background music** for commercial use
- The service is a **content delivery platform**, not a content management system
- Allowing customer playlist manipulation would undermine the core value proposition

## Practical Implications for BMA Social Bot

### What Customers Can Request (Bot Handles):
1. "What song is currently playing?" - ✅ Bot provides info
2. "Turn up the volume" - ✅ Bot adjusts volume
3. "Skip this song" - ✅ Bot skips track
4. "Pause/Resume the music" - ✅ Bot controls playback

### What Must Be Escalated to Human Support:
1. "Change the playlist" - ❌ Escalate to support
2. "Play jazz music" - ❌ Escalate to support
3. "Block this song permanently" - ❌ Escalate to support
4. "Create a custom playlist" - ❌ Escalate to support
5. "Schedule different music for evening" - ❌ Escalate to support
6. "Redesign our music atmosphere" - ❌ Escalate to support

## Implementation Strategy

### Bot Response Flow:
1. **Controllable Requests** → Bot executes via API
2. **Playlist/Design Requests** → Bot escalates to Google Chat with "Music Design Request" tag
3. **Complex Music Curation** → Human support handles via Soundtrack dashboard

### Recommended Bot Responses for Unsupported Features:
- "I'll connect you with our music design team who can help customize your playlists."
- "Playlist changes require our specialists. Let me escalate this to them."
- "Our team will help you redesign your music atmosphere. Forwarding your request now."

## Authentication Model
- **API Token**: Service-to-service integration (what we use)
- **User Login**: For business owners/managers only
- **Customer Auth**: Not supported (deliberate restriction)

## Conclusion
The bot should focus on **real-time playback control** and **status monitoring** while escalating all playlist/curation requests to human support. This aligns with both API capabilities and Soundtrack's licensing model.
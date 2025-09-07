# CRITICAL: Soundtrack Your Brand API Limitations

## Executive Summary
**The Soundtrack Your Brand API CANNOT change playlists, block songs, or provide "jukebox" functionality.** This is a fundamental limitation due to music licensing restrictions, not a technical issue we can solve.

## What the API CAN Do (Confirmed Working)
✅ **Volume Control** - `setVolume` mutation works
✅ **Skip Tracks** - `skip` mutation works  
✅ **Pause/Resume** - `play` and `pause` mutations work
✅ **Read Status** - Can check what's playing, zone status, etc.

## What the API CANNOT Do (Confirmed Impossible)
❌ **Change Playlists** - No mutation exists for this
❌ **Block/Ban Songs** - Not supported
❌ **Access Playlist Library** - Cannot browse available playlists
❌ **Customer Control** - Visitors/customers cannot control playback (licensing restriction)
❌ **Create/Edit Playlists** - No playlist management capabilities

## The Legal Reality
From the official documentation:
> "Due to licensing restrictions, visitors are currently not allowed to control playback, meaning 'jukebox' functionality is not possible"

This is because:
1. Soundtrack Your Brand has commercial background music licenses
2. These licenses are for professionally curated music, not on-demand selection
3. Allowing customer control would violate these licensing agreements

## What This Means for Our Bot

### DO NOT:
- Promise to change playlists
- Say "Done!" when asked to change music genres
- Pretend the API can do things it cannot
- Try to work around these limitations

### INSTEAD DO:
- Be honest about limitations
- Offer to control volume, skip, pause/resume
- Suggest using the Soundtrack app for playlist changes
- Notify support team when customers need playlist changes

## Alternative Approaches

### For Venue Staff:
- They can use the official Soundtrack app
- Bot can help with volume/skip/pause controls
- Bot can monitor and report status

### For Customers:
- Bot can tell them what's playing
- Bot can notify staff of requests
- Bot CANNOT give them direct control

## Technical Notes

### The Fictional Mutation We Were Using:
```graphql
# THIS DOES NOT EXIST - DO NOT USE
mutation SetPlaylist($input: SetPlaylistInput!) {
  setPlaylist(input: $input) {
    __typename
  }
}
```

### The Real Mutation That Also Doesn't Help:
```graphql
# setPlayFrom exists but doesn't do what we need
# It's for setting playback sources, not selecting playlists
mutation SetPlayFrom($input: SetPlayFromInput!) {
  setPlayFrom(input: $input) {
    __typename
  }
}
```

## Bottom Line
**We must pivot from a "playlist control bot" to a "playback control and information bot"**. Any attempt to make the bot change playlists is fighting against fundamental API and legal limitations that cannot be overcome.

## References
- Technical Feasibility Report provided by user (January 2025)
- Soundtrack Your Brand v2 API Documentation
- Testing confirms these limitations in production
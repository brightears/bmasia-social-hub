# BMA Social Hub - System Documentation for Claude

## Current Status (Checkpoint V5 - Stable)
**Last Updated**: 2025-01-19
**Stable Commit**: f697e48 (checkpoint-v5-stable-bot)

## System Overview
BMA Social Hub is an AI-powered customer support system for BMA's music venue clients, integrating WhatsApp, LINE, and Google Chat for seamless support operations.

## Core Components

### 1. WhatsApp/LINE Bot (`backend/bot_ai_first.py`)
- **AI Model**: Google Gemini 1.5 Flash
- **Purpose**: First-line support for venue music systems
- **Capabilities**:
  - Answer product questions (licensing, features, pricing)
  - Control music via Soundtrack API (volume, skip, pause/play)
  - Check what's playing in specific zones
  - Smart escalation to human support when needed

### 2. Venue Management (`backend/venue_manager.py`)
- **Database**: `backend/venue_data.md` (923 venues, 4,342 contacts)
- **Confidence Threshold**: 90% (only explicit mentions match)
- **Key Fix**: Renamed venue "ok" to "OK Venue Bangkok" to prevent false matches

### 3. Google Chat Integration
- **Spaces**:
  - BMA Customer Support (TECHNICAL issues)
  - BMA Music Design Team (DESIGN/playlist issues)
  - BMA Sales & Finance (SALES/new customers)
- **Human Mode**: Once human responds, bot bypasses for that conversation

### 4. Soundtrack API Integration
- **Capabilities**: Volume control, skip tracks, check playing, pause/play
- **Limitations**: Cannot change playlists or block songs (licensing)

## Current Bot Behavior

### What Bot Answers Directly:
- Product information (SYB vs Beat Breeze)
- Licensing questions (PRO requirements)
- Track counts (100M+ for SYB, 30K for Beat Breeze)
- Hardware requirements
- General features and capabilities
- Music control commands for existing venues
- Contract information for verified users

### What Bot Escalates:
- **TECHNICAL**: System down, zones offline, hardware issues
- **DESIGN**: Playlist changes, event music, song blocking
- **SALES**: Demo requests, pricing quotes, new sign-ups
- **General**: Anything it cannot answer

### Key Configuration Points:
- **Confidence for venue matching**: 90% (very strict)
- **Product info extraction**: Simplified key points from product_info.md
- **Response style**: Natural, varied, no repetitive phrases
- **Meta-commentary**: Disabled for human reply enhancement

## Environment Variables (Render)
```
WHATSAPP_TOKEN=<Meta WhatsApp API token>
WHATSAPP_PHONE_NUMBER_ID=742462142273418
WHATSAPP_VERIFY_TOKEN=<verification token>
LINE_CHANNEL_ACCESS_TOKEN=<LINE API token>
LINE_CHANNEL_SECRET=<LINE secret>
GEMINI_API_KEY=<Google Gemini API key>
GOOGLE_CREDENTIALS_JSON=<Google service account JSON>
SOUNDTRACK_API_CREDENTIALS=<base64 encoded credentials>
REDIS_URL=<Redis connection URL>
```

## Recent Fixes Applied
1. ✅ Fixed incorrect licensing information in bot responses
2. ✅ Added track count information to product knowledge
3. ✅ Removed AI meta-commentary from Google Chat replies
4. ✅ Fixed department routing (new customers → Sales)
5. ✅ Bot answers general questions instead of unnecessary escalation
6. ✅ Made responses more natural, less repetitive
7. ✅ Fixed hardware/speaker information in responses
8. ✅ Prevented false venue assignments (raised threshold to 90%)
9. ✅ Fixed "ok" venue name causing false matches

## Testing Commands
```bash
# Test locally
cd backend
python main_simple.py

# Check deployment logs
python check_render_logs.py

# Deploy to Render
git push origin main
```

## Important Notes
- **Human Mode Persistence**: 24 hours or until service restart
- **Venue Confidence**: Must be 90%+ for assignment (explicit mentions only)
- **Demo Requests**: Forward to Sales (no direct link due to WhatsApp formatting)
- **CSV Export**: Use `export_venues_to_csv.py` for CRM exports

## Rollback Instructions
If issues arise, rollback to this checkpoint:
```bash
git reset --hard checkpoint-v5-stable-bot
git push --force origin main
```

## Next Potential Improvements
- Add more sophisticated venue verification questions
- Implement conversation threading for better context
- Add support for multiple languages
- Enhance AI's ability to handle complex multi-part questions
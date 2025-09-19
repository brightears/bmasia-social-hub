# BMA Social Hub - System Documentation for Claude

## Current Status (Checkpoint V7 - Database Migration Complete)
**Last Updated**: 2025-01-19
**Stable Commit**: (creating checkpoint-v7-database)

## System Overview
BMA Social Hub is an AI-powered customer support system for BMA's music venue clients, integrating WhatsApp, LINE, and Google Chat for seamless support operations. Now with high-performance PostgreSQL database backend.

## Core Components

### 1. WhatsApp/LINE Bot (`backend/bot_ai_first.py`)
- **AI Model**: Google Gemini 1.5 Flash
- **Purpose**: First-line support for venue music systems
- **Capabilities**:
  - Answer product questions (licensing, features, pricing)
  - Control music via Soundtrack API (volume, skip, pause/play)
  - Check what's playing in specific zones
  - Smart escalation to human support when needed

### 2. Venue Management (PostgreSQL Database)
- **Primary Storage**: PostgreSQL on Render (921 venues, 898 zones)
- **Fallback**: `backend/venue_data.md` (when USE_DATABASE=false)
- **Manager**: `backend/venue_manager_hybrid.py` (dual-mode support)
- **Performance**: <10ms lookups with trigram fuzzy matching
- **Confidence Threshold**: 90% (only explicit mentions match)

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
DATABASE_URL=<PostgreSQL connection string with SSL>
USE_DATABASE=true  # Switch to 'false' for instant rollback to file mode
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
10. ✅ Corrected country availability (India available, Hong Kong not)
11. ✅ Updated track library description (major + independent artists)
12. ✅ **MAJOR: Migrated to PostgreSQL database** - solved memory overflow
13. ✅ Implemented fuzzy venue matching with trigram indexes
14. ✅ Added connection pooling for high-performance queries
15. ✅ Created hybrid venue manager with instant rollback capability

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

## Database Architecture
- **PostgreSQL 16**: 921 venues, 898 zones, 8 product info records
- **Connection**: Asyncpg with 20 base + 30 overflow pool
- **Performance**: <10ms venue lookups (vs ~100ms with files)
- **Fuzzy Search**: PostgreSQL trigram similarity for typo tolerance
- **Feature Flag**: USE_DATABASE=true/false for instant mode switching
- **Files**:
  - `database_manager.py`: Async database operations
  - `venue_manager_hybrid.py`: Dual-mode venue manager
  - `database/schema.sql`: Complete PostgreSQL schema
  - `DATABASE_MIGRATION_COMPLETE.md`: Full migration details

## Rollback Instructions
If issues arise:

### Quick rollback (database to file mode):
```bash
# In Render dashboard: Set USE_DATABASE=false
# Service instantly reverts to venue_data.md
```

### Full rollback to checkpoint:
```bash
git reset --hard checkpoint-v7-database
git push --force origin main
```

Previous stable checkpoints:
- checkpoint-v7-database (creating now)
- checkpoint-v6-stable-bot (6575cd1)
- checkpoint-v5-stable-bot (f697e48)
- checkpoint-v4 (482add6)

## Next Potential Improvements
- Add Redis caching layer for hot data
- Implement conversation persistence in database
- Add venue contact management
- Create admin dashboard for venue updates
- Add database backup automation
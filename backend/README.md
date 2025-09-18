# BMA Social Backend

## Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python main_simple.py

# The service will be available at http://localhost:8000
```

## Main Components

### Core Files
- `main_simple.py` - FastAPI application entry point
- `bot_ai_first.py` - AI bot logic with Gemini integration
- `venue_manager.py` - Venue database and matching logic
- `conversation_tracker.py` - Conversation state management
- `google_chat.py` - Google Chat integration for escalations
- `reply_interface.py` - Web UI for human support replies

### Data Files
- `venue_data.md` - Venue database (923 venues)
- `product_info.md` - Product information for bot responses

### Endpoints
- `POST /webhook` - WhatsApp webhook
- `POST /line/webhook` - LINE webhook
- `GET /reply/{thread_key}` - Human reply interface
- `GET /health` - Health check

## Deployment
Deployed on Render.com with automatic deployments from main branch.

## Testing
```bash
# Check WhatsApp webhook
curl -X GET http://localhost:8000/webhook?hub.verify_token=YOUR_TOKEN

# Send test message
python test_server.py
```

## Environment Variables
See `.env.example` for required variables.

## Bot Behavior
- Answers product questions directly
- Controls music for identified venues
- Escalates complex issues to human support
- Maintains conversation context
# BMA Social Deployment Status

**Last Deployment**: September 7, 2025
**Platform**: Render.com
**Service**: bma-social-api-q9uu
**URL**: https://bma-social-api-q9uu.onrender.com
**Status**: ✅ LIVE & OPERATIONAL

## Deployment Configuration

### GitHub Integration
- **Repository**: brightears/bmasia-social-hub
- **Branch**: main
- **Auto-Deploy**: Enabled (pushes to main trigger deployment)

### Environment Variables (Configured on Render)
- ✅ `OPENAI_API_KEY` - For bot AI processing
- ✅ `GOOGLE_CREDENTIALS_JSON` - Service account for Google Chat
- ✅ `WHATSAPP_TOKEN` - Meta Business API token
- ✅ `WHATSAPP_PHONE_NUMBER_ID` - WhatsApp Business number
- ✅ `SOUNDTRACK_API_CREDENTIALS` - Music API (base64 encoded)
- ✅ `GCHAT_CUSTOMER_SUPPORT_SPACE` - spaces/AAQA1j6BK08

### Service Account
- **Email**: bma-social-chat@bmasia-social-hub.iam.gserviceaccount.com
- **Project**: bmasia-social-hub
- **Permissions**: Google Chat API enabled

## Active Features

### 1. WhatsApp Bot (bot_fresh_start.py)
- ✅ Receives and processes customer messages
- ✅ Detects urgent issues with keywords
- ✅ Escalates to Google Chat when needed
- ✅ Handles music control commands
- ✅ Maintains conversation context

### 2. Google Chat Integration (google_chat_client.py)
- ✅ Sends notifications to Customer Support space
- ✅ Includes reply buttons with thread tracking
- ✅ Routes to appropriate departments
- ✅ Priority levels for urgent issues

### 3. Reply Interface (reply_interface.py)
- ✅ Web form at `/reply/{thread_key}`
- ✅ Direct WhatsApp message sending
- ✅ Activates human mode on first reply
- ✅ Tracks conversation history

### 4. Conversation Management (conversation_tracker.py)
- ✅ Per-customer mode tracking
- ✅ Bot/human mode switching
- ✅ Thread continuity
- ✅ 24-hour activity windows

## Deployment Commands

### Manual Deploy (if needed)
```bash
# Push changes to GitHub
git add .
git commit -m "Update description"
git push origin main
# Render auto-deploys from main branch
```

### Check Deployment Status
1. Visit: https://dashboard.render.com
2. Select: bma-social-api-q9uu service
3. View: Logs tab for real-time logs

### Test Endpoints
```bash
# Health check
curl https://bma-social-api-q9uu.onrender.com/health

# Webhook verification (GET)
curl https://bma-social-api-q9uu.onrender.com/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=bma_social_2024&hub.challenge=test
```

## Troubleshooting

### If notifications aren't working:
1. Check GOOGLE_CREDENTIALS_JSON is set in Render environment
2. Verify GCHAT_CUSTOMER_SUPPORT_SPACE is correct
3. Check service account permissions in Google Cloud Console

### If replies aren't sending:
1. Verify WHATSAPP_TOKEN is set
2. Check WHATSAPP_PHONE_NUMBER_ID matches your number
3. Ensure customer sent message within 24 hours

### If bot isn't responding:
1. Check OPENAI_API_KEY is valid
2. Verify bot_fresh_start.py is imported in main_simple.py
3. Check conversation isn't in human mode

## Recent Changes
- Added urgent keyword detection at start of bot processing
- Implemented human mode per customer
- Fixed conversation tracker to store actual message text
- Added reply interface with WhatsApp integration
- Updated Google Chat to use Customer Support space

## Next Deployment
Any push to main branch will trigger automatic deployment on Render.
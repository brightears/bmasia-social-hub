# Google Chat Integration Setup Guide

## Overview
The BMA Social bot now integrates with Google Chat to automatically escalate critical issues to the BMAsia All group. Messages are categorized by department (Sales, Operations, Design, Finance) and priority levels.

## Setup Steps

### 1. Enable Google Chat API

1. Go to Google Cloud Console: https://console.cloud.google.com
2. Select your project (same one used for Sheets/Gmail)
3. Enable the Google Chat API:
   ```
   https://console.cloud.google.com/apis/library/chat.googleapis.com
   ```
4. Click "Enable"

### 2. Create a Chat Bot

1. In Google Cloud Console, go to:
   ```
   APIs & Services → Google Chat API → Configuration
   ```

2. Configure your bot:
   - **Bot name**: BMA Social Support Bot
   - **Avatar URL**: (optional, add your logo)
   - **Description**: Automated support notifications from WhatsApp/LINE
   - **Functionality**: 
     - ✓ Bot works in direct messages
     - ✓ Bot works in spaces with multiple users
   - **Connection settings**: HTTP endpoint URL (not needed for our use case)
   - **Permissions**: 
     - ✓ Bot can be added to spaces
     - ✓ Bot can send messages

3. Save the configuration

### 3. Add Bot to Your Space

1. Open Google Chat
2. Go to your "BMAsia All" space (or create one if needed)
3. Click on the space name → "Add people & apps"
4. Search for "BMA Social Support Bot"
5. Click "Add" to add the bot to the space

### 4. Get the Space ID

1. In Google Chat, go to your BMAsia All space
2. Click on the space name → "View space details"
3. Look for the Space ID (format: `spaces/AAAAXXX123456`)
4. Copy this ID

### 5. Configure Environment Variables

Add to your `.env` file:
```env
GCHAT_BMASIA_ALL_SPACE=spaces/YOUR_SPACE_ID_HERE
```

Add to Render environment variables:
```
GCHAT_BMASIA_ALL_SPACE = spaces/YOUR_SPACE_ID_HERE
```

### 6. Test the Integration

Run the test script:
```bash
python test_google_chat.py
```

This will:
- Verify API connection
- Check space access
- Test message categorization
- Optionally send a test notification

## How It Works

### Automatic Escalation
The bot automatically escalates messages containing critical keywords:
- "all zones offline" → 🔴 Critical Operations
- "system down" → 🔴 Critical Operations
- "urgent"/"emergency" → 🔴 Critical General
- "cancel" → 🔴 Critical Sales
- "unhappy customer" → 🟡 High Priority

### Message Format
Notifications appear in Google Chat with:
```
🔴 ⚙️ Operations - Hilton Pattaya
━━━━━━━━━━━━━━━━━━━━━━━━━━━
Issue Description:
All zones are offline and not playing music!

Venue Information:
• Venue: Hilton Pattaya
• Contract Expires: 2025-10-31
• Total Zones: 5
• Contact: norbert@hilton.com

Contact Information:
• Reported By: Norbert
• Phone: +66 812345678
• Platform: WhatsApp

Bot Analysis:
Bot response: I understand all zones are offline...

Received at 2024-12-02 15:30:45
```

### Department Categories
Messages are tagged with departments for easy filtering:
- 💰 **Sales**: Contract, renewal, pricing, expansion
- ⚙️ **Operations**: Technical issues, offline zones, errors
- 🎨 **Design**: Playlist, music selection, volume
- 💳 **Finance**: Payment, invoice, billing
- 📢 **General**: Other issues

### Priority Levels
- 🔴 **Critical**: Immediate attention required
- 🟡 **High**: Important but not critical
- 🟢 **Normal**: Regular notification
- ℹ️ **Info**: Informational only

## Customization

### Adding New Escalation Rules
Edit `google_chat_client.py` ROUTING_RULES:
```python
'new_keyword': (Department.SALES, Priority.HIGH),
```

### Changing Escalation Threshold
Edit the `should_escalate()` function to add/remove critical keywords.

### Multiple Spaces (Future)
To send to different spaces based on department, modify the DEPARTMENT_SPACES configuration.

## Troubleshooting

### Bot Not Sending Messages
1. Check if Google Chat API is enabled
2. Verify the space ID is correct
3. Ensure bot is added to the space
4. Check service account has Chat Bot scope

### "Cannot access space" Error
1. Bot might not be added to the space
2. Space ID might be incorrect
3. Try removing and re-adding the bot

### No Escalation Happening
1. Message might not contain critical keywords
2. Check if CHAT_AVAILABLE is True in bot logs
3. Verify environment variables are set

## Security Notes
- Bot has read-only access to send messages
- Cannot read existing messages in the space
- Only escalates based on keyword detection
- No sensitive data is logged

## Integration Points

### WhatsApp/LINE → Bot → Google Chat Flow
1. User sends message via WhatsApp/LINE
2. Bot processes with Gemini AI
3. If critical issue detected → Send to Google Chat
4. Team members in Chat space see notification
5. Bot adds "escalated" notice to user response

### Manual Escalation
You can also manually trigger escalations in code:
```python
from google_chat_client import escalate_to_chat

escalate_to_chat(
    message="Custom escalation message",
    venue_name="Hilton Pattaya",
    venue_data={'zones': 5}
)
```

## Next Steps
1. Monitor escalations in Google Chat
2. Adjust routing rules based on team feedback
3. Consider adding daily summary reports
4. Implement two-way communication (future)
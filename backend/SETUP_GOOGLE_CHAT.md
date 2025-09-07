# Google Chat Setup for BMA Social Bot

## Overview
The bot automatically sends notifications to your Google Chat space when:
- Customers request playlist changes (bot can't do this due to API limitations)
- Technical issues are reported
- Complex requests need human assistance
- Any request is beyond the bot's capabilities

## Current Status
❌ **Google Chat is NOT configured** - Notifications will not work until you complete setup

## Setup Instructions

### 1. Create a Google Cloud Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing one
3. Enable the **Google Chat API**:
   - Go to APIs & Services > Library
   - Search for "Google Chat API"
   - Click Enable

4. Create a Service Account:
   - Go to IAM & Admin > Service Accounts
   - Click "Create Service Account"
   - Name it: `bma-social-bot`
   - Grant role: `Chat Bot` (or `Editor` for full access)
   - Click "Create Key" > JSON
   - Save the downloaded JSON file

### 2. Add Service Account to Your Google Chat Space

1. Open Google Chat
2. Go to your space (e.g., "BMAsia All")
3. Click the space name at top
4. Click "Manage webhooks & bots" or "Add people & apps"
5. Add the service account email (from the JSON file)
   - Format: `bma-social-bot@your-project.iam.gserviceaccount.com`

### 3. Get Your Space ID

1. In Google Chat, click on your space
2. Click the space name at the top
3. Look for "Space ID" in the details
4. Copy this ID (format: `spaces/AAAA8kdhs_s`)

### 4. Configure the Bot

Add these to your `.env` file:

```bash
# Google Chat Configuration
GOOGLE_CREDENTIALS_JSON='paste-entire-json-content-here'
GCHAT_BMASIA_ALL_SPACE='spaces/YOUR_SPACE_ID'
```

**Important**: The `GOOGLE_CREDENTIALS_JSON` should be the entire JSON content as a single line string, like:
```bash
GOOGLE_CREDENTIALS_JSON='{"type":"service_account","project_id":"your-project","private_key_id":"...","private_key":"-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n","client_email":"...","client_id":"...","auth_uri":"...","token_uri":"...","auth_provider_x509_cert_url":"...","client_x509_cert_url":"..."}'
```

### 5. Test the Setup

Run the test script:
```bash
cd /Users/benorbe/Documents/BMAsia\ Social\ Hub/backend
source venv/bin/activate
python test_notifications.py
```

## How It Works

When customers request something the bot can't do (like changing playlists), the bot:

1. **Gives a confident response**: "I've passed this to our music design team and they'll take care of it right away!"

2. **Sends a Google Chat notification** with:
   - Department tag (🎨 Design, ⚙️ Operations, etc.)
   - Priority level (🔴 Critical, 🟡 High, 🟢 Normal)
   - Venue name and zone
   - Customer's request
   - Timestamp

3. **Your team sees** something like:
   ```
   🎨 Design | 🟢 Normal Priority
   
   Venue: Hilton Pattaya - Edge
   Request: Customer wants to play smooth jazz
   Time: 2025-01-20 14:30:00
   Platform: WhatsApp
   ```

## What Triggers Notifications

### Automatic Escalation:
- Playlist change requests (API can't do this)
- Music genre changes
- Custom playlist creation
- Special event music needs
- Technical issues (zones offline)
- Complex scheduling requests
- Contract/pricing questions

### Bot Limitations:
- Whenever the bot says "I don't know" or "I can't help"
- When requests are beyond API capabilities
- When manual intervention is needed

## Troubleshooting

### Notifications Not Sending?

1. **Check credentials exist**:
   ```bash
   grep GOOGLE_CREDENTIALS_JSON .env
   ```

2. **Check space ID is set**:
   ```bash
   grep GCHAT_BMASIA_ALL_SPACE .env
   ```

3. **Verify service account has access**:
   - Go to your Google Chat space
   - Check if the service account is listed as a member

4. **Check logs**:
   Look for these messages in bot logs:
   - ✅ "Google Chat notification sent"
   - ❌ "Google Chat not connected"

### Common Issues:

- **"Google Chat not connected"**: Missing GOOGLE_CREDENTIALS_JSON
- **"Invalid space ID"**: Wrong format for GCHAT_BMASIA_ALL_SPACE
- **"Permission denied"**: Service account not added to space
- **No notifications**: Check that google-api-python-client is installed

## Benefits

With Google Chat properly configured:
- ✅ Team gets instant notifications for customer requests
- ✅ No requests fall through the cracks
- ✅ Customers get confident responses
- ✅ Team can respond quickly to urgent issues
- ✅ Proper routing to right department (Design, Ops, Sales, etc.)

## Next Steps

After setup:
1. Run the test script to verify everything works
2. Monitor the Google Chat space for test notifications
3. Train team on responding to bot notifications
4. Consider setting up department-specific spaces for better routing
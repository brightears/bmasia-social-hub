# How to Add Google Chat Webhook to Render

Since the bot is already deployed and running on Render, you just need to add the webhook URL as an environment variable.

## Steps:

### 1. Get the Webhook URL from Google Chat

1. Open **Google Chat**
2. Go to **"BMAsia Working Group"** space  
3. Click the **space name** at the top
4. Click **"Manage webhooks"** or "Apps & integrations"
5. Find **"BMA Social Support Bot"**
6. Copy the webhook URL (looks like: `https://chat.googleapis.com/v1/spaces/AAQA3gAn8GY/messages?key=...&token=...`)

### 2. Add to Render

Option A: Using Render Dashboard (Easier)
1. Go to https://dashboard.render.com/web/srv-d2m6l0re5dus739fso30
2. Click **"Environment"** in the left sidebar
3. Click **"Add Environment Variable"**
4. Add:
   - Key: `GOOGLE_CHAT_WEBHOOK_URL`
   - Value: `<paste the webhook URL from step 1>`
5. Click **"Save Changes"**
6. The service will automatically redeploy

Option B: Using Render CLI
```bash
# If you have Render CLI installed
render env:set GOOGLE_CHAT_WEBHOOK_URL='<webhook-url>' -s srv-d2m6l0re5dus739fso30
```

### 3. Verify It's Working

After the service redeploys (takes ~2 minutes), test it:
1. Send a WhatsApp message asking to change playlists
2. Check Google Chat for the notification

## That's It!

The bot will now send notifications to Google Chat whenever:
- Customers request playlist changes
- Technical issues occur  
- Any request needs human help

## Current Status:
- ✅ Bot is deployed and running
- ✅ WhatsApp integration working
- ❌ Google Chat notifications need webhook URL
- ✅ Once you add the webhook URL, everything works!
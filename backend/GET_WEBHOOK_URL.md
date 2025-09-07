# How to Connect Google Chat to the Bot

Since you already have "BMA Social Support Bot" working in Google Chat, you just need to get its webhook URL!

## Quick Setup (2 minutes)

### Step 1: Get the Webhook URL

1. Open **Google Chat**
2. Go to **"BMAsia Working Group"** space (or wherever your bot is)
3. Click the **space name** at the top
4. Click **"Manage webhooks"** (or "Apps & integrations")
5. Find **"BMA Social Support Bot"**
6. Click the **three dots** (⋮) next to it
7. Click **"Copy webhook URL"**

The URL looks like:
```
https://chat.googleapis.com/v1/spaces/AAQA3gAn8GY/messages?key=...&token=...
```

### Step 2: Add to .env File

Add this line to your `.env` file:
```bash
GOOGLE_CHAT_WEBHOOK_URL='paste-the-webhook-url-here'
```

### Step 3: Test It!

Run this command:
```bash
cd /Users/benorbe/Documents/BMAsia\ Social\ Hub/backend
source venv/bin/activate
python3 -c "from google_chat_webhook import google_chat_webhook; print(google_chat_webhook.send_notification('Test message from bot', 'Test Venue'))"
```

If it prints `True`, you should see a message in your Google Chat!

## That's It! 🎉

Now when customers ask for things the bot can't do (like changing playlists), it will:
1. Tell them: "I've passed this to our team and they'll take care of it!"
2. Send a notification to your Google Chat space
3. Your team sees it and takes action

## If You Don't Have a Webhook Yet

If "BMA Social Support Bot" doesn't exist yet:

1. In Google Chat, go to your space
2. Click space name > "Manage webhooks"
3. Click **"Add webhook"**
4. Name it: **"BMA Social Support Bot"**
5. Copy the URL it gives you
6. Add to .env as shown above

## Troubleshooting

**No "Manage webhooks" option?**
- You need to be a space manager
- Or the space might not allow webhooks

**Webhook not sending?**
- Check the URL is complete (includes key= and token=)
- Make sure there are no extra quotes or spaces

**Want to test manually?**
```bash
curl -X POST 'YOUR_WEBHOOK_URL' \
  -H 'Content-Type: application/json' \
  -d '{"text": "Hello from BMA Social Bot!"}'
```

## How Notifications Look

When the bot sends a notification, your team sees:

```
🎨 Music Design Request
Hilton Pattaya - Edge - 2025-01-20 14:30:00

Request: Customer wants to play smooth jazz
Zones: Drift Bar, Edge, Horizon, Shore
Contact: +66891234567
Platform: WhatsApp
```

The bot automatically categorizes:
- 🎨 Music Design - playlist/music requests
- ⚙️ Operations - technical issues
- 💰 Sales - contracts/renewals
- 💳 Finance - payments/invoices
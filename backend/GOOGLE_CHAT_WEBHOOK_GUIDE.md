# Where to Find Your Google Chat Webhook URL

## Direct Links:

### Option 1: Google Chat Web
**Direct link:** https://chat.google.com

### Option 2: Gmail (if you use Chat in Gmail)
**Direct link:** https://mail.google.com/chat

## Step-by-Step Instructions:

### 1. Open Google Chat
Go to: **https://chat.google.com**

### 2. Find Your Space
- Look in the left sidebar for **"BMAsia Working Group"** 
- Or search for it in the search bar at the top
- Click on the space to open it

### 3. Access Space Settings
Once you're in the space:
- **Method 1:** Click the space name at the very top of the chat window
- **Method 2:** Click the dropdown arrow (▼) next to the space name
- **Method 3:** Click the three dots (⋮) menu → "View space details"

### 4. Find Webhooks Section
In the space details/settings, look for one of these:
- **"Manage webhooks"**
- **"Apps & integrations"** 
- **"Manage apps"**
- **"Webhooks"**

Click on it.

### 5. Find Your Bot
Look for **"BMA Social Support Bot"** in the list

### 6. Get the Webhook URL
- Click on the bot name or the three dots (⋮) next to it
- Look for options like:
  - **"Copy webhook URL"**
  - **"View configuration"**
  - **"Settings"**
- Copy the entire URL

The webhook URL looks like this:
```
https://chat.googleapis.com/v1/spaces/AAQA3gAn8GY/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=VUxK8J2vRb3K_2DF7bQgPaJpTtHQoLnAw3BjpGokyTc
```

## If You Don't See "Manage Webhooks":

### You might need to be a Space Manager:
1. Click space name → "View members"
2. Check if you're listed as "Space manager"
3. If not, ask a space manager to:
   - Either promote you to manager
   - Or copy the webhook URL for you

### Or webhooks might not be enabled:
1. Space settings → "Access settings"
2. Make sure "Allow webhooks" is turned on

## If "BMA Social Support Bot" Doesn't Exist Yet:

### Create a New Webhook:
1. In the webhooks section, click **"+ Add webhook"** or **"Create webhook"**
2. Name it: **"BMA Social Support Bot"**
3. (Optional) Add an avatar URL
4. Click **"Save"** or **"Create"**
5. Copy the webhook URL that appears

## Can't Find Anything?

### Alternative: Check with your Google Workspace Admin
If you're using Google Workspace (formerly G Suite):
- Go to: https://admin.google.com
- Apps → Google Workspace → Google Chat
- Check if webhooks are enabled for your organization

### Direct Google Chat Help:
https://support.google.com/chat/answer/7651360

## Once You Have the URL:

1. **Add it to your local .env file:**
```bash
GOOGLE_CHAT_WEBHOOK_URL='paste-the-url-here'
```

2. **Add it to Render:**
- Go to: https://dashboard.render.com/web/srv-d2m6l0re5dus739fso30/env
- Add the same environment variable
- Save and redeploy

That's it! The bot will start sending notifications to Google Chat.
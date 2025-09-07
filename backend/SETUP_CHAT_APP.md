# Set Up Google Chat App for Service Account

## The Issue
Service accounts can't be added directly to Google Chat spaces. They need to be configured as Chat apps first.

## Step-by-Step Setup

### 1. Enable Google Chat API
Go to: https://console.cloud.google.com/apis/library/chat.googleapis.com

1. Make sure you're in project: `bmasia-social-hub`
2. Click **"Enable"** if not already enabled

### 2. Configure the Chat App
Go to: https://console.cloud.google.com/apis/api/chat.googleapis.com/hangouts-chat

Or search for "Google Chat API" and click **"Configuration"**

### 3. Create/Configure Chat App

Click **"Configuration"** tab, then fill in:

#### App Details:
- **App name:** BMA Customer Support Bot
- **Avatar URL:** (leave blank or add an icon URL)
- **Description:** Handles WhatsApp customer support messages

#### Functionality:
- ✅ **Receive 1:1 messages** - Check this
- ✅ **Join spaces and group conversations** - Check this

#### Connection Settings:
Choose **"App URL"** and enter:
```
https://bma-social-api-q9uu.onrender.com/webhooks/google-chat
```

#### Permissions:
- Select: **"Specific people and groups in your domain"**
- Or: **"Everyone in your organization"**

#### Service Account:
- Select: **"This app uses a service account"**
- Choose: `bma-social-chat@bmasia-social-hub.iam.gserviceaccount.com`

### 4. Save Configuration
Click **"Save"** or **"Create"**

### 5. Add the App to Your Space

After configuring, the app should be available to add:

1. Go to "BMA Customer Support" space
2. Click **"+ Add apps"**
3. Search for **"BMA Customer Support Bot"**
4. Click **"Add to space"**

## Alternative: Simple Bot Without Receiving Messages

If you only need the bot to SEND messages (not receive), you can:

1. Skip the Chat app configuration
2. Just grant the service account permission to the space via API

But since we want two-way communication, the Chat app is needed.

## Verification

Once set up, you should see:
- The bot appears in the space as "BMA Customer Support Bot"
- It can send messages to the space
- It can receive messages when people reply

## Next Steps

After the Chat app is configured and added to the space:
1. Test sending a WhatsApp message
2. Check if notification appears in Google Chat
3. Reply in the thread
4. Check if reply goes back to WhatsApp

## Troubleshooting

If you can't find the Configuration tab:
1. Make sure Google Chat API is enabled
2. Try this direct link: https://console.cloud.google.com/apis/api/chat.googleapis.com/config
3. Or go to APIs & Services → Google Chat API → Manage → Configuration
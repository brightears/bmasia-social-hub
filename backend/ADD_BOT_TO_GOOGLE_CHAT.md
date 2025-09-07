# Add BMA Social Bot to Google Chat Space

## You're Right! We Need to Add the Bot to Your Space

The new service account `bma-social-chat@bmasia-social-hub.iam.gserviceaccount.com` needs to be added to your Google Chat space.

## Steps to Add the Bot:

### 1. Open Google Chat
Go to: https://chat.google.com

### 2. Go to Your Space
Find and open **"BMAsia Working Group"** space

### 3. Add the Bot
There are two ways:

#### Option A: Add as App (Recommended)
1. Click the space name at the top
2. Click **"Manage apps"** or **"Apps & integrations"**
3. Click **"+ Add apps"**
4. Search for **"BMA Social"** or the bot name
5. Click **"Add to space"**

#### Option B: Add Service Account Directly
1. In the space, type:
   ```
   @bma-social-chat@bmasia-social-hub.iam.gserviceaccount.com
   ```
2. Or click **"Add people & apps"** (+ icon)
3. Enter: `bma-social-chat@bmasia-social-hub.iam.gserviceaccount.com`
4. Click **"Add"**

### 4. Grant Permissions
When prompted, make sure the bot has permission to:
- Read messages
- Post messages
- Access space information

## If You Can't Find the Bot

The bot might need to be published first. In that case:

1. Go to Google Cloud Console: https://console.cloud.google.com
2. Select project: `bmasia-social-hub`
3. Go to **"Google Chat API"**
4. Configure the Chat app with:
   - Name: **BMA Social Support Bot**
   - Avatar URL: (optional)
   - Description: Handles customer support requests from WhatsApp
   - Service account: `bma-social-chat@bmasia-social-hub.iam.gserviceaccount.com`

## Test After Adding
Once added, the bot should be able to send messages to the space when:
- WhatsApp users request playlist changes
- Technical issues occur
- Human assistance is needed

## Current Status
- ✅ Service account created
- ✅ Credentials configured locally and on Render
- ❌ Bot needs to be added to Google Chat space
- ⏳ Waiting for you to add it!

Let me know once you've added it and we can test!
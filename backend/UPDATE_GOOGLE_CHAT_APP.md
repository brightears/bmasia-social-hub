# Update Google Chat App to Use New Service Account

## The Problem
The "BMA Social Support Bot" in your Google Chat space is using the OLD service account that no longer exists. We need to update it to use the new `bma-social-chat` service account.

## Steps to Update the Chat App

### 1. Go to Google Cloud Console
https://console.cloud.google.com

### 2. Select Your Project
Make sure `bmasia-social-hub` is selected

### 3. Enable and Configure Google Chat API
1. In the search bar, type **"Google Chat API"**
2. Click on **Google Chat API**
3. If not enabled, click **"Enable"**
4. Click **"Configuration"** or **"Manage"**

### 4. Configure the Chat App
You should see configuration for Chat apps. Either:

**Option A: Edit Existing App** (if you see "BMA Social Support Bot")
1. Click on the existing app
2. Update the configuration:
   - **App name:** BMA Social Support Bot
   - **Avatar URL:** (optional, can leave blank)
   - **Description:** Handles customer support from WhatsApp/LINE
   - **Functionality:** Check "Receive 1:1 messages" and "Join spaces and group conversations"
   - **Connection settings:** 
     - Select **"App URL"** or **"Cloud Pub/Sub"** 
     - For App URL: `https://bma-social-api-q9uu.onrender.com/webhooks/google-chat`
   - **Permissions:**
     - Select **"Service account"**
     - Choose: `bma-social-chat@bmasia-social-hub.iam.gserviceaccount.com`
   - **Visibility:** 
     - "Specific people and groups" 
     - Add your domain or keep it private to your organization

**Option B: Create New App** (if no existing app or can't edit)
1. Click **"+ Create"** or **"Configure a new Chat app"**
2. Fill in:
   - **App name:** BMA Social Support Bot (New)
   - **Avatar URL:** (optional)
   - **Description:** Automated notifications from WhatsApp/LINE support
   - **Functionality:** Check both message types
   - **Connection settings:** 
     - Select **"App URL"**
     - URL: `https://bma-social-api-q9uu.onrender.com/webhooks/google-chat`
   - **Permissions:**
     - Select **"Service account"**
     - Choose: `bma-social-chat@bmasia-social-hub.iam.gserviceaccount.com`

### 5. Save and Deploy
Click **"Save"** or **"Create"**

### 6. Update in Google Chat Space
1. Go back to Google Chat
2. In "BMAsia Working Group" space
3. If you created a new app:
   - Remove the old "BMA Social Support Bot"
   - Add the new one
4. If you updated the existing app:
   - It should automatically use the new service account

## Alternative: Direct API Method

Since we're using service account authentication to SEND messages (not receive), we might not need a Chat app at all. The service account can post messages directly to the space using the Chat API.

To test this:
1. Just make sure the service account `bma-social-chat@bmasia-social-hub.iam.gserviceaccount.com` has access to the space
2. Try adding it directly as a member (not as an app)

## What We're Using
- **Service Account:** `bma-social-chat@bmasia-social-hub.iam.gserviceaccount.com`
- **Space ID:** `spaces/AAQA3gAn8GY`
- **Method:** Direct API calls using service account (not webhooks)

The bot only needs to SEND messages to Google Chat, not receive them, so a full Chat app might not be necessary.
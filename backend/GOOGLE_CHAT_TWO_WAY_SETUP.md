# Enable Two-Way Communication: Google Chat ↔ WhatsApp

## The Vision
Team members can reply directly in Google Chat, and the bot will relay their response back to the WhatsApp customer. No need to switch apps!

## How It Would Work

### Customer Support Flow:
1. **Customer on WhatsApp:** "My music isn't working at Table 5"
2. **Bot sends to Google Chat:** 
   ```
   🚨 Support Request from Customer Name (+60123456789)
   Venue: Café Milano
   Issue: My music isn't working at Table 5
   [Reply to this message to respond to customer]
   ```
3. **Team member replies in Google Chat:** "Hi! I'm checking on this now. Can you try restarting the tablet?"
4. **Bot sends back via WhatsApp:** "Hi! I'm checking on this now. Can you try restarting the tablet?"

## What We Need to Set Up

### 1. Configure Chat App to Receive Messages
In Google Cloud Console:
- Enable the Chat app to receive messages
- Set up webhook URL: `https://bma-social-api-q9uu.onrender.com/webhooks/google-chat`
- Configure app to handle:
  - Direct messages (@mentions)
  - Messages in spaces
  - Thread replies

### 2. Add Webhook Endpoint
Create `/webhooks/google-chat` endpoint to:
```python
@app.post("/webhooks/google-chat")
async def handle_google_chat_message(request: Request):
    # Parse incoming Google Chat message
    # Extract the thread ID (links to original customer)
    # Get the reply text
    # Send reply back to customer via WhatsApp
```

### 3. Track Conversation Threads
Store mapping between:
- Google Chat thread ID ↔ WhatsApp conversation ID
- Customer phone number
- Active conversation state

### 4. Message Threading
When bot sends to Google Chat:
- Include customer's WhatsApp ID in message metadata
- Create a thread for each conversation
- Team replies in that thread
- Bot knows which customer to send reply to

## Implementation Steps

### Step 1: Update Google Chat App Configuration
1. Go to: https://console.cloud.google.com
2. Google Chat API → Configuration
3. Update "BMA Social Support Bot":
   - **Connection settings:** App URL
   - **URL:** `https://bma-social-api-q9uu.onrender.com/webhooks/google-chat`
   - **Permissions:** Service account + receive messages
   - **Features:** 
     - ✅ Receive 1:1 messages
     - ✅ Join spaces and group conversations

### Step 2: Create Webhook Handler
```python
# In main_simple.py or new file

@app.post("/webhooks/google-chat")
async def google_chat_webhook(request: Request):
    """Handle incoming messages from Google Chat"""
    
    data = await request.json()
    
    # Check if it's a message (not other events)
    if data.get("type") == "MESSAGE":
        message = data.get("message", {})
        text = message.get("text", "")
        thread = message.get("thread", {})
        
        # Extract customer info from thread
        thread_name = thread.get("name", "")
        
        # Look up the original WhatsApp conversation
        # (stored when we sent the notification)
        customer_phone = await get_customer_from_thread(thread_name)
        
        if customer_phone:
            # Send the reply back via WhatsApp
            await send_whatsapp_message(
                phone=customer_phone,
                message=text
            )
            
            # Confirm in Google Chat
            return {"text": "✅ Reply sent to customer"}
        else:
            return {"text": "⚠️ Could not find customer conversation"}
    
    return {"status": "ok"}
```

### Step 3: Update Notification Format
When sending notifications to Google Chat, include:
```python
def send_support_notification(customer_phone, customer_name, issue):
    message = {
        "text": f"🚨 Support Request",
        "cards": [{
            "header": {
                "title": f"Customer: {customer_name}",
                "subtitle": f"WhatsApp: {customer_phone}"
            },
            "sections": [{
                "widgets": [{
                    "textParagraph": {
                        "text": f"Issue: {issue}"
                    }
                }]
            }]
        }],
        "thread": {
            "name": f"whatsapp_{customer_phone}_{timestamp}"
        }
    }
    # Store thread mapping for replies
    store_thread_mapping(thread_name, customer_phone)
```

## Benefits

### For Support Team:
- ✅ Reply directly in Google Chat (no app switching)
- ✅ See entire conversation history in one thread
- ✅ Multiple team members can collaborate
- ✅ Faster response times

### For Customers:
- ✅ Get responses faster
- ✅ Seamless experience (still just using WhatsApp)
- ✅ Human touch when needed

### For Operations:
- ✅ All communications logged in one place
- ✅ Can track response times
- ✅ Easy handoffs between team members

## Security Considerations
- Verify Google Chat webhook signatures
- Validate that messages come from your space
- Sanitize messages before sending to WhatsApp
- Rate limit responses

## Would You Like This Feature?

This would transform the bot from a notification system into a full two-way communication bridge. Your team could handle all WhatsApp support directly from Google Chat!

Let me know if you want to implement this - it would take about 1-2 hours to set up properly.
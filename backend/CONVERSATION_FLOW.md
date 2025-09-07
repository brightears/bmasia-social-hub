# Complete Conversation Flow - BMA Social Support System
**Status**: FULLY IMPLEMENTED & WORKING
**Last Verified**: September 7, 2025

## Overview
The system now supports seamless handoff between bot and human support with conversation continuity and per-customer mode tracking.

## Flow Stages

### Stage 1: Initial Customer Message
```
Customer → WhatsApp → Bot Processing
```
- Customer sends message via WhatsApp
- Bot analyzes message for urgency/complexity
- Bot checks if conversation is already in "human mode"

### Stage 2A: Bot Can Handle (Simple Requests)
```
Bot → Direct Response → Customer
```
- Volume adjustments, skip songs, simple queries
- Bot responds directly
- Conversation stays in "bot mode"

### Stage 2B: Bot Escalates (Urgent/Complex)
```
Bot → Google Chat Notification → Support Team
```
- Urgent issues (system down, VIP events, emergency keywords)
- Complex requests (cancellations, complaints)
- Creates notification in "BMA Customer Support" space (spaces/AAQA1j6BK08)
- Includes "📝 Reply to Customer" button with thread_key
- Conversation remains in "bot mode" until support replies
- Priority levels: Critical 🔴, High 🟡, Normal 🟢, Info ℹ️

### Stage 3: Support Team Takes Over
```
Support → Reply Interface → Customer
```
1. Support clicks "Reply to Customer" button
2. Opens web form with customer info and message
3. Support types reply
4. System:
   - Sends reply DIRECTLY to customer (no bot processing)
   - **Switches conversation to "human mode"**
   - Logs conversation history

### Stage 4: Ongoing Conversation (Human Mode Active)
```
Customer → Google Chat → Support → Customer
```
When customer replies after support has taken over:
1. System detects "human mode" is active
2. **Bypasses bot completely**
3. Forwards message directly to Google Chat
4. Continues in same thread
5. Customer gets: "Your message has been received by our support team"
6. Support sees continuation in Google Chat
7. Support uses Reply button to respond
8. Cycle continues...

## Key Features

### Conversation Modes
- **Bot Mode** (default): Bot processes all messages
- **Human Mode**: Activated when support replies, all future messages go to human
- **Mode Scope**: Per customer phone number (not global)
- **Mode Duration**: 24 hours from last activity
- **Parallel Processing**: Other customers remain in bot mode

### Benefits
1. **No Conflicting Responses**: Bot doesn't interfere once human takes over
2. **Thread Continuity**: All messages stay in same Google Chat thread
3. **Context Preservation**: Support sees full conversation history
4. **Seamless Handoff**: Customer doesn't notice the transition
5. **Direct Communication**: Support replies go straight to customer

### When Conversation Ends
- After period of inactivity (24 hours)
- If support marks as resolved
- New conversations start fresh in bot mode

## Testing the Flow

1. **Customer sends urgent message** → Bot escalates to Google Chat
2. **Support clicks Reply button** → Sends response to customer
3. **Customer replies back** → Goes directly to Google Chat (not bot)
4. **Support continues conversation** → Direct back-and-forth

## Technical Details

### Mode Tracking
- Stored in `conversation_tracker`
- Per phone number basis
- Persists across messages

### Bypass Logic
```python
if conversation_tracker.is_human_mode(phone_number):
    # Forward to Google Chat
else:
    # Process with bot
```

### Reply Interface
- URL: `/reply/{thread_key}`
- Sets human mode on first reply
- Tracks all messages in conversation

## Implementation Status

### ✅ Completed Features
- Bot escalation to Google Chat
- Reply interface at `/reply/{thread_key}`
- Human mode activation on support reply
- Per-customer conversation tracking
- Message forwarding when in human mode
- Thread continuity in Google Chat
- Auto-reset after 24 hours

## Future Enhancements

1. **Manual Mode Toggle**: Let support switch between bot/human mode
2. **Auto-Resolution**: Return to bot mode after issue resolved
3. **Handoff Messages**: Custom messages when switching modes
4. **Multiple Agents**: Track which support agent is handling
5. **Satisfaction Survey**: After human conversation ends
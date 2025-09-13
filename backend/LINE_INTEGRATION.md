# Line Messaging Integration

## Overview

This integration adds Line messaging support to the BMA Social music bot while maintaining full compatibility with the existing WhatsApp functionality. Both platforms now use the same AI-powered bot (`bot_ai_first.py`) and support human handoff through Google Chat.

## Implementation Details

### New Endpoints

- **POST `/webhooks/line`**: Main Line webhook endpoint
  - Handles message events, follow/unfollow events
  - Validates webhook signatures for security
  - Processes messages through the same bot as WhatsApp

### Key Features

1. **Unified Bot Processing**: Both WhatsApp and Line messages are processed by `bot_ai_first.py`
2. **Signature Verification**: Secure webhook handling with HMAC-SHA256 signature validation
3. **Human Handoff**: Support for escalating conversations to human agents via Google Chat
4. **Platform Detection**: Automatic platform detection for proper response routing
5. **Bi-directional Communication**: Support for both reply tokens (immediate responses) and push messages

### Message Flow

1. Line sends webhook to `/webhooks/line`
2. System verifies webhook signature
3. Extracts message and user information
4. Processes message through `music_bot.process_message()`
5. Sends response back via Line API (reply or push message)

### Configuration

Required environment variables (already configured in `.env`):
```
LINE_CHANNEL_ACCESS_TOKEN=Uz6PX8p/wC68AJdHsxB77ZPdj+SfHQdKd8nUUoD06J7qW2RGb0a3WfD17+3i6vDDdm2WjiYhG1eU7a1VitaIRFhtsZT4phJie8ruzMch8WcFCmfmUAdPRbrpaGauKIB6J9Mb1bP6pxY0MpBOi4R/IgdB04t89/1O/w1cDnyilFU=
LINE_CHANNEL_SECRET=4a300933f706cbf7fe023a9dbf543eb7
```

## API Integration Points

### Line Webhook Handler (`/webhooks/line`)

Handles these event types:
- `message`: Incoming text messages from users
- `follow`: User added bot as friend (sends welcome message)
- `unfollow`: User blocked bot (logs event)

### Google Chat Integration

Updated to support both platforms:
- Detects platform from conversation metadata
- Routes replies to appropriate API (WhatsApp Graph API or Line Messaging API)
- Maintains conversation threading

## Security Features

1. **Signature Verification**: All Line webhooks are validated using HMAC-SHA256
2. **Environment Variables**: Sensitive tokens stored in environment variables
3. **Error Handling**: Comprehensive error handling with logging

## Preserved Functionality

### WhatsApp Integration (Unchanged)
- All existing WhatsApp functionality preserved
- Same webhook endpoints and verification
- Same bot processing logic
- Same Google Chat integration

### Bot Functionality (Enhanced)
- Same AI decision-making process
- Same contextual verification for sensitive data
- Same access to product info, venue data, and Soundtrack API
- Now works identically across both platforms

## Testing

Run the integration test:
```bash
python test_line_integration.py
```

This tests:
- Webhook diagnostics endpoint
- WhatsApp webhook preservation
- Line webhook structure
- Bot message API functionality

## Deployment Configuration

### Line Developer Console

1. Set webhook URL: `https://your-domain.com/webhooks/line`
2. Enable message events
3. Verify webhook signature validation

### Webhook Diagnostics

Check configuration at: `/webhook-test`

Returns:
- Webhook URLs for both platforms
- Configuration status
- Platform-specific settings

## Platform Differences

| Feature | WhatsApp | Line |
|---------|----------|------|
| User ID | Phone number | Line User ID |
| Message Format | Graph API | Line Messaging API |
| Verification | Verify token | HMAC signature |
| Profile API | Graph API | Line Profile API |
| Rich Messages | Templates | Flex messages |

## Error Handling

- Invalid signatures return HTTP 400
- Missing credentials log warnings but don't crash
- Failed API calls are logged with full error details
- Fallback responses ensure users always get a reply

## Monitoring

All Line interactions are logged with:
- Event types and processing status
- Message sending success/failure
- Profile retrieval attempts
- Signature verification results

## Future Enhancements

Potential Line-specific features to implement:
- Rich messages using Flex Message format
- Quick reply buttons
- Image/sticker handling
- Group chat support
- Rich menu implementation

## Code Structure

### New Functions in `main_simple.py`

- `verify_line_signature()`: Webhook signature validation
- `process_line_event()`: Event processing logic
- `get_line_user_name()`: User profile retrieval
- `send_line_message()`: Message sending with reply/push support

### Updated Functions

- `google_chat_webhook()`: Enhanced to support both platforms
- `webhook_diagnostics()`: Added Line configuration info

### Dependencies

- `aiohttp`: For Line API communication (already in requirements.txt)
- `hmac`, `hashlib`, `base64`: For signature verification (standard library)

## Conclusion

The Line integration is designed to be:
- **Safe**: No changes to existing WhatsApp functionality
- **Secure**: Full webhook signature validation
- **Consistent**: Same bot behavior across platforms
- **Maintainable**: Clean separation of platform-specific code
- **Scalable**: Ready for additional messaging platforms

Both WhatsApp and Line users now get the same intelligent music operations assistance with seamless human handoff when needed.
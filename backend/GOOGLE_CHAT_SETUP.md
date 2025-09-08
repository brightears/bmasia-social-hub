# Google Chat Multi-Space Setup Guide

## Overview
The BMA Social bot now supports routing messages to three separate Google Chat spaces based on the issue type. This ensures each team only sees relevant notifications and can manage their workload effectively.

## Why Multiple Spaces?
- **Clear ownership** - Each team owns their space
- **Reduced noise** - Teams only see relevant issues  
- **Better organization** - Easy to track and find issues
- **Scalable** - Can add more spaces as you grow
- **Team autonomy** - Each team configures their own notifications

## Step 1: Create Three Google Chat Spaces

1. **Open Google Chat** (chat.google.com)
2. Click on "Spaces" → "+ Create space"
3. Create three spaces with these names:
   - **BMA Technical Support** (for Keith and technical team)
   - **BMA Music Design** (for design/curation team)
   - **BMA Sales & Finance** (for sales and finance team)

### Space Configuration
For each space:
1. Set as "Space" (not "Collaboration")
2. Add relevant team members
3. Enable threaded conversations
4. Allow external users (for bot access)

## Step 2: Get Space IDs

For each space you created:
1. Click on the space name
2. Click on the space settings (gear icon)
3. Click "Copy space ID" or look at the URL
4. The space ID looks like: `spaces/AAAAAAAAAA`

## Step 3: Add Service Account to Spaces

The service account `bma-social-chat@bmasia-social-hub.iam.gserviceaccount.com` needs to be added to each space:

1. In each space, click "Add people & apps"
2. Enter: `bma-social-chat@bmasia-social-hub.iam.gserviceaccount.com`
3. Click "Add" (may show as an app/bot)
4. Grant "Member" permissions

## Step 4: Update Environment Variables

### Local Development (.env file)
```env
# Department-specific spaces for better organization
GCHAT_TECHNICAL_SPACE=spaces/[YOUR_TECHNICAL_SPACE_ID]
GCHAT_DESIGN_SPACE=spaces/[YOUR_DESIGN_SPACE_ID]
GCHAT_SALES_SPACE=spaces/[YOUR_SALES_SPACE_ID]

# Keep existing spaces for backward compatibility
GCHAT_CUSTOMER_SUPPORT_SPACE=spaces/AAQA1j6BK08
```

### Production (Render.com)
1. Go to https://dashboard.render.com
2. Select the `bma-social-api-q9uu` service
3. Go to "Environment" tab
4. Add these variables:
   - `GCHAT_TECHNICAL_SPACE` = `spaces/[YOUR_TECHNICAL_SPACE_ID]`
   - `GCHAT_DESIGN_SPACE` = `spaces/[YOUR_DESIGN_SPACE_ID]`
   - `GCHAT_SALES_SPACE` = `spaces/[YOUR_SALES_SPACE_ID]`
5. Save changes (will trigger redeploy)

## Message Routing Logic

Messages are automatically routed based on content:

### 🔧 Technical Support Space
**Team**: Keith and technical team
**Keywords**: offline, broken, error, failed, not working, system down, API, crashed, hardware, connection
**Priority Levels**:
- 🔴 CRITICAL: System down, all zones offline, crashed
- 🟡 HIGH: Zone offline, hardware issues, not playing
- 🟢 NORMAL: Minor errors, connection issues

**Example Messages**:
- "All zones are offline at Hilton"
- "The music system crashed"
- "API error when trying to skip songs"
- "Hardware failure in the main zone"

### 🎨 Music Design Space
**Team**: Design and curation team
**Keywords**: playlist, music design, event, party, schedule, block song, atmosphere, genre, music selection
**Priority Levels**:
- 🟡 HIGH: Events (time-sensitive), tomorrow
- 🟢 NORMAL: Playlist changes, song blocking, scheduling

**Example Messages**:
- "Need music for private event tomorrow"
- "Change playlist to jazz at Edge"
- "Block this song permanently"
- "Schedule different music for dinner time"
- "Redesign our music atmosphere"

### 💼 Sales & Finance Space
**Team**: Sales and finance team
**Keywords**: price, cost, quote, cancel, contract, payment, invoice, billing, complaint, refund, unhappy
**Priority Levels**:
- 🔴 CRITICAL: Cancellation threats
- 🟡 HIGH: Payment issues, complaints, refunds
- 🟢 NORMAL: Pricing inquiries, quotes

**Example Messages**:
- "How much does Soundtrack cost?"
- "Want to cancel our service"
- "Invoice is incorrect"
- "Need a quote for 10 zones"
- "Unhappy with the service"

## Message Format in Google Chat

Each notification includes:
```
🟡 🎨 Design - Hilton Pattaya
━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 Music Design Request

Customer wants music for private event tomorrow at Edge zone.

Venue Information:
• Name: Hilton Pattaya
• Zones: 5
• Contact: Manager

Customer:
• Name: John
• Phone: +66812345678
• Platform: WhatsApp

📝 Reply to Customer
[Button to reply via web form]

Thread: whatsapp_66812345678_hilton_pattaya
```

## Testing the Setup

After configuration, test each category:

### Test Technical Routing
Send via WhatsApp: "System is completely down at Hilton Pattaya"
- Should appear in **Technical Support** space
- Priority: CRITICAL 🔴
- Keith should be notified

### Test Design Routing
Send via WhatsApp: "Need music setup for wedding tomorrow at Edge"
- Should appear in **Music Design** space
- Priority: HIGH 🟡
- Design team should be notified

### Test Sales Routing
Send via WhatsApp: "What's the pricing for 5 zones?"
- Should appear in **Sales & Finance** space
- Priority: NORMAL 🟢
- Sales team should be notified

## Fallback Behavior

If a specific space is not configured:
1. System tries to use the Customer Support space
2. If that fails, uses any available space
3. Logs warning about missing configuration

The system is designed to always deliver the message somewhere rather than fail silently.

## Benefits for Each Team

### Technical Team
- Only sees technical issues
- Can prioritize system-down situations
- Clear SLAs for different priority levels
- Direct access to error details

### Design Team
- Focuses on music and playlist requests
- Can batch similar requests
- Sees event requests with time constraints
- No distraction from technical issues

### Sales Team
- All prospects in one place
- Can track conversion opportunities
- Sees cancellation risks immediately
- Handles all financial matters

## Troubleshooting

### "Cannot access [Space Name] space"
- Ensure service account is added to the space
- Check space ID is correct in environment variables
- Verify space allows external users

### Messages going to wrong space
- Check the routing keywords in the message
- Review department detection logic
- Can be manually overridden in code if needed

### No notifications received
- Verify at least one space is configured
- Check Google credentials are valid
- Ensure service has been redeployed after adding env vars

## Migration from Single Space

If you're currently using a single space:
1. Keep the existing space as fallback
2. Create new spaces gradually
3. Add team members to their respective spaces
4. Update environment variables
5. Monitor for a few days
6. Decommission old space when comfortable

## Future Enhancements

Consider adding:
- **Emergency Space**: For after-hours critical issues
- **VIP Space**: For high-value customer issues  
- **Development Space**: For testing and debugging
- **Archive Space**: For resolved issues
- **Regional Spaces**: For different geographic regions

## Best Practices

1. **Regular Reviews**: Review routing rules monthly
2. **Team Training**: Ensure teams know their space
3. **Clear Escalation**: Define when to move between spaces
4. **Thread Management**: Keep conversations in threads
5. **Notification Settings**: Each team configures their own

## Contact

For issues with setup:
- Technical: Keith (Technical Support space)
- Configuration: Admin team
- Bot issues: Development team

---

*Last Updated: September 2024*
*Version: 2.0 - Multi-Space Support*
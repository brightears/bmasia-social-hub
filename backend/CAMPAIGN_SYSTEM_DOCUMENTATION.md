# BMA Social AI-Powered Campaign Management System

## Overview

The campaign system is an AI-first solution where ChatGPT 4o composes, manages, and monitors marketing campaigns to **customers** (businesses like Hilton Pattaya) about their **venues/zones** (music zones like Edge, Drift Bar). The system supports intelligent filtering by brand, region, contract status, and more.

---

## Key Concepts

### Terminology
- **Customer**: The business entity (e.g., Hilton Pattaya, Marriott Bangkok)
- **Venue/Zone**: Music zones within a customer (e.g., Edge, Drift Bar, Horizon)
- **Brand**: Corporate group (e.g., all Hilton properties globally)
- **Campaign**: Targeted communication to multiple customers
- **Orchestrator**: Main coordinator between AI, data, and sending

### System Architecture
```
Human Request → AI Interprets → Filters Customers → AI Composes Messages → Multi-channel Send
       ↑                                                                           ↓
       └────────────────── AI Analyzes Responses ←────────────────────────────────┘
```

---

## Features

### 1. Natural Language Campaign Creation
```python
# Human says: "Send renewal reminders to all Hiltons expiring in October"
# System automatically:
- Identifies campaign type: renewal
- Filters: brand = "Hilton Hotels & Resorts", expiry = October 2025
- Finds matching customers
- AI writes personalized messages for each
```

### 2. Smart Filtering
- **By Brand**: All Hiltons, all Marriotts, etc.
- **By Region**: Asia Pacific, Europe, Americas
- **By Country/City**: Thailand, Bangkok, Pattaya
- **By Business Type**: Hotels, Restaurants, Beach Clubs
- **By Contract Status**: Expiring in X days
- **By Platform**: Soundtrack Your Brand vs Beat Breeze
- **By Size**: Enterprise (>10 zones), Medium (4-10), Small (1-3)

### 3. AI Message Composition
- Personalized for each customer
- Mentions ALL their venues/zones
- Adapts tone to brand (formal for Hilton, casual for beach clubs)
- Includes specific value propositions
- Clear call-to-action

### 4. Multi-Channel Delivery
- **WhatsApp**: Template messages with personalization
- **Line**: Broadcast messages to opted-in users
- **Email**: HTML formatted with branding

### 5. Response Intelligence
- AI analyzes campaign responses
- Determines intent (interested, question, complaint)
- Suggests appropriate action
- Escalates to human when needed

---

## API Endpoints

### Create Campaign
```http
POST /api/campaigns/create

# Natural language request:
{
    "human_request": "Send Christmas music offers to all hotels in Asia"
}

# Or structured request:
{
    "type": "seasonal",
    "filters": {
        "business_type": "Hotel",
        "region": "Asia Pacific"
    },
    "context": "Christmas playlist promotion"
}
```

### Preview Campaign
```http
GET /api/campaigns/{campaign_id}/preview

# Returns sample messages and statistics before sending
```

### Send Campaign
```http
POST /api/campaigns/{campaign_id}/send
{
    "channels": ["whatsapp", "email"],
    "test_mode": true  // Send to first customer only
}
```

### Get Statistics
```http
GET /api/campaigns/statistics

# Returns customer stats, send limits, campaign metrics
```

### Handle Response
```http
POST /api/campaigns/response
{
    "identifier": "+66856644142",
    "message": "Yes, please renew all zones",
    "channel": "whatsapp"
}
```

---

## Campaign Types

### 1. Renewal Reminders
- Targets customers with expiring contracts
- Mentions specific expiry date and current pricing
- Emphasizes all zones/venues
- Clear renewal CTA

### 2. Seasonal Offers
- Holiday-specific music offerings
- Region-aware (Christmas for West, CNY for Asia)
- Promotes special playlists
- Time-limited offers

### 3. Brand Announcements
- New features or services
- Targets specific brands (all Hiltons)
- Maintains brand voice
- Cross-property benefits

### 4. Quarterly Follow-ups
- Regular check-ins
- Performance summaries
- Satisfaction checks
- Upsell opportunities

### 5. Service Surveys
- Post-issue resolution
- NPS scoring
- Feedback collection
- Service improvement

---

## Example Campaigns

### Example 1: Hilton Brand Renewal
**Human Request**: "Send renewal reminders to all Hiltons expiring this quarter"

**AI Actions**:
1. Filters: brand = "Hilton Hotels & Resorts", contract_expiry < 90 days
2. Finds: 3 Hilton properties
3. Composes personalized messages:
```
Hi Rudolf,

Your Hilton Pattaya music service for all 4 zones (Edge, Drift Bar,
Horizon, Shore) expires on October 31, 2025.

Your current rate of THB 12,000 per zone remains locked for renewal.
That's THB 48,000 annually for complete property coverage.

Reply YES to secure your renewal or CALL to discuss.

Best regards,
BMA Social Team
```

### Example 2: Regional Seasonal Campaign
**Human Request**: "Christmas music offer for all Asia Pacific hotels"

**AI Actions**:
1. Filters: region = "Asia Pacific", business_type = "Hotel"
2. Finds: 45 hotels across multiple brands
3. Composes culturally appropriate messages
4. Schedules for optimal timezone delivery

---

## File Structure
```
backend/
├── campaigns/
│   ├── __init__.py                 # Module initialization
│   ├── campaign_ai.py              # AI brain for campaigns
│   ├── campaign_orchestrator.py    # Main coordinator
│   ├── customer_manager.py         # Customer data management
│   └── campaign_sender.py          # Multi-channel sending
├── venue_data.md                   # Customer database
├── main_simple.py                  # API endpoints added
└── test_campaign_system.py         # Test script
```

---

## Configuration

### Required Environment Variables
```bash
# AI
OPENAI_API_KEY=sk-...

# WhatsApp
WHATSAPP_ACCESS_TOKEN=...
WHATSAPP_PHONE_NUMBER_ID=...

# Line
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_CHANNEL_SECRET=...

# Email (optional)
CAMPAIGN_EMAIL_SENDER=campaigns@bmasocial.com
CAMPAIGN_EMAIL_PASSWORD=...
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

### Rate Limits
- WhatsApp: 1000 template messages/day
- Line: 500 users per broadcast
- Email: 100 per hour

---

## Testing

Run the test script:
```bash
cd backend
python test_campaign_system.py
```

This will:
1. Load customer data
2. Create test campaigns
3. Preview messages
4. Test filtering
5. Analyze sample responses

---

## Best Practices

### 1. Campaign Creation
- Use natural language for flexibility
- Be specific about targeting
- Provide context for better AI composition
- Always preview before sending

### 2. Message Composition
- Let AI handle personalization
- Review samples before bulk send
- Test with single customer first
- Monitor response rates

### 3. Filtering
- Start broad, then narrow
- Use brand filters for consistency
- Consider timezones for scheduling
- Respect opt-out preferences

### 4. Response Handling
- AI analyzes all responses
- Human review for high-value customers
- Quick follow-up on positive responses
- Track conversion metrics

---

## Security & Compliance

### Data Protection
- Customer data stays in venue_data.md
- No external data storage
- Secure API endpoints
- Audit trail of campaigns

### Message Compliance
- WhatsApp template approval required
- Line opt-in verification
- Email unsubscribe links
- Rate limiting enforced

### Access Control
- API authentication required
- Campaign approval workflow
- Test mode for safety
- Rollback capability

---

## Troubleshooting

### Common Issues

**"No customers found"**
- Check filter criteria
- Verify venue_data.md format
- Review customer data fields

**"Message send failed"**
- Verify API credentials
- Check rate limits
- Confirm phone/email formats

**"AI composition error"**
- Check OpenAI API key
- Review customer data completeness
- Verify campaign context

---

## Future Enhancements

1. **Scheduling**: Set campaigns for future dates
2. **A/B Testing**: Test different messages
3. **Analytics Dashboard**: Visual campaign performance
4. **Template Library**: Pre-approved message templates
5. **Automation Rules**: Trigger campaigns on events
6. **CRM Integration**: Sync with external systems

---

## Support

For issues or questions:
1. Check test script output
2. Review API endpoint responses
3. Check main_simple.py logs
4. Verify environment variables

---

**Version**: 1.0.0
**Last Updated**: September 13, 2025
**Status**: Production Ready ✅
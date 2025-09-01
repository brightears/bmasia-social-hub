# Gmail Integration Setup Guide

## Overview
The bot can now search BMA team emails for venue correspondence, support history, and contract discussions. This provides valuable context when helping clients.

## Smart Search Features
- **Contextual Triggers**: Only searches when relevant keywords are detected
- **Multi-Inbox**: Searches across all BMA team members
- **Caching**: Results cached for 5 minutes to avoid redundant searches
- **Smart Filtering**: Focuses on relevant emails based on query type

## Search Triggers

The bot will automatically search emails when users mention:

### Contract/Pricing
- "contract", "renewal", "pricing", "negotiate", "rate", "cost", "invoice"
- Searches last 180 days

### Technical Issues
- "issue", "problem", "fixed", "resolved", "ticket", "support"
- Searches last 30 days

### Follow-ups
- "follow up", "following up", "update on", "status of", "progress"
- Searches last 14 days

### References
- "email", "sent", "mentioned", "discussed", "agreed", "confirmed"
- Searches last 30 days

### History
- "previous", "last time", "before", "history", "earlier", "past"
- Searches last 60 days

## Setup Steps

### Option 1: Google Workspace Domain-Wide Delegation (Recommended for Organizations)

1. **Enable Gmail API**
   - Go to: https://console.cloud.google.com/apis/library/gmail.googleapis.com?project=bmasia-social-hub
   - Click "ENABLE"

2. **Set Up Domain-Wide Delegation**
   - Go to Google Admin Console: https://admin.google.com
   - Security → API Controls → Domain-wide Delegation
   - Add new client:
     - Client ID: `109302315012481422492` (from your service account)
     - Scopes: `https://www.googleapis.com/auth/gmail.readonly`
   - Authorize for your domain

3. **The bot will automatically access**:
   - norbert@bmasiamusic.com
   - production@bmasiamusic.com
   - keith@bmasiamusic.com
   - (Add more in `gmail_client.py`)

### Option 2: Individual OAuth2 Setup (If no Google Workspace admin access)

1. **Create OAuth2 Credentials**
   - Go to: https://console.cloud.google.com/apis/credentials?project=bmasia-social-hub
   - Create Credentials → OAuth client ID
   - Application type: Desktop app
   - Download the credentials JSON

2. **Authorize Each Account**
   - Run authorization script for each BMA email
   - Store refresh tokens securely

### Option 3: Use Existing IMAP/SMTP (Simplest but Limited)

Since you already have SMTP credentials in .env:
```python
SMTP_USER=norbert@bmasiamusic.com
SMTP_PASSWORD=your_app_password
```

We could modify to use IMAP for basic email search (limited features).

## Testing

Once set up, test with these messages:

```
"Hi, I'm from Hilton Pattaya"
"Did we discuss the contract renewal recently?"
"What was the last issue we had?"
"Following up on our email from last week"
```

## What the Bot Shows

### When Contract Mentioned
```
📧 Latest contract discussion: 'RE: Hilton Pattaya Renewal 2025' on 2025-08-15
   Subject: RE: Hilton Pattaya Renewal 2025
   Preview: Thanks for sending the renewal proposal. We're reviewing the new rates...
```

### When Issue Referenced
```
📧 Recent technical issues:
   • Zone Edge offline issue (2025-08-20) ✅ Resolved
   • Volume scheduling problem (2025-08-18) ✅ Resolved
   • Music stopped in Lobby (2025-08-10) ⚠️ Open
```

### General History
```
📧 Found 12 emails about this venue in the last 30 days
Last contact: 2025-08-25
```

## Security Notes

- Service account only has READ access to emails
- Searches are limited to venue-specific queries
- Results are cached to minimize API calls
- No sensitive data is stored permanently

## Performance Optimization

The smart search system:
1. Only searches when trigger keywords detected
2. Caches results for 5 minutes
3. Limits to 20 most recent emails
4. Focuses on specific date ranges based on query type
5. Deduplicates emails across multiple inboxes

## Adding More BMA Emails

Edit `gmail_client.py`:
```python
BMA_EMAILS = [
    'norbert@bmasiamusic.com',
    'production@bmasiamusic.com',
    'keith@bmasiamusic.com',
    'newmember@bmasiamusic.com',  # Add new team member
]
```

## Troubleshooting

### "Delegation denied" Error
- Domain-wide delegation not set up correctly
- Check Google Admin Console settings

### No Emails Found
- Check if Gmail API is enabled
- Verify service account has access
- Check if emails exist for the venue

### Slow Performance
- Reduce MAX_RESULTS in gmail_client.py
- Increase cache TTL
- Limit search depth

## Future Enhancements

- **Google Drive Integration**: Search and retrieve actual contracts
- **Attachment Processing**: Extract data from PDFs and documents
- **Automated Summaries**: Weekly venue communication reports
- **Sentiment Analysis**: Detect urgent or problematic conversations
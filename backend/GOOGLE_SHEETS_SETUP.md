# Google Sheets Integration Setup Guide

## Step 1: Create a Google Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing "BMAsia Social Hub"
3. Enable Google Sheets API:
   - Go to "APIs & Services" > "Library"
   - Search for "Google Sheets API"
   - Click and Enable it

## Step 2: Create Service Account Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "Service Account"
3. Fill in:
   - Service account name: `bma-social-sheets`
   - Service account ID: (auto-generated)
   - Description: "BMA Social bot Google Sheets access"
4. Click "Create and Continue"
5. Skip the optional roles (click "Continue")
6. Click "Done"

## Step 3: Download Credentials

1. Click on the service account you just created
2. Go to "Keys" tab
3. Click "Add Key" > "Create new key"
4. Choose "JSON" format
5. Download the file (keep it secure!)

## Step 4: Share Your Google Sheets

1. Open your Google Sheet:
   https://docs.google.com/spreadsheets/d/1awtlzSY7eBwkvA9cbbjrb5wx--okEtWuj53b0AVSv44/

2. Click "Share" button
3. Add the service account email (found in the JSON file as "client_email")
   Example: `bma-social-sheets@your-project.iam.gserviceaccount.com`
4. Give it "Editor" permission (or "Viewer" if read-only)
5. Click "Send"

## Step 5: Add Credentials to Render

1. Open the downloaded JSON file
2. Copy the entire contents
3. Go to Render Dashboard
4. Add environment variable:
   ```
   GOOGLE_CREDENTIALS_JSON = [paste entire JSON content]
   MASTER_SHEET_ID = 1awtlzSY7eBwkvA9cbbjrb5wx--okEtWuj53b0AVSv44
   ```

## Step 6: Test the Integration

Once set up, the bot will be able to:
- Read venue data from your master sheet
- Write conversation logs to venue-specific sheets
- Update venue information as needed

## Sheet Structure Expected

The integration expects these columns (flexible, will adapt to your structure):

### Master Venue Sheet
- **Name**: Venue name (required)
- **Phone**: WhatsApp number
- **Email**: Contact email
- **Location**: City/Country
- **Has_Soundtrack**: TRUE/FALSE
- **Soundtrack_ID**: If has Soundtrack
- **Sheet_URL**: Link to venue-specific sheet (optional)
- **Gmail_Label**: For email filtering (optional)
- **Contact_Name**: Primary contact
- **Zone_Count**: Number of music zones

### Venue-Specific Sheets (optional)
Each venue can have its own sheet with tabs:
- **Info**: Venue details and zones
- **History**: Conversation logs
- **Issues**: Common problems and solutions
- **Notes**: Special instructions

## Testing Commands

After setup, test with:

```python
# In Python console or test script
from google_sheets_client import sheets_client

# Test connection
venues = sheets_client.get_all_venues()
print(f"Found {len(venues)} venues")

# Test venue search
venue = sheets_client.find_venue_by_name("Grand Plaza")
print(venue)
```

## Troubleshooting

### "Permission denied" error
- Make sure you shared the sheet with the service account email
- Check that the service account has at least "Viewer" permission

### "API not enabled" error
- Go back to Google Cloud Console
- Enable both "Google Sheets API" and "Google Drive API"

### "Invalid credentials" error
- Check that GOOGLE_CREDENTIALS_JSON contains valid JSON
- Ensure no extra quotes or escaping issues

## Security Notes

- Never commit the credentials JSON to git
- Keep the service account email private
- Use "Viewer" permission if only reading data
- Rotate keys periodically in production

## Next Steps

Once connected, the bot will:
1. Load venue data on startup
2. Identify venues by name in conversations
3. Access venue-specific information
4. Log conversations back to sheets
5. Maintain history and analytics
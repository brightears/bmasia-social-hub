# Generate New Service Account Key

The current service account key appears to be corrupted. Follow these steps to generate a new one:

## Steps to Create a New Key:

1. **Go to Service Accounts Page**
   https://console.cloud.google.com/iam-admin/serviceaccounts?project=bmasia-social-hub

2. **Find Your Service Account**
   Look for: `bma-social-sheets@bmasia-social-hub.iam.gserviceaccount.com`

3. **Click on the Service Account**
   Click on the email to open its details

4. **Go to the "Keys" Tab**
   You'll see it at the top of the service account details page

5. **Delete Old Key (Optional)**
   If there's an existing key, you can delete it first

6. **Add New Key**
   - Click "ADD KEY" → "Create new key"
   - Choose **JSON** format
   - Click "CREATE"
   - The key will download automatically

7. **Update Your Configuration**
   - Open the downloaded JSON file
   - Copy the ENTIRE contents (from `{` to `}`)
   - Replace the GOOGLE_CREDENTIALS_JSON value in your .env file
   - Also update it in Render's environment variables

## What the JSON Should Look Like:

```json
{
  "type": "service_account",
  "project_id": "bmasia-social-hub",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "bma-social-sheets@bmasia-social-hub.iam.gserviceaccount.com",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "...",
  "universe_domain": "googleapis.com"
}
```

## Important Notes:

- The private_key field should have actual newlines (`\n`) in it
- Don't modify or format the JSON - use it exactly as downloaded
- Keep this file secure - it provides access to your Google Sheets

## After Updating:

Run the verification script again:
```bash
python verify_sheets_setup.py
```

This should resolve the authentication issue!
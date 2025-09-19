# Database Setup Instructions

## 1. Get Your Database Credentials from Render

### PostgreSQL Credentials
1. Go to https://dashboard.render.com
2. Click on **bma-social-db-q9uu**
3. Copy the **External Database URL** (starts with `postgresql://`)

### Redis Credentials
1. Go to https://dashboard.render.com
2. Click on **bma-social-redis-q9uu**
3. Copy the **External Redis URL** (starts with `redis://`)

## 2. Add to Your .env File

Add these lines to your `/backend/.env` file:

```bash
# Database Configuration
DATABASE_URL=<paste-your-postgresql-url-here>
REDIS_URL=<paste-your-redis-url-here>

# Feature Flag - Start with false for testing
USE_DATABASE=false
```

Example format (don't use these actual values):
```bash
DATABASE_URL=postgresql://bma_user:password123@dpg-abc123.singapore-postgres.render.com/bma_social_esoq
REDIS_URL=redis://red-abc123:password456@singapore-redis.render.com:6379
```

## 3. Test Your Connection

Run the test script:
```bash
cd backend
python test_database_setup.py
```

You should see:
- ✅ Connected to PostgreSQL
- ✅ Connected to Redis/Valkey

## 4. Create Database Schema

If tables don't exist yet:
```bash
cd backend/database

# Option 1: Using psql
psql $DATABASE_URL < schema.sql

# Option 2: Using Python
python -c "
import psycopg2
import os
from dotenv import load_dotenv
load_dotenv('../.env')
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
with open('schema.sql', 'r') as f:
    conn.cursor().execute(f.read())
conn.commit()
print('Schema created!')
"
```

## 5. Migrate Your Data

```bash
cd backend/database

# Migrate venue data (923 venues, 4,342 contacts)
python migrate_venue_data.py

# Migrate product information
python migrate_product_info.py
```

## 6. Test Locally with Database

```bash
cd backend

# Enable database mode
export USE_DATABASE=true

# Run the bot
python main_simple.py

# Test with a message like "Hi from Hilton Pattaya"
```

## 7. Deploy to Render

Once testing is successful:

1. **Update Render Environment Variables**:
   - Go to your service on Render
   - Add environment variables:
     - `DATABASE_URL`: (same as above)
     - `REDIS_URL`: (same as above)
     - `USE_DATABASE`: `false` (start with file mode)

2. **Deploy the Code**:
```bash
git add .
git commit -m "Add database support with migration scripts"
git push origin main
```

3. **Run Migration on Render** (if needed):
   - SSH into your Render service or use the Shell tab
   - Run migration scripts

4. **Enable Database Mode**:
   - Change `USE_DATABASE` to `true` in Render environment
   - Monitor logs for any issues

## Rollback Plan

If anything goes wrong, simply change `USE_DATABASE=false` in Render environment variables. The bot will immediately switch back to using venue_data.md file.
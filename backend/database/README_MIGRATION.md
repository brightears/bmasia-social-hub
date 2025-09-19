# Database Migration Guide

## Overview
This guide explains how to migrate from the file-based system (venue_data.md) to PostgreSQL database for improved performance and scalability.

## Prerequisites

1. PostgreSQL 16 database on Render (already set up)
2. Redis/Valkey on Render (already set up)
3. Python dependencies installed:
```bash
pip install psycopg2-binary asyncpg redis python-dotenv
```

## Migration Steps

### Step 1: Set Environment Variables

Create or update `.env` file in the backend directory:
```bash
# Database Configuration
DATABASE_URL=postgresql://username:password@host:port/database_name
REDIS_URL=redis://host:port/0

# Feature Flag (start with false for testing)
USE_DATABASE=false
```

For Render deployment, get the actual connection strings from:
- PostgreSQL: Render Dashboard → Database → Connection String
- Redis/Valkey: Render Dashboard → Key-Value Store → Connection String

### Step 2: Create Database Schema

```bash
cd backend/database

# Connect to your PostgreSQL database and run the schema
psql $DATABASE_URL < schema.sql

# Or use Python script (if psql not available)
python -c "
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv('../.env')
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
with open('schema.sql', 'r') as f:
    conn.cursor().execute(f.read())
conn.commit()
conn.close()
print('Schema created successfully!')
"
```

### Step 3: Migrate Venue Data

```bash
cd backend/database

# Run venue data migration
python migrate_venue_data.py

# Expected output:
# Parsed 923 venues from ../venue_data.md
# Created 923 venues
# Created ~3000 zones
# Created 4342 contacts
# ✅ Migration completed successfully!
```

### Step 4: Migrate Product Information

```bash
cd backend/database

# Run product info migration
python migrate_product_info.py

# Expected output:
# Created 45+ product information records
# ✅ Product information migration completed successfully!
```

### Step 5: Test Database Queries

```bash
cd backend

# Test the database manager
python -c "
import asyncio
from database_manager import DatabaseManager
import os
from dotenv import load_dotenv

load_dotenv()

async def test():
    db = DatabaseManager(os.getenv('DATABASE_URL'), os.getenv('REDIS_URL'))
    await db.initialize()

    # Test venue search
    venues = await db.find_venues_by_name('Hilton', threshold=0.3)
    print(f'Found {len(venues)} venues matching Hilton')

    # Test product info
    products = await db.get_product_info(['SYB'], 'pricing')
    print(f'Found {len(products)} product pricing records')

    # Check health
    health = await db.health_check()
    print(f'Health: {health}')

    await db.close()

asyncio.run(test())
"
```

### Step 6: Enable Database Mode

1. **Test with single bot instance**:
```bash
# Set environment variable
export USE_DATABASE=true

# Run the bot
python main_simple.py

# Test with WhatsApp/LINE messages
```

2. **Monitor performance**:
- Check response times (target: <10ms for venue lookups)
- Monitor cache hit rates (target: >90%)
- Watch for any errors in logs

3. **Gradual rollout**:
```python
# In venue_manager_hybrid.py, you can control the rollout percentage:
import random

# 10% of requests use database
self.use_database = random.random() < 0.1
```

### Step 7: Deploy to Production

1. **Update Render environment variables**:
```bash
USE_DATABASE=true
DATABASE_URL=<your-render-postgres-url>
REDIS_URL=<your-render-redis-url>
```

2. **Deploy**:
```bash
git add .
git commit -m "Enable database mode for bot"
git push origin main
```

3. **Monitor**:
- Watch Render logs for any errors
- Check database metrics in Render dashboard
- Monitor Redis cache hit rates

## Performance Expectations

### Before (File-based):
- Venue lookup: ~100ms
- Memory usage: ~500MB (entire file loaded)
- Concurrent support: Limited
- Scaling: Poor (linear with file size)

### After (Database):
- Venue lookup: <10ms
- Memory usage: ~50MB (no file loading)
- Concurrent support: 1000+ queries
- Scaling: Excellent (indexed queries)

## Rollback Plan

If issues occur, rollback is instant:

1. **Immediate rollback**:
```bash
# Set environment variable
export USE_DATABASE=false

# Or in Render dashboard
USE_DATABASE=false
```

2. **The system will immediately revert to file-based mode**

3. **No data loss** - venue_data.md remains untouched

## Troubleshooting

### Database Connection Failed
```python
# Check connection
psql $DATABASE_URL -c "SELECT 1"

# Verify credentials
echo $DATABASE_URL
```

### Slow Queries
```sql
-- Check missing indexes
SELECT schemaname, tablename, indexname
FROM pg_indexes
WHERE schemaname = 'public';

-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM venues WHERE name ILIKE '%hotel%';
```

### Cache Not Working
```python
# Test Redis connection
redis-cli -u $REDIS_URL ping
# Should return: PONG
```

### Migration Verification
```sql
-- Check record counts
SELECT 'venues' as table_name, COUNT(*) as count FROM venues
UNION ALL
SELECT 'zones', COUNT(*) FROM zones
UNION ALL
SELECT 'contacts', COUNT(*) FROM contacts
UNION ALL
SELECT 'product_info', COUNT(*) FROM product_info;
```

## Database Maintenance

### Backup
```bash
# Create backup
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql

# Restore from backup
psql $DATABASE_URL < backup_20250119.sql
```

### Update Statistics
```sql
-- Update query planner statistics
ANALYZE venues;
ANALYZE zones;
ANALYZE contacts;
```

### Monitor Performance
```sql
-- Check slow queries
SELECT query, calls, mean_exec_time
FROM pg_stat_statements
WHERE mean_exec_time > 10
ORDER BY mean_exec_time DESC
LIMIT 10;
```

## Next Steps

After successful migration:

1. Remove file-based fallback (after 1 week of stable operation)
2. Implement real-time venue status monitoring
3. Add analytics queries for business insights
4. Set up automated backups
5. Implement data archiving for old conversations

## Support

For issues or questions:
- Check logs: `python check_render_logs.py`
- Database metrics: Render Dashboard → Database → Metrics
- Redis metrics: Render Dashboard → Key-Value Store → Metrics
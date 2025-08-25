# Technical Specifications

## System Requirements

### Performance Targets
- Response time: <100ms for API calls
- Bot response: <1 second for simple queries
- Monitoring detection: <10 minutes for any issue
- Dashboard refresh: Real-time (<5 seconds)
- Database queries: <500ms for complex aggregations

### Scale Requirements
- Current: 2,000 venues / 10,000 zones
- Target: 10,000 venues / 50,000 zones
- Concurrent users: 1,000+
- Messages/day: 10,000+
- API calls/hour: 120,000+

## API Integrations

### Soundtrack Your Brand API
- Endpoint: https://api.soundtrackyourbrand.com/v2
- Authentication: OAuth 2.0
- Rate limits: 1000 requests/minute
- Key operations:
  - GET /devices - List all devices
  - GET /devices/{id}/status - Check device status
  - POST /devices/{id}/volume - Adjust volume
  - POST /devices/{id}/playlist - Change playlist

### WhatsApp Business API
- Version: v17.0
- Webhook URL: https://api.bma-social.com/webhooks/whatsapp
- Message types: text, image, document, location
- Session timeout: 24 hours

### Line Business API
- Version: v2
- Channel type: Messaging API
- Webhook URL: https://api.bma-social.com/webhooks/line
- Rich menu support: Yes

## Database Schema

### Core Tables
```sql
-- Venues table
CREATE TABLE venues (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    brand VARCHAR(100),
    country VARCHAR(2),
    timezone VARCHAR(50),
    soundtrack_account_id VARCHAR(100),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Zones table
CREATE TABLE zones (
    id UUID PRIMARY KEY,
    venue_id UUID REFERENCES venues(id),
    name VARCHAR(100),
    zone_type VARCHAR(50), -- lobby, restaurant, pool, spa
    soundtrack_device_id VARCHAR(100),
    last_status VARCHAR(20),
    last_check TIMESTAMP,
    created_at TIMESTAMP
);

-- Conversations table
CREATE TABLE conversations (
    id UUID PRIMARY KEY,
    venue_id UUID REFERENCES venues(id),
    channel VARCHAR(20), -- whatsapp, line, email
    external_id VARCHAR(100), -- WhatsApp/Line conversation ID
    status VARCHAR(20),
    assigned_to UUID REFERENCES team_members(id),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Messages table
CREATE TABLE messages (
    id UUID PRIMARY KEY,
    conversation_id UUID REFERENCES conversations(id),
    sender_type VARCHAR(20), -- bot, user, team
    content TEXT,
    metadata JSONB,
    created_at TIMESTAMP
);

-- Satisfaction Scores table
CREATE TABLE satisfaction_scores (
    id UUID PRIMARY KEY,
    conversation_id UUID REFERENCES conversations(id),
    venue_id UUID REFERENCES venues(id),
    score INTEGER CHECK (score >= 1 AND score <= 5),
    feedback TEXT,
    created_at TIMESTAMP
);

-- Music Status Logs table
CREATE TABLE music_status_logs (
    id UUID PRIMARY KEY,
    zone_id UUID REFERENCES zones(id),
    status VARCHAR(20),
    uptime_percentage DECIMAL(5,2),
    response_time_ms INTEGER,
    error_message TEXT,
    created_at TIMESTAMP
);

-- Campaigns table
CREATE TABLE campaigns (
    id UUID PRIMARY KEY,
    name VARCHAR(255),
    type VARCHAR(50), -- marketing, service, holiday
    channel VARCHAR(20),
    target_venues UUID[],
    message_template TEXT,
    scheduled_at TIMESTAMP,
    status VARCHAR(20),
    created_by UUID REFERENCES team_members(id),
    created_at TIMESTAMP
);

-- Alerts table
CREATE TABLE alerts (
    id UUID PRIMARY KEY,
    zone_id UUID REFERENCES zones(id),
    alert_type VARCHAR(50),
    severity VARCHAR(20),
    message TEXT,
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP,
    created_at TIMESTAMP
);

-- Team Members table
CREATE TABLE team_members (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(100),
    role VARCHAR(50),
    permissions JSONB,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP
);
```

## Environment Variables
```env
# Database
DATABASE_URL=postgresql://user:pass@localhost/bma_social
REDIS_URL=redis://localhost:6379

# APIs
SOUNDTRACK_CLIENT_ID=xxx
SOUNDTRACK_CLIENT_SECRET=xxx
WHATSAPP_ACCESS_TOKEN=xxx
WHATSAPP_VERIFY_TOKEN=xxx
LINE_CHANNEL_ACCESS_TOKEN=xxx
LINE_CHANNEL_SECRET=xxx
CLAUDE_API_KEY=xxx
OPENWEATHERMAP_API_KEY=xxx

# Security
JWT_SECRET_KEY=xxx
WEBHOOK_SECRET=xxx
CORS_ORIGINS=["http://localhost:3000", "https://portal.bma-social.com"]

# Monitoring
SENTRY_DSN=xxx
POLLING_INTERVAL=300  # seconds
ALERT_COOLDOWN=3600  # seconds
MAX_RETRIES=3

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=xxx
SMTP_PASSWORD=xxx
```

## API Endpoints

### Authentication
```
POST /api/v1/auth/login
POST /api/v1/auth/refresh
POST /api/v1/auth/logout
```

### Venues
```
GET /api/v1/venues
GET /api/v1/venues/{id}
POST /api/v1/venues
PUT /api/v1/venues/{id}
DELETE /api/v1/venues/{id}
GET /api/v1/venues/{id}/zones
GET /api/v1/venues/{id}/satisfaction
```

### Monitoring
```
GET /api/v1/monitoring/status
GET /api/v1/monitoring/zones/{id}/history
POST /api/v1/monitoring/zones/{id}/check
GET /api/v1/monitoring/alerts
POST /api/v1/monitoring/alerts/{id}/resolve
```

### Conversations
```
GET /api/v1/conversations
GET /api/v1/conversations/{id}
POST /api/v1/conversations/{id}/messages
POST /api/v1/conversations/{id}/assign
POST /api/v1/conversations/{id}/close
```

### Campaigns
```
GET /api/v1/campaigns
POST /api/v1/campaigns
GET /api/v1/campaigns/{id}
PUT /api/v1/campaigns/{id}
POST /api/v1/campaigns/{id}/send
GET /api/v1/campaigns/{id}/analytics
```

### Webhooks
```
POST /api/v1/webhooks/whatsapp
POST /api/v1/webhooks/line
```

### Analytics
```
GET /api/v1/analytics/dashboard
GET /api/v1/analytics/satisfaction
GET /api/v1/analytics/uptime
GET /api/v1/analytics/conversations
```

## Deployment Configuration

### Render.com Setup
```yaml
services:
  - type: web
    name: bma-social-api
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /health
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: bma-social-db
          property: connectionString
      - key: REDIS_URL
        fromService:
          name: bma-social-redis
          type: redis
          property: connectionString
    
  - type: worker
    name: bma-social-worker
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: celery -A app.worker worker --loglevel=info
    
  - type: worker
    name: bma-social-scheduler
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: celery -A app.worker beat --loglevel=info
    
  - type: redis
    name: bma-social-redis
    plan: starter
    
databases:
  - name: bma-social-db
    plan: starter
    databaseName: bma_social
    user: bma_user
```

### Docker Configuration
```dockerfile
# Backend Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### CI/CD Pipeline
```yaml
# .github/workflows/deploy.yml
name: Deploy to Render

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Deploy to Render
        env:
          deploy_url: ${{ secrets.RENDER_DEPLOY_HOOK_URL }}
        run: |
          curl "$deploy_url"
```

## Security Considerations

### Authentication
- JWT tokens with 24-hour expiry
- Refresh tokens with 7-day expiry
- Role-based permissions (admin, manager, viewer)
- Multi-factor authentication for admin accounts

### Data Protection
- All passwords hashed with bcrypt
- Sensitive data encrypted at rest
- TLS 1.3 for all communications
- PII data anonymization for analytics

### API Security
- Rate limiting per IP and per user
- Webhook signature validation
- CORS configuration
- SQL injection prevention via ORM
- XSS protection headers

### Monitoring & Alerting
- Real-time error tracking with Sentry
- Performance monitoring
- Security audit logs
- Automated vulnerability scanning
- Uptime monitoring with status page

## Performance Optimization

### Caching Strategy
- Redis for session management
- Query result caching (5-minute TTL)
- Static asset CDN caching
- Database connection pooling

### Database Optimization
- Indexed foreign keys
- Partitioned tables for logs
- Read replicas for analytics
- Automatic vacuum scheduling

### Background Jobs
- Celery for async processing
- Priority queues for urgent tasks
- Retry logic with exponential backoff
- Dead letter queue for failed jobs

## Testing Strategy

### Unit Tests
- 80% code coverage target
- Mock external API calls
- Test all business logic

### Integration Tests
- API endpoint testing
- Database transaction testing
- Message queue testing

### Load Testing
- Simulate 10,000 concurrent users
- Test 1M API calls/day
- Monitor response times under load

### Security Testing
- OWASP ZAP scanning
- Dependency vulnerability checks
- Penetration testing quarterly
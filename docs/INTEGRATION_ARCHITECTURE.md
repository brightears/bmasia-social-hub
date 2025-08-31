# BMA Social Integration Architecture

## Executive Summary
This document outlines the comprehensive integration architecture for BMA Social's AI bot system, designed to handle 2000+ venues with plans to scale to 10,000+. The architecture prioritizes natural venue identification through conversation, multi-source data aggregation, and intelligent caching strategies.

## 1. Architecture Overview

### 1.1 Core Design Principles
- **Natural Conversation First**: Venue identification through dialogue, not phone numbers
- **Source Priority**: Google Sheets → Soundtrack API → Gmail → Database
- **Scalable Design**: Horizontal scaling ready for 10,000+ venues
- **Resilient Operation**: Circuit breakers and fallback mechanisms
- **Performance Optimized**: Multi-layer caching with TTL strategies

### 1.2 System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interface Layer                      │
├───────────────┬─────────────────────┬───────────────────────┤
│   WhatsApp    │      LINE Bot       │   Future Channels     │
└───────┬───────┴──────────┬──────────┴───────────┬───────────┘
        │                  │                      │
        └──────────────────▼──────────────────────┘
                           │
                  ┌────────▼─────────┐
                  │ Venue Identifier  │
                  │   (Natural NLP)   │
                  └────────┬─────────┘
                           │
                  ┌────────▼─────────┐
                  │ Data Aggregator   │
                  │  (Multi-Source)   │
                  └────────┬─────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
┌───────▼──────┐  ┌────────▼────────┐  ┌─────▼──────┐
│Google Sheets │  │ Soundtrack API  │  │   Gmail    │
│  (Primary)   │  │  (Real-time)    │  │ (History)  │
└──────────────┘  └─────────────────┘  └────────────┘
        │                  │                  │
        └──────────────────▼──────────────────┘
                           │
                  ┌────────▼─────────┐
                  │   PostgreSQL DB   │
                  │  (Local Cache)    │
                  └────────┬─────────┘
                           │
                  ┌────────▼─────────┐
                  │   Redis Cache     │
                  │  (Hot Data)       │
                  └──────────────────┘
```

## 2. Conversation Flow for Venue Identification

### 2.1 Identification State Machine

```python
States:
1. INITIAL → Greeting and initial parsing
2. ASKING_VENUE_NAME → Collecting venue name
3. CONFIRMING_VENUE → Confirming single match
4. MULTIPLE_MATCHES → Handling multiple possibilities  
5. ASKING_PERSON_NAME → Collecting contact name
6. ASKING_POSITION → Collecting role/position
7. ASKING_ISSUE → Understanding the problem
8. IDENTIFIED → Ready for support
```

### 2.2 Sample Conversation Flow

```
Bot: "Hello! I'm the BMA Social support assistant. To help you effectively, 
     I need to identify your venue first. What's the name of your venue?"

User: "Hilton Bangkok"

Bot: "Is this your venue: Hilton Bangkok located at Sukhumvit Road? (Yes/No)"

User: "Yes"

Bot: "Perfect! Now, may I have your name, please?"

User: "John Smith"

Bot: "Thank you, John. What's your position at Hilton Bangkok?"

User: "Operations Manager"

Bot: "Thank you, John. I have you registered as Operations Manager at 
     Hilton Bangkok. How can I help you today?"

User: "The music in the lobby stopped playing this morning"

Bot: "✅ Venue Identified:
     • Venue: Hilton Bangkok
     • Contact: John Smith (Operations Manager)
     • Issue: Music stopped in lobby
     
     I'm now checking your venue's status and will help resolve this issue."
```

### 2.3 Fuzzy Matching Algorithm

```python
def calculate_venue_confidence(query: str, venue_name: str) -> float:
    # Direct match: 1.0
    if query.lower() == venue_name.lower():
        return 1.0
    
    # Substring match: 0.9
    if query.lower() in venue_name.lower():
        return 0.9
    
    # Levenshtein distance: 0.5-0.85
    similarity = SequenceMatcher(None, query.lower(), venue_name.lower()).ratio()
    
    # Boost for matching venue type keywords
    if any(keyword in both for keyword in ['hotel', 'restaurant', 'spa']):
        similarity += 0.1
    
    return min(similarity, 1.0)
```

## 3. Data Sources Integration

### 3.1 Google Sheets (Primary Source)

**Purpose**: Venue master data and configuration
**Sync Frequency**: Every 30 minutes
**Cache TTL**: 1 hour

**Data Structure**:
```
| Column | Field                  | Type    |
|--------|------------------------|---------|
| A      | venue_id              | Integer |
| B      | venue_name            | String  |
| C      | location              | String  |
| D      | contact_name          | String  |
| E      | contact_email         | String  |
| F      | contact_phone         | String  |
| G      | soundtrack_account_id | String  |
| H      | zone_count            | Integer |
| I      | subscription_status   | String  |
| J      | last_issue_date       | Date    |
| K      | notes                 | String  |
| L      | priority_level        | String  |
| M      | sla_tier              | String  |
```

### 3.2 Soundtrack API (Real-time Status)

**Purpose**: Live zone status and playback monitoring
**Polling Frequency**: Every 5 minutes per venue
**Cache TTL**: 5 minutes

**Key Endpoints**:
- `GET /accounts/{id}/status` - Overall account status
- `GET /accounts/{id}/zones` - Zone list and status
- `GET /zones/{id}/now-playing` - Current playback info
- `POST /zones/{id}/control` - Playback control

### 3.3 Gmail API (Correspondence History)

**Purpose**: Historical context and issue tracking
**Sync Frequency**: On-demand + 2-hour cache
**Cache TTL**: 2 hours

**Data Extracted**:
- Recent communications (last 30 days)
- Issue categories and urgency
- Response status
- Thread context

### 3.4 PostgreSQL Database (Local Cache)

**Purpose**: Persistent local storage and backup
**Tables**:
- `venues` - Venue master data
- `zones` - Zone configuration and status
- `conversations` - Chat history
- `sync_log` - Synchronization audit trail

## 4. Data Synchronization Strategy

### 4.1 Sync Priorities

```python
sync_config = {
    'venue_master': {
        'strategy': 'PERIODIC',
        'interval': timedelta(hours=1),
        'priority': 1,
        'sources': ['google_sheets']
    },
    'zone_status': {
        'strategy': 'REAL_TIME',
        'interval': timedelta(minutes=5),
        'priority': 2,
        'sources': ['soundtrack_api']
    },
    'email_history': {
        'strategy': 'LAZY',
        'interval': timedelta(hours=2),
        'priority': 3,
        'sources': ['gmail']
    }
}
```

### 4.2 Conflict Resolution

1. **Timestamp-based**: Newest data wins
2. **Source Priority**: Google Sheets > Soundtrack > Gmail > Database
3. **Manual Override**: Support team can force specific values

### 4.3 Sync Monitoring

```python
sync_metrics = {
    'last_successful_sync': datetime,
    'venues_synced': int,
    'sync_duration_ms': float,
    'error_count': int,
    'data_consistency_score': float  # 0-1
}
```

## 5. Caching Architecture

### 5.1 Multi-Layer Cache Strategy

```
Layer 1: Redis (Hot Data)
├── Venue identification results (30 min)
├── Active conversations (2 hours)
├── Zone status (5 min)
└── Common responses (1 hour)

Layer 2: PostgreSQL (Warm Data)
├── Venue master data (1 hour)
├── Historical conversations (permanent)
├── Issue patterns (24 hours)
└── Performance metrics (15 min)

Layer 3: Source Systems (Cold Data)
├── Google Sheets (master data)
├── Soundtrack API (real-time)
└── Gmail (history)
```

### 5.2 Cache Key Structure

```python
cache_keys = {
    'venue': 'venue:{venue_id}',
    'venue_search': 'search:{query}:{phone}',
    'zone_status': 'zone_status:{venue_id}',
    'conversation': 'conv:{conversation_id}',
    'response': 'response:{question_hash}',
    'sync_status': 'sync:{source}:{venue_id}'
}
```

### 5.3 Cache Invalidation

- **TTL-based**: Automatic expiration
- **Event-based**: On data updates
- **Manual**: Admin interface for forced refresh

## 6. Error Handling and Resilience

### 6.1 Circuit Breaker Pattern

```python
circuit_breaker_config = {
    'max_failures': 3,
    'recovery_timeout': 300,  # 5 minutes
    'expected_exception': RequestException
}
```

### 6.2 Fallback Strategies

1. **Google Sheets Unavailable**
   - Use cached data from PostgreSQL
   - Alert operations team
   - Continue with degraded service

2. **Soundtrack API Down**
   - Show last known status with timestamp
   - Queue control commands for retry
   - Notify user of temporary limitation

3. **Gmail Unavailable**
   - Skip email history enrichment
   - Continue with core functionality
   - Log for later analysis

### 6.3 Retry Logic

```python
retry_config = {
    'max_attempts': 3,
    'backoff_factor': 2,  # Exponential backoff
    'max_wait': 30,  # seconds
    'retry_on': [500, 502, 503, 504]
}
```

## 7. Scalability Considerations

### 7.1 Current Scale (2000 venues)

**Resource Requirements**:
- API calls: ~24,000/hour (5-min polling)
- Database queries: ~100,000/hour
- Cache memory: ~2GB Redis
- Network bandwidth: ~50 Mbps

**Performance Targets**:
- Venue identification: <2 seconds
- Status check: <500ms (cached)
- Full sync: <5 minutes

### 7.2 Target Scale (10,000 venues)

**Resource Projections**:
- API calls: ~120,000/hour
- Database queries: ~500,000/hour
- Cache memory: ~10GB Redis cluster
- Network bandwidth: ~250 Mbps

**Scaling Strategy**:
1. **Horizontal Scaling**
   - Multiple worker processes
   - Redis cluster with sharding
   - Read replicas for PostgreSQL

2. **Batch Processing**
   - Bulk API calls where possible
   - Aggregated database writes
   - Compressed data transfers

3. **Smart Polling**
   - Adaptive intervals based on venue activity
   - Priority queues for critical venues
   - Predictive pre-fetching

### 7.3 Database Optimization

```sql
-- Indexes for fast venue lookup
CREATE INDEX idx_venues_name ON venues(LOWER(name));
CREATE INDEX idx_venues_phone ON venues(phone_number);
CREATE INDEX idx_venues_soundtrack ON venues(soundtrack_account_id);

-- Partitioning for conversations
CREATE TABLE conversations_2025_01 PARTITION OF conversations
FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
```

## 8. Monitoring and Observability

### 8.1 Key Metrics

```python
metrics = {
    'venue_identification': {
        'success_rate': float,  # Target: >95%
        'avg_duration_ms': float,  # Target: <2000ms
        'retry_count': int
    },
    'data_sync': {
        'sync_lag_seconds': float,  # Target: <300s
        'consistency_score': float,  # Target: >99%
        'failed_syncs': int
    },
    'api_health': {
        'google_sheets_uptime': float,  # Target: >99%
        'soundtrack_api_uptime': float,  # Target: >99%
        'gmail_api_uptime': float  # Target: >95%
    }
}
```

### 8.2 Alerting Thresholds

- Venue identification failure rate >5%
- Sync lag >10 minutes
- API error rate >10%
- Cache hit rate <80%
- Response time >5 seconds

### 8.3 Logging Strategy

```python
log_levels = {
    'venue_identified': 'INFO',
    'sync_completed': 'INFO',
    'api_error': 'ERROR',
    'cache_miss': 'DEBUG',
    'circuit_breaker_open': 'WARNING'
}
```

## 9. Security Considerations

### 9.1 Data Protection

- **Encryption**: TLS for all API communications
- **Authentication**: OAuth2 for Google APIs, API keys for Soundtrack
- **Access Control**: Role-based permissions for venue data
- **Data Masking**: PII redaction in logs

### 9.2 Rate Limiting

```python
rate_limits = {
    'venue_search': '100/minute',
    'status_check': '1000/minute',
    'data_sync': '10/minute',
    'email_send': '50/hour'
}
```

## 10. Implementation Roadmap

### Phase 1: Core Integration (Week 1)
- [x] Venue Identifier with natural conversation
- [x] Google Sheets client
- [x] Data Aggregator framework
- [ ] Basic sync manager

### Phase 2: Real-time Features (Week 2)
- [ ] Soundtrack API integration
- [ ] Zone status monitoring
- [ ] Real-time alerts
- [ ] Performance optimization

### Phase 3: Enhancement (Week 3)
- [ ] Gmail integration
- [ ] Advanced caching
- [ ] Batch processing
- [ ] Analytics dashboard

### Phase 4: Scale Testing (Week 4)
- [ ] Load testing with 10,000 venues
- [ ] Performance tuning
- [ ] Monitoring setup
- [ ] Documentation completion

## 11. Cost Analysis

### Current (2000 venues)
- **Infrastructure**: $90/month
- **API Costs**: ~$50/month (Google APIs)
- **Total**: ~$140/month

### Projected (10,000 venues)
- **Infrastructure**: $500/month
- **API Costs**: ~$250/month
- **CDN/Bandwidth**: $100/month
- **Total**: ~$850/month

## 12. Conclusion

This integration architecture provides a robust, scalable foundation for BMA Social's AI bot system. The design prioritizes:

1. **User Experience**: Natural conversation flow for venue identification
2. **Reliability**: Multiple data sources with intelligent fallback
3. **Performance**: Multi-layer caching and optimization
4. **Scalability**: Ready for 5x growth without major refactoring
5. **Maintainability**: Clear separation of concerns and monitoring

The system is designed to maintain <1 minute response times for urgent issues while handling hundreds of simultaneous conversations across 10,000+ venues.
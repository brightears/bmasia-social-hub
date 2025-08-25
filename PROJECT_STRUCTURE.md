# Project Structure

```
bma-social/
├── README.md
├── TECHNICAL_SPECS.md
├── PROJECT_STRUCTURE.md
├── .env.example
├── .gitignore
├── docker-compose.yml
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app entry point
│   │   ├── config.py               # Configuration management
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── router.py       # Main API router
│   │   │       ├── endpoints/
│   │   │       │   ├── __init__.py
│   │   │       │   ├── auth.py
│   │   │       │   ├── venues.py
│   │   │       │   ├── zones.py
│   │   │       │   ├── conversations.py
│   │   │       │   ├── monitoring.py
│   │   │       │   ├── campaigns.py
│   │   │       │   ├── analytics.py
│   │   │       │   └── webhooks.py
│   │   │       └── dependencies/
│   │   │           ├── __init__.py
│   │   │           ├── auth.py
│   │   │           └── permissions.py
│   │   │
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── security.py         # JWT, authentication, hashing
│   │   │   ├── database.py         # Database connection & session
│   │   │   ├── redis.py            # Redis connection
│   │   │   ├── exceptions.py       # Custom exceptions
│   │   │   └── constants.py        # App-wide constants
│   │   │
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── base.py             # SQLAlchemy base model
│   │   │   ├── venue.py
│   │   │   ├── zone.py
│   │   │   ├── conversation.py
│   │   │   ├── message.py
│   │   │   ├── satisfaction.py
│   │   │   ├── campaign.py
│   │   │   ├── alert.py
│   │   │   └── team.py
│   │   │
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── venue.py            # Pydantic schemas
│   │   │   ├── zone.py
│   │   │   ├── conversation.py
│   │   │   ├── message.py
│   │   │   ├── satisfaction.py
│   │   │   ├── campaign.py
│   │   │   └── analytics.py
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── bot/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── engine.py       # Main bot logic & AI integration
│   │   │   │   ├── intents.py      # Intent recognition
│   │   │   │   ├── responses.py    # Response templates
│   │   │   │   ├── context.py      # Conversation context management
│   │   │   │   └── claude.py       # Claude API client
│   │   │   ├── soundtrack/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── client.py       # Soundtrack API client
│   │   │   │   ├── monitor.py      # Device monitoring service
│   │   │   │   ├── controls.py     # Music control operations
│   │   │   │   └── models.py       # Soundtrack data models
│   │   │   ├── messaging/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py         # Base messaging class
│   │   │   │   ├── whatsapp.py     # WhatsApp Business API
│   │   │   │   ├── line.py         # Line Business API
│   │   │   │   └── email.py        # Email service
│   │   │   ├── alerts/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── manager.py      # Alert management
│   │   │   │   ├── rules.py        # Alert rules engine
│   │   │   │   └── notifications.py # Notification dispatcher
│   │   │   └── analytics/
│   │   │       ├── __init__.py
│   │   │       ├── aggregator.py   # Data aggregation
│   │   │       ├── reports.py      # Report generation
│   │   │       └── metrics.py      # Metrics calculation
│   │   │
│   │   ├── workers/
│   │   │   ├── __init__.py
│   │   │   ├── celery_app.py       # Celery configuration
│   │   │   ├── tasks/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── monitoring.py   # Monitoring tasks
│   │   │   │   ├── campaigns.py    # Campaign tasks
│   │   │   │   ├── alerts.py       # Alert processing
│   │   │   │   └── reports.py      # Report generation
│   │   │   └── schedules.py        # Celery beat schedules
│   │   │
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── validators.py       # Input validation
│   │       ├── formatters.py       # Data formatting
│   │       ├── timezone.py         # Timezone handling
│   │       └── logger.py           # Logging configuration
│   │
│   ├── migrations/                  # Alembic migrations
│   │   ├── alembic.ini
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py             # Pytest fixtures
│   │   ├── unit/
│   │   │   ├── test_bot.py
│   │   │   ├── test_soundtrack.py
│   │   │   └── test_services.py
│   │   ├── integration/
│   │   │   ├── test_api.py
│   │   │   └── test_webhooks.py
│   │   └── fixtures/
│   │       └── sample_data.json
│   │
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── Dockerfile
│   └── .env.example
│
├── frontend-admin/                  # Admin Dashboard (React)
│   ├── public/
│   │   ├── index.html
│   │   └── favicon.ico
│   ├── src/
│   │   ├── index.tsx
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── common/
│   │   │   │   ├── Layout.tsx
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   ├── Header.tsx
│   │   │   │   └── LoadingSpinner.tsx
│   │   │   ├── monitoring/
│   │   │   │   ├── VenueGrid.tsx
│   │   │   │   ├── ZoneCard.tsx
│   │   │   │   ├── StatusIndicator.tsx
│   │   │   │   └── AlertPanel.tsx
│   │   │   ├── conversations/
│   │   │   │   ├── ConversationList.tsx
│   │   │   │   ├── MessageThread.tsx
│   │   │   │   ├── QuickActions.tsx
│   │   │   │   └── AssignmentModal.tsx
│   │   │   └── campaigns/
│   │   │       ├── CampaignBuilder.tsx
│   │   │       ├── TargetSelector.tsx
│   │   │       └── ScheduleForm.tsx
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Monitoring.tsx
│   │   │   ├── Conversations.tsx
│   │   │   ├── Campaigns.tsx
│   │   │   ├── Analytics.tsx
│   │   │   └── Settings.tsx
│   │   ├── services/
│   │   │   ├── api.ts              # API client
│   │   │   ├── auth.ts             # Authentication
│   │   │   ├── websocket.ts        # Real-time updates
│   │   │   └── types.ts            # TypeScript types
│   │   ├── store/
│   │   │   ├── index.ts            # Redux store
│   │   │   ├── slices/
│   │   │   │   ├── auth.ts
│   │   │   │   ├── venues.ts
│   │   │   │   └── monitoring.ts
│   │   │   └── middleware/
│   │   │       └── api.ts
│   │   ├── hooks/
│   │   │   ├── useAuth.ts
│   │   │   ├── useWebSocket.ts
│   │   │   └── usePolling.ts
│   │   ├── utils/
│   │   │   ├── constants.ts
│   │   │   ├── formatters.ts
│   │   │   └── validators.ts
│   │   └── styles/
│   │       ├── theme.ts
│   │       └── global.css
│   ├── package.json
│   ├── tsconfig.json
│   ├── .env.example
│   └── Dockerfile
│
├── frontend-portal/                 # Corporate Portal (React)
│   ├── public/
│   │   ├── index.html
│   │   └── favicon.ico
│   ├── src/
│   │   ├── index.tsx
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── common/
│   │   │   │   ├── Layout.tsx
│   │   │   │   ├── Navigation.tsx
│   │   │   │   └── Footer.tsx
│   │   │   ├── dashboard/
│   │   │   │   ├── SatisfactionChart.tsx
│   │   │   │   ├── UptimeChart.tsx
│   │   │   │   ├── PropertyRanking.tsx
│   │   │   │   └── KPICards.tsx
│   │   │   ├── reports/
│   │   │   │   ├── ReportBuilder.tsx
│   │   │   │   ├── ExportButton.tsx
│   │   │   │   └── ReportViewer.tsx
│   │   │   └── analytics/
│   │   │       ├── TrendAnalysis.tsx
│   │   │       ├── Comparison.tsx
│   │   │       └── Filters.tsx
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Properties.tsx
│   │   │   ├── Analytics.tsx
│   │   │   ├── Reports.tsx
│   │   │   └── Profile.tsx
│   │   ├── services/
│   │   │   ├── api.ts
│   │   │   ├── auth.ts
│   │   │   └── export.ts           # PDF export
│   │   ├── hooks/
│   │   │   ├── useAnalytics.ts
│   │   │   └── useExport.ts
│   │   ├── utils/
│   │   │   ├── charts.ts           # Chart configurations
│   │   │   └── permissions.ts      # Access control
│   │   └── styles/
│   │       └── theme.ts
│   ├── package.json
│   ├── tsconfig.json
│   └── Dockerfile
│
├── scripts/
│   ├── import_venues.py            # Import existing venues from CSV/API
│   ├── test_soundtrack_api.py      # Test Soundtrack integration
│   ├── simulate_load.py            # Load testing script
│   ├── backup_database.sh          # Database backup
│   ├── deploy.sh                   # Deployment script
│   └── seed_data.py                # Seed test data
│
├── docs/
│   ├── API.md                      # API documentation
│   ├── DEPLOYMENT.md               # Deployment guide
│   ├── TROUBLESHOOTING.md          # Common issues & solutions
│   ├── BOT_INTENTS.md              # Bot conversation flows
│   └── INTEGRATION_GUIDE.md        # Third-party integration guide
│
├── .github/
│   └── workflows/
│       ├── ci.yml                  # CI pipeline
│       ├── deploy.yml              # CD pipeline
│       └── security.yml            # Security scanning
│
└── infrastructure/
    ├── terraform/                   # Infrastructure as Code (optional)
    │   ├── main.tf
    │   ├── variables.tf
    │   └── outputs.tf
    └── kubernetes/                  # K8s configs (optional)
        ├── deployment.yaml
        ├── service.yaml
        └── ingress.yaml
```

## Key Directories Explained

### `/backend/app/services/bot/`
The core AI bot logic that powers all intelligent conversations:
- **engine.py**: Main orchestrator that processes messages and determines actions
- **intents.py**: NLP for understanding user requests (volume changes, playlist requests, etc.)
- **responses.py**: Template system for generating natural responses
- **context.py**: Maintains conversation history and venue context
- **claude.py**: Direct integration with Claude API for complex queries

### `/backend/app/services/soundtrack/`
Integration with Soundtrack Your Brand API:
- **client.py**: API wrapper for all Soundtrack operations
- **monitor.py**: Continuous polling service checking device status
- **controls.py**: Volume, playlist, and schedule management
- **models.py**: Data models for devices, playlists, and zones

### `/backend/app/services/messaging/`
Multi-channel communication handling:
- **whatsapp.py**: WhatsApp Business API integration
- **line.py**: Line Business API integration
- **email.py**: Email service for reports and alerts
- **base.py**: Common messaging interface for all channels

### `/backend/app/workers/`
Background job processing with Celery:
- **monitoring.py**: Polls all venues every 5-10 minutes
- **campaigns.py**: Sends bulk messages and tracks engagement
- **alerts.py**: Processes and dispatches urgent notifications
- **reports.py**: Generates scheduled reports for corporate clients

### `/frontend-admin/`
Internal dashboard for BMAsia team:
- Real-time monitoring grid showing all 2000+ venues
- Conversation management with routing capabilities
- Campaign creation and scheduling tools
- Team performance metrics and analytics

### `/frontend-portal/`
Client-facing portal for corporate customers:
- Satisfaction dashboards with drill-down capabilities
- Music analytics showing uptime and compliance
- Custom report builder with PDF export
- Multi-level access control (corporate/regional/property)

### `/scripts/`
Operational and utility scripts:
- **import_venues.py**: Migrates existing venue data
- **test_soundtrack_api.py**: Validates API integration
- **simulate_load.py**: Performance testing
- **seed_data.py**: Creates test data for development

## Development Workflow

### Local Development Setup
1. Backend runs on port 8000 (FastAPI with auto-reload)
2. Admin frontend on port 3000
3. Portal frontend on port 3001
4. Redis on port 6379
5. PostgreSQL on port 5432

### Code Organization Principles
- **Models**: SQLAlchemy ORM models define database structure
- **Schemas**: Pydantic models for API validation and serialization
- **Services**: Business logic separated from API endpoints
- **Workers**: Async tasks that don't block API responses
- **Utils**: Reusable helper functions

### Testing Structure
- **Unit tests**: Test individual functions and classes
- **Integration tests**: Test API endpoints and service interactions
- **Fixtures**: Shared test data for consistency

### Configuration Management
- Environment variables for secrets and deployment-specific settings
- Config classes for structured configuration
- `.env.example` files as templates for required variables

## Module Responsibilities

### Backend Core Modules
| Module | Responsibility |
|--------|---------------|
| `api/` | HTTP endpoints and request handling |
| `core/` | Fundamental app services (auth, db, security) |
| `models/` | Database table definitions |
| `schemas/` | API request/response models |
| `services/` | Business logic and external integrations |
| `workers/` | Background job processing |
| `utils/` | Helper functions and utilities |

### Frontend Module Structure
| Module | Responsibility |
|--------|---------------|
| `components/` | Reusable UI components |
| `pages/` | Full page components/routes |
| `services/` | API communication and data fetching |
| `store/` | State management (Redux) |
| `hooks/` | Custom React hooks |
| `utils/` | Helper functions |
| `styles/` | Theme and global styles |

## File Naming Conventions

- **Python files**: `snake_case.py`
- **React components**: `PascalCase.tsx`
- **Utilities/hooks**: `camelCase.ts`
- **Constants**: `UPPER_SNAKE_CASE`
- **CSS/Styles**: `kebab-case.css`

## Import Structure

### Python Imports
```python
# Standard library
import os
import json

# Third-party
from fastapi import FastAPI
from sqlalchemy import create_engine

# Local application
from app.core.database import get_db
from app.services.bot.engine import BotEngine
```

### TypeScript Imports
```typescript
// React and third-party
import React from 'react';
import { useSelector } from 'react-redux';

// Local components
import Layout from '@/components/common/Layout';

// Services and utilities
import { api } from '@/services/api';
import { formatDate } from '@/utils/formatters';
```
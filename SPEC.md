# Specification: Python backend developer to build robust integration with GTN Trade API and GTN WebSocket, synchronizing trading and account data into SQL Server. Three Python services: (1) Get Orders API Import, (2) WebSocket Spool Listener, (3) WebSocket Spool Processor. Uses official GTN documentation for Order Search API and Trade API Events WebSocket. Requires auto-creating system tables (tbl_system_service, tbl_system_service_exec, tbl_system_service_debug), dynamic schema handling, and comprehensive audit logging.

## 1. Project Overview

**Project:** Python backend developer to build robust integration with GTN Trade API and GTN WebSocket, synchronizing trading and account data into SQL Server. Three Python services: (1) Get Orders API Import, (2) WebSocket Spool Listener, (3) WebSocket Spool Processor. Uses official GTN documentation for Order Search API and Trade API Events WebSocket. Requires auto-creating system tables (tbl_system_service, tbl_system_service_exec, tbl_system_service_debug), dynamic schema handling, and comprehensive audit logging.
**GitHub:** https://github.com/9KMan/JOB-20260602144428-000063
**Lead:** Less than 30 hrs/week
**Client:** GTN Trade API Integration
**Tier:** MEDIUM
**Budget:** hourly ($15-35/hr, <30hrs/wk, <1mo, contract-to-hire)
**Rate:** $15-35/hr

## 2. Technical Stack

python · sql-server · odbc · websockets · api-integration · json · rest-api · etl · audit-logging

## 3. Architecture

- Backend: Python (FastAPI/Flask) REST API
- Database: PostgreSQL with proper indexing

### API Design
- RESTful endpoints with JSON request/response
- Authentication via JWT (HS256) or bcrypt
- Middleware for logging, error handling, CORS
- Versioned routes (/api/v1/...)

### Data Layer
- PostgreSQL as primary datastore
- Connection pooling via PGBouncer or similar
- Migration management via Alembic or raw SQL
- Indexes on foreign keys and high-cardinality columns

### Frontend (if applicable)
- Single-page application or server-rendered pages
- Responsive UI with modern CSS/JS framework
- State management for complex client-side logic

## 4. Data Model

### Core Entities
- Define entity schema based on job requirements
- Use UUIDs for primary keys (not auto-increment)
- Add created_at / updated_at timestamps to all tables
- Soft-delete pattern where appropriate

### Relationships
- Foreign key constraints with ON DELETE CASCADE
- Many-to-many via junction tables
- Eager loading for nested relationships in API

## 5. Project Structure

```
├── api/                  # FastAPI / Express routes + schemas
├── models/               # DB models / SQLAlchemy / Prisma
├── services/             # Business logic layer
├── workers/              # Background jobs (Celery, BullMQ, etc.)
├── migrations/           # DB migrations (Alembic / Flyway)
├── tests/                # Unit + integration tests
├── Dockerfile            # Production container
├── docker-compose.yml     # Local dev environment
└── README.md             # Setup instructions
```

## 6. Out of Scope

- Mobile apps (web only unless specified)
- Third-party integrations not mentioned in requirements
- Performance optimization at scale (1M+ users)
- White-label / multi-tenant unless explicitly required

## 7. Acceptance Criteria

- [ ] REST API with all planned endpoints implemented
- [ ] Database schema created and migrations applied
- [ ] Frontend UI implemented and responsive
- [ ] README with setup and run instructions

**GitHub:** https://github.com/9KMan/JOB-20260602144428-000063

# Plan 5: 5. Project Structure

## Objective
5. Project Structure

## Steps

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


## Files
- Create files as needed for: 5. Project Structure

## Done When
- All referenced files exist
- Code compiles/parses
- Atomic git commit created

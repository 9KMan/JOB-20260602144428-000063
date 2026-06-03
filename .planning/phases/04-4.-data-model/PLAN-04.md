# Plan 4: 4. Data Model

## Objective
4. Data Model

## Steps

### Core Entities
- Define entity schema based on job requirements
- Use UUIDs for primary keys (not auto-increment)
- Add created_at / updated_at timestamps to all tables
- Soft-delete pattern where appropriate

### Relationships
- Foreign key constraints with ON DELETE CASCADE
- Many-to-many via junction tables
- Eager loading for nested relationships in API


## Files
- Create files as needed for: 4. Data Model

## Done When
- All referenced files exist
- Code compiles/parses
- Atomic git commit created

# Database Migrations

## Version Control

Migrations are versioned as `NNN_description.sql`. Run in order.

## Migration Order

1. `../schema/001_initial_schema.sql` - Core tables
2. `../seeds/001_seed_foods_from_datasets.sql` - Initial food data

## Rollback

Run `rollback_001.sql` to revert the initial schema. **Warning**: This drops all data.

## Migration Tool (Alembic / node-pg-migrate)

For production, use a migration tool:

- **Node.js**: `node-pg-migrate` or `db-migrate`
- **Python**: Alembic (if using Python ORM)

## Automated Tests

Run schema validation:

```bash
psql $DATABASE_URL -f database/schema/001_initial_schema.sql --dry-run
```

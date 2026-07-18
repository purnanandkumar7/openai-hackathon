# Database Migrations

Atlas AI uses [Alembic](https://alembic.sqlalchemy.org/) for database schema migrations.

## Setup

Alembic is pre-configured to use the `DATABASE_URL` environment variable.
Initialise the migrations directory (first time only):

```bash
alembic init app/db/migrations
```

Edit `alembic.ini` to set:
```ini
script_location = app/db/migrations
```

Edit `app/db/migrations/env.py` to import the SQLAlchemy `Base` and `DATABASE_URL`:

```python
from app.db.database import Base
from app.config import get_settings

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
target_metadata = Base.metadata
```

## Common Commands

```bash
# Generate a new migration after model changes
alembic revision --autogenerate -m "add_incident_labels"

# Apply all pending migrations
alembic upgrade head

# Roll back one migration
alembic downgrade -1

# Show current revision
alembic current

# Show migration history
alembic history --verbose
```

## Development

In development, `init_db()` calls `Base.metadata.create_all()` which creates
tables automatically without running migrations. Use Alembic only in staging
and production environments.

## Production Deployment

Run migrations as a Kubernetes init container or a pre-deploy job:

```yaml
initContainers:
  - name: db-migrate
    image: atlas-ai-backend:latest
    command: ["alembic", "upgrade", "head"]
    env:
      - name: DATABASE_URL
        valueFrom:
          secretKeyRef:
            name: atlas-ai-secrets
            key: DATABASE_URL
```

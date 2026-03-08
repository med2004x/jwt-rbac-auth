# JWT RBAC Auth

JWT RBAC Auth is a compact authentication control plane for internal platform services that need short-lived access tokens, refresh rotation, and explicit admin-driven role assignment. It is designed to demonstrate a production-style auth boundary rather than a toy login form.

## Problem Statement
Teams often bolt authorization onto a service after the fact, which leads to hardcoded roles, refresh-token reuse, and poor auditability around privileged changes. This project solves that by combining token rotation, Redis-backed revocation, and explicit audit events for administrative role updates in one service.

## Architecture
The component topology and runtime flows are documented in [`docs/diagrams/architecture.mmd`](docs/diagrams/architecture.mmd).

## Key Design Decisions
- Access tokens stay short-lived while refresh tokens are rotated on every use to constrain replay windows.
- Redis stores active refresh token identifiers and revoked token identifiers so rotation remains fast without adding a join-heavy lookup path to PostgreSQL.
- Role changes require an admin token and emit an audit event asynchronously to avoid blocking the control path on secondary work.
- Middleware is used for request logging, token parsing, and exception normalization so handlers stay focused on auth rules.
- SQL migrations are committed as raw SQL to keep the schema history explicit and easy to inspect.

## Tech Stack
- Python 3.12
- FastAPI 0.115
- SQLAlchemy 2.0 with asyncpg
- PostgreSQL 16
- Redis 7
- PyJWT 2.10
- passlib[bcrypt] 1.7

## How It Works
`POST /auth/register` creates a user with a hashed password and the default `member` role. `POST /auth/login` verifies credentials, issues an access token and refresh token pair, and registers the refresh token identifier in Redis. `POST /auth/refresh` rotates the refresh token by revoking the old identifier and minting a fresh pair. `POST /admin/users/{user_id}/role` is guarded by the admin role and emits an audit event into Redis using a background task.

## Scalability Model
The service is stateless from the HTTP tier perspective, so it scales horizontally behind a load balancer. PostgreSQL is the source of truth for user records while Redis handles high-churn token state. The primary bottleneck becomes password verification and login volume, followed by PostgreSQL write throughput for user and audit history growth.

## Running Locally
```bash
docker compose up --build
```

In a second shell:

```bash
curl http://localhost:8080/healthz
```

## Configuration
- `APP_NAME`: service name injected into logs and health responses
- `APP_HOST`: bind host for local execution outside Docker
- `APP_PORT`: bind port for local execution outside Docker
- `DATABASE_URL`: async SQLAlchemy connection string
- `MIGRATION_DATABASE_URL`: sync PostgreSQL connection string for the migration script
- `REDIS_URL`: Redis connection for token rotation and audit event publishing
- `JWT_ISSUER`: issuer claim written into every token
- `JWT_AUDIENCE`: audience claim required during token verification
- `JWT_SECRET_KEY`: symmetric signing key for access and refresh tokens
- `ACCESS_TOKEN_TTL_SECONDS`: lifetime for access tokens
- `REFRESH_TOKEN_TTL_SECONDS`: lifetime for refresh tokens
- `DEFAULT_ADMIN_EMAIL`: bootstrap admin account email
- `DEFAULT_ADMIN_PASSWORD`: bootstrap admin account password
- `LOG_LEVEL`: structured logging level

## API Reference or CLI Usage
Sample requests live in [`examples/curl.http`](examples/curl.http). A typical login flow looks like:

```bash
curl -X POST http://localhost:8080/auth/login \
  -H "content-type: application/json" \
  -d '{"email":"admin@example.com","password":"AdminPass123!"}'
```

## Tests
```bash
pip install -r src/requirements.txt
python -m pytest tests -q
```

The tests cover token rotation and admin role assignment with audit event publication.

## License
MIT


# Architecture Overview

`jwt-rbac-auth` is organized around three runtime concerns:

1. FastAPI handles authentication, identity lookups, and privileged role changes.
2. PostgreSQL stores durable user and audit history.
3. Redis stores refresh-token state and receives audit events from background tasks.

The service bootstraps a default admin account at startup so local environments can exercise the full RBAC flow immediately. Middleware is applied globally for logging, exception normalization, and best-effort bearer-token parsing.


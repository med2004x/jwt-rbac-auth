from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
import structlog

from app.main import RuntimeOverrides, build_application
from app.models import Base
from app.services.stores import TokenStore
from app.services.tokens import TokenService
from app.config import Settings


class InMemoryTokenStore(TokenStore):
    def __init__(self) -> None:
        self._active_refresh_tokens: dict[str, int] = {}
        self.audit_events: list[dict[str, str]] = []

    async def store_refresh_token(self, token_identifier: str, user_id: int, ttl_seconds: int) -> None:
        self._active_refresh_tokens[token_identifier] = user_id

    async def is_refresh_token_active(self, token_identifier: str) -> bool:
        return token_identifier in self._active_refresh_tokens

    async def revoke_refresh_token(self, token_identifier: str, ttl_seconds: int) -> None:
        self._active_refresh_tokens.pop(token_identifier, None)

    async def publish_audit_event(self, event_name: str, event_payload: dict[str, str]) -> None:
        self.audit_events.append({"event_name": event_name, **event_payload})

    async def read_audit_events(self) -> list[dict[str, str]]:
        return list(self.audit_events)


@pytest_asyncio.fixture()
async def test_client(tmp_path: Path) -> AsyncIterator[tuple[AsyncClient, InMemoryTokenStore]]:
    database_path = tmp_path / "auth.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    token_store = InMemoryTokenStore()
    test_settings = Settings(
        APP_NAME="jwt-rbac-auth-test",
        APP_HOST="127.0.0.1",
        APP_PORT=8080,
        DATABASE_URL=f"sqlite+aiosqlite:///{database_path}",
        MIGRATION_DATABASE_URL=f"sqlite:///{database_path}",
        REDIS_URL="redis://unused:6379/0",
        JWT_ISSUER="jwt-rbac-auth-test",
        JWT_AUDIENCE="portfolio-tests",
        JWT_SECRET_KEY="development-secret",
        ACCESS_TOKEN_TTL_SECONDS=900,
        REFRESH_TOKEN_TTL_SECONDS=3600,
        DEFAULT_ADMIN_EMAIL="admin@example.com",
        DEFAULT_ADMIN_PASSWORD="AdminPass123!",
        LOG_LEVEL="INFO",
    )
    token_service = TokenService(
        secret_key=test_settings.jwt_secret_key,
        issuer=test_settings.jwt_issuer,
        audience=test_settings.jwt_audience,
        access_ttl_seconds=test_settings.access_token_ttl_seconds,
        refresh_ttl_seconds=test_settings.refresh_token_ttl_seconds,
    )
    runtime_overrides = RuntimeOverrides(
        settings=test_settings,
        engine=engine,
        session_factory=session_factory,
        token_store=token_store,
        token_service=token_service,
        logger=structlog.get_logger("jwt-rbac-auth-test"),
        redis_client=None,
    )
    application = build_application(runtime_overrides=runtime_overrides)

    async with application.router.lifespan_context(application):
        transport = ASGITransport(app=application)
        async with AsyncClient(transport=transport, base_url="http://testserver") as api_client:
            yield api_client, token_store


@pytest.mark.asyncio
async def test_register_login_refresh_and_me(test_client: tuple[AsyncClient, InMemoryTokenStore]) -> None:
    api_client, _ = test_client

    registration_response = await api_client.post(
        "/auth/register",
        json={"email": "analyst@example.com", "password": "StrongSecret123!"},
    )
    assert registration_response.status_code == 201

    login_response = await api_client.post(
        "/auth/login",
        json={"email": "analyst@example.com", "password": "StrongSecret123!"},
    )
    assert login_response.status_code == 200
    token_payload = login_response.json()

    me_response = await api_client.get("/auth/me", headers={"authorization": f"Bearer {token_payload['access_token']}"})
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "analyst@example.com"

    refresh_response = await api_client.post("/auth/refresh", json={"refresh_token": token_payload["refresh_token"]})
    assert refresh_response.status_code == 200
    rotated_payload = refresh_response.json()
    assert rotated_payload["refresh_token"] != token_payload["refresh_token"]

    stale_refresh_response = await api_client.post("/auth/refresh", json={"refresh_token": token_payload["refresh_token"]})
    assert stale_refresh_response.status_code == 401


@pytest.mark.asyncio
async def test_admin_role_assignment_publishes_audit_event(test_client: tuple[AsyncClient, InMemoryTokenStore]) -> None:
    api_client, token_store = test_client

    await api_client.post("/auth/register", json={"email": "member@example.com", "password": "StrongSecret123!"})
    admin_login_response = await api_client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": "AdminPass123!"},
    )
    admin_access_token = admin_login_response.json()["access_token"]

    role_response = await api_client.post(
        "/admin/users/2/role",
        json={"role": "support"},
        headers={"authorization": f"Bearer {admin_access_token}"},
    )
    assert role_response.status_code == 200
    assert role_response.json()["role"] == "support"
    assert token_store.audit_events[0]["target_email"] == "member@example.com"

from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastapi import FastAPI
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
import structlog

from app.config import Settings, get_settings
from app.database import build_engine, build_session_factory
from app.middleware.auth import auth_middleware
from app.middleware.errors import error_middleware
from app.middleware.logging import logging_middleware
from app.models import UserRecord, UserRole
from app.routers.auth import router as auth_router
from app.services.auth import AuthService
from app.services.passwords import PasswordService
from app.services.stores import RedisTokenStore
from app.services.tokens import TokenService


@dataclass
class RuntimeOverrides:
    settings: Settings
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    token_store: object
    token_service: TokenService
    logger: object
    redis_client: object | None = None


async def _ensure_admin_user(database_session: AsyncSession, settings: Settings) -> None:
    existing_admin = await database_session.execute(select(UserRecord).where(UserRecord.email == settings.default_admin_email))
    admin_record = existing_admin.scalar_one_or_none()
    if admin_record is not None:
        return
    password_service = PasswordService()
    bootstrap_admin = UserRecord(
        email=settings.default_admin_email,
        password_hash=password_service.hash_password(settings.default_admin_password),
        role=UserRole.ADMIN,
    )
    database_session.add(bootstrap_admin)
    await database_session.commit()


@asynccontextmanager
async def lifespan(application: FastAPI):
    overrides: RuntimeOverrides | None = getattr(application.state, "runtime_overrides", None)
    if overrides is None:
        settings = get_settings()
        structlog.configure(
            processors=[
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.add_log_level,
                structlog.processors.JSONRenderer(),
            ]
        )
        logger = structlog.get_logger(settings.app_name)
        engine = build_engine(settings.database_url)
        session_factory = build_session_factory(engine)
        redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
        token_service = TokenService(
            secret_key=settings.jwt_secret_key,
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            access_ttl_seconds=settings.access_token_ttl_seconds,
            refresh_ttl_seconds=settings.refresh_token_ttl_seconds,
        )
        token_store = RedisTokenStore(redis_client)
    else:
        settings = overrides.settings
        logger = overrides.logger
        engine = overrides.engine
        session_factory = overrides.session_factory
        redis_client = overrides.redis_client
        token_service = overrides.token_service
        token_store = overrides.token_store
    application.state.settings = settings
    application.state.logger = logger
    application.state.engine = engine
    application.state.session_factory = session_factory
    application.state.redis = redis_client
    application.state.token_service = token_service
    application.state.token_store = token_store
    application.state.auth_service = AuthService(PasswordService(), token_service, token_store)
    async with session_factory() as database_session:
        await _ensure_admin_user(database_session, settings)
    yield
    if redis_client is not None:
        await redis_client.aclose()
    await engine.dispose()


def build_application(runtime_overrides: RuntimeOverrides | None = None) -> FastAPI:
    application = FastAPI(title="JWT RBAC Auth", lifespan=lifespan)
    application.state.runtime_overrides = runtime_overrides
    application.add_middleware(BaseHTTPMiddleware, dispatch=error_middleware)
    application.add_middleware(BaseHTTPMiddleware, dispatch=logging_middleware)
    application.add_middleware(BaseHTTPMiddleware, dispatch=auth_middleware)
    application.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    application.include_router(auth_router)
    return application


app = build_application()

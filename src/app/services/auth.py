import json

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditEventRecord, UserRecord, UserRole
from app.schemas import RoleValue
from app.services.passwords import PasswordService
from app.services.stores import TokenStore
from app.services.tokens import TokenSubject, TokenService


class AuthService:
    def __init__(
        self,
        password_service: PasswordService,
        token_service: TokenService,
        token_store: TokenStore,
    ) -> None:
        self._password_service = password_service
        self._token_service = token_service
        self._token_store = token_store

    async def register_user(self, database_session: AsyncSession, email: str, password: str) -> UserRecord:
        user_record = UserRecord(email=email.lower(), password_hash=self._password_service.hash_password(password))
        database_session.add(user_record)
        try:
            await database_session.commit()
        except IntegrityError as exc:
            await database_session.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists") from exc
        await database_session.refresh(user_record)
        return user_record

    async def authenticate(self, database_session: AsyncSession, email: str, password: str) -> tuple[str, str]:
        lookup_statement = select(UserRecord).where(UserRecord.email == email.lower())
        lookup_result = await database_session.execute(lookup_statement)
        user_record = lookup_result.scalar_one_or_none()
        if user_record is None or not self._password_service.verify_password(password, user_record.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        token_subject = TokenSubject(user_id=user_record.id, email=user_record.email, role=user_record.role.value)
        access_token = self._token_service.issue_access_token(token_subject)
        refresh_token, token_identifier = self._token_service.issue_refresh_token(token_subject)
        await self._token_store.store_refresh_token(
            token_identifier=token_identifier,
            user_id=user_record.id,
            ttl_seconds=self._token_service.refresh_ttl_seconds,
        )
        return access_token, refresh_token

    async def refresh_tokens(self, refresh_token: str) -> tuple[str, str]:
        token_subject, token_identifier = self._token_service.decode_refresh_token(refresh_token)
        if not await self._token_store.is_refresh_token_active(token_identifier):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token is not active")

        await self._token_store.revoke_refresh_token(
            token_identifier=token_identifier,
            ttl_seconds=self._token_service.refresh_ttl_seconds,
        )
        access_token = self._token_service.issue_access_token(token_subject)
        rotated_refresh_token, rotated_identifier = self._token_service.issue_refresh_token(token_subject)
        await self._token_store.store_refresh_token(
            token_identifier=rotated_identifier,
            user_id=token_subject.user_id,
            ttl_seconds=self._token_service.refresh_ttl_seconds,
        )
        return access_token, rotated_refresh_token

    async def assign_role(
        self,
        database_session: AsyncSession,
        actor_email: str,
        target_user_id: int,
        requested_role: RoleValue,
    ) -> UserRecord:
        target_user = await database_session.get(UserRecord, target_user_id)
        if target_user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        target_user.role = UserRole(requested_role.value)
        database_session.add(target_user)
        database_session.add(
            AuditEventRecord(
                actor_email=actor_email,
                target_email=target_user.email,
                event_type="role-assigned",
                event_payload=json.dumps({"role": requested_role.value}),
            )
        )
        await database_session.commit()
        await database_session.refresh(target_user)
        return target_user


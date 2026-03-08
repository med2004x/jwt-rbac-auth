from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserRecord, UserRole
from app.services.tokens import TokenSubject


async def get_database_session(request: Request) -> AsyncSession:
    session_factory = request.app.state.session_factory
    async with session_factory() as database_session:
        yield database_session


async def require_authenticated_user(
    request: Request,
    database_session: AsyncSession = Depends(get_database_session),
) -> UserRecord:
    token_subject: TokenSubject | None = getattr(request.state, "token_subject", None)
    if token_subject is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    user_record = await database_session.get(UserRecord, token_subject.user_id)
    if user_record is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown token subject")
    return user_record


async def require_admin_user(
    authenticated_user: UserRecord = Depends(require_authenticated_user),
) -> UserRecord:
    if authenticated_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return authenticated_user


from fastapi import APIRouter, BackgroundTasks, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_database_session, require_admin_user, require_authenticated_user
from app.models import UserRecord
from app.schemas import (
    HealthResponse,
    LoginRequest,
    RefreshRequest,
    RegistrationRequest,
    RoleAssignmentRequest,
    TokenPairResponse,
    UserResponse,
)

router = APIRouter()


@router.get("/healthz", response_model=HealthResponse)
async def health_check(request: Request) -> HealthResponse:
    return HealthResponse(service=request.app.state.settings.app_name, status="ok")


@router.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    registration_payload: RegistrationRequest,
    request: Request,
    database_session: AsyncSession = Depends(get_database_session),
) -> UserResponse:
    created_user = await request.app.state.auth_service.register_user(
        database_session,
        registration_payload.email,
        registration_payload.password,
    )
    return UserResponse.model_validate(created_user)


@router.post("/auth/login", response_model=TokenPairResponse)
async def login_user(
    login_payload: LoginRequest,
    request: Request,
    database_session: AsyncSession = Depends(get_database_session),
) -> TokenPairResponse:
    access_token, refresh_token = await request.app.state.auth_service.authenticate(
        database_session, login_payload.email, login_payload.password
    )
    return TokenPairResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=request.app.state.settings.access_token_ttl_seconds,
    )


@router.post("/auth/refresh", response_model=TokenPairResponse)
async def refresh_token_pair(refresh_payload: RefreshRequest, request: Request) -> TokenPairResponse:
    access_token, refresh_token = await request.app.state.auth_service.refresh_tokens(refresh_payload.refresh_token)
    return TokenPairResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=request.app.state.settings.access_token_ttl_seconds,
    )


@router.get("/auth/me", response_model=UserResponse)
async def fetch_current_user(
    authenticated_user: UserRecord = Depends(require_authenticated_user),
) -> UserResponse:
    return UserResponse.model_validate(authenticated_user)


@router.post("/admin/users/{target_user_id}/role", response_model=UserResponse)
async def update_user_role(
    target_user_id: int,
    role_assignment: RoleAssignmentRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    admin_user: UserRecord = Depends(require_admin_user),
    database_session: AsyncSession = Depends(get_database_session),
) -> UserResponse:
    updated_user = await request.app.state.auth_service.assign_role(
        database_session,
        actor_email=admin_user.email,
        target_user_id=target_user_id,
        requested_role=role_assignment.role,
    )
    background_tasks.add_task(
        request.app.state.token_store.publish_audit_event,
        "role-assigned",
        {
            "actor_email": admin_user.email,
            "target_email": updated_user.email,
            "role": updated_user.role.value,
        },
    )
    return UserResponse.model_validate(updated_user)


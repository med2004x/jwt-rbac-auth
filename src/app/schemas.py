from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RoleValue(StrEnum):
    ADMIN = "admin"
    MEMBER = "member"
    SUPPORT = "support"


class RegistrationRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=32)


class RoleAssignmentRequest(BaseModel):
    role: RoleValue


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    role: RoleValue
    created_at: datetime


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class HealthResponse(BaseModel):
    service: str
    status: str


import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class UserResponse(BaseModel):
    """Safe public representation of an authenticated user."""
    id: uuid.UUID
    github_user_id: str
    github_login: str
    name: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuthStatusResponse(BaseModel):
    """Authentication status check response."""
    authenticated: bool
    user: Optional[UserResponse] = None


class MessageResponse(BaseModel):
    """Standard message response."""
    message: str

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.security import generate_session_token, hash_session_token
from app.models.user import User
from app.models.user_session import UserSession


def create_user_session(db: Session, user_id: uuid.UUID) -> Tuple[str, UserSession]:
    """
    Creates a new database-backed user session.
    Generates a secure raw token, stores ONLY its SHA-256 digest in the database,
    and returns (raw_token, session_record).
    """
    raw_token = generate_session_token()
    token_hash = hash_session_token(raw_token)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=settings.SESSION_EXPIRE_SECONDS)

    session_record = UserSession(
        id=uuid.uuid4(),
        user_id=user_id,
        token_hash=token_hash,
        created_at=now,
        expires_at=expires_at,
        is_revoked=False
    )
    db.add(session_record)
    db.commit()
    db.refresh(session_record)
    return raw_token, session_record


def get_valid_session_user(db: Session, raw_token: str) -> Optional[User]:
    """
    Validates a session by computing the SHA-256 hash of the incoming raw token
    and looking up an active, unrevoked, unexpired session in PostgreSQL.
    Returns the associated User if valid, or None.
    """
    if not raw_token:
        return None

    token_hash = hash_session_token(raw_token)
    now = datetime.now(timezone.utc)

    stmt = (
        select(UserSession)
        .options(joinedload(UserSession.user))
        .where(
            UserSession.token_hash == token_hash,
            UserSession.is_revoked.is_(False),
            UserSession.expires_at > now
        )
    )
    session = db.scalars(stmt).first()
    if not session or not session.user:
        return None

    return session.user


def revoke_session(db: Session, raw_token: str) -> bool:
    """
    Revokes a session server-side by marking is_revoked = True in PostgreSQL.
    Any future attempts to use this session token will be rejected immediately.
    """
    if not raw_token:
        return False

    token_hash = hash_session_token(raw_token)
    stmt = select(UserSession).where(UserSession.token_hash == token_hash)
    session = db.scalars(stmt).first()
    if session and not session.is_revoked:
        session.is_revoked = True
        db.commit()
        return True
    return False

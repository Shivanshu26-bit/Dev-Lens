import logging
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings

logger = logging.getLogger(__name__)

# Engine created with pool_pre_ping to verify connections before checkout.
# Does not establish a network connection until first use.
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=getattr(settings, "DB_ECHO", False),
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a thread-local, scoped database session
    per HTTP request and ensures clean disposal on exit.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

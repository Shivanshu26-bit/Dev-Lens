import pytest
from app.core.config import Settings


def test_database_url_default():
    """Verify default DATABASE_URL is postgresql+psycopg driver."""
    settings = Settings()
    assert "postgresql+psycopg://" in settings.DATABASE_URL
    assert not settings.DB_ECHO


def test_database_url_normalization():
    """Verify postgresql:// and postgres:// are normalized to postgresql+psycopg://."""
    s1 = Settings(DATABASE_URL="postgresql://user:pass@localhost:5432/mydb")
    assert s1.DATABASE_URL == "postgresql+psycopg://user:pass@localhost:5432/mydb"

    s2 = Settings(DATABASE_URL="postgres://user:pass@localhost:5432/mydb")
    assert s2.DATABASE_URL == "postgresql+psycopg://user:pass@localhost:5432/mydb"

    s3 = Settings(DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/mydb")
    assert s3.DATABASE_URL == "postgresql+psycopg://user:pass@localhost:5432/mydb"

    s4 = Settings(DATABASE_URL="sqlite:///./test.db")
    assert s4.DATABASE_URL == "sqlite:///./test.db"

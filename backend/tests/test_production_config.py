import os
import pytest
from unittest.mock import patch, MagicMock
from pydantic import ValidationError

from app.core.config import Settings
from app.db.migrate import run_migrations, get_alembic_config


def test_cors_origins_json_array_parsing():
    """Verify CORS origins correctly parses valid JSON array strings."""
    s = Settings(BACKEND_CORS_ORIGINS='["https://app.devlens.com", "https://devlens.com"]')
    assert s.BACKEND_CORS_ORIGINS == ["https://app.devlens.com", "https://devlens.com"]


def test_cors_origins_comma_separated_parsing():
    """Verify CORS origins parses comma-separated string with whitespace trimming."""
    s = Settings(BACKEND_CORS_ORIGINS="https://app.devlens.com, https://devlens.com  ,  https://api.devlens.com ")
    assert s.BACKEND_CORS_ORIGINS == [
        "https://app.devlens.com",
        "https://devlens.com",
        "https://api.devlens.com"
    ]


def test_cors_origins_empty_string():
    """Verify empty string returns empty list of origins."""
    s = Settings(BACKEND_CORS_ORIGINS="   ")
    assert s.BACKEND_CORS_ORIGINS == []


def test_cookie_samesite_valid_values():
    """Verify valid SameSite values ('lax', 'strict', 'none') are accepted and normalized."""
    s_lax = Settings(SESSION_COOKIE_SAMESITE="Lax")
    assert s_lax.SESSION_COOKIE_SAMESITE == "lax"

    s_strict = Settings(SESSION_COOKIE_SAMESITE="STRICT")
    assert s_strict.SESSION_COOKIE_SAMESITE == "strict"

    s_none = Settings(
        SESSION_COOKIE_SAMESITE="none",
        SESSION_COOKIE_SECURE=True,
        SECRET_KEY="custom-strong-secret-key-for-prod-testing"
    )
    assert s_none.SESSION_COOKIE_SAMESITE == "none"


def test_cookie_samesite_invalid_value():
    """Verify invalid SameSite value raises validation error."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(SESSION_COOKIE_SAMESITE="invalid_value")
    assert "Invalid SESSION_COOKIE_SAMESITE" in str(exc_info.value)


def test_cookie_samesite_none_requires_secure():
    """Verify SameSite=None without Secure=True is rejected to avoid modern browser drops."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            SESSION_COOKIE_SAMESITE="none",
            SESSION_COOKIE_SECURE=False
        )
    assert "SESSION_COOKIE_SAMESITE='none' requires SESSION_COOKIE_SECURE=True" in str(exc_info.value)


def test_production_secret_key_validation():
    """Verify production mode rejects default or insecure secret keys."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            SESSION_COOKIE_SECURE=True,
            SECRET_KEY="devlens-insecure-secret-key-change-in-production-32b"
        )
    assert "Insecure default SECRET_KEY cannot be used in production" in str(exc_info.value)

    # Valid custom key passes
    s = Settings(
        SESSION_COOKIE_SECURE=True,
        SECRET_KEY="cryptographically-strong-production-secret-key"
    )
    assert s.SESSION_COOKIE_SECURE is True
    assert s.SECRET_KEY == "cryptographically-strong-production-secret-key"


def test_migration_helper_missing_config():
    """Verify run_migrations raises FileNotFoundError when config file does not exist."""
    with pytest.raises(FileNotFoundError):
        run_migrations(config_path="/path/to/nonexistent/alembic.ini")


@patch("app.db.migrate.command.upgrade")
def test_migration_helper_executes_upgrade(mock_upgrade):
    """Verify run_migrations correctly calls alembic command.upgrade with target revision."""
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    alembic_ini = os.path.join(backend_dir, "alembic.ini")

    run_migrations(config_path=alembic_ini, target="head")
    assert mock_upgrade.called
    args, kwargs = mock_upgrade.call_args
    assert args[1] == "head"

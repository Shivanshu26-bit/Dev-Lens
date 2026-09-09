import uuid
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.session import get_db
from app.api.auth import get_current_user
from app.main import app
# Import all models to ensure they register on Base.metadata
from app.models import User, UserSession, Repository, AnalysisRun


# In-memory SQLite engine with StaticPool to share connection across threads
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(test_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session():
    """Provides a fresh isolated database session for each test."""
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(autouse=True)
def override_get_db(db_session):
    """Automatically overrides FastAPI's get_db dependency to use the isolated test database."""
    def _override():
        yield db_session

    app.dependency_overrides[get_db] = _override
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(autouse=True)
def override_current_user(request, db_session):
    """
    Automatically provides an authenticated test user for existing pipeline/analyzer tests.
    Tests marked with @pytest.mark.unauthenticated or @pytest.mark.skip_auth_mock
    bypass this override to test real 401/cookie authentication behavior.
    """
    if "unauthenticated" in request.keywords or "skip_auth_mock" in request.keywords:
        yield None
    else:
        user = User(
            id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            github_user_id="1000001",
            github_login="devlens-tester",
            name="DevLens Tester",
            email="tester@devlens.local",
            avatar_url="https://avatars.githubusercontent.com/u/1000001?v=4"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        def _override():
            return user

        app.dependency_overrides[get_current_user] = _override
        yield user
        app.dependency_overrides.pop(get_current_user, None)

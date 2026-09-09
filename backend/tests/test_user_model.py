import uuid
import pytest
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.user import User
from app.models.repository import Repository
from app.models.analysis import AnalysisRun


def test_user_model_creation(db_session: Session):
    """Test creating a User model with UUID and GitHub profile fields."""
    user = User(
        github_user_id="987654",
        github_login="octocat",
        name="The Octocat",
        email="octocat@github.com",
        avatar_url="https://avatars.githubusercontent.com/u/987654?v=4"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert isinstance(user.id, uuid.UUID)
    assert user.github_user_id == "987654"
    assert user.github_login == "octocat"
    assert user.name == "The Octocat"
    assert user.email == "octocat@github.com"
    assert user.avatar_url == "https://avatars.githubusercontent.com/u/987654?v=4"
    assert user.created_at is not None
    assert user.updated_at is not None
    assert "octocat" in repr(user)


def test_github_user_id_uniqueness(db_session: Session):
    """Test that github_user_id is unique across users."""
    user1 = User(github_user_id="dup-123", github_login="user1")
    db_session.add(user1)
    db_session.commit()

    user2 = User(github_user_id="dup-123", github_login="user2")
    db_session.add(user2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_user_repository_relationship(db_session: Session):
    """Test relationship between User and Repository models."""
    user = User(github_user_id="rel-123", github_login="rel-user")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    repo = Repository(
        user_id=user.id,
        github_url="https://github.com/rel-user/sample-repo",
        owner="rel-user",
        name="sample-repo"
    )
    db_session.add(repo)
    db_session.commit()
    db_session.refresh(user)

    assert len(user.repositories) == 1
    assert user.repositories[0].name == "sample-repo"
    assert repo.user.id == user.id


def test_cascade_delete_user_deletes_repositories(db_session: Session):
    """Test that deleting a User cascades and deletes their owned repositories and analyses."""
    user = User(github_user_id="del-123", github_login="del-user")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    repo = Repository(
        user_id=user.id,
        github_url="https://github.com/del-user/to-delete",
        owner="del-user",
        name="to-delete"
    )
    db_session.add(repo)
    db_session.commit()
    db_session.refresh(repo)

    run = AnalysisRun(repository_id=repo.id)
    db_session.add(run)
    db_session.commit()

    # Delete the user
    db_session.delete(user)
    db_session.commit()

    # Verify repository and child analysis run were cascade-deleted
    assert db_session.get(Repository, repo.id) is None
    assert db_session.get(AnalysisRun, run.id) is None


def test_user_session_relationship_and_cascade_delete(db_session: Session):
    """Test User relationship with UserSession and cascade deletion of sessions."""
    from app.models.user_session import UserSession
    from datetime import datetime, timezone, timedelta

    user = User(github_user_id="sess-123", github_login="sess-user")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    session1 = UserSession(
        user_id=user.id,
        token_hash="a" * 64,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    session2 = UserSession(
        user_id=user.id,
        token_hash="b" * 64,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db_session.add_all([session1, session2])
    db_session.commit()
    db_session.refresh(user)

    assert len(user.sessions) == 2
    assert session1.user.id == user.id

    # Delete the user
    db_session.delete(user)
    db_session.commit()

    # Verify sessions were cascade-deleted
    assert db_session.get(UserSession, session1.id) is None
    assert db_session.get(UserSession, session2.id) is None


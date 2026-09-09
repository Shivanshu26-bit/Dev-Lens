import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
import httpx

from app.core.config import settings
from app.core.security import (
    create_oauth_state,
    verify_oauth_state,
)
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth_schemas import UserResponse, MessageResponse
from app.services.user_service import get_user_by_id, get_or_create_user
from app.services.session_service import (
    create_user_session,
    get_valid_session_user,
    revoke_session,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    """
    Reusable FastAPI dependency that extracts and validates the HttpOnly session cookie
    against active, unrevoked sessions stored in PostgreSQL.
    Raises HTTP 401 Unauthorized if the session is missing, expired, or revoked.
    """
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    user = get_valid_session_user(db, token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session"
        )

    return user


@router.get("/github/login")
def github_login(response: Response):
    """
    Initiates GitHub OAuth flow by generating a signed CSRF state and redirecting to GitHub.
    """
    if not settings.GITHUB_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub OAuth is not configured. Please set GITHUB_CLIENT_ID."
        )

    state = create_oauth_state()
    gh_auth_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={settings.GITHUB_CLIENT_ID}"
        f"&redirect_uri={settings.GITHUB_REDIRECT_URI}"
        f"&scope=read:user%20user:email"
        f"&state={state}"
    )

    redirect = RedirectResponse(url=gh_auth_url, status_code=status.HTTP_302_FOUND)
    redirect.set_cookie(
        key="oauth_state",
        value=state,
        httponly=True,
        samesite="lax",
        secure=settings.SESSION_COOKIE_SECURE,
        max_age=600,  # 10 minutes
        path="/"
    )
    return redirect


@router.get("/github/callback")
async def github_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Handles callback from GitHub OAuth:
    1. Validates CSRF state.
    2. Exchanges code for access token.
    3. Fetches user profile from GitHub API.
    4. Upserts local User record.
    5. Sets HttpOnly session cookie and redirects to frontend.
    """
    # 1. Handle user cancellation or GitHub errors
    if error:
        safe_error = error or "oauth_error"
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}?auth_error={safe_error}",
            status_code=status.HTTP_302_FOUND
        )

    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing authorization code or state"
        )

    # 2. Validate state signature and expiration
    if not verify_oauth_state(state):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state parameter"
        )

    cookie_state = request.cookies.get("oauth_state")
    if cookie_state and cookie_state != state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth state mismatch (possible CSRF attempt)"
        )

    # 3. Exchange code for access token
    token_url = "https://github.com/login/oauth/access_token"
    token_payload = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "client_secret": settings.GITHUB_CLIENT_SECRET,
        "code": code,
        "redirect_uri": settings.GITHUB_REDIRECT_URI,
    }

    try:
        async with httpx.AsyncClient() as client:
            token_res = await client.post(
                token_url,
                json=token_payload,
                headers={"Accept": "application/json"},
                timeout=15.0
            )

            if token_res.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Failed to exchange authorization code with GitHub"
                )

            token_data = token_res.json()
            if "error" in token_data or "access_token" not in token_data:
                err_detail = token_data.get("error_description") or token_data.get("error") or "Token exchange failed"
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"GitHub token error: {err_detail}"
                )

            access_token = token_data["access_token"]

            # 4. Fetch GitHub user profile
            user_res = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json"
                },
                timeout=15.0
            )

            if user_res.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Failed to fetch user profile from GitHub"
                )

            gh_profile = user_res.json()

            # 5. Fetch verified email if profile email is omitted
            email = gh_profile.get("email")
            if not email:
                try:
                    emails_res = await client.get(
                        "https://api.github.com/user/emails",
                        headers={
                            "Authorization": f"Bearer {access_token}",
                            "Accept": "application/json"
                        },
                        timeout=10.0
                    )
                    if emails_res.status_code == 200:
                        emails_list = emails_res.json()
                        # Pick primary verified email
                        for em in emails_list:
                            if em.get("primary") and em.get("verified"):
                                email = em.get("email")
                                break
                        if not email and emails_list:
                            email = emails_list[0].get("email")
                except Exception as e:
                    logger.warning(f"Could not fetch user emails: {e}")

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Communication timeout connecting to GitHub: {str(e)}"
        )

    # 6. Upsert User in database
    user = get_or_create_user(db, gh_profile, email=email)

    # 7. Create database-backed session token and redirect
    raw_token, _ = create_user_session(db, user.id)
    redirect = RedirectResponse(url=settings.FRONTEND_URL, status_code=status.HTTP_302_FOUND)
    redirect.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=raw_token,
        httponly=True,
        samesite=settings.SESSION_COOKIE_SAMESITE,
        secure=settings.SESSION_COOKIE_SECURE,
        max_age=settings.SESSION_EXPIRE_SECONDS,
        path="/"
    )
    redirect.delete_cookie("oauth_state", path="/")
    return redirect


@router.post("/logout", response_model=MessageResponse)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Logs out the current user by revoking the session in PostgreSQL
    and clearing the session cookie from the browser.
    """
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if token:
        revoke_session(db, token)

    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite=settings.SESSION_COOKIE_SAMESITE,
        secure=settings.SESSION_COOKIE_SECURE
    )
    return MessageResponse(message="Logged out successfully")


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Returns profile information for the currently authenticated user.
    """
    return current_user


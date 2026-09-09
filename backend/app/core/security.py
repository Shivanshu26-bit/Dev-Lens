import base64
import hashlib
import hmac
import json
import secrets
import time
import uuid
from typing import Optional

from app.core.config import settings


def _b64_encode(data: bytes) -> str:
    """Encodes bytes to URL-safe base64 string without trailing padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64_decode(data_str: str) -> bytes:
    """Decodes URL-safe base64 string with restored padding."""
    padding = 4 - (len(data_str) % 4)
    if padding != 4:
        data_str += "=" * padding
    return base64.urlsafe_b64decode(data_str.encode("ascii"))


def generate_session_token() -> str:
    """
    Generates a cryptographically secure random session token string (URL-safe).
    This raw token is issued to the client via HttpOnly cookie.
    """
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    """
    Computes a deterministic SHA-256 hex digest of the raw session token.
    ONLY this digest is stored in the database.
    """
    if not token:
        return ""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()



def create_oauth_state() -> str:
    """
    Generates a cryptographically secure, signed OAuth state parameter valid for 10 minutes.
    """
    now = int(time.time())
    payload = {
        "nonce": secrets.token_hex(16),
        "exp": now + 600,  # 10 minutes
    }
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_b64 = _b64_encode(payload_bytes)

    signature = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256
    ).digest()
    sig_b64 = _b64_encode(signature)

    return f"{payload_b64}.{sig_b64}"


def verify_oauth_state(state: str) -> bool:
    """
    Verifies an OAuth state parameter's HMAC-SHA256 signature and expiration.
    """
    if not state or "." not in state:
        return False

    try:
        parts = state.split(".", 1)
        if len(parts) != 2:
            return False
        payload_b64, sig_b64 = parts

        expected_sig = hmac.new(
            settings.SECRET_KEY.encode("utf-8"),
            payload_b64.encode("utf-8"),
            hashlib.sha256
        ).digest()
        actual_sig = _b64_decode(sig_b64)

        if not hmac.compare_digest(expected_sig, actual_sig):
            return False

        payload_bytes = _b64_decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))

        exp = payload.get("exp")
        if not exp or int(exp) < int(time.time()):
            return False

        return True
    except Exception:
        return False

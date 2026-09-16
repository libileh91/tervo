"""
Tervo — Security utilities.

JWT token creation/verification and password hashing (bcrypt).
"""

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

# ── Password hashing ──────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    """Hash a plain-text password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against its bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ── JWT tokens ─────────────────────────────────────────────


def _create_token(data: dict, expires_delta: timedelta, token_type: str) -> str:
    """Create a JWT token with the given payload and expiration."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    to_encode.update(
        {
            "sub": str(data.get("sub")),
            "exp": now + expires_delta,
            "iat": now,
            "type": token_type,
        }
    )
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(user_id: int) -> str:
    """Create a short-lived access token (default: 30 min)."""
    expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return _create_token({"sub": user_id}, expires, "access")


def create_refresh_token(user_id: int) -> str:
    """Create a long-lived refresh token (default: 7 days)."""
    expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return _create_token({"sub": user_id}, expires, "refresh")


def decode_token(token: str) -> dict | None:
    """Decode a JWT token. Returns payload dict or None if invalid/expired."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None

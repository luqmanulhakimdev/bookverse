import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from .config import settings

password_hasher = PasswordHasher()
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    try:
        return password_hasher.verify(encoded, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False


def create_access_token(user_id: UUID) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(user_id),
            "jti": secrets.token_urlsafe(12),
            "iat": now,
            "exp": now + timedelta(minutes=settings.access_token_minutes),
            "type": "access",
        },
        settings.jwt_secret,
        algorithm=ALGORITHM,
    )


def decode_access_token(token: str) -> UUID:
    claims = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    if claims.get("type") != "access":
        raise jwt.InvalidTokenError("Wrong token type")
    return UUID(claims["sub"])


def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

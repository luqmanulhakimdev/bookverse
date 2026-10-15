from uuid import UUID

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..models import User
from ..security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def current_user(
    token: str = Depends(oauth2_scheme), session: AsyncSession = Depends(get_session)
) -> User:
    try:
        user_id: UUID = decode_access_token(token)
    except (jwt.InvalidTokenError, ValueError):
        raise HTTPException(
            status_code=401,
            detail={"code": "invalid_token", "message": "Sign in again"},
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=401, detail={"code": "invalid_token", "message": "Sign in again"}
        )
    return user

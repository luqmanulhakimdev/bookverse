from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_session
from ..models import RefreshToken, User
from ..schemas_auth import Credentials, TokenResponse
from ..security import (
    create_access_token,
    hash_password,
    new_refresh_token,
    token_digest,
    verify_password,
)

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
COOKIE_NAME = "bookverse_refresh"


def set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        secure=settings.refresh_cookie_secure,
        samesite="strict",
        max_age=settings.refresh_token_days * 86400,
        path="/api/v1/auth",
    )


async def issue_refresh(session: AsyncSession, user_id, family_id=None) -> str:
    token = new_refresh_token()
    session.add(
        RefreshToken(
            user_id=user_id,
            family_id=family_id or uuid4(),
            token_hash=token_digest(token),
            expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_days),
        )
    )
    return token


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    credentials: Credentials, response: Response, session: AsyncSession = Depends(get_session)
):
    user = User(email=str(credentials.email), password_hash=hash_password(credentials.password))
    session.add(user)
    try:
        await session.flush()
        refresh = await issue_refresh(session, user.id)
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=409,
            detail={"code": "email_exists", "message": "Email is already registered"},
        ) from None
    set_refresh_cookie(response, refresh)
    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: Credentials, response: Response, session: AsyncSession = Depends(get_session)
):
    user = await session.scalar(select(User).where(User.email == str(credentials.email)))
    if user is None or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail={"code": "invalid_credentials", "message": "Email or password is incorrect"},
        )
    refresh = await issue_refresh(session, user.id)
    await session.commit()
    set_refresh_cookie(response, refresh)
    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access(
    request: Request, response: Response, session: AsyncSession = Depends(get_session)
):
    raw_token = request.cookies.get(COOKIE_NAME)
    if not raw_token:
        raise HTTPException(
            status_code=401, detail={"code": "refresh_required", "message": "Sign in again"}
        )
    row = await session.scalar(
        select(RefreshToken)
        .where(RefreshToken.token_hash == token_digest(raw_token))
        .with_for_update()
    )
    now = datetime.now(UTC)
    if row is None:
        raise HTTPException(
            status_code=401, detail={"code": "invalid_refresh", "message": "Sign in again"}
        )
    expiry = row.expires_at.replace(tzinfo=UTC) if row.expires_at.tzinfo is None else row.expires_at
    if row.revoked_at is not None or expiry <= now:
        await session.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == row.family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        await session.commit()
        response.delete_cookie(COOKIE_NAME, path="/api/v1/auth")
        raise HTTPException(
            status_code=401, detail={"code": "refresh_expired", "message": "Sign in again"}
        )
    row.revoked_at = now
    next_token = await issue_refresh(session, row.user_id, row.family_id)
    await session.commit()
    set_refresh_cookie(response, next_token)
    return TokenResponse(access_token=create_access_token(row.user_id))


@router.post("/logout", status_code=204)
async def logout(
    request: Request, response: Response, session: AsyncSession = Depends(get_session)
):
    raw_token = request.cookies.get(COOKIE_NAME)
    if raw_token:
        row = await session.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == token_digest(raw_token))
        )
        if row:
            await session.execute(
                update(RefreshToken)
                .where(RefreshToken.family_id == row.family_id, RefreshToken.revoked_at.is_(None))
                .values(revoked_at=datetime.now(UTC))
            )
            await session.commit()
    response.delete_cookie(COOKIE_NAME, path="/api/v1/auth")
    response.status_code = 204
    return response

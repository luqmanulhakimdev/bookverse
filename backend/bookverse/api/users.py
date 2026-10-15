from fastapi import APIRouter, Depends

from ..models import User
from ..schemas_auth import UserPublic
from .dependencies import current_user

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("/me", response_model=UserPublic)
async def me(user: User = Depends(current_user)):
    return user

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import UserResponse
from app.services.firebase_auth import FirebaseAuthService
from app.core.jwt import get_current_user

router = APIRouter()


@router.post("/firebase", response_model=UserResponse)
async def firebase_auth(request: Request, db: AsyncSession = Depends(get_db)):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Firebase token")

    id_token = auth_header.split(" ")[1]
    try:
        firebase_user = await FirebaseAuthService.verify_id_token(id_token)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    user = await FirebaseAuthService.get_or_create_user(db, firebase_user)
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is pending verification. Please contact an admin.",
        )
    return UserResponse(id=str(user.id), email=user.email, is_verified=user.is_verified, role=user.role)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse(id=str(current_user.id), email=current_user.email, is_verified=current_user.is_verified, role=current_user.role)

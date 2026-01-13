from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_auth_service, get_current_user, security
from app.core.auth import UserLogin, Token
from app.services.auth_service import AuthService
from app.models.models import User
from pydantic import BaseModel


router = APIRouter(prefix="/api/auth", tags=["authentication"])


class UserResponse(BaseModel):
    id: str
    username: str
    created_at: str
    
    class Config:
        from_attributes = True


@router.post("/login", response_model=Token)
async def login(
    user_data: UserLogin,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Authenticate user and return JWT token
    """
    token = auth_service.authenticate(user_data.username, user_data.password)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


@router.post("/logout")
async def logout():
    """
    Logout user (client-side token invalidation)
    """
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user information
    """
    return UserResponse(
        id=str(current_user.id),
        username=current_user.username,
        created_at=current_user.created_at.isoformat()
    )
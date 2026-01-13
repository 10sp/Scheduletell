from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.auth_service import AuthService
from app.services.appointment_service import AppointmentService
from app.services.availability_service import AvailabilityService
from app.models.models import User


# HTTP Bearer token scheme
security = HTTPBearer()


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    """Dependency to get AuthService instance"""
    return AuthService(db)


def get_appointment_service(db: Session = Depends(get_db)) -> AppointmentService:
    """Dependency to get AppointmentService instance"""
    return AppointmentService(db)


def get_availability_service(db: Session = Depends(get_db)) -> AvailabilityService:
    """Dependency to get AvailabilityService instance"""
    return AvailabilityService(db)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> User:
    """
    Dependency to get current authenticated user from JWT token
    
    Raises:
        HTTPException: 401 if token is invalid or user not found
    """
    token = credentials.credentials
    user = auth_service.get_current_user(token)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


def require_authentication(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> bool:
    """
    Dependency to require valid authentication
    
    Returns:
        True if authentication is valid
        
    Raises:
        HTTPException: 401 if token is invalid
    """
    token = credentials.credentials
    is_valid = auth_service.validate_token(token)
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return True
from datetime import timedelta
from typing import Optional
from sqlalchemy.orm import Session
from app.core.auth import (
    authenticate_user, 
    create_access_token, 
    verify_token, 
    get_user_by_username,
    Token,
    TokenData
)
from app.core.config import settings
from app.models.models import User


class AuthService:
    """Authentication service for managing user authentication and JWT tokens"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def authenticate(self, username: str, password: str) -> Optional[Token]:
        """
        Authenticate user with username and password, return JWT token if successful
        
        Args:
            username: User's username
            password: User's plain text password
            
        Returns:
            Token object with access_token, token_type, and expires_in if successful
            None if authentication fails
        """
        user = authenticate_user(self.db, username, password)
        if not user:
            return None
        
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": user.username}, 
            expires_delta=access_token_expires
        )
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60  # Convert to seconds
        )
    
    def validate_token(self, token: str) -> bool:
        """
        Validate a JWT token
        
        Args:
            token: JWT token string
            
        Returns:
            True if token is valid, False otherwise
        """
        token_data = verify_token(token)
        if not token_data or not token_data.username:
            return False
        
        # Verify user still exists in database
        user = get_user_by_username(self.db, token_data.username)
        return user is not None
    
    def get_current_user(self, token: str) -> Optional[User]:
        """
        Get current user from JWT token
        
        Args:
            token: JWT token string
            
        Returns:
            User object if token is valid, None otherwise
        """
        token_data = verify_token(token)
        if not token_data or not token_data.username:
            return None
        
        user = get_user_by_username(self.db, token_data.username)
        return user
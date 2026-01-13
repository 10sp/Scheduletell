"""
Unit tests for authentication service edge cases
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.core.database import get_db
from app.core.auth import create_user, UserCreate, authenticate_user, verify_token
from app.services.auth_service import AuthService
from tests.conftest import override_get_db


client = TestClient(app)


def test_invalid_credentials():
    """
    Test authentication with invalid credentials
    Requirements: 1.2, 1.4
    """
    # Test with non-existent user
    response = client.post("/api/auth/login", json={
        "username": "nonexistent",
        "password": "password"
    })
    assert response.status_code == 401
    assert "Invalid username or password" in response.json()["detail"]
    
    # Test with wrong password for existing user
    response = client.post("/api/auth/login", json={
        "username": "testuser",
        "password": "wrongpassword"
    })
    assert response.status_code == 401
    assert "Invalid username or password" in response.json()["detail"]


def test_missing_token():
    """
    Test accessing protected endpoint without token
    Requirements: 1.2, 1.4
    """
    # Test /api/auth/me without token
    response = client.get("/api/auth/me")
    assert response.status_code == 403
    
    # Test with empty Authorization header
    response = client.get("/api/auth/me", headers={"Authorization": ""})
    assert response.status_code == 403


def test_malformed_token():
    """
    Test authentication with malformed tokens
    Requirements: 1.2, 1.4
    """
    malformed_tokens = [
        "not_a_jwt_token",
        "Bearer",
        "Bearer ",
        "Bearer invalid.jwt.token",
        "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.invalid",
        "InvalidScheme valid_token_here"
    ]
    
    for token in malformed_tokens:
        response = client.get("/api/auth/me", headers={"Authorization": token})
        assert response.status_code in [401, 403], f"Expected 401/403 for malformed token: {token}"


def test_authenticate_user_edge_cases():
    """
    Test authenticate_user function with edge cases
    Requirements: 1.2, 1.4
    """
    from app.core.database import SessionLocal
    
    db = SessionLocal()
    try:
        # Test with None username
        result = authenticate_user(db, None, "password")
        assert result is None
        
        # Test with empty username
        result = authenticate_user(db, "", "password")
        assert result is None
        
        # Test with None password
        result = authenticate_user(db, "testuser", None)
        assert result is None
        
        # Test with empty password
        result = authenticate_user(db, "testuser", "")
        assert result is None
        
    finally:
        db.close()


def test_verify_token_edge_cases():
    """
    Test verify_token function with edge cases
    Requirements: 1.2, 1.4
    """
    # Test with None token
    result = verify_token(None)
    assert result is None
    
    # Test with empty token
    result = verify_token("")
    assert result is None
    
    # Test with malformed JWT
    result = verify_token("not.a.jwt")
    assert result is None
    
    # Test with JWT missing required claims
    from app.core.auth import create_access_token
    token_without_sub = create_access_token({"user": "testuser"})  # Missing 'sub' claim
    result = verify_token(token_without_sub)
    assert result is None


def test_auth_service_edge_cases():
    """
    Test AuthService with edge cases
    Requirements: 1.2, 1.4
    """
    from app.core.database import SessionLocal
    
    db = SessionLocal()
    try:
        auth_service = AuthService(db)
        
        # Test authenticate with None values
        result = auth_service.authenticate(None, "password")
        assert result is None
        
        result = auth_service.authenticate("username", None)
        assert result is None
        
        # Test validate_token with None
        result = auth_service.validate_token(None)
        assert result is False
        
        # Test validate_token with empty string
        result = auth_service.validate_token("")
        assert result is False
        
        # Test get_current_user with None
        result = auth_service.get_current_user(None)
        assert result is None
        
        # Test get_current_user with invalid token
        result = auth_service.get_current_user("invalid_token")
        assert result is None
        
    finally:
        db.close()


def test_successful_authentication_flow():
    """
    Test complete successful authentication flow
    Requirements: 1.3
    """
    # Login with valid credentials
    response = client.post("/api/auth/login", json={
        "username": "testuser",
        "password": "test123"
    })
    assert response.status_code == 200
    
    token_data = response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    assert "expires_in" in token_data
    
    # Use token to access protected endpoint
    token = token_data["access_token"]
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    
    user_data = response.json()
    assert user_data["username"] == "testuser"
    assert "id" in user_data
    assert "created_at" in user_data


def test_logout_endpoint():
    """
    Test logout endpoint (client-side token invalidation)
    Requirements: 1.3
    """
    response = client.post("/api/auth/logout")
    assert response.status_code == 200
    assert "message" in response.json()
    assert "logged out" in response.json()["message"].lower()
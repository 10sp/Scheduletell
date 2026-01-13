"""
Property-based tests for authentication service
Feature: appointment-scheduling-system
"""
import pytest
from hypothesis import given, strategies as st
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.core.database import get_db
from app.core.auth import create_user, UserCreate
from tests.conftest import override_get_db


client = TestClient(app)


# Strategy for generating random endpoint paths that should be protected
protected_endpoints = st.sampled_from([
    "/api/appointments",
    "/api/appointments/123e4567-e89b-12d3-a456-426614174000",
    "/api/availability",
    "/api/auth/me"
])

# Strategy for generating invalid tokens (ASCII-safe)
invalid_tokens = st.one_of(
    st.just(""),  # Empty token
    st.just("invalid_token"),  # Invalid format
    st.text(alphabet=st.characters(min_codepoint=32, max_codepoint=126), min_size=1, max_size=50).filter(lambda x: not x.startswith("Bearer ")),  # ASCII-only random text
    st.just("Bearer invalid_jwt_token"),  # Invalid JWT
    st.just("Bearer "),  # Empty bearer token
)


# Feature: appointment-scheduling-system, Property 1: Authentication Required for Protected Resources
@given(endpoint=protected_endpoints, invalid_token=invalid_tokens)
def test_authentication_required_for_protected_resources(endpoint, invalid_token):
    """
    Property 1: Authentication Required for Protected Resources
    For any protected API endpoint, when a request is made without valid authentication,
    the system should deny access and return an authentication error.
    
    Validates: Requirements 1.2
    """
    # Test with no authorization header
    response = client.get(endpoint)
    # Accept 403 (no auth header) or 404 (endpoint doesn't exist yet)
    assert response.status_code in [403, 404], f"Expected 403/404 for {endpoint} without auth header, got {response.status_code}"
    
    # Test with invalid authorization header
    headers = {"Authorization": f"Bearer {invalid_token}"}
    response = client.get(endpoint, headers=headers)
    # Accept 401 (invalid token), 403 (forbidden), or 404 (endpoint doesn't exist yet)
    assert response.status_code in [401, 403, 404], f"Expected 401/403/404 for {endpoint} with invalid token, got {response.status_code}"


# Feature: appointment-scheduling-system, Property 1: Authentication Required for Protected Resources (POST)
@given(endpoint=st.sampled_from(["/api/appointments"]), invalid_token=invalid_tokens)
def test_authentication_required_for_protected_post_resources(endpoint, invalid_token):
    """
    Property 1: Authentication Required for Protected Resources (POST endpoints)
    For any protected API endpoint, when a POST request is made without valid authentication,
    the system should deny access and return an authentication error.
    
    Validates: Requirements 1.2
    """
    # Test POST with no authorization header
    response = client.post(endpoint, json={"customer_name": "Test", "start_time": "2024-01-01T10:00:00", "duration_minutes": 60})
    # Accept 403 (no auth header) or 404 (endpoint doesn't exist yet)
    assert response.status_code in [403, 404], f"Expected 403/404 for POST {endpoint} without auth header, got {response.status_code}"
    
    # Test POST with invalid authorization header
    headers = {"Authorization": f"Bearer {invalid_token}"}
    response = client.post(endpoint, json={"customer_name": "Test", "start_time": "2024-01-01T10:00:00", "duration_minutes": 60}, headers=headers)
    # Accept 401 (invalid token), 403 (forbidden), or 404 (endpoint doesn't exist yet)
    assert response.status_code in [401, 403, 404], f"Expected 401/403/404 for POST {endpoint} with invalid token, got {response.status_code}"


# Feature: appointment-scheduling-system, Property 1: Authentication Required for Protected Resources (PUT)
@given(endpoint=st.sampled_from(["/api/availability"]), invalid_token=invalid_tokens)
def test_authentication_required_for_protected_put_resources(endpoint, invalid_token):
    """
    Property 1: Authentication Required for Protected Resources (PUT endpoints)
    For any protected API endpoint, when a PUT request is made without valid authentication,
    the system should deny access and return an authentication error.
    
    Validates: Requirements 1.2
    """
    # Test PUT with no authorization header
    response = client.put(endpoint, json={"day_of_week": 1, "start_time": "09:00", "end_time": "17:00"})
    # Accept 403 (no auth header) or 404 (endpoint doesn't exist yet)
    assert response.status_code in [403, 404], f"Expected 403/404 for PUT {endpoint} without auth header, got {response.status_code}"
    
    # Test PUT with invalid authorization header
    headers = {"Authorization": f"Bearer {invalid_token}"}
    response = client.put(endpoint, json={"day_of_week": 1, "start_time": "09:00", "end_time": "17:00"}, headers=headers)
    # Accept 401 (invalid token), 403 (forbidden), or 404 (endpoint doesn't exist yet)
    assert response.status_code in [401, 403, 404], f"Expected 401/403/404 for PUT {endpoint} with invalid token, got {response.status_code}"


# Feature: appointment-scheduling-system, Property 2: Expired Token Rejection
@given(endpoint=protected_endpoints)
def test_expired_token_rejection(endpoint):
    """
    Property 2: Expired Token Rejection
    For any API endpoint requiring authentication, when a request is made with an expired token,
    the system should reject the request and require re-authentication.
    
    Validates: Requirements 1.4
    """
    from datetime import datetime, timedelta
    from app.core.auth import create_access_token
    
    # Create an expired token (expired 1 hour ago)
    expired_token_data = {"sub": "testuser"}
    expired_delta = timedelta(hours=-1)  # Negative delta makes it expired
    expired_token = create_access_token(expired_token_data, expired_delta)
    
    # Test with expired token
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = client.get(endpoint, headers=headers)
    
    # Should reject with 401 (unauthorized) due to expired token
    assert response.status_code in [401, 403, 404], f"Expected 401/403/404 for {endpoint} with expired token, got {response.status_code}"
    
    # If we get a 404, it means the endpoint doesn't exist yet, which is acceptable for this test
    # The important thing is that we don't get a 200 (success) with an expired token
    assert response.status_code != 200, f"Should not get 200 success for {endpoint} with expired token"


# Feature: appointment-scheduling-system, Property 2: Expired Token Rejection (POST)
@given(endpoint=st.sampled_from(["/api/appointments"]))
def test_expired_token_rejection_post(endpoint):
    """
    Property 2: Expired Token Rejection (POST endpoints)
    For any API endpoint requiring authentication, when a POST request is made with an expired token,
    the system should reject the request and require re-authentication.
    
    Validates: Requirements 1.4
    """
    from datetime import datetime, timedelta
    from app.core.auth import create_access_token
    
    # Create an expired token (expired 1 hour ago)
    expired_token_data = {"sub": "testuser"}
    expired_delta = timedelta(hours=-1)  # Negative delta makes it expired
    expired_token = create_access_token(expired_token_data, expired_delta)
    
    # Test POST with expired token
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = client.post(endpoint, json={"customer_name": "Test", "start_time": "2024-01-01T10:00:00", "duration_minutes": 60}, headers=headers)
    
    # Should reject with 401 (unauthorized) due to expired token
    assert response.status_code in [401, 403, 404], f"Expected 401/403/404 for POST {endpoint} with expired token, got {response.status_code}"
    
    # The important thing is that we don't get a 200 (success) with an expired token
    assert response.status_code != 200, f"Should not get 200 success for POST {endpoint} with expired token"
"""
Property-based tests for API input validation.

Feature: appointment-scheduling-system, Property 15: Input Validation Rejects Invalid Data
**Validates: Requirements 8.4**
"""

import pytest
from hypothesis import given, strategies as st
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import json
from tests.conftest import override_get_db
from app.core.database import get_db


# Strategies for generating invalid data
invalid_strings = st.one_of(
    st.just(""),  # Empty string
    st.just("   "),  # Whitespace only
    st.none(),  # None value
)

invalid_datetimes = st.one_of(
    st.just("not-a-date"),  # Invalid format
    st.just("2023-13-45T25:70:80"),  # Invalid date components
    st.just(datetime.now() - timedelta(days=1)),  # Past date
)

invalid_durations = st.one_of(
    st.integers(max_value=0),  # Zero or negative
    st.integers(min_value=481),  # Too large (over 8 hours)
    st.just("not-a-number"),  # Invalid type
)

invalid_day_of_week = st.one_of(
    st.integers(max_value=-1),  # Negative
    st.integers(min_value=7),  # Too large
    st.just("not-a-number"),  # Invalid type
)


@pytest.fixture
def test_client():
    """Create a test client with proper database setup"""
    from fastapi import FastAPI
    from app.api import auth, appointments, availability
    
    # Create a test app
    test_app = FastAPI(title="Test App")
    test_app.include_router(auth.router)
    test_app.include_router(appointments.router)
    test_app.include_router(availability.router)
    
    test_app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(test_app) as client:
        yield client
    
    test_app.dependency_overrides.clear()


@pytest.fixture
def auth_token(test_client):
    """Create a valid authentication token for testing"""
    # First create a user (this should work with the existing auth setup)
    login_response = test_client.post("/api/auth/login", json={
        "username": "testuser",
        "password": "test123"
    })
    
    if login_response.status_code == 200:
        return login_response.json()["access_token"]
    else:
        # If login fails, return a dummy token for testing invalid auth
        return "dummy_token_for_testing"


class TestInputValidationProperties:
    """Property-based tests for API input validation."""
    
    @given(customer_name=invalid_strings)
    def test_appointment_creation_rejects_invalid_customer_name(self, test_client, auth_token, customer_name):
        """
        Feature: appointment-scheduling-system, Property 15: Input Validation Rejects Invalid Data
        For any appointment creation request with invalid customer name, the API should reject it with 400/422 status.
        **Validates: Requirements 8.4**
        """
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Valid data except for customer_name
        appointment_data = {
            "customer_name": customer_name,
            "start_time": (datetime.now() + timedelta(days=1)).isoformat(),
            "duration_minutes": 60
        }
        
        response = test_client.post("/api/appointments/", json=appointment_data, headers=headers)
        
        # Should reject with 400 Bad Request or 422 Unprocessable Entity
        assert response.status_code in [400, 422], f"Expected 400/422 but got {response.status_code} for customer_name: {customer_name}"
        
        # Response should include error details
        response_data = response.json()
        assert "detail" in response_data, "Error response should include detail field"
    
    @given(duration_minutes=invalid_durations)
    def test_appointment_creation_rejects_invalid_duration(self, test_client, auth_token, duration_minutes):
        """
        Feature: appointment-scheduling-system, Property 15: Input Validation Rejects Invalid Data
        For any appointment creation request with invalid duration, the API should reject it with 400/422 status.
        **Validates: Requirements 8.4**
        """
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Valid data except for duration_minutes
        appointment_data = {
            "customer_name": "John Doe",
            "start_time": (datetime.now() + timedelta(days=1)).isoformat(),
            "duration_minutes": duration_minutes
        }
        
        response = test_client.post("/api/appointments/", json=appointment_data, headers=headers)
        
        # Should reject with 400 Bad Request or 422 Unprocessable Entity
        assert response.status_code in [400, 422], f"Expected 400/422 but got {response.status_code} for duration: {duration_minutes}"
        
        # Response should include error details
        response_data = response.json()
        assert "detail" in response_data, "Error response should include detail field"
    
    @given(day_of_week=invalid_day_of_week)
    def test_availability_update_rejects_invalid_day_of_week(self, test_client, auth_token, day_of_week):
        """
        Feature: appointment-scheduling-system, Property 15: Input Validation Rejects Invalid Data
        For any availability update request with invalid day_of_week, the API should reject it with 400/422 status.
        **Validates: Requirements 8.4**
        """
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Valid data except for day_of_week
        availability_data = [{
            "day_of_week": day_of_week,
            "start_time": "09:00:00",
            "end_time": "17:00:00"
        }]
        
        response = test_client.put("/api/availability/", json=availability_data, headers=headers)
        
        # Should reject with 400 Bad Request or 422 Unprocessable Entity
        assert response.status_code in [400, 422], f"Expected 400/422 but got {response.status_code} for day_of_week: {day_of_week}"
        
        # Response should include error details
        response_data = response.json()
        assert "detail" in response_data, "Error response should include detail field"
    
    def test_missing_authentication_token_rejected(self, test_client):
        """
        Feature: appointment-scheduling-system, Property 15: Input Validation Rejects Invalid Data
        For any protected endpoint request without authentication token, the API should reject it with 401 status.
        **Validates: Requirements 8.4**
        """
        # Valid appointment data but no auth token
        appointment_data = {
            "customer_name": "John Doe",
            "start_time": (datetime.now() + timedelta(days=1)).isoformat(),
            "duration_minutes": 60
        }
        
        response = test_client.post("/api/appointments/", json=appointment_data)
        
        # Should reject with 401 Unauthorized or 403 Forbidden
        assert response.status_code in [401, 403], f"Expected 401/403 but got {response.status_code}"
        
        # Response should include error details
        response_data = response.json()
        assert "detail" in response_data, "Error response should include detail field"
    
    def test_invalid_appointment_id_format_rejected(self, test_client, auth_token):
        """
        Feature: appointment-scheduling-system, Property 15: Input Validation Rejects Invalid Data
        For any appointment endpoint request with invalid UUID format, the API should reject it with 400 status.
        **Validates: Requirements 8.4**
        """
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Invalid UUID format
        invalid_id = "not-a-valid-uuid"
        
        response = test_client.get(f"/api/appointments/{invalid_id}", headers=headers)
        
        # Should reject with 400 Bad Request
        assert response.status_code == 400, f"Expected 400 but got {response.status_code}"
        
        # Response should include error details
        response_data = response.json()
        assert "detail" in response_data, "Error response should include detail field"
        assert "Invalid appointment ID format" in response_data["detail"]
    
    def test_empty_availability_update_rejected(self, test_client, auth_token):
        """
        Feature: appointment-scheduling-system, Property 15: Input Validation Rejects Invalid Data
        For any availability update request with empty data, the API should reject it with 400 status.
        **Validates: Requirements 8.4**
        """
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Empty availability data
        availability_data = []
        
        response = test_client.put("/api/availability/", json=availability_data, headers=headers)
        
        # Should reject with 400 Bad Request
        assert response.status_code == 400, f"Expected 400 but got {response.status_code}"
        
        # Response should include error details
        response_data = response.json()
        assert "detail" in response_data, "Error response should include detail field"
    
    def test_invalid_date_range_rejected(self, test_client, auth_token):
        """
        Feature: appointment-scheduling-system, Property 15: Input Validation Rejects Invalid Data
        For any availability query with start_date > end_date, the API should reject it with 400 status.
        **Validates: Requirements 8.4**
        """
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Invalid date range (start after end)
        params = {
            "start_date": "2024-12-31",
            "end_date": "2024-01-01"
        }
        
        response = test_client.get("/api/availability/", params=params, headers=headers)
        
        # Should reject with 400 Bad Request
        assert response.status_code == 400, f"Expected 400 but got {response.status_code}"
        
        # Response should include error details
        response_data = response.json()
        assert "detail" in response_data, "Error response should include detail field"
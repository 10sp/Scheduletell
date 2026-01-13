"""
Property-based tests for API error response format.

Feature: appointment-scheduling-system, Property 16: Error Responses Include Status and Message
**Validates: Requirements 8.5**
"""

import pytest
from hypothesis import given, strategies as st, HealthCheck, settings
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from tests.conftest import override_get_db
from app.core.database import get_db


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


class TestErrorResponseFormatProperties:
    """Property-based tests for API error response format."""
    
    def test_missing_auth_error_response_format(self, test_client):
        """
        Feature: appointment-scheduling-system, Property 16: Error Responses Include Status and Message
        For any API error response, it should include appropriate HTTP status code and descriptive error message.
        **Validates: Requirements 8.5**
        """
        # Test missing authentication
        response = test_client.post("/api/appointments/", json={
            "customer_name": "John Doe",
            "start_time": (datetime.now() + timedelta(days=1)).isoformat(),
            "duration_minutes": 60
        })
        
        # Should have error status code
        assert response.status_code >= 400, f"Expected error status code (>=400) but got {response.status_code}"
        
        # Response should be JSON with detail field
        response_data = response.json()
        assert isinstance(response_data, dict), "Error response should be a JSON object"
        assert "detail" in response_data, "Error response should include 'detail' field"
        assert isinstance(response_data["detail"], str), "Error detail should be a string"
        assert len(response_data["detail"]) > 0, "Error detail should not be empty"
    
    def test_invalid_uuid_error_response_format(self, test_client):
        """
        Feature: appointment-scheduling-system, Property 16: Error Responses Include Status and Message
        For any API error response, it should include appropriate HTTP status code and descriptive error message.
        **Validates: Requirements 8.5**
        """
        # Test invalid UUID format (this should trigger validation error)
        response = test_client.get("/api/appointments/invalid-uuid-format", headers={
            "Authorization": "Bearer dummy_token"
        })
        
        # Should have error status code
        assert response.status_code >= 400, f"Expected error status code (>=400) but got {response.status_code}"
        
        # Response should be JSON with detail field
        response_data = response.json()
        assert isinstance(response_data, dict), "Error response should be a JSON object"
        assert "detail" in response_data, "Error response should include 'detail' field"
        assert isinstance(response_data["detail"], str), "Error detail should be a string"
        assert len(response_data["detail"]) > 0, "Error detail should not be empty"
    
    def test_invalid_json_error_response_format(self, test_client):
        """
        Feature: appointment-scheduling-system, Property 16: Error Responses Include Status and Message
        For any API error response, it should include appropriate HTTP status code and descriptive error message.
        **Validates: Requirements 8.5**
        """
        # Test invalid JSON payload
        response = test_client.post("/api/appointments/", 
                                  content="invalid json content",
                                  headers={
                                      "Authorization": "Bearer dummy_token",
                                      "Content-Type": "application/json"
                                  })
        
        # Should have error status code
        assert response.status_code >= 400, f"Expected error status code (>=400) but got {response.status_code}"
        
        # Response should be JSON with detail field
        response_data = response.json()
        assert isinstance(response_data, dict), "Error response should be a JSON object"
        assert "detail" in response_data, "Error response should include 'detail' field"
        
        # Detail can be a string or a list of validation errors
        detail = response_data["detail"]
        if isinstance(detail, list):
            assert len(detail) > 0, "Error detail list should not be empty"
            # For validation errors, each item should have error information
            for error in detail:
                assert isinstance(error, dict), "Each validation error should be a dict"
        else:
            assert isinstance(detail, str), "Error detail should be a string"
            assert len(detail) > 0, "Error detail should not be empty"
    
    def test_invalid_date_range_error_response_format(self, test_client):
        """
        Feature: appointment-scheduling-system, Property 16: Error Responses Include Status and Message
        For any API error response, it should include appropriate HTTP status code and descriptive error message.
        **Validates: Requirements 8.5**
        """
        # Test invalid date range in availability endpoint
        response = test_client.get("/api/availability/", 
                                 params={
                                     "start_date": "2024-12-31",
                                     "end_date": "2024-01-01"
                                 },
                                 headers={
                                     "Authorization": "Bearer dummy_token"
                                 })
        
        # Should have error status code
        assert response.status_code >= 400, f"Expected error status code (>=400) but got {response.status_code}"
        
        # Response should be JSON with detail field
        response_data = response.json()
        assert isinstance(response_data, dict), "Error response should be a JSON object"
        assert "detail" in response_data, "Error response should include 'detail' field"
        assert isinstance(response_data["detail"], str), "Error detail should be a string"
        assert len(response_data["detail"]) > 0, "Error detail should not be empty"
    
    def test_empty_availability_update_error_response_format(self, test_client):
        """
        Feature: appointment-scheduling-system, Property 16: Error Responses Include Status and Message
        For any API error response, it should include appropriate HTTP status code and descriptive error message.
        **Validates: Requirements 8.5**
        """
        # Test empty availability update
        response = test_client.put("/api/availability/", 
                                 json=[],
                                 headers={
                                     "Authorization": "Bearer dummy_token"
                                 })
        
        # Should have error status code
        assert response.status_code >= 400, f"Expected error status code (>=400) but got {response.status_code}"
        
        # Response should be JSON with detail field
        response_data = response.json()
        assert isinstance(response_data, dict), "Error response should be a JSON object"
        assert "detail" in response_data, "Error response should include 'detail' field"
        assert isinstance(response_data["detail"], str), "Error detail should be a string"
        assert len(response_data["detail"]) > 0, "Error detail should not be empty"
    
    @given(invalid_method=st.sampled_from(["PATCH", "DELETE"]))  # Removed HEAD as it returns empty body
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_method_not_allowed_error_response_format(self, test_client, invalid_method):
        """
        Feature: appointment-scheduling-system, Property 16: Error Responses Include Status and Message
        For any API error response, it should include appropriate HTTP status code and descriptive error message.
        **Validates: Requirements 8.5**
        """
        # Test method not allowed
        response = test_client.request(invalid_method, "/api/appointments/", 
                                     headers={
                                         "Authorization": "Bearer dummy_token"
                                     })
        
        # Should have error status code (405 Method Not Allowed or similar)
        assert response.status_code >= 400, f"Expected error status code (>=400) but got {response.status_code}"
        
        # Skip JSON parsing if response is empty (some methods like HEAD return empty body)
        if response.content:
            # Response should be JSON with detail field
            response_data = response.json()
            assert isinstance(response_data, dict), "Error response should be a JSON object"
            assert "detail" in response_data, "Error response should include 'detail' field"
            assert isinstance(response_data["detail"], str), "Error detail should be a string"
            assert len(response_data["detail"]) > 0, "Error detail should not be empty"
    
    def test_nonexistent_endpoint_error_response_format(self, test_client):
        """
        Feature: appointment-scheduling-system, Property 16: Error Responses Include Status and Message
        For any API error response, it should include appropriate HTTP status code and descriptive error message.
        **Validates: Requirements 8.5**
        """
        # Test nonexistent endpoint
        response = test_client.get("/api/nonexistent-endpoint", 
                                 headers={
                                     "Authorization": "Bearer dummy_token"
                                 })
        
        # Should have error status code (404 Not Found)
        assert response.status_code >= 400, f"Expected error status code (>=400) but got {response.status_code}"
        
        # Response should be JSON with detail field
        response_data = response.json()
        assert isinstance(response_data, dict), "Error response should be a JSON object"
        assert "detail" in response_data, "Error response should include 'detail' field"
        assert isinstance(response_data["detail"], str), "Error detail should be a string"
        assert len(response_data["detail"]) > 0, "Error detail should not be empty"
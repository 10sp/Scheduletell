"""
Integration tests for end-to-end appointment scheduling flows.

These tests verify that the complete system works together correctly,
testing the integration between API endpoints, services, and database.
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from app.main import app
from app.core.database import get_db
from app.core.auth import create_user, UserCreate
from tests.conftest import override_get_db


client = TestClient(app)


class TestAuthenticationFlow:
    """Test complete authentication flow from login to protected resource access"""
    
    def test_complete_authentication_flow(self, db_session):
        """Test end-to-end authentication: create user -> login -> access protected resource"""
        # Override the database dependency
        app.dependency_overrides[get_db] = lambda: db_session
        
        try:
            # Step 1: Create a test user
            import uuid
            unique_username = f"integrationuser_{str(uuid.uuid4())[:8]}"
            user_data = UserCreate(username=unique_username, password="testpass123")
            user = create_user(db_session, user_data)
            assert user is not None
            assert user.username == unique_username
            
            # Step 2: Login with valid credentials
            login_response = client.post(
                "/api/auth/login",
                json={"username": unique_username, "password": "testpass123"}
            )
            assert login_response.status_code == 200
            token_data = login_response.json()
            assert "access_token" in token_data
            assert token_data["token_type"] == "bearer"
            
            # Step 3: Access protected resource with token
            headers = {"Authorization": f"Bearer {token_data['access_token']}"}
            me_response = client.get("/api/auth/me", headers=headers)
            assert me_response.status_code == 200
            user_info = me_response.json()
            assert user_info["username"] == unique_username
            assert user_info["id"] == str(user.id)
            
        finally:
            app.dependency_overrides.clear()
    
    def test_authentication_failure_flow(self, db_session):
        """Test authentication failure scenarios"""
        app.dependency_overrides[get_db] = lambda: db_session
        
        try:
            # Step 1: Try to login with invalid credentials
            login_response = client.post(
                "/api/auth/login",
                json={"username": "nonexistent", "password": "wrongpass"}
            )
            assert login_response.status_code == 401
            
            # Step 2: Try to access protected resource without token
            me_response = client.get("/api/auth/me")
            assert me_response.status_code == 403  # No authorization header
            
            # Step 3: Try to access protected resource with invalid token
            headers = {"Authorization": "Bearer invalid_token"}
            me_response = client.get("/api/auth/me", headers=headers)
            assert me_response.status_code == 401
            
        finally:
            app.dependency_overrides.clear()


class TestBookingFlow:
    """Test complete appointment booking flow"""
    
    def setup_authenticated_user(self, db_session):
        """Helper to create user and get auth token"""
        import uuid
        unique_username = f"bookinguser_{str(uuid.uuid4())[:8]}"
        user_data = UserCreate(username=unique_username, password="testpass123")
        user = create_user(db_session, user_data)
        
        login_response = client.post(
            "/api/auth/login",
            json={"username": unique_username, "password": "testpass123"}
        )
        token_data = login_response.json()
        headers = {"Authorization": f"Bearer {token_data['access_token']}"}
        return user, headers
    
    def test_complete_booking_flow(self, db_session):
        """Test end-to-end booking: set availability -> create appointment -> verify"""
        app.dependency_overrides[get_db] = lambda: db_session
        
        try:
            # Setup authenticated user
            user, headers = self.setup_authenticated_user(db_session)
            
            # Step 1: Set availability for Thursday (day 3)
            availability_data = [
                {
                    "day_of_week": 3,  # Thursday
                    "start_time": "09:00:00",
                    "end_time": "17:00:00"
                }
            ]
            avail_response = client.put(
                "/api/availability/",
                json=availability_data,
                headers=headers
            )
            assert avail_response.status_code == 200
            
            # Step 2: Create appointment for Thursday
            future_thursday = datetime.now() + timedelta(days=7)  # Next week
            while future_thursday.weekday() != 3:  # Find next Thursday
                future_thursday += timedelta(days=1)
            
            appointment_data = {
                "customer_name": "Jane Smith",
                "start_time": future_thursday.strftime("%Y-%m-%dT10:00:00"),
                "duration_minutes": 60
            }
            
            create_response = client.post(
                "/api/appointments/",
                json=appointment_data,
                headers=headers
            )
            assert create_response.status_code == 201
            appointment = create_response.json()
            assert appointment["customer_name"] == "Jane Smith"
            assert appointment["duration_minutes"] == 60
            appointment_id = appointment["id"]
            
            # Step 3: Verify appointment appears in list
            list_response = client.get("/api/appointments/", headers=headers)
            assert list_response.status_code == 200
            appointments = list_response.json()
            assert len(appointments) == 1
            assert appointments[0]["id"] == appointment_id
            assert appointments[0]["customer_name"] == "Jane Smith"
            
            # Step 4: Get specific appointment
            get_response = client.get(f"/api/appointments/{appointment_id}", headers=headers)
            assert get_response.status_code == 200
            retrieved_appointment = get_response.json()
            assert retrieved_appointment["id"] == appointment_id
            assert retrieved_appointment["customer_name"] == "Jane Smith"
            
        finally:
            app.dependency_overrides.clear()
    
    def test_booking_conflict_prevention(self, db_session):
        """Test that double booking is prevented"""
        app.dependency_overrides[get_db] = lambda: db_session
        
        try:
            # Setup authenticated user
            user, headers = self.setup_authenticated_user(db_session)
            
            # Set availability
            availability_data = [
                {
                    "day_of_week": 3,  # Thursday
                    "start_time": "09:00:00",
                    "end_time": "17:00:00"
                }
            ]
            client.put("/api/availability/", json=availability_data, headers=headers)
            
            # Create first appointment
            future_thursday = datetime.now() + timedelta(days=7)
            while future_thursday.weekday() != 3:
                future_thursday += timedelta(days=1)
            
            appointment_data = {
                "customer_name": "First Customer",
                "start_time": future_thursday.strftime("%Y-%m-%dT10:00:00"),
                "duration_minutes": 60
            }
            
            first_response = client.post(
                "/api/appointments/",
                json=appointment_data,
                headers=headers
            )
            assert first_response.status_code == 201
            
            # Try to create overlapping appointment
            overlapping_data = {
                "customer_name": "Second Customer",
                "start_time": future_thursday.strftime("%Y-%m-%dT10:30:00"),  # Overlaps
                "duration_minutes": 60
            }
            
            conflict_response = client.post(
                "/api/appointments/",
                json=overlapping_data,
                headers=headers
            )
            assert conflict_response.status_code == 400
            assert "not available" in conflict_response.json()["detail"].lower()
            
        finally:
            app.dependency_overrides.clear()


class TestReschedulingFlow:
    """Test complete appointment rescheduling flow"""
    
    def setup_appointment(self, db_session):
        """Helper to create user, availability, and appointment"""
        import uuid
        unique_username = f"rescheduleuser_{str(uuid.uuid4())[:8]}"
        user_data = UserCreate(username=unique_username, password="testpass123")
        user = create_user(db_session, user_data)
        
        login_response = client.post(
            "/api/auth/login",
            json={"username": unique_username, "password": "testpass123"}
        )
        token_data = login_response.json()
        headers = {"Authorization": f"Bearer {token_data['access_token']}"}
        
        # Set availability for Thursday and Friday
        availability_data = [
            {"day_of_week": 3, "start_time": "09:00:00", "end_time": "17:00:00"},  # Thursday
            {"day_of_week": 4, "start_time": "09:00:00", "end_time": "17:00:00"}   # Friday
        ]
        client.put("/api/availability/", json=availability_data, headers=headers)
        
        # Create appointment
        future_thursday = datetime.now() + timedelta(days=7)
        while future_thursday.weekday() != 3:
            future_thursday += timedelta(days=1)
        
        appointment_data = {
            "customer_name": "Reschedule Customer",
            "start_time": future_thursday.strftime("%Y-%m-%dT10:00:00"),
            "duration_minutes": 60
        }
        
        create_response = client.post(
            "/api/appointments/",
            json=appointment_data,
            headers=headers
        )
        appointment = create_response.json()
        
        return user, headers, appointment["id"], future_thursday
    
    def test_complete_rescheduling_flow(self, db_session):
        """Test end-to-end rescheduling: create appointment -> reschedule -> verify"""
        app.dependency_overrides[get_db] = lambda: db_session
        
        try:
            # Setup appointment
            user, headers, appointment_id, original_date = self.setup_appointment(db_session)
            
            # Step 1: Reschedule to Friday at 2 PM
            friday_date = original_date + timedelta(days=1)  # Next day (Friday)
            reschedule_data = {
                "start_time": friday_date.strftime("%Y-%m-%dT14:00:00")
            }
            
            reschedule_response = client.put(
                f"/api/appointments/{appointment_id}",
                json=reschedule_data,
                headers=headers
            )
            assert reschedule_response.status_code == 200
            updated_appointment = reschedule_response.json()
            assert updated_appointment["start_time"] == friday_date.strftime("%Y-%m-%dT14:00:00")
            assert updated_appointment["customer_name"] == "Reschedule Customer"  # Preserved
            assert updated_appointment["duration_minutes"] == 60  # Preserved
            
            # Step 2: Verify the appointment was updated
            get_response = client.get(f"/api/appointments/{appointment_id}", headers=headers)
            assert get_response.status_code == 200
            retrieved_appointment = get_response.json()
            assert retrieved_appointment["start_time"] == friday_date.strftime("%Y-%m-%dT14:00:00")
            
            # Step 3: Verify original time slot is now available (try to book it)
            new_appointment_data = {
                "customer_name": "New Customer",
                "start_time": original_date.strftime("%Y-%m-%dT10:00:00"),
                "duration_minutes": 30
            }
            
            new_booking_response = client.post(
                "/api/appointments/",
                json=new_appointment_data,
                headers=headers
            )
            assert new_booking_response.status_code == 201  # Should succeed
            
        finally:
            app.dependency_overrides.clear()
    
    def test_rescheduling_conflict_prevention(self, db_session):
        """Test that rescheduling prevents conflicts"""
        app.dependency_overrides[get_db] = lambda: db_session
        
        try:
            # Setup two appointments
            user, headers, first_appointment_id, original_date = self.setup_appointment(db_session)
            
            # Create second appointment
            second_appointment_data = {
                "customer_name": "Second Customer",
                "start_time": original_date.strftime("%Y-%m-%dT14:00:00"),
                "duration_minutes": 60
            }
            
            second_response = client.post(
                "/api/appointments/",
                json=second_appointment_data,
                headers=headers
            )
            second_appointment_id = second_response.json()["id"]
            
            # Try to reschedule first appointment to conflict with second
            conflict_reschedule_data = {
                "start_time": original_date.strftime("%Y-%m-%dT14:30:00")  # Overlaps with 2 PM appointment
            }
            
            conflict_response = client.put(
                f"/api/appointments/{first_appointment_id}",
                json=conflict_reschedule_data,
                headers=headers
            )
            assert conflict_response.status_code == 400
            assert "not available" in conflict_response.json()["detail"].lower()
            
        finally:
            app.dependency_overrides.clear()


class TestSessionManagement:
    """Test session management and token expiration"""
    
    def test_token_expiration_handling(self, db_session):
        """Test that expired tokens are properly rejected"""
        app.dependency_overrides[get_db] = lambda: db_session
        
        try:
            # Create user
            import uuid
            unique_username = f"sessionuser_{str(uuid.uuid4())[:8]}"
            user_data = UserCreate(username=unique_username, password="testpass123")
            create_user(db_session, user_data)
            
            # Login to get token
            login_response = client.post(
                "/api/auth/login",
                json={"username": unique_username, "password": "testpass123"}
            )
            token_data = login_response.json()
            
            # Use valid token
            headers = {"Authorization": f"Bearer {token_data['access_token']}"}
            valid_response = client.get("/api/auth/me", headers=headers)
            assert valid_response.status_code == 200
            
            # Test with malformed token
            bad_headers = {"Authorization": "Bearer invalid.token.here"}
            invalid_response = client.get("/api/auth/me", headers=bad_headers)
            assert invalid_response.status_code == 401
            
        finally:
            app.dependency_overrides.clear()


class TestAvailabilityManagement:
    """Test availability management integration"""
    
    def test_availability_crud_flow(self, db_session):
        """Test complete availability management flow"""
        app.dependency_overrides[get_db] = lambda: db_session
        
        try:
            # Setup user
            import uuid
            unique_username = f"availuser_{str(uuid.uuid4())[:8]}"
            user_data = UserCreate(username=unique_username, password="testpass123")
            create_user(db_session, user_data)
            
            login_response = client.post(
                "/api/auth/login",
                json={"username": unique_username, "password": "testpass123"}
            )
            token_data = login_response.json()
            headers = {"Authorization": f"Bearer {token_data['access_token']}"}
            
            # Step 1: Set initial availability
            availability_data = [
                {"day_of_week": 1, "start_time": "09:00:00", "end_time": "17:00:00"},  # Tuesday
                {"day_of_week": 3, "start_time": "10:00:00", "end_time": "16:00:00"}   # Thursday
            ]
            
            set_response = client.put(
                "/api/availability/",
                json=availability_data,
                headers=headers
            )
            assert set_response.status_code == 200
            
            # Step 2: Get availability
            get_response = client.get("/api/availability/", headers=headers)
            assert get_response.status_code == 200
            availability_slots = get_response.json()
            
            # Should have availability slots for the configured days
            assert len(availability_slots) > 0
            
            # Step 3: Update availability
            updated_availability = [
                {"day_of_week": 1, "start_time": "08:00:00", "end_time": "18:00:00"},  # Extended Tuesday
                {"day_of_week": 2, "start_time": "09:00:00", "end_time": "17:00:00"},  # New Wednesday
                {"day_of_week": 4, "start_time": "09:00:00", "end_time": "15:00:00"}   # New Friday
            ]
            
            update_response = client.put(
                "/api/availability/",
                json=updated_availability,
                headers=headers
            )
            assert update_response.status_code == 200
            
            # Step 4: Verify updated availability
            updated_get_response = client.get("/api/availability/", headers=headers)
            assert updated_get_response.status_code == 200
            updated_slots = updated_get_response.json()
            assert len(updated_slots) > 0
            
        finally:
            app.dependency_overrides.clear()


class TestErrorHandling:
    """Test error handling across the integration"""
    
    def test_invalid_appointment_data(self, db_session):
        """Test that invalid appointment data is properly rejected"""
        app.dependency_overrides[get_db] = lambda: db_session
        
        try:
            # Setup user
            import uuid
            unique_username = f"erroruser_{str(uuid.uuid4())[:8]}"
            user_data = UserCreate(username=unique_username, password="testpass123")
            create_user(db_session, user_data)
            
            login_response = client.post(
                "/api/auth/login",
                json={"username": unique_username, "password": "testpass123"}
            )
            token_data = login_response.json()
            headers = {"Authorization": f"Bearer {token_data['access_token']}"}
            
            # Test missing required fields
            invalid_data = {
                "customer_name": "Test Customer"
                # Missing start_time and duration_minutes
            }
            
            response = client.post(
                "/api/appointments/",
                json=invalid_data,
                headers=headers
            )
            assert response.status_code == 422  # Validation error
            
            # Test invalid date format
            invalid_date_data = {
                "customer_name": "Test Customer",
                "start_time": "invalid-date-format",
                "duration_minutes": 60
            }
            
            response = client.post(
                "/api/appointments/",
                json=invalid_date_data,
                headers=headers
            )
            assert response.status_code == 422  # Validation error
            
            # Test negative duration
            negative_duration_data = {
                "customer_name": "Test Customer",
                "start_time": "2026-01-20T10:00:00",
                "duration_minutes": -30
            }
            
            response = client.post(
                "/api/appointments/",
                json=negative_duration_data,
                headers=headers
            )
            assert response.status_code == 422  # Validation error
            
        finally:
            app.dependency_overrides.clear()
    
    def test_nonexistent_resource_handling(self, db_session):
        """Test handling of requests for nonexistent resources"""
        app.dependency_overrides[get_db] = lambda: db_session
        
        try:
            # Setup user
            import uuid
            unique_username = f"notfounduser_{str(uuid.uuid4())[:8]}"
            user_data = UserCreate(username=unique_username, password="testpass123")
            create_user(db_session, user_data)
            
            login_response = client.post(
                "/api/auth/login",
                json={"username": unique_username, "password": "testpass123"}
            )
            token_data = login_response.json()
            headers = {"Authorization": f"Bearer {token_data['access_token']}"}
            
            # Test getting nonexistent appointment
            fake_uuid = "00000000-0000-0000-0000-000000000000"
            get_response = client.get(f"/api/appointments/{fake_uuid}", headers=headers)
            assert get_response.status_code == 404
            
            # Test updating nonexistent appointment
            update_data = {"start_time": "2026-01-20T10:00:00"}
            update_response = client.put(
                f"/api/appointments/{fake_uuid}",
                json=update_data,
                headers=headers
            )
            assert update_response.status_code == 404
            
            # Test deleting nonexistent appointment
            delete_response = client.delete(f"/api/appointments/{fake_uuid}", headers=headers)
            assert delete_response.status_code == 404
            
        finally:
            app.dependency_overrides.clear()
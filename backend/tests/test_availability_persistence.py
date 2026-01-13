import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from datetime import time
from tests.test_models import User, Availability
from tests.conftest import TestingSessionLocal, TestBase, engine
import uuid


# Hypothesis strategies for generating test data
@st.composite
def availability_data_strategy(draw):
    """Generate valid availability data for testing"""
    # Day of week (0=Monday, 6=Sunday)
    day_of_week = draw(st.integers(min_value=0, max_value=6))
    
    # Generate start time (8 AM to 6 PM to ensure reasonable business hours)
    start_hour = draw(st.integers(min_value=8, max_value=17))
    start_minute = draw(st.integers(min_value=0, max_value=59))
    start_time = time(hour=start_hour, minute=start_minute)
    
    # Generate end time (at least 1 hour after start, but before 8 PM)
    min_end_hour = start_hour + 1
    max_end_hour = min(23, start_hour + 10)  # Max 10 hours, but not past 11 PM
    end_hour = draw(st.integers(min_value=min_end_hour, max_value=max_end_hour))
    
    # If same hour, ensure end minute is greater than start minute
    if end_hour == min_end_hour:
        end_minute = draw(st.integers(min_value=start_minute + 1, max_value=59))
    else:
        end_minute = draw(st.integers(min_value=0, max_value=59))
    
    end_time = time(hour=end_hour, minute=end_minute)
    
    return {
        'day_of_week': day_of_week,
        'start_time': start_time,
        'end_time': end_time
    }


class TestAvailabilityPersistence:
    """Test availability persistence functionality"""
    
    # Feature: appointment-scheduling-system, Property 17: Availability Persistence Round Trip
    @given(availability_data=availability_data_strategy())
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=10)
    def test_availability_persistence_round_trip(self, availability_data):
        """
        Property 17: Availability Persistence Round Trip
        For any availability configuration saved to the database, when retrieving that 
        availability configuration, the system should return matching day of week, start time, and end time.
        
        Validates: Requirements 10.2
        """
        # Create database tables
        TestBase.metadata.create_all(bind=engine)
        
        # Create a database session
        db_session = TestingSessionLocal()
        
        try:
            # Create a test user first
            user = User(
                username=f"testuser_{uuid.uuid4().hex[:8]}",
                password_hash="test_hash"
            )
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)
            
            # Create availability with the generated data
            availability = Availability(
                user_id=user.id,
                day_of_week=availability_data['day_of_week'],
                start_time=availability_data['start_time'],
                end_time=availability_data['end_time']
            )
            
            # Persist the availability
            db_session.add(availability)
            db_session.commit()
            db_session.refresh(availability)
            
            # Store the ID for retrieval
            availability_id = availability.id
            user_id = user.id
            
            # Clear the session to ensure we're reading from database
            db_session.expunge_all()
            
            # Retrieve the availability by ID
            retrieved_availability = db_session.query(Availability).filter(Availability.id == availability_id).first()
            
            # Verify the availability was retrieved successfully
            assert retrieved_availability is not None, "Availability should be retrievable by ID"
            
            # Verify all key fields match (round trip property)
            assert retrieved_availability.day_of_week == availability_data['day_of_week'], \
                f"Day of week mismatch: expected {availability_data['day_of_week']}, got {retrieved_availability.day_of_week}"
            
            assert retrieved_availability.start_time == availability_data['start_time'], \
                f"Start time mismatch: expected '{availability_data['start_time']}', got '{retrieved_availability.start_time}'"
            
            assert retrieved_availability.end_time == availability_data['end_time'], \
                f"End time mismatch: expected '{availability_data['end_time']}', got '{retrieved_availability.end_time}'"
            
            # Verify the user relationship is maintained
            assert retrieved_availability.user_id == user_id, "User relationship should be maintained"
            
        finally:
            # Clean up
            db_session.close()
            TestBase.metadata.drop_all(bind=engine)
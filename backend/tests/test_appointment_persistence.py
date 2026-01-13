import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from datetime import datetime, timedelta
from tests.test_models import User, Appointment
from tests.conftest import TestingSessionLocal, TestBase, engine
import uuid


# Hypothesis strategies for generating test data
@st.composite
def user_strategy(draw):
    """Generate a valid User for testing"""
    username = draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    password_hash = draw(st.text(min_size=8, max_size=100))
    return User(
        username=username,
        password_hash=password_hash
    )


@st.composite
def appointment_data_strategy(draw):
    """Generate valid appointment data for testing"""
    customer_name = draw(st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'))))
    
    # Generate a future datetime (within next 365 days)
    base_time = datetime.now()
    days_ahead = draw(st.integers(min_value=1, max_value=365))
    hours = draw(st.integers(min_value=0, max_value=23))
    minutes = draw(st.integers(min_value=0, max_value=59))
    
    start_time = base_time.replace(hour=hours, minute=minutes, second=0, microsecond=0) + timedelta(days=days_ahead)
    
    # Duration between 15 minutes and 8 hours
    duration_minutes = draw(st.integers(min_value=15, max_value=480))
    
    return {
        'customer_name': customer_name,
        'start_time': start_time,
        'duration_minutes': duration_minutes
    }


class TestAppointmentPersistence:
    """Test appointment persistence functionality"""
    
    # Feature: appointment-scheduling-system, Property 8: Appointment Persistence Round Trip
    @given(appointment_data=appointment_data_strategy())
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=10)
    def test_appointment_persistence_round_trip(self, appointment_data):
        """
        Property 8: Appointment Persistence Round Trip
        For any successfully created appointment, when retrieving that appointment by ID, 
        the system should return an appointment with matching customer name, start time, and duration.
        
        Validates: Requirements 3.4, 10.1
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
            
            # Create appointment with the generated data
            appointment = Appointment(
                user_id=user.id,
                customer_name=appointment_data['customer_name'],
                start_time=appointment_data['start_time'],
                duration_minutes=appointment_data['duration_minutes']
            )
            
            # Persist the appointment
            db_session.add(appointment)
            db_session.commit()
            db_session.refresh(appointment)
            
            # Store the ID for retrieval
            appointment_id = appointment.id
            user_id = user.id
            
            # Clear the session to ensure we're reading from database
            db_session.expunge_all()
            
            # Retrieve the appointment by ID
            retrieved_appointment = db_session.query(Appointment).filter(Appointment.id == appointment_id).first()
            
            # Verify the appointment was retrieved successfully
            assert retrieved_appointment is not None, "Appointment should be retrievable by ID"
            
            # Verify all key fields match (round trip property)
            assert retrieved_appointment.customer_name == appointment_data['customer_name'], \
                f"Customer name mismatch: expected '{appointment_data['customer_name']}', got '{retrieved_appointment.customer_name}'"
            
            assert retrieved_appointment.start_time == appointment_data['start_time'], \
                f"Start time mismatch: expected '{appointment_data['start_time']}', got '{retrieved_appointment.start_time}'"
            
            assert retrieved_appointment.duration_minutes == appointment_data['duration_minutes'], \
                f"Duration mismatch: expected {appointment_data['duration_minutes']}, got {retrieved_appointment.duration_minutes}"
            
            # Verify the user relationship is maintained
            assert retrieved_appointment.user_id == user_id, "User relationship should be maintained"
            
        finally:
            # Clean up
            db_session.close()
            TestBase.metadata.drop_all(bind=engine)
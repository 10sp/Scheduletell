import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from datetime import datetime, timedelta
from tests.test_models import User, Appointment, Availability
from tests.conftest import TestingSessionLocal, TestBase, engine
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uuid
import tempfile
import os


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


@st.composite
def availability_data_strategy(draw):
    """Generate valid availability data for testing"""
    day_of_week = draw(st.integers(min_value=0, max_value=6))  # 0=Monday, 6=Sunday
    start_hour = draw(st.integers(min_value=0, max_value=22))
    end_hour = draw(st.integers(min_value=start_hour + 1, max_value=23))
    
    start_time = datetime.strptime(f"{start_hour:02d}:00", "%H:%M").time()
    end_time = datetime.strptime(f"{end_hour:02d}:00", "%H:%M").time()
    
    return {
        'day_of_week': day_of_week,
        'start_time': start_time,
        'end_time': end_time
    }


class TestDataPersistenceAcrossRestarts:
    """Test data persistence across application restarts"""
    
    # Feature: appointment-scheduling-system, Property 18: Data Persistence Across Restarts
    @given(
        appointment_data=appointment_data_strategy(),
        availability_data=availability_data_strategy()
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=10)
    def test_data_persistence_across_restarts(self, appointment_data, availability_data):
        """
        Property 18: Data Persistence Across Restarts
        For any appointment or availability data persisted before a system restart, 
        when querying for that data after restart, the system should return the same data.
        
        Validates: Requirements 10.3
        """
        # Create a temporary database file to simulate persistence
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
            temp_db_path = temp_db.name
        
        try:
            # Phase 1: Create data before "restart"
            # Create first database engine and session
            engine1 = create_engine(f"sqlite:///{temp_db_path}", connect_args={"check_same_thread": False})
            TestBase.metadata.create_all(bind=engine1)
            SessionLocal1 = sessionmaker(autocommit=False, autoflush=False, bind=engine1)
            
            # Store original data IDs for later verification
            user_id = None
            appointment_id = None
            availability_id = None
            
            # Create and persist data in first session
            with SessionLocal1() as db_session1:
                # Create a test user
                user = User(
                    username=f"testuser_{uuid.uuid4().hex[:8]}",
                    password_hash="test_hash"
                )
                db_session1.add(user)
                db_session1.commit()
                db_session1.refresh(user)
                user_id = user.id
                
                # Create appointment
                appointment = Appointment(
                    user_id=user.id,
                    customer_name=appointment_data['customer_name'],
                    start_time=appointment_data['start_time'],
                    duration_minutes=appointment_data['duration_minutes']
                )
                db_session1.add(appointment)
                db_session1.commit()
                db_session1.refresh(appointment)
                appointment_id = appointment.id
                
                # Create availability
                availability = Availability(
                    user_id=user.id,
                    day_of_week=availability_data['day_of_week'],
                    start_time=availability_data['start_time'],
                    end_time=availability_data['end_time']
                )
                db_session1.add(availability)
                db_session1.commit()
                db_session1.refresh(availability)
                availability_id = availability.id
            
            # Phase 2: Simulate restart by disposing engine and creating new one
            engine1.dispose()  # Close all connections (simulate shutdown)
            
            # Phase 3: Create new engine and session (simulate restart)
            engine2 = create_engine(f"sqlite:///{temp_db_path}", connect_args={"check_same_thread": False})
            SessionLocal2 = sessionmaker(autocommit=False, autoflush=False, bind=engine2)
            
            # Phase 4: Verify data persisted across restart
            with SessionLocal2() as db_session2:
                # Retrieve user
                retrieved_user = db_session2.query(User).filter(User.id == user_id).first()
                assert retrieved_user is not None, "User should persist across restart"
                assert retrieved_user.username.startswith("testuser_"), "User data should be intact"
                assert retrieved_user.password_hash == "test_hash", "User password hash should persist"
                
                # Retrieve appointment
                retrieved_appointment = db_session2.query(Appointment).filter(Appointment.id == appointment_id).first()
                assert retrieved_appointment is not None, "Appointment should persist across restart"
                assert retrieved_appointment.customer_name == appointment_data['customer_name'], \
                    f"Appointment customer name should persist: expected '{appointment_data['customer_name']}', got '{retrieved_appointment.customer_name}'"
                assert retrieved_appointment.start_time == appointment_data['start_time'], \
                    f"Appointment start time should persist: expected '{appointment_data['start_time']}', got '{retrieved_appointment.start_time}'"
                assert retrieved_appointment.duration_minutes == appointment_data['duration_minutes'], \
                    f"Appointment duration should persist: expected {appointment_data['duration_minutes']}, got {retrieved_appointment.duration_minutes}"
                assert retrieved_appointment.user_id == user_id, "Appointment user relationship should persist"
                
                # Retrieve availability
                retrieved_availability = db_session2.query(Availability).filter(Availability.id == availability_id).first()
                assert retrieved_availability is not None, "Availability should persist across restart"
                assert retrieved_availability.day_of_week == availability_data['day_of_week'], \
                    f"Availability day should persist: expected {availability_data['day_of_week']}, got {retrieved_availability.day_of_week}"
                assert retrieved_availability.start_time == availability_data['start_time'], \
                    f"Availability start time should persist: expected '{availability_data['start_time']}', got '{retrieved_availability.start_time}'"
                assert retrieved_availability.end_time == availability_data['end_time'], \
                    f"Availability end time should persist: expected '{availability_data['end_time']}', got '{retrieved_availability.end_time}'"
                assert retrieved_availability.user_id == user_id, "Availability user relationship should persist"
            
            # Clean up second engine
            engine2.dispose()
            
        finally:
            # Clean up temporary database file
            try:
                os.unlink(temp_db_path)
            except OSError:
                pass  # File might already be deleted
    
    def test_database_connection_recovery_after_restart(self):
        """
        Test that database connections can be re-established after a simulated restart.
        This tests the connection pooling and recovery mechanisms.
        """
        # Create a temporary database file
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
            temp_db_path = temp_db.name
        
        try:
            # Create first engine with connection pooling
            engine1 = create_engine(
                f"sqlite:///{temp_db_path}",
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                connect_args={"check_same_thread": False}
            )
            TestBase.metadata.create_all(bind=engine1)
            
            # Test initial connection
            with engine1.connect() as conn:
                from sqlalchemy import text
                result = conn.execute(text("SELECT 1")).fetchone()
                assert result[0] == 1, "Initial connection should work"
            
            # Dispose engine (simulate shutdown)
            engine1.dispose()
            
            # Create new engine (simulate restart)
            engine2 = create_engine(
                f"sqlite:///{temp_db_path}",
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                connect_args={"check_same_thread": False}
            )
            
            # Test connection after restart
            with engine2.connect() as conn:
                from sqlalchemy import text
                result = conn.execute(text("SELECT 1")).fetchone()
                assert result[0] == 1, "Connection should work after restart"
            
            # Verify database schema still exists
            with engine2.connect() as conn:
                from sqlalchemy import text
                # Check if tables exist by querying sqlite_master
                result = conn.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
                ).fetchone()
                assert result is not None, "Database schema should persist across restart"
            
            engine2.dispose()
            
        finally:
            # Clean up temporary database file
            try:
                os.unlink(temp_db_path)
            except OSError:
                pass
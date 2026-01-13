"""
Unit tests for dashboard query logic.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.models import Base, User, Appointment, Availability
from app.services.appointment_service import AppointmentService


@pytest.fixture(scope="function")
def test_db():
    """Create a test database for each test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_get_upcoming_appointments_method_exists():
    """Test that the get_upcoming_appointments method exists."""
    assert hasattr(AppointmentService, 'get_upcoming_appointments')


def test_get_upcoming_appointments_returns_list(test_db):
    """Test that get_upcoming_appointments returns a list."""
    service = AppointmentService(test_db, calcom_client=None)
    
    # Create a test user
    user = User(
        username="testuser",
        password_hash="hashed_password"
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    
    # Call the method
    result = service.get_upcoming_appointments(user.id)
    
    # Should return a list (empty in this case)
    assert isinstance(result, list)
    assert len(result) == 0


def test_get_upcoming_appointments_filters_future_only(test_db):
    """Test that get_upcoming_appointments only returns future appointments."""
    service = AppointmentService(test_db, calcom_client=None)
    
    # Create a test user
    user = User(
        username="testuser",
        password_hash="hashed_password"
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    
    # Create a past appointment
    past_appointment = Appointment(
        user_id=user.id,
        customer_name="Past Customer",
        start_time=datetime.now() - timedelta(hours=1),
        duration_minutes=30
    )
    test_db.add(past_appointment)
    
    # Create a future appointment
    future_appointment = Appointment(
        user_id=user.id,
        customer_name="Future Customer",
        start_time=datetime.now() + timedelta(hours=1),
        duration_minutes=30
    )
    test_db.add(future_appointment)
    test_db.commit()
    
    # Call the method
    result = service.get_upcoming_appointments(user.id)
    
    # Should only return the future appointment
    assert len(result) == 1
    assert result[0].customer_name == "Future Customer"
    assert result[0].start_time > datetime.now()


def test_get_upcoming_appointments_sorted_chronologically(test_db):
    """Test that get_upcoming_appointments returns appointments sorted by start time."""
    service = AppointmentService(test_db, calcom_client=None)
    
    # Create a test user
    user = User(
        username="testuser",
        password_hash="hashed_password"
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    
    # Create appointments in reverse chronological order
    base_time = datetime.now() + timedelta(hours=1)
    
    appointment2 = Appointment(
        user_id=user.id,
        customer_name="Customer 2",
        start_time=base_time + timedelta(hours=2),
        duration_minutes=30
    )
    test_db.add(appointment2)
    
    appointment1 = Appointment(
        user_id=user.id,
        customer_name="Customer 1",
        start_time=base_time + timedelta(hours=1),
        duration_minutes=30
    )
    test_db.add(appointment1)
    
    appointment3 = Appointment(
        user_id=user.id,
        customer_name="Customer 3",
        start_time=base_time + timedelta(hours=3),
        duration_minutes=30
    )
    test_db.add(appointment3)
    
    test_db.commit()
    
    # Call the method
    result = service.get_upcoming_appointments(user.id)
    
    # Should return appointments sorted chronologically
    assert len(result) == 3
    assert result[0].customer_name == "Customer 1"
    assert result[1].customer_name == "Customer 2"
    assert result[2].customer_name == "Customer 3"
    
    # Verify chronological order
    for i in range(len(result) - 1):
        assert result[i].start_time <= result[i + 1].start_time


def test_get_upcoming_appointments_contains_required_fields(test_db):
    """Test that appointment responses contain all required fields."""
    service = AppointmentService(test_db, calcom_client=None)
    
    # Create a test user
    user = User(
        username="testuser",
        password_hash="hashed_password"
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    
    # Create a future appointment
    appointment = Appointment(
        user_id=user.id,
        customer_name="Test Customer",
        start_time=datetime.now() + timedelta(hours=1),
        duration_minutes=60
    )
    test_db.add(appointment)
    test_db.commit()
    
    # Call the method
    result = service.get_upcoming_appointments(user.id)
    
    # Should return one appointment with all required fields
    assert len(result) == 1
    appt = result[0]
    
    # Verify all required fields are present
    assert hasattr(appt, 'id')
    assert hasattr(appt, 'customer_name')
    assert hasattr(appt, 'start_time')
    assert hasattr(appt, 'duration_minutes')
    assert hasattr(appt, 'end_time')
    assert hasattr(appt, 'created_at')
    assert hasattr(appt, 'updated_at')
    
    # Verify field values
    assert appt.customer_name == "Test Customer"
    assert appt.duration_minutes == 60
    assert appt.start_time is not None
    assert appt.end_time is not None
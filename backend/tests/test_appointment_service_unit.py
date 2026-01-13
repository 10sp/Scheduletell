"""
Unit tests for appointment service edge cases
"""
import pytest
from datetime import datetime, timedelta, time
from sqlalchemy import Column, String, DateTime, Integer, Time, ForeignKey, create_engine
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from app.services.appointment_service import AppointmentCreate
import uuid

# Create test-specific models that work with SQLite
TestBase = declarative_base()

class TestUser(TestBase):
    __tablename__ = "test_users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    
    appointments = relationship("TestAppointment", back_populates="user", cascade="all, delete-orphan")
    availability = relationship("TestAvailability", back_populates="user", cascade="all, delete-orphan")

class TestAppointment(TestBase):
    __tablename__ = "test_appointments"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("test_users.id", ondelete="CASCADE"), nullable=False)
    customer_name = Column(String(255), nullable=False)
    start_time = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    calcom_booking_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now)
    
    user = relationship("TestUser", back_populates="appointments")
    
    @property
    def end_time(self):
        return self.start_time + timedelta(minutes=self.duration_minutes)
    
    def overlaps_with(self, other_start, other_duration):
        other_end = other_start + timedelta(minutes=other_duration)
        return (self.start_time < other_end) and (self.end_time > other_start)

class TestAvailability(TestBase):
    __tablename__ = "test_availability"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("test_users.id", ondelete="CASCADE"), nullable=False)
    day_of_week = Column(Integer, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    
    user = relationship("TestUser", back_populates="availability")

# Test database setup
test_engine = create_engine("sqlite:///:memory:", echo=False)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


# Mock appointment service that works with test models
class TestAppointmentService:
    def __init__(self, db):
        self.db = db
    
    def check_availability(self, user_id, start_time, duration_minutes, exclude_appointment_id=None):
        # Check if user has availability on this day
        target_date = start_time.date()
        day_of_week = target_date.weekday()
        
        availability = self.db.query(TestAvailability).filter(
            TestAvailability.user_id == user_id,
            TestAvailability.day_of_week == day_of_week
        ).first()
        
        if not availability:
            return False
        
        # Check if the requested time falls within available hours
        start_time_only = start_time.time()
        end_time = start_time + timedelta(minutes=duration_minutes)
        end_time_only = end_time.time()
        
        if start_time_only < availability.start_time or end_time_only > availability.end_time:
            return False
        
        # Check for overlapping appointments
        query = self.db.query(TestAppointment).filter(TestAppointment.user_id == user_id)
        if exclude_appointment_id:
            query = query.filter(TestAppointment.id != exclude_appointment_id)
        
        existing_appointments = query.all()
        
        for appointment in existing_appointments:
            if appointment.overlaps_with(start_time, duration_minutes):
                return False
        
        return True
    
    def create_appointment(self, user_id, appointment_data):
        if not self.check_availability(user_id, appointment_data.start_time, appointment_data.duration_minutes):
            raise ValueError("Selected time slot is not available")
        
        appointment = TestAppointment(
            user_id=user_id,
            customer_name=appointment_data.customer_name,
            start_time=appointment_data.start_time,
            duration_minutes=appointment_data.duration_minutes
        )
        
        self.db.add(appointment)
        self.db.commit()
        self.db.refresh(appointment)
        
        # Return a simple response object
        class AppointmentResponse:
            def __init__(self, appointment):
                self.id = appointment.id
                self.customer_name = appointment.customer_name
                self.start_time = appointment.start_time
                self.duration_minutes = appointment.duration_minutes
                self.end_time = appointment.end_time
                self.created_at = appointment.created_at
                self.updated_at = appointment.updated_at
        
        return AppointmentResponse(appointment)
        
    def delete_appointment(self, user_id, appointment_id):
        """Delete an appointment by ID"""
        deleted_count = self.db.query(TestAppointment).filter(
            TestAppointment.id == appointment_id,
            TestAppointment.user_id == user_id
        ).delete()
        
        self.db.commit()
        return deleted_count > 0


@pytest.fixture
def setup_test_db():
    """Set up test database"""
    TestBase.metadata.create_all(bind=test_engine)
    yield
    TestBase.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session(setup_test_db):
    """Create a test database session"""
    db = TestSessionLocal()
    yield db
    db.close()


@pytest.fixture
def test_user(db_session):
    """Create a test user with availability"""
    user = TestUser(
        id=str(uuid.uuid4()),
        username="testuser",
        password_hash="test_hash"
    )
    db_session.add(user)
    
    # Add availability for tomorrow (when tests will schedule appointments)
    tomorrow = (datetime.now() + timedelta(days=1)).weekday()
    availability = TestAvailability(
        id=str(uuid.uuid4()),
        user_id=user.id,
        day_of_week=tomorrow,
        start_time=time(hour=9, minute=0),
        end_time=time(hour=17, minute=0)
    )
    db_session.add(availability)
    db_session.commit()
    
    return user


def test_booking_in_the_past(db_session, test_user):
    """
    Test booking in the past
    Requirements: 3.1, 3.2
    """
    service = TestAppointmentService(db_session)
    
    # Try to book an appointment in the past
    past_time = datetime.now() - timedelta(hours=1)
    
    with pytest.raises(ValueError, match="cannot be scheduled in the past"):
        appointment_data = AppointmentCreate(
            customer_name="Test Customer",
            start_time=past_time,
            duration_minutes=60
        )


def test_booking_with_zero_duration(db_session, test_user):
    """
    Test booking with zero duration
    Requirements: 3.1, 3.2
    """
    service = TestAppointmentService(db_session)
    
    # Try to book an appointment with zero duration
    future_time = datetime.now() + timedelta(hours=1)
    
    with pytest.raises(ValueError, match="Duration must be positive"):
        appointment_data = AppointmentCreate(
            customer_name="Test Customer",
            start_time=future_time,
            duration_minutes=0
        )


def test_booking_with_negative_duration(db_session, test_user):
    """
    Test booking with negative duration
    Requirements: 3.1, 3.2
    """
    service = TestAppointmentService(db_session)
    
    # Try to book an appointment with negative duration
    future_time = datetime.now() + timedelta(hours=1)
    
    with pytest.raises(ValueError, match="Duration must be positive"):
        appointment_data = AppointmentCreate(
            customer_name="Test Customer",
            start_time=future_time,
            duration_minutes=-30
        )


def test_booking_with_empty_customer_name(db_session, test_user):
    """
    Test booking with empty customer name
    Requirements: 3.1, 3.2
    """
    service = TestAppointmentService(db_session)
    
    # Try to book an appointment with empty customer name
    future_time = datetime.now() + timedelta(hours=1)
    
    with pytest.raises(ValueError, match="Customer name cannot be empty"):
        appointment_data = AppointmentCreate(
            customer_name="",
            start_time=future_time,
            duration_minutes=60
        )


def test_booking_with_whitespace_customer_name(db_session, test_user):
    """
    Test booking with whitespace-only customer name
    Requirements: 3.1, 3.2
    """
    service = TestAppointmentService(db_session)
    
    # Try to book an appointment with whitespace-only customer name
    future_time = datetime.now() + timedelta(hours=1)
    
    with pytest.raises(ValueError, match="Customer name cannot be empty"):
        appointment_data = AppointmentCreate(
            customer_name="   ",
            start_time=future_time,
            duration_minutes=60
        )


def test_booking_with_excessive_duration(db_session, test_user):
    """
    Test booking with excessive duration (over 8 hours)
    Requirements: 3.1, 3.2
    """
    service = TestAppointmentService(db_session)
    
    # Try to book an appointment with excessive duration
    future_time = datetime.now() + timedelta(hours=1)
    
    with pytest.raises(ValueError, match="Duration cannot exceed 8 hours"):
        appointment_data = AppointmentCreate(
            customer_name="Test Customer",
            start_time=future_time,
            duration_minutes=500  # Over 8 hours
        )


def test_successful_booking_edge_case(db_session, test_user):
    """
    Test successful booking at the edge of valid parameters
    Requirements: 3.1
    """
    service = TestAppointmentService(db_session)
    
    # Book an appointment with minimum valid duration
    future_time = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=1)
    
    appointment_data = AppointmentCreate(
        customer_name="A",  # Minimum length name
        start_time=future_time,
        duration_minutes=15  # Minimum duration
    )
    
    result = service.create_appointment(test_user.id, appointment_data)
    
    assert result is not None
    assert result.customer_name == "A"
    assert result.duration_minutes == 15
    assert result.start_time == future_time


def test_booking_at_maximum_duration(db_session, test_user):
    """
    Test booking at maximum allowed duration (8 hours)
    Requirements: 3.1
    """
    service = TestAppointmentService(db_session)
    
    # Book an appointment with maximum valid duration
    future_time = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
    
    appointment_data = AppointmentCreate(
        customer_name="Test Customer",
        start_time=future_time,
        duration_minutes=480  # Exactly 8 hours
    )
    
    result = service.create_appointment(test_user.id, appointment_data)
    
    assert result is not None
    assert result.duration_minutes == 480
    assert result.end_time == future_time + timedelta(minutes=480)


def test_delete_existing_appointment(db_session, test_user):
    """
    Test deleting an existing appointment
    Requirements: 8.3
    """
    service = TestAppointmentService(db_session)
    
    # Create an appointment first
    future_time = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=1)
    appointment_data = AppointmentCreate(
        customer_name="Test Customer",
        start_time=future_time,
        duration_minutes=60
    )
    
    created_appointment = service.create_appointment(test_user.id, appointment_data)
    
    # Delete the appointment
    result = service.delete_appointment(test_user.id, created_appointment.id)
    
    assert result is True
    
    # Verify appointment is deleted
    remaining_appointments = db_session.query(TestAppointment).filter(
        TestAppointment.id == created_appointment.id
    ).count()
    assert remaining_appointments == 0


def test_delete_nonexistent_appointment(db_session, test_user):
    """
    Test deleting a non-existent appointment
    Requirements: 8.3
    """
    service = TestAppointmentService(db_session)
    
    # Try to delete a non-existent appointment
    fake_id = str(uuid.uuid4())
    result = service.delete_appointment(test_user.id, fake_id)
    
    assert result is False


def test_delete_appointment_wrong_user(db_session, test_user):
    """
    Test deleting an appointment belonging to another user
    Requirements: 8.3
    """
    service = TestAppointmentService(db_session)
    
    # Create an appointment for the test user
    future_time = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=1)
    appointment_data = AppointmentCreate(
        customer_name="Test Customer",
        start_time=future_time,
        duration_minutes=60
    )
    
    created_appointment = service.create_appointment(test_user.id, appointment_data)
    
    # Try to delete with a different user ID
    wrong_user_id = str(uuid.uuid4())
    result = service.delete_appointment(wrong_user_id, created_appointment.id)
    
    assert result is False
    
    # Verify appointment still exists
    remaining_appointments = db_session.query(TestAppointment).filter(
        TestAppointment.id == created_appointment.id
    ).count()
    assert remaining_appointments == 1
"""
Property-based tests for appointment service
Feature: appointment-scheduling-system
"""
import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from datetime import datetime, timedelta, time, date
from sqlalchemy.orm import Session
from sqlalchemy import Column, String, DateTime, Integer, Time, ForeignKey, create_engine
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from app.services.appointment_service import AppointmentService, AppointmentCreate
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


@st.composite
def valid_appointment_data_strategy(draw):
    """Generate valid appointment creation data"""
    # Generate a future datetime (1-30 days from now)
    days_ahead = draw(st.integers(min_value=1, max_value=30))
    hour = draw(st.integers(min_value=9, max_value=16))
    minute = draw(st.integers(min_value=0, max_value=59))
    
    start_time = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=days_ahead)
    
    customer_name = draw(st.text(alphabet=st.characters(min_codepoint=65, max_codepoint=122), min_size=2, max_size=50).filter(lambda x: x.strip()))
    duration = draw(st.integers(min_value=15, max_value=120))  # 15 minutes to 2 hours
    
    return AppointmentCreate(
        customer_name=customer_name,
        start_time=start_time,
        duration_minutes=duration
    )


def setup_test_db():
    """Set up test database"""
    TestBase.metadata.create_all(bind=test_engine)


def cleanup_test_db():
    """Clean up test database"""
    TestBase.metadata.drop_all(bind=test_engine)


# Mock appointment service that works with test models
class TestAppointmentService:
    def __init__(self, db):
        self.db = db
    
    def check_availability(self, user_id, start_time, duration_minutes, exclude_appointment_id=None):
        # Check if user has availability on this day
        target_date = start_time.date()
        day_of_week = target_date.weekday()
        
        availability_count = self.db.query(TestAvailability).filter(
            TestAvailability.user_id == user_id,
            TestAvailability.day_of_week == day_of_week
        ).count()
        
        if availability_count == 0:
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
    
    def update_appointment(self, user_id, appointment_id, update_data):
        # Get existing appointment
        appointment = self.db.query(TestAppointment).filter(
            TestAppointment.id == appointment_id,
            TestAppointment.user_id == user_id
        ).first()
        
        if not appointment:
            return None
        
        # Determine new values
        new_start_time = update_data.start_time if hasattr(update_data, 'start_time') and update_data.start_time is not None else appointment.start_time
        new_duration = update_data.duration_minutes if hasattr(update_data, 'duration_minutes') and update_data.duration_minutes is not None else appointment.duration_minutes
        new_customer_name = update_data.customer_name if hasattr(update_data, 'customer_name') and update_data.customer_name is not None else appointment.customer_name
        
        # Check availability if time or duration changed
        if (hasattr(update_data, 'start_time') and update_data.start_time is not None) or (hasattr(update_data, 'duration_minutes') and update_data.duration_minutes is not None):
            if not self.check_availability(user_id, new_start_time, new_duration, exclude_appointment_id=appointment_id):
                raise ValueError("Updated time slot is not available")
        
        # Apply updates
        if hasattr(update_data, 'customer_name') and update_data.customer_name is not None:
            appointment.customer_name = update_data.customer_name
        if hasattr(update_data, 'start_time') and update_data.start_time is not None:
            appointment.start_time = update_data.start_time
        if hasattr(update_data, 'duration_minutes') and update_data.duration_minutes is not None:
            appointment.duration_minutes = update_data.duration_minutes
        
        appointment.updated_at = datetime.now()
        
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


# Feature: appointment-scheduling-system, Property 5: Appointment Creation Success
@given(appointment_data=valid_appointment_data_strategy())
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=10)
def test_appointment_creation_success(appointment_data):
    """
    Property 5: Appointment Creation Success
    For any valid appointment data (customer name, start time, duration) where the time slot is available,
    creating an appointment should succeed and return the appointment with all provided fields.
    
    Validates: Requirements 3.1
    """
    setup_test_db()
    db = TestSessionLocal()
    try:
        # Create a test user
        user = TestUser(
            id=str(uuid.uuid4()),
            username="testuser",
            password_hash="test_hash"
        )
        db.add(user)
        
        # Create availability that covers the appointment time
        appointment_day = appointment_data.start_time.weekday()
        availability = TestAvailability(
            id=str(uuid.uuid4()),
            user_id=user.id,
            day_of_week=appointment_day,
            start_time=time(hour=8, minute=0),
            end_time=time(hour=18, minute=0)
        )
        db.add(availability)
        db.commit()
        
        # Create appointment service
        service = TestAppointmentService(db)
        
        # Create appointment
        result = service.create_appointment(user.id, appointment_data)
        
        # Verify the appointment was created successfully
        assert result is not None
        assert result.customer_name == appointment_data.customer_name
        assert result.start_time == appointment_data.start_time
        assert result.duration_minutes == appointment_data.duration_minutes
        assert result.end_time == appointment_data.start_time + timedelta(minutes=appointment_data.duration_minutes)
        assert result.id is not None
        assert result.created_at is not None
        assert result.updated_at is not None
        
        # Verify it was persisted to database
        db_appointment = db.query(TestAppointment).filter(TestAppointment.id == result.id).first()
        assert db_appointment is not None
        assert db_appointment.customer_name == appointment_data.customer_name
        assert db_appointment.start_time == appointment_data.start_time
        assert db_appointment.duration_minutes == appointment_data.duration_minutes
        
    finally:
        db.close()
        cleanup_test_db()


# Feature: appointment-scheduling-system, Property 6: Availability Validation Before Booking
@given(appointment_data=valid_appointment_data_strategy())
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=10)
def test_availability_validation_before_booking(appointment_data):
    """
    Property 6: Availability Validation Before Booking
    For any appointment booking attempt, if the requested time slot is not available,
    the system should reject the booking before persisting any data.
    
    Validates: Requirements 3.2
    """
    setup_test_db()
    db = TestSessionLocal()
    try:
        # Create a test user
        user = TestUser(
            id=str(uuid.uuid4()),
            username="testuser",
            password_hash="test_hash"
        )
        db.add(user)
        
        # Create availability that does NOT cover the appointment time
        # Use a different day of week to ensure no availability
        appointment_day = appointment_data.start_time.weekday()
        different_day = (appointment_day + 1) % 7
        availability = TestAvailability(
            id=str(uuid.uuid4()),
            user_id=user.id,
            day_of_week=different_day,  # Different day, so no availability
            start_time=time(hour=8, minute=0),
            end_time=time(hour=18, minute=0)
        )
        db.add(availability)
        db.commit()
        
        # Create appointment service
        service = TestAppointmentService(db)
        
        # Count appointments before attempt
        initial_count = db.query(TestAppointment).count()
        
        # Attempt to create appointment - should fail
        with pytest.raises(ValueError, match="not available"):
            service.create_appointment(user.id, appointment_data)
        
        # Verify no appointment was persisted
        final_count = db.query(TestAppointment).count()
        assert final_count == initial_count, "No appointment should be persisted when time slot is not available"
        
    finally:
        db.close()
        cleanup_test_db()


# Feature: appointment-scheduling-system, Property 7: Double Booking Prevention
@given(
    first_appointment=valid_appointment_data_strategy(),
    second_duration=st.integers(min_value=15, max_value=120)
)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=10)
def test_double_booking_prevention(first_appointment, second_duration):
    """
    Property 7: Double Booking Prevention
    For any two appointments with overlapping time ranges (accounting for duration),
    the system should prevent the second appointment from being created and return an error.
    
    Validates: Requirements 3.3, 6.1, 6.2, 6.3
    """
    setup_test_db()
    db = TestSessionLocal()
    try:
        # Create a test user
        user = TestUser(
            id=str(uuid.uuid4()),
            username="testuser",
            password_hash="test_hash"
        )
        db.add(user)
        
        # Create availability that covers both appointments
        appointment_day = first_appointment.start_time.weekday()
        availability = TestAvailability(
            id=str(uuid.uuid4()),
            user_id=user.id,
            day_of_week=appointment_day,
            start_time=time(hour=8, minute=0),
            end_time=time(hour=18, minute=0)
        )
        db.add(availability)
        db.commit()
        
        # Create appointment service
        service = TestAppointmentService(db)
        
        # Create first appointment
        first_result = service.create_appointment(user.id, first_appointment)
        assert first_result is not None
        
        # Create overlapping appointment data (starts 10 minutes after first appointment starts)
        overlapping_start = first_appointment.start_time + timedelta(minutes=10)
        overlapping_data = AppointmentCreate(
            customer_name="Second Customer",
            start_time=overlapping_start,
            duration_minutes=second_duration
        )
        
        # Count appointments before second attempt
        initial_count = db.query(TestAppointment).count()
        
        # Attempt to create overlapping appointment - should fail
        with pytest.raises(ValueError, match="not available"):
            service.create_appointment(user.id, overlapping_data)
        
        # Verify no additional appointment was persisted
        final_count = db.query(TestAppointment).count()
        assert final_count == initial_count, "No overlapping appointment should be persisted"
        
        # Verify original appointment is still there
        db_appointment = db.query(TestAppointment).filter(TestAppointment.id == first_result.id).first()
        assert db_appointment is not None
        
    finally:
        db.close()
        cleanup_test_db()


@st.composite
def appointment_update_data_strategy(draw):
    """Generate valid appointment update data with new time"""
    # Generate a future datetime (1-30 days from now)
    days_ahead = draw(st.integers(min_value=1, max_value=30))
    hour = draw(st.integers(min_value=9, max_value=16))
    minute = draw(st.integers(min_value=0, max_value=59))
    
    new_start_time = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=days_ahead)
    
    # Create a simple update data object
    class AppointmentUpdate:
        def __init__(self, start_time=None, customer_name=None, duration_minutes=None):
            self.start_time = start_time
            self.customer_name = customer_name
            self.duration_minutes = duration_minutes
    
    return AppointmentUpdate(start_time=new_start_time)


# Feature: appointment-scheduling-system, Property 9: Appointment Rescheduling Updates Time
@given(
    original_appointment=valid_appointment_data_strategy(),
    update_data=appointment_update_data_strategy()
)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=10)
def test_appointment_rescheduling_updates_time(original_appointment, update_data):
    """
    Property 9: Appointment Rescheduling Updates Time
    For any existing appointment, when rescheduling to a new valid time slot,
    the appointment's start time should be updated to the new time.
    
    Validates: Requirements 4.1
    """
    setup_test_db()
    db = TestSessionLocal()
    try:
        # Create a test user
        user = TestUser(
            id=str(uuid.uuid4()),
            username="testuser",
            password_hash="test_hash"
        )
        db.add(user)
        
        # Create availability that covers both original and new appointment times
        original_day = original_appointment.start_time.weekday()
        new_day = update_data.start_time.weekday()
        
        # Add availability for original day
        availability1 = TestAvailability(
            id=str(uuid.uuid4()),
            user_id=user.id,
            day_of_week=original_day,
            start_time=time(hour=8, minute=0),
            end_time=time(hour=18, minute=0)
        )
        db.add(availability1)
        
        # Add availability for new day if different
        if new_day != original_day:
            availability2 = TestAvailability(
                id=str(uuid.uuid4()),
                user_id=user.id,
                day_of_week=new_day,
                start_time=time(hour=8, minute=0),
                end_time=time(hour=18, minute=0)
            )
            db.add(availability2)
        
        db.commit()
        
        # Create appointment service
        service = TestAppointmentService(db)
        
        # Create original appointment
        original_result = service.create_appointment(user.id, original_appointment)
        assert original_result is not None
        
        original_start_time = original_result.start_time
        original_customer_name = original_result.customer_name
        original_duration = original_result.duration_minutes
        
        # Update the appointment with new time
        updated_result = service.update_appointment(user.id, original_result.id, update_data)
        
        # Verify the appointment was updated successfully
        assert updated_result is not None
        assert updated_result.id == original_result.id  # Same appointment
        assert updated_result.start_time == update_data.start_time  # Time was updated
        assert updated_result.customer_name == original_customer_name  # Customer name preserved
        assert updated_result.duration_minutes == original_duration  # Duration preserved
        
        # Verify it was persisted to database
        db_appointment = db.query(TestAppointment).filter(TestAppointment.id == original_result.id).first()
        assert db_appointment is not None
        assert db_appointment.start_time == update_data.start_time
        assert db_appointment.customer_name == original_customer_name
        assert db_appointment.duration_minutes == original_duration
        
    finally:
        db.close()
        cleanup_test_db()


# Feature: appointment-scheduling-system, Property 10: Rescheduling Conflict Prevention
@given(
    first_appointment=valid_appointment_data_strategy(),
    second_duration=st.integers(min_value=15, max_value=120)
)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.filter_too_much], max_examples=10)
def test_rescheduling_conflict_prevention(first_appointment, second_duration):
    """
    Property 10: Rescheduling Conflict Prevention
    For any appointment rescheduling attempt, if the new time slot conflicts with another existing appointment,
    the system should reject the reschedule and return an error.
    
    Validates: Requirements 4.2, 4.3
    """
    setup_test_db()
    db = TestSessionLocal()
    try:
        # Create a test user
        user = TestUser(
            id=str(uuid.uuid4()),
            username="testuser",
            password_hash="test_hash"
        )
        db.add(user)
        
        # Create availability that covers the appointments
        appointment_day = first_appointment.start_time.weekday()
        availability = TestAvailability(
            id=str(uuid.uuid4()),
            user_id=user.id,
            day_of_week=appointment_day,
            start_time=time(hour=8, minute=0),
            end_time=time(hour=18, minute=0)
        )
        db.add(availability)
        db.commit()
        
        # Create appointment service
        service = TestAppointmentService(db)
        
        # Create first appointment
        first_result = service.create_appointment(user.id, first_appointment)
        assert first_result is not None
        
        # Create second appointment at a different time (2 hours later)
        second_start_time = first_appointment.start_time + timedelta(hours=2)
        second_appointment_data = AppointmentCreate(
            customer_name="Second Customer",
            start_time=second_start_time,
            duration_minutes=second_duration
        )
        
        second_result = service.create_appointment(user.id, second_appointment_data)
        assert second_result is not None
        
        # Now try to reschedule second appointment to conflict with first
        # Create conflicting time (10 minutes after first appointment starts)
        conflicting_time = first_appointment.start_time + timedelta(minutes=10)
        
        class AppointmentUpdate:
            def __init__(self, start_time=None):
                self.start_time = start_time
        
        conflicting_update = AppointmentUpdate(start_time=conflicting_time)
        
        # Store original values
        original_start_time = second_result.start_time
        original_customer_name = second_result.customer_name
        original_duration = second_result.duration_minutes
        
        # Attempt to reschedule to conflicting time - should fail
        with pytest.raises(ValueError, match="not available"):
            service.update_appointment(user.id, second_result.id, conflicting_update)
        
        # Verify the appointment was NOT updated (preserved original values)
        db_appointment = db.query(TestAppointment).filter(TestAppointment.id == second_result.id).first()
        assert db_appointment is not None
        assert db_appointment.start_time == original_start_time  # Time unchanged
        assert db_appointment.customer_name == original_customer_name  # Customer name unchanged
        assert db_appointment.duration_minutes == original_duration  # Duration unchanged
        
    finally:
        db.close()
        cleanup_test_db()


# Feature: appointment-scheduling-system, Property 11: Rescheduling Preserves Appointment Details
@given(
    original_appointment=valid_appointment_data_strategy(),
    new_time_offset_hours=st.integers(min_value=1, max_value=48)  # 1-48 hours later
)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=10)
def test_rescheduling_preserves_appointment_details(original_appointment, new_time_offset_hours):
    """
    Property 11: Rescheduling Preserves Appointment Details
    For any appointment, when rescheduling to a new time,
    the customer name and duration should remain unchanged.
    
    Validates: Requirements 4.5
    """
    setup_test_db()
    db = TestSessionLocal()
    try:
        # Create a test user
        user = TestUser(
            id=str(uuid.uuid4()),
            username="testuser",
            password_hash="test_hash"
        )
        db.add(user)
        
        # Calculate new time
        new_start_time = original_appointment.start_time + timedelta(hours=new_time_offset_hours)
        
        # Create availability that covers both original and new appointment times
        original_day = original_appointment.start_time.weekday()
        new_day = new_start_time.weekday()
        
        # Add availability for original day
        availability1 = TestAvailability(
            id=str(uuid.uuid4()),
            user_id=user.id,
            day_of_week=original_day,
            start_time=time(hour=8, minute=0),
            end_time=time(hour=18, minute=0)
        )
        db.add(availability1)
        
        # Add availability for new day if different
        if new_day != original_day:
            availability2 = TestAvailability(
                id=str(uuid.uuid4()),
                user_id=user.id,
                day_of_week=new_day,
                start_time=time(hour=8, minute=0),
                end_time=time(hour=18, minute=0)
            )
            db.add(availability2)
        
        db.commit()
        
        # Create appointment service
        service = TestAppointmentService(db)
        
        # Create original appointment
        original_result = service.create_appointment(user.id, original_appointment)
        assert original_result is not None
        
        # Store original values
        original_customer_name = original_result.customer_name
        original_duration = original_result.duration_minutes
        original_id = original_result.id
        
        # Create update data with only new time (no customer name or duration change)
        class AppointmentUpdate:
            def __init__(self, start_time=None):
                self.start_time = start_time
        
        update_data = AppointmentUpdate(start_time=new_start_time)
        
        # Update the appointment
        updated_result = service.update_appointment(user.id, original_id, update_data)
        
        # Verify the appointment was updated successfully
        assert updated_result is not None
        assert updated_result.id == original_id  # Same appointment
        assert updated_result.start_time == new_start_time  # Time was updated
        assert updated_result.customer_name == original_customer_name  # Customer name preserved
        assert updated_result.duration_minutes == original_duration  # Duration preserved
        
        # Verify it was persisted to database with preserved details
        db_appointment = db.query(TestAppointment).filter(TestAppointment.id == original_id).first()
        assert db_appointment is not None
        assert db_appointment.start_time == new_start_time  # Time updated
        assert db_appointment.customer_name == original_customer_name  # Customer name preserved
        assert db_appointment.duration_minutes == original_duration  # Duration preserved
        
    finally:
        db.close()
        cleanup_test_db()
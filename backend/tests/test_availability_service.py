import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from datetime import time, date, datetime, timedelta
from tests.test_models import User, Availability  # Use test models for SQLite compatibility
from tests.conftest import TestingSessionLocal, TestBase, engine
from app.services.availability_service import AvailabilityService, AvailabilityUpdate
import uuid


# Hypothesis strategies for generating test data
@st.composite
def availability_record_strategy(draw):
    """Generate valid availability record data for testing"""
    # Day of week (0=Monday, 6=Sunday)
    day_of_week = draw(st.integers(min_value=0, max_value=6))
    
    # Generate start time (8 AM to 6 PM to ensure reasonable business hours)
    start_hour = draw(st.integers(min_value=8, max_value=17))
    start_minute = draw(st.integers(min_value=0, max_value=59))
    start_time = time(hour=start_hour, minute=start_minute)
    
    # Generate end time (at least 1 hour after start, but before 8 PM)
    min_end_hour = start_hour + 1
    max_end_hour = min(23, start_hour + 10)  # Max 10 hours, but not past 11 PM
    
    # Ensure we have a valid range for end hour
    if min_end_hour > max_end_hour:
        min_end_hour = max_end_hour
    
    end_hour = draw(st.integers(min_value=min_end_hour, max_value=max_end_hour))
    
    # If same hour, ensure end minute is greater than start minute
    if end_hour == start_hour:
        # If we're in the same hour, end minute must be greater than start minute
        if start_minute >= 59:
            # If start minute is 59, we need to move to next hour
            end_hour = min(end_hour + 1, 23)
            end_minute = 0
        else:
            end_minute = draw(st.integers(min_value=start_minute + 1, max_value=59))
    else:
        end_minute = draw(st.integers(min_value=0, max_value=59))
    
    end_time = time(hour=end_hour, minute=end_minute)
    
    return {
        'day_of_week': day_of_week,
        'start_time': start_time,
        'end_time': end_time
    }


@st.composite
def date_range_strategy(draw):
    """Generate a valid date range for testing"""
    # Start with a base date (today or in the near future)
    base_date = date.today()
    
    # Generate start date (within next 30 days)
    start_offset = draw(st.integers(min_value=0, max_value=30))
    start_date = base_date + timedelta(days=start_offset)
    
    # Generate end date (1-14 days after start date)
    duration = draw(st.integers(min_value=1, max_value=14))
    end_date = start_date + timedelta(days=duration)
    
    return start_date, end_date


class TestAvailabilityService:
    """Test availability service functionality"""
    
    # Feature: appointment-scheduling-system, Property 3: Complete Availability Retrieval
    @given(
        availability_records=st.lists(availability_record_strategy(), min_size=1, max_size=7),
        date_range=date_range_strategy()
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=10)
    def test_complete_availability_retrieval(self, availability_records, date_range):
        """
        Property 3: Complete Availability Retrieval
        For any set of availability records in the database, when querying availability 
        for a date range that includes those records, the system should return all matching 
        availability records.
        
        Validates: Requirements 2.1
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
            
            # Create availability records in the database
            created_availabilities = []
            for record in availability_records:
                availability = Availability(
                    user_id=user.id,
                    day_of_week=record['day_of_week'],
                    start_time=record['start_time'],
                    end_time=record['end_time']
                )
                db_session.add(availability)
                created_availabilities.append(availability)
            
            db_session.commit()
            
            # Create availability service
            availability_service = AvailabilityService(db_session)
            
            # Query availability for the date range
            start_date, end_date = date_range
            time_slots = availability_service.get_availability(user.id, start_date, end_date)
            
            # Calculate expected time slots based on the date range and availability records
            expected_slots = []
            current_date = start_date
            
            while current_date <= end_date:
                day_of_week = current_date.weekday()  # 0=Monday, 6=Sunday
                
                # Find availability records for this day of week
                matching_records = [
                    record for record in availability_records 
                    if record['day_of_week'] == day_of_week
                ]
                
                # Create expected time slots for each matching record
                for record in matching_records:
                    expected_start = datetime.combine(current_date, record['start_time'])
                    expected_end = datetime.combine(current_date, record['end_time'])
                    expected_slots.append((expected_start, expected_end))
                
                current_date += timedelta(days=1)
            
            # Sort expected slots by start time for comparison
            expected_slots.sort(key=lambda slot: slot[0])
            
            # Verify that all expected time slots are returned
            assert len(time_slots) == len(expected_slots), \
                f"Expected {len(expected_slots)} time slots, but got {len(time_slots)}"
            
            # Verify each time slot matches expectations
            for i, (expected_start, expected_end) in enumerate(expected_slots):
                actual_slot = time_slots[i]
                
                assert actual_slot.start_time == expected_start, \
                    f"Time slot {i} start time mismatch: expected {expected_start}, got {actual_slot.start_time}"
                
                assert actual_slot.end_time == expected_end, \
                    f"Time slot {i} end time mismatch: expected {expected_end}, got {actual_slot.end_time}"
                
                assert actual_slot.available == True, \
                    f"Time slot {i} should be marked as available"
            
            # Verify time slots are sorted chronologically
            for i in range(1, len(time_slots)):
                assert time_slots[i-1].start_time <= time_slots[i].start_time, \
                    f"Time slots should be sorted chronologically: slot {i-1} starts at {time_slots[i-1].start_time}, slot {i} starts at {time_slots[i].start_time}"
            
        finally:
            # Clean up
            db_session.close()
            Base.metadata.drop_all(bind=engine)
    
    # Feature: appointment-scheduling-system, Property 4: Availability Read Consistency
    @given(availability_updates=st.lists(availability_record_strategy(), min_size=1, max_size=5))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=10)
    def test_availability_read_consistency(self, availability_updates):
        """
        Property 4: Availability Read Consistency
        For any availability update, when the availability is immediately retrieved after 
        the update, the retrieved data should match the updated data.
        
        Validates: Requirements 2.3
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
            
            # Create availability service
            availability_service = AvailabilityService(db_session)
            
            # Convert test data to AvailabilityUpdate objects
            update_objects = []
            for record in availability_updates:
                update_objects.append(AvailabilityUpdate(
                    day_of_week=record['day_of_week'],
                    start_time=record['start_time'],
                    end_time=record['end_time']
                ))
            
            # Set availability using the service
            success = availability_service.set_availability(user.id, update_objects)
            assert success, "Setting availability should succeed"
            
            # Immediately retrieve the availability
            # Use a date range that covers all days of the week
            start_date = date.today()
            end_date = start_date + timedelta(days=7)
            
            retrieved_slots = availability_service.get_availability(user.id, start_date, end_date)
            
            # Calculate expected time slots based on the updates
            expected_slots = []
            current_date = start_date
            
            while current_date <= end_date:
                day_of_week = current_date.weekday()  # 0=Monday, 6=Sunday
                
                # Find availability updates for this day of week
                matching_updates = [
                    update for update in update_objects 
                    if update.day_of_week == day_of_week
                ]
                
                # Create expected time slots for each matching update
                for update in matching_updates:
                    expected_start = datetime.combine(current_date, update.start_time)
                    expected_end = datetime.combine(current_date, update.end_time)
                    expected_slots.append((expected_start, expected_end))
                
                current_date += timedelta(days=1)
            
            # Sort expected slots by start time for comparison
            expected_slots.sort(key=lambda slot: slot[0])
            
            # Verify that retrieved data matches the updated data (read consistency)
            assert len(retrieved_slots) == len(expected_slots), \
                f"Expected {len(expected_slots)} time slots after update, but got {len(retrieved_slots)}"
            
            # Verify each time slot matches the update data
            for i, (expected_start, expected_end) in enumerate(expected_slots):
                actual_slot = retrieved_slots[i]
                
                assert actual_slot.start_time == expected_start, \
                    f"Time slot {i} start time inconsistency: expected {expected_start}, got {actual_slot.start_time}"
                
                assert actual_slot.end_time == expected_end, \
                    f"Time slot {i} end time inconsistency: expected {expected_end}, got {actual_slot.end_time}"
                
                assert actual_slot.available == True, \
                    f"Time slot {i} should be marked as available"
            
            # Additional consistency check: verify the data persisted correctly in the database
            db_availability_records = db_session.query(Availability).filter(
                Availability.user_id == user.id
            ).all()
            
            # Should have the same number of records as updates
            assert len(db_availability_records) == len(update_objects), \
                f"Database should contain {len(update_objects)} availability records, but found {len(db_availability_records)}"
            
            # Verify each database record matches an update
            for db_record in db_availability_records:
                # Find matching update
                matching_update = None
                for update in update_objects:
                    if (update.day_of_week == db_record.day_of_week and
                        update.start_time == db_record.start_time and
                        update.end_time == db_record.end_time):
                        matching_update = update
                        break
                
                assert matching_update is not None, \
                    f"Database record {db_record} does not match any update"
            
        finally:
            # Clean up
            db_session.close()
            TestBase.metadata.drop_all(bind=engine)
"""
Appointment service for managing appointments with validation logic and Cal.com integration.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Union
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from pydantic import BaseModel, validator
import uuid

from app.models.models import User, Appointment, Availability
from app.services.calcom_client import CalcomClient, CalcomBooking, CalcomError
from app.services.availability_service import AvailabilityService

logger = logging.getLogger(__name__)


class AppointmentCreate(BaseModel):
    """Data model for creating appointments."""
    customer_name: str
    start_time: datetime
    duration_minutes: int
    
    @validator('customer_name')
    def validate_customer_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Customer name cannot be empty')
        return v.strip()
    
    @validator('start_time')
    def validate_start_time(cls, v):
        if v <= datetime.now():
            raise ValueError('Appointment cannot be scheduled in the past')
        return v
    
    @validator('duration_minutes')
    def validate_duration(cls, v):
        if v <= 0:
            raise ValueError('Duration must be positive')
        if v > 480:  # 8 hours max
            raise ValueError('Duration cannot exceed 8 hours')
        return v


class AppointmentUpdate(BaseModel):
    """Data model for updating appointments."""
    customer_name: Optional[str] = None
    start_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    
    @validator('customer_name')
    def validate_customer_name(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError('Customer name cannot be empty')
        return v.strip() if v else v
    
    @validator('start_time')
    def validate_start_time(cls, v):
        if v is not None and v <= datetime.now():
            raise ValueError('Appointment cannot be scheduled in the past')
        return v
    
    @validator('duration_minutes')
    def validate_duration(cls, v):
        if v is not None:
            if v <= 0:
                raise ValueError('Duration must be positive')
            if v > 480:  # 8 hours max
                raise ValueError('Duration cannot exceed 8 hours')
        return v


class AppointmentResponse(BaseModel):
    """Response model for appointment data."""
    id: str
    customer_name: str
    start_time: datetime
    duration_minutes: int
    end_time: datetime
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AppointmentService:
    """
    Service for managing appointments with validation logic and Cal.com integration.
    
    Handles:
    - CRUD operations for appointments
    - Double booking validation
    - Appointment rescheduling logic
    - Synchronization with Cal.com
    """
    
    def __init__(self, db: Session, calcom_client: Optional[CalcomClient] = None):
        self.db = db
        self.calcom_client = calcom_client or CalcomClient()
        self.availability_service = AvailabilityService(db, calcom_client)
    
    def check_availability(self, user_id: Union[str, uuid.UUID], start_time: datetime, duration_minutes: int, exclude_appointment_id: Optional[Union[str, uuid.UUID]] = None) -> bool:
        """
        Check if a time slot is available for booking.
        
        Args:
            user_id: String ID or UUID of the user
            start_time: Start time of the appointment
            duration_minutes: Duration in minutes
            exclude_appointment_id: Optional appointment ID to exclude from conflict check (for rescheduling)
            
        Returns:
            True if the time slot is available, False otherwise
        """
        try:
            # Convert string IDs to UUIDs if necessary
            if isinstance(user_id, str):
                try:
                    user_uuid = uuid.UUID(user_id)
                except ValueError:
                    user_uuid = user_id
            else:
                user_uuid = user_id
            
            exclude_uuid = None
            if exclude_appointment_id is not None:
                if isinstance(exclude_appointment_id, str):
                    try:
                        exclude_uuid = uuid.UUID(exclude_appointment_id)
                    except ValueError:
                        exclude_uuid = exclude_appointment_id
                else:
                    exclude_uuid = exclude_appointment_id
            
            # Check if user has availability on this day
            target_date = start_time.date()
            if not self.availability_service.has_availability_on_day(user_uuid, target_date):
                logger.info(f"No availability configured for user {user_id} on {target_date}")
                return False
            
            # Check if the requested time falls within available hours
            day_availability = self.availability_service.get_availability_for_day(user_uuid, target_date)
            
            end_time = start_time + timedelta(minutes=duration_minutes)
            time_slot_available = False
            
            for slot in day_availability:
                if slot.available and slot.start_time <= start_time and slot.end_time >= end_time:
                    time_slot_available = True
                    break
            
            if not time_slot_available:
                logger.info(f"Requested time slot {start_time} - {end_time} is outside available hours")
                return False
            
            # Check for overlapping appointments
            query = self.db.query(Appointment).filter(
                Appointment.user_id == user_uuid
            )
            
            # Exclude specific appointment if provided (for rescheduling)
            if exclude_uuid is not None:
                query = query.filter(Appointment.id != exclude_uuid)
            
            existing_appointments = query.all()
            
            # Check for overlaps using the model's overlap detection
            for appointment in existing_appointments:
                if appointment.overlaps_with(start_time, duration_minutes):
                    logger.info(f"Time slot conflicts with existing appointment {appointment.id}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking availability: {e}")
            return False
    
    def create_appointment(self, user_id: Union[str, uuid.UUID], appointment_data: AppointmentCreate) -> AppointmentResponse:
        """
        Create a new appointment with validation.
        
        Args:
            user_id: String ID or UUID of the user
            appointment_data: Appointment creation data
            
        Returns:
            Created appointment response
            
        Raises:
            ValueError: If appointment data is invalid or time slot is not available
        """
        try:
            # Convert string ID to UUID if necessary
            if isinstance(user_id, str):
                try:
                    user_uuid = uuid.UUID(user_id)
                except ValueError:
                    user_uuid = user_id
            else:
                user_uuid = user_id
            
            # Validate availability
            if not self.check_availability(user_uuid, appointment_data.start_time, appointment_data.duration_minutes):
                raise ValueError("Selected time slot is not available")
            
            # Create appointment
            appointment = Appointment(
                user_id=user_uuid,
                customer_name=appointment_data.customer_name,
                start_time=appointment_data.start_time,
                duration_minutes=appointment_data.duration_minutes
            )
            
            self.db.add(appointment)
            self.db.commit()
            self.db.refresh(appointment)
            
            logger.info(f"Created appointment {appointment.id} for user {user_id}")
            
            # Convert to response model
            return AppointmentResponse(
                id=str(appointment.id),
                customer_name=appointment.customer_name,
                start_time=appointment.start_time,
                duration_minutes=appointment.duration_minutes,
                end_time=appointment.end_time,
                created_at=appointment.created_at,
                updated_at=appointment.updated_at
            )
            
        except ValueError:
            # Re-raise validation errors
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create appointment: {e}")
            raise ValueError(f"Failed to create appointment: {e}")
    
    def get_appointment(self, user_id: Union[str, uuid.UUID], appointment_id: Union[str, uuid.UUID]) -> Optional[AppointmentResponse]:
        """
        Get a specific appointment by ID.
        
        Args:
            user_id: String ID or UUID of the user
            appointment_id: String ID or UUID of the appointment
            
        Returns:
            Appointment response or None if not found
        """
        try:
            # Convert string IDs to UUIDs if necessary
            if isinstance(user_id, str):
                try:
                    user_uuid = uuid.UUID(user_id)
                except ValueError:
                    user_uuid = user_id
            else:
                user_uuid = user_id
            
            if isinstance(appointment_id, str):
                try:
                    appointment_uuid = uuid.UUID(appointment_id)
                except ValueError:
                    appointment_uuid = appointment_id
            else:
                appointment_uuid = appointment_id
            
            appointment = self.db.query(Appointment).filter(
                and_(
                    Appointment.id == appointment_uuid,
                    Appointment.user_id == user_uuid
                )
            ).first()
            
            if not appointment:
                return None
            
            return AppointmentResponse(
                id=str(appointment.id),
                customer_name=appointment.customer_name,
                start_time=appointment.start_time,
                duration_minutes=appointment.duration_minutes,
                end_time=appointment.end_time,
                created_at=appointment.created_at,
                updated_at=appointment.updated_at
            )
            
        except Exception as e:
            logger.error(f"Failed to get appointment {appointment_id}: {e}")
            return None
    
    def get_appointments(self, user_id: Union[str, uuid.UUID], start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[AppointmentResponse]:
        """
        Get appointments for a user with optional date range filtering.
        
        Args:
            user_id: String ID or UUID of the user
            start_date: Optional start date for filtering (inclusive)
            end_date: Optional end date for filtering (inclusive)
            
        Returns:
            List of appointment responses
        """
        try:
            # Convert string ID to UUID if necessary
            if isinstance(user_id, str):
                try:
                    user_uuid = uuid.UUID(user_id)
                except ValueError:
                    user_uuid = user_id
            else:
                user_uuid = user_id
            
            query = self.db.query(Appointment).filter(
                Appointment.user_id == user_uuid
            )
            
            # Apply date range filters
            if start_date:
                query = query.filter(Appointment.start_time >= start_date)
            if end_date:
                # Include appointments that start on the end_date
                end_of_day = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                query = query.filter(Appointment.start_time <= end_of_day)
            
            # Order by start time
            appointments = query.order_by(Appointment.start_time).all()
            
            # Convert to response models
            return [
                AppointmentResponse(
                    id=str(appointment.id),
                    customer_name=appointment.customer_name,
                    start_time=appointment.start_time,
                    duration_minutes=appointment.duration_minutes,
                    end_time=appointment.end_time,
                    created_at=appointment.created_at,
                    updated_at=appointment.updated_at
                )
                for appointment in appointments
            ]
            
        except Exception as e:
            logger.error(f"Failed to get appointments for user {user_id}: {e}")
            return []
    
    def update_appointment(self, user_id: Union[str, uuid.UUID], appointment_id: Union[str, uuid.UUID], update_data: AppointmentUpdate) -> Optional[AppointmentResponse]:
        """
        Update an existing appointment with rescheduling, conflict validation, and Cal.com integration.
        
        Args:
            user_id: String ID or UUID of the user
            appointment_id: String ID or UUID of the appointment
            update_data: Update data
            
        Returns:
            Updated appointment response or None if not found
            
        Raises:
            ValueError: If update data is invalid or causes conflicts
        """
        try:
            # Convert string IDs to UUIDs if necessary
            if isinstance(user_id, str):
                try:
                    user_uuid = uuid.UUID(user_id)
                except ValueError:
                    user_uuid = user_id
            else:
                user_uuid = user_id
            
            if isinstance(appointment_id, str):
                try:
                    appointment_uuid = uuid.UUID(appointment_id)
                except ValueError:
                    appointment_uuid = appointment_id
            else:
                appointment_uuid = appointment_id
            
            # Get existing appointment
            appointment = self.db.query(Appointment).filter(
                and_(
                    Appointment.id == appointment_uuid,
                    Appointment.user_id == user_uuid
                )
            ).first()
            
            if not appointment:
                return None
            
            # Store original values for Cal.com update
            original_customer_name = appointment.customer_name
            original_start_time = appointment.start_time
            original_duration = appointment.duration_minutes
            
            # Determine new values
            new_customer_name = update_data.customer_name if update_data.customer_name is not None else appointment.customer_name
            new_start_time = update_data.start_time if update_data.start_time is not None else appointment.start_time
            new_duration = update_data.duration_minutes if update_data.duration_minutes is not None else appointment.duration_minutes
            
            # Check availability if time or duration changed
            if (update_data.start_time is not None or update_data.duration_minutes is not None):
                if not self.check_availability(user_uuid, new_start_time, new_duration, exclude_appointment_id=appointment_uuid):
                    raise ValueError("Updated time slot is not available")
            
            # Update Cal.com booking if we have a booking ID and time/duration changed
            calcom_updated = False
            if appointment.calcom_booking_id and (update_data.start_time is not None or update_data.duration_minutes is not None):
                try:
                    # Create Cal.com booking data for update
                    calcom_booking = CalcomBooking(
                        eventTypeId=1,  # Default event type
                        start=new_start_time.isoformat(),
                        end=(new_start_time + timedelta(minutes=new_duration)).isoformat(),
                        attendee={
                            "name": new_customer_name,
                            "email": f"{new_customer_name.lower().replace(' ', '.')}@example.com"  # Placeholder email
                        },
                        metadata={"appointment_id": str(appointment_uuid)}
                    )
                    
                    # Update in Cal.com (this is async, but we'll handle it synchronously for now)
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(
                            self.calcom_client.update_booking(appointment.calcom_booking_id, calcom_booking)
                        )
                        calcom_updated = True
                        logger.info(f"Updated Cal.com booking {appointment.calcom_booking_id}")
                    finally:
                        loop.close()
                        
                except Exception as e:
                    logger.warning(f"Failed to update Cal.com booking {appointment.calcom_booking_id}: {e}")
                    # Continue with local update even if Cal.com fails
            
            # Apply updates to local appointment
            if update_data.customer_name is not None:
                appointment.customer_name = update_data.customer_name
            if update_data.start_time is not None:
                appointment.start_time = update_data.start_time
            if update_data.duration_minutes is not None:
                appointment.duration_minutes = update_data.duration_minutes
            
            self.db.commit()
            self.db.refresh(appointment)
            
            logger.info(f"Updated appointment {appointment.id} (Cal.com sync: {'success' if calcom_updated else 'skipped/failed'})")
            
            return AppointmentResponse(
                id=str(appointment.id),
                customer_name=appointment.customer_name,
                start_time=appointment.start_time,
                duration_minutes=appointment.duration_minutes,
                end_time=appointment.end_time,
                created_at=appointment.created_at,
                updated_at=appointment.updated_at
            )
            
        except ValueError:
            # Re-raise validation errors
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update appointment {appointment_id}: {e}")
            raise ValueError(f"Failed to update appointment: {e}")
    
    def delete_appointment(self, user_id: Union[str, uuid.UUID], appointment_id: Union[str, uuid.UUID]) -> bool:
        """
        Delete an appointment with Cal.com integration.
        
        Args:
            user_id: String ID or UUID of the user
            appointment_id: String ID or UUID of the appointment
            
        Returns:
            True if deleted successfully, False if not found
        """
        try:
            # Convert string IDs to UUIDs if necessary
            if isinstance(user_id, str):
                try:
                    user_uuid = uuid.UUID(user_id)
                except ValueError:
                    user_uuid = user_id
            else:
                user_uuid = user_id
            
            if isinstance(appointment_id, str):
                try:
                    appointment_uuid = uuid.UUID(appointment_id)
                except ValueError:
                    appointment_uuid = appointment_id
            else:
                appointment_uuid = appointment_id
            
            # Get the appointment first to check for Cal.com booking ID
            appointment = self.db.query(Appointment).filter(
                and_(
                    Appointment.id == appointment_uuid,
                    Appointment.user_id == user_uuid
                )
            ).first()
            
            if not appointment:
                logger.info(f"Appointment {appointment_id} not found for deletion")
                return False
            
            # Delete from Cal.com if we have a booking ID
            calcom_deleted = False
            if appointment.calcom_booking_id:
                try:
                    # Delete from Cal.com (this is async, but we'll handle it synchronously for now)
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(
                            self.calcom_client.delete_booking(appointment.calcom_booking_id)
                        )
                        calcom_deleted = True
                        logger.info(f"Deleted Cal.com booking {appointment.calcom_booking_id}")
                    finally:
                        loop.close()
                        
                except Exception as e:
                    logger.warning(f"Failed to delete Cal.com booking {appointment.calcom_booking_id}: {e}")
                    # Continue with local deletion even if Cal.com fails
            
            # Delete from local database
            deleted_count = self.db.query(Appointment).filter(
                and_(
                    Appointment.id == appointment_uuid,
                    Appointment.user_id == user_uuid
                )
            ).delete()
            
            self.db.commit()
            
            if deleted_count > 0:
                logger.info(f"Deleted appointment {appointment_id} (Cal.com sync: {'success' if calcom_deleted else 'skipped/failed'})")
                return True
            else:
                logger.info(f"Appointment {appointment_id} not found for deletion")
                return False
                
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete appointment {appointment_id}: {e}")
            return False
    
    def get_upcoming_appointments(self, user_id: Union[str, uuid.UUID]) -> List[AppointmentResponse]:
        """
        Get all upcoming appointments for dashboard display.
        
        Returns appointments with start times in the future, sorted chronologically.
        Ensures all required fields (appointment time, duration, customer name) are included.
        
        Args:
            user_id: String ID or UUID of the user
            
        Returns:
            List of upcoming appointment responses sorted by start time
        """
        try:
            # Convert string ID to UUID if necessary
            if isinstance(user_id, str):
                try:
                    user_uuid = uuid.UUID(user_id)
                except ValueError:
                    user_uuid = user_id
            else:
                user_uuid = user_id
            
            # Get current time for filtering upcoming appointments
            current_time = datetime.now()
            
            # Query for upcoming appointments
            appointments = self.db.query(Appointment).filter(
                and_(
                    Appointment.user_id == user_uuid,
                    Appointment.start_time > current_time
                )
            ).order_by(Appointment.start_time).all()
            
            # Convert to response models with all required fields
            return [
                AppointmentResponse(
                    id=str(appointment.id),
                    customer_name=appointment.customer_name,
                    start_time=appointment.start_time,
                    duration_minutes=appointment.duration_minutes,
                    end_time=appointment.end_time,
                    created_at=appointment.created_at,
                    updated_at=appointment.updated_at
                )
                for appointment in appointments
            ]
            
        except Exception as e:
            logger.error(f"Failed to get upcoming appointments for user {user_id}: {e}")
            return []
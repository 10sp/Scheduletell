"""
Availability service for managing user availability and synchronization with Cal.com.
"""

import logging
from datetime import date, datetime, time, timedelta
from typing import List, Optional, Dict, Any, Union
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from pydantic import BaseModel
import uuid

from app.models.models import User, Availability
from app.services.calcom_client import CalcomClient, CalcomAvailability, CalcomError

logger = logging.getLogger(__name__)


class TimeSlot(BaseModel):
    """Represents a time slot with availability information."""
    start_time: datetime
    end_time: datetime
    available: bool


class AvailabilityUpdate(BaseModel):
    """Data model for availability updates."""
    day_of_week: int
    start_time: time
    end_time: time


class AvailabilityService:
    """
    Service for managing user availability with CRUD operations and Cal.com synchronization.
    
    Handles:
    - Retrieving availability with date range filtering
    - Setting/updating availability
    - Synchronizing availability with Cal.com
    """
    
    def __init__(self, db: Session, calcom_client: Optional[CalcomClient] = None):
        self.db = db
        self.calcom_client = calcom_client or CalcomClient()
    
    def get_availability(self, user_id: Union[str, uuid.UUID], start_date: date, end_date: date) -> List[TimeSlot]:
        """
        Get availability for a user within a date range.
        
        Args:
            user_id: String ID or UUID of the user (compatible with both test and production models)
            start_date: Start date for availability query
            end_date: End date for availability query (inclusive)
            
        Returns:
            List of TimeSlot objects representing available time slots
        """
        try:
            # Convert string ID to UUID if necessary
            if isinstance(user_id, str):
                try:
                    user_uuid = uuid.UUID(user_id)
                except ValueError:
                    # If it's not a valid UUID string, use it as-is (for test models)
                    user_uuid = user_id
            else:
                user_uuid = user_id
            
            # Query availability records for the user
            availability_records = self.db.query(Availability).filter(
                Availability.user_id == user_uuid
            ).all()
            
            if not availability_records:
                logger.info(f"No availability records found for user {user_id}")
                return []
            
            time_slots = []
            current_date = start_date
            
            # Generate time slots for each day in the date range
            while current_date <= end_date:
                day_of_week = current_date.weekday()  # 0=Monday, 6=Sunday
                
                # Find availability for this day of week
                day_availability = [
                    avail for avail in availability_records 
                    if avail.day_of_week == day_of_week
                ]
                
                # Create time slots for each availability window
                for avail in day_availability:
                    start_datetime = datetime.combine(current_date, avail.start_time)
                    end_datetime = datetime.combine(current_date, avail.end_time)
                    
                    time_slots.append(TimeSlot(
                        start_time=start_datetime,
                        end_time=end_datetime,
                        available=True
                    ))
                
                current_date += timedelta(days=1)
            
            # Sort time slots by start time
            time_slots.sort(key=lambda slot: slot.start_time)
            
            logger.info(f"Retrieved {len(time_slots)} time slots for user {user_id}")
            return time_slots
            
        except Exception as e:
            logger.error(f"Failed to get availability for user {user_id}: {e}")
            raise
    
    def set_availability(self, user_id: Union[str, uuid.UUID], availability_updates: List[AvailabilityUpdate]) -> bool:
        """
        Set availability for a user, replacing existing availability.
        
        Args:
            user_id: String ID or UUID of the user (compatible with both test and production models)
            availability_updates: List of availability updates
            
        Returns:
            True if successful
            
        Raises:
            ValueError: If availability data is invalid
        """
        try:
            # Validate input
            for update in availability_updates:
                if not (0 <= update.day_of_week <= 6):
                    raise ValueError(f"Invalid day_of_week: {update.day_of_week}")
                if update.start_time >= update.end_time:
                    raise ValueError(f"Start time must be before end time: {update.start_time} >= {update.end_time}")
            
            # Convert string ID to UUID if necessary
            if isinstance(user_id, str):
                try:
                    user_uuid = uuid.UUID(user_id)
                except ValueError:
                    # If it's not a valid UUID string, use it as-is (for test models)
                    user_uuid = user_id
            else:
                user_uuid = user_id
            
            # Start transaction
            # Delete existing availability for the user
            self.db.query(Availability).filter(
                Availability.user_id == user_uuid
            ).delete()
            
            # Create new availability records
            for update in availability_updates:
                availability = Availability(
                    user_id=user_uuid,
                    day_of_week=update.day_of_week,
                    start_time=update.start_time,
                    end_time=update.end_time
                )
                self.db.add(availability)
            
            # Commit changes
            self.db.commit()
            
            logger.info(f"Updated availability for user {user_id} with {len(availability_updates)} records")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to set availability for user {user_id}: {e}")
            raise
    
    async def sync_with_calcom(self, user_id: Union[str, uuid.UUID]) -> bool:
        """
        Synchronize user availability with Cal.com.
        
        Args:
            user_id: String ID or UUID of the user (compatible with both test and production models)
            
        Returns:
            True if synchronization was successful
            
        Raises:
            CalcomError: If Cal.com synchronization fails
        """
        try:
            # Convert string ID to UUID if necessary
            if isinstance(user_id, str):
                try:
                    user_uuid = uuid.UUID(user_id)
                except ValueError:
                    # If it's not a valid UUID string, use it as-is (for test models)
                    user_uuid = user_id
            else:
                user_uuid = user_id
            
            # Get current availability from database
            availability_records = self.db.query(Availability).filter(
                Availability.user_id == user_uuid
            ).all()
            
            if not availability_records:
                logger.warning(f"No availability records to sync for user {user_id}")
                return True
            
            # Convert to Cal.com format
            date_ranges = []
            
            # For simplicity, we'll create a week's worth of availability
            # In a real implementation, you might want to sync for a longer period
            base_date = date.today()
            
            for avail in availability_records:
                # Calculate the next occurrence of this day of week
                days_ahead = avail.day_of_week - base_date.weekday()
                if days_ahead <= 0:  # Target day already happened this week
                    days_ahead += 7
                
                target_date = base_date + timedelta(days=days_ahead)
                
                start_datetime = datetime.combine(target_date, avail.start_time)
                end_datetime = datetime.combine(target_date, avail.end_time)
                
                date_ranges.append({
                    "start": start_datetime.isoformat(),
                    "end": end_datetime.isoformat()
                })
            
            # Create Cal.com availability object
            calcom_availability = CalcomAvailability(
                dateRanges=date_ranges,
                timeZone="UTC"
            )
            
            # Sync with Cal.com
            success = await self.calcom_client.update_availability(calcom_availability)
            
            if success:
                logger.info(f"Successfully synced availability with Cal.com for user {user_id}")
            else:
                logger.error(f"Failed to sync availability with Cal.com for user {user_id}")
            
            return success
            
        except CalcomError as e:
            logger.error(f"Cal.com error during sync for user {user_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during Cal.com sync for user {user_id}: {e}")
            raise CalcomError(f"Sync failed: {e}")
    
    def get_availability_for_day(self, user_id: Union[str, uuid.UUID], target_date: date) -> List[TimeSlot]:
        """
        Get availability for a specific day.
        
        Args:
            user_id: String ID or UUID of the user (compatible with both test and production models)
            target_date: Date to get availability for
            
        Returns:
            List of TimeSlot objects for the specified day
        """
        return self.get_availability(user_id, target_date, target_date)
    
    def has_availability_on_day(self, user_id: Union[str, uuid.UUID], target_date: date) -> bool:
        """
        Check if user has any availability on a specific day.
        
        Args:
            user_id: String ID or UUID of the user (compatible with both test and production models)
            target_date: Date to check
            
        Returns:
            True if user has availability on the specified day
        """
        day_of_week = target_date.weekday()
        
        # Convert string ID to UUID if necessary
        if isinstance(user_id, str):
            try:
                user_uuid = uuid.UUID(user_id)
            except ValueError:
                # If it's not a valid UUID string, use it as-is (for test models)
                user_uuid = user_id
        else:
            user_uuid = user_id
        
        availability_count = self.db.query(Availability).filter(
            and_(
                Availability.user_id == user_uuid,
                Availability.day_of_week == day_of_week
            )
        ).count()
        
        return availability_count > 0
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from app.core.database import get_db
from app.core.dependencies import get_current_user, get_availability_service
from app.services.availability_service import AvailabilityService, TimeSlot, AvailabilityUpdate
from app.models.models import User

router = APIRouter(prefix="/api/availability", tags=["availability"])


@router.get("/", response_model=List[TimeSlot])
async def get_availability(
    start_date: Optional[date] = Query(None, description="Start date for availability query (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date for availability query (YYYY-MM-DD)"),
    current_user: User = Depends(get_current_user),
    availability_service: AvailabilityService = Depends(get_availability_service)
):
    """
    Get availability with optional date range filters
    """
    try:
        # Default to next 30 days if no dates provided
        if start_date is None:
            start_date = date.today()
        if end_date is None:
            from datetime import timedelta
            end_date = start_date + timedelta(days=30)
        
        # Validate date range
        if start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start date must be before or equal to end date"
            )
        
        availability = availability_service.get_availability(
            current_user.id, 
            start_date=start_date, 
            end_date=end_date
        )
        return availability
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve availability"
        )


@router.put("/", status_code=status.HTTP_200_OK)
async def update_availability(
    availability_updates: List[AvailabilityUpdate],
    current_user: User = Depends(get_current_user),
    availability_service: AvailabilityService = Depends(get_availability_service)
):
    """
    Update availability settings
    """
    try:
        # Validate input
        if not availability_updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one availability update is required"
            )
        
        success = availability_service.set_availability(current_user.id, availability_updates)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update availability"
            )
        
        return {"message": "Availability updated successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update availability"
        )
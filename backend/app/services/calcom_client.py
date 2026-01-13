"""
Cal.com API client wrapper with retry logic and error handling.
"""

import asyncio
import logging
from datetime import date, datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class CalcomBooking(BaseModel):
    """Data model for Cal.com booking requests."""
    eventTypeId: int
    start: str  # ISO datetime string
    end: str    # ISO datetime string
    attendee: Dict[str, str]  # {"name": "...", "email": "..."}
    metadata: Optional[Dict[str, Any]] = None


class CalcomBookingResponse(BaseModel):
    """Response model for Cal.com booking operations."""
    id: int
    uid: str
    title: str
    startTime: str
    endTime: str
    attendees: List[Dict[str, Any]]
    status: str


class CalcomAvailability(BaseModel):
    """Data model for Cal.com availability."""
    dateRanges: List[Dict[str, str]]  # [{"start": "...", "end": "..."}]
    timeZone: str = "UTC"


class CalcomError(Exception):
    """Base exception for Cal.com API errors."""
    pass


class CalcomRateLimitError(CalcomError):
    """Exception for rate limit errors."""
    pass


class CalcomClient:
    """
    Cal.com API client with authentication, retry logic, and error handling.
    
    Handles:
    - API authentication with API key
    - Exponential backoff retry logic
    - Rate limit handling
    - Network error recovery
    """
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        # Use provided values or fall back to settings
        if api_key is not None:
            self.api_key = api_key
        else:
            self.api_key = settings.calcom_api_key
            
        if base_url is not None:
            self.base_url = base_url
        else:
            self.base_url = settings.calcom_base_url
        
        if not self.api_key:
            raise ValueError("Cal.com API key is required")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Retry configuration
        self.max_retries = 3
        self.base_delay = 1.0  # Base delay in seconds
        self.max_delay = 60.0  # Maximum delay in seconds
    
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic and error handling.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            data: Request body data
            params: Query parameters
            
        Returns:
            Response data as dictionary
            
        Raises:
            CalcomError: For API errors
            CalcomRateLimitError: For rate limit errors
        """
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.request(
                        method=method,
                        url=url,
                        headers=self.headers,
                        json=data,
                        params=params
                    )
                    
                    # Handle rate limiting
                    if response.status_code == 429:
                        if attempt < self.max_retries:
                            delay = self._calculate_delay(attempt)
                            logger.warning(f"Rate limited, retrying in {delay}s (attempt {attempt + 1})")
                            await asyncio.sleep(delay)
                            continue
                        else:
                            raise CalcomRateLimitError("Rate limit exceeded, max retries reached")
                    
                    # Handle other HTTP errors
                    if response.status_code >= 400:
                        error_msg = f"Cal.com API error {response.status_code}: {response.text}"
                        logger.error(error_msg)
                        
                        # Don't retry client errors (4xx) except rate limits
                        if 400 <= response.status_code < 500 and response.status_code != 429:
                            raise CalcomError(error_msg)
                        
                        # Retry server errors (5xx)
                        if attempt < self.max_retries:
                            delay = self._calculate_delay(attempt)
                            logger.warning(f"Server error, retrying in {delay}s (attempt {attempt + 1})")
                            await asyncio.sleep(delay)
                            continue
                        else:
                            raise CalcomError(error_msg)
                    
                    # Success
                    return response.json()
                    
            except httpx.RequestError as e:
                # Network errors - retry with exponential backoff
                if attempt < self.max_retries:
                    delay = self._calculate_delay(attempt)
                    logger.warning(f"Network error: {e}, retrying in {delay}s (attempt {attempt + 1})")
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise CalcomError(f"Network error after {self.max_retries} retries: {e}")
        
        raise CalcomError("Unexpected error in request handling")
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay."""
        delay = self.base_delay * (2 ** attempt)
        return min(delay, self.max_delay)
    
    async def create_booking(self, booking_data: CalcomBooking) -> CalcomBookingResponse:
        """
        Create a new booking in Cal.com.
        
        Args:
            booking_data: Booking information
            
        Returns:
            Created booking response
            
        Raises:
            CalcomError: If booking creation fails
            CalcomRateLimitError: If rate limit is exceeded
        """
        try:
            response_data = await self._make_request(
                method="POST",
                endpoint="/bookings",
                data=booking_data.model_dump()
            )
            return CalcomBookingResponse(**response_data)
        except CalcomRateLimitError:
            # Re-raise rate limit errors as-is
            raise
        except Exception as e:
            logger.error(f"Failed to create booking: {e}")
            raise CalcomError(f"Failed to create booking: {e}")
    
    async def update_booking(self, booking_id: str, update_data: CalcomBooking) -> CalcomBookingResponse:
        """
        Update an existing booking in Cal.com.
        
        Args:
            booking_id: ID of the booking to update
            update_data: Updated booking information
            
        Returns:
            Updated booking response
            
        Raises:
            CalcomError: If booking update fails
        """
        try:
            response_data = await self._make_request(
                method="PATCH",
                endpoint=f"/bookings/{booking_id}",
                data=update_data.model_dump()
            )
            return CalcomBookingResponse(**response_data)
        except Exception as e:
            logger.error(f"Failed to update booking {booking_id}: {e}")
            raise CalcomError(f"Failed to update booking: {e}")
    
    async def delete_booking(self, booking_id: str) -> bool:
        """
        Delete a booking from Cal.com.
        
        Args:
            booking_id: ID of the booking to delete
            
        Returns:
            True if deletion was successful
            
        Raises:
            CalcomError: If booking deletion fails
        """
        try:
            await self._make_request(
                method="DELETE",
                endpoint=f"/bookings/{booking_id}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to delete booking {booking_id}: {e}")
            raise CalcomError(f"Failed to delete booking: {e}")
    
    async def get_availability(self, start_date: date, end_date: date) -> CalcomAvailability:
        """
        Get availability from Cal.com for a date range.
        
        Args:
            start_date: Start date for availability query
            end_date: End date for availability query
            
        Returns:
            Availability data
            
        Raises:
            CalcomError: If availability retrieval fails
        """
        try:
            params = {
                "dateFrom": start_date.isoformat(),
                "dateTo": end_date.isoformat()
            }
            
            response_data = await self._make_request(
                method="GET",
                endpoint="/availability",
                params=params
            )
            
            return CalcomAvailability(**response_data)
        except Exception as e:
            logger.error(f"Failed to get availability: {e}")
            raise CalcomError(f"Failed to get availability: {e}")
    
    async def update_availability(self, availability_data: CalcomAvailability) -> bool:
        """
        Update availability in Cal.com.
        
        Args:
            availability_data: New availability configuration
            
        Returns:
            True if update was successful
            
        Raises:
            CalcomError: If availability update fails
        """
        try:
            await self._make_request(
                method="PUT",
                endpoint="/availability",
                data=availability_data.model_dump()
            )
            return True
        except Exception as e:
            logger.error(f"Failed to update availability: {e}")
            raise CalcomError(f"Failed to update availability: {e}")


# Global client instance
calcom_client = CalcomClient()
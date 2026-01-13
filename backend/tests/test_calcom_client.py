"""
Unit tests for Cal.com client error handling
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import date, datetime
import httpx

from app.services.calcom_client import (
    CalcomClient, 
    CalcomError, 
    CalcomRateLimitError,
    CalcomBooking,
    CalcomAvailability
)


@pytest.fixture
def calcom_client():
    """Create a Cal.com client for testing"""
    return CalcomClient(api_key="test_api_key", base_url="https://api.test.com/v1")


@pytest.fixture
def sample_booking_data():
    """Sample booking data for tests"""
    return CalcomBooking(
        eventTypeId=123,
        start="2024-01-15T10:00:00Z",
        end="2024-01-15T11:00:00Z",
        attendee={"name": "John Doe", "email": "john@example.com"}
    )


@pytest.fixture
def sample_availability_data():
    """Sample availability data for tests"""
    return CalcomAvailability(
        dateRanges=[
            {"start": "2024-01-15T09:00:00Z", "end": "2024-01-15T17:00:00Z"}
        ],
        timeZone="UTC"
    )


class TestCalcomClientRetryLogic:
    """Test retry logic on various failures"""
    
    @pytest.mark.asyncio
    async def test_retry_on_server_error(self, calcom_client):
        """
        Test retry logic when server returns 5xx errors
        Requirements: 7.4
        """
        with patch('httpx.AsyncClient') as mock_client:
            # Mock responses: 500, 500, 200 (success on third try)
            mock_response_500 = MagicMock()
            mock_response_500.status_code = 500
            mock_response_500.text = "Internal Server Error"
            
            mock_response_200 = MagicMock()
            mock_response_200.status_code = 200
            mock_response_200.json.return_value = {
                "id": 123,
                "uid": "test-uid",
                "title": "Test Booking",
                "startTime": "2024-01-15T10:00:00Z",
                "endTime": "2024-01-15T11:00:00Z",
                "attendees": [],
                "status": "confirmed"
            }
            
            mock_client_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            mock_client_instance.request.side_effect = [
                mock_response_500,  # First attempt fails
                mock_response_500,  # Second attempt fails
                mock_response_200   # Third attempt succeeds
            ]
            
            booking_data = CalcomBooking(
                eventTypeId=123,
                start="2024-01-15T10:00:00Z",
                end="2024-01-15T11:00:00Z",
                attendee={"name": "John Doe", "email": "john@example.com"}
            )
            
            # Should succeed after retries
            result = await calcom_client.create_booking(booking_data)
            assert result.id == 123
            assert mock_client_instance.request.call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_exhaustion_on_server_error(self, calcom_client):
        """
        Test that retries are exhausted and error is raised
        Requirements: 7.4
        """
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            
            mock_client_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            mock_client_instance.request.return_value = mock_response
            
            booking_data = CalcomBooking(
                eventTypeId=123,
                start="2024-01-15T10:00:00Z",
                end="2024-01-15T11:00:00Z",
                attendee={"name": "John Doe", "email": "john@example.com"}
            )
            
            # Should raise CalcomError after max retries
            with pytest.raises(CalcomError, match="Cal.com API error 500"):
                await calcom_client.create_booking(booking_data)
            
            # Should have tried max_retries + 1 times
            assert mock_client_instance.request.call_count == calcom_client.max_retries + 1
    
    @pytest.mark.asyncio
    async def test_no_retry_on_client_error(self, calcom_client):
        """
        Test that client errors (4xx) are not retried except rate limits
        Requirements: 7.4
        """
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_response.text = "Bad Request"
            
            mock_client_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            mock_client_instance.request.return_value = mock_response
            
            booking_data = CalcomBooking(
                eventTypeId=123,
                start="2024-01-15T10:00:00Z",
                end="2024-01-15T11:00:00Z",
                attendee={"name": "John Doe", "email": "john@example.com"}
            )
            
            # Should raise CalcomError immediately without retries
            with pytest.raises(CalcomError, match="Cal.com API error 400"):
                await calcom_client.create_booking(booking_data)
            
            # Should have tried only once
            assert mock_client_instance.request.call_count == 1


class TestCalcomClientRateLimitHandling:
    """Test rate limit handling"""
    
    @pytest.mark.asyncio
    async def test_rate_limit_retry_success(self, calcom_client):
        """
        Test successful retry after rate limit
        Requirements: 7.4
        """
        with patch('httpx.AsyncClient') as mock_client, \
             patch('asyncio.sleep') as mock_sleep:
            
            # Mock responses: 429, 429, 200 (success on third try)
            mock_response_429 = MagicMock()
            mock_response_429.status_code = 429
            mock_response_429.text = "Rate Limited"
            
            mock_response_200 = MagicMock()
            mock_response_200.status_code = 200
            mock_response_200.json.return_value = {
                "id": 123,
                "uid": "test-uid",
                "title": "Test Booking",
                "startTime": "2024-01-15T10:00:00Z",
                "endTime": "2024-01-15T11:00:00Z",
                "attendees": [],
                "status": "confirmed"
            }
            
            mock_client_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            mock_client_instance.request.side_effect = [
                mock_response_429,  # First attempt rate limited
                mock_response_429,  # Second attempt rate limited
                mock_response_200   # Third attempt succeeds
            ]
            
            booking_data = CalcomBooking(
                eventTypeId=123,
                start="2024-01-15T10:00:00Z",
                end="2024-01-15T11:00:00Z",
                attendee={"name": "John Doe", "email": "john@example.com"}
            )
            
            # Should succeed after retries
            result = await calcom_client.create_booking(booking_data)
            assert result.id == 123
            assert mock_client_instance.request.call_count == 3
            
            # Should have slept between retries (exponential backoff)
            assert mock_sleep.call_count == 2
            # Check exponential backoff delays
            sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
            assert sleep_calls[0] == 1.0  # First retry delay
            assert sleep_calls[1] == 2.0  # Second retry delay
    
    @pytest.mark.asyncio
    async def test_rate_limit_exhaustion(self, calcom_client):
        """
        Test rate limit error when retries are exhausted
        Requirements: 7.4
        """
        with patch('httpx.AsyncClient') as mock_client, \
             patch('asyncio.sleep') as mock_sleep:
            
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_response.text = "Rate Limited"
            
            mock_client_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            mock_client_instance.request.return_value = mock_response
            
            booking_data = CalcomBooking(
                eventTypeId=123,
                start="2024-01-15T10:00:00Z",
                end="2024-01-15T11:00:00Z",
                attendee={"name": "John Doe", "email": "john@example.com"}
            )
            
            # Should raise CalcomRateLimitError after max retries
            with pytest.raises(CalcomRateLimitError, match="Rate limit exceeded"):
                await calcom_client.create_booking(booking_data)
            
            # Should have tried max_retries + 1 times
            assert mock_client_instance.request.call_count == calcom_client.max_retries + 1
            # Should have slept max_retries times
            assert mock_sleep.call_count == calcom_client.max_retries


class TestCalcomClientNetworkErrorRecovery:
    """Test network error recovery"""
    
    @pytest.mark.asyncio
    async def test_network_error_retry_success(self, calcom_client):
        """
        Test successful retry after network errors
        Requirements: 7.4
        """
        with patch('httpx.AsyncClient') as mock_client, \
             patch('asyncio.sleep') as mock_sleep:
            
            mock_response_200 = MagicMock()
            mock_response_200.status_code = 200
            mock_response_200.json.return_value = {
                "id": 123,
                "uid": "test-uid",
                "title": "Test Booking",
                "startTime": "2024-01-15T10:00:00Z",
                "endTime": "2024-01-15T11:00:00Z",
                "attendees": [],
                "status": "confirmed"
            }
            
            mock_client_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            mock_client_instance.request.side_effect = [
                httpx.ConnectError("Connection failed"),  # First attempt fails
                httpx.TimeoutException("Request timeout"),  # Second attempt fails
                mock_response_200  # Third attempt succeeds
            ]
            
            booking_data = CalcomBooking(
                eventTypeId=123,
                start="2024-01-15T10:00:00Z",
                end="2024-01-15T11:00:00Z",
                attendee={"name": "John Doe", "email": "john@example.com"}
            )
            
            # Should succeed after retries
            result = await calcom_client.create_booking(booking_data)
            assert result.id == 123
            assert mock_client_instance.request.call_count == 3
            
            # Should have slept between retries
            assert mock_sleep.call_count == 2
    
    @pytest.mark.asyncio
    async def test_network_error_exhaustion(self, calcom_client):
        """
        Test network error when retries are exhausted
        Requirements: 7.4
        """
        with patch('httpx.AsyncClient') as mock_client, \
             patch('asyncio.sleep') as mock_sleep:
            
            mock_client_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            mock_client_instance.request.side_effect = httpx.ConnectError("Connection failed")
            
            booking_data = CalcomBooking(
                eventTypeId=123,
                start="2024-01-15T10:00:00Z",
                end="2024-01-15T11:00:00Z",
                attendee={"name": "John Doe", "email": "john@example.com"}
            )
            
            # Should raise CalcomError after max retries
            with pytest.raises(CalcomError, match="Network error after .* retries"):
                await calcom_client.create_booking(booking_data)
            
            # Should have tried max_retries + 1 times
            assert mock_client_instance.request.call_count == calcom_client.max_retries + 1
            # Should have slept max_retries times
            assert mock_sleep.call_count == calcom_client.max_retries


class TestCalcomClientMethods:
    """Test individual client methods with error scenarios"""
    
    @pytest.mark.asyncio
    async def test_create_booking_error_handling(self, calcom_client, sample_booking_data):
        """Test create_booking error handling"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_response.text = "Invalid booking data"
            
            mock_client_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            mock_client_instance.request.return_value = mock_response
            
            with pytest.raises(CalcomError, match="Failed to create booking"):
                await calcom_client.create_booking(sample_booking_data)
    
    @pytest.mark.asyncio
    async def test_update_booking_error_handling(self, calcom_client, sample_booking_data):
        """Test update_booking error handling"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_response.text = "Booking not found"
            
            mock_client_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            mock_client_instance.request.return_value = mock_response
            
            with pytest.raises(CalcomError, match="Failed to update booking"):
                await calcom_client.update_booking("123", sample_booking_data)
    
    @pytest.mark.asyncio
    async def test_delete_booking_error_handling(self, calcom_client):
        """Test delete_booking error handling"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_response.text = "Booking not found"
            
            mock_client_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            mock_client_instance.request.return_value = mock_response
            
            with pytest.raises(CalcomError, match="Failed to delete booking"):
                await calcom_client.delete_booking("123")
    
    @pytest.mark.asyncio
    async def test_get_availability_error_handling(self, calcom_client):
        """Test get_availability error handling"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Server error"
            
            mock_client_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            mock_client_instance.request.return_value = mock_response
            
            with pytest.raises(CalcomError, match="Failed to get availability"):
                await calcom_client.get_availability(date(2024, 1, 15), date(2024, 1, 16))
    
    @pytest.mark.asyncio
    async def test_update_availability_error_handling(self, calcom_client, sample_availability_data):
        """Test update_availability error handling"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_response.text = "Invalid availability data"
            
            mock_client_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            mock_client_instance.request.return_value = mock_response
            
            with pytest.raises(CalcomError, match="Failed to update availability"):
                await calcom_client.update_availability(sample_availability_data)


class TestCalcomClientConfiguration:
    """Test client configuration and initialization"""
    
    def test_client_initialization_without_api_key(self):
        """Test that client raises error without API key"""
        # Test direct initialization without API key
        with pytest.raises(ValueError, match="Cal.com API key is required"):
            CalcomClient(api_key="", base_url="https://api.test.com")
    
    def test_client_initialization_with_settings(self):
        """Test client initialization with settings"""
        # Test direct initialization with API key
        client = CalcomClient(api_key="test_key", base_url="https://api.test.com")
        assert client.api_key == "test_key"
        assert client.base_url == "https://api.test.com"
    
    def test_exponential_backoff_calculation(self, calcom_client):
        """Test exponential backoff delay calculation"""
        # Test delay calculation
        assert calcom_client._calculate_delay(0) == 1.0  # 1 * 2^0
        assert calcom_client._calculate_delay(1) == 2.0  # 1 * 2^1
        assert calcom_client._calculate_delay(2) == 4.0  # 1 * 2^2
        assert calcom_client._calculate_delay(3) == 8.0  # 1 * 2^3
        
        # Test max delay cap
        assert calcom_client._calculate_delay(10) == calcom_client.max_delay  # Should be capped
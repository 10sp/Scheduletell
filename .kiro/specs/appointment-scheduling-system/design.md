# Design Document: Appointment Scheduling System

## Overview

The appointment scheduling system is a full-stack application that enables a single authenticated user to manage appointments through a calendar-driven interface. The architecture follows a three-tier design:

1. **Frontend**: React/Vite application with Cal.com Atoms for calendar UI
2. **Backend**: FastAPI server serving as the single source of truth
3. **External Service**: Cal.com cloud API for scheduling engine capabilities

The backend maintains authoritative state for all appointments and availability, synchronizing with Cal.com to leverage their scheduling infrastructure while ensuring data consistency and reliability.

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend                             │
│                    (React + Vite)                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Dashboard   │  │   Calendar   │  │    Auth      │     │
│  │  Component   │  │  (Cal.com    │  │  Component   │     │
│  │              │  │   Atoms)     │  │              │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ HTTPS/REST
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │     Auth     │  │  Appointment │  │ Availability │     │
│  │   Service    │  │   Service    │  │   Service    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│  ┌──────────────┐  ┌──────────────┐                        │
│  │   Cal.com    │  │   Database   │                        │
│  │    Client    │  │    Layer     │                        │
│  └──────────────┘  └──────────────┘                        │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ Cal.com API
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Cal.com Cloud                             │
│              (Scheduling Engine)                             │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **User Authentication**: Frontend → Backend Auth Service → JWT Token
2. **Appointment Booking**: Frontend → Backend Appointment Service → Database + Cal.com API
3. **Availability Query**: Frontend → Backend Availability Service → Database
4. **Dashboard Load**: Frontend → Backend Appointment Service → Database

### Technology Stack

**Frontend:**
- React 18+ with TypeScript
- Vite for build tooling
- Cal.com Atoms for calendar components
- Axios for HTTP requests
- React Router for navigation
- TanStack Query for state management

**Backend:**
- FastAPI (Python 3.11+)
- SQLAlchemy for ORM
- PostgreSQL for database
- Pydantic for data validation
- JWT for authentication
- Cal.com Python SDK

## Components and Interfaces

### Backend Components

#### 1. Authentication Service

**Responsibilities:**
- User authentication and session management
- JWT token generation and validation
- Single user account management

**Interface:**
```python
class AuthService:
    def authenticate(username: str, password: str) -> AuthToken
    def validate_token(token: str) -> bool
    def get_current_user(token: str) -> User
```

#### 2. Appointment Service

**Responsibilities:**
- CRUD operations for appointments
- Double booking validation
- Appointment rescheduling logic
- Synchronization with Cal.com

**Interface:**
```python
class AppointmentService:
    def create_appointment(appointment_data: AppointmentCreate) -> Appointment
    def get_appointment(appointment_id: str) -> Appointment
    def get_appointments(start_date: datetime, end_date: datetime) -> List[Appointment]
    def update_appointment(appointment_id: str, update_data: AppointmentUpdate) -> Appointment
    def delete_appointment(appointment_id: str) -> bool
    def check_availability(start_time: datetime, duration: int) -> bool
```

#### 3. Availability Service

**Responsibilities:**
- Manage user availability windows
- Sync availability with Cal.com
- Query available time slots

**Interface:**
```python
class AvailabilityService:
    def get_availability(start_date: date, end_date: date) -> List[TimeSlot]
    def set_availability(availability_data: AvailabilityUpdate) -> bool
    def sync_with_calcom() -> bool
```

#### 4. Cal.com Client

**Responsibilities:**
- Wrapper around Cal.com API
- Handle API authentication
- Manage rate limiting and retries

**Interface:**
```python
class CalcomClient:
    def create_booking(booking_data: CalcomBooking) -> CalcomBookingResponse
    def update_booking(booking_id: str, update_data: CalcomBooking) -> CalcomBookingResponse
    def delete_booking(booking_id: str) -> bool
    def get_availability(start_date: date, end_date: date) -> CalcomAvailability
    def update_availability(availability_data: CalcomAvailability) -> bool
```

#### 5. Database Layer

**Responsibilities:**
- Data persistence
- Transaction management
- Query optimization

**Models:**
```python
class User:
    id: UUID
    username: str
    password_hash: str
    created_at: datetime

class Appointment:
    id: UUID
    user_id: UUID
    customer_name: str
    start_time: datetime
    duration_minutes: int
    calcom_booking_id: str
    created_at: datetime
    updated_at: datetime

class Availability:
    id: UUID
    user_id: UUID
    day_of_week: int
    start_time: time
    end_time: time
    created_at: datetime
```

### Frontend Components

#### 1. Dashboard Component

**Responsibilities:**
- Display upcoming appointments
- Provide navigation to booking/rescheduling
- Show appointment summary

**Props:**
```typescript
interface DashboardProps {
  appointments: Appointment[]
  onAppointmentClick: (appointmentId: string) => void
  onNewAppointment: () => void
}
```

#### 2. Calendar Component

**Responsibilities:**
- Render calendar view using Cal.com Atoms
- Handle date selection
- Display appointments on calendar

**Props:**
```typescript
interface CalendarProps {
  appointments: Appointment[]
  availability: TimeSlot[]
  onTimeSlotClick: (slot: TimeSlot) => void
  onAppointmentClick: (appointment: Appointment) => void
}
```

#### 3. Booking Form Component

**Responsibilities:**
- Collect appointment details
- Validate input
- Submit booking request

**Props:**
```typescript
interface BookingFormProps {
  selectedSlot: TimeSlot
  onSubmit: (bookingData: BookingFormData) => void
  onCancel: () => void
}
```

#### 4. Auth Component

**Responsibilities:**
- Handle login form
- Manage authentication state
- Redirect after successful login

**Props:**
```typescript
interface AuthProps {
  onLoginSuccess: (token: string) => void
}
```

### API Endpoints

**Authentication:**
- `POST /api/auth/login` - Authenticate user
- `POST /api/auth/logout` - Invalidate token
- `GET /api/auth/me` - Get current user

**Appointments:**
- `POST /api/appointments` - Create appointment
- `GET /api/appointments` - List appointments (with date range filters)
- `GET /api/appointments/{id}` - Get appointment details
- `PUT /api/appointments/{id}` - Update/reschedule appointment
- `DELETE /api/appointments/{id}` - Delete appointment

**Availability:**
- `GET /api/availability` - Get availability (with date range filters)
- `PUT /api/availability` - Update availability settings

## Data Models

### Appointment

```python
class AppointmentCreate(BaseModel):
    customer_name: str
    start_time: datetime
    duration_minutes: int

class AppointmentUpdate(BaseModel):
    customer_name: Optional[str]
    start_time: Optional[datetime]
    duration_minutes: Optional[int]

class AppointmentResponse(BaseModel):
    id: UUID
    customer_name: str
    start_time: datetime
    duration_minutes: int
    end_time: datetime
    created_at: datetime
    updated_at: datetime
```

### Availability

```python
class TimeSlot(BaseModel):
    start_time: datetime
    end_time: datetime
    available: bool

class AvailabilityUpdate(BaseModel):
    day_of_week: int
    start_time: time
    end_time: time
```

### Authentication

```python
class LoginRequest(BaseModel):
    username: str
    password: str

class AuthToken(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
```


## Correctness Properties

A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.

### Property 1: Authentication Required for Protected Resources

*For any* protected API endpoint, when a request is made without valid authentication, the system should deny access and return an authentication error.

**Validates: Requirements 1.2**

### Property 2: Expired Token Rejection

*For any* API endpoint requiring authentication, when a request is made with an expired token, the system should reject the request and require re-authentication.

**Validates: Requirements 1.4**

### Property 3: Complete Availability Retrieval

*For any* set of availability records in the database, when querying availability for a date range that includes those records, the system should return all matching availability records.

**Validates: Requirements 2.1**

### Property 4: Availability Read Consistency

*For any* availability update, when the availability is immediately retrieved after the update, the retrieved data should match the updated data.

**Validates: Requirements 2.3**

### Property 5: Appointment Creation Success

*For any* valid appointment data (customer name, start time, duration) where the time slot is available, creating an appointment should succeed and return the appointment with all provided fields.

**Validates: Requirements 3.1**

### Property 6: Availability Validation Before Booking

*For any* appointment booking attempt, if the requested time slot is not available, the system should reject the booking before persisting any data.

**Validates: Requirements 3.2**

### Property 7: Double Booking Prevention

*For any* two appointments with overlapping time ranges (accounting for duration), the system should prevent the second appointment from being created and return an error.

**Validates: Requirements 3.3, 6.1, 6.2, 6.3**

### Property 8: Appointment Persistence Round Trip

*For any* successfully created appointment, when retrieving that appointment by ID, the system should return an appointment with matching customer name, start time, and duration.

**Validates: Requirements 3.4, 10.1**

### Property 9: Appointment Rescheduling Updates Time

*For any* existing appointment, when rescheduling to a new valid time slot, the appointment's start time should be updated to the new time.

**Validates: Requirements 4.1**

### Property 10: Rescheduling Conflict Prevention

*For any* appointment rescheduling attempt, if the new time slot conflicts with another existing appointment, the system should reject the reschedule and return an error.

**Validates: Requirements 4.2, 4.3**

### Property 11: Rescheduling Preserves Appointment Details

*For any* appointment, when rescheduling to a new time, the customer name and duration should remain unchanged.

**Validates: Requirements 4.5**

### Property 12: Dashboard Returns All Upcoming Appointments

*For any* set of appointments in the database, when querying for upcoming appointments from the current time, the system should return all appointments with start times in the future.

**Validates: Requirements 5.1**

### Property 13: Appointment Response Contains Required Fields

*For any* appointment returned by the API, the response should include appointment time, duration, and customer name.

**Validates: Requirements 5.2**

### Property 14: Appointments Sorted Chronologically

*For any* list of appointments returned by the dashboard, the appointments should be ordered by start time in ascending order.

**Validates: Requirements 5.4**

### Property 15: Input Validation Rejects Invalid Data

*For any* API endpoint, when receiving a request with invalid input data (missing required fields, invalid formats, or out-of-range values), the system should reject the request before processing.

**Validates: Requirements 8.4**

### Property 16: Error Responses Include Status and Message

*For any* API operation that fails, the response should include an appropriate HTTP status code and a descriptive error message.

**Validates: Requirements 8.5**

### Property 17: Availability Persistence Round Trip

*For any* availability configuration saved to the database, when retrieving that availability configuration, the system should return matching day of week, start time, and end time.

**Validates: Requirements 10.2**

### Property 18: Data Persistence Across Restarts

*For any* appointment or availability data persisted before a system restart, when querying for that data after restart, the system should return the same data.

**Validates: Requirements 10.3**

## Error Handling

### Authentication Errors

- **Invalid Credentials**: Return 401 Unauthorized with message "Invalid username or password"
- **Expired Token**: Return 401 Unauthorized with message "Token has expired"
- **Missing Token**: Return 401 Unauthorized with message "Authentication required"

### Booking Errors

- **Double Booking**: Return 409 Conflict with message "Time slot is already booked"
- **Invalid Time Slot**: Return 400 Bad Request with message "Selected time is not available"
- **Past Date Booking**: Return 400 Bad Request with message "Cannot book appointments in the past"
- **Invalid Duration**: Return 400 Bad Request with message "Duration must be positive"

### Validation Errors

- **Missing Required Field**: Return 422 Unprocessable Entity with field name and "Field is required"
- **Invalid Format**: Return 422 Unprocessable Entity with field name and format requirements
- **Out of Range**: Return 422 Unprocessable Entity with field name and valid range

### Cal.com Integration Errors

- **Sync Failure**: Log error with full context, retry up to 3 times with exponential backoff
- **API Rate Limit**: Wait for rate limit reset, queue operation for retry
- **Network Error**: Log error, retry with exponential backoff

### Database Errors

- **Connection Failure**: Log error, attempt reconnection, return 503 Service Unavailable
- **Constraint Violation**: Return 409 Conflict with descriptive message
- **Transaction Failure**: Rollback transaction, log error, return 500 Internal Server Error

## Testing Strategy

### Dual Testing Approach

The system will employ both unit testing and property-based testing to ensure comprehensive coverage:

- **Unit tests**: Verify specific examples, edge cases, and error conditions
- **Property tests**: Verify universal properties across all inputs

Both testing approaches are complementary and necessary. Unit tests catch concrete bugs in specific scenarios, while property tests verify general correctness across a wide range of inputs.

### Property-Based Testing

**Framework**: Hypothesis (Python) for backend testing

**Configuration**:
- Minimum 100 iterations per property test
- Each test must reference its design document property
- Tag format: `# Feature: appointment-scheduling-system, Property {number}: {property_text}`

**Test Coverage**:
- Each correctness property listed above must be implemented as a property-based test
- Tests should generate random valid inputs to verify properties hold universally
- Edge cases (empty strings, boundary dates, maximum durations) should be included in generators

**Example Property Test Structure**:
```python
from hypothesis import given, strategies as st

# Feature: appointment-scheduling-system, Property 7: Double Booking Prevention
@given(
    appointment1=appointment_strategy(),
    appointment2=overlapping_appointment_strategy()
)
def test_double_booking_prevention(appointment1, appointment2):
    # Create first appointment
    created1 = appointment_service.create_appointment(appointment1)
    assert created1 is not None
    
    # Attempt to create overlapping appointment
    with pytest.raises(ConflictError):
        appointment_service.create_appointment(appointment2)
```

### Unit Testing

**Framework**: pytest for backend, Vitest for frontend

**Focus Areas**:
- Specific examples demonstrating correct behavior
- Edge cases (empty inputs, boundary values, null handling)
- Error conditions and exception handling
- Integration points between components

**Backend Unit Tests**:
- Authentication flow with valid/invalid credentials
- Appointment CRUD operations with specific test data
- Cal.com client error handling and retries
- Database transaction rollback scenarios

**Frontend Unit Tests**:
- Component rendering with various props
- Form validation with specific invalid inputs
- API error handling and user feedback
- Navigation and routing

### Integration Testing

**Scope**: End-to-end flows across multiple components

**Test Scenarios**:
- Complete booking flow: authentication → availability check → booking → dashboard display
- Rescheduling flow: select appointment → validate new time → update → verify change
- Error recovery: Cal.com failure → retry → success
- Session expiration: authenticated request → token expires → re-authentication required

### Test Data Strategy

**Property Test Generators**:
- Valid appointment data: random customer names, future dates, durations 15-120 minutes
- Overlapping appointments: generate pairs with guaranteed time overlap
- Availability windows: random day/time combinations
- Invalid inputs: empty strings, past dates, negative durations, malformed data

**Unit Test Fixtures**:
- Predefined user credentials
- Sample appointments with known times
- Mock Cal.com responses
- Database seed data for consistent test state

### Continuous Testing

- Run unit tests on every commit
- Run property tests on pull requests
- Run integration tests before deployment
- Monitor test execution time and optimize slow tests

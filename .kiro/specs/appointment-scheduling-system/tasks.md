# Implementation Plan: Appointment Scheduling System

## Overview

This implementation plan breaks down the appointment scheduling system into discrete coding tasks. The system uses FastAPI (Python) for the backend and React/Vite (TypeScript) for the frontend. Tasks are organized to build incrementally, with testing integrated throughout to validate functionality early.

## Tasks

- [x] 1. Set up project structure and development environment
  - Create backend directory with FastAPI project structure
  - Create frontend directory with Vite + React + TypeScript
  - Set up PostgreSQL database
  - Configure environment variables for both projects
  - Install core dependencies (FastAPI, SQLAlchemy, React, Cal.com Atoms)
  - Set up testing frameworks (pytest, Hypothesis, Vitest)
  - _Requirements: 8.1, 8.2, 8.3_

- [x] 2. Implement database models and migrations
  - [x] 2.1 Create SQLAlchemy models for User, Appointment, and Availability
    - Define User model with id, username, password_hash, created_at
    - Define Appointment model with id, user_id, customer_name, start_time, duration_minutes, calcom_booking_id, created_at, updated_at
    - Define Availability model with id, user_id, day_of_week, start_time, end_time, created_at
    - _Requirements: 10.1, 10.2_
  
  - [x] 2.2 Write property test for appointment persistence
    - **Property 8: Appointment Persistence Round Trip**
    - **Validates: Requirements 3.4, 10.1**
  
  - [x] 2.3 Write property test for availability persistence
    - **Property 17: Availability Persistence Round Trip**
    - **Validates: Requirements 10.2**

- [x] 3. Implement authentication service
  - [x] 3.1 Create authentication service with JWT token generation
    - Implement password hashing with bcrypt
    - Implement JWT token creation and validation
    - Create user authentication logic
    - _Requirements: 1.1, 1.3_
  
  - [x] 3.2 Write property test for authentication protection
    - **Property 1: Authentication Required for Protected Resources**
    - **Validates: Requirements 1.2**
  
  - [x] 3.3 Write property test for expired token rejection
    - **Property 2: Expired Token Rejection**
    - **Validates: Requirements 1.4**
  
  - [x] 3.4 Write unit tests for authentication edge cases
    - Test invalid credentials
    - Test missing token
    - Test malformed token
    - _Requirements: 1.2, 1.4_

- [x] 4. Implement Cal.com client wrapper
  - [x] 4.1 Create Cal.com API client class
    - Implement authentication with Cal.com API
    - Implement create_booking method
    - Implement update_booking method
    - Implement delete_booking method
    - Implement get_availability method
    - Implement update_availability method
    - Add retry logic with exponential backoff
    - _Requirements: 7.1, 7.4_
  
  - [x] 4.2 Write unit tests for Cal.com error handling
    - Test retry logic on failure
    - Test rate limit handling
    - Test network error recovery
    - _Requirements: 7.4_

- [x] 5. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement availability service
  - [x] 6.1 Create availability service with CRUD operations
    - Implement get_availability method with date range filtering
    - Implement set_availability method
    - Implement sync_with_calcom method
    - _Requirements: 2.1, 2.3_
  
  - [x] 6.2 Write property test for complete availability retrieval
    - **Property 3: Complete Availability Retrieval**
    - **Validates: Requirements 2.1**
  
  - [x] 6.3 Write property test for availability read consistency
    - **Property 4: Availability Read Consistency**
    - **Validates: Requirements 2.3**

- [x] 7. Implement appointment service core logic
  - [x] 7.1 Create appointment service with validation logic
    - Implement check_availability method to detect time slot conflicts
    - Implement overlap detection accounting for duration
    - Implement create_appointment method with validation
    - Implement get_appointment method
    - Implement get_appointments method with date range filtering
    - _Requirements: 3.1, 3.2, 6.1, 6.2, 6.3_
  
  - [x] 7.2 Write property test for appointment creation
    - **Property 5: Appointment Creation Success**
    - **Validates: Requirements 3.1**
  
  - [x] 7.3 Write property test for availability validation
    - **Property 6: Availability Validation Before Booking**
    - **Validates: Requirements 3.2**
  
  - [x] 7.4 Write property test for double booking prevention
    - **Property 7: Double Booking Prevention**
    - **Validates: Requirements 3.3, 6.1, 6.2, 6.3**
  
  - [x] 7.5 Write unit tests for booking edge cases
    - Test booking in the past
    - Test booking with zero duration
    - Test booking with negative duration
    - _Requirements: 3.1, 3.2_

- [x] 8. Implement appointment rescheduling logic
  - [x] 8.1 Add update_appointment method to appointment service
    - Implement rescheduling with conflict validation
    - Ensure customer name and duration preservation
    - Integrate with Cal.com update
    - _Requirements: 4.1, 4.2, 4.3, 4.5_
  
  - [x] 8.2 Write property test for rescheduling updates time
    - **Property 9: Appointment Rescheduling Updates Time**
    - **Validates: Requirements 4.1**
  
  - [x] 8.3 Write property test for rescheduling conflict prevention
    - **Property 10: Rescheduling Conflict Prevention**
    - **Validates: Requirements 4.2, 4.3**
  
  - [x] 8.4 Write property test for rescheduling preserves details
    - **Property 11: Rescheduling Preserves Appointment Details**
    - **Validates: Requirements 4.5**

- [x] 9. Implement appointment deletion
  - [x] 9.1 Add delete_appointment method to appointment service
    - Implement soft delete or hard delete based on requirements
    - Integrate with Cal.com deletion
    - _Requirements: 8.3_

- [x] 10. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [-] 11. Implement FastAPI endpoints
  - [x] 11.1 Create authentication endpoints
    - POST /api/auth/login - authenticate and return JWT
    - POST /api/auth/logout - invalidate token
    - GET /api/auth/me - get current user
    - _Requirements: 1.2, 1.3_
  
  - [x] 11.2 Create appointment endpoints
    - POST /api/appointments - create appointment
    - GET /api/appointments - list appointments with filters
    - GET /api/appointments/{id} - get appointment details
    - PUT /api/appointments/{id} - update/reschedule appointment
    - DELETE /api/appointments/{id} - delete appointment
    - _Requirements: 8.3_
  
  - [x] 11.3 Create availability endpoints
    - GET /api/availability - get availability with date range
    - PUT /api/availability - update availability settings
    - _Requirements: 8.2_
  
  - [x] 11.4 Write property test for input validation
    - **Property 15: Input Validation Rejects Invalid Data**
    - **Validates: Requirements 8.4**
  
  - [x] 11.5 Write property test for error response format
    - **Property 16: Error Responses Include Status and Message**
    - **Validates: Requirements 8.5**
  
  - [x] 11.6 Write unit tests for API endpoints
    - Test each endpoint with valid requests
    - Test error responses for invalid inputs
    - Test authentication middleware
    - _Requirements: 8.3, 8.4, 8.5_

- [x] 12. Implement dashboard query logic
  - [x] 12.1 Add dashboard-specific query methods
    - Implement get_upcoming_appointments method
    - Implement chronological sorting
    - Ensure all required fields in response
    - _Requirements: 5.1, 5.2, 5.4_
  
  - [x] 12.2 Write property test for dashboard returns all upcoming appointments
    - **Property 12: Dashboard Returns All Upcoming Appointments**
    - **Validates: Requirements 5.1**
  
  - [x] 12.3 Write property test for appointment response fields
    - **Property 13: Appointment Response Contains Required Fields**
    - **Validates: Requirements 5.2**
  
  - [x] 12.4 Write property test for chronological sorting
    - **Property 14: Appointments Sorted Chronologically**
    - **Validates: Requirements 5.4**

- [x] 13. Implement data persistence across restarts
  - [x] 13.1 Ensure proper database connection management
    - Configure connection pooling
    - Implement graceful shutdown
    - Test data persistence
    - _Requirements: 10.3_
  
  - [x] 13.2 Write property test for persistence across restarts
    - **Property 18: Data Persistence Across Restarts**
    - **Validates: Requirements 10.3**

- [ ] 14. Checkpoint - Backend complete, all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [-] 15. Set up frontend authentication
  - [x] 15.1 Create authentication context and hooks
    - Implement useAuth hook for managing auth state
    - Implement token storage in localStorage
    - Implement automatic token refresh
    - _Requirements: 1.2, 1.3, 1.4_
  
  - [x] 15.2 Create login component
    - Build login form with validation
    - Handle authentication errors
    - Redirect to dashboard on success
    - _Requirements: 1.3_
  
  - [ ] 15.3 Write unit tests for authentication components
    - Test login form validation
    - Test successful login flow
    - Test error handling
    - _Requirements: 1.3_

- [ ] 16. Implement frontend API client
  - [x] 16.1 Create API client with axios
    - Configure base URL and interceptors
    - Add authentication header injection
    - Implement error handling
    - Create typed API methods for all endpoints
    - _Requirements: 8.1, 8.2, 8.3_
  
  - [x] 16.2 Set up TanStack Query for state management
    - Configure query client
    - Create query hooks for appointments
    - Create mutation hooks for booking/rescheduling
    - _Requirements: 5.3_

- [-] 17. Implement calendar component
  - [x] 17.1 Create calendar view using Cal.com Atoms
    - Integrate Cal.com Atoms calendar component
    - Display appointments on calendar
    - Handle date navigation
    - Implement time slot click handlers
    - _Requirements: 9.1, 9.2, 9.5_
  
  - [ ] 17.2 Write unit tests for calendar component
    - Test appointment rendering
    - Test date navigation
    - Test click handlers
    - _Requirements: 9.1, 9.2_

- [ ] 18. Implement booking form component
  - [x] 18.1 Create booking form with validation
    - Build form with customer name, date, time, duration inputs
    - Implement client-side validation
    - Handle booking submission
    - Display success/error messages
    - _Requirements: 3.1_
  
  - [x] 18.2 Write unit tests for booking form
    - Test form validation
    - Test submission handling
    - Test error display
    - _Requirements: 3.1_

- [ ] 19. Implement dashboard component
  - [x] 19.1 Create dashboard with appointment list
    - Fetch and display upcoming appointments
    - Show appointment time, duration, customer name
    - Implement appointment click handler
    - Add "New Appointment" button
    - _Requirements: 5.1, 5.2, 5.4_
  
  - [-] 19.2 Write unit tests for dashboard component
    - Test appointment list rendering
    - Test empty state
    - Test click handlers
    - _Requirements: 5.1, 5.2_

- [-] 20. Implement appointment detail and reschedule UI
  - [x] 20.1 Create appointment detail modal
    - Display full appointment details
    - Add "Reschedule" button
    - Add "Delete" button
    - _Requirements: 4.1, 9.3_
  
  - [x] 20.2 Create reschedule form
    - Allow date and time modification
    - Validate new time slot availability
    - Handle reschedule submission
    - Display conflict errors
    - _Requirements: 4.1, 4.2, 4.3_
  
  - [ ] 20.3 Write unit tests for reschedule functionality
    - Test reschedule form
    - Test conflict handling
    - Test success flow
    - _Requirements: 4.1, 4.2, 4.3_

- [x] 21. Implement routing and navigation
  - [x] 21.1 Set up React Router
    - Configure routes for login, dashboard, calendar
    - Implement protected route wrapper
    - Add navigation components
    - _Requirements: 9.5_

- [ ] 22. Checkpoint - Frontend complete, all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 23. Integration and end-to-end wiring
  - [x] 23.1 Connect frontend to backend API
    - Verify all API endpoints work with frontend
    - Test complete booking flow
    - Test complete rescheduling flow
    - Test authentication flow
    - _Requirements: All_
  
  - [x] 23.2 Write integration tests
    - Test end-to-end booking flow
    - Test end-to-end rescheduling flow
    - Test authentication and session management
    - _Requirements: All_

- [ ] 24. Final checkpoint - Complete system test
  - Run all unit tests
  - Run all property tests
  - Run all integration tests
  - Verify Cal.com integration works
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Each task references specific requirements for traceability
- Property tests validate universal correctness properties with minimum 100 iterations
- Unit tests validate specific examples and edge cases
- Backend uses Python with FastAPI, SQLAlchemy, and Hypothesis for property testing
- Frontend uses TypeScript with React, Vite, and Vitest for testing
- Cal.com integration is handled through the Cal.com API client wrapper

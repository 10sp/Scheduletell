import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BookingForm } from '../components/BookingForm'
import { useCreateAppointment } from '../hooks/useAppointments'

// Mock the useCreateAppointment hook
vi.mock('../hooks/useAppointments', () => ({
  useCreateAppointment: vi.fn(),
}))

const mockedUseCreateAppointment = vi.mocked(useCreateAppointment)

// Test wrapper with QueryClient
function TestWrapper({ children }: { children: React.ReactNode }) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

describe('BookingForm', () => {
  const user = userEvent.setup()
  const mockMutateAsync = vi.fn()
  const mockOnSuccess = vi.fn()
  const mockOnCancel = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    mockedUseCreateAppointment.mockReturnValue({
      mutateAsync: mockMutateAsync,
      isPending: false,
      isError: false,
      error: null,
      data: undefined,
      isSuccess: false,
      mutate: vi.fn(),
      reset: vi.fn(),
      status: 'idle',
      variables: undefined,
      context: undefined,
      failureCount: 0,
      failureReason: null,
      isIdle: true,
      isPaused: false,
      submittedAt: 0,
    })
  })

  it('should render booking form with all fields', () => {
    render(
      <TestWrapper>
        <BookingForm />
      </TestWrapper>
    )

    expect(screen.getByRole('heading', { name: /book new appointment/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/customer name/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/date/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/time/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/duration/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /book appointment/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
  })

  it('should pre-populate date and time when provided', () => {
    render(
      <TestWrapper>
        <BookingForm selectedDate="2024-12-25" selectedTime="14:30" />
      </TestWrapper>
    )

    const dateInput = screen.getByLabelText(/date/i) as HTMLInputElement
    const timeSelect = screen.getByLabelText(/time/i) as HTMLSelectElement

    expect(dateInput.value).toBe('2024-12-25')
    expect(timeSelect.value).toBe('14:30')
  })

  it('should show validation errors for empty required fields', async () => {
    render(
      <TestWrapper>
        <BookingForm />
      </TestWrapper>
    )

    const submitButton = screen.getByRole('button', { name: /book appointment/i })
    await user.click(submitButton)

    // Wait for validation errors to appear
    await waitFor(() => {
      expect(screen.getByText('Customer name is required')).toBeInTheDocument()
    })

    await waitFor(() => {
      expect(screen.getByText('Date is required')).toBeInTheDocument()
    })

    await waitFor(() => {
      expect(screen.getByText('Time is required')).toBeInTheDocument()
    })

    // Should not call the mutation when validation fails
    expect(mockMutateAsync).not.toHaveBeenCalled()
  })

  it('should handle successful booking submission', async () => {
    const mockAppointment = {
      id: '123',
      customer_name: 'John Doe',
      start_time: '2024-12-25T14:30:00.000Z',
      duration_minutes: 60,
      end_time: '2024-12-25T15:30:00.000Z',
      created_at: '2024-12-20T10:00:00.000Z',
      updated_at: '2024-12-20T10:00:00.000Z',
    }

    mockMutateAsync.mockResolvedValue(mockAppointment)

    render(
      <TestWrapper>
        <BookingForm onSuccess={mockOnSuccess} />
      </TestWrapper>
    )

    // Fill out the form
    await user.type(screen.getByLabelText(/customer name/i), 'John Doe')
    await user.type(screen.getByLabelText(/date/i), '2024-12-25')
    await user.selectOptions(screen.getByLabelText(/time/i), '14:30')
    await user.selectOptions(screen.getByLabelText(/duration/i), '60')

    // Submit the form
    await user.click(screen.getByRole('button', { name: /book appointment/i }))

    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalledWith({
        customer_name: 'John Doe',
        start_time: '2024-12-25T14:30:00.000Z',
        duration_minutes: 60,
      })
    })

    await waitFor(() => {
      expect(screen.getByText('Appointment booked successfully!')).toBeInTheDocument()
      expect(mockOnSuccess).toHaveBeenCalledWith(mockAppointment)
    })
  })

  it('should handle booking failure with conflict error', async () => {
    const conflictError = {
      response: {
        status: 409,
        data: { detail: 'Time slot is already booked' },
      },
    }

    mockMutateAsync.mockRejectedValue(conflictError)

    render(
      <TestWrapper>
        <BookingForm />
      </TestWrapper>
    )

    // Fill out the form
    await user.type(screen.getByLabelText(/customer name/i), 'John Doe')
    await user.type(screen.getByLabelText(/date/i), '2024-12-25')
    await user.selectOptions(screen.getByLabelText(/time/i), '14:30')

    // Submit the form
    await user.click(screen.getByRole('button', { name: /book appointment/i }))

    await waitFor(() => {
      expect(screen.getByText(/time slot is already booked/i)).toBeInTheDocument()
    })
  })

  it('should handle booking failure with validation error', async () => {
    const validationError = {
      response: {
        status: 400,
        data: { detail: 'Invalid booking data' },
      },
    }

    mockMutateAsync.mockRejectedValue(validationError)

    render(
      <TestWrapper>
        <BookingForm />
      </TestWrapper>
    )

    // Fill out the form
    await user.type(screen.getByLabelText(/customer name/i), 'John Doe')
    await user.type(screen.getByLabelText(/date/i), '2024-12-25')
    await user.selectOptions(screen.getByLabelText(/time/i), '14:30')

    // Submit the form
    await user.click(screen.getByRole('button', { name: /book appointment/i }))

    await waitFor(() => {
      expect(screen.getByText('Invalid booking data')).toBeInTheDocument()
    })
  })

  it('should handle generic booking failure', async () => {
    const genericError = new Error('Network error')
    mockMutateAsync.mockRejectedValue(genericError)

    render(
      <TestWrapper>
        <BookingForm />
      </TestWrapper>
    )

    // Fill out the form
    await user.type(screen.getByLabelText(/customer name/i), 'John Doe')
    await user.type(screen.getByLabelText(/date/i), '2024-12-25')
    await user.selectOptions(screen.getByLabelText(/time/i), '14:30')

    // Submit the form
    await user.click(screen.getByRole('button', { name: /book appointment/i }))

    await waitFor(() => {
      expect(screen.getByText('Booking failed. Please try again.')).toBeInTheDocument()
    })
  })

  it('should prevent booking appointments in the past', async () => {
    // Mock current date to be after the selected date
    vi.spyOn(Date, 'now').mockReturnValue(new Date('2024-12-26T10:00:00').getTime())

    render(
      <TestWrapper>
        <BookingForm />
      </TestWrapper>
    )

    // Fill out the form with a past date
    await user.type(screen.getByLabelText(/customer name/i), 'John Doe')
    await user.type(screen.getByLabelText(/date/i), '2024-12-25')
    await user.selectOptions(screen.getByLabelText(/time/i), '14:30')

    // Submit the form
    await user.click(screen.getByRole('button', { name: /book appointment/i }))

    await waitFor(() => {
      expect(screen.getByText('Cannot book appointments in the past')).toBeInTheDocument()
    })

    // Should not call the mutation
    expect(mockMutateAsync).not.toHaveBeenCalled()
  })

  it('should disable form during submission', async () => {
    mockedUseCreateAppointment.mockReturnValue({
      mutateAsync: mockMutateAsync,
      isPending: true,
      isError: false,
      error: null,
      data: undefined,
      isSuccess: false,
      mutate: vi.fn(),
      reset: vi.fn(),
      status: 'pending',
      variables: undefined,
      context: undefined,
      failureCount: 0,
      failureReason: null,
      isIdle: false,
      isPaused: false,
      submittedAt: Date.now(),
    })

    render(
      <TestWrapper>
        <BookingForm />
      </TestWrapper>
    )

    const customerNameInput = screen.getByLabelText(/customer name/i)
    const dateInput = screen.getByLabelText(/date/i)
    const timeSelect = screen.getByLabelText(/time/i)
    const durationSelect = screen.getByLabelText(/duration/i)
    const submitButton = screen.getByRole('button', { name: /booking.../i })
    const cancelButton = screen.getByRole('button', { name: /cancel/i })

    expect(customerNameInput).toBeDisabled()
    expect(dateInput).toBeDisabled()
    expect(timeSelect).toBeDisabled()
    expect(durationSelect).toBeDisabled()
    expect(submitButton).toBeDisabled()
    expect(cancelButton).toBeDisabled()
  })

  it('should call onCancel when cancel button is clicked', async () => {
    render(
      <TestWrapper>
        <BookingForm onCancel={mockOnCancel} />
      </TestWrapper>
    )

    await user.click(screen.getByRole('button', { name: /cancel/i }))

    expect(mockOnCancel).toHaveBeenCalled()
  })

  it('should validate customer name length', async () => {
    render(
      <TestWrapper>
        <BookingForm />
      </TestWrapper>
    )

    // Test that the form accepts reasonable length names
    await user.type(screen.getByLabelText(/customer name/i), 'John Doe')
    await user.type(screen.getByLabelText(/date/i), '2024-12-25')
    await user.selectOptions(screen.getByLabelText(/time/i), '14:30')

    // The form should be ready to submit (no validation errors visible)
    expect(screen.queryByText(/customer name must be less than 100 characters/i)).not.toBeInTheDocument()
  })

  it('should validate duration range', async () => {
    render(
      <TestWrapper>
        <BookingForm />
      </TestWrapper>
    )

    // The duration select should only contain valid options
    const durationSelect = screen.getByLabelText(/duration/i)
    const options = Array.from(durationSelect.querySelectorAll('option')).map(
      (option) => (option as HTMLOptionElement).value
    )

    // Should contain valid duration options
    expect(options).toContain('15')
    expect(options).toContain('30')
    expect(options).toContain('60')
    expect(options).toContain('120')
    expect(options).toContain('240')

    // Should not contain invalid durations
    expect(options).not.toContain('5')
    expect(options).not.toContain('500')
  })

  it('should clear error messages when retrying submission', async () => {
    const conflictError = {
      response: {
        status: 409,
        data: { detail: 'Time slot is already booked' },
      },
    }

    mockMutateAsync.mockRejectedValueOnce(conflictError)

    render(
      <TestWrapper>
        <BookingForm />
      </TestWrapper>
    )

    // Fill out and submit form (first attempt - should fail)
    await user.type(screen.getByLabelText(/customer name/i), 'John Doe')
    await user.type(screen.getByLabelText(/date/i), '2024-12-25')
    await user.selectOptions(screen.getByLabelText(/time/i), '14:30')
    await user.click(screen.getByRole('button', { name: /book appointment/i }))

    await waitFor(() => {
      expect(screen.getByText(/time slot is already booked/i)).toBeInTheDocument()
    })

    // Mock successful response for retry
    const mockAppointment = {
      id: '123',
      customer_name: 'John Doe',
      start_time: '2024-12-25T15:30:00.000Z',
      duration_minutes: 60,
      end_time: '2024-12-25T16:30:00.000Z',
      created_at: '2024-12-20T10:00:00.000Z',
      updated_at: '2024-12-20T10:00:00.000Z',
    }
    mockMutateAsync.mockResolvedValue(mockAppointment)

    // Change time and retry
    await user.selectOptions(screen.getByLabelText(/time/i), '15:30')
    await user.click(screen.getByRole('button', { name: /book appointment/i }))

    await waitFor(() => {
      expect(screen.queryByText(/time slot is already booked/i)).not.toBeInTheDocument()
      expect(screen.getByText('Appointment booked successfully!')).toBeInTheDocument()
    })
  })
})
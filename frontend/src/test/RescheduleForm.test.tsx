import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RescheduleForm } from '../components/RescheduleForm'
import { useUpdateAppointment } from '../hooks/useAppointments'
import { useAvailability } from '../hooks/useAvailability'
import { Appointment } from '../types/appointment'
import { TimeSlot } from '../types/availability'
import { ApiException } from '../types/api'

// Mock the hooks
vi.mock('../hooks/useAppointments', () => ({
  useUpdateAppointment: vi.fn(),
}))

vi.mock('../hooks/useAvailability', () => ({
  useAvailability: vi.fn(),
}))

const mockedUseUpdateAppointment = vi.mocked(useUpdateAppointment)
const mockedUseAvailability = vi.mocked(useAvailability)

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

describe('RescheduleForm', () => {
  const user = userEvent.setup()
  const mockMutateAsync = vi.fn()
  const mockOnClose = vi.fn()
  const mockOnSuccess = vi.fn()

  const mockAppointment: Appointment = {
    id: '123',
    customer_name: 'John Doe',
    start_time: '2024-12-25T14:30:00.000Z',
    duration_minutes: 60,
    end_time: '2024-12-25T15:30:00.000Z',
    created_at: '2024-12-20T10:00:00.000Z',
    updated_at: '2024-12-20T10:00:00.000Z',
  }

  const mockAvailability: TimeSlot[] = [
    {
      start_time: '2024-12-26T09:00:00.000Z',
      end_time: '2024-12-26T17:00:00.000Z',
      available: true,
    },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    
    mockedUseUpdateAppointment.mockReturnValue({
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

    mockedUseAvailability.mockReturnValue({
      data: mockAvailability,
      isLoading: false,
      error: null,
      isError: false,
      isSuccess: true,
      status: 'success',
      dataUpdatedAt: Date.now(),
      errorUpdatedAt: 0,
      failureCount: 0,
      failureReason: null,
      fetchStatus: 'idle',
      isInitialLoading: false,
      isLoadingError: false,
      isPaused: false,
      isPending: false,
      isPlaceholderData: false,
      isRefetchError: false,
      isRefetching: false,
      isStale: false,
      refetch: vi.fn(),
    })

    // Mock current date
    vi.spyOn(Date, 'now').mockReturnValue(new Date('2024-12-20T10:00:00.000Z').getTime())
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('should not render when isOpen is false', () => {
    render(
      <TestWrapper>
        <RescheduleForm
          appointment={mockAppointment}
          isOpen={false}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      </TestWrapper>
    )

    expect(screen.queryByText('Reschedule Appointment')).not.toBeInTheDocument()
  })

  it('should render reschedule form when isOpen is true', () => {
    render(
      <TestWrapper>
        <RescheduleForm
          appointment={mockAppointment}
          isOpen={true}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      </TestWrapper>
    )

    expect(screen.getByText('Reschedule Appointment')).toBeInTheDocument()
    expect(screen.getByText('Current Appointment')).toBeInTheDocument()
    expect(screen.getByText('John Doe')).toBeInTheDocument()
    expect(screen.getByLabelText('New Date')).toBeInTheDocument()
    expect(screen.getByLabelText('New Time')).toBeInTheDocument()
  })

  it('should pre-populate form with current appointment data', () => {
    render(
      <TestWrapper>
        <RescheduleForm
          appointment={mockAppointment}
          isOpen={true}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      </TestWrapper>
    )

    const dateInput = screen.getByLabelText('New Date') as HTMLInputElement
    const timeSelect = screen.getByLabelText('New Time') as HTMLSelectElement

    expect(dateInput.value).toBe('2024-12-25')
    expect(timeSelect.value).toBe('14:30')
  })

  it('should display available time slots when date is selected', async () => {
    render(
      <TestWrapper>
        <RescheduleForm
          appointment={mockAppointment}
          isOpen={true}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      </TestWrapper>
    )

    const dateInput = screen.getByLabelText('New Date')
    await user.clear(dateInput)
    await user.type(dateInput, '2024-12-26')

    await waitFor(() => {
      const timeSelect = screen.getByLabelText('New Time')
      const options = Array.from(timeSelect.querySelectorAll('option')).map(
        (option) => (option as HTMLOptionElement).text
      )
      
      // Should have time slots available
      expect(options.length).toBeGreaterThan(1) // Including the "Select a time" option
      expect(options).toContain('9:00 AM')
    })
  })

  it('should show loading message while fetching availability', () => {
    mockedUseAvailability.mockReturnValue({
      data: [],
      isLoading: true,
      error: null,
      isError: false,
      isSuccess: false,
      status: 'pending',
      dataUpdatedAt: 0,
      errorUpdatedAt: 0,
      failureCount: 0,
      failureReason: null,
      fetchStatus: 'fetching',
      isInitialLoading: true,
      isLoadingError: false,
      isPaused: false,
      isPending: true,
      isPlaceholderData: false,
      isRefetchError: false,
      isRefetching: false,
      isStale: false,
      refetch: vi.fn(),
    })

    render(
      <TestWrapper>
        <RescheduleForm
          appointment={mockAppointment}
          isOpen={true}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      </TestWrapper>
    )

    expect(screen.getByText('Loading available times...')).toBeInTheDocument()
  })

  it('should show no availability message when no slots are available', () => {
    mockedUseAvailability.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
      isError: false,
      isSuccess: true,
      status: 'success',
      dataUpdatedAt: Date.now(),
      errorUpdatedAt: 0,
      failureCount: 0,
      failureReason: null,
      fetchStatus: 'idle',
      isInitialLoading: false,
      isLoadingError: false,
      isPaused: false,
      isPending: false,
      isPlaceholderData: false,
      isRefetchError: false,
      isRefetching: false,
      isStale: false,
      refetch: vi.fn(),
    })

    render(
      <TestWrapper>
        <RescheduleForm
          appointment={mockAppointment}
          isOpen={true}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      </TestWrapper>
    )

    expect(screen.getByText(/No available time slots for the selected date/)).toBeInTheDocument()
  })

  it('should handle successful reschedule submission', async () => {
    const updatedAppointment = {
      ...mockAppointment,
      start_time: '2024-12-26T10:00:00.000Z',
      end_time: '2024-12-26T11:00:00.000Z',
      updated_at: '2024-12-20T12:00:00.000Z',
    }

    mockMutateAsync.mockResolvedValue(updatedAppointment)

    render(
      <TestWrapper>
        <RescheduleForm
          appointment={mockAppointment}
          isOpen={true}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      </TestWrapper>
    )

    // Change the date and time
    const dateInput = screen.getByLabelText('New Date')
    await user.clear(dateInput)
    await user.type(dateInput, '2024-12-26')

    await waitFor(() => {
      const timeSelect = screen.getByLabelText('New Time')
      expect(timeSelect.querySelectorAll('option').length).toBeGreaterThan(1)
    })

    const timeSelect = screen.getByLabelText('New Time')
    await user.selectOptions(timeSelect, '10:00')

    // Submit the form
    const submitButton = screen.getByText('Reschedule Appointment')
    await user.click(submitButton)

    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalledWith({
        id: '123',
        updateData: {
          start_time: '2024-12-26T10:00:00.000Z',
        },
      })
    })

    await waitFor(() => {
      expect(mockOnSuccess).toHaveBeenCalledWith(updatedAppointment)
      expect(mockOnClose).toHaveBeenCalled()
    })
  })

  it('should handle conflict error during reschedule', async () => {
    const conflictError = new ApiException('Time slot is already booked', 409, {})
    mockMutateAsync.mockRejectedValue(conflictError)

    render(
      <TestWrapper>
        <RescheduleForm
          appointment={mockAppointment}
          isOpen={true}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      </TestWrapper>
    )

    // Change the time
    const dateInput = screen.getByLabelText('New Date')
    await user.clear(dateInput)
    await user.type(dateInput, '2024-12-26')

    await waitFor(() => {
      const timeSelect = screen.getByLabelText('New Time')
      expect(timeSelect.querySelectorAll('option').length).toBeGreaterThan(1)
    })

    const timeSelect = screen.getByLabelText('New Time')
    await user.selectOptions(timeSelect, '10:00')

    const submitButton = screen.getByText('Reschedule Appointment')
    await user.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText('This time slot is already booked. Please select a different time.')).toBeInTheDocument()
    })

    expect(mockOnSuccess).not.toHaveBeenCalled()
    expect(mockOnClose).not.toHaveBeenCalled()
  })

  it('should handle validation error during reschedule', async () => {
    const validationError = new ApiException('Invalid reschedule request', 400, {})
    mockMutateAsync.mockRejectedValue(validationError)

    render(
      <TestWrapper>
        <RescheduleForm
          appointment={mockAppointment}
          isOpen={true}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      </TestWrapper>
    )

    // Change the time
    const dateInput = screen.getByLabelText('New Date')
    await user.clear(dateInput)
    await user.type(dateInput, '2024-12-26')

    await waitFor(() => {
      const timeSelect = screen.getByLabelText('New Time')
      expect(timeSelect.querySelectorAll('option').length).toBeGreaterThan(1)
    })

    const timeSelect = screen.getByLabelText('New Time')
    await user.selectOptions(timeSelect, '10:00')

    const submitButton = screen.getByText('Reschedule Appointment')
    await user.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText('Invalid reschedule request')).toBeInTheDocument()
    })
  })

  it('should prevent rescheduling to past dates', async () => {
    render(
      <TestWrapper>
        <RescheduleForm
          appointment={mockAppointment}
          isOpen={true}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      </TestWrapper>
    )

    // Try to reschedule to a past date
    const dateInput = screen.getByLabelText('New Date')
    await user.clear(dateInput)
    await user.type(dateInput, '2024-12-19')

    const timeSelect = screen.getByLabelText('New Time')
    await user.selectOptions(timeSelect, '10:00')

    const submitButton = screen.getByText('Reschedule Appointment')
    await user.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText('Cannot reschedule to a time in the past')).toBeInTheDocument()
    })

    expect(mockMutateAsync).not.toHaveBeenCalled()
  })

  it('should prevent rescheduling to the same time', async () => {
    render(
      <TestWrapper>
        <RescheduleForm
          appointment={mockAppointment}
          isOpen={true}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      </TestWrapper>
    )

    // Keep the same date and time
    const submitButton = screen.getByText('Reschedule Appointment')
    await user.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText('Please select a different time to reschedule')).toBeInTheDocument()
    })

    expect(mockMutateAsync).not.toHaveBeenCalled()
  })

  it('should require both date and time to be selected', async () => {
    render(
      <TestWrapper>
        <RescheduleForm
          appointment={mockAppointment}
          isOpen={true}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      </TestWrapper>
    )

    // Clear the time selection
    const timeSelect = screen.getByLabelText('New Time')
    await user.selectOptions(timeSelect, '')

    const submitButton = screen.getByText('Reschedule Appointment')
    await user.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText('Please select both date and time')).toBeInTheDocument()
    })

    expect(mockMutateAsync).not.toHaveBeenCalled()
  })

  it('should call onClose when close button is clicked', async () => {
    render(
      <TestWrapper>
        <RescheduleForm
          appointment={mockAppointment}
          isOpen={true}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      </TestWrapper>
    )

    const closeButton = screen.getByLabelText('Close modal')
    await user.click(closeButton)

    expect(mockOnClose).toHaveBeenCalledTimes(1)
  })

  it('should call onClose when cancel button is clicked', async () => {
    render(
      <TestWrapper>
        <RescheduleForm
          appointment={mockAppointment}
          isOpen={true}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      </TestWrapper>
    )

    const cancelButton = screen.getByText('Cancel')
    await user.click(cancelButton)

    expect(mockOnClose).toHaveBeenCalledTimes(1)
  })

  it('should call onClose when backdrop is clicked', async () => {
    render(
      <TestWrapper>
        <RescheduleForm
          appointment={mockAppointment}
          isOpen={true}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      </TestWrapper>
    )

    const backdrop = screen.getByRole('dialog')
    await user.click(backdrop)

    expect(mockOnClose).toHaveBeenCalledTimes(1)
  })

  it('should call onClose when Escape key is pressed', async () => {
    render(
      <TestWrapper>
        <RescheduleForm
          appointment={mockAppointment}
          isOpen={true}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      </TestWrapper>
    )

    await user.keyboard('{Escape}')

    expect(mockOnClose).toHaveBeenCalledTimes(1)
  })

  it('should disable form during submission', () => {
    mockedUseUpdateAppointment.mockReturnValue({
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
        <RescheduleForm
          appointment={mockAppointment}
          isOpen={true}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      </TestWrapper>
    )

    expect(screen.getByLabelText('New Date')).toBeDisabled()
    expect(screen.getByLabelText('New Time')).toBeDisabled()
    expect(screen.getByText('Rescheduling...')).toBeDisabled()
    expect(screen.getByText('Cancel')).toBeDisabled()
    expect(screen.getByLabelText('Close modal')).toBeDisabled()
  })

  it('should have proper accessibility attributes', () => {
    render(
      <TestWrapper>
        <RescheduleForm
          appointment={mockAppointment}
          isOpen={true}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      </TestWrapper>
    )

    const dialog = screen.getByRole('dialog')
    expect(dialog).toHaveAttribute('aria-modal', 'true')
    expect(dialog).toHaveAttribute('aria-labelledby', 'reschedule-form-title')

    const closeButton = screen.getByLabelText('Close modal')
    expect(closeButton).toBeInTheDocument()
  })

  it('should show minimum date as today', () => {
    render(
      <TestWrapper>
        <RescheduleForm
          appointment={mockAppointment}
          isOpen={true}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      </TestWrapper>
    )

    const dateInput = screen.getByLabelText('New Date') as HTMLInputElement
    expect(dateInput.min).toBe('2024-12-20') // Current date from mock
  })
})
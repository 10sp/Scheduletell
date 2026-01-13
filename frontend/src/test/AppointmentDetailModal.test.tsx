import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AppointmentDetailModal } from '../components/AppointmentDetailModal'
import { useDeleteAppointment } from '../hooks/useAppointments'
import { Appointment } from '../types/appointment'

// Mock the useDeleteAppointment hook
vi.mock('../hooks/useAppointments', () => ({
  useDeleteAppointment: vi.fn(),
}))

const mockedUseDeleteAppointment = vi.mocked(useDeleteAppointment)

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

describe('AppointmentDetailModal', () => {
  const user = userEvent.setup()
  const mockMutateAsync = vi.fn()
  const mockOnClose = vi.fn()
  const mockOnReschedule = vi.fn()

  const mockAppointment: Appointment = {
    id: '123',
    customer_name: 'John Doe',
    start_time: '2024-12-25T14:30:00.000Z',
    duration_minutes: 60,
    end_time: '2024-12-25T15:30:00.000Z',
    created_at: '2024-12-20T10:00:00.000Z',
    updated_at: '2024-12-20T10:00:00.000Z',
  }

  beforeEach(() => {
    vi.clearAllMocks()
    mockedUseDeleteAppointment.mockReturnValue({
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

  it('should not render when isOpen is false', () => {
    render(
      <TestWrapper>
        <AppointmentDetailModal
          appointment={mockAppointment}
          isOpen={false}
          onClose={mockOnClose}
          onReschedule={mockOnReschedule}
        />
      </TestWrapper>
    )

    expect(screen.queryByText('Appointment Details')).not.toBeInTheDocument()
  })

  it('should render appointment details when isOpen is true', () => {
    render(
      <TestWrapper>
        <AppointmentDetailModal
          appointment={mockAppointment}
          isOpen={true}
          onClose={mockOnClose}
          onReschedule={mockOnReschedule}
        />
      </TestWrapper>
    )

    expect(screen.getByText('Appointment Details')).toBeInTheDocument()
    expect(screen.getByText('John Doe')).toBeInTheDocument()
    expect(screen.getByText('Wednesday, December 25, 2024')).toBeInTheDocument()
    expect(screen.getByText(/8:00 PM/)).toBeInTheDocument()
    expect(screen.getByText(/9:00 PM/)).toBeInTheDocument()
    expect(screen.getByText('1 hour')).toBeInTheDocument()
  })

  it('should display created and updated dates correctly', () => {
    const appointmentWithDifferentUpdatedDate = {
      ...mockAppointment,
      updated_at: '2024-12-21T15:00:00.000Z',
    }

    render(
      <TestWrapper>
        <AppointmentDetailModal
          appointment={appointmentWithDifferentUpdatedDate}
          isOpen={true}
          onClose={mockOnClose}
          onReschedule={mockOnReschedule}
        />
      </TestWrapper>
    )

    expect(screen.getByText(/Dec 20, 2024/)).toBeInTheDocument() // Created date
    expect(screen.getByText(/Dec 21, 2024/)).toBeInTheDocument() // Updated date
  })

  it('should not show updated date when it equals created date', () => {
    render(
      <TestWrapper>
        <AppointmentDetailModal
          appointment={mockAppointment}
          isOpen={true}
          onClose={mockOnClose}
          onReschedule={mockOnReschedule}
        />
      </TestWrapper>
    )

    const updatedLabels = screen.queryAllByText('Last Updated')
    expect(updatedLabels).toHaveLength(0)
  })

  it('should call onClose when close button is clicked', async () => {
    render(
      <TestWrapper>
        <AppointmentDetailModal
          appointment={mockAppointment}
          isOpen={true}
          onClose={mockOnClose}
          onReschedule={mockOnReschedule}
        />
      </TestWrapper>
    )

    const closeButton = screen.getByLabelText('Close modal')
    await user.click(closeButton)

    expect(mockOnClose).toHaveBeenCalledTimes(1)
  })

  it('should call onClose when backdrop is clicked', async () => {
    render(
      <TestWrapper>
        <AppointmentDetailModal
          appointment={mockAppointment}
          isOpen={true}
          onClose={mockOnClose}
          onReschedule={mockOnReschedule}
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
        <AppointmentDetailModal
          appointment={mockAppointment}
          isOpen={true}
          onClose={mockOnClose}
          onReschedule={mockOnReschedule}
        />
      </TestWrapper>
    )

    await user.keyboard('{Escape}')

    expect(mockOnClose).toHaveBeenCalledTimes(1)
  })

  it('should call onReschedule when reschedule button is clicked', async () => {
    render(
      <TestWrapper>
        <AppointmentDetailModal
          appointment={mockAppointment}
          isOpen={true}
          onClose={mockOnClose}
          onReschedule={mockOnReschedule}
        />
      </TestWrapper>
    )

    const rescheduleButton = screen.getByText('Reschedule')
    await user.click(rescheduleButton)

    expect(mockOnReschedule).toHaveBeenCalledWith(mockAppointment)
    expect(mockOnReschedule).toHaveBeenCalledTimes(1)
  })

  it('should show confirmation dialog and delete appointment when confirmed', async () => {
    // Mock window.confirm to return true
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)
    mockMutateAsync.mockResolvedValue(undefined)

    render(
      <TestWrapper>
        <AppointmentDetailModal
          appointment={mockAppointment}
          isOpen={true}
          onClose={mockOnClose}
          onReschedule={mockOnReschedule}
        />
      </TestWrapper>
    )

    const deleteButton = screen.getByText('Delete')
    await user.click(deleteButton)

    expect(confirmSpy).toHaveBeenCalledWith(
      'Are you sure you want to delete this appointment? This action cannot be undone.'
    )
    expect(mockMutateAsync).toHaveBeenCalledWith('123')

    await waitFor(() => {
      expect(mockOnClose).toHaveBeenCalledTimes(1)
    })

    confirmSpy.mockRestore()
  })

  it('should not delete appointment when confirmation is cancelled', async () => {
    // Mock window.confirm to return false
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false)

    render(
      <TestWrapper>
        <AppointmentDetailModal
          appointment={mockAppointment}
          isOpen={true}
          onClose={mockOnClose}
          onReschedule={mockOnReschedule}
        />
      </TestWrapper>
    )

    const deleteButton = screen.getByText('Delete')
    await user.click(deleteButton)

    expect(confirmSpy).toHaveBeenCalled()
    expect(mockMutateAsync).not.toHaveBeenCalled()
    expect(mockOnClose).not.toHaveBeenCalled()

    confirmSpy.mockRestore()
  })

  it('should handle delete error gracefully', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    const deleteError = new Error('Delete failed')
    mockMutateAsync.mockRejectedValue(deleteError)

    render(
      <TestWrapper>
        <AppointmentDetailModal
          appointment={mockAppointment}
          isOpen={true}
          onClose={mockOnClose}
          onReschedule={mockOnReschedule}
        />
      </TestWrapper>
    )

    const deleteButton = screen.getByText('Delete')
    await user.click(deleteButton)

    await waitFor(() => {
      expect(consoleErrorSpy).toHaveBeenCalledWith('Failed to delete appointment:', deleteError)
    })

    // Should not close modal on error
    expect(mockOnClose).not.toHaveBeenCalled()

    confirmSpy.mockRestore()
    consoleErrorSpy.mockRestore()
  })

  it('should disable buttons during delete operation', () => {
    mockedUseDeleteAppointment.mockReturnValue({
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
        <AppointmentDetailModal
          appointment={mockAppointment}
          isOpen={true}
          onClose={mockOnClose}
          onReschedule={mockOnReschedule}
        />
      </TestWrapper>
    )

    expect(screen.getByText('Reschedule')).toBeDisabled()
    expect(screen.getByText('Deleting...')).toBeDisabled()
    expect(screen.getByText('Close')).toBeDisabled()
  })

  it('should format duration correctly for different values', () => {
    const appointmentWith30Min = { ...mockAppointment, duration_minutes: 30 }
    const appointmentWith90Min = { ...mockAppointment, duration_minutes: 90 }
    const appointmentWith120Min = { ...mockAppointment, duration_minutes: 120 }

    // Test 30 minutes
    const { rerender } = render(
      <TestWrapper>
        <AppointmentDetailModal
          appointment={appointmentWith30Min}
          isOpen={true}
          onClose={mockOnClose}
          onReschedule={mockOnReschedule}
        />
      </TestWrapper>
    )
    expect(screen.getByText('30 minutes')).toBeInTheDocument()

    // Test 90 minutes
    rerender(
      <TestWrapper>
        <AppointmentDetailModal
          appointment={appointmentWith90Min}
          isOpen={true}
          onClose={mockOnClose}
          onReschedule={mockOnReschedule}
        />
      </TestWrapper>
    )
    expect(screen.getByText('1 hour 30 minutes')).toBeInTheDocument()

    // Test 120 minutes
    rerender(
      <TestWrapper>
        <AppointmentDetailModal
          appointment={appointmentWith120Min}
          isOpen={true}
          onClose={mockOnClose}
          onReschedule={mockOnReschedule}
        />
      </TestWrapper>
    )
    expect(screen.getByText('2 hours')).toBeInTheDocument()
  })

  it('should have proper accessibility attributes', () => {
    render(
      <TestWrapper>
        <AppointmentDetailModal
          appointment={mockAppointment}
          isOpen={true}
          onClose={mockOnClose}
          onReschedule={mockOnReschedule}
        />
      </TestWrapper>
    )

    const dialog = screen.getByRole('dialog')
    expect(dialog).toHaveAttribute('aria-modal', 'true')
    expect(dialog).toHaveAttribute('aria-labelledby', 'appointment-detail-title')

    const closeButton = screen.getByLabelText('Close modal')
    expect(closeButton).toBeInTheDocument()
  })
})
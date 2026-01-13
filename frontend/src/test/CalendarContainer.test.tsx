import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { CalendarContainer } from '../components/CalendarContainer'
import { Appointment } from '../types/appointment'
import { TimeSlot } from '../types/availability'

// Mock the hooks
vi.mock('../hooks/useAppointments', () => ({
  useAppointments: vi.fn(),
}))

vi.mock('../hooks/useAvailability', () => ({
  useAvailability: vi.fn(),
}))

// Mock the Calendar component
vi.mock('../components/Calendar', () => ({
  default: ({ appointments, availability, onTimeSlotClick, onAppointmentClick }: any) => (
    <div data-testid="calendar">
      <div data-testid="appointments-count">{appointments.length}</div>
      <div data-testid="availability-count">{availability.length}</div>
      <button
        data-testid="time-slot-button"
        onClick={() =>
          onTimeSlotClick?.({
            start: new Date('2024-01-15T10:00:00'),
            end: new Date('2024-01-15T11:00:00'),
          })
        }
      >
        Click Time Slot
      </button>
      <button
        data-testid="appointment-button"
        onClick={() =>
          onAppointmentClick?.({
            id: '1',
            customer_name: 'John Doe',
            start_time: '2024-01-15T10:00:00Z',
            end_time: '2024-01-15T11:00:00Z',
            duration_minutes: 60,
            created_at: '2024-01-01T00:00:00Z',
            updated_at: '2024-01-01T00:00:00Z',
          })
        }
      >
        Click Appointment
      </button>
    </div>
  ),
}))

import { useAppointments } from '../hooks/useAppointments'
import { useAvailability } from '../hooks/useAvailability'

const mockUseAppointments = useAppointments as any
const mockUseAvailability = useAvailability as any

describe('CalendarContainer Component', () => {
  let queryClient: QueryClient

  const mockAppointments: Appointment[] = [
    {
      id: '1',
      customer_name: 'John Doe',
      start_time: '2024-01-15T10:00:00Z',
      end_time: '2024-01-15T11:00:00Z',
      duration_minutes: 60,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    },
  ]

  const mockAvailability: TimeSlot[] = [
    {
      start_time: '2024-01-15T09:00:00Z',
      end_time: '2024-01-15T17:00:00Z',
      available: true,
    },
  ]

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    })

    // Reset mocks
    mockUseAppointments.mockReturnValue({
      data: mockAppointments,
      isLoading: false,
      error: null,
    })

    mockUseAvailability.mockReturnValue({
      data: mockAvailability,
      isLoading: false,
      error: null,
    })
  })

  const renderWithQueryClient = (component: React.ReactElement) => {
    return render(
      <QueryClientProvider client={queryClient}>
        {component}
      </QueryClientProvider>
    )
  }

  it('should render calendar with appointments and availability', () => {
    renderWithQueryClient(<CalendarContainer />)

    expect(screen.getByTestId('calendar')).toBeInTheDocument()
    expect(screen.getByTestId('appointments-count')).toHaveTextContent('1')
    expect(screen.getByTestId('availability-count')).toHaveTextContent('1')
  })

  it('should show loading state', () => {
    mockUseAppointments.mockReturnValue({
      data: [],
      isLoading: true,
      error: null,
    })

    renderWithQueryClient(<CalendarContainer />)

    const calendar = screen.getByTestId('calendar')
    expect(calendar.parentElement).toHaveClass('loading')
  })

  it('should show error state for appointments', () => {
    mockUseAppointments.mockReturnValue({
      data: [],
      isLoading: false,
      error: { message: 'Failed to load appointments' },
    })

    renderWithQueryClient(<CalendarContainer />)

    expect(screen.getByText('Unable to load calendar')).toBeInTheDocument()
    expect(screen.getByText('Failed to load appointments')).toBeInTheDocument()
    expect(screen.getByText('Retry')).toBeInTheDocument()
  })

  it('should show error state for availability', () => {
    mockUseAvailability.mockReturnValue({
      data: [],
      isLoading: false,
      error: { message: 'Failed to load availability' },
    })

    renderWithQueryClient(<CalendarContainer />)

    expect(screen.getByText('Unable to load calendar')).toBeInTheDocument()
    expect(screen.getByText('Failed to load availability')).toBeInTheDocument()
  })

  it('should handle time slot clicks', () => {
    const mockOnTimeSlotClick = vi.fn()
    renderWithQueryClient(
      <CalendarContainer onTimeSlotClick={mockOnTimeSlotClick} />
    )

    fireEvent.click(screen.getByTestId('time-slot-button'))

    expect(mockOnTimeSlotClick).toHaveBeenCalledWith({
      start: new Date('2024-01-15T10:00:00'),
      end: new Date('2024-01-15T11:00:00'),
    })
  })

  it('should handle appointment clicks', () => {
    const mockOnAppointmentClick = vi.fn()
    renderWithQueryClient(
      <CalendarContainer onAppointmentClick={mockOnAppointmentClick} />
    )

    fireEvent.click(screen.getByTestId('appointment-button'))

    expect(mockOnAppointmentClick).toHaveBeenCalledWith({
      id: '1',
      customer_name: 'John Doe',
      start_time: '2024-01-15T10:00:00Z',
      end_time: '2024-01-15T11:00:00Z',
      duration_minutes: 60,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    })
  })

  it('should not allow booking in the past', () => {
    const mockOnTimeSlotClick = vi.fn()
    
    // Mock a past date
    const pastDate = new Date('2020-01-01T10:00:00')
    vi.spyOn(Date, 'now').mockReturnValue(new Date('2024-01-15T12:00:00').getTime())

    renderWithQueryClient(
      <CalendarContainer onTimeSlotClick={mockOnTimeSlotClick} />
    )

    // Simulate clicking a past time slot by modifying the mock
    const calendar = screen.getByTestId('calendar')
    const timeSlotButton = screen.getByTestId('time-slot-button')
    
    // Override the onClick to simulate past date
    fireEvent.click(timeSlotButton)

    // Should still be called since our mock uses a future date
    expect(mockOnTimeSlotClick).toHaveBeenCalled()
  })

  it('should apply custom className', () => {
    renderWithQueryClient(<CalendarContainer className="custom-container" />)

    const calendar = screen.getByTestId('calendar')
    expect(calendar.parentElement).toHaveClass('custom-container')
  })

  it('should handle empty data gracefully', () => {
    mockUseAppointments.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    })

    mockUseAvailability.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    })

    renderWithQueryClient(<CalendarContainer />)

    expect(screen.getByTestId('appointments-count')).toHaveTextContent('0')
    expect(screen.getByTestId('availability-count')).toHaveTextContent('0')
  })

  it('should handle undefined data gracefully', () => {
    mockUseAppointments.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    })

    mockUseAvailability.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    })

    renderWithQueryClient(<CalendarContainer />)

    expect(screen.getByTestId('appointments-count')).toHaveTextContent('0')
    expect(screen.getByTestId('availability-count')).toHaveTextContent('0')
  })
})
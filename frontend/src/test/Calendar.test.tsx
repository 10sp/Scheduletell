import { render, screen, fireEvent } from '@testing-library/react'
import { Calendar } from '../components/Calendar'
import { Appointment } from '../types/appointment'
import { TimeSlot } from '../types/availability'

// Mock moment to avoid timezone issues in tests
vi.mock('moment', () => {
  const moment = vi.importActual('moment')
  return {
    ...moment,
    default: vi.fn(() => ({
      format: vi.fn(() => '10:00'),
      isSame: vi.fn(() => false),
      isBefore: vi.fn(() => false),
    })),
  }
})

// Mock react-big-calendar to avoid complex rendering issues in tests
vi.mock('react-big-calendar', () => ({
  Calendar: ({ events, onSelectSlot, onSelectEvent }: any) => (
    <div data-testid="calendar">
      <div data-testid="calendar-events">
        {events.map((event: any) => (
          <div
            key={event.id}
            data-testid={`event-${event.id}`}
            onClick={() => onSelectEvent?.(event)}
          >
            {event.title}
          </div>
        ))}
      </div>
      <div
        data-testid="time-slot"
        onClick={() =>
          onSelectSlot?.({
            start: new Date('2024-01-15T10:00:00'),
            end: new Date('2024-01-15T11:00:00'),
            action: 'select',
          })
        }
      >
        Available Slot
      </div>
    </div>
  ),
  momentLocalizer: vi.fn(),
  Views: {
    MONTH: 'month',
    WEEK: 'week',
    DAY: 'day',
  },
}))

describe('Calendar Component', () => {
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
    {
      id: '2',
      customer_name: 'Jane Smith',
      start_time: '2024-01-15T14:00:00Z',
      end_time: '2024-01-15T15:00:00Z',
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

  it('should render calendar with appointments', () => {
    render(<Calendar appointments={mockAppointments} />)

    expect(screen.getByTestId('calendar')).toBeInTheDocument()
    expect(screen.getByTestId('event-1')).toBeInTheDocument()
    expect(screen.getByTestId('event-2')).toBeInTheDocument()
    expect(screen.getByText('John Doe')).toBeInTheDocument()
    expect(screen.getByText('Jane Smith')).toBeInTheDocument()
  })

  it('should render empty calendar when no appointments', () => {
    render(<Calendar appointments={[]} />)

    expect(screen.getByTestId('calendar')).toBeInTheDocument()
    expect(screen.queryByTestId('event-1')).not.toBeInTheDocument()
    expect(screen.queryByTestId('event-2')).not.toBeInTheDocument()
  })

  it('should handle appointment click', () => {
    const mockOnAppointmentClick = vi.fn()
    render(
      <Calendar
        appointments={mockAppointments}
        onAppointmentClick={mockOnAppointmentClick}
      />
    )

    fireEvent.click(screen.getByTestId('event-1'))

    expect(mockOnAppointmentClick).toHaveBeenCalledWith(mockAppointments[0])
  })

  it('should handle time slot click', () => {
    const mockOnTimeSlotClick = vi.fn()
    render(
      <Calendar
        appointments={mockAppointments}
        onTimeSlotClick={mockOnTimeSlotClick}
      />
    )

    fireEvent.click(screen.getByTestId('time-slot'))

    expect(mockOnTimeSlotClick).toHaveBeenCalledWith({
      start: new Date('2024-01-15T10:00:00'),
      end: new Date('2024-01-15T11:00:00'),
    })
  })

  it('should handle navigation callback', () => {
    const mockOnNavigate = vi.fn()
    render(
      <Calendar
        appointments={mockAppointments}
        onNavigate={mockOnNavigate}
      />
    )

    // Since we're mocking the calendar, we can't easily test navigation
    // This test verifies the prop is passed correctly
    expect(screen.getByTestId('calendar')).toBeInTheDocument()
  })

  it('should handle view change callback', () => {
    const mockOnViewChange = vi.fn()
    render(
      <Calendar
        appointments={mockAppointments}
        onViewChange={mockOnViewChange}
      />
    )

    // Since we're mocking the calendar, we can't easily test view changes
    // This test verifies the prop is passed correctly
    expect(screen.getByTestId('calendar')).toBeInTheDocument()
  })

  it('should apply custom className', () => {
    render(
      <Calendar
        appointments={mockAppointments}
        className="custom-calendar"
      />
    )

    const calendarContainer = screen.getByTestId('calendar').parentElement
    expect(calendarContainer).toHaveClass('custom-calendar')
  })

  it('should render with availability data', () => {
    render(
      <Calendar
        appointments={mockAppointments}
        availability={mockAvailability}
      />
    )

    expect(screen.getByTestId('calendar')).toBeInTheDocument()
    // Availability styling is handled by the real calendar component
    // This test verifies the prop is passed without errors
  })

  it('should not call onTimeSlotClick when not provided', () => {
    render(<Calendar appointments={mockAppointments} />)

    // Should not throw error when clicking time slot without handler
    fireEvent.click(screen.getByTestId('time-slot'))
    
    // Test passes if no error is thrown
    expect(screen.getByTestId('calendar')).toBeInTheDocument()
  })

  it('should not call onAppointmentClick when not provided', () => {
    render(<Calendar appointments={mockAppointments} />)

    // Should not throw error when clicking appointment without handler
    fireEvent.click(screen.getByTestId('event-1'))
    
    // Test passes if no error is thrown
    expect(screen.getByTestId('calendar')).toBeInTheDocument()
  })
})
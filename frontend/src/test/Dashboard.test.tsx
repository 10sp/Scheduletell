import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Dashboard } from '../components/Dashboard'
import { useAppointments } from '../hooks/useAppointments'
import { Appointment } from '../types/appointment'

// Mock the useAppointments hook
vi.mock('../hooks/useAppointments', () => ({
  useAppointments: vi.fn(),
}))

const mockedUseAppointments = vi.mocked(useAppointments)

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

describe('Dashboard', () => {
  const user = userEvent.setup()
  const mockOnAppointmentClick = vi.fn()
  const mockOnNewAppointment = vi.fn()

  // Mock current date to ensure consistent testing
  const mockCurrentDate = new Date('2024-12-20T10:00:00.000Z')

  beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(Date, 'now').mockReturnValue(mockCurrentDate.getTime())
    vi.spyOn(global, 'Date').mockImplementation((...args: any[]) => {
      if (args.length === 0) {
        return mockCurrentDate
      }
      return new (vi.requireActual('util').types.isDate(args[0]) ? Date : global.Date)(...args)
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  const mockAppointments: Appointment[] = [
    {
      id: '1',
      customer_name: 'John Doe',
      start_time: '2024-12-21T14:30:00.000Z',
      duration_minutes: 60,
      end_time: '2024-12-21T15:30:00.000Z',
      created_at: '2024-12-20T10:00:00.000Z',
      updated_at: '2024-12-20T10:00:00.000Z',
    },
    {
      id: '2',
      customer_name: 'Jane Smith',
      start_time: '2024-12-22T09:00:00.000Z',
      duration_minutes: 30,
      end_time: '2024-12-22T09:30:00.000Z',
      created_at: '2024-12-20T10:00:00.000Z',
      updated_at: '2024-12-20T10:00:00.000Z',
    },
    {
      id: '3',
      customer_name: 'Bob Johnson',
      start_time: '2024-12-19T16:00:00.000Z', // Past appointment
      duration_minutes: 45,
      end_time: '2024-12-19T16:45:00.000Z',
      created_at: '2024-12-19T10:00:00.000Z',
      updated_at: '2024-12-19T10:00:00.000Z',
    },
  ]

  it('renders dashboard header with title and new appointment button', () => {
    mockedUseAppointments.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    })

    render(
      <TestWrapper>
        <Dashboard onNewAppointment={mockOnNewAppointment} />
      </TestWrapper>
    )

    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('New Appointment')).toBeInTheDocument()
  })

  it('displays loading state while fetching appointments', () => {
    mockedUseAppointments.mockReturnValue({
      data: [],
      isLoading: true,
      error: null,
    })

    render(
      <TestWrapper>
        <Dashboard />
      </TestWrapper>
    )

    expect(screen.getByText('Loading appointments...')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'New Appointment' })).toBeDisabled()
  })

  it('displays error state when appointments fail to load', () => {
    const errorMessage = 'Failed to fetch appointments'
    mockedUseAppointments.mockReturnValue({
      data: [],
      isLoading: false,
      error: new Error(errorMessage),
    })

    render(
      <TestWrapper>
        <Dashboard />
      </TestWrapper>
    )

    expect(screen.getByText(`Error loading appointments: ${errorMessage}`)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'New Appointment' })).not.toBeDisabled()
  })

  it('displays empty state when no upcoming appointments exist', () => {
    mockedUseAppointments.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    })

    render(
      <TestWrapper>
        <Dashboard />
      </TestWrapper>
    )

    expect(screen.getByText('No upcoming appointments scheduled.')).toBeInTheDocument()
    expect(screen.getByText('Click "New Appointment" to schedule your first appointment.')).toBeInTheDocument()
  })

  it('displays upcoming appointments list with correct information', () => {
    mockedUseAppointments.mockReturnValue({
      data: mockAppointments,
      isLoading: false,
      error: null,
    })

    render(
      <TestWrapper>
        <Dashboard />
      </TestWrapper>
    )

    // Should show upcoming appointments section
    expect(screen.getByText('Upcoming Appointments')).toBeInTheDocument()

    // Should show John Doe's appointment (future)
    expect(screen.getByText('John Doe')).toBeInTheDocument()
    expect(screen.getByText('Duration: 1h')).toBeInTheDocument()

    // Should show Jane Smith's appointment (future)
    expect(screen.getByText('Jane Smith')).toBeInTheDocument()
    expect(screen.getByText('Duration: 30m')).toBeInTheDocument()

    // Should NOT show Bob Johnson's appointment (past)
    expect(screen.queryByText('Bob Johnson')).not.toBeInTheDocument()
  })

  it('sorts appointments chronologically by start time', () => {
    const unsortedAppointments = [
      {
        id: '2',
        customer_name: 'Jane Smith',
        start_time: '2024-12-22T09:00:00.000Z', // Later
        duration_minutes: 30,
        end_time: '2024-12-22T09:30:00.000Z',
        created_at: '2024-12-20T10:00:00.000Z',
        updated_at: '2024-12-20T10:00:00.000Z',
      },
      {
        id: '1',
        customer_name: 'John Doe',
        start_time: '2024-12-21T14:30:00.000Z', // Earlier
        duration_minutes: 60,
        end_time: '2024-12-21T15:30:00.000Z',
        created_at: '2024-12-20T10:00:00.000Z',
        updated_at: '2024-12-20T10:00:00.000Z',
      },
    ]

    mockedUseAppointments.mockReturnValue({
      data: unsortedAppointments,
      isLoading: false,
      error: null,
    })

    render(
      <TestWrapper>
        <Dashboard />
      </TestWrapper>
    )

    const appointmentItems = screen.getAllByRole('button')
    const appointmentButtons = appointmentItems.filter(button => 
      button.textContent?.includes('John Doe') || button.textContent?.includes('Jane Smith')
    )

    // John Doe should appear first (earlier date)
    expect(appointmentButtons[0]).toHaveTextContent('John Doe')
    expect(appointmentButtons[1]).toHaveTextContent('Jane Smith')
  })

  it('calls onAppointmentClick when appointment is clicked', async () => {
    mockedUseAppointments.mockReturnValue({
      data: mockAppointments,
      isLoading: false,
      error: null,
    })

    render(
      <TestWrapper>
        <Dashboard onAppointmentClick={mockOnAppointmentClick} />
      </TestWrapper>
    )

    const johnDoeAppointment = screen.getByText('John Doe').closest('[role="button"]')
    expect(johnDoeAppointment).toBeInTheDocument()

    await user.click(johnDoeAppointment!)

    expect(mockOnAppointmentClick).toHaveBeenCalledWith('1')
    expect(mockOnAppointmentClick).toHaveBeenCalledTimes(1)
  })

  it('calls onAppointmentClick when appointment is activated with keyboard', async () => {
    mockedUseAppointments.mockReturnValue({
      data: mockAppointments,
      isLoading: false,
      error: null,
    })

    render(
      <TestWrapper>
        <Dashboard onAppointmentClick={mockOnAppointmentClick} />
      </TestWrapper>
    )

    const johnDoeAppointment = screen.getByText('John Doe').closest('[role="button"]')
    expect(johnDoeAppointment).toBeInTheDocument()

    johnDoeAppointment!.focus()
    await user.keyboard('{Enter}')

    expect(mockOnAppointmentClick).toHaveBeenCalledWith('1')
    expect(mockOnAppointmentClick).toHaveBeenCalledTimes(1)
  })

  it('calls onNewAppointment when new appointment button is clicked', async () => {
    mockedUseAppointments.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    })

    render(
      <TestWrapper>
        <Dashboard onNewAppointment={mockOnNewAppointment} />
      </TestWrapper>
    )

    const newAppointmentButton = screen.getByRole('button', { name: 'New Appointment' })
    await user.click(newAppointmentButton)

    expect(mockOnNewAppointment).toHaveBeenCalledTimes(1)
  })

  it('handles appointments with different duration formats correctly', () => {
    const appointmentsWithVariousDurations = [
      {
        id: '1',
        customer_name: 'Short Meeting',
        start_time: '2024-12-21T14:30:00.000Z',
        duration_minutes: 15,
        end_time: '2024-12-21T14:45:00.000Z',
        created_at: '2024-12-20T10:00:00.000Z',
        updated_at: '2024-12-20T10:00:00.000Z',
      },
      {
        id: '2',
        customer_name: 'Long Session',
        start_time: '2024-12-21T15:00:00.000Z',
        duration_minutes: 90,
        end_time: '2024-12-21T16:30:00.000Z',
        created_at: '2024-12-20T10:00:00.000Z',
        updated_at: '2024-12-20T10:00:00.000Z',
      },
      {
        id: '3',
        customer_name: 'Exact Hour',
        start_time: '2024-12-21T16:00:00.000Z',
        duration_minutes: 120,
        end_time: '2024-12-21T18:00:00.000Z',
        created_at: '2024-12-20T10:00:00.000Z',
        updated_at: '2024-12-20T10:00:00.000Z',
      },
    ]

    mockedUseAppointments.mockReturnValue({
      data: appointmentsWithVariousDurations,
      isLoading: false,
      error: null,
    })

    render(
      <TestWrapper>
        <Dashboard />
      </TestWrapper>
    )

    expect(screen.getByText('Duration: 15m')).toBeInTheDocument()
    expect(screen.getByText('Duration: 1h 30m')).toBeInTheDocument()
    expect(screen.getByText('Duration: 2h')).toBeInTheDocument()
  })

  it('does not call click handlers when they are not provided', async () => {
    mockedUseAppointments.mockReturnValue({
      data: mockAppointments,
      isLoading: false,
      error: null,
    })

    render(
      <TestWrapper>
        <Dashboard />
      </TestWrapper>
    )

    const johnDoeAppointment = screen.getByText('John Doe').closest('[role="button"]')
    const newAppointmentButton = screen.getByRole('button', { name: 'New Appointment' })

    // Should not throw errors when clicking without handlers
    await user.click(johnDoeAppointment!)
    await user.click(newAppointmentButton)

    // No assertions needed - test passes if no errors are thrown
  })
})
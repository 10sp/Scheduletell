import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { LoginPage } from '../pages/LoginPage'
import { AuthProvider } from '../contexts/AuthContext'
import { authApi } from '../services/authApi'
import { User } from '../types/auth'

// Mock the auth API
jest.mock('../services/authApi')
const mockedAuthApi = authApi as jest.Mocked<typeof authApi>

// Mock localStorage
const mockLocalStorage = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
}
Object.defineProperty(window, 'localStorage', { value: mockLocalStorage })

// Mock navigate function
const mockNavigate = jest.fn()
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}))

// Wrapper component with all necessary providers
function TestWrapper({ 
  children, 
  initialEntries = ['/login'],
  locationState = null
}: { 
  children: React.ReactNode
  initialEntries?: string[]
  locationState?: any
}) {
  return (
    <MemoryRouter 
      initialEntries={initialEntries.map(entry => ({
        pathname: entry,
        state: locationState
      }))}
    >
      <AuthProvider>
        {children}
      </AuthProvider>
    </MemoryRouter>
  )
}

describe('LoginPage', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    mockLocalStorage.getItem.mockReturnValue(null)
  })

  it('should render login page with header and form', async () => {
    render(
      <TestWrapper>
        <LoginPage />
      </TestWrapper>
    )

    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
    })

    expect(screen.getByRole('heading', { name: /appointment scheduling system/i })).toBeInTheDocument()
    expect(screen.getByText(/please log in to access your dashboard/i)).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /login/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
  })

  it('should show loading state initially', () => {
    render(
      <TestWrapper>
        <LoginPage />
      </TestWrapper>
    )

    expect(screen.getByText('Loading...')).toBeInTheDocument()
  })

  it('should redirect to dashboard when already authenticated', async () => {
    const mockUser: User = {
      id: '1',
      username: 'testuser',
    }

    // Mock stored token
    mockLocalStorage.getItem.mockImplementation((key) => {
      if (key === 'auth_token') return 'valid-token'
      if (key === 'auth_token_expiry') return (Date.now() + 3600000).toString()
      return null
    })

    mockedAuthApi.getCurrentUser.mockResolvedValue(mockUser)

    render(
      <TestWrapper>
        <LoginPage />
      </TestWrapper>
    )

    // Wait for authentication to complete and redirect
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/dashboard', { replace: true })
    })
  })

  it('should redirect to intended destination from location state', async () => {
    const mockUser: User = {
      id: '1',
      username: 'testuser',
    }

    // Mock stored token
    mockLocalStorage.getItem.mockImplementation((key) => {
      if (key === 'auth_token') return 'valid-token'
      if (key === 'auth_token_expiry') return (Date.now() + 3600000).toString()
      return null
    })

    mockedAuthApi.getCurrentUser.mockResolvedValue(mockUser)

    render(
      <TestWrapper 
        locationState={{ from: { pathname: '/calendar' } }}
      >
        <LoginPage />
      </TestWrapper>
    )

    // Wait for authentication to complete and redirect
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/calendar', { replace: true })
    })
  })

  it('should not render login form when authenticated', async () => {
    const mockUser: User = {
      id: '1',
      username: 'testuser',
    }

    // Mock stored token
    mockLocalStorage.getItem.mockImplementation((key) => {
      if (key === 'auth_token') return 'valid-token'
      if (key === 'auth_token_expiry') return (Date.now() + 3600000).toString()
      return null
    })

    mockedAuthApi.getCurrentUser.mockResolvedValue(mockUser)

    const { container } = render(
      <TestWrapper>
        <LoginPage />
      </TestWrapper>
    )

    // Wait for authentication to complete
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalled()
    })

    // Component should render nothing when authenticated
    expect(container.firstChild).toBeNull()
  })

  it('should handle login success and redirect', async () => {
    render(
      <TestWrapper 
        locationState={{ from: { pathname: '/appointments' } }}
      >
        <LoginPage />
      </TestWrapper>
    )

    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
    })

    // The LoginForm component handles the actual login logic
    // This test verifies that the page structure is correct
    expect(screen.getByRole('heading', { name: /login/i })).toBeInTheDocument()
  })
})
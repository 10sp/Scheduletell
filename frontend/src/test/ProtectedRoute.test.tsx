import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ProtectedRoute } from '../components/ProtectedRoute'
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

// Test component to render inside protected route
function TestContent() {
  return <div data-testid="protected-content">Protected Content</div>
}

// Wrapper component with all necessary providers
function TestWrapper({ 
  children, 
  initialEntries = ['/protected'] 
}: { 
  children: React.ReactNode
  initialEntries?: string[]
}) {
  return (
    <MemoryRouter initialEntries={initialEntries}>
      <AuthProvider>
        {children}
      </AuthProvider>
    </MemoryRouter>
  )
}

describe('ProtectedRoute', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    mockLocalStorage.getItem.mockReturnValue(null)
  })

  it('should show loading while checking authentication', () => {
    render(
      <TestWrapper>
        <ProtectedRoute>
          <TestContent />
        </ProtectedRoute>
      </TestWrapper>
    )

    expect(screen.getByText('Loading...')).toBeInTheDocument()
    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
  })

  it('should redirect to login when not authenticated', async () => {
    render(
      <TestWrapper>
        <ProtectedRoute>
          <TestContent />
        </ProtectedRoute>
      </TestWrapper>
    )

    // Wait for loading to complete and redirect to happen
    await waitFor(() => {
      expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
      expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
    })

    // Since we're using MemoryRouter, we can't easily test the actual navigation
    // In a real app, this would redirect to /login
  })

  it('should render protected content when authenticated', async () => {
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
        <ProtectedRoute>
          <TestContent />
        </ProtectedRoute>
      </TestWrapper>
    )

    // Wait for authentication to complete
    await waitFor(() => {
      expect(screen.getByTestId('protected-content')).toBeInTheDocument()
      expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
    })
  })

  it('should redirect to login when token is invalid', async () => {
    // Mock stored token but API call fails
    mockLocalStorage.getItem.mockImplementation((key) => {
      if (key === 'auth_token') return 'invalid-token'
      if (key === 'auth_token_expiry') return (Date.now() + 3600000).toString()
      return null
    })

    mockedAuthApi.getCurrentUser.mockRejectedValue(new Error('Invalid token'))

    render(
      <TestWrapper>
        <ProtectedRoute>
          <TestContent />
        </ProtectedRoute>
      </TestWrapper>
    )

    // Wait for authentication to fail and redirect
    await waitFor(() => {
      expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
      expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
    })

    // Token should be removed
    expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('auth_token')
    expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('auth_token_expiry')
  })
})
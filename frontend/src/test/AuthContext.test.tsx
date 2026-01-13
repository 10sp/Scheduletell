import { render, screen, waitFor, act } from '@testing-library/react'
import { vi } from 'vitest'
import { AuthProvider, useAuth } from '../contexts/AuthContext'
import { authApi } from '../services/authApi'
import { User, AuthToken } from '../types/auth'

// Mock the auth API
vi.mock('../services/authApi')
const mockedAuthApi = vi.mocked(authApi)

// Test component to access auth context
function TestComponent() {
  const { user, isAuthenticated, isLoading, login, logout } = useAuth()
  
  return (
    <div>
      <div data-testid="loading">{isLoading ? 'loading' : 'not-loading'}</div>
      <div data-testid="authenticated">{isAuthenticated ? 'authenticated' : 'not-authenticated'}</div>
      <div data-testid="user">{user ? user.username : 'no-user'}</div>
      <button onClick={() => login({ username: 'test', password: 'test' })}>
        Login
      </button>
      <button onClick={logout}>Logout</button>
    </div>
  )
}

// Mock localStorage
const mockLocalStorage = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
}
Object.defineProperty(window, 'localStorage', { value: mockLocalStorage })

describe('AuthContext', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    mockLocalStorage.getItem.mockReturnValue(null)
  })

  it('should initialize with loading state', () => {
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    expect(screen.getByTestId('loading')).toHaveTextContent('loading')
    expect(screen.getByTestId('authenticated')).toHaveTextContent('not-authenticated')
    expect(screen.getByTestId('user')).toHaveTextContent('no-user')
  })

  it('should handle successful login', async () => {
    const mockAuthToken: AuthToken = {
      access_token: 'test-token',
      token_type: 'bearer',
      expires_in: 3600,
    }
    const mockUser: User = {
      id: '1',
      username: 'testuser',
    }

    mockedAuthApi.login.mockResolvedValue(mockAuthToken)
    mockedAuthApi.getCurrentUser.mockResolvedValue(mockUser)

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    // Wait for initial loading to complete
    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('not-loading')
    })

    // Click login button
    act(() => {
      screen.getByText('Login').click()
    })

    // Wait for login to complete
    await waitFor(() => {
      expect(screen.getByTestId('authenticated')).toHaveTextContent('authenticated')
      expect(screen.getByTestId('user')).toHaveTextContent('testuser')
    })

    // Verify API calls
    expect(mockedAuthApi.login).toHaveBeenCalledWith({
      username: 'test',
      password: 'test',
    })
    expect(mockedAuthApi.getCurrentUser).toHaveBeenCalledWith('test-token')

    // Verify token storage
    expect(mockLocalStorage.setItem).toHaveBeenCalledWith('auth_token', 'test-token')
    expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
      'auth_token_expiry',
      expect.any(String)
    )
  })

  it('should handle login failure', async () => {
    const loginError = new Error('Invalid credentials')
    mockedAuthApi.login.mockRejectedValue(loginError)

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    // Wait for initial loading to complete
    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('not-loading')
    })

    // Click login button and expect error
    await act(async () => {
      try {
        screen.getByText('Login').click()
      } catch (error) {
        // Expected to throw
      }
    })

    await waitFor(() => {
      expect(screen.getByTestId('authenticated')).toHaveTextContent('not-authenticated')
      expect(screen.getByTestId('user')).toHaveTextContent('no-user')
    })
  })

  it('should handle logout', async () => {
    const mockAuthToken: AuthToken = {
      access_token: 'test-token',
      token_type: 'bearer',
      expires_in: 3600,
    }
    const mockUser: User = {
      id: '1',
      username: 'testuser',
    }

    mockedAuthApi.login.mockResolvedValue(mockAuthToken)
    mockedAuthApi.getCurrentUser.mockResolvedValue(mockUser)

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    // Login first
    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('not-loading')
    })

    act(() => {
      screen.getByText('Login').click()
    })

    await waitFor(() => {
      expect(screen.getByTestId('authenticated')).toHaveTextContent('authenticated')
    })

    // Now logout
    act(() => {
      screen.getByText('Logout').click()
    })

    await waitFor(() => {
      expect(screen.getByTestId('authenticated')).toHaveTextContent('not-authenticated')
      expect(screen.getByTestId('user')).toHaveTextContent('no-user')
    })

    // Verify token removal
    expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('auth_token')
    expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('auth_token_expiry')
  })

  it('should restore authentication from stored token', async () => {
    const mockUser: User = {
      id: '1',
      username: 'testuser',
    }

    // Mock stored token
    mockLocalStorage.getItem.mockImplementation((key) => {
      if (key === 'auth_token') return 'stored-token'
      if (key === 'auth_token_expiry') return (Date.now() + 3600000).toString()
      return null
    })

    mockedAuthApi.getCurrentUser.mockResolvedValue(mockUser)

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    // Should automatically authenticate with stored token
    await waitFor(() => {
      expect(screen.getByTestId('authenticated')).toHaveTextContent('authenticated')
      expect(screen.getByTestId('user')).toHaveTextContent('testuser')
      expect(screen.getByTestId('loading')).toHaveTextContent('not-loading')
    })

    expect(mockedAuthApi.getCurrentUser).toHaveBeenCalledWith('stored-token')
  })

  it('should handle expired stored token', async () => {
    // Mock expired token
    mockLocalStorage.getItem.mockImplementation((key) => {
      if (key === 'auth_token') return 'expired-token'
      if (key === 'auth_token_expiry') return (Date.now() - 1000).toString() // Expired
      return null
    })

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    // Should not authenticate with expired token
    await waitFor(() => {
      expect(screen.getByTestId('authenticated')).toHaveTextContent('not-authenticated')
      expect(screen.getByTestId('loading')).toHaveTextContent('not-loading')
    })

    // Should remove expired token
    expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('auth_token')
    expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('auth_token_expiry')
  })

  it('should throw error when useAuth is used outside provider', () => {
    // Suppress console.error for this test
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {})

    expect(() => {
      render(<TestComponent />)
    }).toThrow('useAuth must be used within an AuthProvider')

    consoleSpy.mockRestore()
  })
})
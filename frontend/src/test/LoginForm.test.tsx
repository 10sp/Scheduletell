import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { LoginForm } from '../components/LoginForm'
import { AuthProvider } from '../contexts/AuthContext'
import { authApi } from '../services/authApi'
import { AuthToken, User } from '../types/auth'

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

// Wrapper component with AuthProvider
function TestWrapper({ children }: { children: React.ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>
}

describe('LoginForm', () => {
  const user = userEvent.setup()

  beforeEach(() => {
    jest.clearAllMocks()
    mockLocalStorage.getItem.mockReturnValue(null)
  })

  it('should render login form with all fields', () => {
    render(
      <TestWrapper>
        <LoginForm />
      </TestWrapper>
    )

    expect(screen.getByRole('heading', { name: /login/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /login/i })).toBeInTheDocument()
  })

  it('should show validation errors for empty fields', async () => {
    render(
      <TestWrapper>
        <LoginForm />
      </TestWrapper>
    )

    const submitButton = screen.getByRole('button', { name: /login/i })
    
    // Try to submit without filling fields
    await user.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText('Username is required')).toBeInTheDocument()
      expect(screen.getByText('Password is required')).toBeInTheDocument()
    })
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
    const onSuccess = jest.fn()

    mockedAuthApi.login.mockResolvedValue(mockAuthToken)
    mockedAuthApi.getCurrentUser.mockResolvedValue(mockUser)

    render(
      <TestWrapper>
        <LoginForm onSuccess={onSuccess} />
      </TestWrapper>
    )

    // Fill in the form
    await user.type(screen.getByLabelText(/username/i), 'testuser')
    await user.type(screen.getByLabelText(/password/i), 'testpass')

    // Submit the form
    await user.click(screen.getByRole('button', { name: /login/i }))

    // Wait for login to complete
    await waitFor(() => {
      expect(mockedAuthApi.login).toHaveBeenCalledWith({
        username: 'testuser',
        password: 'testpass',
      })
    })

    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalled()
    })
  })

  it('should handle login failure with 401 error', async () => {
    const loginError = {
      response: {
        status: 401,
        data: { detail: 'Invalid credentials' },
      },
    }
    mockedAuthApi.login.mockRejectedValue(loginError)

    render(
      <TestWrapper>
        <LoginForm />
      </TestWrapper>
    )

    // Fill in the form
    await user.type(screen.getByLabelText(/username/i), 'wronguser')
    await user.type(screen.getByLabelText(/password/i), 'wrongpass')

    // Submit the form
    await user.click(screen.getByRole('button', { name: /login/i }))

    // Wait for error to appear
    await waitFor(() => {
      expect(screen.getByText('Invalid username or password')).toBeInTheDocument()
    })
  })

  it('should handle login failure with API error message', async () => {
    const loginError = {
      response: {
        status: 400,
        data: { detail: 'Account is locked' },
      },
    }
    mockedAuthApi.login.mockRejectedValue(loginError)

    render(
      <TestWrapper>
        <LoginForm />
      </TestWrapper>
    )

    // Fill in the form
    await user.type(screen.getByLabelText(/username/i), 'lockeduser')
    await user.type(screen.getByLabelText(/password/i), 'password')

    // Submit the form
    await user.click(screen.getByRole('button', { name: /login/i }))

    // Wait for error to appear
    await waitFor(() => {
      expect(screen.getByText('Account is locked')).toBeInTheDocument()
    })
  })

  it('should handle generic login failure', async () => {
    const loginError = new Error('Network error')
    mockedAuthApi.login.mockRejectedValue(loginError)

    render(
      <TestWrapper>
        <LoginForm />
      </TestWrapper>
    )

    // Fill in the form
    await user.type(screen.getByLabelText(/username/i), 'testuser')
    await user.type(screen.getByLabelText(/password/i), 'testpass')

    // Submit the form
    await user.click(screen.getByRole('button', { name: /login/i }))

    // Wait for error to appear
    await waitFor(() => {
      expect(screen.getByText('Login failed. Please try again.')).toBeInTheDocument()
    })
  })

  it('should disable form during login', async () => {
    // Mock a slow login response
    mockedAuthApi.login.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 1000)))

    render(
      <TestWrapper>
        <LoginForm />
      </TestWrapper>
    )

    const usernameInput = screen.getByLabelText(/username/i)
    const passwordInput = screen.getByLabelText(/password/i)
    const submitButton = screen.getByRole('button', { name: /login/i })

    // Fill in the form
    await user.type(usernameInput, 'testuser')
    await user.type(passwordInput, 'testpass')

    // Submit the form
    await user.click(submitButton)

    // Check that form is disabled during loading
    await waitFor(() => {
      expect(usernameInput).toBeDisabled()
      expect(passwordInput).toBeDisabled()
      expect(submitButton).toBeDisabled()
      expect(screen.getByText('Logging in...')).toBeInTheDocument()
    })
  })

  it('should clear error when retrying login', async () => {
    const loginError = {
      response: {
        status: 401,
        data: { detail: 'Invalid credentials' },
      },
    }
    
    // First call fails, second succeeds
    mockedAuthApi.login
      .mockRejectedValueOnce(loginError)
      .mockResolvedValueOnce({
        access_token: 'test-token',
        token_type: 'bearer',
        expires_in: 3600,
      })
    
    mockedAuthApi.getCurrentUser.mockResolvedValue({
      id: '1',
      username: 'testuser',
    })

    render(
      <TestWrapper>
        <LoginForm />
      </TestWrapper>
    )

    // Fill in the form and submit (first attempt - fails)
    await user.type(screen.getByLabelText(/username/i), 'testuser')
    await user.type(screen.getByLabelText(/password/i), 'wrongpass')
    await user.click(screen.getByRole('button', { name: /login/i }))

    // Wait for error to appear
    await waitFor(() => {
      expect(screen.getByText('Invalid username or password')).toBeInTheDocument()
    })

    // Clear password and enter correct one
    await user.clear(screen.getByLabelText(/password/i))
    await user.type(screen.getByLabelText(/password/i), 'correctpass')

    // Submit again (second attempt - succeeds)
    await user.click(screen.getByRole('button', { name: /login/i }))

    // Error should be cleared
    await waitFor(() => {
      expect(screen.queryByText('Invalid username or password')).not.toBeInTheDocument()
    })
  })
})
import { createContext, useContext, useReducer, useEffect, ReactNode } from 'react'
import { AuthState, AuthContextType, LoginRequest, User, AuthToken } from '../types/auth'
import { authApi } from '../services/authApi'

// Auth reducer actions
type AuthAction =
  | { type: 'LOGIN_START' }
  | { type: 'LOGIN_SUCCESS'; payload: { user: User; token: string } }
  | { type: 'LOGIN_FAILURE' }
  | { type: 'LOGOUT' }
  | { type: 'REFRESH_START' }
  | { type: 'REFRESH_SUCCESS'; payload: { user: User; token: string } }
  | { type: 'REFRESH_FAILURE' }
  | { type: 'SET_LOADING'; payload: boolean }

// Initial state
const initialState: AuthState = {
  user: null,
  token: null,
  isAuthenticated: false,
  isLoading: true,
}

// Auth reducer
function authReducer(state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {
    case 'LOGIN_START':
    case 'REFRESH_START':
      return {
        ...state,
        isLoading: true,
      }
    case 'LOGIN_SUCCESS':
    case 'REFRESH_SUCCESS':
      return {
        ...state,
        user: action.payload.user,
        token: action.payload.token,
        isAuthenticated: true,
        isLoading: false,
      }
    case 'LOGIN_FAILURE':
    case 'REFRESH_FAILURE':
      return {
        ...state,
        user: null,
        token: null,
        isAuthenticated: false,
        isLoading: false,
      }
    case 'LOGOUT':
      return {
        ...state,
        user: null,
        token: null,
        isAuthenticated: false,
        isLoading: false,
      }
    case 'SET_LOADING':
      return {
        ...state,
        isLoading: action.payload,
      }
    default:
      return state
  }
}

// Create context
const AuthContext = createContext<AuthContextType | undefined>(undefined)

// Token storage utilities
const TOKEN_KEY = 'auth_token'
const TOKEN_EXPIRY_KEY = 'auth_token_expiry'

const getStoredToken = (): string | null => {
  const token = localStorage.getItem(TOKEN_KEY)
  const expiry = localStorage.getItem(TOKEN_EXPIRY_KEY)
  
  if (!token || !expiry) {
    return null
  }
  
  // Check if token is expired
  if (Date.now() > parseInt(expiry)) {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(TOKEN_EXPIRY_KEY)
    return null
  }
  
  return token
}

const storeToken = (token: string, expiresIn: number): void => {
  const expiryTime = Date.now() + (expiresIn * 1000)
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(TOKEN_EXPIRY_KEY, expiryTime.toString())
}

const removeToken = (): void => {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(TOKEN_EXPIRY_KEY)
}

// Auth provider component
interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [state, dispatch] = useReducer(authReducer, initialState)

  // Initialize auth state on mount
  useEffect(() => {
    const initializeAuth = async () => {
      const storedToken = getStoredToken()
      
      if (storedToken) {
        try {
          dispatch({ type: 'REFRESH_START' })
          const user = await authApi.getCurrentUser(storedToken)
          dispatch({ 
            type: 'REFRESH_SUCCESS', 
            payload: { user, token: storedToken } 
          })
        } catch (error) {
          // Token is invalid, remove it
          removeToken()
          dispatch({ type: 'REFRESH_FAILURE' })
        }
      } else {
        dispatch({ type: 'SET_LOADING', payload: false })
      }
    }

    initializeAuth()
  }, [])

  // Auto-refresh token before expiry
  useEffect(() => {
    if (!state.token) return

    const checkTokenExpiry = () => {
      const expiry = localStorage.getItem(TOKEN_EXPIRY_KEY)
      if (!expiry) return

      const expiryTime = parseInt(expiry)
      const timeUntilExpiry = expiryTime - Date.now()
      
      // Refresh token 5 minutes before expiry
      if (timeUntilExpiry < 5 * 60 * 1000 && timeUntilExpiry > 0) {
        refreshToken()
      }
    }

    // Check every minute
    const interval = setInterval(checkTokenExpiry, 60 * 1000)
    return () => clearInterval(interval)
  }, [state.token])

  const login = async (credentials: LoginRequest): Promise<void> => {
    try {
      dispatch({ type: 'LOGIN_START' })
      const authResponse: AuthToken = await authApi.login(credentials)
      const user = await authApi.getCurrentUser(authResponse.access_token)
      
      storeToken(authResponse.access_token, authResponse.expires_in)
      dispatch({ 
        type: 'LOGIN_SUCCESS', 
        payload: { user, token: authResponse.access_token } 
      })
    } catch (error) {
      dispatch({ type: 'LOGIN_FAILURE' })
      throw error
    }
  }

  const logout = (): void => {
    removeToken()
    dispatch({ type: 'LOGOUT' })
  }

  const refreshToken = async (): Promise<void> => {
    const storedToken = getStoredToken()
    if (!storedToken) {
      logout()
      return
    }

    try {
      dispatch({ type: 'REFRESH_START' })
      const user = await authApi.getCurrentUser(storedToken)
      dispatch({ 
        type: 'REFRESH_SUCCESS', 
        payload: { user, token: storedToken } 
      })
    } catch (error) {
      removeToken()
      dispatch({ type: 'REFRESH_FAILURE' })
      throw error
    }
  }

  const contextValue: AuthContextType = {
    ...state,
    login,
    logout,
    refreshToken,
  }

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  )
}

// Custom hook to use auth context
export function useAuth(): AuthContextType {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
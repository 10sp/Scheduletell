import { useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { LoginForm } from '../components/LoginForm'

export function LoginPage() {
  const { isAuthenticated, isLoading } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  // Get the intended destination from location state, default to dashboard
  const from = (location.state as any)?.from?.pathname || '/dashboard'

  useEffect(() => {
    // If already authenticated, redirect to intended destination
    if (isAuthenticated && !isLoading) {
      navigate(from, { replace: true })
    }
  }, [isAuthenticated, isLoading, navigate, from])

  const handleLoginSuccess = () => {
    // Navigate to the intended destination after successful login
    navigate(from, { replace: true })
  }

  // Show loading while checking authentication status
  if (isLoading) {
    return (
      <div className="login-page loading">
        <div>Loading...</div>
      </div>
    )
  }

  // Don't render login form if already authenticated
  if (isAuthenticated) {
    return null
  }

  return (
    <div className="login-page">
      <div className="login-container">
        <div className="login-header">
          <h1>Appointment Scheduling System</h1>
          <p>Please log in to access your dashboard</p>
        </div>
        <LoginForm onSuccess={handleLoginSuccess} />
      </div>
    </div>
  )
}
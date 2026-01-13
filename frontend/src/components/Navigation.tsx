import React from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import './Navigation.css'

export function Navigation() {
  const { isAuthenticated, user, logout } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  // Don't show navigation on login page
  if (location.pathname === '/login') {
    return null
  }

  // Don't show navigation if not authenticated
  if (!isAuthenticated) {
    return null
  }

  const isActive = (path: string) => {
    return location.pathname === path ? 'active' : ''
  }

  return (
    <nav className="navigation">
      <div className="nav-container">
        <div className="nav-brand">
          <Link to="/dashboard" className="brand-link">
            <h2>Appointment Scheduler</h2>
          </Link>
        </div>

        <div className="nav-links">
          <Link 
            to="/dashboard" 
            className={`nav-link ${isActive('/dashboard')}`}
          >
            Dashboard
          </Link>
          <Link 
            to="/calendar" 
            className={`nav-link ${isActive('/calendar')}`}
          >
            Calendar
          </Link>
        </div>

        <div className="nav-user">
          {user && (
            <span className="user-info">
              Welcome, {user.username}
            </span>
          )}
          <button 
            onClick={handleLogout}
            className="logout-btn"
          >
            Logout
          </button>
        </div>
      </div>
    </nav>
  )
}
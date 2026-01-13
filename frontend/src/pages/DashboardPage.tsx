import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Dashboard } from '../components/Dashboard'
import { BookingForm } from '../components/BookingForm'

export function DashboardPage() {
  const navigate = useNavigate()
  const [showBookingForm, setShowBookingForm] = useState(false)

  const handleAppointmentClick = (appointmentId: string) => {
    // The Dashboard component handles appointment details internally
    // This is just for any additional page-level logic if needed
    console.log('Appointment clicked:', appointmentId)
  }

  const handleNewAppointment = () => {
    setShowBookingForm(true)
  }

  const handleBookingFormClose = () => {
    setShowBookingForm(false)
  }

  const handleBookingSuccess = () => {
    setShowBookingForm(false)
    // Optionally show a success message or refresh data
  }

  const handleViewCalendar = () => {
    navigate('/calendar')
  }

  return (
    <div className="dashboard-page">
      <div className="page-header">
        <h1>Dashboard</h1>
        <button 
          className="btn btn-secondary"
          onClick={handleViewCalendar}
        >
          View Calendar
        </button>
      </div>
      
      <Dashboard
        onAppointmentClick={handleAppointmentClick}
        onNewAppointment={handleNewAppointment}
      />

      {/* Booking Form Modal */}
      {showBookingForm && (
        <div className="modal-overlay">
          <div className="modal-content">
            <BookingForm
              onClose={handleBookingFormClose}
              onSuccess={handleBookingSuccess}
            />
          </div>
        </div>
      )}
    </div>
  )
}
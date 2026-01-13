import React, { useState } from 'react'
import { useAppointments, useAppointment } from '../hooks/useAppointments'
import { Appointment } from '../types/appointment'
import { AppointmentDetailModal } from './AppointmentDetailModal'
import { RescheduleForm } from './RescheduleForm'
import './Dashboard.css'

export interface DashboardProps {
  onAppointmentClick?: (appointmentId: string) => void
  onNewAppointment?: () => void
}

export const Dashboard: React.FC<DashboardProps> = ({
  onAppointmentClick,
  onNewAppointment,
}) => {
  const [selectedAppointmentId, setSelectedAppointmentId] = useState<string | null>(null)
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false)
  const [isRescheduleFormOpen, setIsRescheduleFormOpen] = useState(false)

  // Get current date for filtering upcoming appointments
  const now = new Date()
  const startDate = now.toISOString().split('T')[0] // Today's date in YYYY-MM-DD format

  // Fetch upcoming appointments from today onwards
  const { data: appointments = [], isLoading, error } = useAppointments({
    start_date: startDate,
  })

  // Fetch selected appointment details
  const { data: selectedAppointment } = useAppointment(selectedAppointmentId || '')

  // Filter and sort appointments to show only upcoming ones
  const upcomingAppointments = appointments
    .filter((appointment: Appointment) => new Date(appointment.start_time) >= now)
    .sort((a: Appointment, b: Appointment) => 
      new Date(a.start_time).getTime() - new Date(b.start_time).getTime()
    )

  const handleAppointmentClick = (appointmentId: string) => {
    setSelectedAppointmentId(appointmentId)
    setIsDetailModalOpen(true)
    
    // Call the optional prop callback
    if (onAppointmentClick) {
      onAppointmentClick(appointmentId)
    }
  }

  const handleNewAppointment = () => {
    if (onNewAppointment) {
      onNewAppointment()
    }
  }

  const handleCloseDetailModal = () => {
    setIsDetailModalOpen(false)
    setSelectedAppointmentId(null)
  }

  const handleReschedule = (appointment: Appointment) => {
    setIsDetailModalOpen(false)
    setIsRescheduleFormOpen(true)
  }

  const handleCloseRescheduleForm = () => {
    setIsRescheduleFormOpen(false)
  }

  const handleRescheduleSuccess = (updatedAppointment: Appointment) => {
    setIsRescheduleFormOpen(false)
    setSelectedAppointmentId(null)
    // The appointment list will be automatically updated via React Query
  }

  const formatDateTime = (dateTimeString: string) => {
    const date = new Date(dateTimeString)
    return {
      date: date.toLocaleDateString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      }),
      time: date.toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
      }),
    }
  }

  const formatDuration = (minutes: number) => {
    if (minutes < 60) {
      return `${minutes}m`
    }
    const hours = Math.floor(minutes / 60)
    const remainingMinutes = minutes % 60
    return remainingMinutes > 0 ? `${hours}h ${remainingMinutes}m` : `${hours}h`
  }

  if (isLoading) {
    return (
      <div className="dashboard">
        <div className="dashboard-header">
          <h2>Dashboard</h2>
          <button 
            className="new-appointment-btn"
            onClick={handleNewAppointment}
            disabled
          >
            New Appointment
          </button>
        </div>
        <div className="loading">Loading appointments...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="dashboard">
        <div className="dashboard-header">
          <h2>Dashboard</h2>
          <button 
            className="new-appointment-btn"
            onClick={handleNewAppointment}
          >
            New Appointment
          </button>
        </div>
        <div className="error">
          Error loading appointments: {error instanceof Error ? error.message : 'Unknown error'}
        </div>
      </div>
    )
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h2>Dashboard</h2>
        <button 
          className="new-appointment-btn"
          onClick={handleNewAppointment}
        >
          New Appointment
        </button>
      </div>

      <div className="appointments-section">
        <h3>Upcoming Appointments</h3>
        
        {upcomingAppointments.length === 0 ? (
          <div className="empty-state">
            <p>No upcoming appointments scheduled.</p>
            <p>Click "New Appointment" to schedule your first appointment.</p>
          </div>
        ) : (
          <div className="appointments-list">
            {upcomingAppointments.map((appointment) => {
              const { date, time } = formatDateTime(appointment.start_time)
              return (
                <div
                  key={appointment.id}
                  className="appointment-item"
                  onClick={() => handleAppointmentClick(appointment.id)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault()
                      handleAppointmentClick(appointment.id)
                    }
                  }}
                >
                  <div className="appointment-time">
                    <div className="appointment-date">{date}</div>
                    <div className="appointment-time-slot">{time}</div>
                  </div>
                  <div className="appointment-details">
                    <div className="customer-name">{appointment.customer_name}</div>
                    <div className="appointment-duration">
                      Duration: {formatDuration(appointment.duration_minutes)}
                    </div>
                  </div>
                  <div className="appointment-arrow">→</div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Appointment Detail Modal */}
      {selectedAppointment && (
        <AppointmentDetailModal
          appointment={selectedAppointment}
          isOpen={isDetailModalOpen}
          onClose={handleCloseDetailModal}
          onReschedule={handleReschedule}
        />
      )}

      {/* Reschedule Form Modal */}
      {selectedAppointment && (
        <RescheduleForm
          appointment={selectedAppointment}
          isOpen={isRescheduleFormOpen}
          onClose={handleCloseRescheduleForm}
          onSuccess={handleRescheduleSuccess}
        />
      )}
    </div>
  )
}

export default Dashboard
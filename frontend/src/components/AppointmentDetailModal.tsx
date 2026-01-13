import React from 'react'
import { Appointment } from '../types/appointment'
import { useDeleteAppointment } from '../hooks/useAppointments'
import './AppointmentDetailModal.css'

export interface AppointmentDetailModalProps {
  appointment: Appointment
  isOpen: boolean
  onClose: () => void
  onReschedule: (appointment: Appointment) => void
}

export const AppointmentDetailModal: React.FC<AppointmentDetailModalProps> = ({
  appointment,
  isOpen,
  onClose,
  onReschedule,
}) => {
  const deleteAppointmentMutation = useDeleteAppointment()

  const formatDateTime = (dateTimeString: string) => {
    const date = new Date(dateTimeString)
    return {
      date: date.toLocaleDateString('en-US', {
        weekday: 'long',
        month: 'long',
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
      return `${minutes} minutes`
    }
    const hours = Math.floor(minutes / 60)
    const remainingMinutes = minutes % 60
    if (remainingMinutes > 0) {
      return `${hours} hour${hours > 1 ? 's' : ''} ${remainingMinutes} minutes`
    }
    return `${hours} hour${hours > 1 ? 's' : ''}`
  }

  const handleReschedule = () => {
    onReschedule(appointment)
  }

  const handleDelete = async () => {
    if (window.confirm('Are you sure you want to delete this appointment? This action cannot be undone.')) {
      try {
        await deleteAppointmentMutation.mutateAsync(appointment.id)
        onClose()
      } catch (error) {
        console.error('Failed to delete appointment:', error)
        // Error handling is managed by the mutation hook and API client
      }
    }
  }

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose()
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose()
    }
  }

  if (!isOpen) {
    return null
  }

  const { date, time } = formatDateTime(appointment.start_time)
  const endTime = formatDateTime(appointment.end_time).time

  return (
    <div 
      className="modal-backdrop" 
      onClick={handleBackdropClick}
      onKeyDown={handleKeyDown}
      role="dialog"
      aria-modal="true"
      aria-labelledby="appointment-detail-title"
    >
      <div className="appointment-detail-modal">
        <div className="modal-header">
          <h2 id="appointment-detail-title">Appointment Details</h2>
          <button 
            className="close-button"
            onClick={onClose}
            aria-label="Close modal"
          >
            ×
          </button>
        </div>

        <div className="modal-content">
          <div className="appointment-info">
            <div className="info-section">
              <label>Customer Name</label>
              <div className="info-value">{appointment.customer_name}</div>
            </div>

            <div className="info-section">
              <label>Date</label>
              <div className="info-value">{date}</div>
            </div>

            <div className="info-section">
              <label>Time</label>
              <div className="info-value">{time} - {endTime}</div>
            </div>

            <div className="info-section">
              <label>Duration</label>
              <div className="info-value">{formatDuration(appointment.duration_minutes)}</div>
            </div>

            <div className="info-section">
              <label>Created</label>
              <div className="info-value">
                {new Date(appointment.created_at).toLocaleDateString('en-US', {
                  month: 'short',
                  day: 'numeric',
                  year: 'numeric',
                  hour: 'numeric',
                  minute: '2-digit',
                  hour12: true,
                })}
              </div>
            </div>

            {appointment.updated_at !== appointment.created_at && (
              <div className="info-section">
                <label>Last Updated</label>
                <div className="info-value">
                  {new Date(appointment.updated_at).toLocaleDateString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    year: 'numeric',
                    hour: 'numeric',
                    minute: '2-digit',
                    hour12: true,
                  })}
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="modal-actions">
          <button 
            className="reschedule-button"
            onClick={handleReschedule}
            disabled={deleteAppointmentMutation.isPending}
          >
            Reschedule
          </button>
          <button 
            className="delete-button"
            onClick={handleDelete}
            disabled={deleteAppointmentMutation.isPending}
          >
            {deleteAppointmentMutation.isPending ? 'Deleting...' : 'Delete'}
          </button>
          <button 
            className="cancel-button"
            onClick={onClose}
            disabled={deleteAppointmentMutation.isPending}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

export default AppointmentDetailModal
import React, { useState, useEffect } from 'react'
import { Appointment, AppointmentUpdate } from '../types/appointment'
import { useUpdateAppointment } from '../hooks/useAppointments'
import { useAvailability } from '../hooks/useAvailability'
import { ApiException } from '../types/api'
import './RescheduleForm.css'

export interface RescheduleFormProps {
  appointment: Appointment
  isOpen: boolean
  onClose: () => void
  onSuccess: (updatedAppointment: Appointment) => void
}

export const RescheduleForm: React.FC<RescheduleFormProps> = ({
  appointment,
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [selectedDate, setSelectedDate] = useState('')
  const [selectedTime, setSelectedTime] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const updateAppointmentMutation = useUpdateAppointment()

  // Get availability for the selected date
  const { data: availability = [], isLoading: isLoadingAvailability } = useAvailability({
    start_date: selectedDate,
    end_date: selectedDate,
  })

  // Initialize form with current appointment data
  useEffect(() => {
    if (appointment && isOpen) {
      const appointmentDate = new Date(appointment.start_time)
      const dateStr = appointmentDate.toISOString().split('T')[0]
      const timeStr = appointmentDate.toTimeString().slice(0, 5)
      
      setSelectedDate(dateStr)
      setSelectedTime(timeStr)
      setError(null)
      setIsSubmitting(false)
    }
  }, [appointment, isOpen])

  // Generate available time slots for the selected date
  const getAvailableTimeSlots = () => {
    if (!selectedDate || !availability.length) {
      return []
    }

    const slots: string[] = []
    const selectedDateObj = new Date(selectedDate)
    
    availability.forEach(slot => {
      if (slot.available) {
        const startTime = new Date(slot.start_time)
        const endTime = new Date(slot.end_time)
        
        // Generate 15-minute intervals within the available slot
        const current = new Date(startTime)
        while (current < endTime) {
          // Check if this slot can accommodate the appointment duration
          const slotEnd = new Date(current.getTime() + appointment.duration_minutes * 60000)
          if (slotEnd <= endTime) {
            const timeStr = current.toTimeString().slice(0, 5)
            slots.push(timeStr)
          }
          current.setMinutes(current.getMinutes() + 15)
        }
      }
    })

    return slots.sort()
  }

  const availableTimeSlots = getAvailableTimeSlots()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setIsSubmitting(true)

    try {
      // Validate inputs
      if (!selectedDate || !selectedTime) {
        throw new Error('Please select both date and time')
      }

      // Create new start time
      const newStartTime = new Date(`${selectedDate}T${selectedTime}:00`)
      
      // Check if the new time is in the future
      if (newStartTime <= new Date()) {
        throw new Error('Cannot reschedule to a time in the past')
      }

      // Check if this is actually a change
      const currentStartTime = new Date(appointment.start_time)
      if (newStartTime.getTime() === currentStartTime.getTime()) {
        throw new Error('Please select a different time to reschedule')
      }

      // Prepare update data
      const updateData: AppointmentUpdate = {
        start_time: newStartTime.toISOString(),
      }

      // Submit the reschedule request
      const updatedAppointment = await updateAppointmentMutation.mutateAsync({
        id: appointment.id,
        updateData,
      })

      onSuccess(updatedAppointment)
      onClose()
    } catch (error) {
      console.error('Reschedule error:', error)
      
      if (error instanceof ApiException) {
        // Handle specific API errors
        if (error.status === 409) {
          setError('This time slot is already booked. Please select a different time.')
        } else if (error.status === 400) {
          setError(error.message || 'Invalid reschedule request. Please check your selection.')
        } else {
          setError(error.message || 'Failed to reschedule appointment. Please try again.')
        }
      } else if (error instanceof Error) {
        setError(error.message)
      } else {
        setError('An unexpected error occurred. Please try again.')
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget && !isSubmitting) {
      onClose()
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape' && !isSubmitting) {
      onClose()
    }
  }

  const formatCurrentDateTime = () => {
    const date = new Date(appointment.start_time)
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

  // Get minimum date (today)
  const getMinDate = () => {
    const today = new Date()
    return today.toISOString().split('T')[0]
  }

  if (!isOpen) {
    return null
  }

  const currentDateTime = formatCurrentDateTime()

  return (
    <div 
      className="modal-backdrop" 
      onClick={handleBackdropClick}
      onKeyDown={handleKeyDown}
      role="dialog"
      aria-modal="true"
      aria-labelledby="reschedule-form-title"
    >
      <div className="reschedule-form-modal">
        <div className="modal-header">
          <h2 id="reschedule-form-title">Reschedule Appointment</h2>
          <button 
            className="close-button"
            onClick={onClose}
            disabled={isSubmitting}
            aria-label="Close modal"
          >
            ×
          </button>
        </div>

        <div className="modal-content">
          <div className="current-appointment">
            <h3>Current Appointment</h3>
            <div className="appointment-summary">
              <div><strong>Customer:</strong> {appointment.customer_name}</div>
              <div><strong>Date:</strong> {currentDateTime.date}</div>
              <div><strong>Time:</strong> {currentDateTime.time}</div>
              <div><strong>Duration:</strong> {appointment.duration_minutes} minutes</div>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="reschedule-form">
            <div className="form-group">
              <label htmlFor="reschedule-date">New Date</label>
              <input
                type="date"
                id="reschedule-date"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                min={getMinDate()}
                required
                disabled={isSubmitting}
                className="form-input"
              />
            </div>

            <div className="form-group">
              <label htmlFor="reschedule-time">New Time</label>
              {isLoadingAvailability && selectedDate ? (
                <div className="loading-message">Loading available times...</div>
              ) : availableTimeSlots.length > 0 ? (
                <select
                  id="reschedule-time"
                  value={selectedTime}
                  onChange={(e) => setSelectedTime(e.target.value)}
                  required
                  disabled={isSubmitting}
                  className="form-input"
                >
                  <option value="">Select a time</option>
                  {availableTimeSlots.map((timeSlot) => (
                    <option key={timeSlot} value={timeSlot}>
                      {new Date(`2000-01-01T${timeSlot}:00`).toLocaleTimeString('en-US', {
                        hour: 'numeric',
                        minute: '2-digit',
                        hour12: true,
                      })}
                    </option>
                  ))}
                </select>
              ) : selectedDate ? (
                <div className="no-availability">
                  No available time slots for the selected date that can accommodate a {appointment.duration_minutes}-minute appointment.
                </div>
              ) : (
                <div className="select-date-first">
                  Please select a date first to see available times.
                </div>
              )}
            </div>

            {error && (
              <div className="error-message" role="alert">
                {error}
              </div>
            )}

            <div className="form-actions">
              <button
                type="submit"
                disabled={isSubmitting || !selectedDate || !selectedTime || availableTimeSlots.length === 0}
                className="submit-button"
              >
                {isSubmitting ? 'Rescheduling...' : 'Reschedule Appointment'}
              </button>
              <button
                type="button"
                onClick={onClose}
                disabled={isSubmitting}
                className="cancel-button"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}

export default RescheduleForm
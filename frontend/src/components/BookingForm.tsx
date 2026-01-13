import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useCreateAppointment } from '../hooks/useAppointments'
import { AppointmentCreate } from '../types/appointment'
import './BookingForm.css'

// Validation schema
const bookingSchema = z.object({
  customer_name: z.string().min(1, 'Customer name is required').max(100, 'Customer name must be less than 100 characters'),
  date: z.string().min(1, 'Date is required'),
  time: z.string().min(1, 'Time is required'),
  duration_minutes: z.number().min(15, 'Duration must be at least 15 minutes').max(480, 'Duration cannot exceed 8 hours'),
})

type BookingFormData = z.infer<typeof bookingSchema>

interface BookingFormProps {
  selectedDate?: string // ISO date string (YYYY-MM-DD)
  selectedTime?: string // HH:MM format
  selectedSlot?: { start: Date; end: Date } // Time slot from calendar
  onSuccess?: (appointment: any) => void
  onCancel?: () => void
  onClose?: () => void
}

export function BookingForm({ selectedDate, selectedTime, selectedSlot, onSuccess, onCancel, onClose }: BookingFormProps) {
  const createAppointment = useCreateAppointment()
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  // Calculate default values from selectedSlot if provided
  const getDefaultValues = () => {
    if (selectedSlot) {
      const date = selectedSlot.start.toISOString().split('T')[0]
      const time = selectedSlot.start.toTimeString().slice(0, 5)
      const duration = Math.round((selectedSlot.end.getTime() - selectedSlot.start.getTime()) / (1000 * 60))
      
      return {
        customer_name: '',
        date,
        time,
        duration_minutes: Math.max(15, Math.min(480, duration)), // Clamp between 15 minutes and 8 hours
      }
    }
    
    return {
      customer_name: '',
      date: selectedDate || '',
      time: selectedTime || '',
      duration_minutes: 60, // Default to 1 hour
    }
  }

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<BookingFormData>({
    resolver: zodResolver(bookingSchema),
    defaultValues: getDefaultValues(),
  })

  const onSubmit = async (data: BookingFormData) => {
    try {
      setError(null)
      setSuccess(null)

      // Combine date and time into ISO datetime string
      const startDateTime = new Date(`${data.date}T${data.time}:00`)
      
      // Validate that the appointment is in the future
      if (startDateTime <= new Date()) {
        setError('Cannot book appointments in the past')
        return
      }

      const appointmentData: AppointmentCreate = {
        customer_name: data.customer_name,
        start_time: startDateTime.toISOString(),
        duration_minutes: data.duration_minutes,
      }

      const newAppointment = await createAppointment.mutateAsync(appointmentData)
      
      setSuccess('Appointment booked successfully!')
      reset()
      onSuccess?.(newAppointment)
    } catch (err: any) {
      // Handle different types of errors
      if (err.response?.status === 409) {
        setError('Time slot is already booked. Please select a different time.')
      } else if (err.response?.status === 400) {
        setError(err.response.data?.detail || 'Invalid booking data. Please check your inputs.')
      } else if (err.response?.data?.detail) {
        setError(err.response.data.detail)
      } else {
        setError('Booking failed. Please try again.')
      }
    }
  }

  // Generate time options (9 AM to 5 PM in 15-minute intervals)
  const generateTimeOptions = () => {
    const options = []
    for (let hour = 9; hour <= 17; hour++) {
      for (let minute = 0; minute < 60; minute += 15) {
        const timeString = `${hour.toString().padStart(2, '0')}:${minute.toString().padStart(2, '0')}`
        options.push(timeString)
      }
    }
    return options
  }

  // Generate duration options
  const durationOptions = [
    { value: 15, label: '15 minutes' },
    { value: 30, label: '30 minutes' },
    { value: 45, label: '45 minutes' },
    { value: 60, label: '1 hour' },
    { value: 90, label: '1.5 hours' },
    { value: 120, label: '2 hours' },
    { value: 180, label: '3 hours' },
    { value: 240, label: '4 hours' },
  ]

  // Get minimum date (today)
  const today = new Date().toISOString().split('T')[0]

  return (
    <div className="booking-form">
      <h2>Book New Appointment</h2>
      <form onSubmit={handleSubmit(onSubmit)}>
        <div className="form-group">
          <label htmlFor="customer_name">Customer Name</label>
          <input
            id="customer_name"
            type="text"
            {...register('customer_name')}
            disabled={createAppointment.isPending}
            className={errors.customer_name ? 'error' : ''}
            placeholder="Enter customer name"
          />
          {errors.customer_name && (
            <span className="error-message">{errors.customer_name.message}</span>
          )}
        </div>

        <div className="form-row">
          <div className="form-group">
            <label htmlFor="date">Date</label>
            <input
              id="date"
              type="date"
              {...register('date')}
              disabled={createAppointment.isPending}
              className={errors.date ? 'error' : ''}
              min={today}
            />
            {errors.date && (
              <span className="error-message">{errors.date.message}</span>
            )}
          </div>

          <div className="form-group">
            <label htmlFor="time">Time</label>
            <select
              id="time"
              {...register('time')}
              disabled={createAppointment.isPending}
              className={errors.time ? 'error' : ''}
            >
              <option value="">Select time</option>
              {generateTimeOptions().map((time) => (
                <option key={time} value={time}>
                  {time}
                </option>
              ))}
            </select>
            {errors.time && (
              <span className="error-message">{errors.time.message}</span>
            )}
          </div>
        </div>

        <div className="form-group">
          <label htmlFor="duration_minutes">Duration</label>
          <select
            id="duration_minutes"
            {...register('duration_minutes', { valueAsNumber: true })}
            disabled={createAppointment.isPending}
            className={errors.duration_minutes ? 'error' : ''}
          >
            {durationOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          {errors.duration_minutes && (
            <span className="error-message">{errors.duration_minutes.message}</span>
          )}
        </div>

        {error && (
          <div className="error-message booking-error">
            {error}
          </div>
        )}

        {success && (
          <div className="success-message">
            {success}
          </div>
        )}

        <div className="form-actions">
          <button
            type="button"
            onClick={onCancel || onClose}
            disabled={createAppointment.isPending}
            className="cancel-button"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={createAppointment.isPending}
            className="submit-button"
          >
            {createAppointment.isPending ? 'Booking...' : 'Book Appointment'}
          </button>
        </div>
      </form>
    </div>
  )
}
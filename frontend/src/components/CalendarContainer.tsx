import React, { useState, useCallback, useMemo } from 'react'
import { View, Views } from 'react-big-calendar'
import { format, startOfWeek, endOfWeek, startOfMonth, endOfMonth, startOfDay, endOfDay } from 'date-fns'
import Calendar from './Calendar'
import { useAppointments } from '../hooks/useAppointments'
import { useAvailability } from '../hooks/useAvailability'
import { Appointment } from '../types/appointment'

export interface CalendarContainerProps {
  onTimeSlotClick?: (slotInfo: { start: Date; end: Date }) => void
  onAppointmentClick?: (appointment: Appointment) => void
  className?: string
  defaultView?: View
}

export const CalendarContainer: React.FC<CalendarContainerProps> = ({
  onTimeSlotClick,
  onAppointmentClick,
  className = '',
  defaultView = Views.WEEK,
}) => {
  const [currentDate, setCurrentDate] = useState(new Date())
  const [currentView, setCurrentView] = useState<View>(defaultView)

  // Calculate date range based on current view and date
  const dateRange = useMemo(() => {
    let start: Date
    let end: Date

    switch (currentView) {
      case Views.MONTH:
        start = startOfMonth(currentDate)
        end = endOfMonth(currentDate)
        break
      case Views.WEEK:
        start = startOfWeek(currentDate, { weekStartsOn: 0 }) // Sunday
        end = endOfWeek(currentDate, { weekStartsOn: 0 })
        break
      case Views.DAY:
        start = startOfDay(currentDate)
        end = endOfDay(currentDate)
        break
      default:
        start = startOfWeek(currentDate, { weekStartsOn: 0 })
        end = endOfWeek(currentDate, { weekStartsOn: 0 })
    }

    return {
      start_date: format(start, 'yyyy-MM-dd'),
      end_date: format(end, 'yyyy-MM-dd'),
    }
  }, [currentDate, currentView])

  // Fetch appointments for the current date range
  const {
    data: appointments = [],
    isLoading: appointmentsLoading,
    error: appointmentsError,
  } = useAppointments(dateRange)

  // Fetch availability for the current date range
  const {
    data: availability = [],
    isLoading: availabilityLoading,
    error: availabilityError,
  } = useAvailability(dateRange)

  // Handle navigation (date changes)
  const handleNavigate = useCallback((date: Date) => {
    setCurrentDate(date)
  }, [])

  // Handle view changes
  const handleViewChange = useCallback((view: View) => {
    setCurrentView(view)
  }, [])

  // Handle time slot clicks
  const handleTimeSlotClick = useCallback(
    (slotInfo: { start: Date; end: Date }) => {
      // Only allow booking in the future
      const now = new Date()
      if (slotInfo.start < now) {
        return // Don't allow booking in the past
      }

      if (onTimeSlotClick) {
        onTimeSlotClick(slotInfo)
      }
    },
    [onTimeSlotClick]
  )

  // Handle appointment clicks
  const handleAppointmentClick = useCallback(
    (appointment: Appointment) => {
      if (onAppointmentClick) {
        onAppointmentClick(appointment)
      }
    },
    [onAppointmentClick]
  )

  // Determine loading state
  const isLoading = appointmentsLoading || availabilityLoading

  // Determine error state
  const hasError = appointmentsError || availabilityError
  const errorMessage = appointmentsError?.message || availabilityError?.message

  // Render error state
  if (hasError && !isLoading) {
    return (
      <div className={`calendar-container error ${className}`}>
        <div className="calendar-error-message">
          <h3>Unable to load calendar</h3>
          <p>{errorMessage || 'An error occurred while loading the calendar data.'}</p>
          <button
            onClick={() => window.location.reload()}
            className="btn btn-primary"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <Calendar
      appointments={appointments}
      availability={availability}
      onTimeSlotClick={handleTimeSlotClick}
      onAppointmentClick={handleAppointmentClick}
      onNavigate={handleNavigate}
      onViewChange={handleViewChange}
      defaultView={currentView}
      className={`${className} ${isLoading ? 'loading' : ''}`}
    />
  )
}

export default CalendarContainer
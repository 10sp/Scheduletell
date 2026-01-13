import React, { useMemo, useCallback } from 'react'
import { Calendar as BigCalendar, momentLocalizer, View, Views } from 'react-big-calendar'
import moment from 'moment'
import { Appointment } from '../types/appointment'
import { TimeSlot } from '../types/availability'
import 'react-big-calendar/lib/css/react-big-calendar.css'
import './Calendar.css'

// Setup the localizer for react-big-calendar
const localizer = momentLocalizer(moment)

export interface CalendarEvent {
  id: string
  title: string
  start: Date
  end: Date
  resource: Appointment
}

export interface CalendarProps {
  appointments: Appointment[]
  availability?: TimeSlot[]
  onTimeSlotClick?: (slotInfo: { start: Date; end: Date }) => void
  onAppointmentClick?: (appointment: Appointment) => void
  onNavigate?: (date: Date) => void
  onViewChange?: (view: View) => void
  defaultView?: View
  className?: string
}

export const Calendar: React.FC<CalendarProps> = ({
  appointments = [],
  availability = [],
  onTimeSlotClick,
  onAppointmentClick,
  onNavigate,
  onViewChange,
  defaultView = Views.WEEK,
  className = '',
}) => {
  // Convert appointments to calendar events
  const events = useMemo((): CalendarEvent[] => {
    return appointments.map((appointment) => ({
      id: appointment.id,
      title: `${appointment.customer_name}`,
      start: new Date(appointment.start_time),
      end: new Date(appointment.end_time),
      resource: appointment,
    }))
  }, [appointments])

  // Handle slot selection (clicking on empty time slots)
  const handleSelectSlot = useCallback(
    (slotInfo: { start: Date; end: Date; slots: Date[]; action: string }) => {
      if (onTimeSlotClick && slotInfo.action === 'select') {
        onTimeSlotClick({
          start: slotInfo.start,
          end: slotInfo.end,
        })
      }
    },
    [onTimeSlotClick]
  )

  // Handle event selection (clicking on appointments)
  const handleSelectEvent = useCallback(
    (event: CalendarEvent) => {
      if (onAppointmentClick) {
        onAppointmentClick(event.resource)
      }
    },
    [onAppointmentClick]
  )

  // Handle navigation (date changes)
  const handleNavigate = useCallback(
    (date: Date) => {
      if (onNavigate) {
        onNavigate(date)
      }
    },
    [onNavigate]
  )

  // Handle view changes
  const handleViewChange = useCallback(
    (view: View) => {
      if (onViewChange) {
        onViewChange(view)
      }
    },
    [onViewChange]
  )

  // Custom event style getter
  const eventStyleGetter = useCallback(
    (_event: CalendarEvent) => {
      return {
        style: {
          backgroundColor: '#3174ad',
          borderRadius: '4px',
          opacity: 0.8,
          color: 'white',
          border: '0px',
          display: 'block',
        },
      }
    },
    []
  )

  // Custom slot style getter for availability
  const slotStyleGetter = useCallback(
    (date: Date) => {
      // Check if this time slot is available
      const isAvailable = availability.some((slot) => {
        const slotStart = new Date(slot.start_time)
        const slotEnd = new Date(slot.end_time)
        return date >= slotStart && date < slotEnd && slot.available
      })

      if (isAvailable) {
        return {
          style: {
            backgroundColor: '#e8f5e8', // Light green for available slots
          },
        }
      }

      return {}
    },
    [availability]
  )

  // Custom day prop getter
  const dayPropGetter = useCallback(
    (date: Date) => {
      const today = new Date()
      const isToday = moment(date).isSame(today, 'day')
      const isPast = moment(date).isBefore(today, 'day')

      return {
        style: {
          backgroundColor: isToday ? '#f0f8ff' : isPast ? '#f5f5f5' : undefined,
        },
      }
    },
    []
  )

  return (
    <div className={`calendar-container ${className}`}>
      <BigCalendar
        localizer={localizer}
        events={events}
        startAccessor="start"
        endAccessor="end"
        titleAccessor="title"
        defaultView={defaultView}
        views={[Views.MONTH, Views.WEEK, Views.DAY]}
        step={15} // 15-minute intervals
        timeslots={4} // 4 slots per hour (15-minute intervals)
        selectable={!!onTimeSlotClick}
        onSelectSlot={handleSelectSlot}
        onSelectEvent={handleSelectEvent}
        onNavigate={handleNavigate}
        onView={handleViewChange}
        eventPropGetter={eventStyleGetter}
        slotPropGetter={slotStyleGetter}
        dayPropGetter={dayPropGetter}
        popup={true}
        popupOffset={30}
        showMultiDayTimes={true}
        min={new Date(2024, 0, 1, 8, 0)} // 8 AM
        max={new Date(2024, 0, 1, 18, 0)} // 6 PM
        formats={{
          timeGutterFormat: 'HH:mm',
          eventTimeRangeFormat: ({ start, end }) =>
            `${moment(start).format('HH:mm')} - ${moment(end).format('HH:mm')}`,
          agendaTimeRangeFormat: ({ start, end }) =>
            `${moment(start).format('HH:mm')} - ${moment(end).format('HH:mm')}`,
        }}
        messages={{
          allDay: 'All Day',
          previous: '‹',
          next: '›',
          today: 'Today',
          month: 'Month',
          week: 'Week',
          day: 'Day',
          agenda: 'Agenda',
          date: 'Date',
          time: 'Time',
          event: 'Appointment',
          noEventsInRange: 'No appointments in this range.',
          showMore: (total) => `+${total} more`,
        }}
      />
    </div>
  )
}

export default Calendar
import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CalendarContainer } from '../components/CalendarContainer'
import { BookingForm } from '../components/BookingForm'
import { AppointmentDetailModal } from '../components/AppointmentDetailModal'
import { RescheduleForm } from '../components/RescheduleForm'
import { Appointment } from '../types/appointment'
import { useAppointment } from '../hooks/useAppointments'

export function CalendarPage() {
  const navigate = useNavigate()
  const [showBookingForm, setShowBookingForm] = useState(false)
  const [selectedTimeSlot, setSelectedTimeSlot] = useState<{ start: Date; end: Date } | null>(null)
  const [selectedAppointmentId, setSelectedAppointmentId] = useState<string | null>(null)
  const [showAppointmentDetail, setShowAppointmentDetail] = useState(false)
  const [showRescheduleForm, setShowRescheduleForm] = useState(false)

  // Fetch selected appointment details
  const { data: selectedAppointment } = useAppointment(selectedAppointmentId || '')

  const handleTimeSlotClick = (slotInfo: { start: Date; end: Date }) => {
    setSelectedTimeSlot(slotInfo)
    setShowBookingForm(true)
  }

  const handleAppointmentClick = (appointment: Appointment) => {
    setSelectedAppointmentId(appointment.id)
    setShowAppointmentDetail(true)
  }

  const handleBookingFormClose = () => {
    setShowBookingForm(false)
    setSelectedTimeSlot(null)
  }

  const handleBookingSuccess = () => {
    setShowBookingForm(false)
    setSelectedTimeSlot(null)
    // Calendar will automatically refresh via React Query
  }

  const handleAppointmentDetailClose = () => {
    setShowAppointmentDetail(false)
    setSelectedAppointmentId(null)
  }

  const handleReschedule = (appointment: Appointment) => {
    setShowAppointmentDetail(false)
    setShowRescheduleForm(true)
  }

  const handleRescheduleFormClose = () => {
    setShowRescheduleForm(false)
  }

  const handleRescheduleSuccess = (updatedAppointment: Appointment) => {
    setShowRescheduleForm(false)
    setSelectedAppointmentId(null)
    // Calendar will automatically refresh via React Query
  }

  const handleBackToDashboard = () => {
    navigate('/dashboard')
  }

  return (
    <div className="calendar-page">
      <div className="page-header">
        <h1>Calendar</h1>
        <button 
          className="btn btn-secondary"
          onClick={handleBackToDashboard}
        >
          Back to Dashboard
        </button>
      </div>
      
      <div className="calendar-instructions">
        <p>Click on an empty time slot to book a new appointment, or click on an existing appointment to view details.</p>
      </div>

      <CalendarContainer
        onTimeSlotClick={handleTimeSlotClick}
        onAppointmentClick={handleAppointmentClick}
        className="calendar-page-calendar"
      />

      {/* Booking Form Modal */}
      {showBookingForm && selectedTimeSlot && (
        <div className="modal-overlay">
          <div className="modal-content">
            <BookingForm
              selectedSlot={selectedTimeSlot}
              onClose={handleBookingFormClose}
              onSuccess={handleBookingSuccess}
            />
          </div>
        </div>
      )}

      {/* Appointment Detail Modal */}
      {selectedAppointment && (
        <AppointmentDetailModal
          appointment={selectedAppointment}
          isOpen={showAppointmentDetail}
          onClose={handleAppointmentDetailClose}
          onReschedule={handleReschedule}
        />
      )}

      {/* Reschedule Form Modal */}
      {selectedAppointment && (
        <RescheduleForm
          appointment={selectedAppointment}
          isOpen={showRescheduleForm}
          onClose={handleRescheduleFormClose}
          onSuccess={handleRescheduleSuccess}
        />
      )}
    </div>
  )
}
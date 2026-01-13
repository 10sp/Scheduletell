export interface Appointment {
  id: string
  customer_name: string
  start_time: string // ISO datetime string
  duration_minutes: number
  end_time: string // ISO datetime string
  created_at: string
  updated_at: string
}

export interface AppointmentCreate {
  customer_name: string
  start_time: string // ISO datetime string
  duration_minutes: number
}

export interface AppointmentUpdate {
  customer_name?: string
  start_time?: string // ISO datetime string
  duration_minutes?: number
}

export interface AppointmentListParams {
  start_date?: string // ISO date string
  end_date?: string // ISO date string
}
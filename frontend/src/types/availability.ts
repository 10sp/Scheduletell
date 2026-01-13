export interface TimeSlot {
  start_time: string // ISO datetime string
  end_time: string // ISO datetime string
  available: boolean
}

export interface AvailabilityUpdate {
  day_of_week: number // 0-6, where 0 is Sunday
  start_time: string // HH:MM format
  end_time: string // HH:MM format
}

export interface AvailabilityParams {
  start_date?: string // ISO date string
  end_date?: string // ISO date string
}
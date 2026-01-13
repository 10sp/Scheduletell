import axios, { AxiosInstance, AxiosError, AxiosResponse } from 'axios'
import { LoginRequest, AuthToken, User } from '../types/auth'
import { Appointment, AppointmentCreate, AppointmentUpdate, AppointmentListParams } from '../types/appointment'
import { TimeSlot, AvailabilityUpdate, AvailabilityParams } from '../types/availability'
import { ApiException } from '../types/api'

class ApiClient {
  private client: AxiosInstance
  private token: string | null = null

  constructor() {
    this.client = axios.create({
      baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 10000, // 10 second timeout
    })

    this.setupInterceptors()
    this.loadTokenFromStorage()
  }

  private setupInterceptors() {
    // Request interceptor to add auth token
    this.client.interceptors.request.use(
      (config) => {
        if (this.token) {
          config.headers.Authorization = `Bearer ${this.token}`
        }
        return config
      },
      (error) => {
        return Promise.reject(error)
      }
    )

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response: AxiosResponse) => {
        return response
      },
      (error: AxiosError) => {
        const status = error.response?.status || 500
        const message = this.extractErrorMessage(error)
        const details = error.response?.data

        // Handle token expiration
        if (status === 401 && this.token) {
          this.clearToken()
          // Redirect to login or trigger re-authentication
          window.location.href = '/login'
        }

        throw new ApiException(message, status, details)
      }
    )
  }

  private extractErrorMessage(error: AxiosError): string {
    if (error.response?.data) {
      const data = error.response.data as any
      if (typeof data === 'string') return data
      if (data.message) return data.message
      if (data.detail) return data.detail
      if (data.error) return data.error
    }
    
    if (error.message) return error.message
    return 'An unexpected error occurred'
  }

  private loadTokenFromStorage() {
    const storedToken = localStorage.getItem('auth_token')
    if (storedToken) {
      this.token = storedToken
    }
  }

  public setToken(token: string) {
    this.token = token
    localStorage.setItem('auth_token', token)
  }

  public clearToken() {
    this.token = null
    localStorage.removeItem('auth_token')
  }

  public getToken(): string | null {
    return this.token
  }

  // Authentication endpoints
  public async login(credentials: LoginRequest): Promise<AuthToken> {
    const response = await this.client.post<AuthToken>('/auth/login', credentials)
    const authToken = response.data
    this.setToken(authToken.access_token)
    return authToken
  }

  public async logout(): Promise<void> {
    try {
      await this.client.post('/auth/logout')
    } finally {
      this.clearToken()
    }
  }

  public async getCurrentUser(): Promise<User> {
    const response = await this.client.get<User>('/auth/me')
    return response.data
  }

  // Appointment endpoints
  public async createAppointment(appointmentData: AppointmentCreate): Promise<Appointment> {
    const response = await this.client.post<Appointment>('/appointments', appointmentData)
    return response.data
  }

  public async getAppointments(params?: AppointmentListParams): Promise<Appointment[]> {
    const response = await this.client.get<Appointment[]>('/appointments', { params })
    return response.data
  }

  public async getAppointment(id: string): Promise<Appointment> {
    const response = await this.client.get<Appointment>(`/appointments/${id}`)
    return response.data
  }

  public async updateAppointment(id: string, updateData: AppointmentUpdate): Promise<Appointment> {
    const response = await this.client.put<Appointment>(`/appointments/${id}`, updateData)
    return response.data
  }

  public async deleteAppointment(id: string): Promise<void> {
    await this.client.delete(`/appointments/${id}`)
  }

  // Availability endpoints
  public async getAvailability(params?: AvailabilityParams): Promise<TimeSlot[]> {
    const response = await this.client.get<TimeSlot[]>('/availability', { params })
    return response.data
  }

  public async updateAvailability(availabilityData: AvailabilityUpdate[]): Promise<void> {
    await this.client.put('/availability', availabilityData)
  }
}

// Create and export a singleton instance
export const apiClient = new ApiClient()

// Export the class for testing purposes
export { ApiClient }
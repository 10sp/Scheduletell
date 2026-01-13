export interface ApiError {
  message: string
  status: number
  details?: any
}

export interface ApiResponse<T> {
  data: T
  message?: string
}

export class ApiException extends Error {
  public status: number
  public details?: any

  constructor(message: string, status: number, details?: any) {
    super(message)
    this.name = 'ApiException'
    this.status = status
    this.details = details
  }
}
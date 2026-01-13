import { LoginRequest, AuthToken, User } from '../types/auth'
import { apiClient } from './apiClient'

// Legacy auth API wrapper - use apiClient directly for new code
export const authApi = {
  async login(credentials: LoginRequest): Promise<AuthToken> {
    return apiClient.login(credentials)
  },

  async getCurrentUser(token: string): Promise<User> {
    // Set token temporarily if not already set
    const currentToken = apiClient.getToken()
    if (!currentToken && token) {
      apiClient.setToken(token)
    }
    return apiClient.getCurrentUser()
  },

  async logout(): Promise<void> {
    return apiClient.logout()
  },
}
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../services/apiClient'
import { LoginRequest } from '../types/auth'

// Query keys for authentication
export const authKeys = {
  all: ['auth'] as const,
  user: () => [...authKeys.all, 'user'] as const,
}

// Hook to fetch current user (useful for checking auth status)
export function useCurrentUser() {
  return useQuery({
    queryKey: authKeys.user(),
    queryFn: () => apiClient.getCurrentUser(),
    enabled: !!apiClient.getToken(), // Only run if we have a token
    staleTime: 10 * 60 * 1000, // 10 minutes
    gcTime: 15 * 60 * 1000, // 15 minutes
    retry: (failureCount, error: any) => {
      // Don't retry on 401 errors (unauthorized)
      if (error?.status === 401) {
        return false
      }
      return failureCount < 3
    },
  })
}

// Hook for login mutation
export function useLogin() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (credentials: LoginRequest) => apiClient.login(credentials),
    onSuccess: () => {
      // Invalidate and refetch user data after successful login
      queryClient.invalidateQueries({ queryKey: authKeys.user() })
    },
  })
}

// Hook for logout mutation
export function useLogout() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => apiClient.logout(),
    onSuccess: () => {
      // Clear all cached data on logout
      queryClient.clear()
    },
  })
}
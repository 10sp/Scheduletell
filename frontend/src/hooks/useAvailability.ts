import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../services/apiClient'
import { AvailabilityUpdate, AvailabilityParams } from '../types/availability'

// Query keys for consistent cache management
export const availabilityKeys = {
  all: ['availability'] as const,
  lists: () => [...availabilityKeys.all, 'list'] as const,
  list: (params?: AvailabilityParams) => [...availabilityKeys.lists(), params] as const,
}

// Hook to fetch availability
export function useAvailability(params?: AvailabilityParams) {
  return useQuery({
    queryKey: availabilityKeys.list(params),
    queryFn: () => apiClient.getAvailability(params),
    staleTime: 2 * 60 * 1000, // 2 minutes (availability changes less frequently)
    gcTime: 5 * 60 * 1000, // 5 minutes
  })
}

// Hook to update availability
export function useUpdateAvailability() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (availabilityData: AvailabilityUpdate[]) =>
      apiClient.updateAvailability(availabilityData),
    onSuccess: () => {
      // Invalidate all availability queries to ensure fresh data
      queryClient.invalidateQueries({ queryKey: availabilityKeys.all })
    },
  })
}
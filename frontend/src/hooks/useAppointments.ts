import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../services/apiClient'
import { AppointmentCreate, AppointmentUpdate, AppointmentListParams } from '../types/appointment'

// Query keys for consistent cache management
export const appointmentKeys = {
  all: ['appointments'] as const,
  lists: () => [...appointmentKeys.all, 'list'] as const,
  list: (params?: AppointmentListParams) => [...appointmentKeys.lists(), params] as const,
  details: () => [...appointmentKeys.all, 'detail'] as const,
  detail: (id: string) => [...appointmentKeys.details(), id] as const,
}

// Hook to fetch appointments list
export function useAppointments(params?: AppointmentListParams) {
  return useQuery({
    queryKey: appointmentKeys.list(params),
    queryFn: () => apiClient.getAppointments(params),
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes (formerly cacheTime)
  })
}

// Hook to fetch a single appointment
export function useAppointment(id: string) {
  return useQuery({
    queryKey: appointmentKeys.detail(id),
    queryFn: () => apiClient.getAppointment(id),
    enabled: !!id,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

// Hook to create an appointment
export function useCreateAppointment() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (appointmentData: AppointmentCreate) => 
      apiClient.createAppointment(appointmentData),
    onSuccess: (newAppointment) => {
      // Invalidate and refetch appointments list
      queryClient.invalidateQueries({ queryKey: appointmentKeys.lists() })
      
      // Add the new appointment to the cache
      queryClient.setQueryData(
        appointmentKeys.detail(newAppointment.id),
        newAppointment
      )
    },
  })
}

// Hook to update/reschedule an appointment
export function useUpdateAppointment() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, updateData }: { id: string; updateData: AppointmentUpdate }) =>
      apiClient.updateAppointment(id, updateData),
    onSuccess: (updatedAppointment) => {
      // Update the specific appointment in cache
      queryClient.setQueryData(
        appointmentKeys.detail(updatedAppointment.id),
        updatedAppointment
      )
      
      // Invalidate appointments list to ensure consistency
      queryClient.invalidateQueries({ queryKey: appointmentKeys.lists() })
    },
  })
}

// Hook to delete an appointment
export function useDeleteAppointment() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => apiClient.deleteAppointment(id),
    onSuccess: (_, deletedId) => {
      // Remove from cache
      queryClient.removeQueries({ queryKey: appointmentKeys.detail(deletedId) })
      
      // Invalidate appointments list
      queryClient.invalidateQueries({ queryKey: appointmentKeys.lists() })
    },
  })
}
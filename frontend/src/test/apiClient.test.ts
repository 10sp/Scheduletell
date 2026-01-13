import { describe, it, expect, beforeEach, vi } from 'vitest'
import axios from 'axios'
import { ApiClient } from '../services/apiClient'
import { ApiException } from '../types/api'

// Mock axios
vi.mock('axios')
const mockedAxios = vi.mocked(axios)

describe('ApiClient', () => {
  let apiClient: ApiClient
  
  beforeEach(() => {
    vi.clearAllMocks()
    
    // Mock axios.create
    const mockAxiosInstance = {
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() }
      },
      post: vi.fn(),
      get: vi.fn(),
      put: vi.fn(),
      delete: vi.fn()
    }
    
    mockedAxios.create.mockReturnValue(mockAxiosInstance as any)
    
    // Mock localStorage
    Object.defineProperty(window, 'localStorage', {
      value: {
        getItem: vi.fn(),
        setItem: vi.fn(),
        removeItem: vi.fn(),
      },
      writable: true,
    })
    
    apiClient = new ApiClient()
  })

  it('should create axios instance with correct config', () => {
    expect(mockedAxios.create).toHaveBeenCalledWith({
      baseURL: '/api',
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 10000,
    })
  })

  it('should set up request and response interceptors', () => {
    const mockInstance = mockedAxios.create.mock.results[0].value
    expect(mockInstance.interceptors.request.use).toHaveBeenCalled()
    expect(mockInstance.interceptors.response.use).toHaveBeenCalled()
  })

  it('should manage token correctly', () => {
    const testToken = 'test-token-123'
    
    apiClient.setToken(testToken)
    expect(apiClient.getToken()).toBe(testToken)
    expect(localStorage.setItem).toHaveBeenCalledWith('auth_token', testToken)
    
    apiClient.clearToken()
    expect(apiClient.getToken()).toBeNull()
    expect(localStorage.removeItem).toHaveBeenCalledWith('auth_token')
  })
})
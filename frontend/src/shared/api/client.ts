import axios from 'axios'
import { env } from '../config/env'

export const apiClient = axios.create({
  baseURL: `${env.API_BASE_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
})

apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    // Handle global errors here
    return Promise.reject(error.response?.data || error)
  }
)

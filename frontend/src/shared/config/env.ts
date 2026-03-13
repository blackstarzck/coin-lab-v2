const devDefaultApiBaseUrl = import.meta.env.DEV ? 'http://localhost:8012' : ''

export const env = {
  // In development, connect to the backend directly so normal WebSocket reconnects
  // do not surface as Vite proxy ECONNABORTED noise in the terminal.
  API_BASE_URL: import.meta.env.VITE_API_BASE_URL ?? devDefaultApiBaseUrl,
}

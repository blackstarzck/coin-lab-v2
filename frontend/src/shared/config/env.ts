const devDefaultApiBaseUrl = import.meta.env.DEV ? 'http://localhost:8012' : ''

function normalizeLoopbackHostname(value: string): string {
  try {
    const url = new URL(value)
    if (url.hostname === '127.0.0.1' || url.hostname === '0.0.0.0' || url.hostname === '[::1]' || url.hostname === '::1') {
      url.hostname = 'localhost'
      return url.toString()
    }
  } catch {
    return value
  }
  return value
}

function normalizeBaseUrl(value: string | undefined, fallback: string): string {
  const normalized = (value ?? fallback).trim()
  if (!normalized) {
    return ''
  }
  return normalizeLoopbackHostname(normalized).replace(/\/+$/, '')
}

export const env = {
  // In development, connect to the backend directly. We also normalize loopback
  // hosts to localhost because some browser/webview environments fail requests
  // to 127.0.0.1 even when localhost is reachable.
  API_BASE_URL: normalizeBaseUrl(import.meta.env.VITE_API_BASE_URL, devDefaultApiBaseUrl),
}

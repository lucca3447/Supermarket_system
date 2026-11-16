import axios from 'axios'

const baseURL = import.meta.env.DEV
  ? import.meta.env.VITE_API_URL || 'http://localhost:8000'
  : '/api'

export const api = axios.create({
  baseURL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
})

let onUnauthorizedHandler = null
let refreshEmAndamento = null
let accessTokenMemoria = null

export function setOnUnauthorized(handler) {
  onUnauthorizedHandler = handler
}

const ROTAS_AUTH_SEM_RETRY = [
  '/auth/login',
  '/auth/registrar',
  '/auth/refresh',
  '/auth/logout',
]

const ROTAS_EMITEM_TOKEN = ['/auth/login', '/auth/registrar', '/auth/refresh']

api.interceptors.request.use((config) => {
  if (accessTokenMemoria && config.headers) {
    config.headers.Authorization = `Bearer ${accessTokenMemoria}`
  }
  return config
})

api.interceptors.response.use(
  (response) => {
    const url = response.config?.url || ''
    if (url.includes('/auth/logout')) {
      accessTokenMemoria = null
    } else if (
      ROTAS_EMITEM_TOKEN.some((rota) => url.includes(rota)) &&
      response.data?.access_token
    ) {
      accessTokenMemoria = response.data.access_token
    }
    return response
  },
  async (error) => {
    const originalRequest = error.config
    const status = error.response?.status
    const url = originalRequest?.url || ''

    if (
      status !== 401 ||
      !originalRequest ||
      originalRequest._retry ||
      originalRequest._skipAuthRefresh ||
      ROTAS_AUTH_SEM_RETRY.some((rota) => url.includes(rota))
    ) {
      return Promise.reject(error)
    }

    originalRequest._retry = true
    try {
      if (!refreshEmAndamento) {
        refreshEmAndamento = api.post('/auth/refresh').finally(() => {
          refreshEmAndamento = null
        })
      }
      await refreshEmAndamento
      if (originalRequest.headers) {
        delete originalRequest.headers.Authorization
      }
      return api(originalRequest)
    } catch (refreshError) {
      accessTokenMemoria = null
      onUnauthorizedHandler?.()
      return Promise.reject(refreshError)
    }
  },
)

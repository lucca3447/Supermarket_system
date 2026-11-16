import axios from 'axios'

const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
})

let onUnauthorizedHandler = null
let refreshEmAndamento = null

export function setOnUnauthorized(handler) {
  onUnauthorizedHandler = handler
}

const ROTAS_AUTH_SEM_RETRY = [
  '/auth/login',
  '/auth/registrar',
  '/auth/refresh',
  '/auth/logout',
]

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    const status = error.response?.status
    const url = originalRequest?.url || ''

    if (
      status !== 401 ||
      !originalRequest ||
      originalRequest._retry ||
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
      return api(originalRequest)
    } catch (refreshError) {
      onUnauthorizedHandler?.()
      return Promise.reject(refreshError)
    }
  },
)

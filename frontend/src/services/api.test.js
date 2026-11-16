import { describe, expect, it, vi } from 'vitest'
import { api, setOnUnauthorized } from './api'

describe('api interceptor — refresh automático em 401', () => {
  it('configura withCredentials e renova sessão em 401 com retry único', async () => {
    expect(api.defaults.withCredentials).toBe(true)

    const onUnauthorized = vi.fn()
    setOnUnauthorized(onUnauthorized)

    let tentativasProdutos = 0
    let refreshChamado = 0

    api.defaults.adapter = async (config) => {
      if (config.url === '/produtos/') {
        tentativasProdutos += 1
        if (tentativasProdutos === 1) {
          const error = new Error('Unauthorized')
          error.config = config
          error.response = { status: 401, data: { detail: 'Expirado' } }
          throw error
        }
        return {
          data: [{ id_produto: 1, nome: 'Café' }],
          status: 200,
          statusText: 'OK',
          headers: {},
          config,
        }
      }

      if (config.url === '/auth/refresh') {
        refreshChamado += 1
        return { data: { ok: true }, status: 200, statusText: 'OK', headers: {}, config }
      }

      return { data: {}, status: 200, statusText: 'OK', headers: {}, config }
    }

    const res = await api.get('/produtos/')
    expect(res.data).toEqual([{ id_produto: 1, nome: 'Café' }])
    expect(refreshChamado).toBe(1)
    expect(tentativasProdutos).toBe(2)
    expect(onUnauthorized).not.toHaveBeenCalled()
  })

  it('chama onUnauthorized se /auth/refresh falhar e não faz loop em /auth/login', async () => {
    const onUnauthorized = vi.fn()
    setOnUnauthorized(onUnauthorized)

    api.defaults.adapter = async (config) => {
      const error = new Error('Unauthorized')
      error.config = config
      error.response = { status: 401, data: { detail: 'Inválido' } }
      throw error
    }

    await expect(api.get('/produtos/')).rejects.toThrow('Unauthorized')
    expect(onUnauthorized).toHaveBeenCalledTimes(1)

    await expect(api.post('/auth/login', {})).rejects.toThrow('Unauthorized')
    expect(onUnauthorized).toHaveBeenCalledTimes(1)
  })
})

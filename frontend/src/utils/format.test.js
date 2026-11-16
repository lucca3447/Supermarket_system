import { describe, expect, it } from 'vitest'
import { api } from '../services/api'
import {
  calcularResumoCarrinho,
  formatBRL,
  formatDateTime,
} from './format'

describe('format.js e api.js', () => {
  it('carrinho vazio retorna zeros e falta R$ 200,01 para 5% OFF', () => {
    const resumo = calcularResumoCarrinho([])
    expect(resumo).toEqual({
      bruto: 0,
      desconto: 0,
      final: 0,
      faltam: 200.01,
      teveDesconto: false,
      progresso: 0,
    })
  })

  it('compra exata de R$ 200,00 nao aplica desconto e informa que falta R$ 0,01', () => {
    const resumo = calcularResumoCarrinho([{ preco: '100.00', quantidade: 2 }])
    expect(resumo.bruto).toBe(200)
    expect(resumo.desconto).toBe(0)
    expect(resumo.final).toBe(200)
    expect(resumo.faltam).toBe(0.01)
    expect(resumo.teveDesconto).toBe(false)
    expect(resumo.progresso).toBe(100)
  })

  it('compra de R$ 200,01 ativa desconto de 5%', () => {
    const resumo = calcularResumoCarrinho([{ preco: '200.01', quantidade: 1 }])
    expect(resumo.bruto).toBe(200.01)
    expect(resumo.desconto).toBe(10)
    expect(resumo.final).toBe(190.01)
    expect(resumo.faltam).toBe(0)
    expect(resumo.teveDesconto).toBe(true)
    expect(resumo.progresso).toBe(100)
  })

  it('compra de R$ 250,00 aplica R$ 12,50 de desconto e totaliza R$ 237,50', () => {
    const resumo = calcularResumoCarrinho([
      { preco: '89.90', quantidade: 2 },
      { preco: '70.20', quantidade: 1 },
    ])
    expect(resumo.bruto).toBe(250)
    expect(resumo.desconto).toBe(12.5)
    expect(resumo.final).toBe(237.5)
    expect(resumo.teveDesconto).toBe(true)
  })

  it('formatBRL e formatDateTime formatam valores esperados', () => {
    expect(formatBRL(237.5)).toMatch(/R\$\s*237,50/)
    expect(formatBRL(null)).toMatch(/R\$\s*0,00/)
    expect(formatDateTime(null)).toBe('Agora')
    expect(formatDateTime('2026-11-15T17:30:00Z')).toMatch(/\d{2}\/\d{2}\/\d{4}/)
  })

  it('cliente Axios configura baseURL, withCredentials e header JSON', () => {
    expect(api.defaults.baseURL).toBe('http://localhost:8000')
    expect(api.defaults.withCredentials).toBe(true)
    expect(api.defaults.headers['Content-Type']).toBe('application/json')
  })
})

import assert from 'node:assert/strict'
import test from 'node:test'
import {
  calcularResumoCarrinho,
  formatBRL,
  formatDateTime,
} from './format.js'

test('carrinho vazio retorna zeros e falta R$ 200,01 para 5% OFF', () => {
  const resumo = calcularResumoCarrinho([])
  assert.deepEqual(resumo, {
    bruto: 0,
    desconto: 0,
    final: 0,
    faltam: 200.01,
    teveDesconto: false,
    progresso: 0,
  })
})

test('compra exata de R$ 200,00 nao aplica desconto e informa que falta R$ 0,01', () => {
  const resumo = calcularResumoCarrinho([{ preco: '100.00', quantidade: 2 }])
  assert.equal(resumo.bruto, 200)
  assert.equal(resumo.desconto, 0)
  assert.equal(resumo.final, 200)
  assert.equal(resumo.faltam, 0.01)
  assert.equal(resumo.teveDesconto, false)
  assert.equal(resumo.progresso, 100)
})

test('compra de R$ 200,01 ativa desconto de 5%', () => {
  const resumo = calcularResumoCarrinho([{ preco: '200.01', quantidade: 1 }])
  assert.equal(resumo.bruto, 200.01)
  assert.equal(resumo.desconto, 10)
  assert.equal(resumo.final, 190.01)
  assert.equal(resumo.faltam, 0)
  assert.equal(resumo.teveDesconto, true)
  assert.equal(resumo.progresso, 100)
})

test('compra de R$ 250,00 aplica R$ 12,50 de desconto e totaliza R$ 237,50', () => {
  const resumo = calcularResumoCarrinho([
    { preco: '89.90', quantidade: 2 },
    { preco: '70.20', quantidade: 1 },
  ])
  assert.equal(resumo.bruto, 250)
  assert.equal(resumo.desconto, 12.5)
  assert.equal(resumo.final, 237.5)
  assert.equal(resumo.teveDesconto, true)
})

test('formatBRL e formatDateTime formatam valores esperados', () => {
  assert.match(formatBRL(237.5), /R\$\s*237,50/)
  assert.equal(formatDateTime(null), 'Agora')
  assert.match(formatDateTime('2026-11-15T17:30:00Z'), /\d{2}\/\d{2}\/\d{4}/)
})

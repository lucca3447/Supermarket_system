const brlFormatter = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
})

const dateTimeFormatter = new Intl.DateTimeFormat('pt-BR', {
  dateStyle: 'short',
  timeStyle: 'short',
})

export const LIMITE_DESCONTO_CENTAVOS = 20000 // R$ 200,00

export function formatBRL(value) {
  return brlFormatter.format(Number(value || 0))
}

export function formatDateTime(value) {
  if (!value) return 'Agora'
  return dateTimeFormatter.format(new Date(value))
}

// Cálculo exato em centavos para espelhar a regra de negócio do back-end (> R$ 200,00)
export function calcularResumoCarrinho(carrinho) {
  const brutoCentavos = carrinho.reduce((acc, item) => {
    const unitCentavos = Math.round(Number(item.preco) * 100)
    return acc + unitCentavos * item.quantidade
  }, 0)

  const teveDesconto = brutoCentavos > LIMITE_DESCONTO_CENTAVOS
  const descontoCentavos = teveDesconto ? Math.round(brutoCentavos * 0.05) : 0
  const finalCentavos = brutoCentavos - descontoCentavos
  const faltamCentavos = teveDesconto ? 0 : LIMITE_DESCONTO_CENTAVOS + 1 - brutoCentavos
  const progresso = Math.min(
    100,
    Math.round((brutoCentavos / (LIMITE_DESCONTO_CENTAVOS + 1)) * 100),
  )

  return {
    bruto: brutoCentavos / 100,
    desconto: descontoCentavos / 100,
    final: finalCentavos / 100,
    faltam: faltamCentavos / 100,
    teveDesconto,
    progresso,
  }
}

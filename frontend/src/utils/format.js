const brlFormatter = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
})

const dateTimeFormatter = new Intl.DateTimeFormat('pt-BR', {
  dateStyle: 'short',
  timeStyle: 'short',
})

export function formatBRL(value) {
  return brlFormatter.format(Number(value || 0))
}

export function formatDateTime(value) {
  if (!value) return 'Agora'
  return dateTimeFormatter.format(new Date(value))
}

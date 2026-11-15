import { ReceiptText, Sparkles } from 'lucide-react'
import { formatBRL, formatDateTime } from '../utils/format'

export function HistoricoView({ vendas }) {
  const faturamentoTotal = vendas.reduce(
    (acc, venda) => acc + Number(venda.valor_final || 0),
    0,
  )
  const vendasComDesconto = vendas.filter((venda) => venda.teve_desconto).length

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-2xl border border-stone-200/90 bg-white p-4 shadow-xs">
          <p className="text-xs font-semibold text-stone-500">
            Total de vendas registradas
          </p>
          <p className="font-fiscal mt-1 text-2xl font-bold text-stone-900">
            {vendas.length}
          </p>
        </div>

        <div className="rounded-2xl border border-stone-200/90 bg-white p-4 shadow-xs">
          <p className="text-xs font-semibold text-stone-500">
            Faturamento líquido
          </p>
          <p className="font-fiscal mt-1 text-2xl font-bold text-mercado-800">
            {formatBRL(faturamentoTotal)}
          </p>
        </div>

        <div className="rounded-2xl border border-amber-300 bg-amber-50 p-4 shadow-xs">
          <p className="text-xs font-semibold text-oferta-950">
            Vendas com 5% OFF (&gt; R$ 200)
          </p>
          <p className="font-fiscal mt-1 text-2xl font-bold text-oferta-950">
            {vendasComDesconto}
          </p>
        </div>
      </div>

      {vendas.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-stone-300 bg-white/70 p-12 text-center">
          <ReceiptText className="mx-auto h-10 w-10 text-stone-400" />
          <p className="mt-3 font-medium text-stone-700">
            Nenhuma venda registrada ainda.
          </p>
          <p className="mt-1 text-sm text-stone-500">
            Finalize uma simulação na aba Caixa para ver o cupom gravado no banco aqui.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {vendas.map((venda) => (
            <article
              key={venda.id_venda}
              className="rounded-2xl border border-stone-200/90 bg-white p-5 shadow-xs"
            >
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-stone-100 pb-3">
                <div>
                  <h3 className="font-display text-base font-bold text-stone-900">
                    Venda #{String(venda.id_venda).padStart(3, '0')}
                  </h3>
                  <p className="text-xs text-stone-500">
                    {formatDateTime(venda.data_hora)}
                  </p>
                </div>

                {venda.teve_desconto ? (
                  <span className="inline-flex items-center gap-1 rounded-full border border-amber-300 bg-oferta-400 px-3 py-1 text-xs font-bold text-oferta-950">
                    <Sparkles className="h-3.5 w-3.5" />
                    5% OFF Aplicado (-{formatBRL(venda.desconto_aplicado)})
                  </span>
                ) : (
                  <span className="rounded-full bg-kraft-100 px-3 py-1 text-xs font-semibold text-stone-600">
                    Sem desconto (até R$ 200,00)
                  </span>
                )}
              </div>

              <ul className="mt-3 space-y-1.5 text-xs text-stone-700">
                {venda.itens.map((item) => (
                  <li
                    key={item.id_item}
                    className="flex items-center justify-between gap-2"
                  >
                    <span>
                      <span className="font-fiscal font-semibold text-stone-900">
                        {item.quantidade}x
                      </span>{' '}
                      {item.nome_produto}{' '}
                      <span className="font-fiscal text-stone-400">
                        ({formatBRL(item.preco_unitario)})
                      </span>
                    </span>
                    <span className="font-fiscal font-semibold text-stone-900">
                      {formatBRL(item.subtotal)}
                    </span>
                  </li>
                ))}
              </ul>

              <div className="font-fiscal mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-dashed border-stone-200 pt-3 text-xs">
                <div className="flex gap-4 text-stone-500">
                  <span>Bruto: {formatBRL(venda.valor_bruto)}</span>
                  <span>Desc: {formatBRL(venda.desconto_aplicado)}</span>
                </div>
                <div className="text-sm font-bold text-mercado-800">
                  Total: {formatBRL(venda.valor_final)}
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  )
}

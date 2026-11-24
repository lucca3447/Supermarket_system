import { useMemo, useState } from 'react'
import {
  CheckCircle2,
  Minus,
  Plus,
  Receipt,
  Search,
  ShoppingBasket,
  Sparkles,
  Trash2,
  X,
} from 'lucide-react'
import {
  calcularResumoCarrinho,
  formatBRL,
  formatDateTime,
} from '../utils/format'

export function CaixaView({
  produtos,
  carrinho,
  onAdicionar,
  onAlterarQuantidade,
  onRemover,
  onLimpar,
  onFinalizarCompra,
  finalizando,
  ultimaVenda,
  onFecharRecibo,
}) {
  const [busca, setBusca] = useState('')
  const [categoriaAtiva, setCategoriaAtiva] = useState('Todas')

  const categorias = useMemo(() => {
    const unicas = Array.from(new Set(produtos.map((p) => p.categoria))).sort()
    return ['Todas', ...unicas]
  }, [produtos])

  const produtosFiltrados = useMemo(() => {
    const termo = busca.trim().toLowerCase()
    return produtos.filter((produto) => {
      const bateCategoria =
        categoriaAtiva === 'Todas' || produto.categoria === categoriaAtiva
      const bateBusca =
        !termo ||
        produto.nome.toLowerCase().includes(termo) ||
        produto.categoria.toLowerCase().includes(termo)
      return bateCategoria && bateBusca
    })
  }, [produtos, busca, categoriaAtiva])

  const quantidadeNoCarrinho = useMemo(() => {
    const map = new Map()
    carrinho.forEach((item) => map.set(item.id_produto, item.quantidade))
    return map
  }, [carrinho])

  const resumo = useMemo(() => calcularResumoCarrinho(carrinho), [carrinho])

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-12 lg:items-start">
      {/* Coluna Esquerda: Gôndola de Produtos */}
      <section className="space-y-4 lg:col-span-7 xl:col-span-8">
        <div className="rounded-2xl border border-stone-200/90 bg-white p-4 shadow-xs sm:p-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="font-display text-xl font-bold text-stone-900">
                Gôndola de Produtos
              </h2>
              <p className="text-sm text-stone-600">
                Escolha os itens para simular a compra no caixa.
              </p>
            </div>
            <div className="relative w-full sm:w-64">
              <Search className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-stone-400" />
              <input
                type="search"
                maxLength={100}
                value={busca}
                onChange={(e) => setBusca(e.target.value)}
                placeholder="Buscar produto..."
                className="w-full rounded-xl border border-stone-300 bg-kraft-50/50 py-2 pr-3 pl-9 text-sm text-stone-900 outline-none transition focus:border-mercado-800 focus:bg-white focus:ring-2 focus:ring-mercado-800/15"
              />
            </div>
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            {categorias.map((categoria) => {
              const ativa = categoria === categoriaAtiva
              return (
                <button
                  key={categoria}
                  type="button"
                  onClick={() => setCategoriaAtiva(categoria)}
                  className={`cursor-pointer rounded-full px-3 py-1 text-xs font-semibold transition ${
                    ativa
                      ? 'bg-mercado-800 text-white'
                      : 'bg-kraft-100 text-stone-700 hover:bg-kraft-200'
                  }`}
                >
                  {categoria}
                </button>
              )
            })}
          </div>
        </div>

        {produtosFiltrados.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-stone-300 bg-white/70 p-10 text-center">
            <ShoppingBasket className="mx-auto h-10 w-10 text-stone-400" />
            <p className="mt-3 font-medium text-stone-700">
              Nenhum produto encontrado para esse filtro.
            </p>
            <p className="mt-1 text-sm text-stone-500">
              Limpe a busca ou cadastre um novo item na aba Produtos e Estoque.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2 xl:grid-cols-3">
            {produtosFiltrados.map((produto) => {
              const naCesta = quantidadeNoCarrinho.get(produto.id_produto) || 0
              const semEstoque = produto.quantidade_estoque <= 0
              const limiteAtingido = naCesta >= produto.quantidade_estoque
              const estoqueBaixo = produto.quantidade_estoque > 0 && produto.quantidade_estoque <= 5

              return (
                <article
                  key={produto.id_produto}
                  className={`flex flex-col justify-between rounded-2xl border bg-white p-4 transition ${
                    semEstoque
                      ? 'border-stone-200 opacity-65'
                      : 'border-stone-200/90 hover:border-mercado-700/50 hover:shadow-sm'
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-semibold text-stone-500">
                        {produto.categoria}
                      </span>
                      <span
                        className={`font-fiscal rounded-md px-2 py-0.5 text-xs font-semibold ${
                          semEstoque
                            ? 'bg-red-100 text-red-700'
                            : estoqueBaixo
                              ? 'bg-amber-100 text-amber-800'
                              : 'bg-emerald-50 text-mercado-800'
                        }`}
                      >
                        {semEstoque
                          ? 'Esgotado'
                          : `Est: ${produto.quantidade_estoque} ${produto.unidade}`}
                      </span>
                    </div>

                    <h3 className="mt-2.5 text-base font-semibold leading-snug text-stone-900">
                      {produto.nome}
                    </h3>
                  </div>

                  <div className="mt-4 flex items-center justify-between gap-2 pt-3 border-t border-stone-100">
                    <div className="inline-flex items-baseline gap-1 rounded-lg border border-amber-300 bg-oferta-400 px-2.5 py-1 text-oferta-950">
                      <span className="font-fiscal text-sm font-bold">
                        {formatBRL(produto.preco)}
                      </span>
                      <span className="text-[11px] font-semibold opacity-80">
                        /{produto.unidade}
                      </span>
                    </div>

                    <button
                      type="button"
                      disabled={semEstoque || limiteAtingido}
                      onClick={() => onAdicionar(produto)}
                      className="inline-flex cursor-pointer items-center gap-1.5 rounded-xl bg-mercado-800 px-3 py-2 text-xs font-semibold text-white transition hover:bg-mercado-900 disabled:cursor-not-allowed disabled:bg-stone-300 disabled:text-stone-600"
                    >
                      <Plus className="h-3.5 w-3.5" />
                      {semEstoque
                        ? 'Indisponível'
                        : limiteAtingido
                          ? `Max (${naCesta})`
                          : naCesta > 0
                            ? `Mais 1 (${naCesta})`
                            : 'Adicionar'}
                    </button>
                  </div>
                </article>
              )
            })}
          </div>
        )}
      </section>

      {/* Coluna Direita: Bobina de Cupom Fiscal */}
      <aside className="space-y-4 lg:col-span-5 xl:col-span-4 lg:sticky lg:top-6">
        {ultimaVenda && (
          <div className="rounded-2xl border border-emerald-300 bg-emerald-50 p-4 text-emerald-950 shadow-xs">
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-700" />
                <div>
                  <p className="text-sm font-bold">
                    Venda #{String(ultimaVenda.id_venda).padStart(3, '0')} confirmada!
                  </p>
                  <p className="text-xs text-emerald-800">
                    {formatDateTime(ultimaVenda.data_hora)} · Estoque atualizado
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={onFecharRecibo}
                aria-label="Fechar comprovante"
                className="cursor-pointer rounded-lg p-1 text-emerald-700 hover:bg-emerald-100"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="font-fiscal mt-3 space-y-1 border-t border-emerald-200 pt-2 text-xs">
              <div className="flex justify-between">
                <span>Valor bruto</span>
                <span>{formatBRL(ultimaVenda.valor_bruto)}</span>
              </div>
              <div className="flex justify-between">
                <span>Desconto (5% &gt; R$ 200)</span>
                <span>
                  {ultimaVenda.teve_desconto
                    ? `-${formatBRL(ultimaVenda.desconto_aplicado)}`
                    : 'R$ 0,00'}
                </span>
              </div>
              <div className="flex justify-between text-sm font-bold text-emerald-950">
                <span>Total pago</span>
                <span>{formatBRL(ultimaVenda.valor_final)}</span>
              </div>
            </div>
          </div>
        )}

        <div className="drop-shadow-sm">
          <div className="receipt-zig-top" />
          <div className="border-x border-stone-300/80 bg-bobina px-5 py-4">
            <div className="border-b border-dashed border-stone-300 pb-3 text-center">
              <div className="inline-flex items-center gap-1.5 text-mercado-800">
                <Receipt className="h-4 w-4" />
                <span className="font-fiscal text-xs font-bold tracking-wide">
                  CUPOM DE SIMULAÇÃO DE COMPRA
                </span>
              </div>
              <p className="mt-0.5 text-xs text-stone-500">
                Mercado do Lucca · Caixa 01
              </p>
            </div>

            {/* Medidor da regra de negócio (> R$ 200,00 = 5% OFF) */}
            <div
              className={`mt-4 rounded-xl border p-3 text-xs ${
                resumo.teveDesconto
                  ? 'border-emerald-300 bg-emerald-50 text-emerald-950'
                  : 'border-amber-300 bg-amber-50 text-oferta-950'
              }`}
            >
              <div className="flex items-center justify-between gap-2 font-semibold">
                <span className="inline-flex items-center gap-1.5">
                  <Sparkles className="h-3.5 w-3.5 shrink-0" />
                  {resumo.teveDesconto
                    ? 'Desconto de 5% ativado!'
                    : 'Regra: 5% OFF acima de R$ 200,00'}
                </span>
                <span className="font-fiscal">{resumo.progresso}%</span>
              </div>
              <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-white/90">
                <div
                  className={`h-full rounded-full transition-all duration-300 ${
                    resumo.teveDesconto ? 'bg-mercado-700' : 'bg-amber-500'
                  }`}
                  style={{ width: `${resumo.progresso}%` }}
                />
              </div>
              <p className="mt-1.5 leading-relaxed">
                {carrinho.length === 0
                  ? 'Adicione produtos para testar compras até R$ 200,00 e acima de R$ 200,00.'
                  : resumo.teveDesconto
                    ? `Compra superou R$ 200,00. Você economizou ${formatBRL(resumo.desconto)}.`
                    : `Falta ${formatBRL(resumo.faltam)} para superar R$ 200,00 e liberar 5% OFF.`}
              </p>
            </div>

            {/* Lista de Itens no Cupom */}
            <div className="mt-4">
              {carrinho.length === 0 ? (
                <div className="border-y border-dashed border-stone-300 py-8 text-center">
                  <p className="font-fiscal text-xs text-stone-500">
                    CESTA VAZIA — PASSE OS ITENS DA GÔNDOLA
                  </p>
                </div>
              ) : (
                <div className="max-h-72 space-y-2.5 overflow-y-auto border-y border-dashed border-stone-300 py-3 pr-1">
                  {carrinho.map((item, index) => {
                    const subtotalItem = Number(item.preco) * item.quantidade
                    const numeroSequencial = String(index + 1).padStart(3, '0')
                    const noLimite = item.quantidade >= item.quantidade_estoque

                    return (
                      <div
                        key={item.id_produto}
                        className="rounded-lg bg-white/80 p-2.5 ring-1 ring-stone-200/70"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <p className="truncate text-xs font-semibold text-stone-900">
                              <span className="font-fiscal mr-1.5 text-stone-400">
                                {numeroSequencial}
                              </span>
                              {item.nome}
                            </p>
                            <p className="font-fiscal mt-0.5 text-[11px] text-stone-500">
                              {item.quantidade} {item.unidade} x {formatBRL(item.preco)}
                            </p>
                          </div>
                          <span className="font-fiscal shrink-0 text-xs font-bold text-stone-900">
                            {formatBRL(subtotalItem)}
                          </span>
                        </div>

                        <div className="mt-2 flex items-center justify-between">
                          <div className="inline-flex items-center gap-1 rounded-lg border border-stone-200 bg-kraft-50 p-0.5">
                            <button
                              type="button"
                              onClick={() =>
                                onAlterarQuantidade(item.id_produto, item.quantidade - 1)
                              }
                              aria-label={`Diminuir quantidade de ${item.nome}`}
                              className="cursor-pointer rounded-md p-1 text-stone-700 hover:bg-white"
                            >
                              <Minus className="h-3 w-3" />
                            </button>
                            <span className="font-fiscal w-6 text-center text-xs font-semibold">
                              {item.quantidade}
                            </span>
                            <button
                              type="button"
                              disabled={noLimite}
                              onClick={() =>
                                onAlterarQuantidade(item.id_produto, item.quantidade + 1)
                              }
                              aria-label={`Aumentar quantidade de ${item.nome}`}
                              className="cursor-pointer rounded-md p-1 text-stone-700 hover:bg-white disabled:cursor-not-allowed disabled:opacity-40"
                            >
                              <Plus className="h-3 w-3" />
                            </button>
                          </div>

                          <button
                            type="button"
                            onClick={() => onRemover(item.id_produto)}
                            aria-label={`Remover ${item.nome}`}
                            className="cursor-pointer rounded-md p-1 text-stone-400 hover:bg-red-50 hover:text-red-600"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>

            {/* Totais Fiscais */}
            <div className="font-fiscal mt-4 space-y-1.5 text-xs">
              <div className="flex justify-between text-stone-600">
                <span>SUBTOTAL BRUTO</span>
                <span>{formatBRL(resumo.bruto)}</span>
              </div>
              <div
                className={`flex justify-between ${
                  resumo.teveDesconto ? 'font-semibold text-mercado-800' : 'text-stone-400'
                }`}
              >
                <span>DESCONTO (5% &gt; R$ 200)</span>
                <span>
                  {resumo.teveDesconto ? `-${formatBRL(resumo.desconto)}` : 'R$ 0,00'}
                </span>
              </div>
              <div className="flex items-baseline justify-between border-t border-stone-300 pt-2.5 text-base font-bold text-stone-950">
                <span>TOTAL A PAGAR</span>
                <span>{formatBRL(resumo.final)}</span>
              </div>
            </div>

            {/* Ações do Caixa */}
            <div className="mt-5 space-y-2">
              <button
                type="button"
                disabled={carrinho.length === 0 || finalizando}
                onClick={onFinalizarCompra}
                className="w-full cursor-pointer rounded-xl bg-mercado-800 px-4 py-3 text-sm font-semibold text-white shadow-xs transition hover:bg-mercado-900 disabled:cursor-not-allowed disabled:bg-stone-300 disabled:text-stone-600"
              >
                {finalizando ? 'Registrando venda...' : 'Finalizar Compra e Baixar Estoque'}
              </button>

              {carrinho.length > 0 && (
                <button
                  type="button"
                  disabled={finalizando}
                  onClick={onLimpar}
                  className="w-full cursor-pointer rounded-xl border border-stone-300 bg-white px-4 py-2 text-xs font-semibold text-stone-700 transition hover:bg-kraft-100"
                >
                  Esvaziar cesta
                </button>
              )}
            </div>
          </div>
          <div className="receipt-zig-bottom" />
        </div>
      </aside>
    </div>
  )
}

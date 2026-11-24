import { useMemo, useState } from 'react'
import { Minus, PackagePlus, Pencil, Plus, Search, Trash2 } from 'lucide-react'
import { formatBRL } from '../utils/format'
import { InsightEstoqueCard } from './InsightEstoqueCard'

const FORM_INICIAL = {
  nome: '',
  categoria: 'Mercearia',
  unidade: 'un',
  preco: '',
  quantidade_estoque: '',
}

const CATEGORIAS_SUGERIDAS = [
  'Mercearia',
  'Carnes',
  'Peixaria',
  'Grãos',
  'Laticínios',
  'Bebidas',
  'Limpeza',
  'Bomboniere',
  'Padaria',
  'Hortifruti',
]

export function EstoqueView({
  produtos,
  onSalvarProduto,
  onAjustarEstoque,
  onExcluirProduto,
  salvando,
}) {
  const [form, setForm] = useState(FORM_INICIAL)
  const [editId, setEditId] = useState(null)
  const [confirmDeleteId, setConfirmDeleteId] = useState(null)
  const [busca, setBusca] = useState('')
  const [erroForm, setErroForm] = useState('')

  const produtosFiltrados = useMemo(() => {
    const termo = busca.trim().toLowerCase()
    if (!termo) return produtos
    return produtos.filter(
      (p) =>
        p.nome.toLowerCase().includes(termo) ||
        p.categoria.toLowerCase().includes(termo),
    )
  }, [produtos, busca])

  function iniciarEdicao(produto) {
    setEditId(produto.id_produto)
    setConfirmDeleteId(null)
    setErroForm('')
    setForm({
      nome: produto.nome,
      categoria: produto.categoria,
      unidade: produto.unidade,
      preco: String(produto.preco),
      quantidade_estoque: String(produto.quantidade_estoque),
    })
  }

  function cancelarEdicao() {
    setEditId(null)
    setErroForm('')
    setForm(FORM_INICIAL)
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setErroForm('')

    const precoNum = Number(String(form.preco).replace(',', '.'))
    const estoqueNum = Number(form.quantidade_estoque)

    if (form.nome.trim().length < 2) {
      setErroForm('Informe um nome com pelo menos 2 caracteres.')
      return
    }
    if (form.nome.trim().length > 100) {
      setErroForm('O nome do produto deve ter no máximo 100 caracteres.')
      return
    }
    if (form.categoria.trim().length > 50) {
      setErroForm('A categoria deve ter no máximo 50 caracteres.')
      return
    }
    if (!Number.isFinite(precoNum) || precoNum <= 0) {
      setErroForm('O preço precisa ser maior que R$ 0,00.')
      return
    }
    if (precoNum > 99999999.99) {
      setErroForm('O preço deve ser menor que R$ 100.000.000,00.')
      return
    }
    if (!Number.isInteger(estoqueNum) || estoqueNum < 0 || estoqueNum > 2147483647) {
      setErroForm('A quantidade em estoque deve ser um número inteiro maior ou igual a zero.')
      return
    }

    const ok = await onSalvarProduto(
      {
        nome: form.nome.trim(),
        categoria: form.categoria.trim() || 'Mercearia',
        unidade: form.unidade.trim() || 'un',
        preco: precoNum.toFixed(2),
        quantidade_estoque: estoqueNum,
      },
      editId,
    )

    if (ok) {
      setEditId(null)
      setForm(FORM_INICIAL)
    }
  }

  return (
    <div>
      <InsightEstoqueCard
        produtos={produtos}
        onAjustarEstoque={onAjustarEstoque}
        salvando={salvando}
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12 lg:items-start">
      {/* Formulário CRUD */}
      <section className="rounded-2xl border border-stone-200/90 bg-white p-5 shadow-xs lg:col-span-4">
        <div className="flex items-center gap-2 text-mercado-800">
          <PackagePlus className="h-5 w-5" />
          <h2 className="font-display text-lg font-bold text-stone-900">
            {editId ? `Editar Produto #${editId}` : 'Cadastrar Produto'}
          </h2>
        </div>
        <p className="mt-1 text-xs text-stone-500">
          Salve novos itens ou atualize preços e quantidades no banco de dados.
        </p>

        <form onSubmit={handleSubmit} className="mt-4 space-y-3.5">
          <div>
            <label
              htmlFor="produto-nome"
              className="mb-1 block text-xs font-semibold text-stone-700"
            >
              Nome do produto
            </label>
            <input
              id="produto-nome"
              name="nome"
              type="text"
              required
              minLength={2}
              maxLength={100}
              value={form.nome}
              onChange={(e) => setForm({ ...form, nome: e.target.value })}
              placeholder="Ex: Café Especial 500g"
              className="w-full rounded-xl border border-stone-300 bg-white px-3.5 py-2.5 text-sm text-stone-900 outline-none focus:border-mercado-800 focus:ring-2 focus:ring-mercado-800/15"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label
                htmlFor="produto-categoria"
                className="mb-1 block text-xs font-semibold text-stone-700"
              >
                Categoria
              </label>
              <input
                id="produto-categoria"
                name="categoria"
                type="text"
                list="categorias-sugestao"
                required
                minLength={2}
                maxLength={50}
                value={form.categoria}
                onChange={(e) => setForm({ ...form, categoria: e.target.value })}
                className="w-full rounded-xl border border-stone-300 bg-white px-3.5 py-2.5 text-sm text-stone-900 outline-none focus:border-mercado-800 focus:ring-2 focus:ring-mercado-800/15"
              />
              <datalist id="categorias-sugestao">
                {CATEGORIAS_SUGERIDAS.map((cat) => (
                  <option key={cat} value={cat} />
                ))}
              </datalist>
            </div>

            <div>
              <label
                htmlFor="produto-unidade"
                className="mb-1 block text-xs font-semibold text-stone-700"
              >
                Unidade
              </label>
              <select
                id="produto-unidade"
                name="unidade"
                value={form.unidade}
                onChange={(e) => setForm({ ...form, unidade: e.target.value })}
                className="w-full rounded-xl border border-stone-300 bg-white px-3.5 py-2.5 text-sm text-stone-900 outline-none focus:border-mercado-800 focus:ring-2 focus:ring-mercado-800/15"
              >
                <option value="un">un (Unidade)</option>
                <option value="kg">kg (Quilo)</option>
                <option value="pct">pct (Pacote)</option>
                <option value="cx">cx (Caixa)</option>
                <option value="band">band (Bandeja)</option>
                <option value="L">L (Litro)</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label
                htmlFor="produto-preco"
                className="mb-1 block text-xs font-semibold text-stone-700"
              >
                Preço (R$)
              </label>
              <input
                id="produto-preco"
                name="preco"
                type="number"
                step="0.01"
                min="0.01"
                max="99999999.99"
                required
                value={form.preco}
                onChange={(e) => setForm({ ...form, preco: e.target.value })}
                placeholder="0.00"
                className="font-fiscal w-full rounded-xl border border-stone-300 bg-white px-3.5 py-2.5 text-sm text-stone-900 outline-none focus:border-mercado-800 focus:ring-2 focus:ring-mercado-800/15"
              />
            </div>

            <div>
              <label
                htmlFor="produto-estoque"
                className="mb-1 block text-xs font-semibold text-stone-700"
              >
                Estoque inicial
              </label>
              <input
                id="produto-estoque"
                name="quantidade_estoque"
                type="number"
                min="0"
                max="2147483647"
                step="1"
                required
                value={form.quantidade_estoque}
                onChange={(e) =>
                  setForm({ ...form, quantidade_estoque: e.target.value })
                }
                placeholder="0"
                className="font-fiscal w-full rounded-xl border border-stone-300 bg-white px-3.5 py-2.5 text-sm text-stone-900 outline-none focus:border-mercado-800 focus:ring-2 focus:ring-mercado-800/15"
              />
            </div>
          </div>

          {erroForm && (
            <p role="alert" className="rounded-xl bg-red-50 px-3 py-2 text-xs font-medium text-red-700">
              {erroForm}
            </p>
          )}

          <div className="flex flex-col gap-2 pt-1">
            <button
              type="submit"
              disabled={salvando}
              className="w-full cursor-pointer rounded-xl bg-mercado-800 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-mercado-900 disabled:opacity-60"
            >
              {salvando
                ? 'Salvando...'
                : editId
                  ? 'Salvar Alterações'
                  : 'Cadastrar Produto'}
            </button>

            {editId && (
              <button
                type="button"
                onClick={cancelarEdicao}
                className="w-full cursor-pointer rounded-xl border border-stone-300 bg-white px-4 py-2 text-xs font-semibold text-stone-700 hover:bg-kraft-100"
              >
                Cancelar edição
              </button>
            )}
          </div>
        </form>
      </section>

      {/* Tabela de Estoque */}
      <section className="rounded-2xl border border-stone-200/90 bg-white p-5 shadow-xs lg:col-span-8">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="font-display text-lg font-bold text-stone-900">
              Catálogo e Controle de Estoque
            </h2>
            <p className="text-xs text-stone-500">
              {produtos.length} produto(s) cadastrado(s). Ajuste rápido ou edite/remova itens.
            </p>
          </div>
          <div className="relative w-full sm:w-60">
            <Search className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-stone-400" />
            <input
              type="search"
              maxLength={100}
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              placeholder="Filtrar na tabela..."
              className="w-full rounded-xl border border-stone-300 bg-kraft-50/50 py-2 pr-3 pl-9 text-sm text-stone-900 outline-none focus:border-mercado-800 focus:bg-white"
            />
          </div>
        </div>

        <div className="mt-4 overflow-x-auto">
          <table className="w-full border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-stone-200 text-xs font-semibold text-stone-500">
                <th className="py-2.5 pr-3">Produto</th>
                <th className="px-3 py-2.5">Categoria</th>
                <th className="px-3 py-2.5 text-right">Preço</th>
                <th className="px-3 py-2.5 text-center">Estoque</th>
                <th className="py-2.5 pl-3 text-right">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {produtosFiltrados.map((produto) => {
                const emEdicao = editId === produto.id_produto
                const confirmandoExclusao = confirmDeleteId === produto.id_produto
                const baixo = produto.quantidade_estoque <= 5

                return (
                  <tr
                    key={produto.id_produto}
                    className={emEdicao ? 'bg-amber-50/70' : 'hover:bg-kraft-50/60'}
                  >
                    <td className="py-3 pr-3 font-medium text-stone-900">
                      {produto.nome}
                      <span className="font-fiscal ml-1.5 text-xs text-stone-400">
                        /{produto.unidade}
                      </span>
                    </td>
                    <td className="px-3 py-3 text-xs text-stone-600">
                      {produto.categoria}
                    </td>
                    <td className="font-fiscal px-3 py-3 text-right font-semibold text-stone-900">
                      {formatBRL(produto.preco)}
                    </td>
                    <td className="px-3 py-3">
                      <div className="flex items-center justify-center gap-1.5">
                        <button
                          type="button"
                          disabled={produto.quantidade_estoque <= 0 || salvando}
                          onClick={() => onAjustarEstoque(produto, -1)}
                          aria-label={`Reduzir estoque de ${produto.nome}`}
                          className="cursor-pointer rounded-md border border-stone-200 bg-white p-1 text-stone-600 hover:bg-kraft-100 disabled:cursor-not-allowed disabled:opacity-40"
                        >
                          <Minus className="h-3 w-3" />
                        </button>
                        <span
                          className={`font-fiscal min-w-10 rounded-md px-2 py-0.5 text-center text-xs font-bold ${
                            produto.quantidade_estoque === 0
                              ? 'bg-red-100 text-red-700'
                              : baixo
                                ? 'bg-amber-100 text-amber-800'
                                : 'bg-emerald-50 text-mercado-800'
                          }`}
                        >
                          {produto.quantidade_estoque}
                        </span>
                        <button
                          type="button"
                          disabled={salvando}
                          onClick={() => onAjustarEstoque(produto, 1)}
                          aria-label={`Aumentar estoque de ${produto.nome}`}
                          className="cursor-pointer rounded-md border border-stone-200 bg-white p-1 text-stone-600 hover:bg-kraft-100 disabled:opacity-40"
                        >
                          <Plus className="h-3 w-3" />
                        </button>
                      </div>
                    </td>
                    <td className="py-3 pl-3 text-right">
                      <div className="inline-flex items-center justify-end gap-1.5">
                        <button
                          type="button"
                          onClick={() => iniciarEdicao(produto)}
                          className="inline-flex cursor-pointer items-center gap-1 rounded-lg border border-stone-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-stone-700 hover:bg-kraft-100"
                        >
                          <Pencil className="h-3.5 w-3.5" />
                          Editar
                        </button>

                        {confirmandoExclusao ? (
                          <div className="inline-flex items-center gap-1">
                            <button
                              type="button"
                              onClick={async () => {
                                await onExcluirProduto(produto.id_produto)
                                setConfirmDeleteId(null)
                                if (editId === produto.id_produto) {
                                  cancelarEdicao()
                                }
                              }}
                              className="cursor-pointer rounded-lg bg-red-600 px-2.5 py-1.5 text-xs font-semibold text-white hover:bg-red-700"
                            >
                              Confirmar
                            </button>
                            <button
                              type="button"
                              onClick={() => setConfirmDeleteId(null)}
                              className="cursor-pointer rounded-lg border border-stone-200 bg-white px-2.5 py-1.5 text-xs text-stone-600 hover:bg-kraft-100"
                            >
                              Não
                            </button>
                          </div>
                        ) : (
                          <button
                            type="button"
                            onClick={() => setConfirmDeleteId(produto.id_produto)}
                            className="inline-flex cursor-pointer items-center gap-1 rounded-lg border border-red-200 bg-red-50 px-2.5 py-1.5 text-xs font-semibold text-red-700 hover:bg-red-100"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                            Excluir
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>

          {produtosFiltrados.length === 0 && (
            <p className="py-8 text-center text-sm text-stone-500">
              Nenhum produto encontrado.
            </p>
          )}
        </div>
      </section>
      </div>
    </div>
  )
}

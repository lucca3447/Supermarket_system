import { useCallback, useEffect, useState } from 'react'
import {
  AlertCircle,
  Boxes,
  History,
  ShoppingCart,
  Store,
} from 'lucide-react'
import { CaixaView } from './components/CaixaView'
import { EstoqueView } from './components/EstoqueView'
import { HistoricoView } from './components/HistoricoView'
import { api } from './services/api'

const ABAS = [
  { id: 'caixa', label: 'Caixa / Simulação', icon: ShoppingCart },
  { id: 'estoque', label: 'Produtos e Estoque', icon: Boxes },
  { id: 'historico', label: 'Histórico de Vendas', icon: History },
]

export default function App() {
  const [abaAtiva, setAbaAtiva] = useState('caixa')
  const [produtos, setProdutos] = useState([])
  const [vendas, setVendas] = useState([])
  const [carrinho, setCarrinho] = useState([])
  const [carregando, setCarregando] = useState(true)
  const [salvando, setSalvando] = useState(false)
  const [finalizando, setFinalizando] = useState(false)
  const [erro, setErro] = useState('')
  const [ultimaVenda, setUltimaVenda] = useState(null)

  const carregarDados = useCallback(async () => {
    setErro('')
    try {
      const [produtosRes, vendasRes] = await Promise.all([
        api.get('/produtos/'),
        api.get('/vendas/'),
      ])
      const listaProdutos = produtosRes.data
      setProdutos(listaProdutos)
      setVendas(vendasRes.data)

      // Mantém a cesta sincronizada caso estoque ou preço tenham mudado na aba de CRUD
      setCarrinho((atual) =>
        atual
          .map((item) => {
            const atualizado = listaProdutos.find(
              (p) => p.id_produto === item.id_produto,
            )
            if (!atualizado || atualizado.quantidade_estoque <= 0) return null
            return {
              ...atualizado,
              quantidade: Math.min(item.quantidade, atualizado.quantidade_estoque),
            }
          })
          .filter(Boolean),
      )
    } catch (requestError) {
      setErro(
        requestError.response?.data?.detail ||
          'Não foi possível conectar ao back-end FastAPI em http://127.0.0.1:8000.',
      )
    } finally {
      setCarregando(false)
    }
  }, [])

  useEffect(() => {
    carregarDados()
  }, [carregarDados])

  function adicionarAoCarrinho(produto) {
    setUltimaVenda(null)
    setErro('')
    setCarrinho((atual) => {
      const existente = atual.find((item) => item.id_produto === produto.id_produto)
      if (existente) {
        if (existente.quantidade >= produto.quantidade_estoque) return atual
        return atual.map((item) =>
          item.id_produto === produto.id_produto
            ? { ...item, quantidade: item.quantidade + 1 }
            : item,
        )
      }
      return [...atual, { ...produto, quantidade: 1 }]
    })
  }

  function alterarQuantidadeCarrinho(idProduto, novaQuantidade) {
    if (novaQuantidade <= 0) {
      removerDoCarrinho(idProduto)
      return
    }
    setCarrinho((atual) =>
      atual.map((item) => {
        if (item.id_produto !== idProduto) return item
        return {
          ...item,
          quantidade: Math.min(novaQuantidade, item.quantidade_estoque),
        }
      }),
    )
  }

  function removerDoCarrinho(idProduto) {
    setCarrinho((atual) => atual.filter((item) => item.id_produto !== idProduto))
  }

  async function finalizarCompra() {
    if (carrinho.length === 0) return
    setFinalizando(true)
    setErro('')

    try {
      const payload = {
        itens: carrinho.map((item) => ({
          id_produto: item.id_produto,
          quantidade: item.quantidade,
        })),
      }
      const res = await api.post('/vendas/', payload)
      setUltimaVenda(res.data)
      setCarrinho([])
      await carregarDados()
    } catch (requestError) {
      setErro(
        requestError.response?.data?.detail ||
          'Erro ao finalizar a compra. Verifique o estoque disponível.',
      )
    } finally {
      setFinalizando(false)
    }
  }

  async function salvarProduto(payload, editId) {
    setSalvando(true)
    setErro('')
    try {
      if (editId) {
        await api.put(`/produtos/${editId}`, payload)
      } else {
        await api.post('/produtos/', payload)
      }
      await carregarDados()
      return true
    } catch (requestError) {
      setErro(
        requestError.response?.data?.detail || 'Erro ao salvar produto no banco.',
      )
      return false
    } finally {
      setSalvando(false)
    }
  }

  async function ajustarEstoqueRapido(produto, delta) {
    const novoEstoque = Math.max(0, produto.quantidade_estoque + delta)
    setSalvando(true)
    setErro('')
    try {
      await api.put(`/produtos/${produto.id_produto}`, {
        nome: produto.nome,
        categoria: produto.categoria,
        unidade: produto.unidade,
        preco: produto.preco,
        quantidade_estoque: novoEstoque,
      })
      await carregarDados()
    } catch (requestError) {
      setErro(
        requestError.response?.data?.detail || 'Erro ao atualizar estoque.',
      )
    } finally {
      setSalvando(false)
    }
  }

  async function excluirProduto(idProduto) {
    setSalvando(true)
    setErro('')
    try {
      await api.delete(`/produtos/${idProduto}`)
      await carregarDados()
    } catch (requestError) {
      setErro(
        requestError.response?.data?.detail || 'Erro ao excluir produto.',
      )
    } finally {
      setSalvando(false)
    }
  }

  const totalItensCesta = carrinho.reduce((acc, item) => acc + item.quantidade, 0)

  return (
    <div className="min-h-screen bg-kraft-50">
      <header className="bg-mercado-800 text-white shadow-sm">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-4 sm:px-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-oferta-400 text-oferta-950 shadow-xs">
              <Store className="h-6 w-6" />
            </div>
            <div>
              <h1 className="font-display text-xl font-bold tracking-tight">
                Mercadinho Bom Preço
              </h1>
              <p className="text-xs text-emerald-100/90">
                Sistema de Caixa, Controle de Estoque e Desconto Automático (5% &gt; R$ 200)
              </p>
            </div>
          </div>

          <nav className="flex flex-wrap gap-2" aria-label="Navegação principal">
            {ABAS.map((aba) => {
              const Icone = aba.icon
              const ativa = abaAtiva === aba.id
              return (
                <button
                  key={aba.id}
                  type="button"
                  onClick={() => setAbaAtiva(aba.id)}
                  className={`inline-flex cursor-pointer items-center gap-2 rounded-xl px-3.5 py-2 text-xs font-semibold transition sm:text-sm ${
                    ativa
                      ? 'bg-oferta-400 text-oferta-950 shadow-xs'
                      : 'bg-mercado-900/60 text-emerald-50 hover:bg-mercado-900'
                  }`}
                >
                  <Icone className="h-4 w-4" />
                  <span>{aba.label}</span>
                  {aba.id === 'caixa' && totalItensCesta > 0 && (
                    <span className="font-fiscal rounded-full bg-mercado-800 px-1.5 py-0.5 text-[11px] text-white">
                      {totalItensCesta}
                    </span>
                  )}
                  {aba.id === 'historico' && vendas.length > 0 && (
                    <span className="font-fiscal rounded-full bg-white/20 px-1.5 py-0.5 text-[11px]">
                      {vendas.length}
                    </span>
                  )}
                </button>
              )
            })}
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
        {erro && (
          <div className="mb-5 flex items-center justify-between gap-3 rounded-2xl border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 shrink-0 text-red-600" />
              <span>{erro}</span>
            </div>
            <button
              type="button"
              onClick={carregarDados}
              className="cursor-pointer rounded-lg bg-red-600 px-3 py-1 text-xs font-semibold text-white hover:bg-red-700"
            >
              Tentar novamente
            </button>
          </div>
        )}

        {carregando ? (
          <div className="rounded-2xl border border-stone-200 bg-white p-12 text-center text-sm text-stone-600">
            Carregando catálogo e histórico de vendas...
          </div>
        ) : (
          <>
            {abaAtiva === 'caixa' && (
              <CaixaView
                produtos={produtos}
                carrinho={carrinho}
                onAdicionar={adicionarAoCarrinho}
                onAlterarQuantidade={alterarQuantidadeCarrinho}
                onRemover={removerDoCarrinho}
                onLimpar={() => setCarrinho([])}
                onFinalizarCompra={finalizarCompra}
                finalizando={finalizando}
                ultimaVenda={ultimaVenda}
                onFecharRecibo={() => setUltimaVenda(null)}
              />
            )}

            {abaAtiva === 'estoque' && (
              <EstoqueView
                produtos={produtos}
                onSalvarProduto={salvarProduto}
                onAjustarEstoque={ajustarEstoqueRapido}
                onExcluirProduto={excluirProduto}
                salvando={salvando}
              />
            )}

            {abaAtiva === 'historico' && <HistoricoView vendas={vendas} />}
          </>
        )}
      </main>
    </div>
  )
}

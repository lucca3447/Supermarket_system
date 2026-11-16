import { useCallback, useEffect, useState } from 'react'
import { NavLink, Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import {
  AlertCircle,
  Boxes,
  History,
  LogOut,
  ShoppingCart,
  Store,
} from 'lucide-react'
import { CaixaView } from './components/CaixaView'
import { EstoqueView } from './components/EstoqueView'
import { HistoricoView } from './components/HistoricoView'
import { LoginView } from './components/LoginView'
import { api, setOnUnauthorized } from './services/api'

const CARRINHO_STORAGE_KEY = 'carrinho_tde'
const SESSAO_HINT_KEY = 'sessao_ativa_tde'

const ABAS = [
  { id: 'caixa', path: '/caixa', label: 'Caixa / Simulação', icon: ShoppingCart, perfis: ['cliente', 'gerente'] },
  { id: 'estoque', path: '/estoque', label: 'Produtos e Estoque', icon: Boxes, perfis: ['gerente'] },
  { id: 'historico', path: '/historico', label: 'Histórico de Vendas', icon: History, perfis: ['gerente'] },
]

function lerCarrinhoSalvo() {
  try {
    const salvo = localStorage.getItem(CARRINHO_STORAGE_KEY)
    const parsed = salvo ? JSON.parse(salvo) : []
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

export default function App() {
  const navigate = useNavigate()
  const [usuario, setUsuario] = useState(null)
  const [verificandoSessao, setVerificandoSessao] = useState(true)
  const [produtos, setProdutos] = useState([])
  const [vendas, setVendas] = useState([])
  const [dadosIniciaisCarregados, setDadosIniciaisCarregados] = useState(false)
  const [carrinho, setCarrinho] = useState(lerCarrinhoSalvo)
  const [carregando, setCarregando] = useState(false)
  const [salvando, setSalvando] = useState(false)
  const [finalizando, setFinalizando] = useState(false)
  const [erro, setErro] = useState('')
  const [ultimaVenda, setUltimaVenda] = useState(null)

  useEffect(() => {
    try {
      localStorage.setItem(CARRINHO_STORAGE_KEY, JSON.stringify(carrinho))
    } catch {
      // Ignora erro de quota do navegador
    }
  }, [carrinho])

  const limparSessaoLocal = useCallback(() => {
    localStorage.removeItem(SESSAO_HINT_KEY)
    setUsuario(null)
    setProdutos([])
    setVendas([])
    setDadosIniciaisCarregados(false)
    setUltimaVenda(null)
    setErro('')
    navigate('/login', { replace: true })
  }, [navigate])

  useEffect(() => {
    setOnUnauthorized(limparSessaoLocal)
    return () => setOnUnauthorized(null)
  }, [limparSessaoLocal])

  useEffect(() => {
    let ativo = true
    const temHintSessao = localStorage.getItem(SESSAO_HINT_KEY) === '1'
    api
      .get('/auth/me', temHintSessao ? undefined : { _skipAuthRefresh: true })
      .then((res) => {
        if (ativo) {
          localStorage.setItem(SESSAO_HINT_KEY, '1')
          setUsuario(res.data)
        }
      })
      .catch(() => {
        if (ativo) {
          localStorage.removeItem(SESSAO_HINT_KEY)
          setUsuario(null)
        }
      })
      .finally(() => {
        if (ativo) setVerificandoSessao(false)
      })
    return () => {
      ativo = false
    }
  }, [])

  const carregarDados = useCallback(
    async ({ incluirVendas = true } = {}) => {
      if (!usuario) return
      setErro('')
      setCarregando(true)
      try {
        const ehGerente = usuario.perfil === 'gerente'
        const buscarVendas = ehGerente && incluirVendas
        const [produtosRes, vendasRes] = await Promise.all([
          api.get('/produtos/'),
          buscarVendas ? api.get('/vendas/') : Promise.resolve(null),
        ])
        const listaProdutos = produtosRes.data
        setProdutos(listaProdutos)
        if (vendasRes) {
          setVendas(vendasRes.data)
        }
        setDadosIniciaisCarregados(true)

        // Mantém a cesta salva sincronizada com preço e estoque reais do banco
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
            'Não foi possível conectar ao back-end FastAPI em http://localhost:8000.',
        )
      } finally {
        setCarregando(false)
      }
    },
    [usuario],
  )

  useEffect(() => {
    if (usuario) {
      carregarDados()
    }
  }, [usuario, carregarDados])

  function handleAutenticado(usuarioAutenticado) {
    localStorage.setItem(SESSAO_HINT_KEY, '1')
    setUsuario(usuarioAutenticado)
    navigate('/caixa', { replace: true })
  }

  async function handleLogout() {
    await api.post('/auth/logout').catch(() => {})
    setCarrinho([])
    localStorage.removeItem(CARRINHO_STORAGE_KEY)
    limparSessaoLocal()
  }

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
      await carregarDados({ incluirVendas: false })
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
    setSalvando(true)
    setErro('')
    try {
      await api.patch(`/produtos/${produto.id_produto}/estoque`, { delta })
      await carregarDados({ incluirVendas: false })
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
      await carregarDados({ incluirVendas: false })
    } catch (requestError) {
      setErro(
        requestError.response?.data?.detail || 'Erro ao excluir produto.',
      )
    } finally {
      setSalvando(false)
    }
  }

  if (verificandoSessao) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-kraft-50 text-sm text-stone-600">
        Verificando sessão...
      </div>
    )
  }

  if (!usuario) {
    return (
      <Routes>
        <Route
          path="/login"
          element={<LoginView onAutenticado={handleAutenticado} />}
        />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    )
  }

  const abasPermitidas = ABAS.filter((aba) => aba.perfis.includes(usuario.perfil))
  const totalItensCesta = carrinho.reduce((acc, item) => acc + item.quantidade, 0)
  const ehGerente = usuario.perfil === 'gerente'

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

          <div className="flex flex-wrap items-center justify-between gap-3">
            <nav className="flex flex-wrap gap-2" aria-label="Navegação principal">
              {abasPermitidas.map((aba) => {
                const Icone = aba.icon
                return (
                  <NavLink
                    key={aba.id}
                    to={aba.path}
                    className={({ isActive }) =>
                      `inline-flex items-center gap-2 rounded-xl px-3.5 py-2 text-xs font-semibold transition sm:text-sm ${
                        isActive
                          ? 'bg-oferta-400 text-oferta-950 shadow-xs'
                          : 'bg-mercado-900/60 text-emerald-50 hover:bg-mercado-900'
                      }`
                    }
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
                  </NavLink>
                )
              })}
            </nav>

            <div className="flex items-center gap-2 border-l border-emerald-700/70 pl-3">
              <div className="text-right">
                <p className="text-xs font-semibold text-white">{usuario.nome}</p>
                <p className="text-[10px] font-bold tracking-wider text-oferta-400 uppercase">
                  {ehGerente ? 'Gerente' : 'Cliente'}
                </p>
              </div>
              <button
                type="button"
                onClick={handleLogout}
                aria-label="Sair"
                className="inline-flex cursor-pointer items-center gap-1.5 rounded-xl bg-mercado-900/80 px-3 py-2 text-xs font-semibold text-emerald-50 hover:bg-mercado-900"
              >
                <LogOut className="h-3.5 w-3.5" />
                Sair
              </button>
            </div>
          </div>
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
              onClick={() => carregarDados()}
              className="cursor-pointer rounded-lg bg-red-600 px-3 py-1 text-xs font-semibold text-white hover:bg-red-700"
            >
              Tentar novamente
            </button>
          </div>
        )}

        {!dadosIniciaisCarregados && !erro ? (
          <div className="rounded-2xl border border-stone-200 bg-white p-12 text-center text-sm text-stone-600">
            Carregando catálogo e histórico de vendas...
          </div>
        ) : (
          <Routes>
            <Route
              path="/caixa"
              element={
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
              }
            />
            <Route
              path="/estoque"
              element={
                ehGerente ? (
                  <EstoqueView
                    produtos={produtos}
                    onSalvarProduto={salvarProduto}
                    onAjustarEstoque={ajustarEstoqueRapido}
                    onExcluirProduto={excluirProduto}
                    salvando={salvando}
                  />
                ) : (
                  <Navigate to="/caixa" replace />
                )
              }
            />
            <Route
              path="/historico"
              element={
                ehGerente ? (
                  <HistoricoView vendas={vendas} />
                ) : (
                  <Navigate to="/caixa" replace />
                )
              }
            />
            <Route path="/login" element={<Navigate to="/caixa" replace />} />
            <Route path="*" element={<Navigate to="/caixa" replace />} />
          </Routes>
        )}
      </main>
    </div>
  )
}

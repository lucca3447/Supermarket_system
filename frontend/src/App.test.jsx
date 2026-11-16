import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { api } from './services/api'

vi.mock('./services/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
  setOnUnauthorized: vi.fn(),
}))

const USUARIO_GERENTE = {
  id_usuario: 1,
  nome: 'Gerente do Mercado',
  login: 'gerente',
  perfil: 'gerente',
}

const USUARIO_CLIENTE = {
  id_usuario: 2,
  nome: 'Cliente Padrão',
  login: 'cliente',
  perfil: 'cliente',
}

const PRODUTOS_BASE = [
  {
    id_produto: 1,
    nome: 'Picanha Bovina',
    categoria: 'Carnes',
    unidade: 'kg',
    preco: '120.00',
    quantidade_estoque: 3,
  },
  {
    id_produto: 2,
    nome: 'Arroz Tipo 1',
    categoria: 'Grãos',
    unidade: 'pct',
    preco: '30.00',
    quantidade_estoque: 10,
  },
  {
    id_produto: 3,
    nome: 'Café Esgotado',
    categoria: 'Bebidas',
    unidade: 'pct',
    preco: '25.00',
    quantidade_estoque: 0,
  },
]

const VENDAS_BASE = [
  {
    id_venda: 1,
    data_hora: '2026-11-15T17:00:00Z',
    valor_bruto: '240.00',
    desconto_aplicado: '12.00',
    valor_final: '228.00',
    teve_desconto: true,
    itens: [
      {
        id_item: 1,
        id_produto: 1,
        nome_produto: 'Picanha Bovina',
        preco_unitario: '120.00',
        quantidade: 2,
        subtotal: '240.00',
      },
    ],
  },
  {
    id_venda: 2,
    data_hora: '2026-11-15T16:30:00Z',
    valor_bruto: '60.00',
    desconto_aplicado: '0.00',
    valor_final: '60.00',
    teve_desconto: false,
    itens: [
      {
        id_item: 2,
        id_produto: 2,
        nome_produto: 'Arroz Tipo 1',
        preco_unitario: '30.00',
        quantidade: 2,
        subtotal: '60.00',
      },
    ],
  },
]

function renderApp(rotaInicial = '/caixa') {
  return render(
    <MemoryRouter initialEntries={[rotaInicial]}>
      <App />
    </MemoryRouter>,
  )
}

function mockDadosIniciais(
  produtos = PRODUTOS_BASE,
  vendas = VENDAS_BASE,
  usuario = USUARIO_GERENTE,
) {
  api.get.mockImplementation((url) => {
    if (url === '/auth/me') return Promise.resolve({ data: usuario })
    if (url === '/produtos/') return Promise.resolve({ data: produtos })
    if (url === '/vendas/') return Promise.resolve({ data: vendas })
    return Promise.reject(new Error(`Rota não mockada: ${url}`))
  })
}

describe('Mercadinho Bom Preço — Fluxos completos com Auth e RBAC', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('autentica na tela /login (Demo Gerente, erro e registro de Cliente), aplica RBAC e faz logout', async () => {
    api.get.mockImplementation((url) => {
      if (url === '/auth/me') return Promise.reject({ response: { status: 401 } })
      if (url === '/produtos/') return Promise.resolve({ data: PRODUTOS_BASE })
      if (url === '/vendas/') return Promise.resolve({ data: VENDAS_BASE })
      return Promise.reject(new Error(`Rota não mockada: ${url}`))
    })

    renderApp('/estoque')
    expect(await screen.findByText('Entrar no sistema')).toBeInTheDocument()

    // Erro de credenciais no login
    api.post.mockRejectedValueOnce({ response: { data: { detail: 'Usuário ou senha incorretos.' } } })
    fireEvent.click(screen.getByRole('button', { name: /Demo Gerente/i }))
    expect(screen.getByLabelText('Usuário')).toHaveValue('gerente')
    fireEvent.click(screen.getByRole('button', { name: 'Entrar no sistema' }))
    expect(await screen.findByText('Usuário ou senha incorretos.')).toBeInTheDocument()

    // Cadastro de novo Cliente pela aba Criar conta
    fireEvent.click(screen.getByRole('button', { name: /Criar conta \(Cliente\)/i }))
    fireEvent.change(screen.getByLabelText('Nome completo'), { target: { value: 'Maria Silva' } })
    fireEvent.change(screen.getByLabelText('Usuário'), { target: { value: 'maria' } })
    fireEvent.change(screen.getByLabelText('Senha'), { target: { value: 'maria123' } })
    api.post.mockResolvedValueOnce({
      data: {
        access_token: 'tok',
        usuario: { id_usuario: 9, nome: 'Maria Silva', login: 'maria', perfil: 'cliente' },
      },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Cadastrar e entrar' }))

    expect(await screen.findByText('Maria Silva')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Produtos e Estoque/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Histórico de Vendas/i })).not.toBeInTheDocument()
    expect(api.get).not.toHaveBeenCalledWith('/vendas/')

    // Logout limpa sessão e volta para /login
    api.post.mockResolvedValueOnce({ data: { mensagem: 'ok' } })
    fireEvent.click(screen.getByRole('button', { name: 'Sair' }))
    expect(await screen.findByText('Entrar no sistema')).toBeInTheDocument()

    // Preenche Demo Cliente e autentica
    fireEvent.click(screen.getByRole('button', { name: /Demo Cliente/i }))
    expect(screen.getByLabelText('Usuário')).toHaveValue('cliente')
  })

  it('redireciona cliente que tenta acessar /estoque ou /historico diretamente na URL', async () => {
    mockDadosIniciais(PRODUTOS_BASE, VENDAS_BASE, USUARIO_CLIENTE)
    const { unmount } = renderApp('/estoque')
    expect(await screen.findByText('Gôndola de Produtos')).toBeInTheDocument()
    unmount()

    renderApp('/historico')
    expect(await screen.findByText('Gôndola de Produtos')).toBeInTheDocument()
  })

  it('mantém itens do carrinho após F5 via localStorage e sincroniza com estoque', async () => {
    localStorage.setItem(
      'carrinho_tde',
      JSON.stringify([{ ...PRODUTOS_BASE[0], quantidade: 5 }]),
    )
    mockDadosIniciais(PRODUTOS_BASE, VENDAS_BASE, USUARIO_GERENTE)

    renderApp('/caixa')
    await screen.findByText('Picanha Bovina')

    // Quantidade 5 salva no localStorage foi ajustada para o estoque real (3)
    expect(screen.getByRole('button', { name: /Max \(3\)/i })).toBeDisabled()
  })

  it('exibe erro ao falhar carregamento inicial e recupera ao tentar novamente', async () => {
    api.get.mockImplementation((url) => {
      if (url === '/auth/me') return Promise.resolve({ data: USUARIO_GERENTE })
      return Promise.reject({ response: { data: { detail: 'Servidor fora do ar.' } } })
    })
    renderApp('/caixa')

    expect(await screen.findByText('Servidor fora do ar.')).toBeInTheDocument()

    mockDadosIniciais()
    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))

    expect(await screen.findByText('Picanha Bovina')).toBeInTheDocument()
    expect(screen.getByText('Indisponível')).toBeDisabled()
  })

  it('filtra gôndola, manipula cesta, aplica 5% OFF e finaliza compra', async () => {
    let produtosAtuais = PRODUTOS_BASE.map((p) => ({ ...p }))
    let vendasAtuais = []

    api.get.mockImplementation((url) => {
      if (url === '/auth/me') return Promise.resolve({ data: USUARIO_GERENTE })
      if (url === '/produtos/') return Promise.resolve({ data: produtosAtuais })
      if (url === '/vendas/') return Promise.resolve({ data: vendasAtuais })
      return Promise.reject(new Error(`Rota desconhecida: ${url}`))
    })

    const vendaCriada = {
      id_venda: 10,
      data_hora: '2026-11-15T18:00:00Z',
      valor_bruto: '240.00',
      desconto_aplicado: '12.00',
      valor_final: '228.00',
      teve_desconto: true,
      itens: [
        {
          id_item: 1,
          id_produto: 1,
          nome_produto: 'Picanha Bovina',
          preco_unitario: '120.00',
          quantidade: 2,
          subtotal: '240.00',
        },
      ],
    }

    api.post.mockImplementationOnce((url) => {
      if (url === '/vendas/') {
        produtosAtuais = produtosAtuais.map((p) =>
          p.id_produto === 1 ? { ...p, quantidade_estoque: 1 } : p,
        )
        vendasAtuais = [vendaCriada]
        return Promise.resolve({ data: vendaCriada })
      }
      return Promise.reject(new Error('Erro'))
    })

    renderApp('/caixa')
    await screen.findByText('Picanha Bovina')

    // Filtra por categoria e busca sem resultado
    fireEvent.click(screen.getByRole('button', { name: 'Carnes' }))
    expect(screen.queryByText('Arroz Tipo 1')).not.toBeInTheDocument()

    const campoBusca = screen.getByPlaceholderText('Buscar produto...')
    fireEvent.change(campoBusca, { target: { value: 'inexistente' } })
    expect(screen.getByText(/Nenhum produto encontrado/i)).toBeInTheDocument()

    fireEvent.change(campoBusca, { target: { value: '' } })
    fireEvent.click(screen.getByRole('button', { name: 'Todas' }))

    // Adiciona Picanha (R$ 120) -> 2x = R$ 240 -> 5% OFF
    const cardPicanha = screen.getByText('Picanha Bovina').closest('article')
    fireEvent.click(within(cardPicanha).getByRole('button', { name: /Adicionar/i }))
    expect(screen.getByText(/Falta R\$\s*80,01 para superar R\$ 200,00/i)).toBeInTheDocument()

    fireEvent.click(within(cardPicanha).getByRole('button', { name: /Mais 1 \(1\)/i }))
    expect(screen.getByText('Desconto de 5% ativado!')).toBeInTheDocument()

    // Testa incrementar até o máximo (3) e decrementar no cupom
    fireEvent.click(screen.getByLabelText('Aumentar quantidade de Picanha Bovina'))
    expect(within(cardPicanha).getByRole('button', { name: /Max \(3\)/i })).toBeDisabled()
    fireEvent.click(screen.getByLabelText('Diminuir quantidade de Picanha Bovina'))

    // Testa adicionar e remover Arroz pelo botão '-' (quantidade -> 0) e pelo botão de lixeira
    const cardArroz = screen.getByText('Arroz Tipo 1').closest('article')
    fireEvent.click(within(cardArroz).getByRole('button', { name: /Adicionar/i }))
    fireEvent.click(screen.getByLabelText('Diminuir quantidade de Arroz Tipo 1'))
    expect(screen.queryByLabelText('Remover Arroz Tipo 1')).not.toBeInTheDocument()

    fireEvent.click(within(cardArroz).getByRole('button', { name: /Adicionar/i }))
    fireEvent.click(screen.getByLabelText('Remover Arroz Tipo 1'))
    expect(screen.queryByLabelText('Remover Arroz Tipo 1')).not.toBeInTheDocument()

    // Finaliza compra acima de R$ 200,00
    fireEvent.click(screen.getByRole('button', { name: 'Finalizar Compra e Baixar Estoque' }))

    expect(await screen.findByText(/Venda #010 confirmada!/i)).toBeInTheDocument()
    expect(api.post).toHaveBeenCalledWith('/vendas/', {
      itens: [{ id_produto: 1, quantidade: 2 }],
    })

    // Fecha o comprovante exibido
    fireEvent.click(screen.getByLabelText('Fechar comprovante'))
    expect(screen.queryByText(/Venda #010 confirmada!/i)).not.toBeInTheDocument()

    // Testa esvaziar cesta e falha ao finalizar venda + venda sem desconto
    fireEvent.click(within(cardArroz).getByRole('button', { name: /Adicionar/i }))
    fireEvent.click(screen.getByRole('button', { name: 'Esvaziar cesta' }))
    expect(screen.getByText(/CESTA VAZIA/i)).toBeInTheDocument()

    fireEvent.click(within(cardArroz).getByRole('button', { name: /Adicionar/i }))
    api.post.mockRejectedValueOnce({ response: { data: { detail: 'Estoque insuficiente!' } } })
    fireEvent.click(screen.getByRole('button', { name: 'Finalizar Compra e Baixar Estoque' }))
    expect(await screen.findByText('Estoque insuficiente!')).toBeInTheDocument()

    api.post.mockResolvedValueOnce({
      data: {
        id_venda: 11,
        data_hora: '2026-11-15T18:05:00Z',
        valor_bruto: '30.00',
        desconto_aplicado: '0.00',
        valor_final: '30.00',
        teve_desconto: false,
        itens: [],
      },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Finalizar Compra e Baixar Estoque' }))
    expect(await screen.findByText(/Venda #011 confirmada!/i)).toBeInTheDocument()
  })

  it('gerencia CRUD completo de produtos, ajustes rapidos de estoque e sincronizacao da cesta', async () => {
    let produtosAtuais = PRODUTOS_BASE.map((p) => ({ ...p }))
    api.get.mockImplementation((url) => {
      if (url === '/auth/me') return Promise.resolve({ data: USUARIO_GERENTE })
      if (url === '/produtos/') return Promise.resolve({ data: produtosAtuais })
      if (url === '/vendas/') return Promise.resolve({ data: VENDAS_BASE })
      return Promise.reject(new Error('Erro'))
    })

    renderApp('/caixa')
    await screen.findByText('Picanha Bovina')

    // Coloca 3 unidades de Picanha na cesta para testar clamp/remoção quando estoque mudar
    const cardPicanha = screen.getByText('Picanha Bovina').closest('article')
    fireEvent.click(within(cardPicanha).getByRole('button', { name: /Adicionar/i }))
    fireEvent.click(within(cardPicanha).getByRole('button', { name: /Mais 1/i }))
    fireEvent.click(within(cardPicanha).getByRole('button', { name: /Mais 1/i }))

    // Navega para rota /estoque
    fireEvent.click(screen.getByRole('link', { name: /Produtos e Estoque/i }))
    expect(screen.getByText('Catálogo e Controle de Estoque')).toBeInTheDocument()

    // Validações de formulário (nome curto, preço inválido, estoque inválido)
    const form = screen.getByRole('button', { name: 'Cadastrar Produto' }).closest('form')
    fireEvent.change(screen.getByPlaceholderText('Ex: Café Especial 500g'), { target: { value: 'A' } })
    fireEvent.submit(form)
    expect(screen.getByText('Informe um nome com pelo menos 2 caracteres.')).toBeInTheDocument()

    fireEvent.change(screen.getByPlaceholderText('Ex: Café Especial 500g'), { target: { value: 'Leite Integral' } })
    fireEvent.change(screen.getByDisplayValue('Mercearia'), { target: { value: 'Laticínios' } })
    fireEvent.change(screen.getByDisplayValue('un (Unidade)'), { target: { value: 'L' } })
    fireEvent.change(screen.getByPlaceholderText('0.00'), { target: { value: '0' } })
    fireEvent.submit(form)
    expect(screen.getByText('O preço precisa ser maior que R$ 0,00.')).toBeInTheDocument()

    fireEvent.change(screen.getByPlaceholderText('0.00'), { target: { value: '5.50' } })
    fireEvent.change(screen.getByPlaceholderText('0'), { target: { value: '-1' } })
    fireEvent.submit(form)
    expect(
      screen.getByText('A quantidade em estoque deve ser um número inteiro maior ou igual a zero.'),
    ).toBeInTheDocument()

    // Erro ao cadastrar na API e depois sucesso
    fireEvent.change(screen.getByPlaceholderText('0'), { target: { value: '15' } })
    api.post.mockRejectedValueOnce({ response: { data: { detail: 'Erro ao salvar produto.' } } })
    fireEvent.submit(form)
    expect(await screen.findByText('Erro ao salvar produto.')).toBeInTheDocument()

    api.post.mockImplementationOnce((_, payload) => {
      const novo = { ...payload, id_produto: 99 }
      produtosAtuais = [...produtosAtuais, novo]
      return Promise.resolve({ data: novo })
    })
    fireEvent.submit(form)
    await waitFor(() => expect(api.post).toHaveBeenCalledTimes(2))
    expect(await screen.findByText('Leite Integral')).toBeInTheDocument()

    // Ajuste rápido de estoque (-1 reduz Picanha de 3 para 2 e sincroniza cesta!)
    api.patch.mockImplementation((url, payload) => {
      const id = Number(url.split('/').slice(-2, -1)[0])
      let atualizado = null
      produtosAtuais = produtosAtuais.map((p) => {
        if (p.id_produto !== id) return p
        atualizado = { ...p, quantidade_estoque: Math.max(0, p.quantidade_estoque + payload.delta) }
        return atualizado
      })
      return Promise.resolve({ data: atualizado })
    })
    fireEvent.click(screen.getByLabelText('Reduzir estoque de Picanha Bovina'))
    await waitFor(() => expect(api.patch).toHaveBeenCalledWith('/produtos/1/estoque', { delta: -1 }))

    // Erro em ajuste rápido
    api.patch.mockRejectedValueOnce(new Error('Falha de rede'))
    fireEvent.click(screen.getByLabelText('Aumentar estoque de Picanha Bovina'))
    expect(await screen.findByText('Erro ao atualizar estoque.')).toBeInTheDocument()

    // Editar produto e cancelar edição
    const linhaArroz = screen.getByText('Arroz Tipo 1').closest('tr')
    fireEvent.click(within(linhaArroz).getByRole('button', { name: 'Editar' }))
    expect(screen.getByText('Editar Produto #2')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar edição' }))
    expect(screen.getByRole('heading', { name: 'Cadastrar Produto' })).toBeInTheDocument()

    // Editar Picanha e salvar
    api.put.mockImplementation((url, payload) => {
      const id = Number(url.split('/').pop())
      produtosAtuais = produtosAtuais.map((p) => (p.id_produto === id ? { ...p, ...payload } : p))
      return Promise.resolve({ data: { id_produto: id, ...payload } })
    })
    const linhaPicanha = screen.getByText('Picanha Bovina').closest('tr')
    fireEvent.click(within(linhaPicanha).getByRole('button', { name: 'Editar' }))
    fireEvent.change(screen.getByPlaceholderText('0.00'), { target: { value: '130.00' } })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar Alterações' }))
    await waitFor(() =>
      expect(screen.getByRole('heading', { name: 'Cadastrar Produto' })).toBeInTheDocument(),
    )

    // Filtro da tabela com resultado vazio
    const filtroTabela = screen.getByPlaceholderText('Filtrar na tabela...')
    fireEvent.change(filtroTabela, { target: { value: 'nada-aqui' } })
    expect(screen.getByText('Nenhum produto encontrado.')).toBeInTheDocument()
    fireEvent.change(filtroTabela, { target: { value: '' } })

    // Exclusão: abre edição da Picanha, cancela exclusão com "Não", depois confirma exclusão e remove da cesta
    fireEvent.click(within(screen.getByText('Picanha Bovina').closest('tr')).getByRole('button', { name: 'Editar' }))
    fireEvent.click(within(screen.getByText('Picanha Bovina').closest('tr')).getByRole('button', { name: 'Excluir' }))
    fireEvent.click(screen.getByRole('button', { name: 'Não' }))
    expect(screen.queryByRole('button', { name: 'Confirmar' })).not.toBeInTheDocument()

    // Erro na exclusão e depois sucesso
    api.delete.mockRejectedValueOnce(new Error('Erro'))
    fireEvent.click(within(screen.getByText('Picanha Bovina').closest('tr')).getByRole('button', { name: 'Excluir' }))
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar' }))
    expect(await screen.findByText('Erro ao excluir produto.')).toBeInTheDocument()

    api.delete.mockImplementationOnce((url) => {
      const id = Number(url.split('/').pop())
      produtosAtuais = produtosAtuais.filter((p) => p.id_produto !== id)
      return Promise.resolve({ data: { id_produto: id } })
    })
    fireEvent.click(within(screen.getByText('Picanha Bovina').closest('tr')).getByRole('button', { name: 'Excluir' }))
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar' }))

    await waitFor(() => expect(screen.queryByText('Picanha Bovina')).not.toBeInTheDocument())
    expect(screen.getByRole('heading', { name: 'Cadastrar Produto' })).toBeInTheDocument()
  })

  it('exibe historico de vendas com e sem desconto e estado vazio', async () => {
    mockDadosIniciais(PRODUTOS_BASE, [])
    const { unmount } = renderApp('/historico')
    expect(await screen.findByText('Nenhuma venda registrada ainda.')).toBeInTheDocument()
    unmount()

    mockDadosIniciais(PRODUTOS_BASE, VENDAS_BASE)
    renderApp('/caixa')
    await screen.findByText('Picanha Bovina')

    fireEvent.click(screen.getByRole('link', { name: /Histórico de Vendas/i }))
    expect(screen.getByText('Venda #001')).toBeInTheDocument()
    expect(screen.getByText(/5% OFF Aplicado/i)).toBeInTheDocument()
    expect(screen.getByText('Venda #002')).toBeInTheDocument()
    expect(screen.getByText('Sem desconto (até R$ 200,00)')).toBeInTheDocument()
  })

  it('gera insights de estoque (Gemini, fallback local, erro e reposição rápida)', async () => {
    let produtosAtuais = PRODUTOS_BASE.map((p) => ({ ...p }))

    api.get.mockImplementation((url) => {
      if (url === '/auth/me') return Promise.resolve({ data: USUARIO_GERENTE })
      if (url === '/produtos/') return Promise.resolve({ data: produtosAtuais })
      if (url === '/vendas/') return Promise.resolve({ data: VENDAS_BASE })
      if (url === '/insights/estoque') {
        return Promise.resolve({
          data: {
            origem: 'gemini',
            modelo: 'gemini-3.1-flash-lite',
            resumo_executivo: 'Repor café esgotado imediatamente.',
            recomendacoes: ['Repor Café Esgotado.', 'Destacar Picanha Bovina.'],
            alertas: [
              {
                id_produto: 3,
                nome: 'Café Esgotado',
                categoria: 'Bebidas',
                unidade: 'pct',
                estoque_atual: 0,
                nivel: 'critico',
                sugestao_reposicao: 15,
              },
              {
                id_produto: 1,
                nome: 'Picanha Bovina',
                categoria: 'Carnes',
                unidade: 'kg',
                estoque_atual: 3,
                nivel: 'atencao',
                sugestao_reposicao: 9,
              },
            ],
            metricas: {
              total_produtos: 3,
              itens_criticos: 1,
              itens_atencao: 1,
              total_vendas: 2,
              vendas_com_desconto: 1,
              faturamento_total: '288.00',
            },
          },
        })
      }
      return Promise.reject(new Error(`Rota não mockada: ${url}`))
    })

    api.patch.mockImplementation((url, payload) => {
      const id = Number(url.split('/').slice(-2, -1)[0])
      let atualizado = null
      produtosAtuais = produtosAtuais.map((p) => {
        if (p.id_produto !== id) return p
        atualizado = { ...p, quantidade_estoque: Math.max(0, p.quantidade_estoque + payload.delta) }
        return atualizado
      })
      return Promise.resolve({ data: atualizado })
    })

    renderApp('/estoque')
    expect(await screen.findByText('Consultor de Estoque (IA)')).toBeInTheDocument()

    // 1. Consulta com retorno Gemini AI e reposição rápida
    fireEvent.click(screen.getByRole('button', { name: /Gerar Insights/i }))
    expect(await screen.findByText('Gemini AI')).toBeInTheDocument()
    expect(screen.getByText('Repor café esgotado imediatamente.')).toBeInTheDocument()
    expect(screen.getByText('Repor Café Esgotado.')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Repor +15' }))
    await waitFor(() =>
      expect(api.patch).toHaveBeenCalledWith(
        '/produtos/3/estoque',
        { delta: 15 },
      ),
    )

    // 2. Consulta com fallback local e sem alertas
    api.get.mockImplementation((url) => {
      if (url === '/auth/me') return Promise.resolve({ data: USUARIO_GERENTE })
      if (url === '/produtos/') return Promise.resolve({ data: produtosAtuais })
      if (url === '/vendas/') return Promise.resolve({ data: VENDAS_BASE })
      if (url === '/insights/estoque') {
        return Promise.resolve({
          data: {
            origem: 'analise_local',
            modelo: null,
            resumo_executivo: 'Estoque saudável.',
            recomendacoes: ['Manter ritmo atual.'],
            alertas: [],
            metricas: {
              total_produtos: 3,
              itens_criticos: 0,
              itens_atencao: 0,
              total_vendas: 2,
              vendas_com_desconto: 1,
              faturamento_total: '288.00',
            },
          },
        })
      }
      return Promise.reject(new Error(`Rota não mockada: ${url}`))
    })

    fireEvent.click(screen.getByRole('button', { name: /Gerar Insights/i }))
    expect(await screen.findByText('Análise Local (Fallback)')).toBeInTheDocument()
    expect(
      screen.getByText('Nenhum item crítico ou com estoque baixo no momento.'),
    ).toBeInTheDocument()

    // 3. Erro na rota de insights
    api.get.mockImplementationOnce(() => Promise.reject(new Error('Falha')))
    fireEvent.click(screen.getByRole('button', { name: /Gerar Insights/i }))
    expect(
      await screen.findByText('Não foi possível gerar os insights de estoque agora.'),
    ).toBeInTheDocument()
  })
})

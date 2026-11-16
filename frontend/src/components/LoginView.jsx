import { useState } from 'react'
import { KeyRound, LogIn, ShieldCheck, Store, UserPlus } from 'lucide-react'
import { api } from '../services/api'

export function LoginView({ onAutenticado }) {
  const [modo, setModo] = useState('entrar')
  const [nome, setNome] = useState('')
  const [login, setLogin] = useState('')
  const [senha, setSenha] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [erro, setErro] = useState('')

  function alternarModo(novoModo) {
    setModo(novoModo)
    setErro('')
  }

  function preencherDemo(usuarioDemo, senhaDemo) {
    setModo('entrar')
    setLogin(usuarioDemo)
    setSenha(senhaDemo)
    setErro('')
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setErro('')
    setEnviando(true)

    try {
      const endpoint = modo === 'entrar' ? '/auth/login' : '/auth/registrar'
      const payload =
        modo === 'entrar' ? { login, senha } : { nome, login, senha }
      const res = await api.post(endpoint, payload)
      onAutenticado(res.data.usuario)
    } catch (requestError) {
      setErro(
        requestError.response?.data?.detail ||
          'Não foi possível autenticar. Verifique os dados informados.',
      )
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-kraft-50 px-4 py-8">
      <div className="w-full max-w-md rounded-2xl border border-stone-200/90 bg-white p-6 shadow-sm sm:p-8">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-oferta-400 text-oferta-950 shadow-xs">
            <Store className="h-6 w-6" />
          </div>
          <div>
            <h1 className="font-display text-xl font-bold text-stone-900">
              Mercado do Lucca
            </h1>
            <p className="text-xs text-stone-500">
              Acesse com seu perfil de Cliente ou Gerente
            </p>
          </div>
        </div>

        <div className="mt-6 grid grid-cols-2 gap-2 rounded-xl bg-kraft-100 p-1">
          <button
            type="button"
            onClick={() => alternarModo('entrar')}
            className={`inline-flex cursor-pointer items-center justify-center gap-1.5 rounded-lg py-2 text-xs font-semibold transition ${
              modo === 'entrar'
                ? 'bg-white text-mercado-800 shadow-xs'
                : 'text-stone-600 hover:text-stone-900'
            }`}
          >
            <LogIn className="h-3.5 w-3.5" />
            Entrar
          </button>
          <button
            type="button"
            onClick={() => alternarModo('registrar')}
            className={`inline-flex cursor-pointer items-center justify-center gap-1.5 rounded-lg py-2 text-xs font-semibold transition ${
              modo === 'registrar'
                ? 'bg-white text-mercado-800 shadow-xs'
                : 'text-stone-600 hover:text-stone-900'
            }`}
          >
            <UserPlus className="h-3.5 w-3.5" />
            Criar conta (Cliente)
          </button>
        </div>

        <form onSubmit={handleSubmit} className="mt-5 space-y-4">
          {modo === 'registrar' && (
            <div>
              <label
                htmlFor="auth-nome"
                className="mb-1 block text-xs font-semibold text-stone-700"
              >
                Nome completo
              </label>
              <input
                id="auth-nome"
                type="text"
                required
                minLength={2}
                value={nome}
                onChange={(e) => setNome(e.target.value)}
                placeholder="Ex: Maria Oliveira"
                className="w-full rounded-xl border border-stone-300 bg-white px-3.5 py-2.5 text-sm text-stone-900 outline-none focus:border-mercado-800 focus:ring-2 focus:ring-mercado-800/15"
              />
            </div>
          )}

          <div>
            <label
              htmlFor="auth-login"
              className="mb-1 block text-xs font-semibold text-stone-700"
            >
              Usuário
            </label>
            <input
              id="auth-login"
              type="text"
              required
              minLength={2}
              value={login}
              onChange={(e) => setLogin(e.target.value)}
              placeholder="Ex: gerente ou cliente"
              className="w-full rounded-xl border border-stone-300 bg-white px-3.5 py-2.5 text-sm text-stone-900 outline-none focus:border-mercado-800 focus:ring-2 focus:ring-mercado-800/15"
            />
          </div>

          <div>
            <label
              htmlFor="auth-senha"
              className="mb-1 block text-xs font-semibold text-stone-700"
            >
              Senha
            </label>
            <input
              id="auth-senha"
              type="password"
              required
              minLength={4}
              value={senha}
              onChange={(e) => setSenha(e.target.value)}
              placeholder="••••••"
              className="w-full rounded-xl border border-stone-300 bg-white px-3.5 py-2.5 text-sm text-stone-900 outline-none focus:border-mercado-800 focus:ring-2 focus:ring-mercado-800/15"
            />
          </div>

          {erro && (
            <p className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs font-medium text-red-700">
              {erro}
            </p>
          )}

          <button
            type="submit"
            disabled={enviando}
            className="w-full cursor-pointer rounded-xl bg-mercado-800 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-mercado-900 disabled:opacity-60"
          >
            {enviando
              ? 'Autenticando...'
              : modo === 'entrar'
                ? 'Entrar no sistema'
                : 'Cadastrar e entrar'}
          </button>
        </form>

        {modo === 'entrar' && (
          <div className="mt-6 border-t border-stone-100 pt-4">
            <p className="mb-2 flex items-center gap-1.5 text-[11px] font-semibold tracking-wide text-stone-500 uppercase">
              <KeyRound className="h-3.5 w-3.5" />
              Acesso rápido para demonstração
            </p>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => preencherDemo('gerente', 'gerente123')}
                className="inline-flex cursor-pointer items-center justify-center gap-1.5 rounded-xl border border-emerald-200 bg-emerald-50/70 px-3 py-2 text-xs font-semibold text-mercado-800 hover:bg-emerald-100"
              >
                <ShieldCheck className="h-3.5 w-3.5" />
                Demo Gerente
              </button>
              <button
                type="button"
                onClick={() => preencherDemo('cliente', 'cliente123')}
                className="inline-flex cursor-pointer items-center justify-center gap-1.5 rounded-xl border border-stone-200 bg-kraft-50 px-3 py-2 text-xs font-semibold text-stone-700 hover:bg-kraft-100"
              >
                Demo Cliente
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

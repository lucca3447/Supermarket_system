import { useState } from 'react'
import { AlertTriangle, RefreshCw, Sparkles } from 'lucide-react'
import { api } from '../services/api'
import { extrairMensagemErro, formatBRL } from '../utils/format'

export function InsightEstoqueCard({ produtos, onAjustarEstoque, salvando }) {
  const [insight, setInsight] = useState(null)
  const [carregando, setCarregando] = useState(false)
  const [erro, setErro] = useState('')

  async function gerarInsights() {
    setCarregando(true)
    setErro('')
    try {
      const res = await api.get('/insights/estoque')
      setInsight(res.data)
    } catch (requestError) {
      setErro(
        extrairMensagemErro(
          requestError,
          'Não foi possível gerar os insights de estoque agora.',
        ),
      )
    } finally {
      setCarregando(false)
    }
  }

  function handleReporAlerta(alerta) {
    const produtoAlvo = produtos.find((p) => p.id_produto === alerta.id_produto)
    if (!produtoAlvo) return
    onAjustarEstoque(produtoAlvo, alerta.sugestao_reposicao)
  }

  return (
    <section className="mb-6 rounded-2xl border border-stone-200/90 bg-white p-5 shadow-xs">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-oferta-400/25 text-mercado-800">
            <Sparkles className="h-5 w-5" />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="font-display text-lg font-bold text-stone-900">
                Consultor de Estoque (IA)
              </h2>
              {insight && (
                <span
                  className={`rounded-full px-2.5 py-0.5 text-[11px] font-bold ${
                    insight.origem === 'gemini'
                      ? 'bg-mercado-800 text-white'
                      : 'bg-oferta-400 text-oferta-950'
                  }`}
                >
                  {insight.origem === 'gemini'
                    ? 'Gemini AI'
                    : 'Análise Local (Fallback)'}
                </span>
              )}
            </div>
            <p className="text-xs text-stone-500">
              Analisa giro de vendas, risco de ruptura e impacto da regra de 5% OFF (&gt; R$ 200,00).
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={gerarInsights}
          disabled={carregando}
          className="inline-flex cursor-pointer items-center justify-center gap-2 rounded-xl bg-mercado-800 px-4 py-2.5 text-xs font-semibold text-white transition hover:bg-mercado-900 disabled:opacity-60 sm:text-sm"
        >
          <RefreshCw className={`h-4 w-4 ${carregando ? 'animate-spin' : ''}`} />
          <span>{carregando ? 'Analisando...' : 'Gerar Insights'}</span>
        </button>
      </div>

      {erro && (
        <p role="alert" className="mt-4 rounded-xl border border-red-200 bg-red-50 px-3.5 py-2.5 text-xs font-medium text-red-700">
          {erro}
        </p>
      )}

      {insight && (
        <div className="mt-4 space-y-4 border-t border-stone-100 pt-4">
          <div className="rounded-xl bg-kraft-50 p-3.5 text-sm text-stone-800">
            <p className="font-medium">{insight.resumo_executivo}</p>
            <p className="font-fiscal mt-1.5 text-xs text-stone-500">
              Vendas: {insight.metricas.total_vendas} · Com 5% OFF:{' '}
              {insight.metricas.vendas_com_desconto} · Faturamento:{' '}
              {formatBRL(insight.metricas.faturamento_total)}
            </p>
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
            <div className="space-y-2 lg:col-span-7">
              <h3 className="text-xs font-bold tracking-wide text-stone-500 uppercase">
                Recomendações
              </h3>
              <ul className="space-y-2">
                {insight.recomendacoes.map((rec, idx) => (
                  <li
                    key={idx}
                    className="flex items-start gap-2 rounded-xl border border-stone-200/70 bg-white px-3 py-2 text-xs text-stone-700 sm:text-sm"
                  >
                    <span className="font-fiscal mt-0.5 inline-flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-mercado-800/10 text-[10px] font-bold text-mercado-800">
                      {idx + 1}
                    </span>
                    <span>{rec}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="space-y-2 lg:col-span-5">
              <h3 className="text-xs font-bold tracking-wide text-stone-500 uppercase">
                Alertas de Reposição ({insight.alertas.length})
              </h3>
              {insight.alertas.length === 0 ? (
                <p className="rounded-xl border border-emerald-200 bg-emerald-50/70 px-3 py-2.5 text-xs font-medium text-mercado-800">
                  Nenhum item crítico ou com estoque baixo no momento.
                </p>
              ) : (
                <div className="space-y-2">
                  {insight.alertas.map((alerta) => {
                    const produtoExiste = produtos.some(
                      (p) => p.id_produto === alerta.id_produto,
                    )
                    return (
                      <div
                        key={alerta.id_produto}
                        className="flex items-center justify-between gap-2 rounded-xl border border-stone-200 bg-kraft-50/50 px-3 py-2"
                      >
                        <div className="min-w-0">
                          <div className="flex items-center gap-1.5">
                            <AlertTriangle
                              className={`h-3.5 w-3.5 shrink-0 ${
                                alerta.nivel === 'critico'
                                  ? 'text-red-600'
                                  : 'text-amber-600'
                              }`}
                            />
                            <p className="truncate text-xs font-semibold text-stone-900">
                              {alerta.nome}
                            </p>
                          </div>
                          <p className="font-fiscal text-[11px] text-stone-500">
                            Atual: {alerta.estoque_atual} {alerta.unidade} ·{' '}
                            {alerta.nivel === 'critico' ? 'Crítico' : 'Atenção'}
                          </p>
                        </div>

                        {produtoExiste && (
                          <button
                            type="button"
                            disabled={salvando}
                            onClick={() => handleReporAlerta(alerta)}
                            className="font-fiscal shrink-0 cursor-pointer rounded-lg bg-oferta-400 px-2.5 py-1.5 text-xs font-bold text-oferta-950 transition hover:bg-oferta-300 disabled:opacity-60"
                          >
                            Repor +{alerta.sugestao_reposicao}
                          </button>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </section>
  )
}

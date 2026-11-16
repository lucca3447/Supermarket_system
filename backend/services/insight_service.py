import json
from collections import defaultdict
from decimal import Decimal

import httpx
from sqlalchemy.orm import Session

from core.config import settings
from models.produto_model import Produto
from models.venda_model import Venda
from repositories.produto_repository import ProdutoRepository
from repositories.venda_repository import VendaRepository
from schemas.insight_schema import (
    AlertaEstoque,
    InsightEstoqueResponse,
    MetricasInsight,
)

LIMITE_ESTOQUE_BAIXO = 5
GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class InsightService:
    """Gera insights de estoque e vendas via Gemini AI com fallback analítico local."""

    def __init__(self, db: Session):
        self.produto_repo = ProdutoRepository(db)
        self.venda_repo = VendaRepository(db)

    def gerar_insights(self) -> InsightEstoqueResponse:
        produtos = self.produto_repo.listar()
        vendas = self.venda_repo.listar()
        diagnostico = self._coletar_diagnostico(produtos, vendas)

        parecer_gemini = self._consultar_gemini(diagnostico)
        if parecer_gemini:
            modelo_ativo = settings.GEMINI_MODEL.strip() or "gemini-3.1-flash-lite"
            return InsightEstoqueResponse(
                origem="gemini",
                modelo=modelo_ativo,
                resumo_executivo=parecer_gemini["resumo_executivo"],
                recomendacoes=parecer_gemini["recomendacoes"],
                alertas=diagnostico["alertas"],
                metricas=diagnostico["metricas"],
            )

        local = self._gerar_analise_local(diagnostico)
        return InsightEstoqueResponse(
            origem="analise_local",
            modelo=None,
            resumo_executivo=local["resumo_executivo"],
            recomendacoes=local["recomendacoes"],
            alertas=diagnostico["alertas"],
            metricas=diagnostico["metricas"],
        )

    def _coletar_diagnostico(
        self, produtos: list[Produto], vendas: list[Venda]
    ) -> dict:
        demanda_por_id: dict[int, int] = defaultdict(int)
        saida_por_nome: dict[str, int] = defaultdict(int)
        faturamento_total = Decimal("0.00")
        vendas_com_desconto = 0

        for venda in vendas:
            faturamento_total += Decimal(venda.valor_final)
            if venda.teve_desconto:
                vendas_com_desconto += 1
            for item in venda.itens:
                saida_por_nome[item.nome_produto] += item.quantidade
                if item.id_produto is not None:
                    demanda_por_id[item.id_produto] += item.quantidade

        alertas: list[AlertaEstoque] = []
        sem_giro: list[str] = []

        for produto in produtos:
            demanda = demanda_por_id.get(produto.id_produto, 0)
            estoque = produto.quantidade_estoque

            if estoque == 0:
                alertas.append(
                    AlertaEstoque(
                        id_produto=produto.id_produto,
                        nome=produto.nome,
                        categoria=produto.categoria,
                        unidade=produto.unidade,
                        estoque_atual=estoque,
                        nivel="critico",
                        sugestao_reposicao=max(15, demanda * 2),
                    )
                )
            elif estoque <= LIMITE_ESTOQUE_BAIXO or estoque < demanda:
                alvo = max(12, demanda * 2)
                alertas.append(
                    AlertaEstoque(
                        id_produto=produto.id_produto,
                        nome=produto.nome,
                        categoria=produto.categoria,
                        unidade=produto.unidade,
                        estoque_atual=estoque,
                        nivel="atencao",
                        sugestao_reposicao=max(5, alvo - estoque),
                    )
                )

            if demanda == 0 and estoque >= 15:
                sem_giro.append(produto.nome)

        alertas.sort(key=lambda a: (0 if a.nivel == "critico" else 1, a.estoque_atual, a.nome))

        top_vendidos = [
            {"nome": nome, "quantidade": qtd}
            for nome, qtd in sorted(saida_por_nome.items(), key=lambda par: (-par[1], par[0]))[:3]
        ]

        metricas = MetricasInsight(
            total_produtos=len(produtos),
            itens_criticos=sum(1 for a in alertas if a.nivel == "critico"),
            itens_atencao=sum(1 for a in alertas if a.nivel == "atencao"),
            total_vendas=len(vendas),
            vendas_com_desconto=vendas_com_desconto,
            faturamento_total=faturamento_total.quantize(Decimal("0.01")),
        )

        return {
            "metricas": metricas,
            "alertas": alertas,
            "top_vendidos": top_vendidos,
            "sem_giro": sem_giro[:3],
        }

    def _consultar_gemini(self, diagnostico: dict) -> dict | None:
        api_key = settings.GEMINI_API_KEY.strip()
        if not api_key:
            return None

        metricas: MetricasInsight = diagnostico["metricas"]
        alertas: list[AlertaEstoque] = diagnostico["alertas"]

        resumo_dados = {
            "metricas": {
                "total_produtos": metricas.total_produtos,
                "itens_criticos": metricas.itens_criticos,
                "itens_atencao": metricas.itens_atencao,
                "total_vendas": metricas.total_vendas,
                "vendas_com_desconto_5_pct": metricas.vendas_com_desconto,
                "faturamento_total_brl": str(metricas.faturamento_total),
            },
            "alertas": [
                {
                    "nome": a.nome,
                    "nivel": a.nivel,
                    "estoque_atual": a.estoque_atual,
                    "sugestao_reposicao": a.sugestao_reposicao,
                }
                for a in alertas[:6]
            ],
            "top_vendidos": diagnostico["top_vendidos"],
            "sem_giro": diagnostico["sem_giro"],
        }

        prompt = (
            "Você é um consultor especialista em gestão de supermercado. "
            "Analise o snapshot abaixo e retorne um JSON estrito com as chaves: "
            '"resumo_executivo" (1 a 2 frases objetivas em português do Brasil) e '
            '"recomendacoes" (lista com 3 ações curtas cobrindo reposição prioritária, '
            "giro de estoque e incentivo à regra de 5% de desconto para compras acima de R$ 200,00).\n"
            f"Dados: {json.dumps(resumo_dados, ensure_ascii=False)}"
        )

        url = GEMINI_ENDPOINT.format(
            model=settings.GEMINI_MODEL.strip() or "gemini-3.1-flash-lite"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"},
        }

        try:
            response = httpx.post(
                url,
                headers={"x-goog-api-key": api_key},
                json=payload,
                timeout=15.0,
            )
            response.raise_for_status()
            data = response.json()
            texto = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(texto)

            resumo = parsed.get("resumo_executivo")
            recs = parsed.get("recomendacoes")
            if (
                not isinstance(resumo, str)
                or not resumo.strip()
                or not isinstance(recs, list)
                or not recs
            ):
                return None

            recomendacoes_limpas = [str(item).strip() for item in recs if str(item).strip()][:4]
            if not recomendacoes_limpas:
                return None

            return {
                "resumo_executivo": resumo.strip(),
                "recomendacoes": recomendacoes_limpas,
            }
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            print(f"[AVISO] Gemini indisponível ({type(exc).__name__}). Usando análise local.")
            return None

    def _gerar_analise_local(self, diagnostico: dict) -> dict:
        metricas: MetricasInsight = diagnostico["metricas"]
        alertas: list[AlertaEstoque] = diagnostico["alertas"]
        top_vendidos: list[dict] = diagnostico["top_vendidos"]
        sem_giro: list[str] = diagnostico["sem_giro"]

        if metricas.itens_criticos > 0 or metricas.itens_atencao > 0:
            resumo = (
                f"Catálogo com {metricas.total_produtos} produto(s): "
                f"{metricas.itens_criticos} item(ns) esgotado(s) e "
                f"{metricas.itens_atencao} em atenção. "
                f"Faturamento acumulado em R$ {metricas.faturamento_total:.2f} "
                f"em {metricas.total_vendas} venda(s)."
            )
        else:
            resumo = (
                f"Estoque saudável nos {metricas.total_produtos} produto(s) cadastrados, "
                f"sem risco imediato de ruptura. Faturamento atual de "
                f"R$ {metricas.faturamento_total:.2f} em {metricas.total_vendas} venda(s)."
            )

        recomendacoes: list[str] = []

        if alertas:
            prioridade = alertas[0]
            recomendacoes.append(
                f"Priorize a reposição de {prioridade.nome} (+{prioridade.sugestao_reposicao} {prioridade.unidade}) para evitar perda de vendas."
            )
        else:
            recomendacoes.append(
                "Mantenha o monitoramento de giro antes de novas compras para preservar capital de giro."
            )

        if top_vendidos:
            lider = top_vendidos[0]
            recomendacoes.append(
                f"Destaque no caixa o campeão de saída '{lider['nome']}' ({lider['quantidade']} un. vendidas) como âncora para combos."
            )
        else:
            recomendacoes.append(
                "Registre novas vendas no Caixa para identificar os itens de maior saída e refinar a previsão de demanda."
            )

        if sem_giro:
            itens_parados = ", ".join(sem_giro[:2])
            recomendacoes.append(
                f"Monte kits com itens sem giro ({itens_parados}) para ajudar clientes a ultrapassarem R$ 200,00 e ativarem os 5% OFF."
            )
        else:
            recomendacoes.append(
                f"Conversão da regra de desconto: {metricas.vendas_com_desconto} de {metricas.total_vendas} venda(s) superaram R$ 200,00 com 5% OFF."
            )

        return {
            "resumo_executivo": resumo,
            "recomendacoes": recomendacoes,
        }

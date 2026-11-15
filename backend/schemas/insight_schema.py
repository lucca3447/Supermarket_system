from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class AlertaEstoque(BaseModel):
    id_produto: int
    nome: str
    categoria: str
    unidade: str
    estoque_atual: int
    nivel: Literal["critico", "atencao"]
    sugestao_reposicao: int


class MetricasInsight(BaseModel):
    total_produtos: int
    itens_criticos: int
    itens_atencao: int
    total_vendas: int
    vendas_com_desconto: int
    faturamento_total: Decimal


class InsightEstoqueResponse(BaseModel):
    origem: Literal["gemini", "analise_local"]
    modelo: str | None = None
    resumo_executivo: str
    recomendacoes: list[str]
    alertas: list[AlertaEstoque]
    metricas: MetricasInsight

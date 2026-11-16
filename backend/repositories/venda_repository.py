from datetime import datetime
from decimal import Decimal
from sqlalchemy import case, func
from sqlalchemy.orm import Session, selectinload

from models.venda_model import ItemVenda, Venda


class VendaRepository:
    def __init__(self, db: Session):
        self.db = db

    def listar(self, limit: int = 100, offset: int = 0) -> list[Venda]:
        return (
            self.db.query(Venda)
            .options(selectinload(Venda.itens))
            .order_by(Venda.id_venda.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def obter_resumo_insights(self, corte_demanda: datetime) -> dict:
        totais = self.db.query(
            func.count(Venda.id_venda),
            func.coalesce(func.sum(Venda.valor_final), 0),
            func.coalesce(
                func.sum(case((Venda.teve_desconto.is_(True), 1), else_=0)), 0
            ),
        ).one()

        top_rows = (
            self.db.query(
                ItemVenda.nome_produto,
                func.sum(ItemVenda.quantidade).label("total_qtd"),
            )
            .group_by(ItemVenda.nome_produto)
            .order_by(
                func.sum(ItemVenda.quantidade).desc(),
                ItemVenda.nome_produto.asc(),
            )
            .limit(3)
            .all()
        )

        demanda_rows = (
            self.db.query(
                ItemVenda.id_produto,
                func.sum(ItemVenda.quantidade),
            )
            .join(Venda, ItemVenda.id_venda == Venda.id_venda)
            .filter(
                ItemVenda.id_produto.isnot(None),
                Venda.data_hora >= corte_demanda,
            )
            .group_by(ItemVenda.id_produto)
            .all()
        )

        return {
            "total_vendas": int(totais[0] or 0),
            "faturamento_total": Decimal(str(totais[1] or 0)).quantize(
                Decimal("0.01")
            ),
            "vendas_com_desconto": int(totais[2] or 0),
            "top_vendidos": [
                {"nome": nome, "quantidade": int(qtd)} for nome, qtd in top_rows
            ],
            "demanda_por_id": {
                int(id_prod): int(qtd) for id_prod, qtd in demanda_rows
            },
        }

    def criar(self, venda: Venda) -> Venda:
        try:
            self.db.add(venda)
            self.db.commit()
            self.db.refresh(venda)
            return venda
        except Exception:
            self.db.rollback()
            raise

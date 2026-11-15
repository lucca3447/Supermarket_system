from sqlalchemy.orm import Session, joinedload

from models.venda_model import Venda


class VendaRepository:
    def __init__(self, db: Session):
        self.db = db

    def listar(self) -> list[Venda]:
        return (
            self.db.query(Venda)
            .options(joinedload(Venda.itens))
            .order_by(Venda.id_venda.desc())
            .all()
        )

    def criar(self, venda: Venda) -> Venda:
        try:
            self.db.add(venda)
            self.db.commit()
            self.db.refresh(venda)
            return venda
        except Exception:
            self.db.rollback()
            raise

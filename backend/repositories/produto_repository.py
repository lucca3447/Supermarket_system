from sqlalchemy import update
from sqlalchemy.orm import Session

from models.produto_model import Produto
from schemas.produto_schema import ProdutoCreate, ProdutoUpdate


class ProdutoRepository:
    def __init__(self, db: Session):
        self.db = db

    def listar(self) -> list[Produto]:
        return self.db.query(Produto).order_by(Produto.nome.asc()).all()

    def buscar_por_id(self, id_produto: int) -> Produto | None:
        return (
            self.db.query(Produto)
            .filter(Produto.id_produto == id_produto)
            .first()
        )

    def buscar_por_ids(self, ids: list[int]) -> list[Produto]:
        return (
            self.db.query(Produto)
            .filter(Produto.id_produto.in_(ids))
            .all()
        )

    def criar(self, payload: ProdutoCreate) -> Produto:
        novo_produto = Produto(
            nome=payload.nome.strip(),
            categoria=payload.categoria.strip(),
            unidade=payload.unidade.strip(),
            preco=payload.preco,
            quantidade_estoque=payload.quantidade_estoque,
        )
        self.db.add(novo_produto)
        self.db.commit()
        self.db.refresh(novo_produto)
        return novo_produto

    def atualizar(self, produto_existente: Produto, payload: ProdutoUpdate) -> Produto:
        produto_existente.nome = payload.nome.strip()
        produto_existente.categoria = payload.categoria.strip()
        produto_existente.unidade = payload.unidade.strip()
        produto_existente.preco = payload.preco
        produto_existente.quantidade_estoque = payload.quantidade_estoque
        self.db.commit()
        self.db.refresh(produto_existente)
        return produto_existente

    def deletar(self, produto: Produto) -> None:
        self.db.delete(produto)
        self.db.commit()

    def baixar_estoque_atomico(self, id_produto: int, quantidade: int) -> bool:
        stmt = (
            update(Produto)
            .where(
                Produto.id_produto == id_produto,
                Produto.quantidade_estoque >= quantidade,
            )
            .values(quantidade_estoque=Produto.quantidade_estoque - quantidade)
            .execution_options(synchronize_session="evaluate")
        )
        resultado = self.db.execute(stmt)
        return resultado.rowcount == 1

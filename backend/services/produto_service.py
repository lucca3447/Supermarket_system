from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models.produto_model import Produto
from repositories.produto_repository import ProdutoRepository
from schemas.produto_schema import ProdutoCreate, ProdutoUpdate


class ProdutoService:
    def __init__(self, db: Session):
        self.repository = ProdutoRepository(db)

    def listar(self) -> list[Produto]:
        return self.repository.listar()

    def buscar_por_id(self, id_produto: int) -> Produto:
        produto = self.repository.buscar_por_id(id_produto)
        if not produto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Produto não encontrado.",
            )
        return produto

    def criar(self, payload: ProdutoCreate) -> Produto:
        return self.repository.criar(payload)

    def atualizar(self, id_produto: int, payload: ProdutoUpdate) -> Produto:
        produto_existente = self.buscar_por_id(id_produto)
        return self.repository.atualizar(produto_existente, payload)

    def deletar(self, id_produto: int) -> dict:
        produto = self.buscar_por_id(id_produto)
        self.repository.deletar(produto)
        return {"mensagem": "Produto removido com sucesso.", "id_produto": id_produto}

    def ajustar_estoque(self, id_produto: int, delta: int) -> Produto:
        produto = self.repository.ajustar_estoque_atomico(id_produto, delta)
        if not produto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Produto não encontrado.",
            )
        return produto

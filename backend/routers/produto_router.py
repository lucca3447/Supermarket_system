from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from models.produto_model import Produto
from schemas.produto_schema import ProdutoCreate, ProdutoResponse, ProdutoUpdate

router = APIRouter(prefix="/produtos", tags=["Produtos"])


def _buscar_produto_ou_404(db: Session, id_produto: int) -> Produto:
    produto = db.query(Produto).filter(Produto.id_produto == id_produto).first()
    if not produto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado.",
        )
    return produto


@router.get("/", response_model=list[ProdutoResponse])
def listar_produtos(db: Session = Depends(get_db)):
    return db.query(Produto).order_by(Produto.nome.asc()).all()


@router.get("/{id_produto}", response_model=ProdutoResponse)
def buscar_produto(id_produto: int, db: Session = Depends(get_db)):
    return _buscar_produto_ou_404(db, id_produto)


@router.post("/", response_model=ProdutoResponse, status_code=status.HTTP_201_CREATED)
def criar_produto(payload: ProdutoCreate, db: Session = Depends(get_db)):
    novo_produto = Produto(
        nome=payload.nome.strip(),
        categoria=payload.categoria.strip(),
        unidade=payload.unidade.strip(),
        preco=payload.preco,
        quantidade_estoque=payload.quantidade_estoque,
    )
    db.add(novo_produto)
    db.commit()
    db.refresh(novo_produto)
    return novo_produto


@router.put("/{id_produto}", response_model=ProdutoResponse)
def atualizar_produto(id_produto: int, payload: ProdutoUpdate, db: Session = Depends(get_db)):
    produto = _buscar_produto_ou_404(db, id_produto)
    produto.nome = payload.nome.strip()
    produto.categoria = payload.categoria.strip()
    produto.unidade = payload.unidade.strip()
    produto.preco = payload.preco
    produto.quantidade_estoque = payload.quantidade_estoque
    db.commit()
    db.refresh(produto)
    return produto


@router.delete("/{id_produto}")
def deletar_produto(id_produto: int, db: Session = Depends(get_db)):
    produto = _buscar_produto_ou_404(db, id_produto)
    db.delete(produto)
    db.commit()
    return {"mensagem": "Produto removido com sucesso.", "id_produto": id_produto}

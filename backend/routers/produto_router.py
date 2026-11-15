from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from core.database import get_db
from schemas.produto_schema import ProdutoCreate, ProdutoResponse, ProdutoUpdate
from services.produto_service import ProdutoService

router = APIRouter(prefix="/produtos", tags=["Produtos"])


@router.get("/", response_model=list[ProdutoResponse])
def listar_produtos(db: Session = Depends(get_db)):
    service = ProdutoService(db)
    return service.listar()


@router.get("/{id_produto}", response_model=ProdutoResponse)
def buscar_produto(id_produto: int, db: Session = Depends(get_db)):
    service = ProdutoService(db)
    return service.buscar_por_id(id_produto)


@router.post("/", response_model=ProdutoResponse, status_code=status.HTTP_201_CREATED)
def criar_produto(payload: ProdutoCreate, db: Session = Depends(get_db)):
    service = ProdutoService(db)
    return service.criar(payload)


@router.put("/{id_produto}", response_model=ProdutoResponse)
def atualizar_produto(id_produto: int, payload: ProdutoUpdate, db: Session = Depends(get_db)):
    service = ProdutoService(db)
    return service.atualizar(id_produto, payload)


@router.delete("/{id_produto}")
def deletar_produto(id_produto: int, db: Session = Depends(get_db)):
    service = ProdutoService(db)
    return service.deletar(id_produto)

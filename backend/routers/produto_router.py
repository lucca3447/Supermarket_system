from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from core.auth_dependencies import get_current_user, require_gerente
from core.database import get_db
from models.usuario_model import Usuario
from schemas.produto_schema import (
    EstoqueAjusteRequest,
    ProdutoCreate,
    ProdutoResponse,
    ProdutoUpdate,
)
from services.produto_service import ProdutoService

router = APIRouter(prefix="/produtos", tags=["Produtos"])


@router.get("/", response_model=list[ProdutoResponse])
@router.get("", response_model=list[ProdutoResponse], include_in_schema=False)
def listar_produtos(
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    service = ProdutoService(db)
    return service.listar()


@router.get("/{id_produto}", response_model=ProdutoResponse)
def buscar_produto(
    id_produto: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    service = ProdutoService(db)
    return service.buscar_por_id(id_produto)


@router.post("/", response_model=ProdutoResponse, status_code=status.HTTP_201_CREATED)
@router.post(
    "",
    response_model=ProdutoResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def criar_produto(
    payload: ProdutoCreate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_gerente),
):
    service = ProdutoService(db)
    return service.criar(payload)


@router.put("/{id_produto}", response_model=ProdutoResponse)
def atualizar_produto(
    id_produto: int,
    payload: ProdutoUpdate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_gerente),
):
    service = ProdutoService(db)
    return service.atualizar(id_produto, payload)


@router.patch("/{id_produto}/estoque", response_model=ProdutoResponse)
def ajustar_estoque_produto(
    id_produto: int,
    payload: EstoqueAjusteRequest,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_gerente),
):
    service = ProdutoService(db)
    return service.ajustar_estoque(id_produto, payload.delta)


@router.delete("/{id_produto}")
def deletar_produto(
    id_produto: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_gerente),
):
    service = ProdutoService(db)
    return service.deletar(id_produto)

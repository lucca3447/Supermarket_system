from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from core.database import get_db
from schemas.venda_schema import VendaCreate, VendaResponse
from services.venda_service import VendaService

router = APIRouter(prefix="/vendas", tags=["Vendas"])


@router.get("/", response_model=list[VendaResponse])
def listar_vendas(db: Session = Depends(get_db)):
    service = VendaService(db)
    return service.listar()


@router.post("/", response_model=VendaResponse, status_code=status.HTTP_201_CREATED)
def registrar_venda(payload: VendaCreate, db: Session = Depends(get_db)):
    service = VendaService(db)
    return service.registrar_venda(payload)

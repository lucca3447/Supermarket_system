from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.auth_dependencies import require_gerente
from core.database import get_db
from models.usuario_model import Usuario
from schemas.insight_schema import InsightEstoqueResponse
from services.insight_service import InsightService

router = APIRouter(prefix="/insights", tags=["Insights de Estoque (IA)"])


@router.get("/estoque", response_model=InsightEstoqueResponse)
def obter_insights_estoque(
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_gerente),
):
    service = InsightService(db)
    return service.gerar_insights()

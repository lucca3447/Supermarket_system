from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.database import get_db
from schemas.insight_schema import InsightEstoqueResponse
from services.insight_service import InsightService

router = APIRouter(prefix="/insights", tags=["Insights de Estoque (IA)"])


@router.get("/estoque", response_model=InsightEstoqueResponse)
def obter_insights_estoque(db: Session = Depends(get_db)):
    service = InsightService(db)
    return service.gerar_insights()

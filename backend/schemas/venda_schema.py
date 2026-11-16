from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_serializer


class ItemCompraCreate(BaseModel):
    id_produto: int
    quantidade: int = Field(..., gt=0)


class VendaCreate(BaseModel):
    itens: list[ItemCompraCreate] = Field(..., min_length=1)


class ItemVendaResponse(BaseModel):
    id_item: int
    id_produto: Optional[int] = None
    nome_produto: str
    preco_unitario: Decimal
    quantidade: int
    subtotal: Decimal

    model_config = ConfigDict(from_attributes=True)


class VendaResponse(BaseModel):
    id_venda: int
    data_hora: datetime
    valor_bruto: Decimal
    desconto_aplicado: Decimal
    valor_final: Decimal
    teve_desconto: bool
    itens: list[ItemVendaResponse]

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("data_hora")
    def serializar_data_hora_utc(self, valor: datetime) -> str:
        aware = (
            valor.replace(tzinfo=timezone.utc)
            if valor.tzinfo is None
            else valor.astimezone(timezone.utc)
        )
        return aware.isoformat().replace("+00:00", "Z")

from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class ProdutoBase(BaseModel):
    nome: str = Field(..., min_length=2, max_length=100)
    categoria: str = Field(default="Mercearia", min_length=2, max_length=50)
    unidade: str = Field(default="un", min_length=1, max_length=15)
    preco: Decimal = Field(..., gt=0)
    quantidade_estoque: int = Field(default=0, ge=0)


class ProdutoCreate(ProdutoBase):
    pass


class ProdutoUpdate(ProdutoBase):
    pass


class ProdutoResponse(BaseModel):
    id_produto: int
    nome: str
    categoria: str
    unidade: str
    preco: Decimal
    quantidade_estoque: int

    model_config = ConfigDict(from_attributes=True)

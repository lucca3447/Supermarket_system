from sqlalchemy import Column, Integer, Numeric, String
from core.database import Base


class Produto(Base):
    __tablename__ = "produtos"

    id_produto = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nome = Column(String(100), nullable=False)
    categoria = Column(String(50), nullable=False, default="Mercearia")
    unidade = Column(String(15), nullable=False, default="un")
    preco = Column(Numeric(10, 2), nullable=False)
    quantidade_estoque = Column(Integer, nullable=False, default=0)

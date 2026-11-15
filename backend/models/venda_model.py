from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import relationship
from core.database import Base


class Venda(Base):
    __tablename__ = "vendas"

    id_venda = Column(Integer, primary_key=True, index=True, autoincrement=True)
    data_hora = Column(DateTime, server_default=func.now(), nullable=False)
    valor_bruto = Column(Numeric(10, 2), nullable=False)
    desconto_aplicado = Column(Numeric(10, 2), nullable=False, default=0)
    valor_final = Column(Numeric(10, 2), nullable=False)
    teve_desconto = Column(Boolean, nullable=False, default=False)

    itens = relationship("ItemVenda", back_populates="venda", cascade="all, delete-orphan")


class ItemVenda(Base):
    __tablename__ = "itens_venda"

    id_item = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_venda = Column(Integer, ForeignKey("vendas.id_venda", ondelete="CASCADE"), nullable=False)
    id_produto = Column(Integer, ForeignKey("produtos.id_produto", ondelete="SET NULL"), nullable=True)
    nome_produto = Column(String(100), nullable=False)
    preco_unitario = Column(Numeric(10, 2), nullable=False)
    quantidade = Column(Integer, nullable=False)
    subtotal = Column(Numeric(10, 2), nullable=False)

    venda = relationship("Venda", back_populates="itens")

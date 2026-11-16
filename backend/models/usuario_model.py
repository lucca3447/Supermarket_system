from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from core.database import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id_usuario = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nome = Column(String(100), nullable=False)
    login = Column(String(50), nullable=False, unique=True, index=True)
    senha_hash = Column(String(255), nullable=False)
    perfil = Column(String(20), nullable=False, default="cliente")

    refresh_tokens = relationship(
        "RefreshToken", back_populates="usuario", cascade="all, delete-orphan"
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id_token = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_usuario = Column(
        Integer,
        ForeignKey("usuarios.id_usuario", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, nullable=False, default=False)

    usuario = relationship("Usuario", back_populates="refresh_tokens")

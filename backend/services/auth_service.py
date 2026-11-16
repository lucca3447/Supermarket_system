from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from core.config import settings
from core.security import (
    criar_access_token,
    gerar_hash_senha,
    gerar_refresh_token,
    hash_token,
    verificar_senha,
)
from models.usuario_model import RefreshToken, Usuario
from repositories.usuario_repository import UsuarioRepository
from schemas.auth_schema import LoginRequest, RegistroRequest


def _utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AuthService:
    def __init__(self, db: Session):
        self.repo = UsuarioRepository(db)

    def autenticar(self, payload: LoginRequest) -> tuple[str, str, Usuario]:
        usuario = self.repo.buscar_por_login(payload.login)
        if not usuario or not verificar_senha(payload.senha, usuario.senha_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuário ou senha incorretos.",
            )
        return self._emitir_par_tokens(usuario)

    def registrar_cliente(self, payload: RegistroRequest) -> tuple[str, str, Usuario]:
        if self.repo.buscar_por_login(payload.login):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Este login já está em uso.",
            )

        novo_usuario = Usuario(
            nome=payload.nome,
            login=payload.login,
            senha_hash=gerar_hash_senha(payload.senha),
            perfil="cliente",
        )
        usuario = self.repo.criar(novo_usuario)
        return self._emitir_par_tokens(usuario)

    def rotacionar_refresh(self, refresh_token_bruto: str) -> tuple[str, str, Usuario]:
        registro = self.repo.buscar_refresh_por_hash(hash_token(refresh_token_bruto))
        if not registro or registro.revoked or registro.expires_at <= _utcnow_naive():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sessão expirada. Faça login novamente.",
            )

        usuario = self.repo.buscar_por_id(registro.id_usuario)
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuário não encontrado.",
            )

        self.repo.revogar_refresh_token(registro)
        return self._emitir_par_tokens(usuario)

    def revogar_refresh(self, refresh_token_bruto: str | None) -> None:
        if not refresh_token_bruto:
            return
        registro = self.repo.buscar_refresh_por_hash(hash_token(refresh_token_bruto))
        if registro and not registro.revoked:
            self.repo.revogar_refresh_token(registro)

    def _emitir_par_tokens(self, usuario: Usuario) -> tuple[str, str, Usuario]:
        access_token = criar_access_token(usuario.id_usuario, usuario.perfil)
        refresh_bruto, refresh_hash = gerar_refresh_token()
        expires_at = _utcnow_naive() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        self.repo.salvar_refresh_token(
            RefreshToken(
                id_usuario=usuario.id_usuario,
                token_hash=refresh_hash,
                expires_at=expires_at,
                revoked=False,
            )
        )
        return access_token, refresh_bruto, usuario

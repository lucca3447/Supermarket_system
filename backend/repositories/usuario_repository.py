from datetime import datetime

from sqlalchemy import delete, or_, update
from sqlalchemy.orm import Session

from models.usuario_model import RefreshToken, Usuario


class UsuarioRepository:
    def __init__(self, db: Session):
        self.db = db

    def buscar_por_id(self, id_usuario: int) -> Usuario | None:
        return (
            self.db.query(Usuario)
            .filter(Usuario.id_usuario == id_usuario)
            .first()
        )

    def buscar_por_login(self, login: str) -> Usuario | None:
        return (
            self.db.query(Usuario)
            .filter(Usuario.login == login)
            .first()
        )

    def criar(self, usuario: Usuario) -> Usuario:
        self.db.add(usuario)
        self.db.commit()
        self.db.refresh(usuario)
        return usuario

    def salvar_refresh_token(
        self, token: RefreshToken, commit: bool = True
    ) -> RefreshToken:
        self.db.add(token)
        if commit:
            self.db.commit()
            self.db.refresh(token)
        else:
            self.db.flush()
        return token

    def buscar_refresh_por_hash(self, token_hash: str) -> RefreshToken | None:
        return (
            self.db.query(RefreshToken)
            .filter(RefreshToken.token_hash == token_hash)
            .first()
        )

    def revogar_refresh_token(self, token: RefreshToken) -> None:
        token.revoked = True
        self.db.commit()

    def revogar_refresh_se_ativo(self, id_token: int) -> bool:
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.id_token == id_token,
                RefreshToken.revoked.is_(False),
            )
            .values(revoked=True)
            .execution_options(synchronize_session="evaluate")
        )
        return self.db.execute(stmt).rowcount == 1

    def limpar_refresh_tokens_inativos(
        self, id_usuario: int, agora: datetime, ignorar_id: int | None = None
    ) -> None:
        condicao_inativo = or_(
            RefreshToken.revoked.is_(True),
            RefreshToken.expires_at <= agora,
        )
        stmt = delete(RefreshToken).where(
            RefreshToken.id_usuario == id_usuario,
            condicao_inativo,
        )
        if ignorar_id is not None:
            stmt = stmt.where(RefreshToken.id_token != ignorar_id)
        self.db.execute(stmt)

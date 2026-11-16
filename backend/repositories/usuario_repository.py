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

    def salvar_refresh_token(self, token: RefreshToken) -> RefreshToken:
        self.db.add(token)
        self.db.commit()
        self.db.refresh(token)
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

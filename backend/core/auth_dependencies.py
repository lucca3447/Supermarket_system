from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import decodificar_token
from models.usuario_model import Usuario
from repositories.usuario_repository import UsuarioRepository

http_bearer = HTTPBearer(auto_error=False)


def _erro_nao_autorizado(detail: str = "Credenciais inválidas ou ausentes.") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(http_bearer),
    db: Session = Depends(get_db),
) -> Usuario:
    # Prioridade: cookie HttpOnly do navegador; fallback: Bearer token (Swagger/testes)
    token = request.cookies.get("access_token") or (
        credentials.credentials if credentials else None
    )
    if not token:
        raise _erro_nao_autorizado("Autenticação obrigatória.")

    payload = decodificar_token(token)
    if not payload or payload.get("type") != "access":
        raise _erro_nao_autorizado("Token inválido ou expirado.")

    sub = payload.get("sub")
    if not isinstance(sub, str) or not sub.isdigit():
        raise _erro_nao_autorizado("Token inválido.")

    usuario = UsuarioRepository(db).buscar_por_id(int(sub))
    if not usuario:
        raise _erro_nao_autorizado("Usuário não encontrado.")

    return usuario


def require_gerente(usuario: Usuario = Depends(get_current_user)) -> Usuario:
    if usuario.perfil != "gerente":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito ao perfil gerente.",
        )
    return usuario

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from core.auth_dependencies import get_current_user
from core.config import settings
from core.database import get_db
from models.usuario_model import Usuario
from schemas.auth_schema import (
    AuthResponse,
    LoginRequest,
    RegistroRequest,
    UsuarioResponse,
)
from services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Autenticação"])


def _definir_cookies_auth(
    response: Response, access_token: str, refresh_token: str
) -> None:
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.COOKIE_SECURE,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.COOKIE_SECURE,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/",
    )


def _limpar_cookies_auth(response: Response) -> None:
    response.delete_cookie(
        key="access_token",
        path="/",
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.COOKIE_SECURE,
    )
    response.delete_cookie(
        key="refresh_token",
        path="/",
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.COOKIE_SECURE,
    )


@router.post("/login", response_model=AuthResponse)
def login(
    payload: LoginRequest, response: Response, db: Session = Depends(get_db)
):
    access_token, refresh_token, usuario = AuthService(db).autenticar(payload)
    _definir_cookies_auth(response, access_token, refresh_token)
    return AuthResponse(access_token=access_token, usuario=usuario)


@router.post(
    "/registrar",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
)
def registrar_cliente(
    payload: RegistroRequest, response: Response, db: Session = Depends(get_db)
):
    access_token, refresh_token, usuario = AuthService(db).registrar_cliente(payload)
    _definir_cookies_auth(response, access_token, refresh_token)
    return AuthResponse(access_token=access_token, usuario=usuario)


@router.post("/refresh", response_model=AuthResponse)
def refresh(
    request: Request, response: Response, db: Session = Depends(get_db)
):
    refresh_token_cookie = request.cookies.get("refresh_token")
    if not refresh_token_cookie:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token ausente.",
        )

    access_token, novo_refresh, usuario = AuthService(db).rotacionar_refresh(
        refresh_token_cookie
    )
    _definir_cookies_auth(response, access_token, novo_refresh)
    return AuthResponse(access_token=access_token, usuario=usuario)


@router.post("/logout")
def logout(
    request: Request, response: Response, db: Session = Depends(get_db)
):
    AuthService(db).revogar_refresh(request.cookies.get("refresh_token"))
    _limpar_cookies_auth(response)
    return {"mensagem": "Sessão encerrada com sucesso."}


@router.get("/me", response_model=UsuarioResponse)
def me(usuario: Usuario = Depends(get_current_user)):
    return usuario

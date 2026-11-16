from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    login: str = Field(..., min_length=2, max_length=50)
    senha: str = Field(..., min_length=4, max_length=100)

    model_config = ConfigDict(str_strip_whitespace=True)


class RegistroRequest(BaseModel):
    nome: str = Field(..., min_length=2, max_length=100)
    login: str = Field(..., min_length=2, max_length=50)
    senha: str = Field(..., min_length=4, max_length=100)

    model_config = ConfigDict(str_strip_whitespace=True)


class UsuarioResponse(BaseModel):
    id_usuario: int
    nome: str
    login: str
    perfil: Literal["gerente", "cliente"]

    model_config = ConfigDict(from_attributes=True)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioResponse

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _CredenciaisBase(BaseModel):
    login: str = Field(..., min_length=2, max_length=50)
    senha: str = Field(..., min_length=4, max_length=72)

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("senha")
    @classmethod
    def validar_limite_bytes_bcrypt(cls, valor: str) -> str:
        if len(valor.encode("utf-8")) > 72:
            raise ValueError("A senha deve ter no máximo 72 bytes.")
        return valor


class LoginRequest(_CredenciaisBase):
    pass


class RegistroRequest(_CredenciaisBase):
    nome: str = Field(..., min_length=2, max_length=100)


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

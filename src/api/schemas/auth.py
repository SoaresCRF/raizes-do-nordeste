from typing import Annotated, Literal

from pydantic import StringConstraints

from src.api.schemas.base import EsquemaEntrada, EsquemaSaida
from src.api.schemas.campos import TAMANHO_MAXIMO_SENHA, Email
from src.domain.usuario.usuario import Perfil

TIPO_TOKEN = "Bearer"


class Credenciais(EsquemaEntrada):
    email: Email
    senha: Annotated[str, StringConstraints(min_length=1, max_length=TAMANHO_MAXIMO_SENHA)]


class UsuarioDaSessao(EsquemaSaida):
    id: int
    nome: str
    perfil: Perfil


class TokensEmitidos(EsquemaSaida):
    access_token: str
    token_type: Literal["Bearer"] = TIPO_TOKEN
    expires_in: int
    user: UsuarioDaSessao

from typing import Literal

from pydantic import Field, PostgresDsn, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

# O PyJWT recomenda chave de pelo menos 32 bytes para HS256.
TAMANHO_MINIMO_SEGREDO_JWT = 32


class Configuracao(BaseSettings):
    # extra="ignore": o mesmo .env alimenta o docker compose (BANCO_ADMIN_SENHA etc.).
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    porta: int = Field(gt=0, lt=65536)
    banco_url: PostgresDsn
    banco_url_teste: PostgresDsn | None = None
    jwt_segredo: str = Field(min_length=TAMANHO_MINIMO_SEGREDO_JWT)
    jwt_expiracao_minutos: int = Field(gt=0)
    gateway_timeout_segundos: float = Field(gt=0)
    nivel_log: Literal["DEBUG", "INFO", "WARNING", "ERROR"]


class ConfiguracaoInvalida(Exception):
    pass


def carregar_configuracao() -> Configuracao:
    try:
        return Configuracao()
    except ValidationError as erro:
        variaveis = ", ".join(str(detalhe["loc"][0]).upper() for detalhe in erro.errors())
        raise ConfiguracaoInvalida(
            f"Variáveis de ambiente ausentes ou inválidas: {variaveis}"
        ) from erro

from typing import Literal

from pydantic import Field, PostgresDsn, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

TAMANHO_MINIMO_SEGREDO_JWT = 32


class Configuracao(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", hide_input_in_errors=True
    )

    porta: int = Field(gt=0, lt=65536)
    banco_url: PostgresDsn = Field(repr=False)
    jwt_segredo: str = Field(min_length=TAMANHO_MINIMO_SEGREDO_JWT, repr=False)
    jwt_expiracao_minutos: int = Field(gt=0)
    nivel_log: Literal["DEBUG", "INFO", "WARNING", "ERROR"]


class ErroConfiguracao(Exception):
    pass


def carregar_configuracao() -> Configuracao:
    try:
        return Configuracao()
    except ValidationError as erro:
        variaveis = ", ".join(str(detalhe["loc"][0]).upper() for detalhe in erro.errors())
        raise ErroConfiguracao(
            f"Variáveis de ambiente ausentes ou inválidas: {variaveis}"
        ) from erro

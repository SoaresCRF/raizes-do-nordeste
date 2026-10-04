import pytest

from src.config.configuracao import TAMANHO_MINIMO_SEGREDO_JWT, Configuracao


@pytest.fixture
def configuracao_api() -> Configuracao:
    return Configuracao(
        porta=8000,
        banco_url="postgresql+psycopg://teste:teste@127.0.0.1:5432/inexistente",
        jwt_segredo="x" * TAMANHO_MINIMO_SEGREDO_JWT,
        jwt_expiracao_minutos=60,
        gateway_timeout_segundos=3,
        nivel_log="INFO",
    )

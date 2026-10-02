import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine

from src.config.configuracao import carregar_configuracao

TIMEOUT_CONEXAO_SEGUNDOS = 5


@pytest.fixture(scope="session")
def url_banco_teste() -> str:
    url = carregar_configuracao().banco_url_teste
    assert url is not None, "BANCO_URL_TESTE não definida no .env"
    return str(url)


@pytest.fixture(scope="session")
def configuracao_alembic(url_banco_teste):
    configuracao = Config("alembic.ini")
    configuracao.attributes["banco_url"] = url_banco_teste
    return configuracao


@pytest.fixture(scope="session")
def engine_teste(url_banco_teste, configuracao_alembic):
    command.upgrade(configuracao_alembic, "head")
    engine = create_engine(
        url_banco_teste, connect_args={"connect_timeout": TIMEOUT_CONEXAO_SEGUNDOS}
    )
    yield engine
    engine.dispose()


@pytest.fixture
def conexao_teste(engine_teste):
    with engine_teste.connect() as conexao:
        transacao = conexao.begin()
        yield conexao
        transacao.rollback()

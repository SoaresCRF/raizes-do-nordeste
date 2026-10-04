import uuid

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from src.config.configuracao import carregar_configuracao
from src.infrastructure.database.seeds.dados_iniciais import SENHA_DESENVOLVIMENTO, popular_banco
from src.infrastructure.database.tabelas import metadata
from src.infrastructure.seguranca.hash_senha import HashSenha
from src.main import criar_app

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


SENHA_CLIENTE_NOVO = "SenhaForte123"


@pytest.fixture(scope="module")
def banco_semeado(engine_teste):
    with engine_teste.begin() as conexao:
        popular_banco(conexao, HashSenha())
    yield engine_teste
    with engine_teste.begin() as conexao:
        conexao.execute(
            text(f"TRUNCATE TABLE {', '.join(metadata.tables)} RESTART IDENTITY CASCADE")
        )


@pytest.fixture
def cliente_http(configuracao_api, url_banco_teste, banco_semeado):
    app = criar_app(configuracao_api.model_copy(update={"banco_url": url_banco_teste}))
    with TestClient(app) as cliente:
        yield cliente


@pytest.fixture
def cliente_novo(cliente_http) -> dict:
    dados = {
        "nome": "Cliente de Teste",
        "email": f"teste-{uuid.uuid4().hex[:12]}@exemplo.com.br",
        "senha": SENHA_CLIENTE_NOVO,
        "consentimentoFidelidade": True,
    }
    resposta = cliente_http.post("/usuarios", json=dados)
    assert resposta.status_code == 201, resposta.text
    return dados | {"id": resposta.json()["id"]}


@pytest.fixture
def entrar(cliente_http):
    def entrar_como(email: str, senha: str = SENHA_DESENVOLVIMENTO) -> dict[str, str]:
        resposta = cliente_http.post("/auth/login", json={"email": email, "senha": senha})
        assert resposta.status_code == 200, resposta.text
        return {"Authorization": f"Bearer {resposta.json()['accessToken']}"}

    return entrar_como

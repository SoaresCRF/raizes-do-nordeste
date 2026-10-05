import uuid

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text, update

from src.config.configuracao import carregar_configuracao
from src.infrastructure.database.seeds.dados_iniciais import (
    DOMINIO_EMAIL,
    SENHA_DESENVOLVIMENTO,
    popular_banco,
)
from src.infrastructure.database.tabelas import estoque, metadata, pedido, usuario
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
EMAIL_CLIENTE = f"cliente@{DOMINIO_EMAIL}"
UNIDADE_DO_PEDIDO = 1
# Tapioca: saldo 100 em Recife no seed, folga para os pedidos de um módulo de testes.
PRODUTO_DO_PEDIDO = 1
# Café da manhã completo: R$ 49,90 no seed; três dão 149 pontos (RN18).
CAFE_COMPLETO = 5


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


@pytest.fixture
def entrar_como_cliente(entrar):
    def entrar_como(cliente: dict) -> dict[str, str]:
        return entrar(cliente["email"], cliente["senha"])

    return entrar_como


@pytest.fixture
def saldo_de_estoque(banco_semeado):
    def consultar(unidade_id: int, produto_id: int) -> int | None:
        with banco_semeado.connect() as conexao:
            return conexao.execute(
                select(estoque.c.quantidade).where(
                    estoque.c.unidade_id == unidade_id, estoque.c.produto_id == produto_id
                )
            ).scalar_one_or_none()

    return consultar


@pytest.fixture
def id_do_usuario(banco_semeado):
    def buscar(email: str) -> int:
        with banco_semeado.connect() as conexao:
            return conexao.execute(
                select(usuario.c.id).where(usuario.c.email == email)
            ).scalar_one()

    return buscar


@pytest.fixture
def fazer_pedido(cliente_http, entrar):
    def fazer(email: str = EMAIL_CLIENTE, senha: str = SENHA_DESENVOLVIMENTO, **alteracoes) -> dict:
        corpo = {
            "canalPedido": "APP",
            "unidadeId": UNIDADE_DO_PEDIDO,
            "itens": [{"produtoId": PRODUTO_DO_PEDIDO, "quantidade": 1}],
            "formaPagamento": "MOCK",
        } | alteracoes
        resposta = cliente_http.post("/pedidos", json=corpo, headers=entrar(email, senha))
        assert resposta.status_code == 201, resposta.text
        return resposta.json()

    return fazer


@pytest.fixture
def pagar_pedido(cliente_http):
    def pagar(pedido_id: int, headers: dict, resultado: str = "APROVADO") -> dict:
        resposta = cliente_http.post(
            "/pagamentos",
            json={"pedidoId": pedido_id},
            headers=headers | {"X-Simular-Resultado": resultado},
        )
        assert resposta.status_code == 201, resposta.text
        return resposta.json()

    return pagar


@pytest.fixture
def definir_status_do_pedido(banco_semeado):
    # Atalho pelo banco para os testes de status que não dependem do pagamento.
    def definir(pedido_id: int, status: str) -> None:
        with banco_semeado.begin() as conexao:
            conexao.execute(update(pedido).where(pedido.c.id == pedido_id).values(status=status))

    return definir


@pytest.fixture
def acumular_pontos(fazer_pedido, pagar_pedido, entrar):
    def acumular(cliente: dict, quantidade_cafes: int) -> int:
        criado = fazer_pedido(
            cliente["email"],
            cliente["senha"],
            itens=[{"produtoId": CAFE_COMPLETO, "quantidade": quantidade_cafes}],
        )
        pagar_pedido(criado["pedidoId"], entrar(cliente["email"], cliente["senha"]))
        return criado["pedidoId"]

    return acumular


@pytest.fixture
def saldo_de_pontos(cliente_http):
    def consultar(headers: dict) -> int:
        resposta = cliente_http.get("/fidelidade/saldo", headers=headers)
        assert resposta.status_code == 200, resposta.text
        return resposta.json()["saldoPontos"]

    return consultar

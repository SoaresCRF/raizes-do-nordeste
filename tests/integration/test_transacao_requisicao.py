import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, insert, select, text

from src.api.dependencias import ConexaoBanco
from src.domain.erros.erros import EstoqueInsuficiente
from src.domain.unidade.unidade import TipoUnidade
from src.infrastructure.database.tabelas import unidade
from src.main import criar_app

NOME_UNIDADE_TESTE = "Unidade do teste de transação"


@pytest.fixture
def cliente(configuracao_api, url_banco_teste, engine_teste):
    app = criar_app(configuracao_api.model_copy(update={"banco_url": url_banco_teste}))

    @app.post("/teste/unidades")
    def criar_unidade(conexao: ConexaoBanco, falhar: bool = False):
        conexao.execute(
            insert(unidade),
            {
                "nome": NOME_UNIDADE_TESTE,
                "cidade": "Recife",
                "uf": "PE",
                "regiao": "Nordeste",
                "tipo": TipoUnidade.FORMATO_REDUZIDO,
            },
        )
        if falhar:
            raise EstoqueInsuficiente("Falha simulada depois do insert")
        return {"criada": True}

    @app.get("/teste/fuso")
    def consultar_fuso(conexao: ConexaoBanco):
        return {"fuso": conexao.execute(text("SHOW TimeZone")).scalar_one()}

    with TestClient(app) as cliente:
        yield cliente
    with engine_teste.begin() as conexao:
        conexao.execute(delete(unidade).where(unidade.c.nome == NOME_UNIDADE_TESTE))


def _unidades_de_teste(engine) -> int:
    with engine.connect() as conexao:
        consulta = select(func.count()).where(unidade.c.nome == NOME_UNIDADE_TESTE)
        return conexao.execute(consulta).scalar_one()


def test_confirma_transacao_quando_a_rota_termina_sem_erro(cliente, engine_teste):
    resposta = cliente.post("/teste/unidades")

    assert resposta.status_code == 200
    assert _unidades_de_teste(engine_teste) == 1


def test_desfaz_transacao_quando_a_rota_levanta_erro(cliente, engine_teste):
    resposta = cliente.post("/teste/unidades?falhar=true")

    assert resposta.status_code == 409
    assert _unidades_de_teste(engine_teste) == 0


def test_sessao_do_banco_usa_utc(cliente):
    assert cliente.get("/teste/fuso").json() == {"fuso": "UTC"}

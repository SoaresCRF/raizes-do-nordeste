import pytest
from sqlalchemy import select

from src.domain.auditoria.auditoria import AcaoAuditoria
from src.infrastructure.database.repositorios.auditoria import RepositorioAuditoria
from src.infrastructure.database.tabelas import log_auditoria
from src.infrastructure.logging.logger import request_id_atual

REQUEST_ID = "3f2c9a4e-0000-4000-8000-000000000001"
ENTIDADE_ID = 42


@pytest.fixture
def requisicao_em_andamento():
    token = request_id_atual.set(REQUEST_ID)
    yield
    request_id_atual.reset(token)


def _registrar(conexao, **alteracoes) -> None:
    dados = {
        "usuario_id": None,
        "unidade_id": None,
        "acao": AcaoAuditoria.UNIDADE_CRIADA,
        "entidade": "Unidade",
        "entidade_id": ENTIDADE_ID,
        "dados_antes": None,
        "dados_depois": {"nome": "Unidade de Teste"},
    } | alteracoes
    RepositorioAuditoria(conexao).registrar(**dados)


def _ultimo_registro(conexao):
    return conexao.execute(select(log_auditoria).order_by(log_auditoria.c.id.desc())).first()


def test_grava_a_acao_com_o_request_id_da_requisicao(conexao_teste, requisicao_em_andamento):
    _registrar(conexao_teste)

    registro = _ultimo_registro(conexao_teste)
    assert registro.acao == "UNIDADE_CRIADA"
    assert registro.entidade == "Unidade"
    assert registro.entidade_id == ENTIDADE_ID
    assert registro.request_id == REQUEST_ID
    assert registro.created_at is not None


def test_guarda_antes_e_depois_como_json(conexao_teste):
    _registrar(conexao_teste, dados_antes={"preco": "18.90"}, dados_depois={"preco": "19.90"})

    registro = _ultimo_registro(conexao_teste)
    assert registro.dados_antes == {"preco": "18.90"}
    assert registro.dados_depois == {"preco": "19.90"}


def test_fora_de_requisicao_grava_request_id_nulo(conexao_teste):
    _registrar(conexao_teste)

    assert _ultimo_registro(conexao_teste).request_id is None

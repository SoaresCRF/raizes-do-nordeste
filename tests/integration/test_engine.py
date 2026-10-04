import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from src.infrastructure.database.conexao import criar_engine

VALOR_SIGILOSO = "valor-sigiloso-do-teste"


def test_erro_do_banco_nao_expoe_parametros_vinculados(url_banco_teste):
    engine = criar_engine(url_banco_teste)
    consulta_que_falha = text("select cast(:valor as text), 1 / 0")

    with pytest.raises(DBAPIError) as erro:
        with engine.connect() as conexao:
            conexao.execute(consulta_que_falha, {"valor": VALOR_SIGILOSO})
    engine.dispose()

    assert VALOR_SIGILOSO not in str(erro.value)

import pytest
from sqlalchemy import create_engine, text

from src.config.configuracao import carregar_configuracao

TIMEOUT_CONEXAO_SEGUNDOS = 5


@pytest.fixture(params=["banco_url", "banco_url_teste"])
def conexao(request):
    url = getattr(carregar_configuracao(), request.param)
    assert url is not None, f"{request.param.upper()} não definida no .env"
    engine = create_engine(str(url), connect_args={"connect_timeout": TIMEOUT_CONEXAO_SEGUNDOS})
    with engine.connect() as conexao_aberta:
        yield conexao_aberta
    engine.dispose()


def test_conecta_no_banco_configurado(conexao):
    assert conexao.execute(text("select 1")).scalar_one() == 1


def test_usuario_da_aplicacao_nao_e_superusuario(conexao):
    privilegios = conexao.execute(
        text(
            "select rolsuper, rolcreatedb, rolcreaterole from pg_roles where rolname = current_user"
        )
    ).one()

    assert tuple(privilegios) == (False, False, False)


def test_usuario_da_aplicacao_pode_criar_tabelas(conexao):
    assert conexao.execute(
        text("select has_schema_privilege(current_user, 'public', 'CREATE')")
    ).scalar_one()

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from sqlalchemy import inspect

from src.infrastructure.database.tabelas import metadata

TABELA_DE_VERSAO = "alembic_version"


def _tabelas_da_aplicacao(engine) -> set[str]:
    return set(inspect(engine).get_table_names()) - {TABELA_DE_VERSAO}


def test_banco_migrado_corresponde_as_tabelas_definidas(engine_teste):
    with engine_teste.connect() as conexao:
        diferencas = compare_metadata(MigrationContext.configure(conexao), metadata)

    assert diferencas == []


def test_rollback_completo_e_reaplicacao(engine_teste, configuracao_alembic):
    command.downgrade(configuracao_alembic, "base")
    assert _tabelas_da_aplicacao(engine_teste) == set()

    command.upgrade(configuracao_alembic, "head")
    assert _tabelas_da_aplicacao(engine_teste) == set(metadata.tables)

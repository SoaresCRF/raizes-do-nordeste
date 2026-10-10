import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from sqlalchemy import inspect

from src.infrastructure.database.tabelas import metadata

TABELA_DE_VERSAO = "alembic_version"

# Índices de desempenho do item 3.2 (RNF20).
INDICES_DE_DESEMPENHO = {
    "pedido": {
        ("ix_pedido_unidade_id_status", ("unidade_id", "status")),
        ("ix_pedido_canal_pedido", ("canal_pedido",)),
        ("ix_pedido_cliente_id", ("cliente_id",)),
    },
    "log_auditoria": {("ix_log_auditoria_entidade_entidade_id", ("entidade", "entidade_id"))},
    "movimentacao_estoque": {("ix_movimentacao_estoque_estoque_id", ("estoque_id",))},
}


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


@pytest.mark.parametrize("tabela", sorted(INDICES_DE_DESEMPENHO))
def test_indices_de_desempenho_existem_no_banco(engine_teste, tabela):
    indices = {
        (indice["name"], tuple(indice["column_names"]))
        for indice in inspect(engine_teste).get_indexes(tabela)
    }

    assert INDICES_DE_DESEMPENHO[tabela] <= indices

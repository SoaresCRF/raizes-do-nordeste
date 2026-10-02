from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from src.config.configuracao import carregar_configuracao
from src.infrastructure.database.tabelas import metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = metadata


def _url_do_banco() -> str:
    # Os testes passam a URL do banco de teste em config.attributes; a CLI usa BANCO_URL.
    return config.attributes.get("banco_url") or str(carregar_configuracao().banco_url)


def run_migrations_offline() -> None:
    context.configure(
        url=_url_do_banco(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(_url_do_banco(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from src.config import carregar_configuracao
from src.infrastructure.database.tabelas import metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = metadata


engine = create_engine(str(carregar_configuracao().banco_url), poolclass=pool.NullPool)
with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

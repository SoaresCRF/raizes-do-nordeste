from sqlalchemy import Engine, create_engine


def criar_engine(url: str) -> Engine:
    # Sessão em UTC: os timestamps voltam do banco em UTC e a API os devolve com "Z" (RNF24).
    # hide_parameters: erros do SQLAlchemy incluem os valores vinculados e iriam parar no log.
    return create_engine(url, connect_args={"options": "-c timezone=UTC"}, hide_parameters=True)

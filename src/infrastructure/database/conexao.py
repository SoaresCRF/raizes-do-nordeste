from sqlalchemy import Engine, create_engine

CONEXOES_MAXIMAS = 15


def criar_engine(url: str) -> Engine:
    return create_engine(
        url,
        connect_args={"options": "-c timezone=UTC"},
        hide_parameters=True,
        pool_size=CONEXOES_MAXIMAS,
        max_overflow=0,
    )

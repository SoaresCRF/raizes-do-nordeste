from sqlalchemy import create_engine

from src.config.configuracao import carregar_configuracao
from src.infrastructure.database.seeds.dados_iniciais import popular_banco
from src.infrastructure.seguranca.hash_senha import HashSenha


def main() -> None:
    engine = create_engine(str(carregar_configuracao().banco_url))
    with engine.begin() as conexao:
        popular_banco(conexao, HashSenha())
    engine.dispose()


if __name__ == "__main__":
    main()

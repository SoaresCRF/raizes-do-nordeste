from src.config.configuracao import carregar_configuracao
from src.infrastructure.database.conexao import criar_engine
from src.infrastructure.database.seeds.dados_iniciais import popular_banco


def main() -> None:
    engine = criar_engine(str(carregar_configuracao().banco_url))
    with engine.begin() as conexao:
        popular_banco(conexao)
    engine.dispose()


if __name__ == "__main__":
    main()

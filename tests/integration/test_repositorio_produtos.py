from datetime import date

import pytest

from src.infrastructure.database.repositorios.produtos import RepositorioProdutos

UNIDADE_RECIFE = 1
CANJICA = 7


@pytest.mark.parametrize(
    ("hoje", "aparece"),
    [
        (date(2026, 5, 31), False),
        (date(2026, 6, 1), True),
        (date(2026, 7, 31), True),
        (date(2026, 8, 1), False),
    ],
)
def test_produto_sazonal_aparece_so_dentro_do_periodo_inclusive(banco_semeado, hoje, aparece):
    with banco_semeado.connect() as conexao:
        itens = RepositorioProdutos(conexao).listar_cardapio(UNIDADE_RECIFE, hoje, 100, 0)

    assert (CANJICA in [item.produto_id for item in itens]) is aparece

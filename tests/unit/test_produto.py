from datetime import date

import pytest

from src.domain.erros.erros import DadosInvalidos, DetalheErro
from src.domain.produto.produto import validar_periodo

JUNHO = date(2026, 6, 1)
JULHO = date(2026, 7, 31)


@pytest.mark.parametrize(
    ("disponivel_de", "disponivel_ate"),
    [(None, None), (JUNHO, None), (None, JULHO), (JUNHO, JULHO), (JUNHO, JUNHO)],
)
def test_aceita_periodo_coerente(disponivel_de, disponivel_ate):
    validar_periodo(disponivel_de, disponivel_ate)


def test_recusa_periodo_que_termina_antes_de_comecar():
    with pytest.raises(DadosInvalidos) as erro:
        validar_periodo(JULHO, JUNHO)

    assert erro.value.detalhes == [
        DetalheErro("disponivelAte", "Deve ser igual ou posterior a disponivelDe")
    ]

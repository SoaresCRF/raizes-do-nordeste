from datetime import date

import pytest

from src.domain.erros.erros import DadosInvalidos, DetalheErro
from src.domain.relatorio.relatorio import validar_periodo_do_relatorio

PRIMEIRO_DE_OUTUBRO = date(2026, 10, 1)
CINCO_DE_OUTUBRO = date(2026, 10, 5)


@pytest.mark.parametrize(
    ("de", "ate"),
    [
        (None, None),
        (PRIMEIRO_DE_OUTUBRO, None),
        (None, CINCO_DE_OUTUBRO),
        (PRIMEIRO_DE_OUTUBRO, CINCO_DE_OUTUBRO),
        (CINCO_DE_OUTUBRO, CINCO_DE_OUTUBRO),
    ],
)
def test_aceita_periodo_aberto_ou_em_ordem(de, ate):
    validar_periodo_do_relatorio(de, ate)


def test_recusa_periodo_que_termina_antes_de_comecar():
    with pytest.raises(DadosInvalidos) as erro:
        validar_periodo_do_relatorio(CINCO_DE_OUTUBRO, PRIMEIRO_DE_OUTUBRO)

    assert erro.value.detalhes == [DetalheErro("ate", "Deve ser igual ou posterior a de")]

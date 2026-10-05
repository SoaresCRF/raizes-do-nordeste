import pytest

from src.domain.erros.erros import DadosInvalidos, DetalheErro, EstoqueInsuficiente
from src.domain.estoque.estoque import SALDO_MAXIMO, TipoMovimentacao, calcular_saldo

PRODUTO = 3


def test_entrada_soma_ao_saldo():
    assert calcular_saldo(5, TipoMovimentacao.ENTRADA, 10, PRODUTO) == 15


def test_saida_subtrai_do_saldo():
    assert calcular_saldo(10, TipoMovimentacao.SAIDA, 3, PRODUTO) == 7


def test_saida_pode_zerar_o_saldo():
    assert calcular_saldo(2, TipoMovimentacao.SAIDA, 2, PRODUTO) == 0


def test_saida_maior_que_o_saldo_e_recusada():
    with pytest.raises(EstoqueInsuficiente) as erro:
        calcular_saldo(2, TipoMovimentacao.SAIDA, 3, PRODUTO)

    assert erro.value.mensagem == "Estoque insuficiente do produto 3"
    assert erro.value.detalhes == [DetalheErro("quantidade", "Disponível: 2")]


def test_entrada_ate_o_teto_e_aceita():
    assert calcular_saldo(SALDO_MAXIMO - 1, TipoMovimentacao.ENTRADA, 1, PRODUTO) == SALDO_MAXIMO


def test_entrada_que_passa_do_teto_e_recusada():
    with pytest.raises(DadosInvalidos) as erro:
        calcular_saldo(SALDO_MAXIMO, TipoMovimentacao.ENTRADA, 1, PRODUTO)

    assert erro.value.detalhes == [
        DetalheErro("quantidade", f"Saldo resultante passa de {SALDO_MAXIMO}")
    ]

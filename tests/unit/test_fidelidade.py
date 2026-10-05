from datetime import UTC, datetime
from decimal import Decimal

import pytest

from src.domain.erros.erros import DadosInvalidos, DetalheErro, SaldoPontosInsuficiente
from src.domain.fidelidade.fidelidade import (
    calcular_desconto_do_resgate,
    calcular_pontos_ganhos,
    tem_consentimento_fidelidade,
    valor_dos_pontos,
)
from src.domain.usuario.usuario import Consentimento, FinalidadeConsentimento

AGORA = datetime(2026, 10, 4, tzinfo=UTC)


def _consentimento(finalidade: FinalidadeConsentimento, concedido: bool) -> Consentimento:
    return Consentimento(
        id=1,
        usuario_id=7,
        finalidade=finalidade,
        concedido=concedido,
        versao_termo="1.0",
        registrado_em=AGORA,
        created_at=AGORA,
        updated_at=AGORA,
    )


@pytest.mark.parametrize(("total", "pontos"), [("18.90", 18), ("100.00", 100), ("0.99", 0)])
def test_um_ponto_por_real_pago_arredondado_para_baixo(total, pontos):
    assert calcular_pontos_ganhos(Decimal(total)) == pontos


def test_consentimento_de_fidelidade_concedido_vale():
    assert tem_consentimento_fidelidade([_consentimento(FinalidadeConsentimento.FIDELIDADE, True)])


def test_consentimento_de_fidelidade_revogado_nao_vale():
    assert not tem_consentimento_fidelidade(
        [_consentimento(FinalidadeConsentimento.FIDELIDADE, False)]
    )


def test_sem_consentimento_registrado_nao_vale():
    assert not tem_consentimento_fidelidade([])


def test_consentimento_de_marketing_nao_vale_para_fidelidade():
    assert not tem_consentimento_fidelidade(
        [_consentimento(FinalidadeConsentimento.MARKETING, True)]
    )


@pytest.mark.parametrize(
    ("pontos", "valor"),
    [(0, "0"), (99, "0"), (100, "5.00"), (149, "5.00"), (250, "10.00"), (-87, "0")],
)
def test_cada_100_pontos_valem_cinco_reais(pontos, valor):
    assert valor_dos_pontos(pontos) == Decimal(valor)


def test_resgate_converte_pontos_em_desconto():
    assert calcular_desconto_do_resgate(100, 149, Decimal("18.90")) == Decimal("5.00")


def test_resgate_acima_do_saldo_e_recusado():
    with pytest.raises(SaldoPontosInsuficiente) as erro:
        calcular_desconto_do_resgate(100, 99, Decimal("18.90"))

    assert erro.value.mensagem == "Saldo de 99 pontos não cobre o resgate de 100"
    assert erro.value.detalhes == [DetalheErro("pontos", "Saldo disponível: 99")]


@pytest.mark.parametrize("total", ["10.00", "6.50"])
def test_desconto_igual_ou_maior_que_o_total_e_recusado(total):
    with pytest.raises(DadosInvalidos) as erro:
        calcular_desconto_do_resgate(200, 500, Decimal(total))

    assert erro.value.detalhes == [
        DetalheErro(
            "pontos", f"Desconto de 10.00 precisa ser menor que o total do pedido ({total})"
        )
    ]

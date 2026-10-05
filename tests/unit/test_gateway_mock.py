from decimal import Decimal

import pytest

from src.application.portas.gateway_pagamento import FalhaGateway
from src.infrastructure.pagamento.gateway_mock import (
    MOTIVO_RECUSA_SIMULADA,
    GatewayPagamentoMock,
    ResultadoSimulado,
)

REFERENCIA = 42
VALOR = Decimal("18.90")


def test_mock_aprova_com_transacao_e_payload():
    resposta = GatewayPagamentoMock(ResultadoSimulado.APROVADO).cobrar(REFERENCIA, VALOR)

    assert resposta.aprovado
    assert resposta.motivo_recusa is None
    assert resposta.transacao_externa_id.startswith("MOCK-")
    assert resposta.payload == {
        "transacaoId": resposta.transacao_externa_id,
        "referencia": REFERENCIA,
        "valor": "18.90",
        "status": "APROVADO",
        "motivo": None,
    }


def test_mock_recusa_com_motivo():
    resposta = GatewayPagamentoMock(ResultadoSimulado.RECUSADO).cobrar(REFERENCIA, VALOR)

    assert not resposta.aprovado
    assert resposta.motivo_recusa == MOTIVO_RECUSA_SIMULADA
    assert (resposta.payload["status"], resposta.payload["motivo"]) == (
        "RECUSADO",
        MOTIVO_RECUSA_SIMULADA,
    )


def test_mock_em_erro_levanta_falha_do_gateway():
    with pytest.raises(FalhaGateway):
        GatewayPagamentoMock(ResultadoSimulado.ERRO).cobrar(REFERENCIA, VALOR)


def test_cada_cobranca_gera_uma_transacao_diferente():
    gateway = GatewayPagamentoMock(ResultadoSimulado.APROVADO)

    primeira = gateway.cobrar(1, VALOR)
    segunda = gateway.cobrar(2, VALOR)

    assert primeira.transacao_externa_id != segunda.transacao_externa_id


@pytest.mark.parametrize("resultado", [ResultadoSimulado.APROVADO, ResultadoSimulado.RECUSADO])
def test_mock_estorna_sem_erro(resultado):
    GatewayPagamentoMock(resultado).estornar("MOCK-abc", VALOR)


def test_mock_em_erro_nao_estorna():
    with pytest.raises(FalhaGateway):
        GatewayPagamentoMock(ResultadoSimulado.ERRO).estornar("MOCK-abc", VALOR)

import uuid
from decimal import Decimal

from src.application.gateway_pagamento import ErroGateway, RespostaCobranca
from src.domain.pagamento import StatusPagamento

MOTIVO_RECUSA_SIMULADA = "Transação não autorizada pela operadora (simulação)"
PREFIXO_TRANSACAO = "MOCK-"


class GatewayPagamentoMock:
    def __init__(self, resultado: StatusPagamento) -> None:
        self._resultado = resultado

    def cobrar(self, referencia: int, valor: Decimal) -> RespostaCobranca:
        if self._resultado == StatusPagamento.ERRO:
            raise ErroGateway("Gateway simulado fora do ar")
        aprovado = self._resultado == StatusPagamento.APROVADO
        transacao_id = f"{PREFIXO_TRANSACAO}{uuid.uuid4().hex}"
        motivo = None if aprovado else MOTIVO_RECUSA_SIMULADA
        return RespostaCobranca(
            aprovado=aprovado,
            transacao_externa_id=transacao_id,
            motivo_recusa=motivo,
            payload={
                "transacaoId": transacao_id,
                "referencia": referencia,
                "valor": str(valor),
                "status": self._resultado.value,
                "motivo": motivo,
            },
        )

import uuid
from decimal import Decimal
from enum import StrEnum

from src.application.portas.gateway_pagamento import FalhaGateway, RespostaCobranca

MOTIVO_RECUSA_SIMULADA = "Transação não autorizada pela operadora (simulação)"
PREFIXO_TRANSACAO = "MOCK-"


class ResultadoSimulado(StrEnum):
    APROVADO = "APROVADO"
    RECUSADO = "RECUSADO"
    ERRO = "ERRO"
    TIMEOUT = "TIMEOUT"


class GatewayPagamentoMock:
    """Nenhum pagamento real acontece (RN11); o resultado vem do X-Simular-Resultado (Q06)."""

    def __init__(self, resultado: ResultadoSimulado, timeout_segundos: float) -> None:
        self._resultado = resultado
        self._timeout_segundos = timeout_segundos

    def _simular_falha(self) -> None:
        if self._resultado == ResultadoSimulado.ERRO:
            raise FalhaGateway("Gateway simulado fora do ar")
        if self._resultado == ResultadoSimulado.TIMEOUT:
            # Sem esperar o prazo passar: a falha é a mesma que o cliente HTTP de um
            # gateway real levantaria ao estourar o timeout configurado (RNF18).
            raise FalhaGateway(f"Gateway simulado não respondeu em {self._timeout_segundos:g} s")

    def cobrar(self, referencia: int, valor: Decimal) -> RespostaCobranca:
        self._simular_falha()
        aprovado = self._resultado == ResultadoSimulado.APROVADO
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

    def estornar(self, transacao_externa_id: str, valor: Decimal) -> None:
        # Só a falha importa no estorno: os outros resultados simulados estornam.
        self._simular_falha()

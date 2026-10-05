from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class RespostaCobranca:
    aprovado: bool
    transacao_externa_id: str
    motivo_recusa: str | None
    payload: dict


class FalhaGateway(Exception):
    """O gateway não respondeu ou respondeu com erro; a cobrança não aconteceu (RN15)."""


class GatewayPagamento(Protocol):
    # Única interface do projeto: o mock existe para ser trocado por um gateway real
    # (seção 10 do PROJETO.md).
    def cobrar(self, referencia: int, valor: Decimal) -> RespostaCobranca: ...
    def estornar(self, transacao_externa_id: str, valor: Decimal) -> None: ...

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class RespostaCobranca:
    aprovado: bool
    transacao_externa_id: str
    motivo_recusa: str | None
    payload: dict


class ErroGateway(Exception):
    pass


class GatewayPagamento(Protocol):
    def cobrar(self, referencia: int, valor: Decimal) -> RespostaCobranca: ...

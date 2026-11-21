from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum


class FormaPagamento(StrEnum):
    MOCK = "MOCK"


class StatusPagamento(StrEnum):
    APROVADO = "APROVADO"
    RECUSADO = "RECUSADO"
    ERRO = "ERRO"


@dataclass
class Pagamento:
    id: int
    pedido_id: int
    status: StatusPagamento
    valor: Decimal
    forma_pagamento: FormaPagamento
    transacao_externa_id: str | None
    motivo_recusa: str | None
    payload_gateway: dict | None
    created_at: datetime
    updated_at: datetime

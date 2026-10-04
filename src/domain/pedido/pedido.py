from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from src.domain.pagamento.pagamento import FormaPagamento


class CanalPedido(StrEnum):
    APP = "APP"
    TOTEM = "TOTEM"
    BALCAO = "BALCAO"
    PICKUP = "PICKUP"
    WEB = "WEB"


class StatusPedido(StrEnum):
    AGUARDANDO_PAGAMENTO = "AGUARDANDO_PAGAMENTO"
    EM_PREPARO = "EM_PREPARO"
    PRONTO = "PRONTO"
    ENTREGUE = "ENTREGUE"
    CANCELADO = "CANCELADO"


@dataclass
class Pedido:
    id: int
    cliente_id: int | None
    unidade_id: int
    canal_pedido: CanalPedido
    status: StatusPedido
    forma_pagamento: FormaPagamento
    subtotal: Decimal
    desconto: Decimal
    total: Decimal
    criado_por_id: int
    motivo_cancelamento: str | None
    created_at: datetime
    updated_at: datetime


@dataclass
class ItemPedido:
    id: int
    pedido_id: int
    produto_id: int
    quantidade: int
    preco_unitario: Decimal
    created_at: datetime
    updated_at: datetime

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class TipoTransacaoFidelidade(StrEnum):
    ACUMULO = "ACUMULO"
    RESGATE = "RESGATE"
    ESTORNO = "ESTORNO"


@dataclass
class TransacaoFidelidade:
    id: int
    cliente_id: int
    tipo: TipoTransacaoFidelidade
    pontos: int
    pedido_id: int
    created_at: datetime
    updated_at: datetime

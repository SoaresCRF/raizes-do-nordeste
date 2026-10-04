from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class TipoMovimentacao(StrEnum):
    ENTRADA = "ENTRADA"
    SAIDA = "SAIDA"


@dataclass
class Estoque:
    id: int
    unidade_id: int
    produto_id: int
    quantidade: int
    created_at: datetime
    updated_at: datetime


@dataclass
class MovimentacaoEstoque:
    id: int
    estoque_id: int
    tipo: TipoMovimentacao
    quantidade: int
    motivo: str
    pedido_id: int | None
    usuario_id: int
    created_at: datetime
    updated_at: datetime

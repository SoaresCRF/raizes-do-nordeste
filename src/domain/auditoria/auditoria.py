from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class AcaoAuditoria(StrEnum):
    UNIDADE_CRIADA = "UNIDADE_CRIADA"
    PRODUTO_ALTERADO = "PRODUTO_ALTERADO"
    PRODUTO_DESATIVADO = "PRODUTO_DESATIVADO"
    ESTOQUE_MOVIMENTADO = "ESTOQUE_MOVIMENTADO"
    PEDIDO_CRIADO = "PEDIDO_CRIADO"
    ACESSO_DADOS_PESSOAIS = "ACESSO_DADOS_PESSOAIS"
    STATUS_ALTERADO = "STATUS_ALTERADO"
    PEDIDO_CANCELADO = "PEDIDO_CANCELADO"
    PAGAMENTO_REGISTRADO = "PAGAMENTO_REGISTRADO"
    PONTOS_RESGATADOS = "PONTOS_RESGATADOS"


@dataclass
class LogAuditoria:
    id: int
    usuario_id: int | None
    unidade_id: int | None
    acao: str
    entidade: str
    entidade_id: int
    dados_antes: dict | None
    dados_depois: dict | None
    request_id: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class FiltrosAuditoria:
    entidade: str | None
    entidade_id: int | None
    unidade_id: int | None

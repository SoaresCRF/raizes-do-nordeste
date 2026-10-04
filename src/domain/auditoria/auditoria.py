from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class AcaoAuditoria(StrEnum):
    UNIDADE_CRIADA = "UNIDADE_CRIADA"
    PRODUTO_ALTERADO = "PRODUTO_ALTERADO"
    PRODUTO_DESATIVADO = "PRODUTO_DESATIVADO"


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

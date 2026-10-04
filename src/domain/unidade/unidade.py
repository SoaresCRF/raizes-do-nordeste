from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class TipoUnidade(StrEnum):
    COZINHA_COMPLETA = "COZINHA_COMPLETA"
    FORMATO_REDUZIDO = "FORMATO_REDUZIDO"


@dataclass(frozen=True)
class DadosUnidade:
    nome: str
    cidade: str
    uf: str
    regiao: str
    tipo: TipoUnidade


@dataclass
class Unidade:
    id: int
    nome: str
    cidade: str
    uf: str
    regiao: str
    tipo: TipoUnidade
    ativa: bool
    created_at: datetime
    updated_at: datetime

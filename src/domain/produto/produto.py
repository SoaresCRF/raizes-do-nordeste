from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from src.domain.erros.erros import RecursoNaoEncontrado


@dataclass(frozen=True)
class DadosProduto:
    nome: str
    descricao: str | None
    preco: Decimal


@dataclass(frozen=True)
class ItemCardapio:
    produto_id: int
    nome: str
    descricao: str | None
    preco: Decimal
    disponivel: bool


def produto_nao_encontrado(produto_id: int) -> RecursoNaoEncontrado:
    return RecursoNaoEncontrado(f"Produto {produto_id} não encontrado")


@dataclass
class Produto:
    id: int
    nome: str
    descricao: str | None
    preco: Decimal
    ativo: bool
    created_at: datetime
    updated_at: datetime

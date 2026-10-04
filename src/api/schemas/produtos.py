from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import Field

from src.api.schemas.base import EsquemaEntrada, EsquemaSaida, ValorMonetario
from src.api.schemas.campos import Nome

# Coluna preco: numeric(10, 2). Fora disso o banco recusa e a requisição viraria 500.
Preco = Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=2)]


class NovoProduto(EsquemaEntrada):
    nome: Nome
    descricao: str | None = None
    preco: Preco
    disponivel_de: date | None = None
    disponivel_ate: date | None = None


class AlteracaoProduto(NovoProduto):
    ativo: bool


class ProdutoResposta(EsquemaSaida):
    id: int
    nome: str
    descricao: str | None
    preco: ValorMonetario
    ativo: bool
    disponivel_de: date | None
    disponivel_ate: date | None


class ItemCardapioResposta(EsquemaSaida):
    produto_id: int
    nome: str
    descricao: str | None
    preco: ValorMonetario
    disponivel: bool

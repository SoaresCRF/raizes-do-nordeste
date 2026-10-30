from dataclasses import dataclass
from math import ceil
from typing import Annotated, Self

from fastapi import Query

from src.api.schemas.base import EsquemaSaida

LIMITE_PADRAO = 10
LIMITE_MAXIMO = 100
PAGINA_MAXIMA = 1_000_000


@dataclass(frozen=True)
class ParametrosPaginacao:
    page: int
    limit: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit


def obter_paginacao(
    page: Annotated[int, Query(ge=1, le=PAGINA_MAXIMA)] = 1,
    limit: Annotated[int, Query(ge=1, le=LIMITE_MAXIMO)] = LIMITE_PADRAO,
) -> ParametrosPaginacao:
    return ParametrosPaginacao(page=page, limit=limit)


class Paginacao(EsquemaSaida):
    page: int
    limit: int
    total: int
    total_paginas: int


class Pagina[T](EsquemaSaida):
    dados: list[T]
    paginacao: Paginacao

    @classmethod
    def criar(cls, dados: list[T], total: int, parametros: ParametrosPaginacao) -> Self:
        return cls(
            dados=dados,
            paginacao=Paginacao(
                page=parametros.page,
                limit=parametros.limit,
                total=total,
                total_paginas=ceil(total / parametros.limit),
            ),
        )

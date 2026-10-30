from typing import Annotated

from pydantic import Field, StringConstraints

from src.api.schemas.base import EsquemaEntrada, EsquemaSaida
from src.api.schemas.campos import ID_MAXIMO
from src.domain.estoque.estoque import SALDO_MAXIMO, TipoMovimentacao

TAMANHO_MAXIMO_MOTIVO = 200


class SaldoResposta(EsquemaSaida):
    produto_id: int
    nome: str
    quantidade: int


class NovaMovimentacao(EsquemaEntrada):
    unidade_id: Annotated[int, Field(le=ID_MAXIMO)]
    produto_id: Annotated[int, Field(le=ID_MAXIMO)]
    tipo: TipoMovimentacao
    quantidade: Annotated[int, Field(strict=True, gt=0, le=SALDO_MAXIMO)]
    motivo: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=TAMANHO_MAXIMO_MOTIVO),
    ]


class MovimentacaoResposta(EsquemaSaida):
    movimentacao_id: int
    tipo: TipoMovimentacao
    quantidade: int
    saldo_atual: int

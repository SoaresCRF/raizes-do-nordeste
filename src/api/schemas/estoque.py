from typing import Annotated

from pydantic import Field, StringConstraints

from src.api.schemas.base import DataHoraUtc, EsquemaEntrada, EsquemaSaida
from src.api.schemas.campos import ID_MAXIMO
from src.domain.estoque.estoque import SALDO_MAXIMO, TipoMovimentacao

# Coluna movimentacao_estoque.motivo: varchar(200).
TAMANHO_MAXIMO_MOTIVO = 200


class SaldoResposta(EsquemaSaida):
    produto_id: int
    nome: str
    quantidade: int


class NovaMovimentacao(EsquemaEntrada):
    unidade_id: Annotated[int, Field(le=ID_MAXIMO)]
    produto_id: Annotated[int, Field(le=ID_MAXIMO)]
    tipo: TipoMovimentacao
    # strict: sem ele o Pydantic aceita true como 1 e "10" como 10 (RN06 pede inteiro).
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


class MovimentacaoHistoricoResposta(EsquemaSaida):
    movimentacao_id: int
    produto_id: int
    tipo: TipoMovimentacao
    quantidade: int
    motivo: str
    pedido_id: int | None
    usuario_id: int
    created_at: DataHoraUtc

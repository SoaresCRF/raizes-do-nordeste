from typing import Annotated

from pydantic import Field, StringConstraints

from src.api.schemas.base import DataHoraUtc, EsquemaEntrada, EsquemaSaida, ValorMonetario
from src.api.schemas.campos import ID_MAXIMO
from src.domain.estoque.estoque import SALDO_MAXIMO
from src.domain.pagamento.pagamento import FormaPagamento, StatusPagamento
from src.domain.pedido.pedido import CanalPedido, StatusPedido

# Coluna pedido.motivo_cancelamento: varchar(200).
TAMANHO_MAXIMO_MOTIVO_CANCELAMENTO = 200


class ItemNovoPedido(EsquemaEntrada):
    produto_id: Annotated[int, Field(le=ID_MAXIMO)]
    # strict: sem ele o Pydantic aceita true como 1 e "2" como 2.
    quantidade: Annotated[int, Field(strict=True, gt=0, le=SALDO_MAXIMO)]


class NovoPedido(EsquemaEntrada):
    canal_pedido: CanalPedido
    unidade_id: Annotated[int, Field(le=ID_MAXIMO)]
    cliente_id: Annotated[int, Field(le=ID_MAXIMO)] | None = None
    itens: Annotated[list[ItemNovoPedido], Field(min_length=1)]
    forma_pagamento: FormaPagamento


class AlteracaoStatus(EsquemaEntrada):
    status: StatusPedido


class Cancelamento(EsquemaEntrada):
    motivo: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True, min_length=1, max_length=TAMANHO_MAXIMO_MOTIVO_CANCELAMENTO
        ),
    ]


class ItemPedidoResposta(EsquemaSaida):
    produto_id: int
    quantidade: int
    preco_unitario: ValorMonetario


class PedidoResumoResposta(EsquemaSaida):
    pedido_id: int
    cliente_id: int | None
    canal_pedido: CanalPedido
    unidade_id: int
    status: StatusPedido
    subtotal: ValorMonetario
    desconto: ValorMonetario
    total: ValorMonetario
    created_at: DataHoraUtc


class PedidoCriadoResposta(PedidoResumoResposta):
    itens: list[ItemPedidoResposta]


class ClienteDoPedidoResposta(EsquemaSaida):
    id: int
    nome: str


class UltimoPagamentoResposta(EsquemaSaida):
    pagamento_id: int
    status: StatusPagamento
    valor: ValorMonetario
    created_at: DataHoraUtc


class PedidoDetalhadoResposta(PedidoCriadoResposta):
    motivo_cancelamento: str | None
    cliente: ClienteDoPedidoResposta | None
    ultimo_pagamento: UltimoPagamentoResposta | None
    updated_at: DataHoraUtc


class StatusAlteradoResposta(EsquemaSaida):
    pedido_id: int
    status_anterior: StatusPedido
    status: StatusPedido
    updated_at: DataHoraUtc


class CancelamentoResposta(EsquemaSaida):
    pedido_id: int
    status: StatusPedido
    motivo_cancelamento: str
    pagamento_estornado: bool

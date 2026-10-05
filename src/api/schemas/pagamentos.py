from typing import Annotated

from pydantic import Field

from src.api.schemas.base import DataHoraUtc, EsquemaEntrada, EsquemaSaida, ValorMonetario
from src.api.schemas.campos import ID_MAXIMO
from src.domain.pagamento.pagamento import FormaPagamento, StatusPagamento
from src.domain.pedido.pedido import StatusPedido


class SolicitacaoPagamento(EsquemaEntrada):
    pedido_id: Annotated[int, Field(le=ID_MAXIMO)]


class PagamentoRegistradoResposta(EsquemaSaida):
    pagamento_id: int
    pedido_id: int
    status: StatusPagamento
    valor: ValorMonetario
    transacao_externa_id: str | None
    mensagem: str
    status_pedido: StatusPedido
    payload_gateway: dict | None


class PagamentoResposta(EsquemaSaida):
    pagamento_id: int
    pedido_id: int
    status: StatusPagamento
    valor: ValorMonetario
    forma_pagamento: FormaPagamento
    transacao_externa_id: str | None
    motivo_recusa: str | None
    payload_gateway: dict | None
    created_at: DataHoraUtc
    updated_at: DataHoraUtc

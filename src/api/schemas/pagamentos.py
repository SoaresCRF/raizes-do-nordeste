from typing import Annotated

from pydantic import Field

from src.api.schemas.base import EsquemaEntrada, EsquemaSaida, ValorMonetario
from src.api.schemas.campos import ID_MAXIMO
from src.domain.pagamento.pagamento import StatusPagamento
from src.domain.pedido.pedido import StatusPedido

MENSAGEM_APROVADO = "Pagamento aprovado; o pedido seguiu para o preparo"
MENSAGEM_RECUSADO = "Pagamento recusado ({motivo}); o pedido continua aguardando pagamento"


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

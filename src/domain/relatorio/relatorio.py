from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

from src.domain.erros.erros import MENSAGEM_DADOS_INVALIDOS, DadosInvalidos, DetalheErro
from src.domain.pedido.pedido import StatusPedido


class Agrupamento(StrEnum):
    UNIDADE = "unidade"
    REGIAO = "regiao"
    CANAL = "canal"
    PRODUTO = "produto"


# Venda é pedido pago e não cancelado: o cancelamento de pedido pago estorna o
# pagamento (RN16), então ele sai do relatório.
STATUS_DE_VENDA = (StatusPedido.EM_PREPARO, StatusPedido.PRONTO, StatusPedido.ENTREGUE)


@dataclass(frozen=True)
class LinhaRelatorio:
    grupo_id: int | None
    grupo: str
    pedidos: int
    quantidade: int
    total: Decimal


def validar_periodo_do_relatorio(de: date | None, ate: date | None) -> None:
    if de is None or ate is None or de <= ate:
        return
    raise DadosInvalidos(
        MENSAGEM_DADOS_INVALIDOS, [DetalheErro("ate", "Deve ser igual ou posterior a de")]
    )

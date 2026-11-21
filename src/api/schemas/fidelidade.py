from typing import Annotated

from pydantic import Field

from src.api.schemas.base import DataHoraUtc, EsquemaEntrada, EsquemaSaida, ValorMonetario
from src.api.schemas.campos import ID_MAXIMO
from src.domain.fidelidade import PONTOS_POR_RESGATE, TipoTransacaoFidelidade


class SaldoPontosResposta(EsquemaSaida):
    saldo_pontos: int
    valor_equivalente: ValorMonetario


class TransacaoFidelidadeResposta(EsquemaSaida):
    transacao_id: int
    tipo: TipoTransacaoFidelidade
    pontos: int
    pedido_id: int
    created_at: DataHoraUtc


class NovoResgate(EsquemaEntrada):
    pedido_id: Annotated[int, Field(le=ID_MAXIMO)]
    pontos: Annotated[int, Field(strict=True, gt=0, multiple_of=PONTOS_POR_RESGATE)]


class ResgateResposta(EsquemaSaida):
    pedido_id: int
    pontos_resgatados: int
    desconto: ValorMonetario
    total_atualizado: ValorMonetario
    saldo_pontos: int

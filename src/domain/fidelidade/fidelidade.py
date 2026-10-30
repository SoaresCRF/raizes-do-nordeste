import math
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from src.domain.erros.erros import (
    DadosInvalidos,
    DetalheErro,
    SaldoPontosInsuficiente,
)
from src.domain.usuario.usuario import Consentimento, FinalidadeConsentimento

PONTOS_POR_REAL = 1
PONTOS_POR_RESGATE = 100
VALOR_POR_RESGATE = Decimal("5.00")


class TipoTransacaoFidelidade(StrEnum):
    ACUMULO = "ACUMULO"
    RESGATE = "RESGATE"
    ESTORNO = "ESTORNO"


@dataclass
class TransacaoFidelidade:
    id: int
    cliente_id: int
    tipo: TipoTransacaoFidelidade
    pontos: int
    pedido_id: int
    created_at: datetime
    updated_at: datetime


def calcular_pontos_ganhos(total_pago: Decimal) -> int:
    return math.floor(total_pago * PONTOS_POR_REAL)


def tem_consentimento_fidelidade(consentimentos: list[Consentimento]) -> bool:
    return any(
        consentimento.finalidade == FinalidadeConsentimento.FIDELIDADE and consentimento.concedido
        for consentimento in consentimentos
    )


def calcular_valor_dos_pontos(pontos: int) -> Decimal:
    return pontos // PONTOS_POR_RESGATE * VALOR_POR_RESGATE


def calcular_desconto_do_resgate(pontos: int, saldo: int, total: Decimal) -> Decimal:
    if pontos > saldo:
        raise SaldoPontosInsuficiente(
            f"Saldo de {saldo} pontos não cobre o resgate de {pontos}",
            [DetalheErro("pontos", f"Saldo disponível: {saldo}")],
        )
    desconto = calcular_valor_dos_pontos(pontos)
    if desconto >= total:
        raise DadosInvalidos.no_campo(
            "pontos", f"Desconto de {desconto} precisa ser menor que o total do pedido ({total})"
        )
    return desconto

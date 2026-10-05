import math
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from src.domain.erros.erros import (
    MENSAGEM_DADOS_INVALIDOS,
    DadosInvalidos,
    DetalheErro,
    SaldoPontosInsuficiente,
)
from src.domain.usuario.usuario import Consentimento, FinalidadeConsentimento

# Q08: 1 ponto por real pago, arredondado para baixo (RN18).
PONTOS_POR_REAL = 1
# Q08: resgate em blocos de 100 pontos, cada um valendo R$ 5,00 de desconto (RN19).
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
    """Recebe os consentimentos vigentes, o mais recente de cada finalidade (RN17)."""
    return any(
        consentimento.finalidade == FinalidadeConsentimento.FIDELIDADE and consentimento.concedido
        for consentimento in consentimentos
    )


def valor_dos_pontos(pontos: int) -> Decimal:
    """Desconto que os pontos compram; saldo negativo (Q12) vale zero."""
    return max(pontos, 0) // PONTOS_POR_RESGATE * VALOR_POR_RESGATE


def calcular_desconto_do_resgate(pontos: int, saldo: int, total: Decimal) -> Decimal:
    """Resgate simples (RN19): saldo suficiente e desconto menor que o total do pedido."""
    if pontos > saldo:
        raise SaldoPontosInsuficiente(
            f"Saldo de {saldo} pontos não cobre o resgate de {pontos}",
            [DetalheErro("pontos", f"Saldo disponível: {saldo}")],
        )
    desconto = valor_dos_pontos(pontos)
    # O pedido precisa manter valor a pagar: pagamento de valor zero não passa pelo
    # gateway, e o pedido ficaria preso em AGUARDANDO_PAGAMENTO.
    if desconto >= total:
        raise DadosInvalidos(
            MENSAGEM_DADOS_INVALIDOS,
            [
                DetalheErro(
                    "pontos",
                    f"Desconto de {desconto} precisa ser menor que o total do pedido ({total})",
                )
            ],
        )
    return desconto

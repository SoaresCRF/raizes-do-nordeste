from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from src.domain.erros import (
    DadosInvalidos,
    DetalheErro,
    EstoqueInsuficiente,
)

SALDO_MAXIMO = 2_147_483_647


class TipoMovimentacao(StrEnum):
    ENTRADA = "ENTRADA"
    SAIDA = "SAIDA"


@dataclass(frozen=True)
class SaldoProduto:
    produto_id: int
    nome: str
    quantidade: int


@dataclass(frozen=True)
class DadosMovimentacao:
    unidade_id: int
    produto_id: int
    tipo: TipoMovimentacao
    quantidade: int
    motivo: str


def calcular_saldo(
    saldo_atual: int, tipo: TipoMovimentacao, quantidade: int, produto_id: int
) -> int:
    if tipo == TipoMovimentacao.SAIDA:
        if quantidade > saldo_atual:
            raise EstoqueInsuficiente(
                f"Estoque insuficiente do produto {produto_id}",
                [DetalheErro("quantidade", f"Disponível: {saldo_atual}")],
            )
        return saldo_atual - quantidade
    novo_saldo = saldo_atual + quantidade
    if novo_saldo > SALDO_MAXIMO:
        raise DadosInvalidos.no_campo("quantidade", f"Saldo resultante passa de {SALDO_MAXIMO}")
    return novo_saldo


@dataclass
class Estoque:
    id: int
    unidade_id: int
    produto_id: int
    quantidade: int
    created_at: datetime
    updated_at: datetime


@dataclass
class MovimentacaoEstoque:
    id: int
    estoque_id: int
    tipo: TipoMovimentacao
    quantidade: int
    motivo: str
    pedido_id: int | None
    usuario_id: int
    created_at: datetime
    updated_at: datetime

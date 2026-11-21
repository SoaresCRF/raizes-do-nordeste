from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from src.domain.erros import (
    MENSAGEM_DADOS_INVALIDOS,
    AcessoNegado,
    DadosInvalidos,
    DetalheErro,
    EstoqueInsuficiente,
    PagamentoNaoPermitido,
    ProdutoIndisponivelNaUnidade,
    RecursoNaoEncontrado,
    TransicaoStatusInvalida,
)
from src.domain.pagamento import FormaPagamento, Pagamento
from src.domain.produto import Produto, produto_nao_encontrado
from src.domain.usuario import Perfil, UsuarioAutenticado, verificar_acesso_a_unidade

VALOR_MAXIMO_PEDIDO = Decimal("99999999.99")
MENSAGEM_ESTOQUE_INSUFICIENTE = "Não há quantidade suficiente para um ou mais itens"
ENTIDADE_PEDIDO = "Pedido"


class CanalPedido(StrEnum):
    APP = "APP"
    TOTEM = "TOTEM"
    BALCAO = "BALCAO"
    PICKUP = "PICKUP"
    WEB = "WEB"


class StatusPedido(StrEnum):
    AGUARDANDO_PAGAMENTO = "AGUARDANDO_PAGAMENTO"
    EM_PREPARO = "EM_PREPARO"
    PRONTO = "PRONTO"
    ENTREGUE = "ENTREGUE"
    CANCELADO = "CANCELADO"


CANAIS_POR_PERFIL = {
    Perfil.CLIENTE: (CanalPedido.APP, CanalPedido.TOTEM, CanalPedido.PICKUP, CanalPedido.WEB),
    Perfil.ATENDENTE: (CanalPedido.BALCAO,),
}

TRANSICOES_VALIDAS = {
    StatusPedido.AGUARDANDO_PAGAMENTO: (StatusPedido.EM_PREPARO, StatusPedido.CANCELADO),
    StatusPedido.EM_PREPARO: (StatusPedido.PRONTO,),
    StatusPedido.PRONTO: (StatusPedido.ENTREGUE,),
}

PERFIS_POR_STATUS_MANUAL = {
    StatusPedido.PRONTO: (Perfil.COZINHA, Perfil.GERENTE, Perfil.ADMIN),
    StatusPedido.ENTREGUE: (Perfil.ATENDENTE, Perfil.GERENTE, Perfil.ADMIN),
}


@dataclass(frozen=True)
class ItemSolicitado:
    produto_id: int
    quantidade: int


@dataclass(frozen=True)
class DadosPedido:
    canal_pedido: CanalPedido
    unidade_id: int
    cliente_id: int | None
    itens: list[ItemSolicitado]
    forma_pagamento: FormaPagamento


@dataclass(frozen=True)
class ItemPrecificado:
    produto_id: int
    quantidade: int
    preco_unitario: Decimal


@dataclass
class Pedido:
    id: int
    cliente_id: int | None
    unidade_id: int
    canal_pedido: CanalPedido
    status: StatusPedido
    forma_pagamento: FormaPagamento
    subtotal: Decimal
    desconto: Decimal
    total: Decimal
    criado_por_id: int
    motivo_cancelamento: str | None
    created_at: datetime
    updated_at: datetime


@dataclass
class ItemPedido:
    id: int
    pedido_id: int
    produto_id: int
    quantidade: int
    preco_unitario: Decimal
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class FiltrosPedido:
    canal_pedido: CanalPedido | None
    status: StatusPedido | None
    unidade_id: int | None
    cliente_id: int | None


@dataclass(frozen=True)
class ClienteDoPedido:
    id: int
    nome: str


@dataclass(frozen=True)
class PedidoDetalhado:
    pedido: Pedido
    itens: list[ItemPedido]
    cliente: ClienteDoPedido | None
    ultimo_pagamento: Pagamento | None


def validar_origem_do_pedido(perfil: Perfil, canal: CanalPedido, cliente_id: int | None) -> None:
    if canal not in CANAIS_POR_PERFIL.get(perfil, ()):
        raise DadosInvalidos.no_campo(
            "canalPedido", f"Canal {canal} não permitido para o perfil {perfil}"
        )
    if perfil == Perfil.CLIENTE and cliente_id is not None:
        raise DadosInvalidos.no_campo("clienteId", "Não se aplica ao perfil CLIENTE")


def validar_itens_distintos(itens: list[ItemSolicitado]) -> None:
    vistos: set[int] = set()
    detalhes = []
    for indice, item in enumerate(itens):
        if item.produto_id in vistos:
            detalhes.append(DetalheErro(f"itens[{indice}].produtoId", "Produto repetido no pedido"))
        vistos.add(item.produto_id)
    if detalhes:
        raise DadosInvalidos(MENSAGEM_DADOS_INVALIDOS, detalhes)


def precificar_itens(
    itens: list[ItemSolicitado],
    produtos: dict[int, Produto],
    ofertados: set[int],
    saldos: dict[int, int],
    unidade_id: int,
) -> list[ItemPrecificado]:
    ofertados_com_estoque = ofertados & saldos.keys()
    for item in itens:
        if item.produto_id not in produtos:
            raise produto_nao_encontrado(item.produto_id)
    indisponiveis = [
        DetalheErro(f"itens[{indice}].produtoId", f"Indisponível na unidade {unidade_id}")
        for indice, item in enumerate(itens)
        if item.produto_id not in ofertados_com_estoque
    ]
    if indisponiveis:
        raise ProdutoIndisponivelNaUnidade(
            f"Produto indisponível na unidade {unidade_id}", indisponiveis
        )
    sem_saldo = [
        DetalheErro(f"itens[{indice}].quantidade", f"Disponível: {saldos[item.produto_id]}")
        for indice, item in enumerate(itens)
        if item.quantidade > saldos[item.produto_id]
    ]
    if sem_saldo:
        raise EstoqueInsuficiente(MENSAGEM_ESTOQUE_INSUFICIENTE, sem_saldo)
    return [
        ItemPrecificado(item.produto_id, item.quantidade, produtos[item.produto_id].preco)
        for item in itens
    ]


def calcular_subtotal(itens: list[ItemPrecificado]) -> Decimal:
    subtotal = sum((item.quantidade * item.preco_unitario for item in itens), Decimal(0))
    if subtotal > VALOR_MAXIMO_PEDIDO:
        raise DadosInvalidos.no_campo("itens", f"Total passa de {VALOR_MAXIMO_PEDIDO}")
    return subtotal


def pedido_nao_encontrado(pedido_id: int) -> RecursoNaoEncontrado:
    return RecursoNaoEncontrado(f"Pedido {pedido_id} não encontrado")


def _pertence_a_outro_cliente(usuario: UsuarioAutenticado, pedido: Pedido) -> bool:
    return usuario.perfil == Perfil.CLIENTE and pedido.cliente_id != usuario.id


def verificar_pedido_acessivel(
    usuario: UsuarioAutenticado, pedido_id: int, pedido: Pedido | None
) -> Pedido:
    if pedido is None or _pertence_a_outro_cliente(usuario, pedido):
        raise pedido_nao_encontrado(pedido_id)
    verificar_acesso_a_unidade(usuario, pedido.unidade_id)
    return pedido


def verificar_aguardando_pagamento(pedido: Pedido) -> None:
    if pedido.status != StatusPedido.AGUARDANDO_PAGAMENTO:
        raise PagamentoNaoPermitido(
            f"Pedido {pedido.id} está {pedido.status} e não aceita pagamento nem resgate"
        )


def verificar_transicao(atual: StatusPedido, novo: StatusPedido) -> None:
    if novo not in TRANSICOES_VALIDAS.get(atual, ()):
        raise TransicaoStatusInvalida(f"Pedido em {atual} não pode passar para {novo}")


def verificar_status_manual(perfil: Perfil, novo: StatusPedido) -> None:
    perfis = PERFIS_POR_STATUS_MANUAL.get(novo)
    if perfis is None:
        raise DadosInvalidos.no_campo(
            "status", "Deve ser um destes valores: 'PRONTO' ou 'ENTREGUE'"
        )
    if perfil not in perfis:
        raise AcessoNegado(f"Perfil {perfil} não pode marcar pedido como {novo}")

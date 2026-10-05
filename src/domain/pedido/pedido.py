from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from src.domain.erros.erros import (
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
from src.domain.pagamento.pagamento import FormaPagamento, Pagamento
from src.domain.produto.produto import Produto
from src.domain.usuario.usuario import Perfil, UsuarioAutenticado, verificar_acesso_a_unidade

# Teto das colunas numeric(10, 2) de subtotal e total; acima dele o banco recusa e daria 500.
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


# RN26: o atendente registra o pedido do balcão; o cliente usa os canais de autoatendimento.
CANAIS_POR_PERFIL = {
    Perfil.CLIENTE: (CanalPedido.APP, CanalPedido.TOTEM, CanalPedido.PICKUP, CanalPedido.WEB),
    Perfil.ATENDENTE: (CanalPedido.BALCAO,),
}

# RN10: ciclo de vida do pedido (seção 9.2).
TRANSICOES_VALIDAS = {
    StatusPedido.AGUARDANDO_PAGAMENTO: (StatusPedido.EM_PREPARO, StatusPedido.CANCELADO),
    StatusPedido.EM_PREPARO: (StatusPedido.PRONTO, StatusPedido.CANCELADO),
    StatusPedido.PRONTO: (StatusPedido.ENTREGUE,),
}

# Matriz da seção 3. EM_PREPARO vem do pagamento aprovado (E27) e CANCELADO do
# cancelamento (E26); nenhum dos dois é marcado à mão.
PERFIS_POR_STATUS_MANUAL = {
    StatusPedido.PRONTO: (Perfil.COZINHA, Perfil.GERENTE, Perfil.ADMIN),
    StatusPedido.ENTREGUE: (Perfil.ATENDENTE, Perfil.GERENTE, Perfil.ADMIN),
}

# RN16: depois do pagamento, só a gerência cancela, porque o cancelamento estorna o
# pagamento no gateway (Q12).
PERFIS_QUE_CANCELAM = {
    StatusPedido.AGUARDANDO_PAGAMENTO: (
        Perfil.CLIENTE,
        Perfil.ATENDENTE,
        Perfil.GERENTE,
        Perfil.ADMIN,
    ),
    StatusPedido.EM_PREPARO: (Perfil.GERENTE, Perfil.ADMIN),
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
    """Canal coerente com quem cria o pedido (RN26); só o atendente informa o cliente (CF06)."""
    if canal not in CANAIS_POR_PERFIL.get(perfil, ()):
        detalhe = DetalheErro("canalPedido", f"Canal {canal} não permitido para o perfil {perfil}")
    elif perfil == Perfil.CLIENTE and cliente_id is not None:
        detalhe = DetalheErro("clienteId", "Não se aplica ao perfil CLIENTE")
    else:
        return
    raise DadosInvalidos(MENSAGEM_DADOS_INVALIDOS, [detalhe])


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
    """Confere existência (RN02), oferta (RN03, RN24) e saldo (RN04) e copia o preço (RN08).

    `ofertados` são os produtos que o cardápio da unidade mostra hoje.
    """
    # O cardápio é lido depois de travar o estoque; uma linha de estoque criada nesse
    # intervalo não está em `saldos`, e o produto conta como indisponível.
    ofertados = ofertados & saldos.keys()
    for item in itens:
        if item.produto_id not in produtos:
            raise RecursoNaoEncontrado(f"Produto {item.produto_id} não encontrado")
    indisponiveis = [
        DetalheErro(f"itens[{indice}].produtoId", f"Indisponível na unidade {unidade_id}")
        for indice, item in enumerate(itens)
        if item.produto_id not in ofertados
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
    """Soma de quantidade × preço copiado do produto, calculada no servidor (RN08)."""
    subtotal = sum((item.quantidade * item.preco_unitario for item in itens), Decimal(0))
    if subtotal > VALOR_MAXIMO_PEDIDO:
        raise DadosInvalidos(
            MENSAGEM_DADOS_INVALIDOS,
            [DetalheErro("itens", f"Total passa de {VALOR_MAXIMO_PEDIDO}")],
        )
    return subtotal


def pedido_nao_encontrado(pedido_id: int) -> RecursoNaoEncontrado:
    return RecursoNaoEncontrado(f"Pedido {pedido_id} não encontrado")


def verificar_acesso_ao_pedido(usuario: UsuarioAutenticado, pedido: Pedido) -> None:
    """Cliente só alcança os próprios pedidos (RN22); funcionário, os da unidade (RN23).

    Pedido de outro cliente responde como inexistente, para não revelar que existe.
    """
    if usuario.perfil != Perfil.CLIENTE:
        verificar_acesso_a_unidade(usuario, pedido.unidade_id)
    elif pedido.cliente_id != usuario.id:
        raise pedido_nao_encontrado(pedido.id)


def verificar_pedido_acessivel(
    usuario: UsuarioAutenticado, pedido_id: int, pedido: Pedido | None
) -> Pedido:
    if pedido is None:
        raise pedido_nao_encontrado(pedido_id)
    verificar_acesso_ao_pedido(usuario, pedido)
    return pedido


def verificar_aguardando_pagamento(pedido: Pedido) -> None:
    """Pagamento e resgate de pontos só valem para pedido AGUARDANDO_PAGAMENTO (RN14, RN19)."""
    if pedido.status != StatusPedido.AGUARDANDO_PAGAMENTO:
        raise PagamentoNaoPermitido(
            f"Pedido {pedido.id} está {pedido.status} e não aceita pagamento nem resgate"
        )


def validar_transicao(atual: StatusPedido, novo: StatusPedido) -> None:
    if novo not in TRANSICOES_VALIDAS.get(atual, ()):
        raise TransicaoStatusInvalida(f"Pedido em {atual} não pode passar para {novo}")


def verificar_status_manual(perfil: Perfil, novo: StatusPedido) -> None:
    perfis = PERFIS_POR_STATUS_MANUAL.get(novo)
    if perfis is None:
        raise DadosInvalidos(
            MENSAGEM_DADOS_INVALIDOS,
            [DetalheErro("status", "Deve ser um destes valores: 'PRONTO' ou 'ENTREGUE'")],
        )
    if perfil not in perfis:
        raise AcessoNegado(f"Perfil {perfil} não pode marcar pedido como {novo}")


def verificar_cancelamento(perfil: Perfil, status: StatusPedido) -> None:
    validar_transicao(status, StatusPedido.CANCELADO)
    if perfil not in PERFIS_QUE_CANCELAM[status]:
        raise AcessoNegado(f"Perfil {perfil} não pode cancelar pedido em {status}")

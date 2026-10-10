from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query

from src.api.autenticacao import FuncionarioLogado, UsuarioLogado, exigir_perfil
from src.api.dependencias import ConexaoBanco, ServicoGatewayPagamento
from src.api.openapi import pedidos as documentacao
from src.api.schemas.campos import ID_MAXIMO, IdDoRecurso
from src.api.schemas.paginacao import Pagina, ParametrosPaginacao, obter_paginacao
from src.api.schemas.pedidos import (
    AlteracaoStatus,
    Cancelamento,
    CancelamentoResposta,
    ClienteDoPedidoResposta,
    ItemPedidoResposta,
    NovoPedido,
    PedidoCriadoResposta,
    PedidoDetalhadoResposta,
    PedidoResumoResposta,
    StatusAlteradoResposta,
    UltimoPagamentoResposta,
)
from src.application.pedidos.pedidos import (
    alterar_status,
    cancelar_pedido,
    consultar_pedido,
    criar_pedido,
    listar_pedidos,
)
from src.domain.pagamento.pagamento import Pagamento
from src.domain.pedido.pedido import (
    CanalPedido,
    DadosPedido,
    FiltrosPedido,
    ItemPedido,
    ItemSolicitado,
    Pedido,
    StatusPedido,
)
from src.domain.usuario.usuario import Perfil, UsuarioAutenticado

roteador = APIRouter(prefix="/pedidos", tags=["Pedidos"])

AutorDoPedido = Annotated[
    UsuarioAutenticado, Depends(exigir_perfil(Perfil.CLIENTE, Perfil.ATENDENTE))
]
AutorDoCancelamento = Annotated[
    UsuarioAutenticado,
    Depends(exigir_perfil(Perfil.CLIENTE, Perfil.ATENDENTE, Perfil.GERENTE, Perfil.ADMIN)),
]


def _campos_do_resumo(pedido: Pedido) -> dict:
    return {
        "pedido_id": pedido.id,
        "cliente_id": pedido.cliente_id,
        "canal_pedido": pedido.canal_pedido,
        "unidade_id": pedido.unidade_id,
        "status": pedido.status,
        "subtotal": pedido.subtotal,
        "desconto": pedido.desconto,
        "total": pedido.total,
        "created_at": pedido.created_at,
    }


def _itens_resposta(itens: list[ItemPedido]) -> list[ItemPedidoResposta]:
    return [ItemPedidoResposta.model_validate(item, from_attributes=True) for item in itens]


def _ultimo_pagamento(pagamento: Pagamento | None) -> UltimoPagamentoResposta | None:
    if pagamento is None:
        return None
    return UltimoPagamentoResposta(
        pagamento_id=pagamento.id,
        status=pagamento.status,
        valor=pagamento.valor,
        created_at=pagamento.created_at,
    )


@roteador.post("", status_code=HTTPStatus.CREATED, **documentacao.CRIAR_PEDIDO)
def criar_novo_pedido(
    novo: Annotated[NovoPedido, Body(openapi_examples=documentacao.EXEMPLOS_CRIAR_PEDIDO)],
    usuario: AutorDoPedido,
    conexao: ConexaoBanco,
) -> PedidoCriadoResposta:
    dados = DadosPedido(
        canal_pedido=novo.canal_pedido,
        unidade_id=novo.unidade_id,
        cliente_id=novo.cliente_id,
        itens=[ItemSolicitado(item.produto_id, item.quantidade) for item in novo.itens],
        forma_pagamento=novo.forma_pagamento,
    )
    pedido, itens = criar_pedido(conexao, usuario, dados)
    return PedidoCriadoResposta(**_campos_do_resumo(pedido), itens=_itens_resposta(itens))


@roteador.get("", **documentacao.LISTAR_PEDIDOS)
def listar_pedidos_acessiveis(
    paginacao: Annotated[ParametrosPaginacao, Depends(obter_paginacao)],
    usuario: UsuarioLogado,
    conexao: ConexaoBanco,
    canal_pedido: Annotated[
        CanalPedido | None,
        Query(alias="canalPedido", openapi_examples=documentacao.EXEMPLOS_CANAL_PEDIDO),
    ] = None,
    status: Annotated[
        StatusPedido | None, Query(openapi_examples=documentacao.EXEMPLOS_STATUS_PEDIDO)
    ] = None,
    unidade_id: Annotated[int | None, Query(alias="unidadeId", gt=0, le=ID_MAXIMO)] = None,
) -> Pagina[PedidoResumoResposta]:
    filtros = FiltrosPedido(
        canal_pedido=canal_pedido, status=status, unidade_id=unidade_id, cliente_id=None
    )
    pedidos, total = listar_pedidos(conexao, usuario, filtros, paginacao.limit, paginacao.offset)
    return Pagina[PedidoResumoResposta].criar(
        [PedidoResumoResposta(**_campos_do_resumo(pedido)) for pedido in pedidos],
        total,
        paginacao,
    )


@roteador.get("/{id}", **documentacao.CONSULTAR_PEDIDO)
def consultar_pedido_por_id(
    pedido_id: IdDoRecurso, usuario: UsuarioLogado, conexao: ConexaoBanco
) -> PedidoDetalhadoResposta:
    detalhado = consultar_pedido(conexao, usuario, pedido_id)
    pedido = detalhado.pedido
    cliente = (
        ClienteDoPedidoResposta.model_validate(detalhado.cliente, from_attributes=True)
        if detalhado.cliente
        else None
    )
    return PedidoDetalhadoResposta(
        **_campos_do_resumo(pedido),
        itens=_itens_resposta(detalhado.itens),
        motivo_cancelamento=pedido.motivo_cancelamento,
        cliente=cliente,
        ultimo_pagamento=_ultimo_pagamento(detalhado.ultimo_pagamento),
        updated_at=pedido.updated_at,
    )


@roteador.patch("/{id}/status", **documentacao.ALTERAR_STATUS)
def alterar_status_do_pedido(
    pedido_id: IdDoRecurso,
    alteracao: Annotated[
        AlteracaoStatus, Body(openapi_examples=documentacao.EXEMPLOS_ALTERAR_STATUS)
    ],
    usuario: FuncionarioLogado,
    conexao: ConexaoBanco,
) -> StatusAlteradoResposta:
    anterior, pedido = alterar_status(conexao, usuario, pedido_id, alteracao.status)
    return StatusAlteradoResposta(
        pedido_id=pedido.id,
        status_anterior=anterior,
        status=pedido.status,
        updated_at=pedido.updated_at,
    )


@roteador.post("/{id}/cancelamento", **documentacao.CANCELAR_PEDIDO)
def cancelar_pedido_existente(
    pedido_id: IdDoRecurso,
    cancelamento: Annotated[
        Cancelamento, Body(openapi_examples=documentacao.EXEMPLOS_CANCELAR_PEDIDO)
    ],
    usuario: AutorDoCancelamento,
    gateway: ServicoGatewayPagamento,
    conexao: ConexaoBanco,
) -> CancelamentoResposta:
    pedido, pagamento_estornado = cancelar_pedido(
        conexao, usuario, gateway, pedido_id, cancelamento.motivo
    )
    return CancelamentoResposta(
        pedido_id=pedido.id,
        status=pedido.status,
        motivo_cancelamento=pedido.motivo_cancelamento,
        pagamento_estornado=pagamento_estornado,
    )

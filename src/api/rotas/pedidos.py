from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query

from src.api.autenticacao import (
    ClienteAtendenteOuGestorLogado,
    ClienteOuAtendenteLogado,
    FuncionarioLogado,
    UsuarioLogado,
)
from src.api.dependencias import ConexaoBanco
from src.api.openapi import pedidos as documentacao
from src.api.schemas.campos import IdDoRecurso
from src.api.schemas.paginacao import Pagina, ParametrosPaginacao, obter_paginacao
from src.api.schemas.pedidos import (
    AlteracaoStatus,
    Cancelamento,
    CancelamentoResposta,
    NovoPedido,
    PedidoCriadoResposta,
    PedidoDetalhadoResposta,
    PedidoResumoResposta,
    StatusAlteradoResposta,
)
from src.application.pedidos import (
    alterar_status,
    cancelar_pedido,
    consultar_pedido,
    criar_pedido,
    listar_pedidos,
)
from src.domain.pagamento import Pagamento
from src.domain.pedido import (
    CanalPedido,
    DadosPedido,
    FiltrosPedido,
    ItemSolicitado,
    Pedido,
    StatusPedido,
)

roteador = APIRouter(prefix="/pedidos", tags=["Pedidos"])


def _montar_campos_do_resumo(pedido: Pedido) -> dict:
    return {**vars(pedido), "pedido_id": pedido.id}


def _montar_ultimo_pagamento(pagamento: Pagamento | None) -> dict | None:
    if pagamento is None:
        return None
    return {**vars(pagamento), "pagamento_id": pagamento.id}


@roteador.post("", status_code=HTTPStatus.CREATED, **documentacao.CRIAR_PEDIDO)
def criar_novo_pedido(
    novo: Annotated[NovoPedido, Body(openapi_examples=documentacao.EXEMPLOS_CRIAR_PEDIDO)],
    usuario: ClienteOuAtendenteLogado,
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
    return PedidoCriadoResposta.model_validate({**_montar_campos_do_resumo(pedido), "itens": itens})


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
) -> Pagina[PedidoResumoResposta]:
    filtros = FiltrosPedido(
        canal_pedido=canal_pedido, status=status, unidade_id=None, cliente_id=None
    )
    pedidos, total = listar_pedidos(conexao, usuario, filtros, paginacao.limit, paginacao.offset)
    return Pagina[PedidoResumoResposta].criar(
        [
            PedidoResumoResposta.model_validate(_montar_campos_do_resumo(pedido))
            for pedido in pedidos
        ],
        total,
        paginacao,
    )


@roteador.get("/{id}", **documentacao.CONSULTAR_PEDIDO)
def consultar_pedido_por_id(
    pedido_id: IdDoRecurso, usuario: UsuarioLogado, conexao: ConexaoBanco
) -> PedidoDetalhadoResposta:
    detalhado = consultar_pedido(conexao, usuario, pedido_id)
    return PedidoDetalhadoResposta.model_validate(
        {
            **_montar_campos_do_resumo(detalhado.pedido),
            "itens": detalhado.itens,
            "cliente": detalhado.cliente,
            "ultimo_pagamento": _montar_ultimo_pagamento(detalhado.ultimo_pagamento),
        }
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
    usuario: ClienteAtendenteOuGestorLogado,
    conexao: ConexaoBanco,
) -> CancelamentoResposta:
    pedido = cancelar_pedido(conexao, usuario, pedido_id, cancelamento.motivo)
    return CancelamentoResposta(
        pedido_id=pedido.id,
        status=pedido.status,
        motivo_cancelamento=pedido.motivo_cancelamento,
    )

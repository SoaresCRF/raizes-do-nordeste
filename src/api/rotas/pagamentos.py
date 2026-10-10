from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Request
from fastapi.responses import JSONResponse

from src.api.autenticacao import exigir_perfil
from src.api.dependencias import ConexaoBanco, ServicoGatewayPagamento
from src.api.erros import resposta_de_erro
from src.api.openapi import pagamentos as documentacao
from src.api.schemas.campos import IdDoRecurso
from src.api.schemas.pagamentos import (
    PagamentoRegistradoResposta,
    PagamentoResposta,
    SolicitacaoPagamento,
)
from src.application.pagamentos.pagamentos import consultar_pagamento, solicitar_pagamento
from src.domain.erros.erros import GatewayPagamentoIndisponivel
from src.domain.pagamento.pagamento import Pagamento, StatusPagamento
from src.domain.usuario.usuario import Perfil, UsuarioAutenticado

roteador = APIRouter(prefix="/pagamentos", tags=["Pagamentos"])

PagadorDoPedido = Annotated[
    UsuarioAutenticado, Depends(exigir_perfil(Perfil.CLIENTE, Perfil.ATENDENTE))
]
ConsultorDePagamento = Annotated[
    UsuarioAutenticado,
    Depends(exigir_perfil(Perfil.CLIENTE, Perfil.ATENDENTE, Perfil.GERENTE, Perfil.ADMIN)),
]
MENSAGEM_APROVADO = "Pagamento aprovado; o pedido seguiu para o preparo"


def _mensagem(pagamento: Pagamento) -> str:
    if pagamento.status == StatusPagamento.APROVADO:
        return MENSAGEM_APROVADO
    return f"Pagamento recusado ({pagamento.motivo_recusa}); o pedido continua aguardando pagamento"


@roteador.post(
    "",
    status_code=HTTPStatus.CREATED,
    response_model=PagamentoRegistradoResposta,
    **documentacao.SOLICITAR_PAGAMENTO,
)
def solicitar_pagamento_do_pedido(
    solicitacao: Annotated[
        SolicitacaoPagamento, Body(openapi_examples=documentacao.EXEMPLOS_SOLICITAR_PAGAMENTO)
    ],
    usuario: PagadorDoPedido,
    gateway: ServicoGatewayPagamento,
    conexao: ConexaoBanco,
    request: Request,
) -> PagamentoRegistradoResposta | JSONResponse:
    pagamento, pedido = solicitar_pagamento(conexao, usuario, gateway, solicitacao.pedido_id)
    if pagamento.status == StatusPagamento.ERRO:
        # Resposta montada aqui em vez de levantar o erro: a exceção desfaria a transação,
        # e o pagamento ERRO precisa ficar registrado (RN15).
        return resposta_de_erro(
            HTTPStatus.SERVICE_UNAVAILABLE,
            GatewayPagamentoIndisponivel.codigo,
            f"Gateway de pagamento indisponível; pagamento {pagamento.id} registrado com erro",
            request.url.path,
        )
    return PagamentoRegistradoResposta(
        pagamento_id=pagamento.id,
        pedido_id=pedido.id,
        status=pagamento.status,
        valor=pagamento.valor,
        transacao_externa_id=pagamento.transacao_externa_id,
        mensagem=_mensagem(pagamento),
        status_pedido=pedido.status,
        payload_gateway=pagamento.payload_gateway,
    )


@roteador.get("/{id}", **documentacao.CONSULTAR_PAGAMENTO)
def consultar_pagamento_por_id(
    pagamento_id: IdDoRecurso, usuario: ConsultorDePagamento, conexao: ConexaoBanco
) -> PagamentoResposta:
    pagamento = consultar_pagamento(conexao, usuario, pagamento_id)
    return PagamentoResposta(
        pagamento_id=pagamento.id,
        pedido_id=pagamento.pedido_id,
        status=pagamento.status,
        valor=pagamento.valor,
        forma_pagamento=pagamento.forma_pagamento,
        transacao_externa_id=pagamento.transacao_externa_id,
        motivo_recusa=pagamento.motivo_recusa,
        payload_gateway=pagamento.payload_gateway,
        created_at=pagamento.created_at,
        updated_at=pagamento.updated_at,
    )

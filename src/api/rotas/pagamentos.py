from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse

from src.api.autenticacao import ClienteOuAtendenteLogado
from src.api.dependencias import ConexaoBanco, ServicoGatewayPagamento
from src.api.erros import resposta_de_erro
from src.api.openapi import pagamentos as documentacao
from src.api.schemas.pagamentos import (
    MENSAGEM_APROVADO,
    MENSAGEM_RECUSADO,
    PagamentoRegistradoResposta,
    SolicitacaoPagamento,
)
from src.application.pagamentos.pagamentos import solicitar_pagamento
from src.domain.erros.erros import GatewayPagamentoIndisponivel
from src.domain.pagamento.pagamento import Pagamento, StatusPagamento

roteador = APIRouter(prefix="/pagamentos", tags=["Pagamentos"])


def _montar_mensagem(pagamento: Pagamento) -> str:
    if pagamento.status == StatusPagamento.APROVADO:
        return MENSAGEM_APROVADO
    return MENSAGEM_RECUSADO.format(motivo=pagamento.motivo_recusa)


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
    usuario: ClienteOuAtendenteLogado,
    gateway: ServicoGatewayPagamento,
    conexao: ConexaoBanco,
    request: Request,
) -> PagamentoRegistradoResposta | JSONResponse:
    pagamento, pedido = solicitar_pagamento(conexao, usuario, gateway, solicitacao.pedido_id)
    if pagamento.status == StatusPagamento.ERRO:
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
        mensagem=_montar_mensagem(pagamento),
        status_pedido=pedido.status,
        payload_gateway=pagamento.payload_gateway,
    )

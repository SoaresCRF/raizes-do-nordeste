import logging

from sqlalchemy import Connection

from src.application.fidelidade.fidelidade import creditar_pontos
from src.application.portas.gateway_pagamento import ErroGateway, GatewayPagamento
from src.domain.auditoria.auditoria import AcaoAuditoria
from src.domain.pagamento.pagamento import Pagamento, StatusPagamento
from src.domain.pedido.pedido import (
    Pedido,
    StatusPedido,
    verificar_aguardando_pagamento,
    verificar_pedido_acessivel,
)
from src.domain.usuario.usuario import UsuarioAutenticado
from src.infrastructure.database.repositorios.auditoria import RepositorioAuditoria
from src.infrastructure.database.repositorios.pagamentos import RepositorioPagamentos
from src.infrastructure.database.repositorios.pedidos import RepositorioPedidos

logger = logging.getLogger(__name__)

ENTIDADE_PAGAMENTO = "Pagamento"


def _cobrar(
    repositorio: RepositorioPagamentos, gateway: GatewayPagamento, pedido: Pedido
) -> Pagamento:
    try:
        resposta = gateway.cobrar(pedido.id, pedido.total)
    except ErroGateway as erro:
        logger.warning("Gateway de pagamento falhou no pedido %s: %s", pedido.id, erro)
        return repositorio.inserir(
            pedido.id,
            pedido.total,
            pedido.forma_pagamento,
            status=StatusPagamento.ERRO,
            transacao_externa_id=None,
            motivo_recusa=None,
            payload_gateway=None,
        )
    return repositorio.inserir(
        pedido.id,
        pedido.total,
        pedido.forma_pagamento,
        status=StatusPagamento.APROVADO if resposta.aprovado else StatusPagamento.RECUSADO,
        transacao_externa_id=resposta.transacao_externa_id,
        motivo_recusa=resposta.motivo_recusa,
        payload_gateway=resposta.payload,
    )


def _colocar_em_preparo(conexao: Connection, usuario: UsuarioAutenticado, pedido: Pedido) -> Pedido:
    em_preparo = RepositorioPedidos(conexao).atualizar_status(pedido.id, StatusPedido.EM_PREPARO)
    RepositorioAuditoria(conexao).registrar_do_pedido(
        usuario.id,
        AcaoAuditoria.STATUS_ALTERADO,
        pedido,
        {"status": pedido.status},
        {"status": em_preparo.status},
    )
    creditar_pontos(conexao, em_preparo)
    return em_preparo


def solicitar_pagamento(
    conexao: Connection, usuario: UsuarioAutenticado, gateway: GatewayPagamento, pedido_id: int
) -> tuple[Pagamento, Pedido]:
    pedido = verificar_pedido_acessivel(
        usuario, pedido_id, RepositorioPedidos(conexao).travar(pedido_id)
    )
    verificar_aguardando_pagamento(pedido)
    registrado = _cobrar(RepositorioPagamentos(conexao), gateway, pedido)
    RepositorioAuditoria(conexao).registrar(
        usuario_id=usuario.id,
        unidade_id=pedido.unidade_id,
        acao=AcaoAuditoria.PAGAMENTO_REGISTRADO,
        entidade=ENTIDADE_PAGAMENTO,
        entidade_id=registrado.id,
        dados_antes=None,
        dados_depois={
            "pedidoId": pedido.id,
            "status": registrado.status,
            "valor": str(registrado.valor),
        },
    )
    if registrado.status == StatusPagamento.APROVADO:
        pedido = _colocar_em_preparo(conexao, usuario, pedido)
    return registrado, pedido

import logging

from sqlalchemy import Connection

from src.application.fidelidade.fidelidade import creditar_pontos, estornar_pontos
from src.application.portas.gateway_pagamento import FalhaGateway, GatewayPagamento
from src.domain.auditoria.auditoria import AcaoAuditoria
from src.domain.erros.erros import GatewayPagamentoIndisponivel, RecursoNaoEncontrado
from src.domain.fidelidade.fidelidade import TipoTransacaoFidelidade
from src.domain.pagamento.pagamento import Pagamento, StatusPagamento
from src.domain.pedido.pedido import (
    ENTIDADE_PEDIDO,
    Pedido,
    StatusPedido,
    verificar_aguardando_pagamento,
    verificar_pedido_acessivel,
)
from src.domain.usuario.usuario import Perfil, UsuarioAutenticado, verificar_acesso_a_unidade
from src.infrastructure.database.repositorios.auditoria import RepositorioAuditoria
from src.infrastructure.database.repositorios.pagamentos import RepositorioPagamentos
from src.infrastructure.database.repositorios.pedidos import RepositorioPedidos

logger = logging.getLogger(__name__)

ENTIDADE_PAGAMENTO = "Pagamento"


def _cobrar(
    repositorio: RepositorioPagamentos, gateway: GatewayPagamento, pendente: Pagamento
) -> Pagamento:
    try:
        resposta = gateway.cobrar(pendente.id, pendente.valor)
    except FalhaGateway as erro:
        # RN15: a tentativa fica registrada como ERRO e o pedido não muda.
        logger.warning("Gateway de pagamento falhou no pagamento %s: %s", pendente.id, erro)
        return repositorio.registrar_resultado(
            pendente.id,
            status=StatusPagamento.ERRO,
            transacao_externa_id=None,
            motivo_recusa=None,
            payload_gateway=None,
        )
    return repositorio.registrar_resultado(
        pendente.id,
        status=StatusPagamento.APROVADO if resposta.aprovado else StatusPagamento.RECUSADO,
        transacao_externa_id=resposta.transacao_externa_id,
        motivo_recusa=resposta.motivo_recusa,
        payload_gateway=resposta.payload,
    )


def _colocar_em_preparo(conexao: Connection, usuario: UsuarioAutenticado, pedido: Pedido) -> Pedido:
    em_preparo = RepositorioPedidos(conexao).atualizar_status(pedido.id, StatusPedido.EM_PREPARO)
    RepositorioAuditoria(conexao).registrar(
        usuario_id=usuario.id,
        unidade_id=pedido.unidade_id,
        acao=AcaoAuditoria.STATUS_ALTERADO,
        entidade=ENTIDADE_PEDIDO,
        entidade_id=pedido.id,
        dados_antes={"status": pedido.status},
        dados_depois={"status": em_preparo.status},
    )
    creditar_pontos(conexao, em_preparo)
    return em_preparo


def solicitar_pagamento(
    conexao: Connection, usuario: UsuarioAutenticado, gateway: GatewayPagamento, pedido_id: int
) -> tuple[Pagamento, Pedido]:
    # FOR UPDATE: duas solicitações simultâneas do mesmo pedido não geram dois
    # pagamentos aprovados (RN14).
    pedido = verificar_pedido_acessivel(
        usuario, pedido_id, RepositorioPedidos(conexao).travar(pedido_id)
    )
    verificar_aguardando_pagamento(pedido)
    repositorio = RepositorioPagamentos(conexao)
    # Nasce PENDENTE para que o gateway receba o id do pagamento como referência.
    pendente = repositorio.inserir_pendente(pedido.id, pedido.total, pedido.forma_pagamento)
    registrado = _cobrar(repositorio, gateway, pendente)
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


def consultar_pagamento(
    conexao: Connection, usuario: UsuarioAutenticado, pagamento_id: int
) -> Pagamento:
    pagamento = RepositorioPagamentos(conexao).buscar_por_id(pagamento_id)
    pedido = RepositorioPedidos(conexao).buscar_por_id(pagamento.pedido_id) if pagamento else None
    # Pagamento de pedido de outro cliente responde como inexistente (RN22).
    if pedido is None or (usuario.perfil == Perfil.CLIENTE and pedido.cliente_id != usuario.id):
        raise RecursoNaoEncontrado(f"Pagamento {pagamento_id} não encontrado")
    verificar_acesso_a_unidade(usuario, pedido.unidade_id)
    return pagamento


def estornar_pagamento_aprovado(
    conexao: Connection, gateway: GatewayPagamento, usuario_id: int, pedido: Pedido
) -> bool:
    """Estorna no gateway o pagamento aprovado do pedido, se houver (RN16, Q12)."""
    repositorio = RepositorioPagamentos(conexao)
    aprovado = repositorio.buscar_ultimo_do_pedido(pedido.id)
    if aprovado is None or aprovado.status != StatusPagamento.APROVADO:
        return False
    try:
        gateway.estornar(aprovado.transacao_externa_id, aprovado.valor)
    except FalhaGateway as erro:
        logger.warning(
            "Gateway de pagamento falhou no estorno do pagamento %s: %s", aprovado.id, erro
        )
        # A exceção desfaz a transação da requisição: o pedido fica como estava (Q12).
        raise GatewayPagamentoIndisponivel(
            f"Gateway de pagamento indisponível; pedido {pedido.id} não foi cancelado"
        ) from erro
    repositorio.atualizar_status(aprovado.id, StatusPagamento.ESTORNADO)
    RepositorioAuditoria(conexao).registrar(
        usuario_id=usuario_id,
        unidade_id=pedido.unidade_id,
        acao=AcaoAuditoria.PAGAMENTO_ESTORNADO,
        entidade=ENTIDADE_PAGAMENTO,
        entidade_id=aprovado.id,
        dados_antes={"status": aprovado.status},
        dados_depois={"status": StatusPagamento.ESTORNADO},
    )
    estornar_pontos(conexao, pedido, TipoTransacaoFidelidade.ACUMULO)
    return True

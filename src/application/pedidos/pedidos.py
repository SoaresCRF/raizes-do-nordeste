from dataclasses import replace
from datetime import UTC, datetime

from sqlalchemy import Connection

from src.application.fidelidade.fidelidade import estornar_pontos
from src.application.pagamentos.pagamentos import estornar_pagamento_aprovado
from src.application.portas.gateway_pagamento import GatewayPagamento
from src.application.unidades.unidades import consultar_unidade
from src.domain.auditoria.auditoria import AcaoAuditoria
from src.domain.erros.erros import RecursoNaoEncontrado
from src.domain.estoque.estoque import Estoque, TipoMovimentacao, calcular_saldo
from src.domain.fidelidade.fidelidade import TipoTransacaoFidelidade
from src.domain.pedido.pedido import (
    ENTIDADE_PEDIDO,
    ClienteDoPedido,
    DadosPedido,
    FiltrosPedido,
    ItemPedido,
    ItemPrecificado,
    Pedido,
    PedidoDetalhado,
    StatusPedido,
    calcular_subtotal,
    precificar_itens,
    validar_itens_distintos,
    validar_origem_do_pedido,
    validar_transicao,
    verificar_cancelamento,
    verificar_pedido_acessivel,
    verificar_status_manual,
)
from src.domain.usuario.usuario import (
    PERFIS_LOTADOS_EM_UNIDADE,
    Perfil,
    UsuarioAutenticado,
    verificar_acesso_a_unidade,
)
from src.infrastructure.database.repositorios.auditoria import RepositorioAuditoria
from src.infrastructure.database.repositorios.estoque import RepositorioEstoque
from src.infrastructure.database.repositorios.pagamentos import RepositorioPagamentos
from src.infrastructure.database.repositorios.pedidos import RepositorioPedidos
from src.infrastructure.database.repositorios.produtos import RepositorioProdutos
from src.infrastructure.database.repositorios.usuarios import RepositorioUsuarios

ENTIDADE_USUARIO = "Usuario"


def _verificar_cliente(conexao: Connection, cliente_id: int) -> None:
    cliente = RepositorioUsuarios(conexao).buscar_por_id(cliente_id)
    if cliente is None or cliente.perfil != Perfil.CLIENTE or not cliente.ativo:
        raise RecursoNaoEncontrado(f"Cliente {cliente_id} não encontrado")


def _precificar(
    conexao: Connection, dados: DadosPedido, estoques: dict[int, Estoque]
) -> list[ItemPrecificado]:
    produto_ids = [item.produto_id for item in dados.itens]
    repositorio = RepositorioProdutos(conexao)
    # Datas do sistema em UTC; RN24 compara só o dia, como no cardápio.
    hoje = datetime.now(UTC).date()
    return precificar_itens(
        dados.itens,
        repositorio.buscar_por_ids(produto_ids),
        repositorio.listar_ids_no_cardapio(dados.unidade_id, produto_ids, hoje),
        {produto_id: estoque.quantidade for produto_id, estoque in estoques.items()},
        dados.unidade_id,
    )


def _movimentar_itens(
    conexao: Connection,
    usuario_id: int,
    pedido_id: int,
    itens: list[ItemPedido],
    estoques: dict[int, Estoque],
    tipo: TipoMovimentacao,
    motivo: str,
) -> None:
    repositorio = RepositorioEstoque(conexao)
    for item in itens:
        estoque = estoques[item.produto_id]
        saldo = calcular_saldo(estoque.quantidade, tipo, item.quantidade, item.produto_id)
        repositorio.atualizar_quantidade(estoque.id, saldo)
        repositorio.registrar_movimentacao(
            estoque_id=estoque.id,
            tipo=tipo,
            quantidade=item.quantidade,
            motivo=motivo,
            usuario_id=usuario_id,
            pedido_id=pedido_id,
        )


def _itens_para_auditoria(itens: list[ItemPedido]) -> list[dict]:
    # Preço como texto para não perder centavos no JSON, como na auditoria de produto.
    return [
        {
            "produtoId": item.produto_id,
            "quantidade": item.quantidade,
            "precoUnitario": str(item.preco_unitario),
        }
        for item in itens
    ]


def _auditar_pedido(
    conexao: Connection,
    usuario_id: int,
    acao: AcaoAuditoria,
    pedido: Pedido,
    dados_antes: dict | None,
    dados_depois: dict,
) -> None:
    RepositorioAuditoria(conexao).registrar(
        usuario_id=usuario_id,
        unidade_id=pedido.unidade_id,
        acao=acao,
        entidade=ENTIDADE_PEDIDO,
        entidade_id=pedido.id,
        dados_antes=dados_antes,
        dados_depois=dados_depois,
    )


def criar_pedido(
    conexao: Connection, usuario: UsuarioAutenticado, dados: DadosPedido
) -> tuple[Pedido, list[ItemPedido]]:
    validar_origem_do_pedido(usuario.perfil, dados.canal_pedido, dados.cliente_id)
    validar_itens_distintos(dados.itens)
    # RN23 antes da existência: o atendente não descobre pelo 404 se a unidade existe.
    verificar_acesso_a_unidade(usuario, dados.unidade_id)
    consultar_unidade(conexao, dados.unidade_id)
    if dados.cliente_id is not None:
        _verificar_cliente(conexao, dados.cliente_id)
    # FOR UPDATE antes de conferir o saldo: dois pedidos simultâneos não vendem a mesma
    # unidade de estoque (RN04, Q11).
    estoques = RepositorioEstoque(conexao).travar_varios(
        dados.unidade_id, [item.produto_id for item in dados.itens]
    )
    itens = _precificar(conexao, dados, estoques)
    repositorio = RepositorioPedidos(conexao)
    pedido = repositorio.inserir(
        cliente_id=usuario.id if usuario.perfil == Perfil.CLIENTE else dados.cliente_id,
        unidade_id=dados.unidade_id,
        canal_pedido=dados.canal_pedido,
        forma_pagamento=dados.forma_pagamento,
        subtotal=calcular_subtotal(itens),
        criado_por_id=usuario.id,
    )
    itens_do_pedido = repositorio.inserir_itens(pedido.id, itens)
    _movimentar_itens(
        conexao,
        usuario.id,
        pedido.id,
        itens_do_pedido,
        estoques,
        TipoMovimentacao.SAIDA,
        f"Pedido {pedido.id}",
    )
    _auditar_pedido(
        conexao,
        usuario.id,
        AcaoAuditoria.PEDIDO_CRIADO,
        pedido,
        None,
        {
            "status": pedido.status,
            "canalPedido": pedido.canal_pedido,
            "clienteId": pedido.cliente_id,
            "total": str(pedido.total),
            "itens": _itens_para_auditoria(itens_do_pedido),
        },
    )
    return pedido, itens_do_pedido


def listar_pedidos(
    conexao: Connection,
    usuario: UsuarioAutenticado,
    filtros: FiltrosPedido,
    limit: int,
    offset: int,
) -> tuple[list[Pedido], int]:
    if usuario.perfil == Perfil.CLIENTE:
        filtros = replace(filtros, cliente_id=usuario.id)
    elif usuario.perfil in PERFIS_LOTADOS_EM_UNIDADE:
        # Sem o filtro, o funcionário vê a própria unidade; com outra unidade, 403 (RN23).
        unidade_id = usuario.unidade_id if filtros.unidade_id is None else filtros.unidade_id
        verificar_acesso_a_unidade(usuario, unidade_id)
        filtros = replace(filtros, unidade_id=unidade_id)
    repositorio = RepositorioPedidos(conexao)
    return repositorio.listar(filtros, limit, offset), repositorio.contar(filtros)


def _identificar_cliente_e_auditar_acesso(
    conexao: Connection, usuario: UsuarioAutenticado, pedido: Pedido
) -> ClienteDoPedido | None:
    if pedido.cliente_id is None:
        return None
    cliente = RepositorioUsuarios(conexao).buscar_por_id(pedido.cliente_id)
    if usuario.perfil != Perfil.CLIENTE:
        # RN21: registra que um funcionário viu dados do cliente, sem os dados em si.
        RepositorioAuditoria(conexao).registrar(
            usuario_id=usuario.id,
            unidade_id=pedido.unidade_id,
            acao=AcaoAuditoria.ACESSO_DADOS_PESSOAIS,
            entidade=ENTIDADE_USUARIO,
            entidade_id=cliente.id,
            dados_antes=None,
            dados_depois={"pedidoId": pedido.id},
        )
    return ClienteDoPedido(id=cliente.id, nome=cliente.nome)


def consultar_pedido(
    conexao: Connection, usuario: UsuarioAutenticado, pedido_id: int
) -> PedidoDetalhado:
    repositorio = RepositorioPedidos(conexao)
    pedido = verificar_pedido_acessivel(usuario, pedido_id, repositorio.buscar_por_id(pedido_id))
    return PedidoDetalhado(
        pedido=pedido,
        itens=repositorio.listar_itens(pedido.id),
        cliente=_identificar_cliente_e_auditar_acesso(conexao, usuario, pedido),
        ultimo_pagamento=RepositorioPagamentos(conexao).buscar_ultimo_do_pedido(pedido.id),
    )


def alterar_status(
    conexao: Connection, usuario: UsuarioAutenticado, pedido_id: int, novo_status: StatusPedido
) -> tuple[StatusPedido, Pedido]:
    verificar_status_manual(usuario.perfil, novo_status)
    repositorio = RepositorioPedidos(conexao)
    # FOR UPDATE: mudança de status e cancelamento simultâneos não partem do mesmo
    # status lido.
    pedido = verificar_pedido_acessivel(usuario, pedido_id, repositorio.travar(pedido_id))
    validar_transicao(pedido.status, novo_status)
    alterado = repositorio.atualizar_status(pedido.id, novo_status)
    _auditar_pedido(
        conexao,
        usuario.id,
        AcaoAuditoria.STATUS_ALTERADO,
        alterado,
        {"status": pedido.status},
        {"status": alterado.status},
    )
    return pedido.status, alterado


def cancelar_pedido(
    conexao: Connection,
    usuario: UsuarioAutenticado,
    gateway: GatewayPagamento,
    pedido_id: int,
    motivo: str,
) -> tuple[Pedido, bool]:
    repositorio = RepositorioPedidos(conexao)
    pedido = verificar_pedido_acessivel(usuario, pedido_id, repositorio.travar(pedido_id))
    verificar_cancelamento(usuario.perfil, pedido.status)
    pagamento_estornado = estornar_pagamento_aprovado(conexao, gateway, usuario.id, pedido)
    estornar_pontos(conexao, pedido, TipoTransacaoFidelidade.RESGATE)
    itens = repositorio.listar_itens(pedido.id)
    # Trava sem olhar o cardápio: o estoque volta mesmo que o produto tenha saído de
    # oferta depois do pedido (RN07).
    estoques = RepositorioEstoque(conexao).travar_varios(
        pedido.unidade_id, [item.produto_id for item in itens]
    )
    _movimentar_itens(
        conexao,
        usuario.id,
        pedido.id,
        itens,
        estoques,
        TipoMovimentacao.ENTRADA,
        f"Cancelamento do pedido {pedido.id}",
    )
    cancelado = repositorio.cancelar(pedido.id, motivo)
    _auditar_pedido(
        conexao,
        usuario.id,
        AcaoAuditoria.PEDIDO_CANCELADO,
        cancelado,
        {"status": pedido.status},
        {"status": cancelado.status, "motivoCancelamento": cancelado.motivo_cancelamento},
    )
    return cancelado, pagamento_estornado

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from src.domain.erros.erros import (
    AcessoNegado,
    DadosInvalidos,
    DetalheErro,
    EstoqueInsuficiente,
    PagamentoNaoPermitido,
    ProdutoIndisponivelNaUnidade,
    RecursoNaoEncontrado,
    TransicaoStatusInvalida,
)
from src.domain.pagamento.pagamento import FormaPagamento
from src.domain.pedido.pedido import (
    VALOR_MAXIMO_PEDIDO,
    CanalPedido,
    ItemPrecificado,
    ItemSolicitado,
    Pedido,
    StatusPedido,
    calcular_subtotal,
    precificar_itens,
    validar_itens_distintos,
    validar_origem_do_pedido,
    validar_transicao,
    verificar_acesso_ao_pedido,
    verificar_aguardando_pagamento,
    verificar_cancelamento,
    verificar_pedido_acessivel,
    verificar_status_manual,
)
from src.domain.produto.produto import Produto
from src.domain.usuario.usuario import Perfil, UsuarioAutenticado

UNIDADE = 1
TAPIOCA = 1
CUSCUZ = 2
PRODUTO_INEXISTENTE = 99
CLIENTE_ID = 7
OUTRA_UNIDADE = 2
PEDIDO_ID = 10
AGORA = datetime(2026, 10, 4, tzinfo=UTC)


def _produto(produto_id: int, preco: str) -> Produto:
    return Produto(
        id=produto_id,
        nome=f"Produto {produto_id}",
        descricao=None,
        preco=Decimal(preco),
        ativo=True,
        disponivel_de=None,
        disponivel_ate=None,
        created_at=AGORA,
        updated_at=AGORA,
    )


PRODUTOS = {TAPIOCA: _produto(TAPIOCA, "18.90"), CUSCUZ: _produto(CUSCUZ, "24.90")}


@pytest.mark.parametrize(
    ("perfil", "canal"),
    [
        (Perfil.CLIENTE, CanalPedido.APP),
        (Perfil.CLIENTE, CanalPedido.TOTEM),
        (Perfil.CLIENTE, CanalPedido.PICKUP),
        (Perfil.CLIENTE, CanalPedido.WEB),
        (Perfil.ATENDENTE, CanalPedido.BALCAO),
    ],
)
def test_canal_coerente_com_o_perfil_e_aceito(perfil, canal):
    validar_origem_do_pedido(perfil, canal, None)


@pytest.mark.parametrize(
    ("perfil", "canal"),
    [
        (Perfil.CLIENTE, CanalPedido.BALCAO),
        (Perfil.ATENDENTE, CanalPedido.APP),
        (Perfil.ATENDENTE, CanalPedido.WEB),
    ],
)
def test_canal_incoerente_com_o_perfil_e_recusado(perfil, canal):
    with pytest.raises(DadosInvalidos) as erro:
        validar_origem_do_pedido(perfil, canal, None)

    assert erro.value.detalhes == [
        DetalheErro("canalPedido", f"Canal {canal} não permitido para o perfil {perfil}")
    ]


def test_cliente_nao_informa_cliente_id():
    with pytest.raises(DadosInvalidos) as erro:
        validar_origem_do_pedido(Perfil.CLIENTE, CanalPedido.APP, CLIENTE_ID)

    assert erro.value.detalhes == [DetalheErro("clienteId", "Não se aplica ao perfil CLIENTE")]


def test_atendente_informa_cliente_id():
    validar_origem_do_pedido(Perfil.ATENDENTE, CanalPedido.BALCAO, CLIENTE_ID)


def test_produto_repetido_e_recusado():
    itens = [ItemSolicitado(TAPIOCA, 1), ItemSolicitado(CUSCUZ, 1), ItemSolicitado(TAPIOCA, 2)]

    with pytest.raises(DadosInvalidos) as erro:
        validar_itens_distintos(itens)

    assert erro.value.detalhes == [DetalheErro("itens[2].produtoId", "Produto repetido no pedido")]


def test_itens_copiam_o_preco_do_produto():
    itens = [ItemSolicitado(TAPIOCA, 2), ItemSolicitado(CUSCUZ, 1)]

    precificados = precificar_itens(
        itens, PRODUTOS, {TAPIOCA, CUSCUZ}, {TAPIOCA: 5, CUSCUZ: 1}, UNIDADE
    )

    assert precificados == [
        ItemPrecificado(TAPIOCA, 2, Decimal("18.90")),
        ItemPrecificado(CUSCUZ, 1, Decimal("24.90")),
    ]


def test_produto_inexistente_e_recusado():
    with pytest.raises(RecursoNaoEncontrado) as erro:
        precificar_itens([ItemSolicitado(PRODUTO_INEXISTENTE, 1)], PRODUTOS, set(), {}, UNIDADE)

    assert erro.value.mensagem == f"Produto {PRODUTO_INEXISTENTE} não encontrado"


def test_produto_nao_ofertado_e_recusado_apontando_o_item():
    itens = [ItemSolicitado(TAPIOCA, 1), ItemSolicitado(CUSCUZ, 1)]

    with pytest.raises(ProdutoIndisponivelNaUnidade) as erro:
        precificar_itens(itens, PRODUTOS, {TAPIOCA}, {TAPIOCA: 5, CUSCUZ: 1}, UNIDADE)

    assert erro.value.detalhes == [
        DetalheErro("itens[1].produtoId", f"Indisponível na unidade {UNIDADE}")
    ]


def test_produto_ofertado_sem_linha_de_estoque_travada_e_indisponivel():
    itens = [ItemSolicitado(TAPIOCA, 1), ItemSolicitado(CUSCUZ, 1)]

    with pytest.raises(ProdutoIndisponivelNaUnidade) as erro:
        precificar_itens(itens, PRODUTOS, {TAPIOCA, CUSCUZ}, {TAPIOCA: 5}, UNIDADE)

    assert erro.value.detalhes == [
        DetalheErro("itens[1].produtoId", f"Indisponível na unidade {UNIDADE}")
    ]


def test_quantidade_acima_do_saldo_e_recusada_com_o_disponivel():
    itens = [ItemSolicitado(TAPIOCA, 6), ItemSolicitado(CUSCUZ, 1)]

    with pytest.raises(EstoqueInsuficiente) as erro:
        precificar_itens(itens, PRODUTOS, {TAPIOCA, CUSCUZ}, {TAPIOCA: 5, CUSCUZ: 1}, UNIDADE)

    assert erro.value.detalhes == [DetalheErro("itens[0].quantidade", "Disponível: 5")]


def test_quantidade_igual_ao_saldo_e_aceita():
    [item] = precificar_itens([ItemSolicitado(CUSCUZ, 1)], PRODUTOS, {CUSCUZ}, {CUSCUZ: 1}, UNIDADE)

    assert item.quantidade == 1


def test_subtotal_soma_quantidade_vezes_preco():
    itens = [
        ItemPrecificado(TAPIOCA, 2, Decimal("18.90")),
        ItemPrecificado(CUSCUZ, 1, Decimal("24.90")),
    ]

    assert calcular_subtotal(itens) == Decimal("62.70")


def test_subtotal_acima_do_teto_e_recusado():
    with pytest.raises(DadosInvalidos) as erro:
        calcular_subtotal([ItemPrecificado(TAPIOCA, 2, VALOR_MAXIMO_PEDIDO)])

    assert erro.value.detalhes == [DetalheErro("itens", f"Total passa de {VALOR_MAXIMO_PEDIDO}")]


def _pedido_do_cliente(cliente_id: int | None) -> Pedido:
    return Pedido(
        id=PEDIDO_ID,
        cliente_id=cliente_id,
        unidade_id=UNIDADE,
        canal_pedido=CanalPedido.APP,
        status=StatusPedido.AGUARDANDO_PAGAMENTO,
        forma_pagamento=FormaPagamento.MOCK,
        subtotal=Decimal("18.90"),
        desconto=Decimal(0),
        total=Decimal("18.90"),
        criado_por_id=CLIENTE_ID,
        motivo_cancelamento=None,
        created_at=AGORA,
        updated_at=AGORA,
    )


def _usuario(perfil: Perfil, usuario_id: int = CLIENTE_ID, unidade_id: int | None = None):
    return UsuarioAutenticado(id=usuario_id, perfil=perfil, unidade_id=unidade_id, sessao_id=1)


def test_cliente_acessa_o_proprio_pedido():
    verificar_acesso_ao_pedido(_usuario(Perfil.CLIENTE), _pedido_do_cliente(CLIENTE_ID))


@pytest.mark.parametrize("dono", [CLIENTE_ID + 1, None])
def test_pedido_de_outro_cliente_responde_como_inexistente(dono):
    with pytest.raises(RecursoNaoEncontrado) as erro:
        verificar_acesso_ao_pedido(_usuario(Perfil.CLIENTE), _pedido_do_cliente(dono))

    assert erro.value.mensagem == f"Pedido {PEDIDO_ID} não encontrado"


@pytest.mark.parametrize("perfil", [Perfil.ATENDENTE, Perfil.COZINHA, Perfil.GERENTE])
def test_funcionario_acessa_pedido_da_propria_unidade(perfil):
    verificar_acesso_ao_pedido(_usuario(perfil, 1, UNIDADE), _pedido_do_cliente(CLIENTE_ID))


@pytest.mark.parametrize("perfil", [Perfil.ATENDENTE, Perfil.COZINHA, Perfil.GERENTE])
def test_funcionario_nao_acessa_pedido_de_outra_unidade(perfil):
    with pytest.raises(AcessoNegado):
        verificar_acesso_ao_pedido(
            _usuario(perfil, 1, OUTRA_UNIDADE), _pedido_do_cliente(CLIENTE_ID)
        )


def test_admin_acessa_pedido_de_qualquer_unidade():
    verificar_acesso_ao_pedido(_usuario(Perfil.ADMIN, 1), _pedido_do_cliente(CLIENTE_ID))


@pytest.mark.parametrize(
    ("atual", "novo"),
    [
        (StatusPedido.AGUARDANDO_PAGAMENTO, StatusPedido.EM_PREPARO),
        (StatusPedido.AGUARDANDO_PAGAMENTO, StatusPedido.CANCELADO),
        (StatusPedido.EM_PREPARO, StatusPedido.PRONTO),
        (StatusPedido.EM_PREPARO, StatusPedido.CANCELADO),
        (StatusPedido.PRONTO, StatusPedido.ENTREGUE),
    ],
)
def test_transicao_do_ciclo_de_vida_e_aceita(atual, novo):
    validar_transicao(atual, novo)


@pytest.mark.parametrize(
    ("atual", "novo"),
    [
        (StatusPedido.AGUARDANDO_PAGAMENTO, StatusPedido.PRONTO),
        (StatusPedido.AGUARDANDO_PAGAMENTO, StatusPedido.ENTREGUE),
        (StatusPedido.EM_PREPARO, StatusPedido.ENTREGUE),
        (StatusPedido.EM_PREPARO, StatusPedido.AGUARDANDO_PAGAMENTO),
        (StatusPedido.PRONTO, StatusPedido.CANCELADO),
        (StatusPedido.ENTREGUE, StatusPedido.CANCELADO),
        (StatusPedido.CANCELADO, StatusPedido.EM_PREPARO),
    ],
)
def test_transicao_fora_do_ciclo_de_vida_e_recusada(atual, novo):
    with pytest.raises(TransicaoStatusInvalida) as erro:
        validar_transicao(atual, novo)

    assert erro.value.mensagem == f"Pedido em {atual} não pode passar para {novo}"


@pytest.mark.parametrize(
    ("perfil", "novo"),
    [
        (Perfil.COZINHA, StatusPedido.PRONTO),
        (Perfil.GERENTE, StatusPedido.PRONTO),
        (Perfil.ADMIN, StatusPedido.PRONTO),
        (Perfil.ATENDENTE, StatusPedido.ENTREGUE),
        (Perfil.GERENTE, StatusPedido.ENTREGUE),
        (Perfil.ADMIN, StatusPedido.ENTREGUE),
    ],
)
def test_perfil_da_matriz_marca_o_status(perfil, novo):
    verificar_status_manual(perfil, novo)


@pytest.mark.parametrize(
    ("perfil", "novo"),
    [(Perfil.COZINHA, StatusPedido.ENTREGUE), (Perfil.ATENDENTE, StatusPedido.PRONTO)],
)
def test_perfil_fora_da_matriz_nao_marca_o_status(perfil, novo):
    with pytest.raises(AcessoNegado):
        verificar_status_manual(perfil, novo)


@pytest.mark.parametrize(
    "novo",
    [StatusPedido.AGUARDANDO_PAGAMENTO, StatusPedido.EM_PREPARO, StatusPedido.CANCELADO],
)
def test_status_de_outro_fluxo_nao_e_marcado_manualmente(novo):
    with pytest.raises(DadosInvalidos) as erro:
        verificar_status_manual(Perfil.ADMIN, novo)

    assert erro.value.detalhes == [
        DetalheErro("status", "Deve ser um destes valores: 'PRONTO' ou 'ENTREGUE'")
    ]


@pytest.mark.parametrize(
    ("perfil", "status"),
    [
        (Perfil.CLIENTE, StatusPedido.AGUARDANDO_PAGAMENTO),
        (Perfil.ATENDENTE, StatusPedido.AGUARDANDO_PAGAMENTO),
        (Perfil.GERENTE, StatusPedido.AGUARDANDO_PAGAMENTO),
        (Perfil.ADMIN, StatusPedido.AGUARDANDO_PAGAMENTO),
        (Perfil.GERENTE, StatusPedido.EM_PREPARO),
        (Perfil.ADMIN, StatusPedido.EM_PREPARO),
    ],
)
def test_cancelamento_permitido_ao_perfil(perfil, status):
    verificar_cancelamento(perfil, status)


@pytest.mark.parametrize("perfil", [Perfil.CLIENTE, Perfil.ATENDENTE])
def test_pedido_pago_so_e_cancelado_pela_gerencia(perfil):
    with pytest.raises(AcessoNegado) as erro:
        verificar_cancelamento(perfil, StatusPedido.EM_PREPARO)

    assert erro.value.mensagem == f"Perfil {perfil} não pode cancelar pedido em EM_PREPARO"


@pytest.mark.parametrize(
    "status", [StatusPedido.PRONTO, StatusPedido.ENTREGUE, StatusPedido.CANCELADO]
)
def test_pedido_pronto_entregue_ou_cancelado_nao_e_cancelado(status):
    with pytest.raises(TransicaoStatusInvalida):
        verificar_cancelamento(Perfil.ADMIN, status)


def test_pedido_inexistente_nao_e_encontrado():
    with pytest.raises(RecursoNaoEncontrado) as erro:
        verificar_pedido_acessivel(_usuario(Perfil.CLIENTE), PEDIDO_ID, None)

    assert erro.value.mensagem == f"Pedido {PEDIDO_ID} não encontrado"


def test_pedido_acessivel_e_devolvido():
    pedido = _pedido_do_cliente(CLIENTE_ID)

    assert verificar_pedido_acessivel(_usuario(Perfil.CLIENTE), PEDIDO_ID, pedido) is pedido


def test_pedido_aguardando_pagamento_aceita_pagamento():
    verificar_aguardando_pagamento(_pedido_do_cliente(CLIENTE_ID))


@pytest.mark.parametrize(
    "status",
    [StatusPedido.EM_PREPARO, StatusPedido.PRONTO, StatusPedido.ENTREGUE, StatusPedido.CANCELADO],
)
def test_pedido_fora_de_aguardando_pagamento_recusa_pagamento(status):
    pedido = replace(_pedido_do_cliente(CLIENTE_ID), status=status)

    with pytest.raises(PagamentoNaoPermitido) as erro:
        verificar_aguardando_pagamento(pedido)

    assert erro.value.mensagem == (
        f"Pedido {PEDIDO_ID} está {status} e não aceita pagamento nem resgate"
    )

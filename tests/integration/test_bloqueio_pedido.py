import pytest
from psycopg.errors import LockNotAvailable
from sqlalchemy import select, text, update
from sqlalchemy.exc import OperationalError

from src.application.pagamentos.pagamentos import solicitar_pagamento
from src.application.pedidos.pedidos import alterar_status, criar_pedido
from src.domain.pagamento.pagamento import FormaPagamento
from src.domain.pedido.pedido import CanalPedido, DadosPedido, ItemSolicitado, StatusPedido
from src.domain.usuario.usuario import Perfil, UsuarioAutenticado
from src.infrastructure.database.seeds.dados_iniciais import DOMINIO_EMAIL
from src.infrastructure.database.tabelas import estoque, pedido, usuario
from src.infrastructure.pagamento.gateway_mock import GatewayPagamentoMock, ResultadoSimulado

UNIDADE_RECIFE = 1
TAPIOCA = 1
PEDIDO_DE_TAPIOCA = DadosPedido(
    canal_pedido=CanalPedido.APP,
    unidade_id=UNIDADE_RECIFE,
    cliente_id=None,
    itens=[ItemSolicitado(TAPIOCA, 1)],
    forma_pagamento=FormaPagamento.MOCK,
)
# O lock acontece antes de qualquer gravação: o id não precisa existir no banco.
CLIENTE = UsuarioAutenticado(id=1, perfil=Perfil.CLIENTE, unidade_id=None, sessao_id=1)
COZINHA = UsuarioAutenticado(id=1, perfil=Perfil.COZINHA, unidade_id=UNIDADE_RECIFE, sessao_id=1)
# A outra transação segura o lock até o fim do teste: sem limite, a espera não acabaria.
ESPERA_MAXIMA_PELO_LOCK = "200ms"
TIMEOUT_GATEWAY_SEGUNDOS = 3.0


def test_pedido_espera_o_lock_do_estoque(banco_semeado):
    with banco_semeado.connect() as primeira, banco_semeado.connect() as segunda:
        primeira.begin()
        primeira.execute(
            select(estoque)
            .where(estoque.c.unidade_id == UNIDADE_RECIFE, estoque.c.produto_id == TAPIOCA)
            .with_for_update()
        )
        segunda.begin()
        segunda.execute(text(f"SET LOCAL lock_timeout = '{ESPERA_MAXIMA_PELO_LOCK}'"))

        with pytest.raises(OperationalError) as erro:
            criar_pedido(segunda, CLIENTE, PEDIDO_DE_TAPIOCA)

    assert isinstance(erro.value.orig, LockNotAvailable)


def _novo_pedido(banco_semeado) -> int:
    with banco_semeado.begin() as conexao:
        cliente_id = conexao.execute(
            select(usuario.c.id).where(usuario.c.email == f"cliente@{DOMINIO_EMAIL}")
        ).scalar_one()
        cliente = UsuarioAutenticado(
            id=cliente_id, perfil=Perfil.CLIENTE, unidade_id=None, sessao_id=1
        )
        criado, _ = criar_pedido(conexao, cliente, PEDIDO_DE_TAPIOCA)
    return criado.id


def _pedido_em_preparo(banco_semeado) -> int:
    pedido_id = _novo_pedido(banco_semeado)
    with banco_semeado.begin() as conexao:
        conexao.execute(
            update(pedido).where(pedido.c.id == pedido_id).values(status=StatusPedido.EM_PREPARO)
        )
    return pedido_id


def test_mudanca_de_status_espera_o_lock_do_pedido(banco_semeado):
    pedido_id = _pedido_em_preparo(banco_semeado)
    with banco_semeado.connect() as primeira, banco_semeado.connect() as segunda:
        primeira.begin()
        primeira.execute(select(pedido).where(pedido.c.id == pedido_id).with_for_update())
        segunda.begin()
        segunda.execute(text(f"SET LOCAL lock_timeout = '{ESPERA_MAXIMA_PELO_LOCK}'"))

        with pytest.raises(OperationalError) as erro:
            alterar_status(segunda, COZINHA, pedido_id, StatusPedido.PRONTO)

    assert isinstance(erro.value.orig, LockNotAvailable)


def test_pagamento_espera_o_lock_do_pedido(banco_semeado):
    pedido_id = _novo_pedido(banco_semeado)
    gateway = GatewayPagamentoMock(ResultadoSimulado.APROVADO, TIMEOUT_GATEWAY_SEGUNDOS)
    with banco_semeado.connect() as primeira, banco_semeado.connect() as segunda:
        primeira.begin()
        primeira.execute(select(pedido).where(pedido.c.id == pedido_id).with_for_update())
        segunda.begin()
        segunda.execute(text(f"SET LOCAL lock_timeout = '{ESPERA_MAXIMA_PELO_LOCK}'"))

        with pytest.raises(OperationalError) as erro:
            solicitar_pagamento(segunda, CLIENTE, gateway, pedido_id)

    assert isinstance(erro.value.orig, LockNotAvailable)

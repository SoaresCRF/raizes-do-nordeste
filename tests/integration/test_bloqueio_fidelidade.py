import pytest
from psycopg.errors import LockNotAvailable
from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError

from src.application.fidelidade.fidelidade import resgatar_pontos
from src.application.pedidos.pedidos import criar_pedido
from src.domain.pagamento.pagamento import FormaPagamento
from src.domain.pedido.pedido import CanalPedido, DadosPedido, ItemSolicitado
from src.domain.usuario.usuario import Perfil, UsuarioAutenticado
from src.infrastructure.database.repositorios.usuarios import RepositorioUsuarios
from src.infrastructure.database.seeds.dados_iniciais import DOMINIO_EMAIL
from src.infrastructure.database.tabelas import usuario

TAPIOCA = 1
UNIDADE_RECIFE = 1
# A outra transação segura o lock até o fim do teste: sem limite, a espera não acabaria.
ESPERA_MAXIMA_PELO_LOCK = "200ms"


def test_resgate_espera_o_lock_do_cliente(banco_semeado):
    with banco_semeado.begin() as conexao:
        cliente_id = conexao.execute(
            select(usuario.c.id).where(usuario.c.email == f"cliente@{DOMINIO_EMAIL}")
        ).scalar_one()
        cliente = UsuarioAutenticado(
            id=cliente_id, perfil=Perfil.CLIENTE, unidade_id=None, sessao_id=1
        )
        criado, _ = criar_pedido(
            conexao,
            cliente,
            DadosPedido(
                canal_pedido=CanalPedido.APP,
                unidade_id=UNIDADE_RECIFE,
                cliente_id=None,
                itens=[ItemSolicitado(TAPIOCA, 1)],
                forma_pagamento=FormaPagamento.MOCK,
            ),
        )
    with banco_semeado.connect() as primeira, banco_semeado.connect() as segunda:
        primeira.begin()
        RepositorioUsuarios(primeira).travar(cliente_id)
        segunda.begin()
        segunda.execute(text(f"SET LOCAL lock_timeout = '{ESPERA_MAXIMA_PELO_LOCK}'"))

        with pytest.raises(OperationalError) as erro:
            resgatar_pontos(segunda, cliente, criado.id, 100)

    assert isinstance(erro.value.orig, LockNotAvailable)

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, insert, select, text
from sqlalchemy.exc import IntegrityError

from src.domain.estoque.estoque import TipoMovimentacao
from src.domain.pagamento.pagamento import FormaPagamento
from src.domain.pedido.pedido import CanalPedido, StatusPedido
from src.domain.unidade.unidade import TipoUnidade
from src.domain.usuario.usuario import Perfil
from src.infrastructure.database.tabelas import (
    estoque,
    item_pedido,
    movimentacao_estoque,
    pedido,
    produto,
    unidade,
    usuario,
)


def _criar_unidade(conexao) -> int:
    return conexao.execute(
        insert(unidade).returning(unidade.c.id),
        {
            "nome": "Unidade Teste",
            "cidade": "Recife",
            "uf": "PE",
            "regiao": "Nordeste",
            "tipo": TipoUnidade.COZINHA_COMPLETA,
        },
    ).scalar_one()


def _dados_usuario(**campos) -> dict:
    return {
        "nome": "Usuário Teste",
        "email": "teste@raizesdonordeste.com.br",
        "senha_hash": "hash",
        "perfil": Perfil.CLIENTE,
        "unidade_id": None,
    } | campos


def test_rejeita_email_duplicado(conexao_teste):
    conexao_teste.execute(insert(usuario), _dados_usuario())

    with pytest.raises(IntegrityError):
        conexao_teste.execute(insert(usuario), _dados_usuario(nome="Outro Usuário"))


def test_rejeita_funcionario_de_unidade_sem_unidade(conexao_teste):
    with pytest.raises(IntegrityError):
        conexao_teste.execute(insert(usuario), _dados_usuario(perfil=Perfil.GERENTE))


def test_rejeita_cliente_vinculado_a_unidade(conexao_teste):
    unidade_id = _criar_unidade(conexao_teste)

    with pytest.raises(IntegrityError):
        conexao_teste.execute(insert(usuario), _dados_usuario(unidade_id=unidade_id))


def test_aceita_atendente_lotado_em_unidade(conexao_teste):
    unidade_id = _criar_unidade(conexao_teste)

    conexao_teste.execute(
        insert(usuario), _dados_usuario(perfil=Perfil.ATENDENTE, unidade_id=unidade_id)
    )

    total = conexao_teste.execute(select(func.count()).select_from(usuario)).scalar_one()
    assert total == 1


def test_rejeita_perfil_fora_do_enum(conexao_teste):
    with pytest.raises(IntegrityError):
        conexao_teste.execute(
            text(
                "insert into usuario (nome, email, senha_hash, perfil) "
                "values ('Teste', 'x@raizesdonordeste.com.br', 'hash', 'VISITANTE')"
            )
        )


def _criar_produto(conexao, **campos) -> int:
    return conexao.execute(
        insert(produto).returning(produto.c.id),
        {"nome": "Tapioca", "preco": Decimal("18.90")} | campos,
    ).scalar_one()


def test_rejeita_produto_com_preco_zero(conexao_teste):
    with pytest.raises(IntegrityError):
        _criar_produto(conexao_teste, preco=Decimal("0"))


def test_rejeita_periodo_de_disponibilidade_invertido(conexao_teste):
    with pytest.raises(IntegrityError):
        _criar_produto(
            conexao_teste, disponivel_de=date(2026, 7, 31), disponivel_ate=date(2026, 6, 1)
        )


def test_rejeita_saldo_de_estoque_negativo(conexao_teste):
    estoque_id = conexao_teste.execute(
        insert(estoque).returning(estoque.c.id),
        {
            "unidade_id": _criar_unidade(conexao_teste),
            "produto_id": _criar_produto(conexao_teste),
            "quantidade": 1,
        },
    ).scalar_one()

    with pytest.raises(IntegrityError):
        conexao_teste.execute(
            estoque.update().where(estoque.c.id == estoque_id).values(quantidade=-1)
        )


def test_rejeita_estoque_duplicado_para_unidade_e_produto(conexao_teste):
    registro = {
        "unidade_id": _criar_unidade(conexao_teste),
        "produto_id": _criar_produto(conexao_teste),
        "quantidade": 1,
    }
    conexao_teste.execute(insert(estoque), registro)

    with pytest.raises(IntegrityError):
        conexao_teste.execute(insert(estoque), registro)


def _criar_cliente(conexao) -> int:
    return conexao.execute(insert(usuario).returning(usuario.c.id), _dados_usuario()).scalar_one()


def _dados_pedido(conexao, **campos) -> dict:
    cliente_id = _criar_cliente(conexao)
    return {
        "cliente_id": cliente_id,
        "unidade_id": _criar_unidade(conexao),
        "canal_pedido": CanalPedido.APP,
        "forma_pagamento": FormaPagamento.MOCK,
        "subtotal": Decimal("37.80"),
        "desconto": Decimal("0"),
        "total": Decimal("37.80"),
        "criado_por_id": cliente_id,
    } | campos


def test_pedido_nasce_aguardando_pagamento(conexao_teste):
    status = conexao_teste.execute(
        insert(pedido).returning(pedido.c.status), _dados_pedido(conexao_teste)
    ).scalar_one()

    assert status == StatusPedido.AGUARDANDO_PAGAMENTO


def test_rejeita_total_inconsistente(conexao_teste):
    with pytest.raises(IntegrityError):
        conexao_teste.execute(insert(pedido), _dados_pedido(conexao_teste, total=Decimal("1.00")))


def test_rejeita_desconto_maior_que_subtotal(conexao_teste):
    with pytest.raises(IntegrityError):
        conexao_teste.execute(
            insert(pedido),
            _dados_pedido(
                conexao_teste,
                subtotal=Decimal("10.00"),
                desconto=Decimal("15.00"),
                total=Decimal("-5.00"),
            ),
        )


def test_rejeita_item_com_quantidade_zero(conexao_teste):
    pedido_id = conexao_teste.execute(
        insert(pedido).returning(pedido.c.id), _dados_pedido(conexao_teste)
    ).scalar_one()

    with pytest.raises(IntegrityError):
        conexao_teste.execute(
            insert(item_pedido),
            {
                "pedido_id": pedido_id,
                "produto_id": _criar_produto(conexao_teste),
                "quantidade": 0,
                "preco_unitario": Decimal("18.90"),
            },
        )


def test_rejeita_movimentacao_com_quantidade_zero(conexao_teste):
    estoque_id = conexao_teste.execute(
        insert(estoque).returning(estoque.c.id),
        {
            "unidade_id": _criar_unidade(conexao_teste),
            "produto_id": _criar_produto(conexao_teste),
            "quantidade": 10,
        },
    ).scalar_one()

    with pytest.raises(IntegrityError):
        conexao_teste.execute(
            insert(movimentacao_estoque),
            {
                "estoque_id": estoque_id,
                "tipo": TipoMovimentacao.ENTRADA,
                "quantidade": 0,
                "motivo": "Teste",
                "usuario_id": _criar_cliente(conexao_teste),
            },
        )

from decimal import Decimal

import pytest
from sqlalchemy import func, select, text

from src.domain.unidade.unidade import TipoUnidade
from src.domain.usuario.usuario import PERFIS_LOTADOS_EM_UNIDADE, Perfil
from src.infrastructure.database.seeds.dados_iniciais import SENHA_DESENVOLVIMENTO, popular_banco
from src.infrastructure.database.tabelas import (
    consentimento,
    estoque,
    metadata,
    produto,
    unidade,
    usuario,
)
from src.infrastructure.seguranca.hash_senha import HashSenha

VALOR_MINIMO_PEDIDO_T50 = Decimal("100.00")


@pytest.fixture(scope="module")
def engine_populado(engine_teste):
    with engine_teste.begin() as conexao:
        popular_banco(conexao, HashSenha())
    yield engine_teste
    with engine_teste.begin() as conexao:
        conexao.execute(
            text(f"TRUNCATE TABLE {', '.join(metadata.tables)} RESTART IDENTITY CASCADE")
        )


# Conexão por teste: uma conexão aberta durante o módulo seguraria locks e
# travaria o TRUNCATE do seed no último teste.
@pytest.fixture
def banco_populado(engine_populado):
    with engine_populado.connect() as conexao:
        yield conexao


def _contar_usuarios(conexao) -> int:
    return conexao.execute(select(func.count()).select_from(usuario)).scalar_one()


def _id_produto(conexao, nome: str) -> int:
    return conexao.execute(select(produto.c.id).where(produto.c.nome == nome)).scalar_one()


def _saldo(conexao, unidade_id: int, nome_produto: str) -> int | None:
    return conexao.execute(
        select(estoque.c.quantidade).where(
            estoque.c.unidade_id == unidade_id,
            estoque.c.produto_id == _id_produto(conexao, nome_produto),
        )
    ).scalar_one_or_none()


def test_unidade_1_e_recife_e_unidade_2_e_do_interior(banco_populado):
    unidades = banco_populado.execute(
        select(unidade.c.id, unidade.c.cidade, unidade.c.tipo).order_by(unidade.c.id)
    ).all()

    assert [tuple(u) for u in unidades] == [
        (1, "Recife", TipoUnidade.COZINHA_COMPLETA),
        (2, "Caruaru", TipoUnidade.FORMATO_REDUZIDO),
    ]


def test_produtos_do_estudo_de_caso_e_um_sazonal(banco_populado):
    nomes = set(banco_populado.execute(select(produto.c.nome)).scalars())
    sazonais = banco_populado.execute(
        select(func.count()).where(produto.c.disponivel_ate.is_not(None))
    ).scalar_one()

    assert {
        "Tapioca",
        "Cuscuz recheado",
        "Bolo de macaxeira",
        "Suco regional",
        "Café da manhã completo",
        "Café passado",
    } <= nomes
    assert sazonais == 1


def test_unidade_2_nao_oferece_cafe_da_manha_completo(banco_populado):
    assert _saldo(banco_populado, 2, "Café da manhã completo") is None


def test_bolo_de_macaxeira_tem_saldo_baixo_na_unidade_1(banco_populado):
    assert _saldo(banco_populado, 1, "Bolo de macaxeira") == 2


def test_pedido_do_cenario_t50_passa_de_cem_reais(banco_populado):
    precos = dict(banco_populado.execute(select(produto.c.nome, produto.c.preco)).all())

    assert (
        2 * precos["Café da manhã completo"] + precos["Cuscuz recheado"] > VALOR_MINIMO_PEDIDO_T50
    )


def test_ha_usuario_de_cada_perfil_com_a_senha_de_desenvolvimento(banco_populado):
    usuarios = banco_populado.execute(select(usuario.c.perfil, usuario.c.senha_hash)).all()
    hash_senha = HashSenha()

    assert {perfil for perfil, _ in usuarios} == set(Perfil)
    assert all(hash_senha.confere(SENHA_DESENVOLVIMENTO, senha_hash) for _, senha_hash in usuarios)


def test_cada_unidade_tem_um_gerente(banco_populado):
    unidades_com_gerente = banco_populado.execute(
        select(usuario.c.unidade_id).where(usuario.c.perfil == Perfil.GERENTE)
    ).scalars()

    assert sorted(unidades_com_gerente) == [1, 2]


def test_funcionarios_da_unidade_1_estao_lotados_nela(banco_populado):
    lotados = banco_populado.execute(
        select(usuario.c.perfil).where(
            usuario.c.perfil.in_(PERFIS_LOTADOS_EM_UNIDADE), usuario.c.unidade_id == 1
        )
    ).scalars()

    assert set(lotados) == set(PERFIS_LOTADOS_EM_UNIDADE)


def test_so_um_dos_clientes_tem_consentimento_de_fidelidade(banco_populado):
    clientes_com_consentimento = (
        banco_populado.execute(
            select(usuario.c.email)
            .join(consentimento, consentimento.c.usuario_id == usuario.c.id)
            .where(usuario.c.perfil == Perfil.CLIENTE, consentimento.c.concedido.is_(True))
        )
        .scalars()
        .all()
    )
    total_clientes = banco_populado.execute(
        select(func.count()).where(usuario.c.perfil == Perfil.CLIENTE)
    ).scalar_one()

    assert clientes_com_consentimento == ["cliente@raizesdonordeste.com.br"]
    assert total_clientes == 2


def test_seed_rodado_duas_vezes_mantem_os_mesmos_dados(engine_populado):
    with engine_populado.connect() as conexao:
        contagem_antes = _contar_usuarios(conexao)

    with engine_populado.begin() as conexao:
        popular_banco(conexao, HashSenha())

    with engine_populado.connect() as conexao:
        contagem_depois = _contar_usuarios(conexao)
        recife_id = conexao.execute(
            select(unidade.c.id).where(unidade.c.cidade == "Recife")
        ).scalar_one()

    assert contagem_depois == contagem_antes
    assert recife_id == 1

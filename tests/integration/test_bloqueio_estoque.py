import pytest
from psycopg.errors import LockNotAvailable
from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError

from src.application.estoque.estoque import movimentar_estoque
from src.domain.estoque.estoque import DadosMovimentacao, TipoMovimentacao
from src.domain.usuario.usuario import Perfil, UsuarioAutenticado
from src.infrastructure.database.tabelas import estoque

UNIDADE_RECIFE = 1
TAPIOCA = 1
ADMIN = UsuarioAutenticado(id=1, perfil=Perfil.ADMIN, unidade_id=None, sessao_id=1)
# A outra transação segura o lock até o fim do teste: sem limite, a espera não acabaria.
ESPERA_MAXIMA_PELO_LOCK = "200ms"


def test_movimentacao_espera_o_lock_da_linha_de_estoque(banco_semeado):
    saida = DadosMovimentacao(
        unidade_id=UNIDADE_RECIFE,
        produto_id=TAPIOCA,
        tipo=TipoMovimentacao.SAIDA,
        quantidade=1,
        motivo="Teste de concorrência",
    )
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
            movimentar_estoque(segunda, ADMIN, saida)

    assert isinstance(erro.value.orig, LockNotAvailable)

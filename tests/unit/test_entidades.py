from dataclasses import fields

import pytest

from src.domain.auditoria.auditoria import LogAuditoria
from src.domain.estoque.estoque import Estoque, MovimentacaoEstoque
from src.domain.fidelidade.fidelidade import TransacaoFidelidade
from src.domain.pagamento.pagamento import Pagamento
from src.domain.pedido.pedido import ItemPedido, Pedido
from src.domain.produto.produto import Produto
from src.domain.unidade.unidade import Unidade
from src.domain.usuario.usuario import Consentimento, Sessao, Usuario
from src.infrastructure.database import tabelas

ENTIDADES_E_TABELAS = [
    (Unidade, tabelas.unidade),
    (Usuario, tabelas.usuario),
    (Consentimento, tabelas.consentimento),
    (Produto, tabelas.produto),
    (Estoque, tabelas.estoque),
    (MovimentacaoEstoque, tabelas.movimentacao_estoque),
    (Pedido, tabelas.pedido),
    (ItemPedido, tabelas.item_pedido),
    (Pagamento, tabelas.pagamento),
    (TransacaoFidelidade, tabelas.transacao_fidelidade),
    (LogAuditoria, tabelas.log_auditoria),
    (Sessao, tabelas.sessao),
]


@pytest.mark.parametrize(
    ("entidade", "tabela"),
    ENTIDADES_E_TABELAS,
    ids=[entidade.__name__ for entidade, _ in ENTIDADES_E_TABELAS],
)
def test_entidade_tem_as_colunas_da_tabela_na_mesma_ordem(entidade, tabela):
    assert [campo.name for campo in fields(entidade)] == [coluna.name for coluna in tabela.columns]


def test_toda_tabela_tem_entidade():
    assert {tabela.name for _, tabela in ENTIDADES_E_TABELAS} == set(tabelas.metadata.tables)

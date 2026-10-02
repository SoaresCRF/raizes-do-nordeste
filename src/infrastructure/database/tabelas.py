from enum import StrEnum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Identity,
    Index,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
    true,
)

from src.domain.estoque.estoque import TipoMovimentacao
from src.domain.pagamento.pagamento import FormaPagamento
from src.domain.pedido.pedido import CanalPedido, StatusPedido
from src.domain.unidade.unidade import TipoUnidade
from src.domain.usuario.usuario import PERFIS_LOTADOS_EM_UNIDADE, Perfil

# Nomes determinísticos de constraints e índices: o autogenerate e o downgrade
# dependem deles para criar e remover exatamente os mesmos objetos.
CONVENCAO_DE_NOMES = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=CONVENCAO_DE_NOMES)


def _enum(tipo: type[StrEnum], nome: str) -> Enum:
    # VARCHAR + CHECK em vez de ENUM nativo: o rollback não deixa tipos para trás
    # e acrescentar um valor não exige ALTER TYPE.
    return Enum(tipo, name=nome, native_enum=False, create_constraint=True)


def _colunas_de_data() -> list[Column]:
    return [
        Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
        Column(
            "updated_at",
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
            onupdate=func.now(),
        ),
    ]


unidade = Table(
    "unidade",
    metadata,
    Column("id", Integer, Identity(), primary_key=True),
    Column("nome", String(120), nullable=False),
    Column("cidade", String(80), nullable=False),
    Column("uf", String(2), nullable=False),
    Column("regiao", String(40), nullable=False),
    Column("tipo", _enum(TipoUnidade, "tipo_unidade"), nullable=False),
    Column("ativa", Boolean, nullable=False, server_default=true()),
    *_colunas_de_data(),
)

_PERFIS_LOTADOS_SQL = ", ".join(f"'{perfil}'" for perfil in PERFIS_LOTADOS_EM_UNIDADE)

usuario = Table(
    "usuario",
    metadata,
    Column("id", Integer, Identity(), primary_key=True),
    Column("nome", String(120), nullable=False),
    Column("email", String(160), nullable=False, unique=True),
    Column("senha_hash", Text, nullable=False),
    Column("perfil", _enum(Perfil, "perfil"), nullable=False),
    Column("unidade_id", Integer, ForeignKey("unidade.id")),
    Column("ativo", Boolean, nullable=False, server_default=true()),
    Column("anonimizado_em", DateTime(timezone=True)),
    *_colunas_de_data(),
    CheckConstraint(
        f"(perfil IN ({_PERFIS_LOTADOS_SQL})) = (unidade_id IS NOT NULL)",
        name="unidade_conforme_perfil",
    ),
)

produto = Table(
    "produto",
    metadata,
    Column("id", Integer, Identity(), primary_key=True),
    Column("nome", String(120), nullable=False),
    Column("descricao", Text),
    Column("preco", Numeric(10, 2), nullable=False),
    Column("ativo", Boolean, nullable=False, server_default=true()),
    Column("disponivel_de", Date),
    Column("disponivel_ate", Date),
    *_colunas_de_data(),
    CheckConstraint("preco > 0", name="preco_positivo"),
    CheckConstraint(
        "disponivel_de IS NULL OR disponivel_ate IS NULL OR disponivel_de <= disponivel_ate",
        name="periodo_disponibilidade_valido",
    ),
)

estoque = Table(
    "estoque",
    metadata,
    Column("id", Integer, Identity(), primary_key=True),
    Column("unidade_id", Integer, ForeignKey("unidade.id"), nullable=False),
    Column("produto_id", Integer, ForeignKey("produto.id"), nullable=False),
    Column("quantidade", Integer, nullable=False),
    *_colunas_de_data(),
    UniqueConstraint("unidade_id", "produto_id"),
    CheckConstraint("quantidade >= 0", name="quantidade_nao_negativa"),
)

pedido = Table(
    "pedido",
    metadata,
    Column("id", Integer, Identity(), primary_key=True),
    Column("cliente_id", Integer, ForeignKey("usuario.id"), index=True),
    Column("unidade_id", Integer, ForeignKey("unidade.id"), nullable=False),
    Column("canal_pedido", _enum(CanalPedido, "canal_pedido"), nullable=False, index=True),
    Column(
        "status",
        _enum(StatusPedido, "status_pedido"),
        nullable=False,
        server_default=StatusPedido.AGUARDANDO_PAGAMENTO,
    ),
    Column("forma_pagamento", _enum(FormaPagamento, "forma_pagamento"), nullable=False),
    Column("subtotal", Numeric(10, 2), nullable=False),
    Column("desconto", Numeric(10, 2), nullable=False, server_default="0"),
    Column("total", Numeric(10, 2), nullable=False),
    Column("criado_por_id", Integer, ForeignKey("usuario.id"), nullable=False),
    Column("motivo_cancelamento", String(200)),
    *_colunas_de_data(),
    CheckConstraint("subtotal >= 0", name="subtotal_nao_negativo"),
    CheckConstraint("desconto >= 0 AND desconto <= subtotal", name="desconto_valido"),
    CheckConstraint("total = subtotal - desconto", name="total_consistente"),
    Index("ix_pedido_unidade_id_status", "unidade_id", "status"),
)

item_pedido = Table(
    "item_pedido",
    metadata,
    Column("id", Integer, Identity(), primary_key=True),
    Column("pedido_id", Integer, ForeignKey("pedido.id"), nullable=False),
    Column("produto_id", Integer, ForeignKey("produto.id"), nullable=False),
    Column("quantidade", Integer, nullable=False),
    Column("preco_unitario", Numeric(10, 2), nullable=False),
    *_colunas_de_data(),
    CheckConstraint("quantidade > 0", name="quantidade_positiva"),
    CheckConstraint("preco_unitario > 0", name="preco_unitario_positivo"),
)

movimentacao_estoque = Table(
    "movimentacao_estoque",
    metadata,
    Column("id", Integer, Identity(), primary_key=True),
    Column("estoque_id", Integer, ForeignKey("estoque.id"), nullable=False, index=True),
    Column("tipo", _enum(TipoMovimentacao, "tipo_movimentacao"), nullable=False),
    Column("quantidade", Integer, nullable=False),
    Column("motivo", String(200), nullable=False),
    Column("pedido_id", Integer, ForeignKey("pedido.id")),
    Column("usuario_id", Integer, ForeignKey("usuario.id"), nullable=False),
    *_colunas_de_data(),
    CheckConstraint("quantidade > 0", name="quantidade_positiva"),
)

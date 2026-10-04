"""cria tabela pedido

Revision ID: 2b19486ba543
Revises: 676b732eca01
Create Date: 2026-10-02 19:15:36.965888

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "2b19486ba543"
down_revision: str | Sequence[str] | None = "676b732eca01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pedido",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("cliente_id", sa.Integer(), nullable=True),
        sa.Column("unidade_id", sa.Integer(), nullable=False),
        sa.Column(
            "canal_pedido",
            sa.Enum(
                "APP",
                "TOTEM",
                "BALCAO",
                "PICKUP",
                "WEB",
                name="canal_pedido",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "AGUARDANDO_PAGAMENTO",
                "EM_PREPARO",
                "PRONTO",
                "ENTREGUE",
                "CANCELADO",
                name="status_pedido",
                native_enum=False,
                create_constraint=True,
            ),
            server_default="AGUARDANDO_PAGAMENTO",
            nullable=False,
        ),
        sa.Column(
            "forma_pagamento",
            sa.Enum("MOCK", name="forma_pagamento", native_enum=False, create_constraint=True),
            nullable=False,
        ),
        sa.Column("subtotal", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column(
            "desconto", sa.Numeric(precision=10, scale=2), server_default="0", nullable=False
        ),
        sa.Column("total", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("criado_por_id", sa.Integer(), nullable=False),
        sa.Column("motivo_cancelamento", sa.String(length=200), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "desconto >= 0 AND desconto <= subtotal", name=op.f("ck_pedido_desconto_valido")
        ),
        sa.CheckConstraint("subtotal >= 0", name=op.f("ck_pedido_subtotal_nao_negativo")),
        sa.CheckConstraint("total = subtotal - desconto", name=op.f("ck_pedido_total_consistente")),
        sa.ForeignKeyConstraint(
            ["cliente_id"], ["usuario.id"], name=op.f("fk_pedido_cliente_id_usuario")
        ),
        sa.ForeignKeyConstraint(
            ["criado_por_id"], ["usuario.id"], name=op.f("fk_pedido_criado_por_id_usuario")
        ),
        sa.ForeignKeyConstraint(
            ["unidade_id"], ["unidade.id"], name=op.f("fk_pedido_unidade_id_unidade")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pedido")),
    )
    op.create_index(op.f("ix_pedido_canal_pedido"), "pedido", ["canal_pedido"], unique=False)
    op.create_index(op.f("ix_pedido_cliente_id"), "pedido", ["cliente_id"], unique=False)
    op.create_index("ix_pedido_unidade_id_status", "pedido", ["unidade_id", "status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_pedido_unidade_id_status", table_name="pedido")
    op.drop_index(op.f("ix_pedido_cliente_id"), table_name="pedido")
    op.drop_index(op.f("ix_pedido_canal_pedido"), table_name="pedido")
    op.drop_table("pedido")

"""cria tabela movimentacao_estoque

Revision ID: bdf942c29573
Revises: 5d3f51590801
Create Date: 2026-10-02 19:15:57.983090

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bdf942c29573"
down_revision: str | Sequence[str] | None = "5d3f51590801"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "movimentacao_estoque",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("estoque_id", sa.Integer(), nullable=False),
        sa.Column(
            "tipo",
            sa.Enum(
                "ENTRADA",
                "SAIDA",
                name="tipo_movimentacao",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("quantidade", sa.Integer(), nullable=False),
        sa.Column("motivo", sa.String(length=200), nullable=False),
        sa.Column("pedido_id", sa.Integer(), nullable=True),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
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
            "quantidade > 0", name=op.f("ck_movimentacao_estoque_quantidade_positiva")
        ),
        sa.ForeignKeyConstraint(
            ["estoque_id"], ["estoque.id"], name=op.f("fk_movimentacao_estoque_estoque_id_estoque")
        ),
        sa.ForeignKeyConstraint(
            ["pedido_id"], ["pedido.id"], name=op.f("fk_movimentacao_estoque_pedido_id_pedido")
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"], ["usuario.id"], name=op.f("fk_movimentacao_estoque_usuario_id_usuario")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_movimentacao_estoque")),
    )
    op.create_index(
        op.f("ix_movimentacao_estoque_estoque_id"),
        "movimentacao_estoque",
        ["estoque_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_movimentacao_estoque_estoque_id"), table_name="movimentacao_estoque")
    op.drop_table("movimentacao_estoque")
